"""Performance comparison: Async vs Sync document loading.

This script demonstrates the speed improvements when using AsyncEnterpriseAgent
for loading and parsing multiple documents concurrently.
"""

import asyncio
import time
from pathlib import Path

from rich.console import Console
from rich.table import Table

from traceai.agents import EnterpriseAgent, AsyncEnterpriseAgent

console = Console()


def sync_load_documents():
    """Load documents using sync agent."""
    console.print("\n[bold cyan]═══ Sync Mode ═══[/bold cyan]")

    agent = EnterpriseAgent(persist_dir="../outputs/data_sync")

    start = time.time()

    # Load SSIS packages
    console.print("Loading SSIS packages...")
    agent.load_documents("../inputs/ssis")

    # Load COBOL and JCL
    console.print("Loading COBOL and JCL...")
    agent.load_documents("../inputs/cobol", pattern="*.cbl")
    agent.load_documents("../inputs/jcl", pattern="*.jcl")

    # Load JSON, CSV, Excel
    console.print("Loading JSON, CSV, Excel...")
    agent.load_documents("../inputs/json", pattern="*.json")
    agent.load_documents("../inputs/csv", pattern="*.csv")
    agent.load_documents("../inputs/excel", pattern="*.xlsx")

    elapsed = time.time() - start

    # Get stats
    stats = agent.get_graph_stats()

    return elapsed, stats, agent


async def async_load_documents():
    """Load documents using async agent."""
    console.print("\n[bold green]═══ Async Mode ═══[/bold green]")

    agent = AsyncEnterpriseAgent(
        persist_dir="../outputs/data_async",
        max_concurrent_parsers=20  # Higher concurrency for better performance
    )

    start = time.time()

    # Load all document types concurrently
    console.print("Loading all documents concurrently...")
    await asyncio.gather(
        agent.load_documents("../inputs/ssis"),
        agent.load_documents("../inputs/cobol", pattern="*.cbl"),
        agent.load_documents("../inputs/jcl", pattern="*.jcl"),
        agent.load_documents("../inputs/json", pattern="*.json"),
        agent.load_documents("../inputs/csv", pattern="*.csv"),
        agent.load_documents("../inputs/excel", pattern="*.xlsx"),
    )

    elapsed = time.time() - start

    # Get stats
    stats = agent.get_graph_stats()

    return elapsed, stats, agent


def print_results(sync_time, async_time, sync_stats, async_stats):
    """Print comparison results in a nice table."""
    console.print("\n[bold yellow]═══ Performance Comparison ═══[/bold yellow]\n")

    # Timing table
    timing_table = Table(title="Load Time Comparison", show_header=True, header_style="bold magenta")
    timing_table.add_column("Mode", style="cyan", width=12)
    timing_table.add_column("Time (seconds)", justify="right", style="green")
    timing_table.add_column("Speedup", justify="right", style="yellow")

    speedup = sync_time / async_time if async_time > 0 else 0
    timing_table.add_row("Sync", f"{sync_time:.2f}s", "1.0x")
    timing_table.add_row("Async", f"{async_time:.2f}s", f"{speedup:.2f}x")

    console.print(timing_table)

    # Graph stats table
    stats_table = Table(title="Knowledge Graph Statistics", show_header=True, header_style="bold magenta")
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Sync", justify="right", style="white")
    stats_table.add_column("Async", justify="right", style="white")

    stats_table.add_row("Total Nodes", str(sync_stats.get("total_nodes", 0)), str(async_stats.get("total_nodes", 0)))
    stats_table.add_row("Total Edges", str(sync_stats.get("total_edges", 0)), str(async_stats.get("total_edges", 0)))
    stats_table.add_row("Documents", str(sync_stats.get("documents", 0)), str(async_stats.get("documents", 0)))
    stats_table.add_row("Components", str(sync_stats.get("components", 0)), str(async_stats.get("components", 0)))
    stats_table.add_row("Data Sources", str(sync_stats.get("data_sources", 0)), str(async_stats.get("data_sources", 0)))

    console.print("\n", stats_table)

    # Summary
    console.print(f"\n[bold green]✓ Async mode is {speedup:.2f}x faster![/bold green]")
    console.print(f"[dim]Time saved: {sync_time - async_time:.2f} seconds[/dim]\n")


async def demo_streaming():
    """Demonstrate async streaming responses."""
    console.print("\n[bold magenta]═══ Streaming Demo ═══[/bold magenta]\n")

    agent = AsyncEnterpriseAgent(persist_dir="../outputs/data_async")

    # Load some documents first
    console.print("Loading sample documents...")
    await agent.load_documents("../inputs/ssis")

    # Stream a query
    console.print("\n[cyan]Question:[/cyan] What data transformations are in the CustomerETL package?\n")
    console.print("[yellow]Response (streaming):[/yellow] ", end="")

    async for chunk in agent.query_stream("What data transformations are in the CustomerETL package?"):
        console.print(chunk, end="", style="white")

    console.print("\n")


def main():
    """Run the comparison demo."""
    console.print("\n[bold blue]╔═══════════════════════════════════════════════╗[/bold blue]")
    console.print("[bold blue]║   TraceAI: Async vs Sync Performance Test    ║[/bold blue]")
    console.print("[bold blue]╚═══════════════════════════════════════════════╝[/bold blue]\n")

    # Check if example files exist
    inputs_dir = Path("../inputs")
    if not inputs_dir.exists():
        console.print("[red]Error: ../inputs directory not found![/red]")
        console.print("[yellow]Please run this script from examples/scripts/ directory[/yellow]")
        return

    # Run sync test
    try:
        sync_time, sync_stats, sync_agent = sync_load_documents()
        console.print(f"[green]✓ Sync mode completed in {sync_time:.2f}s[/green]")
    except Exception as e:
        console.print(f"[red]✗ Sync mode failed: {e}[/red]")
        return

    # Run async test
    try:
        async_time, async_stats, async_agent = asyncio.run(async_load_documents())
        console.print(f"[green]✓ Async mode completed in {async_time:.2f}s[/green]")
    except Exception as e:
        console.print(f"[red]✗ Async mode failed: {e}[/red]")
        return

    # Print comparison
    print_results(sync_time, async_time, sync_stats, async_stats)

    # Optional: Demo streaming (requires API key)
    if input("\nDemo async streaming? (requires API key) [y/N]: ").lower() == 'y':
        try:
            asyncio.run(demo_streaming())
        except Exception as e:
            console.print(f"[red]Streaming demo failed: {e}[/red]")


if __name__ == "__main__":
    main()
