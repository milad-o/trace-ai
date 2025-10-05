"""Tools for generating graph visualizations (SVG, PNG, PDF)."""

import io
from pathlib import Path
from typing import Any, Literal

import matplotlib
# Use non-GUI backend to avoid threading issues
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from traceai.graph.schema import EdgeType, NodeType
from traceai.logger import logger


class GraphVisualizationInput(BaseModel):
    """Input schema for graph visualization tool."""

    package_name: str | None = Field(
        default=None, description="Name of specific package to visualize (if None, visualize entire graph)"
    )
    output_format: Literal["svg", "png", "pdf"] = Field(
        default="svg", description="Output format: 'svg' (scalable), 'png' (raster), or 'pdf'"
    )
    layout: Literal["hierarchical", "spring", "circular", "kamada_kawai"] = Field(
        default="hierarchical", description="Layout algorithm: hierarchical (tree), spring (force), circular, kamada_kawai"
    )
    output_path: str | None = Field(
        default=None, description="Custom output path (if None, saves to data/visualizations/)"
    )
    show_labels: bool = Field(default=True, description="Show node labels")
    show_edge_labels: bool = Field(default=False, description="Show edge labels (relationship types)")
    node_size: int = Field(default=3000, description="Size of nodes (default: 3000)")
    font_size: int = Field(default=10, description="Font size for labels (default: 10)")


def create_graph_visualization_tool(graph: nx.DiGraph) -> BaseTool:
    """
    Create a graph visualization tool bound to a specific graph.

    Args:
        graph: The NetworkX graph to visualize

    Returns:
        LangChain tool for creating visualizations
    """

    class GraphVisualizationTool(BaseTool):
        name: str = "create_graph_visualization"
        description: str = """Generate a visual diagram of the knowledge graph structure.

Use this tool to create SVG, PNG, or PDF visualizations showing:
- Package hierarchies
- Task dependencies and execution order
- Data flow between tables
- Connections and relationships

Parameters:
- package_name: Focus on specific package (or None for full graph)
- output_format: 'svg' (best for web), 'png' (images), 'pdf' (documents)
- layout: 'hierarchical' (tree-like), 'spring' (organic), 'circular', 'kamada_kawai'
- show_edge_labels: Show relationship types on edges

Returns the file path to the generated visualization."""

        args_schema: type[BaseModel] = GraphVisualizationInput

        def _run(
            self,
            package_name: str | None = None,
            output_format: str = "svg",
            layout: str = "hierarchical",
            output_path: str | None = None,
            show_labels: bool = True,
            show_edge_labels: bool = False,
            node_size: int = 3000,
            font_size: int = 10,
        ) -> str:
            """Generate graph visualization."""
            try:
                # Filter graph if package specified
                if package_name:
                    subgraph = _extract_package_subgraph(graph, package_name)
                    if subgraph.number_of_nodes() == 0:
                        return f"Error: Package '{package_name}' not found in graph"
                    viz_graph = subgraph
                    title = f"Package: {package_name}"
                else:
                    viz_graph = graph
                    title = "Enterprise Knowledge Graph"

                # Determine output path
                if output_path:
                    out_path = Path(output_path)
                else:
                    vis_dir = Path("data/visualizations")
                    vis_dir.mkdir(parents=True, exist_ok=True)
                    filename = f"{package_name or 'full_graph'}.{output_format}"
                    out_path = vis_dir / filename

                # Generate visualization
                _create_visualization(
                    viz_graph,
                    out_path,
                    title=title,
                    layout=layout,
                    show_labels=show_labels,
                    show_edge_labels=show_edge_labels,
                    node_size=node_size,
                    font_size=font_size,
                )

                logger.info(f"Generated {output_format.upper()} visualization: {out_path}")

                return f"Successfully created visualization at: {out_path}\n" f"Format: {output_format.upper()}\n" f"Nodes: {viz_graph.number_of_nodes()}\n" f"Edges: {viz_graph.number_of_edges()}\n"

            except Exception as e:
                logger.error(f"Error creating visualization: {e}")
                return f"Error creating visualization: {str(e)}"

    return GraphVisualizationTool()


def _extract_package_subgraph(graph: nx.DiGraph, package_name: str) -> nx.DiGraph:
    """Extract subgraph for a specific package and its contents."""
    # Find the package node
    package_node = None
    for node_id, data in graph.nodes(data=True):
        if data.get("node_type") == NodeType.PACKAGE and data.get("name", "").lower() == package_name.lower():
            package_node = node_id
            break

    if not package_node:
        return nx.DiGraph()

    # Get all nodes connected to this package (descendants)
    # Include the package itself and everything it contains
    nodes_to_include = {package_node}

    # BFS to find all descendants
    to_visit = [package_node]
    visited = set()

    while to_visit:
        current = to_visit.pop(0)
        if current in visited:
            continue
        visited.add(current)

        # Add all successors (nodes this points to)
        for successor in graph.successors(current):
            nodes_to_include.add(successor)
            if successor not in visited:
                to_visit.append(successor)

    # Create subgraph
    return graph.subgraph(nodes_to_include).copy()


