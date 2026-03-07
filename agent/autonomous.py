import json
import logging
import re

from agent.llm_provider import get_llm, invoke_with_retry
from agent.tools import run_tool

logger = logging.getLogger(__name__)

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
    llm = get_llm("autonomous")

    already_known = [k for k in ["filesystem", "code", "architecture"] if k in memory]

    prompt = (
        SYSTEM_PROMPT
        + f"\n\nProject path: {project_path}"
        + f"\nAlready gathered (do NOT re-run these tools): {already_known}"
        + f"\nCurrent memory:\n{json.dumps({k: v for k, v in memory.items() if k != 'history'}, indent=2)}"
    )

    logger.debug("Autonomous step — known tools: %s", already_known)
    content = invoke_with_retry(llm, prompt)
    decision = _extract_json(content)

    tool = decision.get("tool", "none")

    if tool != "none" and tool not in memory:
        result = run_tool(tool, project_path)
        memory[tool] = result
    elif tool != "none" and tool in memory:
        logger.info("Skipping '%s' — already in memory.", tool)

    return decision, memory


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON found in LLM output: {text[:200]}")
    return json.loads(match.group())
