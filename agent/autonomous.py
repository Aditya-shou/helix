import json
import re

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

from agent.tools import run_tool

load_dotenv()

llm = ChatAnthropic(
    model_name="claude-haiku-4-5-20251001",
    temperature=0,
)  # pyright: ignore[reportCallIssue]

SYSTEM_PROMPT = """
You are Helix, an autonomous engineering agent.
You may choose tools to understand the project.
Available tools:
- filesystem
- code
- architecture

Rules:
- If a tool's data already exists in memory, do NOT call it again.
- Only call a tool if its key is missing from current memory.
- Once all needed tools are called, respond with "tool": "none".

Respond ONLY in JSON:
{
  "thought": "...",
  "tool": "tool_name or none",
  "reason": "...why..."
}
"""


def autonomous_step(project_path: str, memory: dict):
    # Tell the LLM exactly what we already know
    already_known = [k for k in ["filesystem", "code", "architecture"] if k in memory]

    prompt = f"""
        Project path: {project_path}
        Already gathered (do NOT re-run these tools): {already_known}
        Current memory:
        {json.dumps({k: v for k, v in memory.items() if k != "history"}, indent=2)}
    """

    response = llm.invoke(SYSTEM_PROMPT + prompt)
    content = response.content

    if isinstance(content, list):
        content = "".join(str(x) for x in content)

    decision = extract_json(content)

    tool = decision.get("tool", "none")

    # Guard: skip if tool already ran
    if tool != "none" and tool not in memory:
        result = run_tool(tool, project_path)
        memory[tool] = result
    elif tool != "none" and tool in memory:
        print(f"[Helix] Skipping '{tool}' — already in memory.")

    return decision, memory


def extract_json(text: str):
    """Extract JSON object from LLM response."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON found in LLM output")
    return json.loads(match.group())
