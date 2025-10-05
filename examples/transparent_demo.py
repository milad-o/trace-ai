"""Transparent AI Demo - See Everything!

This demo shows EVERYTHING the agent does:
- Every step of reasoning
- Every tool call with arguments
- Every todo created/updated
- Every agent decision
- Full execution trace

No black box - complete transparency!
"""

import os
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree
from rich.live import Live
from rich.table import Table
from rich import print as rprint

from traceai.agents import create_enterprise_agent

console = Console()


def print_header():
    """Print header."""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Enterprise Assistant - Transparent Demo[/bold cyan]\n"
        "[dim]See every step, tool call, todo, and decision[/dim]",
        border_style="cyan"
    ))
    console.print()


def check_api_key():
    """Check API key."""
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    elif os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    else:
        console.print("[red]Error: No API key found[/red]")
        console.print("\nSet: export OPENAI_API_KEY=your_key")
        console.print("  or: export ANTHROPIC_API_KEY=your_key")
        sys.exit(1)


def stream_with_visibility(agent, query):
    """Stream agent response with full visibility of steps."""
    console.print(f"\n[bold yellow]Query:[/bold yellow] {query}")
    console.print()

    step_num = 0
    current_tool = None
    todos = []

    # Stream the response to see intermediate steps
    for chunk in agent.analyze_stream(query, stream_mode="updates"):
        if not chunk:
            continue

        # Check for agent steps
        if "agent" in chunk:
            agent_data = chunk["agent"]

            # Check for messages
            if "messages" in agent_data:
                for msg in agent_data["messages"]:
                    # Tool calls
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            step_num += 1

                            # Create a nice panel for each tool call
                            tool_name = tool_call.get('name', 'unknown')
                            tool_args = tool_call.get('args', {})

                            # Special handling for write_todos
                            if tool_name == 'write_todos':
                                console.print(Panel(
                                    f"[bold green]📝 Planning Step {step_num}[/bold green]\n\n"
                                    f"[cyan]Tool:[/cyan] write_todos\n"
                                    f"[cyan]Creating plan with {len(tool_args.get('todos', []))} todos[/cyan]",
                                    border_style="green"
                                ))

                                # Show todos
                                if 'todos' in tool_args:
                                    table = Table(title="📋 Todos Created", show_header=True)
                                    table.add_column("Status", style="cyan")
                                    table.add_column("Task", style="white")

                                    for todo in tool_args['todos']:
                                        status = todo.get('status', 'pending')
                                        task = todo.get('task', todo.get('description', 'Unknown'))

                                        status_icon = {
                                            'pending': '⏸️  Pending',
                                            'in_progress': '▶️  In Progress',
                                            'completed': '✅ Completed'
                                        }.get(status, status)

                                        table.add_row(status_icon, task)
                                        todos.append(todo)

                                    console.print(table)
                                    console.print()

                            # Other tools
                            else:
                                console.print(Panel(
                                    f"[bold blue]🔧 Tool Call {step_num}[/bold blue]\n\n"
                                    f"[cyan]Tool:[/cyan] {tool_name}\n"
                                    f"[cyan]Arguments:[/cyan] {tool_args}",
                                    border_style="blue"
                                ))

                    # Agent response
                    if hasattr(msg, 'content') and msg.content and not hasattr(msg, 'tool_calls'):
                        console.print(Panel(
                            f"[white]{msg.content}[/white]",
                            title="[green]💬 Agent Response[/green]",
                            border_style="green"
                        ))
                        console.print()

        # Check for tool results
        if "tools" in chunk:
            tools_data = chunk["tools"]
            if "messages" in tools_data:
                for msg in tools_data["messages"]:
                    if hasattr(msg, 'content'):
                        console.print(Panel(
                            f"[dim]{msg.content[:500]}...[/dim]" if len(msg.content) > 500 else f"[dim]{msg.content}[/dim]",
                            title="[yellow]⚙️  Tool Result[/yellow]",
                            border_style="yellow"
                        ))
                        console.print()


def main():
    print_header()

    provider = check_api_key()
    console.print(f"[green]✓ Using {provider.upper()}[/green]\n")

    # Initialize
    console.print("[bold]Initializing Agent...[/bold]")
    samples_dir = Path(__file__).parent / "sample_packages"
    agent = create_enterprise_agent(
        documents_dir=samples_dir,
        model_provider=provider,
    )

    console.print(f"[green]✓ Loaded {len(agent.parsed_documents)} packages[/green]")
    console.print(f"[green]✓ Graph: {agent.graph.number_of_nodes()} nodes, {agent.graph.number_of_edges()} edges[/green]")
    console.print()

    # Demo 1: Simple query to see tool usage
    console.print(Panel.fit(
        "[bold]Demo 1: Simple Query[/bold]\n"
        "Watch the agent select and use tools",
        border_style="cyan"
    ))

    stream_with_visibility(agent, "What packages are in the knowledge graph?")

    # Demo 2: Complex query with planning
    console.print(Panel.fit(
        "[bold]Demo 2: Complex Analysis with Planning[/bold]\n"
        "Watch the agent create a plan with write_todos, then execute step by step",
        border_style="cyan"
    ))

    stream_with_visibility(agent, """
Analyze the CustomerETL package comprehensively:
1. List all tasks
2. Find all tables involved
3. Trace data lineage for the Customer table
4. Analyze impact if Customer table changes

Plan this out step by step using todos.
""")

    # Demo 3: Impact analysis
    console.print(Panel.fit(
        "[bold]Demo 3: Impact Analysis[/bold]\n"
        "Watch the agent use graph tools to analyze impact",
        border_style="cyan"
    ))

    stream_with_visibility(agent,
        "What tasks would be affected if I change the Customer table schema? "
        "Use the impact analysis tools."
    )

    # Summary
    console.print()
    console.print(Panel.fit(
        "[bold green]✓ Demo Complete![/bold green]\n\n"
        "[white]You saw:[/white]\n"
        "  📝 Todos being created (write_todos)\n"
        "  🔧 Tools being called with arguments\n"
        "  ⚙️  Tool results being processed\n"
        "  💬 Agent reasoning at each step\n\n"
        "[dim]Complete transparency - no black box![/dim]",
        border_style="green"
    ))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        console.print("[dim]" + traceback.format_exc() + "[/dim]")
