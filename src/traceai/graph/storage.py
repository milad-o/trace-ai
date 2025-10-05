"""Graph persistence for NetworkX knowledge graph."""

import json
import pickle
from pathlib import Path
from typing import Any

import networkx as nx
from networkx.readwrite import json_graph

from traceai.config import settings
from traceai.logger import logger


class GraphStorage:
    """Handle graph persistence (save/load)."""

    def __init__(self, storage_path: Path | None = None) -> None:
        """
        Initialize graph storage.

        Args:
            storage_path: Path to store graph (defaults to config setting)
        """
        self.storage_path = storage_path or settings.graph_storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def save_pickle(self, graph: nx.DiGraph, path: Path | None = None) -> None:
        """
        Save graph to pickle format (fast, Python-specific).

        Args:
            graph: NetworkX graph to save
            path: Optional path override
        """
        save_path = path or self.storage_path

        try:
            with open(save_path, "wb") as f:
                pickle.dump(graph, f, protocol=pickle.HIGHEST_PROTOCOL)

            logger.info(
                f"Saved graph to {save_path} "
                f"({graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges)"
            )
        except Exception as e:
            logger.error(f"Failed to save graph to {save_path}: {e}")
            raise

    def load_pickle(self, path: Path | None = None) -> nx.DiGraph:
        """
        Load graph from pickle format.

        Args:
            path: Optional path override

        Returns:
            Loaded NetworkX graph
        """
        load_path = path or self.storage_path

        if not load_path.exists():
            logger.warning(f"Graph file not found: {load_path}, returning empty graph")
            return nx.DiGraph()

        try:
            with open(load_path, "rb") as f:
                graph = pickle.load(f)

            logger.info(
                f"Loaded graph from {load_path} "
                f"({graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges)"
            )
            return graph
        except Exception as e:
            logger.error(f"Failed to load graph from {load_path}: {e}")
            raise

    def save_json(self, graph: nx.DiGraph, path: Path) -> None:
        """
        Save graph to JSON format (portable, human-readable).

        Args:
            graph: NetworkX graph to save
            path: Path to save JSON file
        """
        try:
            # Convert graph to node-link format
            graph_data = json_graph.node_link_data(graph)

            with open(path, "w") as f:
                json.dump(graph_data, f, indent=2, default=str)

            logger.info(
                f"Saved graph to JSON {path} "
                f"({graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges)"
            )
        except Exception as e:
            logger.error(f"Failed to save graph to JSON {path}: {e}")
            raise

    def load_json(self, path: Path) -> nx.DiGraph:
        """
        Load graph from JSON format.

        Args:
            path: Path to JSON file

        Returns:
            Loaded NetworkX graph
        """
        if not path.exists():
            logger.warning(f"Graph JSON file not found: {path}, returning empty graph")
            return nx.DiGraph()

        try:
            with open(path, "r") as f:
                graph_data = json.load(f)

            # Convert from node-link format back to graph
            graph = json_graph.node_link_graph(graph_data, directed=True)

            logger.info(
                f"Loaded graph from JSON {path} "
                f"({graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges)"
            )
            return graph
        except Exception as e:
            logger.error(f"Failed to load graph from JSON {path}: {e}")
            raise

    def export_graphml(self, graph: nx.DiGraph, path: Path) -> None:
        """
        Export graph to GraphML format (for visualization tools).

        Note: Converts Enum values to strings for GraphML compatibility.

        Args:
            graph: NetworkX graph
            path: Path to save GraphML file
        """
        try:
            # Create a copy and convert enums to strings, remove None values for GraphML
            graph_copy = graph.copy()
            for node_id, data in graph_copy.nodes(data=True):
                keys_to_remove = []
                for key, value in list(data.items()):
                    if value is None:
                        keys_to_remove.append(key)
                    elif hasattr(value, 'value'):  # Check if it's an Enum
                        data[key] = str(value.value)
                for key in keys_to_remove:
                    del data[key]

            for u, v, data in graph_copy.edges(data=True):
                keys_to_remove = []
                for key, value in list(data.items()):
                    if value is None:
                        keys_to_remove.append(key)
                    elif hasattr(value, 'value'):  # Check if it's an Enum
                        data[key] = str(value.value)
                for key in keys_to_remove:
                    del data[key]

            nx.write_graphml(graph_copy, path)
            logger.info(f"Exported graph to GraphML: {path}")
        except Exception as e:
            logger.error(f"Failed to export graph to GraphML {path}: {e}")
            raise

    def get_storage_info(self) -> dict[str, Any]:
        """Get information about stored graphs."""
        info: dict[str, Any] = {"storage_path": str(self.storage_path), "exists": False}

        if self.storage_path.exists():
            info["exists"] = True
            info["size_bytes"] = self.storage_path.stat().st_size
            info["size_mb"] = round(self.storage_path.stat().st_size / (1024 * 1024), 2)
            info["modified"] = self.storage_path.stat().st_mtime

        return info


# Convenience functions
def save_graph(graph: nx.DiGraph, path: Path | None = None) -> None:
    """
    Save graph to default location (pickle format).

    Args:
        graph: NetworkX graph
        path: Optional path override
    """
    storage = GraphStorage()
    storage.save_pickle(graph, path)


def load_graph(path: Path | None = None) -> nx.DiGraph:
    """
    Load graph from default location (pickle format).

    Args:
        path: Optional path override

    Returns:
        NetworkX graph
    """
    storage = GraphStorage()
    return storage.load_pickle(path)
