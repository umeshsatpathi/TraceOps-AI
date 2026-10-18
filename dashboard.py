"""TraceShield AI | Security Operations Dashboard.
Run: python -m streamlit run dashboard.py
"""
from __future__ import annotations

import html
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from graph_db import get_graph
from graph_tools import get_evidence, score_priority, trace_impact
from graph_intelligence import correlated_findings, what_if_classification
from autonomous_investigator import (
    autonomous_investigate,
    get_investigation_memory,
    plan_investigation,
)

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="TraceShield AI | Security Operations", page_icon="🛡️", layout="wide")

st.markdown("""<style>
.block-container {padding-top: 1.6rem; max-width: 1450px;}
[data-testid="stMetric"] {background: rgba(128,128,128,.07); border: 1px solid rgba(128,128,128,.18); padding: 12px; border-radius: 12px;}
</style>""", unsafe_allow_html=True)

REMEDIATED = {"REMEDIATED", "RESOLVED", "FIXED", "CLOSED"}


def safe_query(cypher: str, params: dict | None = None):
    graph = get_graph()
    if params is None:
        return graph.ro_query(cypher).result_set
    return graph.ro_query(cypher, params=params).result_set


def properties(node) -> dict:
    if node is None:
        return {}
    if isinstance(node, dict):
        return node
    props = getattr(node, "properties", None)
    if isinstance(props, dict):
        return props
    if callable(props):
        try:
            value = props()
            if isinstance(value, dict):
                return value
        except Exception:
            pass
    return {"value": str(node)}


def load_findings() -> list[dict]:
    rows = safe_query("""MATCH (f:Finding)
        RETURN f.id, f.title, f.type, f.severity_level, f.status, f.source
        ORDER BY f.id""")
    result = []
    for finding_id, title, kind, severity, status, source in rows:
        if not finding_id:
            continue
        try:
            priority = score_priority(str(finding_id))
            inherent = int(priority.get("priority_score", 0))
        except Exception:
            inherent = 0
        status = str(status or "UNKNOWN").upper()
        result.append({
            "ID": str(finding_id), "Finding": title or kind or "Unknown finding",
            "Type": kind or "UNKNOWN", "Severity": severity,
            "Status": status, "Source": source or "unknown",
            "Inherent Risk": inherent,
            "Queue": "Regression monitoring" if status in REMEDIATED else "Needs investigation",
        })
    # Make actual scanner observations prominent; keep fixtures visible separately.
    return sorted(result, key=lambda x: (
        x["Status"] in REMEDIATED,
        str(x["Source"]) == "synthetic_fixture",
        -x["Inherent Risk"],
        x["ID"],
    ))


def get_tests() -> list[dict]:
    try:
        rows = safe_query("MATCH (t:TestResult) RETURN t LIMIT 100")
    except Exception:
        return []
    return [properties(row[0]) for row in rows]


def dot_escape(value) -> str:
    return str(value if value is not None else "Unknown").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def build_dot(finding_id: str, paths: list[dict]) -> str:
    lines = [
        'digraph TraceShield {',
        'rankdir=LR; bgcolor="transparent"; pad="0.25"; nodesep="0.55"; ranksep="0.7";',
        'node [shape=box, style="rounded,filled", fillcolor="#1e293b", fontcolor="white", color="#475569", fontname="Arial", margin="0.18,0.12"];',
        'edge [color="#38bdf8", arrowsize=0.7];',
        f'finding [label="Finding\\n{dot_escape(finding_id)}", fillcolor="#9a3412"];',
    ]
    created = set()
    for index, path in enumerate(paths):
        previous = "finding"
        for key, label, fill in [
            ("endpoint", "Endpoint", "#164e63"),
            ("service", "Service", "#1e3a8a"),
            ("database", "Database", "#4c1d95"),
            ("asset", "Data Asset", "#7f1d1d" if path.get("classification") == "sensitive" else "#365314"),
        ]:
            value = path.get(key)
            if value is None:
                continue
            node_id = f"n{index}_{key}"
            detail = f"\\n({dot_escape(path.get('classification'))})" if key == "asset" and path.get("classification") else ""
            if node_id not in created:
                lines.append(f'{node_id} [label="{label}\\n{dot_escape(value)}{detail}", fillcolor="{fill}"];')
                created.add(node_id)
            lines.append(f"{previous} -> {node_id};")
            previous = node_id
    lines.append("}")
    return "\n".join(lines)


