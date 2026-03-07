#!/usr/bin/env python3
"""
helix_cli.py
------------
The main entry point for Helix.

Commands:
    python helix_cli.py run                  — analyze all projects, short summary
    python helix_cli.py status               — show project progress at a glance
    python helix_cli.py tasks [--project N]  — list open tasks
    python helix_cli.py chat                 — interactive mode: ask Helix anything
    python helix_cli.py done <task_key>      — mark a task as completed

Usage examples:
    python helix_cli.py run
    python helix_cli.py tasks --project 1
    python helix_cli.py chat
    python helix_cli.py done setup_pytest_framework
"""

import argparse
import sys
import textwrap

from rich import box
from rich.console import Console
from rich.table import Table

console = Console()


# Helpers


def _short_summary(text: str, max_lines: int = 6) -> str:
    """Trim any long LLM output to the first max_lines non-empty lines."""
    lines = [l for l in text.splitlines() if l.strip()]
    trimmed = lines[:max_lines]
    if len(lines) > max_lines:
        trimmed.append(f"  ... (+{len(lines) - max_lines} more lines)")
    return "\n".join(trimmed)


def _priority_color(priority: str) -> str:
    return {"P0": "red", "P1": "yellow", "P2": "cyan"}.get(priority, "white")


# Commands


def cmd_run(args: argparse.Namespace) -> None:
    """Run the full Helix pipeline across all projects — concise output."""
    from agent.graph import build_graph
    from agent.logging_config import setup_logging
    from agent.state import AgentState

    setup_logging()

    console.print("\n[bold cyan]Helix[/bold cyan] — starting analysis...\n")

    state: AgentState = {
        "user_goal": "analyze all projects",
        "projects": [],
        "updates": [],
    }

    agent = build_graph()

    with console.status("[cyan]Thinking...[/cyan]", spinner="dots"):
        result = agent.invoke(state)

    #  Print concise per-project results
    project_results = result.get("project_results", [])

    for r in project_results:
        status_color = "green" if r["progress_score"] >= 0.5 else "yellow"
        console.print(
            f"[bold]{r['project_name']}[/bold]  "
            f"[{status_color}]{r['progress_score']:.0%} complete[/{status_color}]"
        )

        if r["delta_summary"] and "No measurable" not in r["delta_summary"]:
            for line in r["delta_summary"].splitlines():
                if line.strip():
                    console.print(f"  [dim]{line}[/dim]")

        if r["auto_completed"]:
            console.print(
                f"  [green]✓ Auto-completed:[/green] {', '.join(r['auto_completed'])}"
            )

        # Top 3 P0 tasks only
        p0_tasks = [t for t in r["tasks"] if t.get("priority") == "P0"][:3]
        if p0_tasks:
            console.print("  [red]P0 tasks:[/red]")
            for t in p0_tasks:
                console.print(f"    • {t['task']} — {t['description'][:60]}...")

        console.print()

    #  Portfolio summary (trimmed)
    portfolio = result.get("portfolio_summary", "")
    if portfolio:
        console.print("[bold cyan]Focus next:[/bold cyan]")
        console.print(_short_summary(portfolio, max_lines=8))

    console.print("\n[dim]Run `helix tasks` to see full task list.[/dim]\n")


def cmd_status(args: argparse.Namespace) -> None:
    """Show all projects and their current progress score."""
    from db.database import SessionLocal
    from db.models import Project, Task
    from db.snapshot_models import ProjectSnapshot

    session = SessionLocal()

    projects = session.query(Project).all()

    if not projects:
        console.print(
            "[yellow]No projects found. Add one in reset_and_seed.py[/yellow]"
        )
        session.close()
        return

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
    table.add_column("ID", width=4)
    table.add_column("Project", width=20)
    table.add_column("Progress", width=10)
    table.add_column("Status", width=12)
    table.add_column("P0", width=4)
    table.add_column("P1", width=4)
    table.add_column("Open", width=5)
    table.add_column("Done", width=5)
    table.add_column("Last checked", width=16)

    for p in projects:
        p0 = (
            session.query(Task)
            .filter_by(project_id=p.id, priority="P0", status="open")
            .count()
        )
        p1 = (
            session.query(Task)
            .filter_by(project_id=p.id, priority="P1", status="open")
            .count()
        )
        open_t = session.query(Task).filter_by(project_id=p.id, status="open").count()
        done_t = (
            session.query(Task).filter_by(project_id=p.id, status="completed").count()
        )

        score = p.progress_score or 0.0
        score_color = "green" if score >= 0.5 else ("yellow" if score >= 0.2 else "red")
        checked = (
            p.last_checked.strftime("%Y-%m-%d %H:%M") if p.last_checked else "never"
        )

        table.add_row(
            str(p.id),
            p.name,
            f"[{score_color}]{score:.0%}[/{score_color}]",
            p.status,
            f"[red]{p0}[/red]" if p0 else "0",
            f"[yellow]{p1}[/yellow]" if p1 else "0",
            str(open_t),
            f"[green]{done_t}[/green]",
            f"[dim]{checked}[/dim]",
        )

    session.close()
    console.print()
    console.print(table)


