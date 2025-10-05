"""Tests for graph visualization tools."""

from pathlib import Path

import networkx as nx
import pytest

from enterprise_assistant.graph.builder import build_graph_from_documents
from enterprise_assistant.parsers import parse_ssis
from enterprise_assistant.tools.visualization_tools import create_graph_visualization_tool


@pytest.fixture
def sample_graph():
    """Create a sample graph from test packages."""
    packages_dir = Path("examples/sample_packages")
    docs = [parse_ssis(f) for f in packages_dir.glob("*.dtsx")]
    graph = build_graph_from_documents(docs)
    return graph


def test_create_visualization_tool(sample_graph):
    """Test that visualization tool can be created."""
    tool = create_graph_visualization_tool(sample_graph)

    assert tool is not None
    assert tool.name == "create_graph_visualization"
    assert "visualization" in tool.description.lower()
    assert callable(tool._run)


def test_visualization_svg_output(sample_graph, tmp_path):
    """Test SVG visualization generation."""
    tool = create_graph_visualization_tool(sample_graph)

    output_path = tmp_path / "test.svg"
    result = tool._run(
        package_name="CustomerETL",
        output_format="svg",
        layout="hierarchical",
        output_path=str(output_path),
    )

    assert "Successfully created" in result
    assert output_path.exists()
    assert output_path.stat().st_size > 0

    # Verify it's a valid SVG
    content = output_path.read_text()
    assert "<svg" in content.lower()


def test_visualization_png_output(sample_graph, tmp_path):
    """Test PNG visualization generation."""
    tool = create_graph_visualization_tool(sample_graph)

    output_path = tmp_path / "test.png"
    result = tool._run(
        package_name="CustomerETL",
        output_format="png",
        layout="spring",
        output_path=str(output_path),
    )

    assert "Successfully created" in result
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_visualization_full_graph(sample_graph, tmp_path):
    """Test visualization of full graph (no package filter)."""
    tool = create_graph_visualization_tool(sample_graph)

    output_path = tmp_path / "full_graph.svg"
    result = tool._run(
        package_name=None,  # Full graph
        output_format="svg",
        layout="circular",
        output_path=str(output_path),
    )

    assert "Successfully created" in result
    assert output_path.exists()
    assert "35" in result  # Should mention total nodes


def test_visualization_invalid_package(sample_graph, tmp_path):
    """Test visualization with non-existent package."""
    tool = create_graph_visualization_tool(sample_graph)

    result = tool._run(
        package_name="NonExistentPackage",
        output_format="svg",
        output_path=str(tmp_path / "test.svg"),
    )

    assert "Error" in result or "not found" in result.lower()


def test_visualization_different_layouts(sample_graph, tmp_path):
    """Test different layout algorithms."""
    tool = create_graph_visualization_tool(sample_graph)

    layouts = ["hierarchical", "spring", "circular", "kamada_kawai"]

    for layout in layouts:
        output_path = tmp_path / f"test_{layout}.svg"
        result = tool._run(
            package_name="CustomerETL",
            output_format="svg",
            layout=layout,
            output_path=str(output_path),
        )

        assert "Successfully created" in result, f"Failed for layout: {layout}"
        assert output_path.exists()


def test_visualization_default_output_path(sample_graph):
    """Test visualization with default output path."""
    tool = create_graph_visualization_tool(sample_graph)

    # Clear visualizations directory first
    viz_dir = Path("data/visualizations")
    if viz_dir.exists():
        for f in viz_dir.glob("*"):
            f.unlink()

    result = tool._run(
        package_name="SalesAggregation",
        output_format="svg",
    )

    assert "Successfully created" in result
    assert "data/visualizations" in result

    # Check file was created
    expected_file = viz_dir / "SalesAggregation.svg"
    assert expected_file.exists()


def test_visualization_with_edge_labels(sample_graph, tmp_path):
    """Test visualization with edge labels enabled."""
    tool = create_graph_visualization_tool(sample_graph)

    output_path = tmp_path / "test_edge_labels.svg"
    result = tool._run(
        package_name="CustomerETL",
        output_format="svg",
        show_edge_labels=True,
        output_path=str(output_path),
    )

    assert "Successfully created" in result
    assert output_path.exists()


def test_visualization_custom_node_size(sample_graph, tmp_path):
    """Test visualization with custom node size and font."""
    tool = create_graph_visualization_tool(sample_graph)

    output_path = tmp_path / "test_custom.svg"
    result = tool._run(
        package_name="CustomerETL",
        output_format="svg",
        node_size=5000,
        font_size=12,
        output_path=str(output_path),
    )

    assert "Successfully created" in result
    assert output_path.exists()
