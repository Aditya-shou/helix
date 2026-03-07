import logging

from agent.llm_provider import get_llm, invoke_with_retry

logger = logging.getLogger(__name__)


def reflect_on_plan(plan: str, projects: list) -> str:
    llm = get_llm("reflection")

    project_summary = ""
    for p in projects:
        analysis = p.get("analysis", {})
        project_summary += (
            f"\nProject: {p['name']}"
            f"\nGoals: {p['goals']}"
            f"\nFiles: {analysis.get('files', 0)}"
            f"\nTests: {analysis.get('tests', 0)}"
            f"\nCLI: {analysis.get('has_cli')}\n"
        )

    prompt = f"""
You are a senior engineering reviewer.

A planning agent created the following plan and progress context:

PLAN / ANALYSIS:
{plan}

PROJECT CONTEXT:
{project_summary}

Your job:
1. Identify vague or generic suggestions.
2. Remove steps for work that is already done (check progress_delta if present).
3. Make remaining recommendations more concrete and actionable.
4. DO NOT repeat the original plan blindly.

Return an improved plan as bullet points only.
"""

    logger.debug("Running reflection")
    return invoke_with_retry(llm, prompt)
