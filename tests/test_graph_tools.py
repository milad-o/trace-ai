"""Tests for LangChain graph tools."""

from pathlib import Path

import pytest

from enterprise_assistant.graph.builder import build_graph_from_documents
from enterprise_assistant.parsers.ssis_parser import parse_ssis
from enterprise_assistant.tools.graph_tools import (
    DependencySearchTool,
    GraphQueryTool,
    ImpactAnalysisTool,
    LineageTracerTool,
    create_graph_tools,
)


@pytest.fixture
def sample_graph():
    """Create a sample graph from test SSIS packages."""
    package_path = Path("examples/sample_packages/CustomerETL.dtsx")
    if not package_path.exists():
        pytest.skip("Sample package not found")

    parsed = parse_ssis(package_path)
    graph = build_graph_from_documents([parsed])
    return graph


def test_create_graph_tools(sample_graph):
    """Test creating all graph tools."""
    tools = create_graph_tools(sample_graph)

    assert len(tools) == 4
    assert any(isinstance(tool, GraphQueryTool) for tool in tools)
    assert any(isinstance(tool, LineageTracerTool) for tool in tools)
    assert any(isinstance(tool, ImpactAnalysisTool) for tool in tools)
    assert any(isinstance(tool, DependencySearchTool) for tool in tools)


def test_graph_query_tool_find_all_packages(sample_graph):
    """Test GraphQueryTool finding all packages."""
    tool = GraphQueryTool(graph=sample_graph)

    result = tool._run(node_type="package")

    assert "Found" in result
    assert "package" in result.lower()
    assert "CustomerETL" in result


def test_graph_query_tool_find_tasks(sample_graph):
    """Test GraphQueryTool finding tasks."""
    tool = GraphQueryTool(graph=sample_graph)

    result = tool._run(node_type="task")

    assert "Found" in result
    assert "task" in result.lower()


def test_graph_query_tool_with_name_filter(sample_graph):
    """Test GraphQueryTool with name pattern filtering."""
    tool = GraphQueryTool(graph=sample_graph)

    # Find tasks containing "Truncate"
    result = tool._run(node_type="task", name_pattern="Truncate")

    # Should find the truncate task
    assert "Truncate" in result or "No task nodes found" in result


def test_graph_query_tool_invalid_type(sample_graph):
    """Test GraphQueryTool with invalid node type."""
    tool = GraphQueryTool(graph=sample_graph)

    result = tool._run(node_type="invalid_type")

    assert "Error" in result
    assert "Invalid node_type" in result


def test_graph_query_tool_find_tables(sample_graph):
    """Test GraphQueryTool finding tables."""
    tool = GraphQueryTool(graph=sample_graph)

    result = tool._run(node_type="table")

    # Should find tables extracted from SQL statements
    assert ("Found" in result and "table" in result.lower()) or "No table nodes found" in result


def test_lineage_tracer_tool_upstream(sample_graph):
    """Test LineageTracerTool tracing upstream."""
    tool = LineageTracerTool(graph=sample_graph)

    # Try to trace upstream for a table that exists
    result = tool._run(entity_name="Customers", direction="upstream")

    # Should either find lineage or indicate entity not found
    assert "Data Lineage" in result or "not found" in result


def test_lineage_tracer_tool_downstream(sample_graph):
    """Test LineageTracerTool tracing downstream."""
    tool = LineageTracerTool(graph=sample_graph)

    result = tool._run(entity_name="Customers", direction="downstream")

    assert "Data Lineage" in result or "not found" in result


def test_lineage_tracer_tool_both_directions(sample_graph):
    """Test LineageTracerTool tracing both directions."""
    tool = LineageTracerTool(graph=sample_graph)

    result = tool._run(entity_name="Customers", direction="both")

    assert "Data Lineage" in result or "not found" in result
    # If found, should have both upstream and downstream sections
    if "Data Lineage for:" in result:
        assert "UPSTREAM" in result
        assert "DOWNSTREAM" in result


def test_lineage_tracer_tool_invalid_direction(sample_graph):
    """Test LineageTracerTool with invalid direction."""
    tool = LineageTracerTool(graph=sample_graph)

    result = tool._run(entity_name="Customers", direction="invalid")

    assert "Error" in result
    assert "direction must be" in result


def test_lineage_tracer_tool_not_found(sample_graph):
    """Test LineageTracerTool with non-existent entity."""
    tool = LineageTracerTool(graph=sample_graph)

    result = tool._run(entity_name="NonExistentTable", direction="both")

    assert "not found" in result


