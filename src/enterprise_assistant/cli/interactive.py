"""Interactive CLI for TraceAI using the deep agent."""

import os
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from enterprise_assistant.agents import create_enterprise_agent
from enterprise_assistant.logger import logger

# Load environment variables
load_dotenv()

console = Console()


@click.group()
def cli():
    """TraceAI - AI-powered ETL lineage and transformation analysis."""
    pass


@cli.command()
@click.argument("documents_dir", type=click.Path(exists=True, path_type=Path))
@click.option("--model", default="anthropic", type=click.Choice(["anthropic", "openai"]), help="LLM provider")
@click.option(
    "--model-name", default="claude-3-5-sonnet-20241022", help="Model name (e.g., gpt-4, claude-3-5-sonnet-20241022)"
)
def analyze(documents_dir: Path, model: str, model_name: str):
    """
    Start interactive analysis session for documents in DOCUMENTS_DIR.

    Example:
        trace-ai analyze ./examples/sample_packages
    """
    console.print(Panel.fit("🔍 [bold cyan]TraceAI - ETL Lineage Analyzer[/bold cyan]", border_style="cyan"))

    # Load documents and create agent
    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console, transient=True
    ) as progress:
        task = progress.add_task("Loading documents and initializing agent...", total=None)

        try:
            agent = create_enterprise_agent(documents_dir=documents_dir, model_provider=model, model_name=model_name)

            progress.update(task, description="[green]✓ Agent ready!")

        except Exception as e:
            console.print(f"\n[red]Error initializing agent: {e}[/red]")
            logger.error(f"Failed to initialize agent: {e}")
            return

    # Show what was loaded
    if agent.parsed_documents:
        console.print(f"\n[green]✓[/green] Loaded {len(agent.parsed_documents)} documents")
        console.print(
            f"[green]✓[/green] Knowledge graph: {agent.graph.number_of_nodes()} nodes, {agent.graph.number_of_edges()} edges"
        )
    else:
        console.print("\n[yellow]⚠[/yellow] No documents found")
        return

    # Start interactive session
    console.print("\n" + "=" * 80)
    console.print("[bold]Interactive Analysis Session[/bold]")
    console.print("Type your questions below. Commands: /help, /stats, /quit")
    console.print("=" * 80 + "\n")

    while True:
        try:
            query = console.input("\n[bold cyan]🔍 Question:[/bold cyan] ").strip()

            if not query:
                continue

            # Handle commands
            if query.startswith("/"):
                if query in ["/quit", "/exit", "/q"]:
                    console.print("\n[dim]Goodbye![/dim]")
                    break
                elif query == "/help":
                    _show_help()
                    continue
                elif query == "/stats":
                    _show_stats(agent)
                    continue
                else:
                    console.print(f"[yellow]Unknown command: {query}[/yellow]")
                    continue

            # Process query with agent
            with console.status("[bold green]Agent thinking...", spinner="dots"):
                response = agent.analyze(query)

            # Display response
            console.print("\n[bold green]🤖 Agent:[/bold green]")
            console.print(Panel(Markdown(response), border_style="green"))

        except KeyboardInterrupt:
            console.print("\n\n[dim]Session interrupted. Goodbye![/dim]")
            break
        except EOFError:
            console.print("\n\n[dim]Goodbye![/dim]")
            break
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            logger.error(f"Error during analysis: {e}")


@cli.command()
@click.argument("documents_dir", type=click.Path(exists=True, path_type=Path))
@click.argument("query")
@click.option("--model", default="anthropic", type=click.Choice(["anthropic", "openai"]))
@click.option("--model-name", default="claude-3-5-sonnet-20241022")
def ask(documents_dir: Path, query: str, model: str, model_name: str):
    """
    Ask a single question about documents.

    Example:
        trace-ai ask ./examples/sample_packages "What packages do we have?"
    """
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Initializing...", total=None)

        agent = create_enterprise_agent(documents_dir=documents_dir, model_provider=model, model_name=model_name)

        progress.update(task, description="Analyzing...")
        response = agent.analyze(query)

    console.print("\n[bold cyan]Question:[/bold cyan]", query)
    console.print("\n[bold green]Answer:[/bold green]")
    console.print(Panel(Markdown(response), border_style="green"))


def _show_help():
    """Show help information."""
    help_text = """
# Commands

- `/help` - Show this help
- `/stats` - Show graph statistics
- `/quit` or `/exit` - Exit session

# Example Questions

**Discovery:**
- "What documents do we have?"
- "Show me all tasks that contain SQL"
- "Find components that process customer data"

**Impact Analysis:**
- "What will be affected if I change the Customers table?"
- "Which processes read from the Sales database?"

**Data Lineage:**
- "Trace the lineage of the DimCustomer table"
- "Where does customer data come from?"
- "Show me the data flow for Sales"

**Dependencies:**
- "What must run before the ETL task?"
- "Show me the execution order for the CustomerETL package"
    """
    console.print(Panel(Markdown(help_text), title="Help", border_style="cyan"))


def _show_stats(agent):
    """Show graph statistics."""
    if not agent.graph:
        console.print("[yellow]No graph available[/yellow]")
        return

    from enterprise_assistant.graph.queries import GraphQueries

    queries = GraphQueries(agent.graph)
    stats = queries.get_graph_stats()

    stats_text = f"""
# Knowledge Graph Statistics

**Total Nodes:** {stats.get('total_nodes', 0)}
**Total Edges:** {stats.get('total_edges', 0)}

## Node Types
"""
    for key, value in sorted(stats.items()):
        if key.endswith("_nodes") and value > 0:
            node_type = key.replace("_nodes", "").replace("_", " ").title()
            stats_text += f"- **{node_type}:** {value}\n"

    # Vector store stats
    vs_stats = agent.vector_store.get_stats()
    stats_text += f"\n## Vector Store\n- **Indexed Items:** {vs_stats['total_items']}\n"

    console.print(Panel(Markdown(stats_text), title="Statistics", border_style="cyan"))


@cli.command()
def version():
    """Show version information."""
    console.print("[bold cyan]Enterprise Assistant[/bold cyan] v0.1.0")
    console.print("Powered by LangChain, LangGraph, and deepagents")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
