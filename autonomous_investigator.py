"""TraceShield AI — graph-directed autonomous investigation loop.

This module deliberately keeps execution narrow and auditable:
- it reads connected context from FalkorDB,
- selects only allow-listed defensive actions,
- executes only localhost synthetic/read-only scanners,
- stores the decision and action outcome back in FalkorDB,
- never accepts an arbitrary URL or shell command.

Use:
    python autonomous_investigator.py plan F-004
    python autonomous_investigator.py run F-004
    python autonomous_investigator.py history F-004
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from graph_db import get_graph
from graph_intelligence import investigate
from action_policy import choose_safe_action

ROOT = Path(__file__).resolve().parent
# Hard allow-list. No user-provided commands or targets are accepted.
ACTION_COMMANDS = {
    "RUN_SYNTHETIC_BOLA_CHECK": ["-m", "scanners.bola_check"],
    "RUN_HTTP_HEADER_RESCAN": ["-m", "scanners.http_headers"],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()



def _trim(text: str, limit: int = 1800) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 30] + "... [truncated]"


def get_operational_context(finding_id: str) -> dict:
    """Return project/team ownership connected to the finding when available."""
    graph = get_graph()
    rows = graph.ro_query(
        """
        MATCH (f:Finding {id:$id})-[:AFFECTS]->(e:Endpoint)
        OPTIONAL MATCH (w:Website)-[:EXPOSES]->(e)
        OPTIONAL MATCH (p:Project)-[:CONTAINS]->(w)
        OPTIONAL MATCH (e)-[:ROUTES_TO]->(s:Service)
        OPTIONAL MATCH (team_service:Team)-[:OWNS]->(s)
        OPTIONAL MATCH (team_web:Team)-[:OWNS]->(w)
        RETURN p.id, p.name, w.name, s.name,
               team_service.id, team_service.name,
               team_web.id, team_web.name
        LIMIT 1
        """,
        params={"id": finding_id},
    ).result_set
    if not rows:
        return {}
    row = rows[0]
    owner_id = row[4] or row[6]
    owner_name = row[5] or row[7]
    return {
        "project_id": row[0],
        "project_name": row[1],
        "website": row[2],
        "service": row[3],
        "owner_team_id": owner_id,
        "owner_team_name": owner_name,
    }


def plan_investigation(finding_id: str) -> dict:
    """Read live graph context and return the safe action plan without executing it."""
    context = investigate(finding_id)
    if "error" in context:
        return context
    return {
        "finding_id": finding_id,
        "context": context,
        "operational_context": get_operational_context(finding_id),
        "decision": choose_safe_action(context),
        "guardrails": {
            "arbitrary_url_allowed": False,
            "arbitrary_shell_command_allowed": False,
            "external_targets_allowed": False,
            "automatic_code_remediation_allowed": False,
            "allowed_target": "127.0.0.1:8000",
        },
    }


def _all_test_ids() -> set[str]:
    graph = get_graph()
    try:
        rows = graph.ro_query("MATCH (t:TestResult) RETURN t.id").result_set
    except Exception:
        return set()
    return {str(row[0]) for row in rows if row and row[0]}


def _create_investigation_nodes(finding_id: str, decision: dict, operational: dict) -> tuple[str, str, str]:
    graph = get_graph()
    inv_id = "INV-" + uuid4().hex[:12].upper()
    decision_id = "DEC-" + uuid4().hex[:12].upper()
    action_id = "ACT-" + uuid4().hex[:12].upper()
    started_at = _now()

    graph.query(
        """
        MATCH (f:Finding {id:$finding_id})
        CREATE (i:Investigation {
            id:$inv_id, started_at:$started_at,
            source:'autonomous_investigator', status:'RUNNING'
        })
        CREATE (d:Decision {
            id:$decision_id, action_kind:$action_kind,
            reason:$reason, selected_by:'graph_policy_v1',
            created_at:$started_at
        })
        CREATE (a:Action {
            id:$action_id, kind:$action_kind,
            label:$action_label, target:$target,
            execution_mode:$execution_mode,
            status:'PLANNED', created_at:$started_at
        })
        CREATE (i)-[:INVESTIGATES]->(f)
        CREATE (i)-[:MADE_DECISION]->(d)
        CREATE (d)-[:SELECTED]->(a)
        CREATE (a)-[:TARGETS]->(f)
        """,
        params={
            "finding_id": finding_id,
            "inv_id": inv_id,
            "decision_id": decision_id,
            "action_id": action_id,
            "started_at": started_at,
            "action_kind": decision["action_kind"],
            "reason": decision["reason"],
            "action_label": decision["action_label"],
            "target": str(decision.get("target") or finding_id),
            "execution_mode": decision["execution_mode"],
        },
    )

    # Preserve exactly which evidence and sensitive assets were consulted.
    graph.query(
        """
        MATCH (i:Investigation {id:$inv_id})-[:INVESTIGATES]->(f:Finding)
        MATCH (f)-[:SUPPORTED_BY]->(ev:Evidence)
        MERGE (i)-[:USED_EVIDENCE]->(ev)
        """,
        params={"inv_id": inv_id},
    )
    graph.query(
        """
        MATCH (i:Investigation {id:$inv_id})-[:INVESTIGATES]->(f:Finding)-[:AFFECTS]->(:Endpoint)-[:ROUTES_TO]->(:Service)-[:QUERIES]->(:Database)-[:STORES]->(asset:DataAsset)
        MERGE (i)-[:CONSIDERED]->(asset)
        """,
        params={"inv_id": inv_id},
    )

    owner_team_id = operational.get("owner_team_id")
    if owner_team_id:
        graph.query(
            """
            MATCH (a:Action {id:$action_id}), (t:Team {id:$team_id})
            MERGE (a)-[:ASSIGNED_TO]->(t)
            """,
            params={"action_id": action_id, "team_id": owner_team_id},
        )

    return inv_id, decision_id, action_id


def _finish_action(inv_id: str, action_id: str, status: str, exit_code: int | None, output: str) -> None:
    graph = get_graph()
    completed_at = _now()
    graph.query(
        """
        MATCH (i:Investigation {id:$inv_id})
        MATCH (a:Action {id:$action_id})
        SET i.status=$inv_status, i.completed_at=$completed_at,
            a.status=$action_status, a.exit_code=$exit_code,
            a.completed_at=$completed_at, a.output_summary=$output
        """,
        params={
            "inv_id": inv_id,
            "action_id": action_id,
            "inv_status": "COMPLETED" if status in {"SUCCEEDED", "NO_ACTION"} else "FAILED",
            "action_status": status,
            "exit_code": exit_code,
            "completed_at": completed_at,
            "output": _trim(output),
        },
    )


def _link_new_test_results(action_id: str, new_ids: set[str]) -> None:
    if not new_ids:
        return
    graph = get_graph()
    for test_id in sorted(new_ids):
        graph.query(
            """
            MATCH (a:Action {id:$action_id}), (t:TestResult {id:$test_id})
            MERGE (a)-[:PRODUCED]->(t)
            """,
            params={"action_id": action_id, "test_id": test_id},
        )


def _run_allowlisted(action_kind: str, timeout: int = 75) -> tuple[int, str]:
    args = ACTION_COMMANDS.get(action_kind)
    if args is None:
        raise ValueError(f"Action is not executable: {action_kind}")
    try:
        completed = subprocess.run(
            [sys.executable, *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        output = (completed.stdout or "") + (("\n" + completed.stderr) if completed.stderr else "")
        return completed.returncode, output.strip()
    except subprocess.TimeoutExpired:
        return 124, f"Allow-listed action timed out after {timeout} seconds."
    except Exception as exc:
        return 1, f"Unable to execute allow-listed action: {exc}"


def autonomous_investigate(finding_id: str, execute: bool = True) -> dict:
    """Plan, execute an allow-listed action, and persist the full audit trail."""
    plan = plan_investigation(finding_id)
    if "error" in plan:
        return plan

    decision = plan["decision"]
    inv_id, decision_id, action_id = _create_investigation_nodes(
        finding_id, decision, plan["operational_context"]
    )

    before_tests = _all_test_ids()
    if not execute or decision["action_kind"] == "REVIEW_ONLY":
        message = (
            "Execution disabled; investigation and decision were recorded only."
            if not execute
            else "No allow-listed automated verifier exists for this finding type; recorded for manual review."
        )
        _finish_action(inv_id, action_id, "NO_ACTION", None, message)
        return {
            "investigation_id": inv_id,
            "decision_id": decision_id,
            "action_id": action_id,
            "decision": decision,
            "execution": {"status": "NO_ACTION", "exit_code": None, "output": message},
            "post_investigation": investigate(finding_id),
            "guardrails": plan["guardrails"],
        }

    exit_code, output = _run_allowlisted(decision["action_kind"])
    after_tests = _all_test_ids()
    new_tests = after_tests - before_tests
    action_status = "SUCCEEDED" if exit_code == 0 else "FAILED"
    _finish_action(inv_id, action_id, action_status, exit_code, output)
    _link_new_test_results(action_id, new_tests)

    return {
        "investigation_id": inv_id,
        "decision_id": decision_id,
        "action_id": action_id,
        "decision": decision,
        "execution": {
            "status": action_status,
            "exit_code": exit_code,
            "output": output,
            "new_test_results": sorted(new_tests),
        },
        "post_investigation": investigate(finding_id),
        "operational_context": get_operational_context(finding_id),
        "guardrails": plan["guardrails"],
    }


def get_investigation_memory(finding_id: str) -> list[dict]:
    """Read persistent investigation/decision/action history across sessions."""
    graph = get_graph()
    rows = graph.ro_query(
        """
        MATCH (i:Investigation)-[:INVESTIGATES]->(f:Finding {id:$id})
        OPTIONAL MATCH (i)-[:MADE_DECISION]->(d:Decision)-[:SELECTED]->(a:Action)
        RETURN i.id, i.started_at, i.completed_at, i.status,
               d.id, d.action_kind, d.reason,
               a.id, a.status, a.exit_code, a.output_summary
        ORDER BY i.started_at DESC
        LIMIT 20
        """,
        params={"id": finding_id},
    ).result_set
    keys = (
        "investigation_id", "started_at", "completed_at", "investigation_status",
        "decision_id", "action_kind", "reason",
        "action_id", "action_status", "exit_code", "output_summary",
    )
    return [dict(zip(keys, row)) for row in rows]


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="TraceShield graph-directed autonomous investigator")
    sub = parser.add_subparsers(dest="mode", required=True)
    p_plan = sub.add_parser("plan")
    p_plan.add_argument("finding_id")
    p_run = sub.add_parser("run")
    p_run.add_argument("finding_id")
    p_history = sub.add_parser("history")
    p_history.add_argument("finding_id")
    args = parser.parse_args()

    if args.mode == "plan":
        result = plan_investigation(args.finding_id)
    elif args.mode == "run":
        result = autonomous_investigate(args.finding_id, execute=True)
    else:
        result = get_investigation_memory(args.finding_id)
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
