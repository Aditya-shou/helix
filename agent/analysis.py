import json

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

load_dotenv()

analysis_llm = ChatAnthropic(
    model_name="claude-haiku-4-5-20251001",
    temperature=0,
)  # pyright: ignore[reportCallIssue]

SYSTEM_PROMPT = """
You are Helix, a senior software architect.

Analyze the project understanding and suggest:
1. Improvements
2. Missing components
3. Architectural risks
4. Next engineering tasks

Be specific and actionable.
"""


def analyze_project(memory: dict) -> str:

    prompt = f"""
Project understanding:

{json.dumps(memory, indent=2)}

Provide a structured improvement analysis.
"""

    response = analysis_llm.invoke(SYSTEM_PROMPT + prompt)

    content = response.content

    if isinstance(content, list):
        content = "".join(str(x) for x in content)

    return content
