"""LangChain tools for knowledge graph interaction.

This module provides LangChain tools that wrap the graph query functionality,
enabling AI agents to interact with the knowledge graph.
"""

from typing import Any, Optional

import networkx as nx
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from traceai.graph.queries import GraphQueries
from traceai.graph.schema import NodeType


# Tool Input Schemas


class GraphQueryInput(BaseModel):
    """Input schema for graph query tool."""

    node_type: str = Field(
        description="Type of node to search for (package, task, connection, variable, table)"
    )
    name_pattern: Optional[str] = Field(
        default=None, description="Optional name pattern to filter nodes (case-insensitive substring match)"
    )


class LineageTraceInput(BaseModel):
    """Input schema for lineage tracing tool."""

    entity_name: str = Field(description="Name of the data entity (table, sheet, file) to trace lineage for")
    direction: str = Field(
        default="both",
        description="Direction to trace: 'upstream' (where data comes from), 'downstream' (where data goes), or 'both'",
    )
    max_depth: int = Field(default=10, description="Maximum depth to traverse (default: 10)")


class ImpactAnalysisInput(BaseModel):
    """Input schema for impact analysis tool."""

    entity_name: str = Field(description="Name of the data entity (table, sheet, file) to analyze impact for")
    analysis_type: str = Field(
        default="full",
        description="Type of analysis: 'readers' (components that read), 'writers' (components that write), or 'full' (both)",
    )


class DependencySearchInput(BaseModel):
    """Input schema for dependency search tool."""

    component_name: str = Field(description="Name of the component (task, step, formula) to find dependencies for")
    direction: str = Field(
        default="both",
        description="Direction: 'predecessors' (what must run before), 'successors' (what runs after), or 'both'",
    )


# LangChain Tools


class GraphQueryTool(BaseTool):
    """Tool for querying the knowledge graph.

    This tool allows searching for nodes by type and optionally filtering by name.
    Useful for discovering what exists in the knowledge graph.
    """

    name: str = "graph_query"
    description: str = """
    Query the knowledge graph to find nodes by type.

    Use this tool to discover what exists in the knowledge graph:
    - Find all packages/documents (SSIS packages, COBOL programs, JCL jobs)
    - Find all tasks/components (SSIS tasks, COBOL paragraphs, JCL steps)
    - Find all tables/entities (SQL tables, COBOL files, JCL datasets)
    - Find all connections/data sources (database connections, file connections)
    - Find all variables/parameters

    You can optionally filter by name pattern (case-insensitive substring match).

    IMPORTANT TERMINOLOGY MAPPINGS:
    - COBOL programs, JCL jobs → node_type: "package"
    - COBOL paragraphs, JCL steps, SSIS tasks → node_type: "task"
    - Datasets, COBOL files, SQL tables → node_type: "table"

    Example queries:
    - "Find all COBOL programs" → node_type: "package", name_pattern: "CUST"
    - "Find JCL jobs" → node_type: "package", name_pattern: "DAILY"
    - "Find tasks containing 'ETL'" → node_type: "task", name_pattern: "ETL"
    - "Find datasets in SALES" → node_type: "table", name_pattern: "SALES"
    """
    args_schema: type[BaseModel] = GraphQueryInput

    graph: nx.DiGraph = Field(description="NetworkX graph to query")

    def _run(self, node_type: str, name_pattern: Optional[str] = None) -> str:
        """Execute the graph query."""
        try:
            queries = GraphQueries(self.graph)

            # Map string node type to NodeType enum
            node_type_map = {
                "package": NodeType.PACKAGE,
                "task": NodeType.TASK,
                "connection": NodeType.CONNECTION,
                "variable": NodeType.VARIABLE,
                "table": NodeType.TABLE,
                "column": NodeType.COLUMN,
            }

            node_type_lower = node_type.lower()
            if node_type_lower not in node_type_map:
                return f"Error: Invalid node_type '{node_type}'. Valid types: {', '.join(node_type_map.keys())}"

            # Find nodes by type
            nodes = queries.find_nodes_by_type(node_type_map[node_type_lower])

            # Apply name filter if provided
            if name_pattern:
                pattern_lower = name_pattern.lower()
                filtered_nodes = [
                    (node_id, data)
                    for node_id, data in nodes
                    if data.get("name") and pattern_lower in data["name"].lower()
                ]
                nodes = filtered_nodes

            if not nodes:
                if name_pattern:
                    return f"No {node_type} nodes found matching pattern '{name_pattern}'"
                return f"No {node_type} nodes found in the graph"

            # Format results
            result_lines = [f"Found {len(nodes)} {node_type} node(s):\n"]
            for node_id, data in nodes:
                name = data.get("name", "Unknown")
                description = data.get("description", "")
                result_lines.append(f"- {name}")
                if description:
                    result_lines.append(f"  Description: {description}")

            return "\n".join(result_lines)

        except Exception as e:
            return f"Error executing graph query: {str(e)}"


