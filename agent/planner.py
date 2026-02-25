from dotenv import load_dotenv

# from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

load_dotenv()


planner_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
)

# alternative:
# planner_llm = ChatAnthropic(model="claude-3-haiku-20240307")


def create_plan(projects):
    summary = ""

    for p in projects:
        analysis = p.get("analysis", {})
        summary += f"""
Project: {p["name"]}
Goals: {p["goals"]}
Files: {analysis.get("files", 0)}
Tests: {analysis.get("tests", 0)}
CLI: {analysis.get("has_cli")}
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

    response = planner_llm.invoke(prompt)

    content = response.content

    # Normalize to string
    if isinstance(content, list):
        content = "\n".join(str(c) for c in content)

    return str(content)
