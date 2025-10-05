"""Complex ETL Network Demo - COBOL + JCL + SQLite Integration.

This demo shows how to:
1. Parse a complex network of COBOL programs, JCL jobs, and SQLite databases
2. Build a comprehensive knowledge graph of the entire ETL pipeline
3. Answer complicated questions about data lineage, dependencies, and impact analysis

Example Questions:
- "What's the complete data flow from employee.db to the payroll report?"
- "If I modify the customer table, which COBOL programs and JCL jobs are affected?"
- "Show me all dependencies for the sales batch processing pipeline"
- "What happens if the inventory file fails to load?"
"""

from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich import box
import networkx as nx
import os
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from enterprise_assistant.graph.builder import KnowledgeGraphBuilder
from enterprise_assistant.parsers import parser_registry
from enterprise_assistant.agents.enterprise_agent import create_enterprise_agent

console = Console()


def parse_etl_network():
    """Parse all COBOL, JCL, and database files into a unified knowledge graph."""
    console.print("\n[bold cyan]🔧 Building Complex Mainframe ETL Knowledge Graph...[/bold cyan]\n")

    builder = KnowledgeGraphBuilder()
    examples_dir = Path(__file__).parent

    # Parse COBOL programs from multiple sources
    mainframe_dir = examples_dir / "sample_mainframe"

    # 1. Parse real COBOL samples
    real_cobol_files = list(mainframe_dir.glob("*.cbl")) + list(mainframe_dir.glob("*.CBL"))
    console.print(f"[yellow]📁 Found {len(real_cobol_files)} real COBOL programs[/yellow]")
    for cobol_file in real_cobol_files:
        try:
            parser = parser_registry.get_parser_for_file(cobol_file)
            parsed = parser.parse(cobol_file)
            builder.add_document(parsed)
            console.print(f"  ✓ Parsed {cobol_file.name}")
        except Exception as e:
            console.print(f"  ✗ Error parsing {cobol_file.name}: {e}")

    # 2. Parse synthetic COBOL programs
    synthetic_dir = mainframe_dir / "synthetic" / "cobol"
    if synthetic_dir.exists():
        synthetic_cobol = list(synthetic_dir.glob("*.cbl"))
        console.print(f"\n[yellow]📁 Found {len(synthetic_cobol)} synthetic COBOL programs[/yellow]")
        for cobol_file in synthetic_cobol:
            try:
                parser = parser_registry.get_parser_for_file(cobol_file)
                parsed = parser.parse(cobol_file)
                builder.add_document(parsed)
                console.print(f"  ✓ Parsed {cobol_file.name}")
            except Exception as e:
                console.print(f"  ✗ Error parsing {cobol_file.name}: {e}")

    # 3. Parse real JCL jobs
    real_jcl_dir = mainframe_dir / "jcl"
    if real_jcl_dir.exists():
        real_jcl_files = list(real_jcl_dir.glob("*.jcl")) + list(real_jcl_dir.glob("*.JCL"))
        console.print(f"\n[yellow]📁 Found {len(real_jcl_files)} real JCL jobs[/yellow]")
        for jcl_file in real_jcl_files:
            try:
                parser = parser_registry.get_parser_for_file(jcl_file)
                parsed = parser.parse(jcl_file)
                builder.add_document(parsed)
                console.print(f"  ✓ Parsed {jcl_file.name}")
            except Exception as e:
                console.print(f"  ✗ Error parsing {jcl_file.name}: {e}")

    # 4. Parse synthetic JCL jobs
    synthetic_jcl_dir = mainframe_dir / "synthetic" / "jcl"
    if synthetic_jcl_dir.exists():
        synthetic_jcl = list(synthetic_jcl_dir.glob("*.jcl"))
        console.print(f"\n[yellow]📁 Found {len(synthetic_jcl)} synthetic JCL jobs[/yellow]")
        for jcl_file in synthetic_jcl:
            try:
                parser = parser_registry.get_parser_for_file(jcl_file)
                parsed = parser.parse(jcl_file)
                builder.add_document(parsed)
                console.print(f"  ✓ Parsed {jcl_file.name}")
            except Exception as e:
                console.print(f"  ✗ Error parsing {jcl_file.name}: {e}")

    # Get the graph
    graph = builder.get_graph()

    # Display graph statistics
    console.print(f"\n[bold green]✅ Knowledge Graph Built![/bold green]")

    stats_table = Table(title="Graph Statistics", box=box.ROUNDED)
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Count", style="magenta", justify="right")

    stats_table.add_row("Total Nodes", str(graph.number_of_nodes()))
    stats_table.add_row("Total Edges", str(graph.number_of_edges()))

    # Count by node type
    node_types = {}
    for node_id, data in graph.nodes(data=True):
        node_type = data.get("node_type", "unknown")
        node_types[node_type] = node_types.get(node_type, 0) + 1

    for node_type, count in sorted(node_types.items()):
        stats_table.add_row(f"  └─ {node_type}", str(count))

    console.print(stats_table)

    return graph, builder