def run_command(args: list[str], timeout: int = 90):
    try:
        completed = subprocess.run(
            [sys.executable, *args], cwd=ROOT, capture_output=True,
            text=True, timeout=timeout, encoding="utf-8", errors="replace"
        )
        return completed.returncode, (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
    except subprocess.TimeoutExpired:
        return 124, f"Command timed out after {timeout} seconds."
    except Exception as exc:
        return 1, f"Unable to run command: {exc}"


st.title("🛡️ TraceShield AI")
st.caption("Graph-powered security operations · FalkorDB + Gemini · local authorized DemoShop testing")

try:
    findings = load_findings()
except Exception as exc:
    st.error("Cannot read the FalkorDB findings graph. Ensure Docker and FalkorDB are running.")
    st.exception(exc)
    st.stop()

unresolved = [f for f in findings if f["Status"] not in REMEDIATED]
remediated = [f for f in findings if f["Status"] in REMEDIATED]
confirmed = [f for f in unresolved if f["Status"] in {"CONFIRMED", "OPEN", "ACTIVE"}]

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total findings", len(findings))
m2.metric("Unresolved", len(unresolved))
m3.metric("Remediated", len(remediated))
m4.metric("Confirmed & unresolved", len(confirmed))

st.info("Risk score describes **inherent graph impact**, not current exploitability. Remediated findings stay visible for regression monitoring, but are not automatically ranked above unresolved findings.")

tab_overview, tab_graph, tab_reasoning, tab_timeline, tab_auto, tab_agent, tab_scanner = st.tabs([
    "📊 Investigation Queue", "🕸️ Impact Graph", "🧠 Graph Reasoning", "🧪 Verification Timeline", "⚡ Autonomous Investigation", "🤖 Gemini Agent", "🔎 Local Scanners"
])

with tab_overview:
    st.subheader("Current investigation queue")
    st.caption("Scanner observations are shown first. Seeded fixtures remain available for graph demos but are not independently verified issues.")
    real = [f for f in findings if f["Source"] != "synthetic_fixture"]
    fixtures = [f for f in findings if f["Source"] == "synthetic_fixture"]
    actionable = [f for f in real if f["Status"] not in REMEDIATED]
    if real:
        st.dataframe(pd.DataFrame(real), hide_index=True, use_container_width=True)
    else:
        st.info("No scanner-originated findings yet. Run the local scanners.")
    if actionable:
        candidate = actionable[0]
        st.markdown(f"**Next actionable investigation:** `{candidate['ID']}` — {candidate['Finding']} (inherent risk {candidate['Inherent Risk']}/100).")
        st.caption("Recommendation is based on unresolved scanner-originated findings; it is not a proof of exploitability.")
    elif real:
        st.success("All observed scanner findings are marked remediated or closed; continue regression testing.")
    if fixtures:
        with st.expander(f"Show {len(fixtures)} seeded demonstration finding(s)"):
            st.dataframe(pd.DataFrame(fixtures), hide_index=True, use_container_width=True)
            st.caption("F-001 and F-002 are canonical findings evaluated by live scanners; verification retests update their lifecycle state directly.")

with tab_graph:
    if not findings:
        st.info("Graph visualization will appear when findings exist.")
    else:
        selected = st.selectbox("Select a finding", [f["ID"] for f in findings], key="graph_finding")
        selected_row = next(f for f in findings if f["ID"] == selected)
        try:
            paths = trace_impact(selected)
            evidence = get_evidence(selected)
            st.markdown(f"**{selected_row['Finding']}** · Status: `{selected_row['Status']}` · Inherent risk: **{selected_row['Inherent Risk']}/100**")
            if paths:
                st.graphviz_chart(build_dot(selected, paths), use_container_width=True)
                with st.expander("Show raw graph paths"):
                    st.json(paths)
            else:
                st.warning("No impact path is linked to this finding yet.")
            st.subheader("Evidence attached to finding")
            if evidence:
                for item in evidence:
                    st.write(f"**{item.get('id', 'Evidence')}** — {item.get('summary', '')}")
                    st.caption(f"Observed evidence confirmed: {item.get('confirmed', 'unknown')}")
            else:
                st.caption("No Evidence nodes linked to this finding.")
        except Exception as exc:
            st.error(f"Could not render graph: {exc}")

with tab_reasoning:
    st.subheader("Graph-grounded correlation and what-if reasoning")
    st.caption("Related findings are discovered through shared FalkorDB topology. Correlation is not proof that the same underlying defect exists.")
    if findings:
        choice = st.selectbox("Investigation finding", [f["ID"] for f in findings], index=next((i for i, x in enumerate(findings) if x["ID"] in ("F-001", "F-004")), 0), key="reasoning_finding")
        try:
            related = correlated_findings(choice)
            if related:
                st.markdown("**Connected findings (from live graph traversals)**")
                for other in related:
                    matches = ", ".join(other.get("reasons", []))
                    target = next((x for x in findings if x["ID"] == other["finding_id"]), None)
                    target_status = target["Status"] if target else "UNKNOWN"
                    st.write(f"`{other['finding_id']}` · **{other.get('title','Finding')}** · {target_status} · {matches}")
                st.info("A remediated finding does not automatically remediate another finding sharing an endpoint. Evidence must be evaluated for each claim.")
            else:
                st.caption("No other finding shares an endpoint, service, or database with this finding.")
        except Exception as exc:
            st.warning(f"Graph correlation unavailable: {exc}")
        st.divider()
        st.markdown("**Counterfactual: what if linked data were public?**")
        st.caption("Uses the existing risk formula and the finding's live graph paths, but changes classification in memory only.")
        if st.button("Calculate graph what-if", key="whatif"):
            try:
                result = what_if_classification(choice, "public")
                if "error" in result:
                    st.info(result.get("note") or result["error"])
                else:
                    left, right, delta = st.columns(3)
                    left.metric("Actual risk", result["actual_score"])
                    right.metric("Hypothetical risk", result["hypothetical_score"])
                    delta.metric("Change", result["change"])
                    st.caption(result["note"])
            except Exception as exc:
                st.error(f"What-if calculation failed: {exc}")

with tab_timeline:
    st.subheader("Authorization verification history")
    st.caption("Raw TestResult records from FalkorDB. Test outcomes are historical observations, not guarantees of future security.")
    tests = get_tests()
    if tests:
        def sort_key(t):
            return str(t.get("checked_at") or t.get("timestamp") or t.get("tested_at") or t.get("created_at") or "")
        tests = sorted(tests, key=sort_key)
        for i, test in enumerate(tests, start=1):
            outcome = str(test.get("outcome") or test.get("result") or test.get("status") or "UNKNOWN").upper()
            symbol = "✅" if outcome in {"DENIED", "PASS", "PASSED", "SECURE"} else "🚨" if outcome in {"CONFIRMED", "FAIL", "FAILED", "VULNERABLE"} else "🧪"
            stage = "Detection" if outcome in {"CONFIRMED", "FAIL", "FAILED", "VULNERABLE"} else "Retest" if outcome in {"DENIED", "PASS", "PASSED", "SECURE"} else "Test"
            heading = f"{symbol} {stage} {i} · {outcome} · {test.get('checked_at', 'time unavailable')}"
            with st.expander(heading, expanded=i == len(tests)):
                st.json(test)
    else:
        st.info("No TestResult nodes found. Run `python -m scanners.bola_check` to create a test record.")
    st.markdown("**Recommended follow-up:** Verify F-001 remains protected across additional orders and users; resolve F-002's missing CSP header and rescan.")


with tab_auto:
    st.subheader("Graph-directed autonomous investigation")
    st.caption("This is the 'agent acts on connected data' path: TraceShield reads FalkorDB, chooses a safe action, executes an allow-listed localhost verifier, and writes the decision and result back to FalkorDB.")
    st.warning("Autonomous execution is intentionally constrained: only fixed read-only/synthetic tests against `127.0.0.1:8000` are allowed. No arbitrary URLs, shell commands, credentials, or automatic code remediation.")
    if findings:
        default_index = next((i for i, x in enumerate(findings) if x["ID"] == "F-004"), 0)
        auto_choice = st.selectbox(
            "Finding to investigate",
            [f["ID"] for f in findings],
            index=default_index,
            key="autonomy_finding",
        )
        try:
            plan = plan_investigation(auto_choice)
            if "error" in plan:
                st.error(plan["error"])
            else:
                context = plan["context"]
                decision = plan["decision"]
                op = plan.get("operational_context", {})
                a, b, c, d = st.columns(4)
                a.metric("Current status", context["finding"].get("status", "UNKNOWN"))
                b.metric("Inherent risk", context.get("priority", {}).get("priority_score", 0))
                c.metric("Action", decision.get("action_kind", "REVIEW_ONLY"))
                d.metric("Owner", op.get("owner_team_name") or "Unassigned")

                st.markdown("**Why the graph selected this action**")
                st.write(decision.get("reason", "No decision reason available."))
                if decision.get("sensitive_assets"):
                    st.write("Sensitive assets considered:", ", ".join(decision["sensitive_assets"]))
                if decision.get("related_findings"):
                    st.write("Related findings considered:", ", ".join(x for x in decision["related_findings"] if x))
                if op.get("project_name") or op.get("owner_team_name"):
                    st.caption(f"Operational context: project={op.get('project_name') or 'unknown'} · owner={op.get('owner_team_name') or 'unassigned'}")

                if st.button("⚡ Run graph-directed investigation", type="primary", key="run_autonomy"):
                    with st.spinner("Reading graph → selecting allow-listed action → executing verifier → recording audit trail..."):
                        result = autonomous_investigate(auto_choice, execute=True)
                    st.session_state["last_autonomy_result"] = result

                last = st.session_state.get("last_autonomy_result")
                if last:
                    post_id = last.get("post_investigation", {}).get("finding", {}).get("id")
                    if post_id == auto_choice:
                        execution = last.get("execution", {})
                        if execution.get("status") == "SUCCEEDED":
                            st.success(f"Action completed and recorded in FalkorDB · Investigation {last.get('investigation_id')}")
                        elif execution.get("status") == "NO_ACTION":
                            st.info(f"Investigation recorded without automated execution · {last.get('investigation_id')}")
                        else:
                            st.error(f"Action did not complete successfully · {last.get('investigation_id')}")
                        st.markdown("**Executed action output**")
                        st.code(execution.get("output") or "No command output", language="text")
                        new_tests = execution.get("new_test_results") or []
                        if new_tests:
                            st.caption("New graph TestResult node(s): " + ", ".join(new_tests))

                st.divider()
                st.markdown("**Persistent investigation memory**")
                memory = get_investigation_memory(auto_choice)
                if memory:
                    memory_rows = []
                    for item in memory:
                        memory_rows.append({
                            "Investigation": item.get("investigation_id"),
                            "Started": item.get("started_at"),
                            "Decision": item.get("action_kind"),
                            "Action status": item.get("action_status"),
                            "Exit": item.get("exit_code"),
                        })
                    st.dataframe(pd.DataFrame(memory_rows), hide_index=True, use_container_width=True)
                    with st.expander("Show latest decision rationale"):
                        st.write(memory[0].get("reason") or "No stored rationale")
                else:
                    st.caption("No autonomous investigation history exists for this finding yet.")
        except Exception as exc:
            st.error(f"Autonomous investigation unavailable: {exc}")

with tab_agent:
    st.subheader("Ask the graph-powered security agent")
    question = st.text_area("Investigation request", value="Compare F-001 and F-002 using current verification evidence. Recommend the next unresolved investigation, separating historical impact from current status.", height=110)
    if st.button("Run Gemini investigation", type="primary"):
        with st.spinner("Investigating graph and generating report..."):
            rc, output = run_command(["agent_autonomous.py", question], timeout=120)
        if rc == 0:
            st.success("Investigation complete")
        else:
            st.error(f"Agent exited with code {rc}")
        st.code(output or "No output returned", language="text")

with tab_scanner:
    demo_port = os.getenv("DEMOSHOP_PORT", "5001")
    st.subheader("Authorized localhost-only scanning")
    st.warning(f"These controls run local synthetic tests against DemoShop on port {demo_port}. Start DemoShop in another terminal first.")
    left, right = st.columns(2)
    with left:
        if st.button("Scan missing HTTP headers"):
            with st.spinner("Scanning DemoShop response headers..."):
                rc, output = run_command(["-m", "scanners.http_headers"])
            st.code(output or "No output", language="text")
            if rc == 0:
                st.success("Scanner finished. Refresh the page to update graph results.")
            else:
                st.error("Scanner failed. Check DemoShop and the terminal output.")
    with right:
        if st.button("Run synthetic-user BOLA test"):
            with st.spinner("Testing DemoShop order authorization..."):
                rc, output = run_command(["-m", "scanners.bola_check"])
            st.code(output or "No output", language="text")
            if rc == 0:
                st.info("Test recorded. Refresh the page to see its current status and history.")
            else:
                st.error("Test command failed. Inspect the output.")
    if st.button("Refresh dashboard data"):
        st.rerun()

st.divider()
st.caption("TraceShield AI · Demonstration environment only. Synthetic accounts and data. Graph impact and security findings are not proof of real-world exploitability.")
