
"""
TraceShield AI — Graph-Powered Security Investigation Agent

Technologies:
- Google Gemini: LLM reasoning and tool selection
- LangChain / LangGraph: Agent orchestration
- FalkorDB: Security knowledge graph

Run:
    python agent.py "Investigate F-001"
"""

import json
import os
import sys

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

from graph_tools import (
    get_finding,
    trace_impact,
    get_evidence,
    score_priority,
)

from agent_graph_tools_v2 import (
    investigate_graph_context,
    compare_graph_contexts,
    simulate_data_classification_change,
    record_graph_investigation,
)



# ------------------------------------------------
# 1. Load environment variables
# ------------------------------------------------

load_dotenv()


# ------------------------------------------------
# 2. Define tools available to the AI agent
# ------------------------------------------------

@tool
def read_finding(finding_id: str) -> str:
    """
    Retrieve a security finding from FalkorDB.

    Returns its type, severity, status and other
    available attributes.
    """
    try:
        result = get_finding(finding_id)
        return json.dumps(result, default=str)
    except Exception as error:
        return json.dumps({"error": str(error), "finding_id": finding_id})


@tool
def trace_finding_impact(finding_id: str) -> str:
    """
    Trace a security finding through FalkorDB.

    Retrieves related endpoints, services,
    databases and sensitive data assets.
    """
    try:
        result = trace_impact(finding_id)
        return json.dumps(result, default=str)
    except Exception as error:
        return json.dumps({"error": str(error), "finding_id": finding_id})


@tool
def inspect_finding_evidence(finding_id: str) -> str:
    """
    Retrieve supporting security evidence.

    Helps distinguish confirmed vulnerabilities
    from suspected or unverified findings.
    """
    try:
        result = get_evidence(finding_id)
        return json.dumps(result, default=str)
    except Exception as error:
        return json.dumps({"error": str(error), "finding_id": finding_id})


@tool
def calculate_finding_priority(finding_id: str) -> str:
    """
    Calculate a context-aware security risk score.

    Uses connected graph relationships and
    security severity instead of guessing.
    """
    try:
        result = score_priority(finding_id)
        return json.dumps(result, default=str)
    except Exception as error:
        return json.dumps({"error": str(error), "finding_id": finding_id})


@tool
def compare_security_findings(finding_ids: list[str]) -> str:
    """
    Compare two or more security findings.

    Retrieve finding details, graph relationships,
    supporting evidence, and risk scores from FalkorDB.

    Use this tool when the user asks to compare,
    rank, or prioritize multiple findings.
    """

    if not 2 <= len(finding_ids) <= 10:
        return json.dumps({
            "error": "Provide between 2 and 10 finding IDs."
        })

    investigations = []

    for finding_id in dict.fromkeys(finding_ids):
        finding_id = finding_id.strip()

        try:
            finding = get_finding(finding_id)

            if not finding:
                investigations.append({
                    "finding_id": finding_id,
                    "error": "Finding not found"
                })
                continue

            investigations.append({
                "finding_id": finding_id,
                "finding": finding,
                "impact_path": trace_impact(finding_id),
                "evidence": get_evidence(finding_id),
                "priority": score_priority(finding_id),
            })

        except Exception as error:
            investigations.append({
                "finding_id": finding_id,
                "error": str(error)
            })

    return json.dumps(
        {"investigations": investigations},
        default=str
    )



# ------------------------------------------------
# 3. Create Gemini model
# ------------------------------------------------

def create_llm():

    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY not found. "
            "Add GOOGLE_API_KEY=your_api_key to your .env file."
        )


    model_name = os.getenv(
        "GEMINI_MODEL",
        "gemini-2.5-flash"
    )

    print(f"\n[TraceShield] Gemini model: {model_name}")

    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0,
        max_retries=2,
    )


# ------------------------------------------------
# 4. Build security investigation agent
# ------------------------------------------------

