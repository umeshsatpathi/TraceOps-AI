"""TraceShield AI agent with graph-grounded autonomous action tools.

Run examples:
  python agent_autonomous.py "Autonomously investigate F-004 and verify its current state"
  python agent_autonomous.py "Compare F-003 and F-004 and tell me what action should happen next"
"""
import os
import sys
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from agent_graph_tools_v2 import (
    investigate_graph_context,
    compare_graph_contexts,
    simulate_data_classification_change,
    record_graph_investigation,
)
from agent_autonomy_tools import (
    plan_safe_graph_action,
    run_autonomous_security_investigation,
    recall_investigation_history,
)

load_dotenv()

SYSTEM_PROMPT = """
You are TraceShield, a defensive graph-security investigation agent operating only
on the user's authorized local DemoShop demonstration environment.

Your job is to reason from connected FalkorDB data and use tools when needed.

RULES:
1. Always distinguish inherent graph impact from current exploitability/state.
2. A REMEDIATED finding is a regression-monitoring candidate unless newer evidence
   contradicts the remediation. Do not rank it above an unresolved finding solely
   because its historical/inherent risk score is higher.
3. A graph dependency path is potential impact, not proof of exploitability.
4. A scanner observation proves only the tested condition. State evidence limits.
5. For ordinary analysis, use graph investigation/comparison tools.
6. If the user asks to autonomously investigate, verify, retest, or take the next
   safe action, first call plan_safe_graph_action, then call
   run_autonomous_security_investigation when the plan is appropriate.
7. Autonomous execution is allowed only through the provided tool. Never invent or
   request an arbitrary target, URL, credential, or shell command.
8. When prior actions matter, call recall_investigation_history and use the stored
   graph memory instead of guessing.
9. Never claim that a successful single retest proves the whole application secure.
10. Be explicit when data is synthetic, locally observed, unverified, or remediated.

When you report a decision, explain which graph connections, evidence, prior state,
and current status caused that decision.
"""


def build_agent():
    if not os.getenv("GOOGLE_API_KEY"):
        raise SystemExit("Set GOOGLE_API_KEY in .env before running the Gemini agent.")

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    model = ChatGoogleGenerativeAI(model=model_name, temperature=0)
    tools = [
        investigate_graph_context,
        compare_graph_contexts,
        simulate_data_classification_change,
        record_graph_investigation,
        plan_safe_graph_action,
        run_autonomous_security_investigation,
        recall_investigation_history,
    ]
    return model_name, create_agent(model=model, tools=tools, system_prompt=SYSTEM_PROMPT)


def main():
    model_name, agent = build_agent()
    query = " ".join(sys.argv[1:]) or "Investigate F-004 using its graph context and prior verification history."

    print("=" * 60)
    print("       TRACESHIELD AI - AUTONOMOUS GRAPH AGENT")
    print("=" * 60)
    print(f"\nUser Query: {query}\n")
    print(f"[TraceShield] Gemini model: {model_name}")
    print("[TraceShield] Connected-data tools + allow-listed local actions enabled.\n")

    result = agent.invoke({"messages": [{"role": "user", "content": query}]})
    print("=" * 60)
    print("              SECURITY INVESTIGATION REPORT")
    print("=" * 60)
    
    final_message = result["messages"][-1]
    content = final_message.content

    if isinstance(content, str):
        print(content)

    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                print(block.get("text", ""))

    else:
        print(str(content))



if __name__ == "__main__":
    main()