def test_impact_analysis_tool_readers(sample_graph):
    """Test ImpactAnalysisTool finding readers."""
    tool = ImpactAnalysisTool(graph=sample_graph)

    result = tool._run(entity_name="Customers", analysis_type="readers")

    # Should either show impact or indicate entity not found
    assert "Impact Analysis" in result or "not found" in result
    if "Impact Analysis for:" in result:
        assert "READERS" in result


def test_impact_analysis_tool_writers(sample_graph):
    """Test ImpactAnalysisTool finding writers."""
    tool = ImpactAnalysisTool(graph=sample_graph)

    result = tool._run(entity_name="Customers", analysis_type="writers")

    assert "Impact Analysis" in result or "not found" in result
    if "Impact Analysis for:" in result:
        assert "WRITERS" in result


def test_impact_analysis_tool_full(sample_graph):
    """Test ImpactAnalysisTool full analysis."""
    tool = ImpactAnalysisTool(graph=sample_graph)

    result = tool._run(entity_name="Customers", analysis_type="full")

    assert "Impact Analysis" in result or "not found" in result
    if "Impact Analysis for:" in result:
        assert "READERS" in result
        assert "WRITERS" in result
        assert "TOTAL IMPACT" in result


def test_impact_analysis_tool_invalid_type(sample_graph):
    """Test ImpactAnalysisTool with invalid analysis type."""
    tool = ImpactAnalysisTool(graph=sample_graph)

    result = tool._run(entity_name="Customers", analysis_type="invalid")

    assert "Error" in result
    assert "analysis_type must be" in result


def test_dependency_search_tool_predecessors(sample_graph):
    """Test DependencySearchTool finding predecessors."""
    tool = DependencySearchTool(graph=sample_graph)

    # Try with a task name
    result = tool._run(component_name="Truncate", direction="predecessors")

    # Should either find dependencies or indicate component not found
    assert "Dependencies" in result or "not found" in result


def test_dependency_search_tool_successors(sample_graph):
    """Test DependencySearchTool finding successors."""
    tool = DependencySearchTool(graph=sample_graph)

    result = tool._run(component_name="Truncate", direction="successors")

    assert "Dependencies" in result or "not found" in result


def test_dependency_search_tool_both(sample_graph):
    """Test DependencySearchTool finding both directions."""
    tool = DependencySearchTool(graph=sample_graph)

    result = tool._run(component_name="Truncate", direction="both")

    assert "Dependencies" in result or "not found" in result
    if "Dependencies for:" in result:
        assert "PREDECESSORS" in result
        assert "SUCCESSORS" in result


def test_dependency_search_tool_invalid_direction(sample_graph):
    """Test DependencySearchTool with invalid direction."""
    tool = DependencySearchTool(graph=sample_graph)

    result = tool._run(component_name="Truncate", direction="invalid")

    assert "Error" in result
    assert "direction must be" in result


def test_tool_descriptions_are_helpful():
    """Test that all tools have helpful descriptions."""
    from enterprise_assistant.tools import (
        DependencySearchTool,
        GraphQueryTool,
        ImpactAnalysisTool,
        LineageTracerTool,
    )

    # Create dummy graph for testing descriptions
    import networkx as nx

    dummy_graph = nx.DiGraph()

    tools = [
        GraphQueryTool(graph=dummy_graph),
        LineageTracerTool(graph=dummy_graph),
        ImpactAnalysisTool(graph=dummy_graph),
        DependencySearchTool(graph=dummy_graph),
    ]

    for tool in tools:
        # Each tool should have a name and description
        assert tool.name
        assert tool.description
        assert len(tool.description) > 50  # Should be reasonably detailed


def test_tool_schemas_are_valid():
    """Test that all tools have valid Pydantic schemas."""
    from enterprise_assistant.tools.graph_tools import (
        DependencySearchInput,
        GraphQueryInput,
        ImpactAnalysisInput,
        LineageTraceInput,
    )

    # Test GraphQueryInput
    query_input = GraphQueryInput(node_type="table", name_pattern="Customer")
    assert query_input.node_type == "table"
    assert query_input.name_pattern == "Customer"

    # Test LineageTraceInput
    lineage_input = LineageTraceInput(entity_name="Customers", direction="upstream")
    assert lineage_input.entity_name == "Customers"
    assert lineage_input.direction == "upstream"
    assert lineage_input.max_depth == 10  # Default value

    # Test ImpactAnalysisInput
    impact_input = ImpactAnalysisInput(entity_name="Sales", analysis_type="readers")
    assert impact_input.entity_name == "Sales"
    assert impact_input.analysis_type == "readers"

    # Test DependencySearchInput
    dep_input = DependencySearchInput(component_name="ETL Task", direction="both")
    assert dep_input.component_name == "ETL Task"
    assert dep_input.direction == "both"
