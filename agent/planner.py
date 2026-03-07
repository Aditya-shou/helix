import logging

from agent.llm_provider import get_llm, invoke_with_retry

logger = logging.getLogger(__name__)


def create_plan(projects: list) -> str:
    llm = get_llm("planner")

    summary = ""
    for p in projects:
        analysis = p.get("analysis", {})
        code_info = p.get("code_info", {})
        arch = p.get("architecture", {})
        summary += f"""
Project: {p["name"]}
Goals: {p["goals"]}
Files: {analysis.get("files", 0)}
Tests: {analysis.get("tests", 0)}
CLI: {analysis.get("has_cli")}
Classes: {code_info.get("total_classes", 0)}
Functions: {code_info.get("total_functions", 0)}
Models: {code_info.get("models", [])}
Entry Points: {arch.get("entry_points", [])}
Dependencies: {list(arch.get("dependencies", {}).keys())[:10]}
"""

    prompt = f"""
You are an engineering productivity agent.

Analyze the projects and suggest the NEXT actionable steps.

Rules:
- Be concise
- Suggest practical coding tasks
- Focus on unfinished work

Projects:
{summary}

Return bullet points only.
"""

    logger.debug("Creating plan for %d project(s)", len(projects))
    return invoke_with_retry(llm, prompt)
