import json
import logging

from agent.llm_provider import get_llm, invoke_with_retry

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are Helix, a senior software architect.

Analyze the project and return ONLY this structure — nothing else:

RISKS (max 3 bullet points):
- ...

MISSING (max 3 bullet points):
- ...

NEXT TASKS (max 5, most important first):
- ...

Rules:
- Each bullet point is ONE line maximum
- If progress_delta shows something improved, do NOT suggest it again
- No headers beyond the three above, no markdown tables, no long explanations
"""


def analyze_project(memory: dict) -> str:
    llm = get_llm("analysis")

    prompt = SYSTEM_PROMPT + f"\n\nProject data:\n{json.dumps(memory, indent=2)}"

    logger.debug("Running project analysis")
    return invoke_with_retry(llm, prompt)
