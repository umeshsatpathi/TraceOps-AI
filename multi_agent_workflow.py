
"""
TraceShield AI - Multi-Agent Security Investigation

Agent 1: Investigator
    - Reads connected security graph context
    - Analyzes findings and related assets
    - Records an investigation
    - Prepares a handoff
    - Does NOT execute verification

Agent 2: Verifier
    - Reads shared investigation state from FalkorDB
    - Reviews the approved action plan
    - Executes only allow-listed local verification
    - Reads updated investigation history
    - Summarizes the result

Usage:
    python multi_agent_workflow.py F-004

Requirements:
    - FalkorDB running
    - DemoShop local server running
    - GOOGLE_API_KEY configured in .env
"""

import os
import re
import sys

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from agent_graph_tools_v2 import (
    investigate_graph_context,
    record_graph_investigation,
)

from agent_autonomy_tools import (
    plan_safe_graph_action,
    run_autonomous_security_investigation,
    recall_investigation_history,
)


load_dotenv()


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


# ---------------------------------------------------------
# Helper: Create Gemini model
# ---------------------------------------------------------

def create_gemini_model():
    """Initialize Gemini for TraceShield agents."""

    if not os.getenv("GOOGLE_API_KEY"):
        raise SystemExit(
            "[ERROR] GOOGLE_API_KEY is missing from .env"
        )

    return ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        temperature=0,
        max_retries=0,
    )


# ---------------------------------------------------------
# Helper: Clean Gemini response
# ---------------------------------------------------------

def clean_agent_text(message):
    """
    Extract readable text from a LangChain AIMessage.

    Removes structured response metadata such as
    Gemini's large signature field.
    """

    content = message.content

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []

        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))

            elif isinstance(block, str):
                text_parts.append(block)

        return "\n".join(text_parts).strip()

    return str(content)


# ---------------------------------------------------------
# Helper: Extract final response
# ---------------------------------------------------------

def get_final_response(result):
    """Return readable text from the final agent message."""

    messages = result.get("messages", [])

    if not messages:
        return "No response returned by the agent."

    return clean_agent_text(messages[-1])


# ---------------------------------------------------------
# Helper: Validate finding ID
# ---------------------------------------------------------

def validate_finding_id(finding_id):
    """
    Accept finding IDs such as F-001, F-004, F-123.

    Prevents arbitrary instructions from being inserted
    through the CLI finding ID.
    """

    finding_id = finding_id.strip().upper()

    if not re.fullmatch(r"F-\d{3,}", finding_id):
        raise ValueError(
            "Invalid finding ID. Example: F-004"
        )

    return finding_id


# ---------------------------------------------------------
# Investigator Agent
# ---------------------------------------------------------

def create_investigator_agent():
    """
    Investigator can inspect graph data, plan safe actions,
    and record investigation state.

    It cannot execute the verification tool.
    """

    return create_agent(
        model=create_gemini_model(),

        tools=[
            investigate_graph_context,
            plan_safe_graph_action,
            record_graph_investigation,
        ],

        system_prompt=(
            "You are TraceShield AI Investigator Agent. "

            "Your job is to investigate a security finding "
            "using connected data stored in FalkorDB. "

            "Use the available graph tools to inspect the "
            "finding, evidence, connected services, databases, "
            "sensitive assets, and related findings. "

            "Read the safe action plan and record the "
            "investigation using the available tool. "

            "You must NOT execute security verification. "

            "Your final response must be a concise handoff "
            "for the Verifier Agent. "

            "Include the finding ID, current status, "
            "affected assets, relevant evidence, "
            "approved verification action, and reason. "

            "Never claim a verification was executed "
            "unless the graph evidence confirms it."
        ),
    )


# ---------------------------------------------------------
# Verifier Agent
# ---------------------------------------------------------