def visualize_graph_structure(graph: nx.DiGraph):
    """Visualize the high-level structure of the knowledge graph."""
    console.print("\n[bold cyan]🔍 Graph Structure Overview[/bold cyan]\n")

    tree = Tree("📊 Enterprise Knowledge Graph")

    # Group by document type
    from enterprise_assistant.graph.schema import NodeType
    packages = {}
    for node_id, data in graph.nodes(data=True):
        if data.get("node_type") == NodeType.PACKAGE:
            doc_type = data.get("document_type", "unknown")
            if doc_type not in packages:
                packages[doc_type] = []
            packages[doc_type].append(data.get("name", node_id))

    for doc_type, package_list in sorted(packages.items()):
        type_branch = tree.add(f"[yellow]{doc_type}[/yellow] ({len(package_list)} packages)")
        for package_name in package_list[:5]:  # Show first 5
            type_branch.add(f"[green]{package_name}[/green]")
        if len(package_list) > 5:
            type_branch.add(f"[dim]... and {len(package_list) - 5} more[/dim]")

    console.print(tree)


def answer_complex_questions():
    """Use the agent to answer complicated questions about the ETL network."""
    import os
    console.print("\n[bold cyan]🤖 Agent-Powered Analysis Demo[/bold cyan]\n")

    # Check if API keys are available
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))

    if not has_openai and not has_anthropic:
        console.print(Panel(
            "[bold yellow]⚠️  No API keys found[/bold yellow]\n\n"
            "To run the agent demo with real LLM reasoning, set:\n"
            "  export OPENAI_API_KEY=your_key\n"
            "  or\n"
            "  export ANTHROPIC_API_KEY=your_key\n\n"
            "[dim]Showing what questions the agent WOULD answer...[/dim]",
            border_style="yellow",
            box=box.ROUNDED
        ))

        questions = [
            ("What COBOL programs are in the CUSTOMER domain?",
             "The agent would:\n1. Use graph_query tool to find packages with 'CUSTOMER' in name\n2. Filter for COBOL_PROGRAM document type\n3. Return: CUST001, CUST002, CUST003, CUST004, CUST005, CUST006"),

            ("Show me all JCL jobs that run daily and what programs they execute",
             "The agent would:\n1. Use graph_query to find packages with 'DAILY' in name\n2. Filter for MAINFRAME_JCL document type\n3. For each job, find EXEC PGM= programs\n4. Return: DAILYCUS (CUST001-003), DAILYSAL (SALE001-004), DAILYINV (INV001-004), etc."),

            ("If I modify the SALES.INPUT.TRANS dataset, what components would be affected?",
             "The agent would:\n1. Use analyze_impact tool on 'SALES.INPUT.TRANS'\n2. Find all components that READ from this dataset\n3. Return: SALE001, SALE002, DAILYSAL job step 1"),
        ]

        for i, (question, answer) in enumerate(questions, 1):
            console.print(Panel(
                f"[bold]Question {i}:[/bold] {question}\n\n"
                f"[green]{answer}[/green]",
                border_style="cyan",
                box=box.DOUBLE
            ))
            console.print()

        return

    # API key is available - run real agent
    console.print(f"[green]✓ Using {'openai' if has_openai else 'anthropic'} API[/green]\n")

    mainframe_dir = Path(__file__).parent / "sample_mainframe"
    console.print("[dim]Creating agent and loading mainframe documents...[/dim]")
    agent = create_enterprise_agent(
        documents_dir=mainframe_dir,
        model_provider="openai" if has_openai else "anthropic",
    )
    console.print(f"[green]✓ Agent ready with {len(agent.graph.nodes())} nodes in knowledge graph[/green]\n")

    questions = [
        "What COBOL programs are in the CUSTOMER domain?",
        "Show me all JCL jobs that run daily and what programs they execute",
        "If I modify the SALES.INPUT.TRANS dataset, what components would be affected?",
    ]

    for i, question in enumerate(questions, 1):
        console.print("\n" + "═" * 80)
        console.print(Panel(
            f"[bold white]Question {i}:[/bold white] {question}",
            border_style="cyan",
            box=box.DOUBLE,
            padding=(1, 2)
        ))

        step_num = 0

        # Stream agent response with full visibility
        console.print("[dim]Streaming agent response...[/dim]")
        chunk_count = 0
        for chunk in agent.analyze_stream(question, stream_mode="updates"):
            chunk_count += 1
            if chunk_count == 1:
                console.print(f"[dim]Received first chunk: {list(chunk.keys())}[/dim]")

            # Show errors
            if "error" in chunk:
                console.print(Panel(
                    f"[bold red]Error:[/bold red]\n{chunk['error']}",
                    border_style="red",
                    title="Agent Error"
                ))
                break

            if "agent" in chunk:
                agent_data = chunk["agent"]

                if "messages" in agent_data:
                    for msg in agent_data["messages"]:
                        # Show tool calls
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            for tool_call in msg.tool_calls:
                                step_num += 1
                                tool_name = tool_call.get("name", "unknown")
                                tool_args = tool_call.get("args", {})

                                # Special formatting for different tools
                                if tool_name == 'write_todos':
                                    todos = tool_args.get('todos', [])
                                    console.print(Panel(
                                        f"[bold green]📝 Step {step_num}: Planning[/bold green]\n\n"
                                        f"[cyan]Agent is creating a {len(todos)}-step plan...[/cyan]",
                                        border_style="green",
                                        box=box.ROUNDED
                                    ))
                                elif tool_name == 'graph_query':
                                    query = tool_args.get('query', 'N/A')
                                    console.print(Panel(
                                        f"[bold blue]🔍 Step {step_num}: Graph Query[/bold blue]\n\n"
                                        f"[yellow]Query:[/yellow] {query[:100]}...",
                                        border_style="blue",
                                        box=box.ROUNDED
                                    ))
                                elif tool_name == 'trace_lineage':
                                    entity = tool_args.get('entity_name', 'N/A')
                                    direction = tool_args.get('direction', 'both')
                                    console.print(Panel(
                                        f"[bold magenta]📈 Step {step_num}: Lineage Tracing[/bold magenta]\n\n"
                                        f"[yellow]Entity:[/yellow] {entity}\n"
                                        f"[yellow]Direction:[/yellow] {direction}",
                                        border_style="magenta",
                                        box=box.ROUNDED
                                    ))
                                elif tool_name == 'analyze_impact':
                                    entity = tool_args.get('entity_name', 'N/A')
                                    console.print(Panel(
                                        f"[bold red]⚠️  Step {step_num}: Impact Analysis[/bold red]\n\n"
                                        f"[yellow]Analyzing impact of:[/yellow] {entity}",
                                        border_style="red",
                                        box=box.ROUNDED
                                    ))
                                else:
                                    console.print(Panel(
                                        f"[bold cyan]🔧 Step {step_num}: {tool_name}[/bold cyan]",
                                        border_style="cyan",
                                        box=box.ROUNDED
                                    ))

                        # Show agent's final response
                        if hasattr(msg, 'content') and msg.content and not hasattr(msg, 'tool_calls'):
                            console.print(Panel(
                                f"[bold green]✨ Agent Response:[/bold green]\n\n{msg.content}",
                                border_style="green",
                                box=box.DOUBLE,
                                padding=(1, 2)
                            ))

            # Show tool outputs in proper panels
            if "tools" in chunk:
                tools_data = chunk["tools"]
                if "messages" in tools_data:
                    for msg in tools_data["messages"]:
                        if hasattr(msg, 'content'):
                            content = str(msg.content)

                            # Determine if error or success
                            is_error = content.startswith("Error") or "error" in content.lower()[:50]

                            # Truncate very long output but keep structure
                            if len(content) > 500:
                                lines = content.split('\n')
                                if len(lines) > 20:
                                    content = '\n'.join(lines[:20]) + f"\n\n[dim]... ({len(lines) - 20} more lines)[/dim]"
                                else:
                                    content = content[:500] + "\n\n[dim]... (truncated)[/dim]"

                            # Format in panel
                            if is_error:
                                console.print(Panel(
                                    f"[yellow]{content}[/yellow]",
                                    title="⚠️  Tool Result",
                                    border_style="yellow",
                                    box=box.ROUNDED
                                ))
                            else:
                                console.print(Panel(
                                    f"[green]{content}[/green]",
                                    title="✅ Tool Result",
                                    border_style="green",
                                    box=box.ROUNDED
                                ))

        console.print("\n")