def build_agent():

    model = create_llm()

    
    tools = [
        read_finding,
        trace_finding_impact,
        inspect_finding_evidence,
        calculate_finding_priority,
        compare_security_findings,
        investigate_graph_context,
        compare_graph_contexts,
        simulate_data_classification_change,
        record_graph_investigation,
    ]


    system_prompt = """
You are TraceShield AI, a graph-powered cybersecurity
investigation assistant.

Your job is to investigate security findings using
the FalkorDB security knowledge graph.

MANDATORY INVESTIGATION WORKFLOW:

1. Use read_finding to retrieve the finding.
2. Use trace_finding_impact to investigate
   connected endpoints, backend services,
   databases and sensitive data assets.
3. Use inspect_finding_evidence to inspect
   verification evidence.
4. Use calculate_finding_priority to determine
   the context-aware priority score.
5. Generate a structured security report.

IMPORTANT RULES:

- Always use graph tools before reaching conclusions.
- Never invent vulnerabilities, scores or evidence.
- Never claim an unverified issue is confirmed.
- A dependency relationship is not proof of exploitability.
- All initial seed data is synthetic.
- Never claim a real website was scanned unless
  verified scanner results are provided.
- Recommend only authorized, non-destructive
  verification steps.
- Do not suggest automatically modifying
  production infrastructure.

RESPONSE FORMAT:

Finding ID:
Vulnerability Type:
Severity:
Verification Status:
Risk Score:

Affected Components:
- Endpoint
- Backend Service
- Database
- Data Asset

Graph Investigation:
Explain the actual connected path.

Evidence:
Summarize the available evidence and any limitations.

Potential Impact:
Describe realistic impact without exaggeration.

Recommended Remediation:
Provide actionable defensive fixes.

Next Investigation Step:
Specify any additional verification required.

Only include claims supported by tool results.


MULTIPLE FINDING INVESTIGATION:

You can investigate and compare multiple findings.

If the user requests a comparison between two or more
findings, use compare_security_findings with all their IDs.

For example:
compare_security_findings(
    finding_ids=["F-001", "F-002"]
)

For a single finding, use the individual graph tools.

When comparing multiple findings:

1. Retrieve the findings from FalkorDB.
2. Compare their technical severity.
3. Compare affected endpoints and services.
4. Compare connections to sensitive data assets.
5. Compare the deterministic risk scores.
6. Check the evidence status of each finding.
7. Rank the findings by investigation priority.
8. Explain why one should be investigated first.

Never invent missing graph relationships or findings.
Never treat an unverified finding as a confirmed vulnerability.

Do not refuse a multi-finding comparison simply because
individual tools accept one finding ID.


CURRENT-RISK PRIORITIZATION RULES:

Distinguish inherent risk from current remediation status.

A high historical risk score does not automatically mean
a finding is the highest current investigation priority.

When comparing findings:

1. Retrieve the latest verification status and evidence.
2. Separate confirmed active vulnerabilities from
   remediated vulnerabilities.
3. Prioritize unresolved findings based on their
   graph-derived risk scores and evidence confidence.
4. Treat REMEDIATED findings with successful verification
   as regression-monitoring candidates, unless newer
   evidence contradicts the remediation.
5. Explain the historical impact of remediated findings,
   but do not rank them above unresolved findings solely
   because of their original severity.
6. If verification history is incomplete, explicitly
   state that the remediation confidence is uncertain.

Never confuse risk score with exploitability probability.
Never claim a vulnerability is fully eliminated based
on a single successful test.
"""

    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
    )

    return agent


# ------------------------------------------------
# 5. Run the agent
# ------------------------------------------------

def main():

    query = (
        " ".join(sys.argv[1:])
        or "Investigate security finding F-001. "
           "Explain the possible impact and next steps."
    )

    print("\n" + "=" * 60)
    print("       TRACESHIELD AI - GRAPH SECURITY AGENT")
    print("=" * 60)

    print(f"\nUser Query: {query}")

    try:
        agent = build_agent()
    except RuntimeError as err:
        print(f"\n[TraceShield] Cannot run AI agent: {err}")
        sys.exit(1)

    print("\n[TraceShield] Investigating FalkorDB graph...\n")


    try:
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": query,
                    }
                ]
            },
            config={
                "recursion_limit": 20
            }
        )

        print("\n" + "=" * 60)
        print("              SECURITY INVESTIGATION REPORT")
        print("=" * 60 + "\n")

        # Display final agent response
        final_message = result["messages"][-1]

        content = final_message.content

        if isinstance(content, str):
            print(content)
        else:
            print(json.dumps(content, indent=2, default=str))

    except Exception as error:

        print("\n[TraceShield] Investigation failed.")
        print(f"Error: {error}")

        raise


# ------------------------------------------------
# 6. Entry point
# ------------------------------------------------

if __name__ == "__main__":
    main()