def create_verifier_agent():
    """
    Verifier reads the shared FalkorDB investigation
    history and executes approved local verification.
    """

    return create_agent(
        model=create_gemini_model(),

        tools=[
            recall_investigation_history,
            plan_safe_graph_action,
            run_autonomous_security_investigation,
        ],

        system_prompt=(
            "You are TraceShield AI Verifier Agent. "

            "Your job is to verify an investigated security "
            "finding using the shared FalkorDB graph state. "

            "First, read the investigation history using "
            "the provided history tool. "

            "Then inspect the safe action plan. "

            "Execute verification ONLY through the provided "
            "run_autonomous_security_investigation tool. "

            "Do not execute arbitrary commands, scan external "
            "websites, or perform automatic code remediation. "

            "The permitted test environment is the authorized "
            "local DemoShop demonstration environment. "

            "After executing the verification tool, read "
            "the investigation history again. "

            "Report the actual execution status, HTTP test "
            "results, and any recorded TestResult IDs. "

            "Distinguish historical risk from current "
            "verification status. "

            "If execution fails, explain the failure "
            "rather than claiming success. "

            "Do not invent test results or graph records."
        ),
    )


# ---------------------------------------------------------
# Main Multi-Agent Workflow
# ---------------------------------------------------------

def run(finding_id="F-004"):

    finding_id = validate_finding_id(finding_id)

    print("=" * 65)
    print("       TRACESHIELD AI - MULTI-AGENT WORKFLOW")
    print("=" * 65)

    print(f"\nFinding ID: {finding_id}")
    print(f"Gemini Model: {MODEL_NAME}")

    # -----------------------------------------------------
    # Phase 1: Investigator
    # -----------------------------------------------------

    print("\n[PHASE 1] Investigator Agent")
    print("[INFO] Reading connected FalkorDB graph context...")
    print("[INFO] Preparing investigation handoff...")

    investigator = create_investigator_agent()

    investigator_result = investigator.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Investigate finding {finding_id}. "
                        "Use the graph investigation tools, "
                        "inspect the safe action plan, "
                        "record the investigation, "
                        "and prepare a verification handoff. "
                        "Do not execute verification."
                    ),
                }
            ]
        }
    )

    handoff = get_final_response(investigator_result)

    print("\n" + "=" * 65)
    print("              INVESTIGATOR AGENT HANDOFF")
    print("=" * 65)

    print(handoff)

    # -----------------------------------------------------
    # Phase 2: Verifier
    # -----------------------------------------------------

    print("\n[PHASE 2] Verifier Agent")
    print("[INFO] Reading shared FalkorDB investigation state...")
    print("[INFO] Executing authorized local verification...")

    verifier = create_verifier_agent()

    verifier_result = verifier.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Verify finding {finding_id}. "
                        "Read the shared investigation history "
                        "from FalkorDB, inspect the safe action "
                        "plan, execute the authorized local "
                        "verification tool, then read the "
                        "updated history and report the result. "

                        "\n\nInvestigator handoff:\n"
                        f"{handoff}"
                    ),
                }
            ]
        }
    )

    verification = get_final_response(verifier_result)

    print("\n" + "=" * 65)
    print("                 VERIFIER AGENT RESULT")
    print("=" * 65)

    print(verification)

    print("\n" + "=" * 65)
    print("             MULTI-AGENT WORKFLOW FINISHED")
    print("=" * 65)

    return {
        "finding_id": finding_id,
        "model": MODEL_NAME,
        "investigator_handoff": handoff,
        "verifier_report": verification,
    }


# ---------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------

if __name__ == "__main__":

    finding_id = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "F-004"
    )

    try:
        run(finding_id)

    except KeyboardInterrupt:
        print("\n[TraceShield] Workflow interrupted.")
        sys.exit(130)

    except Exception as error:

        error_message = str(error)

        if (
            "RESOURCE_EXHAUSTED" in error_message
            or "429" in error_message
            or "quota" in error_message.lower()
        ):
            print("\n[ERROR] Gemini API quota exhausted.")
            print(
                "[INFO] The multi-agent workflow could "
                "not complete."
            )
            print(
                "[INFO] You can still run the deterministic "
                "graph investigation:"
            )
            print(
                f"python autonomous_investigator.py run {finding_id}"
            )

        else:
            print(
                f"\n[ERROR] Multi-agent workflow failed: "
                f"{error}"
            )

        sys.exit(1)
