from rich import print

from agent.graph import build_graph
from agent.state import AgentState

agent = build_graph()

state: AgentState = {
    "user_goal": "Update project progress",
    "projects": [],
    "updates": [],
}

result = agent.invoke(state)

print("\n[bold green]Agent Updates:[/bold green]")
for u in result["updates"]:
    print("-", u)
