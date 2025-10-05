"""AI-Powered Demo with Multi-Step Planning.

This demo shows the Enterprise Assistant using OpenAI/Anthropic for:
- Natural language queries
- Multi-step planning with write_todos
- Complex analysis
- Clear terminal output

Requires: OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable
"""

import os
import sys
import re
import logging
from pathlib import Path
from collections import defaultdict

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown
from rich.syntax import Syntax

from traceai.agents import create_enterprise_agent

console = Console()

# Global tool call tracker
captured_tool_calls = []


class ToolCallCaptureHandler(logging.Handler):
    """Custom logging handler to capture tool calls in real-time."""
    
    def __init__(self):
        super().__init__()
        self.tool_calls = []
    
    def emit(self, record):
        """Capture tool calls from log records."""
        if hasattr(record, 'msg') and '🔧 TOOL:' in str(record.msg):
            tool_line = str(record.msg)
            if '🔧 TOOL:' in tool_line:
                tool_name = tool_line.split('🔧 TOOL: ')[1].strip()
                tool_call = {
                    'tool': tool_name,
                    'timestamp': record.created,
                    'level': record.levelname
                }
                self.tool_calls.append(tool_call)
                captured_tool_calls.append(tool_call)


def print_header():
    """Print a nice header."""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Enterprise Assistant - AI-Powered Demo[/bold cyan]\n"
        "[dim]Multi-step planning with write_todos[/dim]",
        border_style="cyan"
    ))
    console.print()


def check_api_key():
    """Check if API key is available."""
    if os.getenv("OPENAI_API_KEY"):
        return "openai", "✓ Using OpenAI API"
    elif os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic", "✓ Using Anthropic API"
    else:
        console.print("[red]✗ Error: No API key found[/red]")
        console.print("\nSet one of these environment variables:")
        console.print("  export OPENAI_API_KEY=your_key")
        console.print("  export ANTHROPIC_API_KEY=your_key")
        sys.exit(1)


