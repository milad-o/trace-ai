"""Tests for knowledge graph operations."""

from pathlib import Path

import networkx as nx
import pytest

from traceai.graph.builder import KnowledgeGraphBuilder, build_graph_from_documents
from traceai.graph.queries import GraphQueries
from traceai.graph.schema import EdgeType, NodeType
from traceai.graph.storage import GraphStorage
from traceai.parsers.ssis_parser import parse_ssis


@pytest.fixture
def sample_graph(tmp_path: Path) -> nx.DiGraph:
    """Create a sample graph from test SSIS packages."""
    # Parse the CustomerETL sample package
    package_path = Path("examples/sample_packages/CustomerETL.dtsx")
    if not package_path.exists():
        pytest.skip("Sample package not found")

    parsed = parse_ssis(package_path)
    graph = build_graph_from_documents([parsed])
    return graph


def test_graph_builder_initialization() -> None:
    """Test graph builder initialization."""
    builder = KnowledgeGraphBuilder()
    assert builder.graph is not None
    assert isinstance(builder.graph, nx.DiGraph)
    assert builder.graph.number_of_nodes() == 0


def test_build_graph_from_package(sample_graph: nx.DiGraph) -> None:
    """Test building graph from parsed package."""
    assert sample_graph.number_of_nodes() > 0
    assert sample_graph.number_of_edges() > 0

    # Check that we have different node types
    node_types = set()
    for _, data in sample_graph.nodes(data=True):
        node_types.add(data.get("node_type"))

    assert NodeType.PACKAGE in node_types
    assert NodeType.TASK in node_types
    assert NodeType.CONNECTION in node_types


def test_find_nodes_by_type(sample_graph: nx.DiGraph) -> None:
    """Test finding nodes by type."""
    queries = GraphQueries(sample_graph)

    packages = queries.find_nodes_by_type(NodeType.PACKAGE)
    assert len(packages) == 1  # One package in sample

    tasks = queries.find_nodes_by_type(NodeType.TASK)
    assert len(tasks) > 0  # Should have multiple tasks

    connections = queries.find_nodes_by_type(NodeType.CONNECTION)
    assert len(connections) > 0  # Should have connections


def test_find_node_by_name(sample_graph: nx.DiGraph) -> None:
    """Test finding nodes by exact name."""
    queries = GraphQueries(sample_graph)

    # Find package by name
    results = queries.find_node_by_name("CustomerETL", NodeType.PACKAGE)
    assert len(results) == 1
    node_id, node_data = results[0]
    assert node_data["name"] == "CustomerETL"


def test_search_nodes(sample_graph: nx.DiGraph) -> None:
    """Test searching nodes by substring."""
    queries = GraphQueries(sample_graph)

    # Search for tasks with "Customer" in name
    results = queries.search_nodes("Customer")
    assert len(results) > 0

    # Search should be case-insensitive
    results_lower = queries.search_nodes("customer")
    assert len(results_lower) > 0


def test_get_package_contents(sample_graph: nx.DiGraph) -> None:
    """Test getting package contents."""
    queries = GraphQueries(sample_graph)

    # Find package node
    packages = queries.find_nodes_by_type(NodeType.PACKAGE)
    package_id, _ = packages[0]

    # Get contents
    contents = queries.get_package_contents(package_id)

    assert "connections" in contents
    assert "variables" in contents
    assert "tasks" in contents

    assert len(contents["tasks"]) > 0  # Should have tasks
    assert len(contents["connections"]) > 0  # Should have connections
    assert len(contents["variables"]) > 0  # Should have variables


def test_task_dependencies(sample_graph: nx.DiGraph) -> None:
    """Test finding task dependencies."""
    queries = GraphQueries(sample_graph)

    # Find tasks
    tasks = queries.find_nodes_by_type(NodeType.TASK)
    assert len(tasks) > 1  # Need at least 2 tasks for dependencies

    # Get dependencies for a task (should have predecessors or successors)
    task_id, _ = tasks[1]  # Use second task (likely has dependencies)
    deps = queries.get_task_dependencies(task_id)

    assert "predecessors" in deps
    assert "successors" in deps