def demonstrate_lineage_tracing(graph: nx.DiGraph):
    """Demonstrate data lineage tracing through the ETL pipeline."""
    console.print("\n[bold cyan]📈 Data Lineage Tracing[/bold cyan]\n")

    from enterprise_assistant.graph.queries import GraphQueries

    queries = GraphQueries(graph)

    # Find a data entity to trace
    from enterprise_assistant.graph.schema import NodeType
    tables = queries.find_nodes_by_type(NodeType.TABLE)

    if tables:
        # Pick first table
        table_id, table_data = tables[0]
        table_name = table_data.get("name", table_id)

        console.print(f"[yellow]Example table found:[/yellow] [bold]{table_name}[/bold]\n")

        # Show connected nodes
        if graph.has_node(table_id):
            predecessors = list(graph.predecessors(table_id))
            successors = list(graph.successors(table_id))

            console.print(f"[green]🔼 Connected predecessors:[/green] {len(predecessors)}")
            for pred_id in predecessors[:5]:
                pred_data = graph.nodes[pred_id]
                console.print(f"  ← {pred_data.get('name', pred_id)} ({pred_data.get('type', 'unknown')})")

            console.print(f"\n[green]🔽 Connected successors:[/green] {len(successors)}")
            for succ_id in successors[:5]:
                succ_data = graph.nodes[succ_id]
                console.print(f"  → {succ_data.get('name', succ_id)} ({succ_data.get('type', 'unknown')})")


