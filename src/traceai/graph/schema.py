"""Knowledge graph schema definitions for SSIS packages.

This module defines the node types, edge types, and attributes used in the
NetworkX knowledge graph.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    """Node types in the knowledge graph."""

    PACKAGE = "Package"
    CONNECTION = "Connection"
    VARIABLE = "Variable"
    TASK = "Task"
    TABLE = "Table"
    COLUMN = "Column"


class EdgeType(str, Enum):
    """Edge types (relationships) in the knowledge graph."""

    CONTAINS = "CONTAINS"  # Package contains Tasks/Variables/Connections
    USES_CONNECTION = "USES_CONNECTION"  # Task uses Connection
    READS_FROM = "READS_FROM"  # Task reads from Table
    WRITES_TO = "WRITES_TO"  # Task writes to Table
    PRECEDES = "PRECEDES"  # Task precedes another Task (execution order)
    DEPENDS_ON = "DEPENDS_ON"  # Package depends on another Package
    HAS_COLUMN = "HAS_COLUMN"  # Table has Column
    TRANSFORMS = "TRANSFORMS"  # Task transforms Column


@dataclass
class NodeAttributes:
    """Base attributes for all nodes."""

    id: str
    name: str
    node_type: NodeType


@dataclass
class PackageNode:
    """Package node attributes."""

    id: str
    name: str
    node_type: NodeType = NodeType.PACKAGE
    description: str | None = None
    version_major: int | None = None
    version_minor: int | None = None
    creator_name: str | None = None
    creation_date: str | None = None
    file_path: str | None = None
    document_type: str | None = None


@dataclass
class ConnectionNode:
    """Connection manager node attributes."""

    id: str
    name: str
    node_type: NodeType = NodeType.CONNECTION
    connection_type: str | None = None
    server_name: str | None = None
    database_name: str | None = None
    connection_string: str | None = None
    description: str | None = None


@dataclass
class VariableNode:
    """Variable node attributes."""

    id: str
    name: str
    node_type: NodeType = NodeType.VARIABLE
    namespace: str | None = None
    data_type: str | None = None
    value: Any | None = None
    description: str | None = None


@dataclass
class TaskNode:
    """Task (executable) node attributes."""

    id: str
    name: str
    node_type: NodeType = NodeType.TASK
    task_type: str | None = None
    description: str | None = None
    sql_statement: str | None = None


@dataclass
class TableNode:
    """Database table node attributes."""

    id: str
    name: str
    node_type: NodeType = NodeType.TABLE
    schema_name: str | None = None
    database_name: str | None = None
    server_name: str | None = None


@dataclass
class ColumnNode:
    """Table column node attributes."""

    id: str
    name: str
    node_type: NodeType = NodeType.COLUMN
    data_type: str | None = None
    nullable: bool | None = None


@dataclass
class EdgeAttributes:
    """Edge (relationship) attributes."""

    edge_type: EdgeType
    constraint_type: str | None = None  # For PRECEDES: Success/Failure/Completion
    expression: str | None = None  # For conditional relationships


def create_node_id(node_type: NodeType, identifier: str) -> str:
    """
    Create a unique node ID.

    Args:
        node_type: Type of node
        identifier: Unique identifier (e.g., package name, task ID)

    Returns:
        Formatted node ID
    """
    return f"{node_type.value}:{identifier}"


def parse_node_id(node_id: str) -> tuple[NodeType, str]:
    """
    Parse a node ID into type and identifier.

    Args:
        node_id: Node ID to parse

    Returns:
        Tuple of (node_type, identifier)
    """
    node_type_str, identifier = node_id.split(":", 1)
    return NodeType(node_type_str), identifier
