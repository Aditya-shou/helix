from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

load_dotenv()


reflection_llm = ChatAnthropic(
    model_name="claude-haiku-4-5-20251001",
    temperature=0.1,
)  # pyright: ignore[reportCallIssue]


def reflect_on_plan(plan: str, projects) -> str:
    project_summary = ""

    for p in projects:
        analysis = p.get("analysis", {})
        project_summary += f"""
Project: {p["name"]}
Goals: {p["goals"]}
Files: {analysis.get("files", 0)}
Tests: {analysis.get("tests", 0)}
CLI: {analysis.get("has_cli")}
"""

    prompt = f"""
You are a senior engineering reviewer.

A planning agent created the following plan:

PLAN:
{plan}

PROJECT CONTEXT:
{project_summary}

Your job:
1. Identify vague or generic suggestions.
2. Remove unnecessary steps.
3. Make recommendations more concrete and actionable.
4. DO NOT repeat the original plan blindly.

Return an improved plan as bullet points only.
"""

    response = reflection_llm.invoke(prompt)

    content = response.content
    if isinstance(content, list):
        content = "\n".join(str(c) for c in content)

    return str(content)
