import json
import logging
import re

from agent.llm_provider import get_llm, invoke_with_retry

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You convert engineering analysis into structured tasks.

Return ONLY a JSON array — no preamble, no markdown fences:

[
  {
    "task": "short_snake_case_id",
    "description": "...",
    "priority": "P0|P1|P2",
    "estimated_hours": number
  }
]
"""


def extract_tasks(analysis_text: str) -> list[dict]:
    llm = get_llm("task")

    prompt = SYSTEM_PROMPT + "\n\n" + analysis_text

    logger.debug("Extracting tasks from analysis")
    content = invoke_with_retry(llm, prompt)

    match = re.search(r"\[.*\]", content, re.DOTALL)
    if not match:
        logger.error("No JSON array found in task extractor output: %s", content[:300])
        raise ValueError("No JSON array found in LLM output")

    return json.loads(match.group())
