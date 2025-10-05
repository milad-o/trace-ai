"""Graph query functions for knowledge graph analysis."""

from typing import Any

import networkx as nx

from traceai.graph.schema import EdgeType, NodeType


class GraphQueries:
    """Query functions for the knowledge graph."""

    def __init__(self, graph: nx.DiGraph) -> None:
        """
        Initialize graph queries.

        Args:
            graph: NetworkX directed graph
        """
        self.graph = graph

    def find_nodes_by_type(self, node_type: NodeType) -> list[tuple[str, dict[str, Any]]]:
        """
        Find all nodes of a specific type.

        Args:
            node_type: Type of nodes to find

        Returns:
            List of (node_id, attributes) tuples
        """
        return [
            (node_id, data)
            for node_id, data in self.graph.nodes(data=True)
            if data.get("node_type") == node_type
        ]

    def find_node_by_name(
        self, name: str, node_type: NodeType | None = None
    ) -> list[tuple[str, dict[str, Any]]]:
        """
        Find nodes by name.

        Args:
            name: Node name to search for
            node_type: Optional node type filter

        Returns:
            List of matching (node_id, attributes) tuples
        """
        matches = []
        for node_id, data in self.graph.nodes(data=True):
            if data.get("name") == name:
                if node_type is None or data.get("node_type") == node_type:
                    matches.append((node_id, data))
        return matches

    def search_nodes(
        self, search_term: str, node_type: NodeType | None = None
    ) -> list[tuple[str, dict[str, Any]]]:
        """
        Search nodes by name (case-insensitive substring match).

        Args:
            search_term: Term to search for
            node_type: Optional node type filter

        Returns:
            List of matching (node_id, attributes) tuples
        """
        search_lower = search_term.lower()
        matches = []

        for node_id, data in self.graph.nodes(data=True):
            name = data.get("name", "").lower()
            if search_lower in name:
                if node_type is None or data.get("node_type") == node_type:
                    matches.append((node_id, data))

        return matches

    def get_package_contents(self, package_id: str) -> dict[str, list[tuple[str, dict]]]:
        """
        Get all contents of a package (connections, variables, tasks).

        Args:
            package_id: Package node ID

        Returns:
            Dict with lists of connections, variables, and tasks
        """
        contents: dict[str, list[tuple[str, dict]]] = {
            "connections": [],
            "variables": [],
            "tasks": [],
        }

        # Find all nodes that the package CONTAINS
        for neighbor in self.graph.successors(package_id):
            edge_data = self.graph.edges[package_id, neighbor]
            if edge_data.get("edge_type") == EdgeType.CONTAINS:
                node_data = self.graph.nodes[neighbor]
                node_type = node_data.get("node_type")

                if node_type == NodeType.CONNECTION:
                    contents["connections"].append((neighbor, node_data))
                elif node_type == NodeType.VARIABLE:
                    contents["variables"].append((neighbor, node_data))
                elif node_type == NodeType.TASK:
                    contents["tasks"].append((neighbor, node_data))

        return contents

    def get_task_dependencies(self, task_id: str) -> dict[str, list[tuple[str, dict]]]:
        """
        Get task dependencies (predecessors and successors).

        Args:
            task_id: Task node ID

        Returns:
            Dict with 'predecessors' and 'successors' lists
        """
        deps: dict[str, list[tuple[str, dict]]] = {"predecessors": [], "successors": []}

        # Find tasks that precede this one
        for predecessor in self.graph.predecessors(task_id):
            edge_data = self.graph.edges[predecessor, task_id]
            if edge_data.get("edge_type") == EdgeType.PRECEDES:
                node_data = self.graph.nodes[predecessor]
                deps["predecessors"].append((predecessor, node_data))

        # Find tasks that this one precedes
        for successor in self.graph.successors(task_id):
            edge_data = self.graph.edges[task_id, successor]
            if edge_data.get("edge_type") == EdgeType.PRECEDES:
                node_data = self.graph.nodes[successor]
                deps["successors"].append((successor, node_data))

        return deps

    def find_tables_read_by_task(self, task_id: str) -> list[tuple[str, dict[str, Any]]]:
        """
        Find all tables that a task reads from.

        Args:
            task_id: Task node ID

        Returns:
            List of (table_id, attributes) tuples
        """
        tables = []
        for neighbor in self.graph.successors(task_id):
            edge_data = self.graph.edges[task_id, neighbor]
            if edge_data.get("edge_type") == EdgeType.READS_FROM:
                node_data = self.graph.nodes[neighbor]
                tables.append((neighbor, node_data))
        return tables

    def find_tables_written_by_task(self, task_id: str) -> list[tuple[str, dict[str, Any]]]:
        """
        Find all tables that a task writes to.

        Args:
            task_id: Task node ID

        Returns:
            List of (table_id, attributes) tuples
        """
        tables = []
        for neighbor in self.graph.successors(task_id):
            edge_data = self.graph.edges[task_id, neighbor]
            if edge_data.get("edge_type") == EdgeType.WRITES_TO:
                node_data = self.graph.nodes[neighbor]
                tables.append((neighbor, node_data))
        return tables

    def find_tasks_reading_from_table(self, table_name: str) -> list[tuple[str, dict[str, Any]]]:
        """
        Find all tasks that read from a specific table.

        Args:
            table_name: Table name to search for

        Returns:
            List of (task_id, attributes) tuples
        """
        tasks = []

        # Find table node(s) with this name
        table_nodes = self.find_node_by_name(table_name, NodeType.TABLE)

        for table_id, _ in table_nodes:
            # Find tasks that read from this table
            for predecessor in self.graph.predecessors(table_id):
                edge_data = self.graph.edges[predecessor, table_id]
                if edge_data.get("edge_type") == EdgeType.READS_FROM:
                    task_data = self.graph.nodes[predecessor]
                    tasks.append((predecessor, task_data))

        return tasks

    def find_tasks_writing_to_table(self, table_name: str) -> list[tuple[str, dict[str, Any]]]:
        """
        Find all tasks that write to a specific table.

        Args:
            table_name: Table name to search for

        Returns:
            List of (task_id, attributes) tuples
        """
        tasks = []

        # Find table node(s) with this name
        table_nodes = self.find_node_by_name(table_name, NodeType.TABLE)

        for table_id, _ in table_nodes:
            # Find tasks that write to this table
            for predecessor in self.graph.predecessors(table_id):
                edge_data = self.graph.edges[predecessor, table_id]
                if edge_data.get("edge_type") == EdgeType.WRITES_TO:
                    task_data = self.graph.nodes[predecessor]
                    tasks.append((predecessor, task_data))

        return tasks

    def trace_data_lineage(
        self, table_name: str, direction: str = "both"
    ) -> dict[str, list[tuple[str, dict]]]:
        """
        Trace data lineage for a table (upstream and/or downstream).

        Args:
            table_name: Table name to trace
            direction: 'upstream' (sources), 'downstream' (targets), or 'both'

        Returns:
            Dict with upstream and/or downstream lineage
        """
        lineage: dict[str, list[tuple[str, dict]]] = {"upstream": [], "downstream": []}

        # Find the table node
        table_nodes = self.find_node_by_name(table_name, NodeType.TABLE)
        if not table_nodes:
            return lineage

        table_id, _ = table_nodes[0]  # Use first match

        if direction in ["upstream", "both"]:
            # Find tasks that write to this table (sources)
            writers = self.find_tasks_writing_to_table(table_name)
            for writer_id, writer_data in writers:
                # Find tables those tasks read from
                upstream_tables = self.find_tables_read_by_task(writer_id)
                lineage["upstream"].extend(upstream_tables)

        if direction in ["downstream", "both"]:
            # Find tasks that read from this table
            readers = self.find_tasks_reading_from_table(table_name)
            for reader_id, reader_data in readers:
                # Find tables those tasks write to
                downstream_tables = self.find_tables_written_by_task(reader_id)
                lineage["downstream"].extend(downstream_tables)

        return lineage

    def find_execution_path(self, from_task_id: str, to_task_id: str) -> list[str] | None:
        """
        Find execution path between two tasks.

        Args:
            from_task_id: Starting task ID
            to_task_id: Target task ID

        Returns:
            List of task IDs in the path, or None if no path exists
        """
        try:
            # Use NetworkX shortest path algorithm
            path = nx.shortest_path(self.graph, from_task_id, to_task_id)
            return path
        except nx.NetworkXNoPath:
            return None

    def find_connected_components(self) -> list[set[str]]:
        """
        Find connected components (groups of related nodes).

        Returns:
            List of sets, each containing node IDs in a component
        """
        # Convert to undirected for component analysis
        undirected = self.graph.to_undirected()
        components = list(nx.connected_components(undirected))
        return components

    def calculate_node_importance(self, node_id: str) -> dict[str, float]:
        """
        Calculate importance metrics for a node.

        Args:
            node_id: Node to analyze

        Returns:
            Dict with importance metrics
        """
        return {
            "in_degree": self.graph.in_degree(node_id),
            "out_degree": self.graph.out_degree(node_id),
            "total_degree": self.graph.in_degree(node_id) + self.graph.out_degree(node_id),
        }

    def get_graph_stats(self) -> dict[str, Any]:
        """Get overall graph statistics."""
        stats: dict[str, Any] = {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "is_directed": self.graph.is_directed(),
            "is_connected": nx.is_weakly_connected(self.graph),
        }

        # Count by node type
        for node_type in NodeType:
            count = sum(
                1
                for _, data in self.graph.nodes(data=True)
                if data.get("node_type") == node_type
            )
            stats[f"{node_type.value.lower()}_count"] = count

        # Count by edge type
        for edge_type in EdgeType:
            count = sum(
                1
                for _, _, data in self.graph.edges(data=True)
                if data.get("edge_type") == edge_type
            )
            stats[f"{edge_type.value.lower()}_count"] = count

        return stats