class LineageTracerTool(BaseTool):
    """Tool for tracing data lineage through the knowledge graph.

    This tool traces how data flows through the system, showing upstream sources
    and downstream consumers of data entities.
    """

    name: str = "trace_lineage"
    description: str = """
    Trace data lineage for a table, sheet, file, or other data entity.

    Use this tool to understand data flow:
    - Where does this data come from? (upstream)
    - Where does this data go? (downstream)
    - What is the complete data flow? (both)

    This helps answer questions like:
    - "What feeds into the Sales table?"
    - "Where is Customer data used downstream?"
    - "Show me the complete flow for the DimCustomer table"

    Example:
    - entity_name: "dbo.Customers", direction: "downstream"
    - entity_name: "Sales", direction: "upstream"
    - entity_name: "StagingTable", direction: "both"
    """
    args_schema: type[BaseModel] = LineageTraceInput

    graph: nx.DiGraph = Field(description="NetworkX graph to query")

    def _run(self, entity_name: str, direction: str = "both", max_depth: int = 10) -> str:
        """Trace data lineage."""
        try:
            queries = GraphQueries(self.graph)

            # Validate direction
            if direction not in ["upstream", "downstream", "both"]:
                return "Error: direction must be 'upstream', 'downstream', or 'both'"

            # Find the entity node
            entity_nodes = queries.find_node_by_name(entity_name)
            if not entity_nodes:
                # Try partial match
                all_tables = queries.find_nodes_by_type(NodeType.TABLE)
                matches = [
                    (node_id, data)
                    for node_id, data in all_tables
                    if entity_name.lower() in data.get("name", "").lower()
                ]
                if matches:
                    suggestions = ", ".join([data["name"] for _, data in matches[:5]])
                    return f"Entity '{entity_name}' not found. Did you mean: {suggestions}?"
                return f"Entity '{entity_name}' not found in the graph"

            # Use first match
            entity_id, entity_data = entity_nodes[0]

            # Trace lineage (using entity name, not ID)
            table_name = entity_data.get('name', entity_name)
            result_lines = [f"Data Lineage for: {table_name}\n"]

            lineage_result = queries.trace_data_lineage(table_name, direction=direction)

            if direction in ["upstream", "both"]:
                upstream = lineage_result.get("upstream", []) if isinstance(lineage_result, dict) else []
                if upstream:
                    result_lines.append(f"\n🔼 UPSTREAM (Data Sources) - {len(upstream)} found:")
                    for task_id, task_data in upstream[:max_depth]:
                        task_name = task_data.get('name', task_id)
                        result_lines.append(f"  ← {task_name}")
                else:
                    result_lines.append("\n🔼 UPSTREAM: No upstream sources found")

            if direction in ["downstream", "both"]:
                downstream = lineage_result.get("downstream", []) if isinstance(lineage_result, dict) else []
                if downstream:
                    result_lines.append(f"\n🔽 DOWNSTREAM (Data Consumers) - {len(downstream)} found:")
                    for task_id, task_data in downstream[:max_depth]:
                        task_name = task_data.get('name', task_id)
                        result_lines.append(f"  → {task_name}")
                else:
                    result_lines.append("\n🔽 DOWNSTREAM: No downstream consumers found")

            return "\n".join(result_lines)

        except Exception as e:
            return f"Error tracing lineage: {str(e)}"


class ImpactAnalysisTool(BaseTool):
    """Tool for analyzing the impact of changes to data entities.

    This tool identifies which components (tasks, formulas, scripts) would be
    affected if a data entity (table, sheet, file) is modified or removed.
    """

    name: str = "analyze_impact"
    description: str = """
    Analyze the impact of changes to a data entity (table, sheet, file).

    Use this tool to answer questions like:
    - "What will break if I delete the Customer table?"
    - "Which processes read from the Sales table?"
    - "What writes to the Staging table?"
    - "Show me everything that touches the DimProduct table"

    The tool identifies:
    - Components that read from the entity
    - Components that write to the entity
    - Complete impact (both readers and writers)

    Example:
    - entity_name: "dbo.Customers", analysis_type: "readers"
    - entity_name: "Sales", analysis_type: "full"
    """
    args_schema: type[BaseModel] = ImpactAnalysisInput

    graph: nx.DiGraph = Field(description="NetworkX graph to query")

    def _run(self, entity_name: str, analysis_type: str = "full") -> str:
        """Analyze impact."""
        try:
            queries = GraphQueries(self.graph)

            # Validate analysis type
            if analysis_type not in ["readers", "writers", "full"]:
                return "Error: analysis_type must be 'readers', 'writers', or 'full'"

            # Find the entity
            entity_nodes = queries.find_node_by_name(entity_name)
            if not entity_nodes:
                return f"Entity '{entity_name}' not found in the graph"

            # Use first match
            entity_id, entity_data = entity_nodes[0]

            result_lines = [f"Impact Analysis for: {entity_data.get('name', entity_name)}\n"]

            if analysis_type in ["readers", "full"]:
                # Use table name (entity_data['name']) not entity_id
                readers = queries.find_tasks_reading_from_table(entity_data.get('name', entity_name))
                result_lines.append(f"\n📖 READERS ({len(readers)} task(s)):")
                if readers:
                    for task_id, task_data in readers:
                        task_name = task_data.get("name", task_id)
                        task_type = task_data.get("task_type", "unknown")
                        result_lines.append(f"  • {task_name} ({task_type})")
                else:
                    result_lines.append("  None")

            if analysis_type in ["writers", "full"]:
                # Use table name (entity_data['name']) not entity_id
                writers = queries.find_tasks_writing_to_table(entity_data.get('name', entity_name))
                result_lines.append(f"\n✍️  WRITERS ({len(writers)} task(s)):")
                if writers:
                    for task_id, task_data in writers:
                        task_name = task_data.get("name", task_id)
                        task_type = task_data.get("task_type", "unknown")
                        result_lines.append(f"  • {task_name} ({task_type})")
                else:
                    result_lines.append("  None")

            total_affected = len(readers) + len(writers) if analysis_type == "full" else len(readers if analysis_type == "readers" else writers)
            result_lines.append(f"\n⚠️  TOTAL IMPACT: {total_affected} component(s) affected")

            return "\n".join(result_lines)

        except Exception as e:
            return f"Error analyzing impact: {str(e)}"