def cmd_tasks(args: argparse.Namespace) -> None:
    """List open tasks, optionally filtered by project."""
    from db.database import SessionLocal
    from db.models import Project, Task

    session = SessionLocal()

    query = session.query(Task).filter_by(status="open")

    if args.project:
        query = query.filter_by(project_id=int(args.project))

    tasks = query.order_by(Task.priority, Task.created_at).all()

    if not tasks:
        console.print("[green]No open tasks.[/green]")
        session.close()
        return

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
    table.add_column("Priority", width=8)
    table.add_column("Project", width=16)
    table.add_column("Task key", width=32)
    table.add_column("Est. hrs", width=8)
    table.add_column("Description", width=50)

    # Group by project name
    project_names: dict[int, str] = {}
    for p in session.query(Project).all():
        project_names[p.id] = p.name

    for t in tasks:
        pname = project_names.get(t.project_id, f"#{t.project_id}")
        color = _priority_color(t.priority)
        desc = textwrap.shorten(t.description, width=50, placeholder="...")

        table.add_row(
            f"[{color}]{t.priority}[/{color}]",
            pname,
            t.task_key,
            str(t.estimated_hours),
            f"[dim]{desc}[/dim]",
        )

    session.close()
    console.print()
    console.print(table)
    console.print(f"\n[dim]Total: {len(tasks)} open task(s)[/dim]\n")


def cmd_done(args: argparse.Namespace) -> None:
    """Mark a task as completed by its task_key."""
    from agent.task_persister import mark_task_complete
    from db.database import SessionLocal
    from db.models import Task

    session = SessionLocal()
    task = session.query(Task).filter_by(task_key=args.task_key).first()

    if not task:
        console.print(f"[red]Task '{args.task_key}' not found.[/red]")
        session.close()
        return

    project_id = task.project_id
    session.close()

    success = mark_task_complete(project_id, args.task_key)
    if success:
        console.print(
            f"[green]✓[/green] Marked [bold]{args.task_key}[/bold] as completed."
        )
    else:
        console.print(f"[red]Failed to mark '{args.task_key}' as completed.[/red]")


def cmd_chat(args: argparse.Namespace) -> None:
    """
    Interactive mode — ask Helix anything about your projects.
    Helix answers using live DB data + the LLM.
    """
    from agent.llm_provider import get_llm, invoke_with_retry
    from db.database import SessionLocal
    from db.models import Project, Task
    from db.snapshot_models import ProjectSnapshot

    console.print(
        "\n[bold cyan]Helix Chat[/bold cyan] — ask me anything about your projects."
    )
    console.print("[dim]Type 'exit' to quit.\n[/dim]")

    # Build a context snapshot from the DB for the LLM to reference
    session = SessionLocal()
    projects = session.query(Project).all()

    context_lines = ["Current project state:\n"]
    for p in projects:
        open_t = session.query(Task).filter_by(project_id=p.id, status="open").count()
        done_t = (
            session.query(Task).filter_by(project_id=p.id, status="completed").count()
        )
        p0_tasks = (
            session.query(Task)
            .filter_by(project_id=p.id, priority="P0", status="open")
            .limit(5)
            .all()
        )

        context_lines.append(
            f"Project: {p.name}\n"
            f"  Progress: {(p.progress_score or 0):.0%}\n"
            f"  Open: {open_t}  Completed: {done_t}\n"
            f"  Top P0 tasks: {', '.join(t.task_key for t in p0_tasks) or 'none'}\n"
        )

    session.close()
    db_context = "\n".join(context_lines)

    llm = get_llm("analysis")
    history: list[dict] = []

    while True:
        try:
            user_input = console.input("[bold cyan]You:[/bold cyan] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Bye.[/dim]")
            break

        if user_input.lower() in ("exit", "quit", "q"):
            console.print("[dim]Bye.[/dim]")
            break

        if not user_input:
            continue

        history.append({"role": "user", "content": user_input})

        # Build full prompt with DB context + conversation history
        history_text = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Helix'}: {m['content']}"
            for m in history[-6:]  # last 3 turns
        )

        prompt = (
            "You are Helix, a personal engineering assistant.\n"
            "Answer concisely — max 8 lines. Be direct and specific.\n\n"
            f"{db_context}\n\n"
            f"Conversation:\n{history_text}\n\n"
            "Helix:"
        )

        with console.status("[cyan]Thinking...[/cyan]", spinner="dots"):
            response = invoke_with_retry(llm, prompt)

        history.append({"role": "assistant", "content": response})
        console.print(f"\n[bold]Helix:[/bold] {response.strip()}\n")


# Argument parser


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="helix",
        description="Helix — your personal autonomous engineering assistant",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # run
    sub.add_parser("run", help="Analyze all projects and show a concise summary")

    # status
    sub.add_parser("status", help="Show project progress at a glance")

    # tasks
    tasks_parser = sub.add_parser("tasks", help="List open tasks")
    tasks_parser.add_argument(
        "--project",
        "-p",
        metavar="PROJECT_ID",
        help="Filter by project id",
    )

    # done
    done_parser = sub.add_parser("done", help="Mark a task as completed")
    done_parser.add_argument("task_key", help="The task key to mark complete")

    # chat
    sub.add_parser("chat", help="Interactive mode — ask Helix anything")

    args = parser.parse_args()

    commands = {
        "run": cmd_run,
        "status": cmd_status,
        "tasks": cmd_tasks,
        "done": cmd_done,
        "chat": cmd_chat,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