def demonstrate_impact_analysis(graph: nx.DiGraph):
    """Demonstrate impact analysis for a component change."""
    console.print("\n[bold cyan]⚠️  Impact Analysis[/bold cyan]\n")

    from enterprise_assistant.graph.queries import GraphQueries

    queries = GraphQueries(graph)

    # Find components
    from enterprise_assistant.graph.schema import NodeType
    tasks = queries.find_nodes_by_type(NodeType.TASK)

    if tasks:
        # Pick first task
        task_id, task_data = tasks[0]
        task_name = task_data.get("name", task_id)

        console.print(f"[yellow]Example task found:[/yellow] [bold]{task_name}[/bold]\n")

        # Get direct graph connections
        if graph.has_node(task_id):
            predecessors = list(graph.predecessors(task_id))
            successors = list(graph.successors(task_id))

            console.print(f"[red]⬅️  Direct predecessors:[/red] {len(predecessors)}")
            for pred_id in predecessors[:5]:
                pred_data = graph.nodes[pred_id]
                console.print(f"  • {pred_data.get('name', pred_id)} ({pred_data.get('type', 'unknown')})")

            console.print(f"\n[red]➡️  Direct successors:[/red] {len(successors)}")
            for succ_id in successors[:5]:
                succ_data = graph.nodes[succ_id]
                console.print(f"  • {succ_data.get('name', succ_id)} ({succ_data.get('type', 'unknown')})")

            if len(predecessors) + len(successors) > 0:
                console.print(f"\n[bold red]⚠️  TOTAL DIRECT IMPACT: {len(predecessors) + len(successors)} component(s)[/bold red]")


def main():
    """Run the complete complex ETL demo."""
    console.print(Panel.fit(
        "[bold cyan]Complex ETL Network Demo[/bold cyan]\n"
        "[yellow]COBOL + JCL + SQLite Integration[/yellow]",
        border_style="cyan",
        box=box.DOUBLE
    ))

    # Step 1: Parse the entire network
    graph, builder = parse_etl_network()

    # Step 2: Visualize structure
    visualize_graph_structure(graph)

    # Step 3: Let the agent answer complex questions using tools!
    answer_complex_questions()

    console.print("\n[bold green]✅ Demo Complete![/bold green]\n")
    console.print("[dim]The agent used graph tools to analyze the mainframe ETL network.[/dim]\n")


if __name__ == "__main__":
    main()