class DependencySearchTool(BaseTool):
    """Tool for finding execution dependencies between components.

    This tool identifies which components must execute before or after a given
    component, based on precedence constraints and dependencies.
    """

    name: str = "find_dependencies"
    description: str = """
    Find execution dependencies for a component (task, step, formula).

    Use this tool to understand execution order:
    - What must run before this component? (predecessors)
    - What runs after this component? (successors)
    - Complete dependency chain (both)

    This helps answer questions like:
    - "What needs to run before the ETL task?"
    - "What happens after the Validation step?"
    - "Show me the execution flow for Data Load"

    Example:
    - component_name: "Load Customer Data", direction: "predecessors"
    - component_name: "Validate", direction: "both"
    """
    args_schema: type[BaseModel] = DependencySearchInput

    graph: nx.DiGraph = Field(description="NetworkX graph to query")

    def _run(self, component_name: str, direction: str = "both") -> str:
        """Find dependencies."""
        try:
            queries = GraphQueries(self.graph)

            # Validate direction
            if direction not in ["predecessors", "successors", "both"]:
                return "Error: direction must be 'predecessors', 'successors', or 'both'"

            # Find the component
            component_nodes = queries.find_node_by_name(component_name)
            if not component_nodes:
                # Try searching in tasks
                all_tasks = queries.find_nodes_by_type(NodeType.TASK)
                matches = [
                    (node_id, data)
                    for node_id, data in all_tasks
                    if component_name.lower() in data.get("name", "").lower()
                ]
                if matches:
                    suggestions = ", ".join([data["name"] for _, data in matches[:5]])
                    return f"Component '{component_name}' not found. Did you mean: {suggestions}?"
                return f"Component '{component_name}' not found in the graph"

            # Use first match
            component_id, component_data = component_nodes[0]

            result_lines = [f"Dependencies for: {component_data.get('name', component_name)}\n"]

            if direction in ["predecessors", "both"]:
                # Get all predecessors (nodes with edges pointing to this component)
                predecessors = list(self.graph.predecessors(component_id))
                result_lines.append(f"\n⬅️  PREDECESSORS ({len(predecessors)} component(s)):")
                if predecessors:
                    for pred_id in predecessors:
                        pred_data = self.graph.nodes[pred_id]
                        pred_name = pred_data.get('name', pred_id)
                        edge_data = self.graph.edges[pred_id, component_id]
                        edge_type = edge_data.get('edge_type', 'unknown')
                        result_lines.append(f"  • {pred_name} ({edge_type})")
                else:
                    result_lines.append("  None (this is a starting point)")

            if direction in ["successors", "both"]:
                # Get all successors (nodes this component has edges to)
                successors = list(self.graph.successors(component_id))
                result_lines.append(f"\n➡️  SUCCESSORS ({len(successors)} component(s)):")
                if successors:
                    for succ_id in successors:
                        succ_data = self.graph.nodes[succ_id]
                        succ_name = succ_data.get('name', succ_id)
                        edge_data = self.graph.edges[component_id, succ_id]
                        edge_type = edge_data.get('edge_type', 'unknown')
                        result_lines.append(f"  • {succ_name} ({edge_type})")
                else:
                    result_lines.append("  None (this is an endpoint)")

            return "\n".join(result_lines)

        except Exception as e:
            return f"Error finding dependencies: {str(e)}"


# Tool factory function


def create_graph_tools(graph: nx.DiGraph) -> list[BaseTool]:
    """
    Create all graph-related LangChain tools.

    Args:
        graph: NetworkX knowledge graph

    Returns:
        List of LangChain tools ready for use with agents
    """
    return [
        GraphQueryTool(graph=graph),
        LineageTracerTool(graph=graph),
        ImpactAnalysisTool(graph=graph),
        DependencySearchTool(graph=graph),
    ]
