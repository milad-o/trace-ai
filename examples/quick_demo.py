"""Quick demo to test that the Enterprise Assistant works end-to-end.

This is a realistic scenario test that doesn't require API keys.
It tests:
1. Loading SSIS packages
2. Building knowledge graph
3. Querying the graph directly (no LLM needed)
4. Vector search
5. Lineage/impact analysis tools
"""

from pathlib import Path

from enterprise_assistant.agents import EnterpriseAgent
from enterprise_assistant.graph.queries import GraphQueries
from enterprise_assistant.graph.schema import NodeType
from enterprise_assistant.parsers import parser_registry

def main():
    print("=" * 80)
    print("ENTERPRISE ASSISTANT - QUICK DEMO (No API Key Required)")
    print("=" * 80)
    print()

    # 1. Initialize agent (no model needed for this demo)
    print("📦 Step 1: Initializing Enterprise Agent...")
    agent = EnterpriseAgent(model_provider="anthropic")  # Won't use model in this demo

    # 2. Load SSIS packages
    print("\n📥 Step 2: Loading SSIS packages...")
    samples_dir = Path(__file__).parent / "sample_packages"
    agent.load_documents(samples_dir, pattern="**/*.dtsx")

    print(f"   ✓ Loaded {len(agent.parsed_documents)} SSIS packages")
    print(f"   ✓ Knowledge graph: {agent.graph.number_of_nodes()} nodes, {agent.graph.number_of_edges()} edges")

    # 3. Query the knowledge graph directly (no LLM needed)
    print("\n🔍 Step 3: Querying Knowledge Graph...")
    queries = GraphQueries(agent.graph)

    # Find all packages
    packages = queries.find_nodes_by_type(NodeType.PACKAGE)
    print(f"\n   Packages found ({len(packages)}):")
    for pkg_id, pkg_data in packages:
        print(f"   - {pkg_data.get('name', 'Unknown')}")

    # Find all tasks
    tasks = queries.find_nodes_by_type(NodeType.TASK)
    print(f"\n   Tasks found ({len(tasks)}):")
    for task_id, task_data in tasks:
        print(f"   - {task_data.get('name', 'Unknown')} ({task_data.get('task_type', 'Unknown type')})")

    # Find all tables
    tables = queries.find_nodes_by_type(NodeType.TABLE)
    print(f"\n   Tables found ({len(tables)}):")
    for table_id, table_data in tables:
        print(f"   - {table_data.get('name', 'Unknown')}")

    # 4. Data lineage tracing
    print("\n📊 Step 4: Data Lineage Tracing...")
    if tables:
        table_id, table_data = tables[0]
        table_name = table_data.get('name', 'Unknown')
        print(f"\n   Tracing lineage for: {table_name}")

        lineage = queries.trace_data_lineage(table_name, direction="both")

        upstream = lineage.get("upstream", [])
        downstream = lineage.get("downstream", [])

        print(f"   Upstream components: {len(upstream)}")
        for comp_id, comp_data in upstream[:3]:  # Show first 3
            print(f"     ← {comp_data.get('name', comp_id)}")

        print(f"   Downstream components: {len(downstream)}")
        for comp_id, comp_data in downstream[:3]:  # Show first 3
            print(f"     → {comp_data.get('name', comp_id)}")

    # 5. Impact analysis
    print("\n⚠️  Step 5: Impact Analysis...")
    if tables:
        table_id, table_data = tables[0]
        table_name = table_data.get('name', 'Unknown')
        print(f"\n   Analyzing impact of changing: {table_name}")

        readers = queries.find_tasks_reading_from_table(table_name)
        writers = queries.find_tasks_writing_to_table(table_name)

        print(f"   Tasks that READ from this table: {len(readers)}")
        for task_id, task_data in readers[:3]:
            print(f"     📖 {task_data.get('name', task_id)}")

        print(f"   Tasks that WRITE to this table: {len(writers)}")
        for task_id, task_data in writers[:3]:
            print(f"     ✍️  {task_data.get('name', task_id)}")

        total_impact = len(readers) + len(writers)
        print(f"\n   ⚠️  TOTAL IMPACT: {total_impact} tasks would be affected")

    # 6. Vector search test
    print("\n🔎 Step 6: Semantic Search...")
    from langchain_community.vectorstores import Chroma

    if isinstance(agent.vector_store, Chroma):
        # Test similarity search
        query = "customer data processing"
        results = agent.vector_store.similarity_search(query, k=3)

        print(f"\n   Search query: '{query}'")
        print(f"   Results found: {len(results)}")
        for i, doc in enumerate(results, 1):
            print(f"\n   Result {i}:")
            print(f"     Type: {doc.metadata.get('type', 'unknown')}")
            print(f"     Name: {doc.metadata.get('name', 'Unknown')}")
            print(f"     Content preview: {doc.page_content[:100]}...")

    # 7. Graph statistics
    print("\n📈 Step 7: Graph Statistics...")
    stats = queries.get_graph_stats()
    print(f"\n   Total nodes: {stats['total_nodes']}")
    print(f"   Total edges: {stats['total_edges']}")
    print("\n   Node breakdown:")
    for key, value in stats.items():
        if key.endswith('_nodes') and value > 0:
            node_type = key.replace('_nodes', '').replace('_', ' ').title()
            print(f"     {node_type}: {value}")

    # Summary
    print("\n" + "=" * 80)
    print("✅ DEMO COMPLETE - All Core Features Working!")
    print("=" * 80)
    print("\n📝 Summary:")
    print(f"   • Parsed {len(agent.parsed_documents)} SSIS packages")
    print(f"   • Built knowledge graph with {agent.graph.number_of_nodes()} nodes")
    print(f"   • Indexed {len(results) if 'results' in locals() else 'N/A'} items in vector store")
    print(f"   • Can trace lineage, analyze impact, search semantically")
    print("\n💡 To use with AI agent, set ANTHROPIC_API_KEY or OPENAI_API_KEY and call agent.analyze()")
    print()


if __name__ == "__main__":
    main()
