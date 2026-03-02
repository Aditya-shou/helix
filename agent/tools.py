from agent.architecture import analyze_architecture
from agent.code_understanding import analyze_codebase
from agent.filesystem import analyze_project_structure

TOOLS = {
    "filesystem": analyze_project_structure,
    "code": analyze_codebase,
    "architecture": analyze_architecture,
}


def run_tool(tool_name: str, path: str):
    if tool_name not in TOOLS:
        return {"error": f"Unknown tool {tool_name}"}

    return TOOLS[tool_name](path)