def test_table_task_relationships(sample_graph: nx.DiGraph) -> None:
    """Test finding tasks related to tables."""
    queries = GraphQueries(sample_graph)

    # Find table nodes
    tables = queries.find_nodes_by_type(NodeType.TABLE)

    if len(tables) > 0:
        # Test finding tasks that read/write to tables
        table_id, table_data = tables[0]
        table_name = table_data["name"]

        readers = queries.find_tasks_reading_from_table(table_name)
        writers = queries.find_tasks_writing_to_table(table_name)

        # At least one should have tasks
        assert len(readers) > 0 or len(writers) > 0


def test_data_lineage(sample_graph: nx.DiGraph) -> None:
    """Test data lineage tracing."""
    queries = GraphQueries(sample_graph)

    # Find a table
    tables = queries.find_nodes_by_type(NodeType.TABLE)

    if len(tables) > 0:
        table_id, table_data = tables[0]
        table_name = table_data["name"]

        # Trace lineage
        lineage = queries.trace_data_lineage(table_name, direction="both")

        assert "upstream" in lineage
        assert "downstream" in lineage
        assert isinstance(lineage["upstream"], list)
        assert isinstance(lineage["downstream"], list)


def test_graph_stats(sample_graph: nx.DiGraph) -> None:
    """Test graph statistics."""
    queries = GraphQueries(sample_graph)

    stats = queries.get_graph_stats()

    assert stats["total_nodes"] > 0
    assert stats["total_edges"] > 0
    assert stats["is_directed"] is True
    assert "package_count" in stats
    assert "task_count" in stats


def test_graph_storage_pickle(tmp_path: Path, sample_graph: nx.DiGraph) -> None:
    """Test graph storage and loading (pickle format)."""
    storage_path = tmp_path / "test_graph.pkl"
    storage = GraphStorage(storage_path)

    # Save graph
    storage.save_pickle(sample_graph)
    assert storage_path.exists()

    # Load graph
    loaded_graph = storage.load_pickle()

    assert loaded_graph.number_of_nodes() == sample_graph.number_of_nodes()
    assert loaded_graph.number_of_edges() == sample_graph.number_of_edges()


def test_graph_storage_json(tmp_path: Path, sample_graph: nx.DiGraph) -> None:
    """Test graph storage in JSON format."""
    json_path = tmp_path / "test_graph.json"
    storage = GraphStorage()

    # Save to JSON
    storage.save_json(sample_graph, json_path)
    assert json_path.exists()

    # Load from JSON
    loaded_graph = storage.load_json(json_path)

    assert loaded_graph.number_of_nodes() == sample_graph.number_of_nodes()
    assert loaded_graph.number_of_edges() == sample_graph.number_of_edges()


def test_graph_export_graphml(tmp_path: Path, sample_graph: nx.DiGraph) -> None:
    """Test exporting graph to GraphML format."""
    graphml_path = tmp_path / "test_graph.graphml"
    storage = GraphStorage()

    storage.export_graphml(sample_graph, graphml_path)
    assert graphml_path.exists()


def test_storage_info(tmp_path: Path) -> None:
    """Test getting storage information."""
    storage_path = tmp_path / "info_test.pkl"
    storage = GraphStorage(storage_path)

    # Before saving
    info = storage.get_storage_info()
    assert info["exists"] is False

    # After saving
    empty_graph = nx.DiGraph()
    storage.save_pickle(empty_graph)

    info = storage.get_storage_info()
    assert info["exists"] is True
    assert "size_bytes" in info
    assert "size_mb" in info


def test_node_importance(sample_graph: nx.DiGraph) -> None:
    """Test calculating node importance."""
    queries = GraphQueries(sample_graph)

    # Get a task node
    tasks = queries.find_nodes_by_type(NodeType.TASK)
    if len(tasks) > 0:
        task_id, _ = tasks[0]

        importance = queries.calculate_node_importance(task_id)

        assert "in_degree" in importance
        assert "out_degree" in importance
        assert "total_degree" in importance
        assert importance["total_degree"] >= 0