def _create_visualization(
    graph: nx.DiGraph,
    output_path: Path,
    title: str = "Knowledge Graph",
    layout: str = "hierarchical",
    show_labels: bool = True,
    show_edge_labels: bool = False,
    node_size: int = 3000,
    font_size: int = 10,
) -> None:
    """Create and save graph visualization using matplotlib."""
    # Create figure
    plt.figure(figsize=(16, 12))
    plt.title(title, fontsize=16, fontweight="bold")

    # Choose layout algorithm
    if layout == "hierarchical":
        # Try to create hierarchical layout
        pos = _hierarchical_layout(graph)
    elif layout == "spring":
        pos = nx.spring_layout(graph, k=2, iterations=50)
    elif layout == "circular":
        pos = nx.circular_layout(graph)
    elif layout == "kamada_kawai":
        pos = nx.kamada_kawai_layout(graph)
    else:
        pos = nx.spring_layout(graph)

    # Color nodes by type
    node_colors = []
    node_types_legend = {}

    color_map = {
        NodeType.PACKAGE: "#FF6B6B",  # Red
        NodeType.TASK: "#4ECDC4",  # Teal
        NodeType.TABLE: "#45B7D1",  # Blue
        NodeType.CONNECTION: "#FFA07A",  # Orange
        NodeType.VARIABLE: "#98D8C8",  # Mint
    }

    for node_id in graph.nodes():
        node_data = graph.nodes[node_id]
        node_type = node_data.get("node_type")

        if node_type in color_map:
            node_colors.append(color_map[node_type])
            node_types_legend[node_type.value if hasattr(node_type, "value") else str(node_type)] = color_map[
                node_type
            ]
        else:
            node_colors.append("#CCCCCC")  # Gray for unknown

    # Draw nodes
    nx.draw_networkx_nodes(graph, pos, node_color=node_colors, node_size=node_size, alpha=0.9)

    # Draw edges with colors based on edge type
    edge_colors = []
    edge_color_map = {
        EdgeType.CONTAINS: "#666666",  # Dark gray
        EdgeType.PRECEDES: "#2E86AB",  # Blue
        EdgeType.READS_FROM: "#06A77D",  # Green
        EdgeType.WRITES_TO: "#D62828",  # Red
    }

    for u, v in graph.edges():
        edge_data = graph[u][v]
        edge_type = edge_data.get("edge_type")

        if edge_type in edge_color_map:
            edge_colors.append(edge_color_map[edge_type])
        else:
            edge_colors.append("#999999")

    nx.draw_networkx_edges(graph, pos, edge_color=edge_colors, arrows=True, arrowsize=20, alpha=0.6, width=2)

    # Draw labels
    if show_labels:
        labels = {}
        for node_id in graph.nodes():
            node_data = graph.nodes[node_id]
            name = node_data.get("name", node_id)
            # Truncate long names
            if len(name) > 20:
                name = name[:17] + "..."
            labels[node_id] = name

        nx.draw_networkx_labels(graph, pos, labels, font_size=font_size, font_weight="bold")

    # Draw edge labels
    if show_edge_labels:
        edge_labels = {}
        for u, v in graph.edges():
            edge_data = graph[u][v]
            edge_type = edge_data.get("edge_type")
            if edge_type:
                label = edge_type.value if hasattr(edge_type, "value") else str(edge_type)
                edge_labels[(u, v)] = label

        nx.draw_networkx_edge_labels(graph, pos, edge_labels, font_size=font_size - 2)

    # Create legend for node types
    legend_elements = []
    for type_name, color in node_types_legend.items():
        legend_elements.append(plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=color, markersize=10, label=type_name))

    if legend_elements:
        plt.legend(handles=legend_elements, loc="upper left", fontsize=10)

    plt.axis("off")
    plt.tight_layout()

    # Save
    plt.savefig(output_path, format=output_path.suffix[1:], dpi=300, bbox_inches="tight")
    plt.close()


def _hierarchical_layout(graph: nx.DiGraph) -> dict[Any, tuple[float, float]]:
    """Create hierarchical layout with packages at top, tasks in middle, tables at bottom."""
    pos = {}

    # Group nodes by type
    packages = []
    tasks = []
    connections = []
    tables = []
    variables = []
    other = []

    for node_id, data in graph.nodes(data=True):
        node_type = data.get("node_type")

        if node_type == NodeType.PACKAGE:
            packages.append(node_id)
        elif node_type == NodeType.TASK:
            tasks.append(node_id)
        elif node_type == NodeType.CONNECTION:
            connections.append(node_id)
        elif node_type == NodeType.TABLE:
            tables.append(node_id)
        elif node_type == NodeType.VARIABLE:
            variables.append(node_id)
        else:
            other.append(node_id)

    # Assign Y levels (higher = top)
    y_levels = {
        "packages": 5.0,
        "tasks": 3.0,
        "connections": 2.0,
        "variables": 1.5,
        "tables": 0.5,
        "other": 2.5,
    }

    # Layout each group horizontally
    def layout_group(nodes: list, y: float) -> None:
        if not nodes:
            return
        x_spacing = 10.0 / max(len(nodes), 1)
        for i, node in enumerate(nodes):
            x = (i - len(nodes) / 2) * x_spacing
            pos[node] = (x, y)

    layout_group(packages, y_levels["packages"])
    layout_group(tasks, y_levels["tasks"])
    layout_group(connections, y_levels["connections"])
    layout_group(variables, y_levels["variables"])
    layout_group(tables, y_levels["tables"])
    layout_group(other, y_levels["other"])

    return pos