def main():
    print_header()

    # Set up tool call capture handler
    tool_handler = ToolCallCaptureHandler()
    logger = logging.getLogger()
    logger.addHandler(tool_handler)

    # Check API key
    provider, key_msg = check_api_key()
    console.print(f"[green]{key_msg}[/green]")
    console.print()

    # Initialize agent with progress indicator
    console.print("[bold]Step 1: Initializing AI-Powered Agent[/bold]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading SSIS packages...", total=None)

        samples_dir = Path(__file__).parent / "sample_packages"
        agent = create_enterprise_agent(
            documents_dir=samples_dir,
            model_provider=provider,
            enable_memory=True,
            enable_audit=True,
            enable_progress=True,
        )

        progress.update(task, description="✓ Agent ready!")

    # Show what was loaded
    console.print()
    graph_nodes = agent.graph.number_of_nodes() if agent.graph else 0
    graph_edges = agent.graph.number_of_edges() if agent.graph else 0
    console.print(Panel(
        f"[green]✓ Loaded {len(agent.parsed_documents)} SSIS packages[/green]\n"
        f"[green]✓ Built knowledge graph: {graph_nodes} nodes, "
        f"{graph_edges} edges[/green]\n"
        f"[green]✓ AI model: {provider}[/green]",
        title="Initialization Complete",
        border_style="green"
    ))
    console.print()

    # Scenario 1: Simple query
    console.print("[bold]Step 2: Simple Natural Language Query[/bold]")
    console.print("[dim]Query: 'What packages are in the knowledge graph?'[/dim]")
    console.print()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("AI is thinking...", total=None)

        response1 = agent.analyze("What packages are in the knowledge graph?")

        progress.update(task, description="✓ Response received!")

    console.print()
    console.print(Panel(response1, title="[cyan]AI Response[/cyan]", border_style="cyan"))
    console.print()

    # Scenario 2: Multi-step planning
    console.print("[bold]Step 3: Complex Query with Multi-Step Planning[/bold]")
    console.print("[dim]The AI will use write_todos to plan this complex task:[/dim]")
    console.print()

    query = """Perform a comprehensive analysis of the CustomerETL package:

1. List all tasks in the package
2. Identify the data flow (what tables are read/written)
3. Trace the lineage for the Customer table
4. Analyze potential impact if the Customer table schema changes
5. Provide recommendations for improving the ETL process

Be thorough and systematic."""

    console.print(Panel(
        query,
        title="[yellow]Complex Query[/yellow]",
        border_style="yellow"
    ))
    console.print()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("AI is planning and executing...", total=None)

        response2 = agent.analyze(query)

        progress.update(task, description="✓ Analysis complete!")

    console.print()
    console.print(Panel(
        response2,
        title="[green]Comprehensive Analysis[/green]",
        border_style="green"
    ))
    console.print()

    # Scenario 3: Impact analysis
    console.print("[bold]Step 4: Impact Analysis Query[/bold]")
    console.print("[dim]Query: 'What would break if I change the Customer table?'[/dim]")
    console.print()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing impact...", total=None)

        response3 = agent.analyze(
            "What would break if I change the Customer table schema? "
            "List all affected tasks and explain the impact."
        )

        progress.update(task, description="✓ Impact analysis complete!")

    console.print()
    console.print(Panel(
        response3,
        title="[red]Impact Analysis[/red]",
        border_style="red"
    ))
    console.print()

    # Show memory stats
    console.print("[bold]Step 5: Memory & Audit Stats[/bold]")
    console.print()

    # Get conversation stats directly from the database
    try:
        from traceai.memory.conversation_store import SQLiteConversationStore
        
        # Access the conversation store directly
        conv_store = SQLiteConversationStore(db_path=agent.persist_dir / "conversation.db")
        stats = conv_store.get_stats()
        
        console.print(Panel(
            f"[cyan]Total messages stored: {stats['total_messages']}[/cyan]\n"
            f"[cyan]Storage type: {stats['storage_type']}[/cyan]\n"
            f"[cyan]Database path: {stats['db_path']}[/cyan]\n"
            f"[dim]All conversations are persisted to SQLite with full-text search[/dim]",
            title="Memory Statistics",
            border_style="cyan"
        ))
    except Exception as e:
        console.print(Panel(
            f"[yellow]Memory stats unavailable: {e}[/yellow]",
            title="Memory Statistics",
            border_style="yellow"
        ))

    # Show tool calls summary
    console.print()
    console.print("[bold]Step 6: Tool Calls Summary[/bold]")
    console.print()
    
    # Display captured tool calls in a proper panel
    if captured_tool_calls:
        tool_calls_display = "[bold cyan]Captured Tool Calls During Demo:[/bold cyan]\n\n"
        
        for i, tool_call in enumerate(captured_tool_calls, 1):
            tool_calls_display += f"[cyan]{i}. {tool_call['tool']}[/cyan]\n"
            tool_calls_display += f"   [dim]Timestamp: {tool_call['timestamp']}[/dim]\n"
            tool_calls_display += f"   [dim]Level: {tool_call['level']}[/dim]\n\n"
        
        # Add statistics
        unique_tools = set(tc['tool'] for tc in captured_tool_calls)
        tool_calls_display += f"[green]✓ {len(captured_tool_calls)} total tool calls captured[/green]\n"
        tool_calls_display += f"[green]✓ {len(unique_tools)} different tool types used[/green]\n"
        tool_calls_display += f"[green]✓ All calls captured in real-time[/green]\n"
        tool_calls_display += f"[green]✓ Full audit trail available[/green]\n\n"
        tool_calls_display += "[dim]This demonstrates the AI's systematic approach to complex analysis![/dim]"
        
        console.print(Panel(
            tool_calls_display,
            title="[bold]Tool Execution Details[/bold]",
            border_style="cyan"
        ))
    else:
        console.print(Panel(
            "[yellow]No tool calls captured during this session[/yellow]\n"
            "[dim]Tool calls are logged to console but not captured in this demo[/dim]",
            title="[bold]Tool Execution Details[/bold]",
            border_style="yellow"
        ))

    console.print()

    # Summary
    console.print(Panel.fit(
        "[bold green]✓ Demo Complete![/bold green]\n\n"
        "[green]The Enterprise Assistant successfully demonstrated its capabilities through:[/green]\n"
        "  • Natural language query processing\n"
        "  • Multi-step planning and execution\n"
        "  • Complex enterprise document analysis\n"
        "  • Impact assessment and recommendations\n"
        "  • Persistent memory and audit logging\n\n"
        "[dim]All tool calls and reasoning steps are visible in the logs above[/dim]",
        border_style="green"
    ))
    console.print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)
