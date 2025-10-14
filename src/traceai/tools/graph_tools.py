"""LangChain tools for knowledge graph interaction.

This module provides LangChain tools that wrap the graph query functionality,
enabling AI agents to interact with the knowledge graph.
"""

from typing import Any, Optional

import networkx as nx
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from traceai.graph.queries import GraphQueries
from traceai.graph.schema import EdgeType, NodeType


# Tool Input Schemas


class GraphQueryInput(BaseModel):
    """Input schema for graph query tool."""

    node_type: str = Field(
        description="Type of node to search for (package, task, connection, variable, table)"
    )
    name_pattern: Optional[str] = Field(
        default=None, description="Optional name pattern to filter nodes (case-insensitive substring match)"
    )
    document_type: Optional[str] = Field(
        default=None,
        description="Optional document_type filter (exact match, e.g. 'cobol_program', only applies to packages)",
    )
    metadata_filters: Optional[dict[str, str]] = Field(
        default=None,
        description="Optional metadata filters where keys map to node attributes (substring match for strings)",
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


class PackageCatalogInput(BaseModel):
    """Input schema for bulk package catalog tool."""

    document_type: Optional[str] = Field(
        default=None,
        description="Optional document_type filter (exact match, e.g. 'cobol_program').",
    )
    name_pattern: Optional[str] = Field(
        default=None,
        description="Optional case-insensitive substring to filter package names (e.g. 'PAY').",
    )
    limit: int = Field(
        default=25,
        ge=1,
        le=200,
        description="Maximum number of packages to include in the response (default 25, max 200).",
    )
    include_components: bool = Field(
        default=False,
        description="Include example component names for each package (up to component_limit entries).",
    )
    include_data_sources: bool = Field(
        default=False,
        description="Include example data sources/entities for each package (up to component_limit entries).",
    )
    include_dependencies: bool = Field(
        default=False,
        description="Include upstream/downstream dependency names (up to component_limit entries).",
    )
    component_limit: int = Field(
        default=5,
        ge=1,
        le=25,
        description="Maximum number of component/data source/dependency names to list per package when included.",
    )


class PackageSummaryInput(BaseModel):
    """Input schema for package summary tool."""

    package_name: str = Field(description="Exact name of the package/document to summarize")
    include_components: bool = Field(
        default=True,
        description="Include key components (tasks, steps) in the summary",
    )
    include_data_sources: bool = Field(
        default=True,
        description="Include data sources and entities linked to the package",
    )
    include_dependencies: bool = Field(
        default=True,
        description="Include upstream/downstream package dependencies",
    )


def _collect_dependency_names(graph: nx.DiGraph, package_id: str) -> tuple[list[str], list[str]]:
    """Return upstream and downstream dependency names for a package node."""

    upstream: list[str] = []
    downstream: list[str] = []

    for predecessor in graph.predecessors(package_id):
        edge = graph.edges[predecessor, package_id]
        if edge.get("edge_type") == EdgeType.DEPENDS_ON:
            upstream.append(graph.nodes[predecessor].get("name", predecessor))

    for successor in graph.successors(package_id):
        edge = graph.edges[package_id, successor]
        if edge.get("edge_type") == EdgeType.DEPENDS_ON:
            downstream.append(graph.nodes[successor].get("name", successor))

    return upstream, downstream


def _build_default_package_description(
    package_data: dict[str, Any],
    task_count: int,
    connection_count: int,
    variable_count: int,
    upstream_count: int,
    downstream_count: int,
) -> str:
    """Generate a fallback description when none is provided in the graph."""

    doc_type = package_data.get("document_type") or "package"
    doc_label = str(doc_type).replace("_", " ")
    return (
        f"{doc_label.capitalize()} with {task_count} component(s), {connection_count} data source(s), "
        f"{variable_count} variable(s), {upstream_count} upstream dependency(ies), and "
        f"{downstream_count} downstream dependency(ies)."
    )


def _format_limited_list(label: str, values: list[str], limit: int) -> str:
    """Format a list with a display limit and overflow indicator."""

    if not values:
        return f"   {label}: None"

    displayed = values[:limit]
    remainder = len(values) - len(displayed)
    suffix = f" (+{remainder} more)" if remainder > 0 else ""
    return f"   {label}: {', '.join(displayed)}{suffix}"


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

    You can optionally filter by:
    - name_pattern (case-insensitive substring match)
    - document_type (exact match, e.g. 'cobol_program')
    - metadata_filters (additional key/value attribute filters)

    IMPORTANT TERMINOLOGY MAPPINGS:
    - COBOL programs, JCL jobs → node_type: "package"
    - COBOL paragraphs, JCL steps, SSIS tasks → node_type: "task"
    - Datasets, COBOL files, SQL tables → node_type: "table"

    Example queries:
    - "Find all COBOL programs" → node_type: "package", document_type: "cobol_program"
    - "Find JCL jobs" → node_type: "package", name_pattern: "DAILY"
    - "Find tasks containing 'ETL'" → node_type: "task", name_pattern: "ETL"
    - "Find datasets in SALES" → node_type: "table", name_pattern: "SALES"
    """
    args_schema: type[BaseModel] = GraphQueryInput

    graph: nx.DiGraph = Field(description="NetworkX graph to query")

    def _run(
        self,
        node_type: str,
        name_pattern: Optional[str] = None,
        document_type: Optional[str] = None,
        metadata_filters: Optional[dict[str, str]] = None,
    ) -> str:
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

            # Apply document type filter when available
            if document_type:
                doc_type_lower = document_type.lower()
                nodes = [
                    (node_id, data)
                    for node_id, data in nodes
                    if str(data.get("document_type", "")).lower() == doc_type_lower
                ]

            # Apply arbitrary metadata filters (substring match for str values)
            if metadata_filters:
                def matches_metadata(data: dict[str, Any]) -> bool:
                    for key, expected in metadata_filters.items():
                        value = data.get(key)
                        if value is None:
                            return False
                        if isinstance(value, str):
                            if expected.lower() not in value.lower():
                                return False
                        else:
                            if value != expected:
                                return False
                    return True

                nodes = [
                    (node_id, data)
                    for node_id, data in nodes
                    if matches_metadata(data)
                ]

            if not nodes:
                if name_pattern:
                    return f"No {node_type} nodes found matching pattern '{name_pattern}'"
                if document_type:
                    return f"No {node_type} nodes found with document_type '{document_type}'"
                return f"No {node_type} nodes found in the graph"

            # Format results
            result_lines = [f"Found {len(nodes)} {node_type} node(s):\n"]
            for node_id, data in nodes:
                name = data.get("name", "Unknown")
                description = data.get("description", "")
                doc_type = data.get("document_type")
                result_lines.append(f"- {name}")
                if doc_type:
                    result_lines.append(f"  Document Type: {doc_type}")
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


class PackageCatalogTool(BaseTool):
    """Tool for retrieving catalog-style summaries of multiple packages."""

    name: str = "package_catalog"
    description: str = """
    Retrieve a catalog of packages/documents and summarize them in a single call.

    Use this tool whenever you need to list or compare many packages at once:
    - Enumerate all COBOL programs with brief descriptions
    - Summarize SSIS packages that match a naming pattern
    - Review upstream/downstream counts without querying each package individually

    Prefer this tool instead of calling package_summary repeatedly. You can
    control how much detail to include (component names, data sources, dependencies)
    while keeping the response concise.
    """
    args_schema: type[BaseModel] = PackageCatalogInput

    graph: nx.DiGraph = Field(description="NetworkX graph to query")

    def _run(
        self,
        document_type: Optional[str] = None,
        name_pattern: Optional[str] = None,
        limit: int = 25,
        include_components: bool = False,
        include_data_sources: bool = False,
        include_dependencies: bool = False,
        component_limit: int = 5,
    ) -> str:
        try:
            queries = GraphQueries(self.graph)
            packages = queries.find_nodes_by_type(NodeType.PACKAGE)

            if document_type:
                doc_filter = document_type.lower()
                packages = [
                    (node_id, data)
                    for node_id, data in packages
                    if str(data.get("document_type", "")).lower() == doc_filter
                ]

            if name_pattern:
                pattern = name_pattern.lower()
                packages = [
                    (node_id, data)
                    for node_id, data in packages
                    if pattern in (data.get("name", "").lower())
                ]

            if not packages:
                return "No packages found for the requested filters."

            # Sort for deterministic output
            packages.sort(key=lambda item: item[1].get("name", item[0]))

            total_matches = len(packages)
            limit = max(1, min(limit, total_matches))
            selected = packages[:limit]

            lines: list[str] = [
                f"Package catalog ({len(selected)} of {total_matches} match(es) shown)",
            ]
            if total_matches > limit:
                lines.append(
                    "   (Increase 'limit' to see more packages, or refine filters to narrow the set.)"
                )

            for idx, (package_id, package_data) in enumerate(selected, start=1):
                name = package_data.get("name", package_id)
                doc_type = package_data.get("document_type") or "unknown"

                contents = queries.get_package_contents(package_id)
                task_count = len(contents.get("tasks", []))
                connection_count = len(contents.get("connections", []))
                variable_count = len(contents.get("variables", []))
                upstream_names, downstream_names = _collect_dependency_names(self.graph, package_id)

                description = package_data.get("description") or _build_default_package_description(
                    package_data,
                    task_count,
                    connection_count,
                    variable_count,
                    len(upstream_names),
                    len(downstream_names),
                )

                lines.append("")
                lines.append(f"{idx}. {name} ({doc_type})")
                lines.append(f"   Summary: {description}")
                lines.append(
                    "   Stats: "
                    f"{task_count} component(s), {connection_count} data source(s), "
                    f"{variable_count} variable(s), {len(upstream_names)} upstream, {len(downstream_names)} downstream"
                )

                if include_components and contents.get("tasks"):
                    component_names = sorted(
                        {task_data.get("name", task_id) for task_id, task_data in contents["tasks"]}
                    )
                    lines.append(_format_limited_list("Components", component_names, component_limit))

                if include_data_sources and contents.get("connections"):
                    connection_names = sorted(
                        {conn_data.get("name", conn_id) for conn_id, conn_data in contents["connections"]}
                    )
                    lines.append(_format_limited_list("Data Sources", connection_names, component_limit))

                if include_dependencies:
                    lines.append(_format_limited_list("Upstream Dependencies", upstream_names, component_limit))
                    lines.append(_format_limited_list("Downstream Dependencies", downstream_names, component_limit))

            return "\n".join(lines)

        except Exception as exc:
            return f"Error generating package catalog: {exc}"


class PackageSummaryTool(BaseTool):
    """Tool for generating a rich summary of a package/document."""

    name: str = "package_summary"
    description: str = """
    Summarize a package or document, including its metadata, contained components,
    associated data sources, and package-level dependencies.

    Use this tool to quickly understand what a document contains:
    - List connections, variables, and tasks in the package
    - Highlight data entities the tasks touch (reads/writes)
    - Show upstream/downstream package dependencies

    Prefer this tool for deep dives on a single package. For listing or comparing
    many packages at once, call package_catalog to avoid repetitive tool calls.
    Example:
    - package_name: "CUST001"
    """
    args_schema: type[BaseModel] = PackageSummaryInput

    graph: nx.DiGraph = Field(description="NetworkX graph to query")

    def _run(
        self,
        package_name: str,
        include_components: bool = True,
        include_data_sources: bool = True,
        include_dependencies: bool = True,
    ) -> str:
        try:
            queries = GraphQueries(self.graph)

            # Locate the package node
            package_nodes = queries.find_node_by_name(package_name, NodeType.PACKAGE)
            if not package_nodes:
                matches = queries.search_nodes(package_name, NodeType.PACKAGE)
                if matches:
                    suggestions = ", ".join([data.get("name", node_id) for node_id, data in matches[:5]])
                    return f"Package '{package_name}' not found. Did you mean: {suggestions}?"
                return f"Package '{package_name}' not found in the graph"

            package_id, package_data = package_nodes[0]

            lines: list[str] = []
            doc_type = package_data.get("document_type", "unknown")
            lines.append(f"Package: {package_data.get('name', package_name)}")
            lines.append(f"Document Type: {doc_type}")

            contents = queries.get_package_contents(package_id)
            upstream_names, downstream_names = _collect_dependency_names(self.graph, package_id)

            description = package_data.get("description") or _build_default_package_description(
                package_data,
                len(contents.get("tasks", [])),
                len(contents.get("connections", [])),
                len(contents.get("variables", [])),
                len(upstream_names),
                len(downstream_names),
            )
            lines.append(f"Description: {description}")
            if package_data.get("file_path"):
                lines.append(f"File: {package_data['file_path']}")

            if include_data_sources and contents.get("connections"):
                lines.append("\nConnections/Data Sources:")
                for conn_id, conn_data in contents["connections"]:
                    conn_name = conn_data.get("name", conn_id)
                    conn_type = conn_data.get("connection_type", conn_data.get("source_type", "unknown"))
                    lines.append(f"  • {conn_name} ({conn_type})")

            if include_components and contents.get("tasks"):
                lines.append("\nComponents:")
                for task_id, task_data in contents["tasks"][:25]:
                    task_name = task_data.get("name", task_id)
                    task_type = task_data.get("task_type", "unknown")
                    lines.append(f"  • {task_name} [{task_type}]")

                    if include_data_sources:
                        reads = queries.find_tables_read_by_task(task_id)
                        writes = queries.find_tables_written_by_task(task_id)
                        if reads:
                            lines.append(
                                "     ↳ Reads: "
                                + ", ".join(sorted({data.get("name", table_id) for table_id, data in reads}))
                            )
                        if writes:
                            lines.append(
                                "     ↳ Writes: "
                                + ", ".join(sorted({data.get("name", table_id) for table_id, data in writes}))
                            )

                if len(contents["tasks"]) > 25:
                    lines.append(
                        f"  … {len(contents['tasks']) - 25} more component(s) omitted for brevity"
                    )

            if include_dependencies:
                if upstream_names:
                    lines.append("\nUpstream Dependencies:")
                    for name in upstream_names:
                        lines.append(f"  • {name}")

                if downstream_names:
                    lines.append("\nDownstream Dependencies:")
                    for name in downstream_names:
                        lines.append(f"  • {name}")

                if not upstream_names and not downstream_names:
                    lines.append("\nDependencies: None")

            return "\n".join(lines)

        except Exception as exc:
            return f"Error generating package summary: {exc}"


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
        PackageCatalogTool(graph=graph),
        PackageSummaryTool(graph=graph),
    ]
