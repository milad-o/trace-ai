"""Graph builder for converting parsed documents to NetworkX knowledge graph.

This module is format-agnostic and works with any ParsedDocument from any parser
(SSIS, Excel, Mainframe, JSON, etc.).
"""

import re
from pathlib import Path
from typing import Any

import networkx as nx

from traceai.graph.schema import (
    ConnectionNode,
    EdgeAttributes,
    EdgeType,
    NodeType,
    PackageNode,
    TableNode,
    TaskNode,
    VariableNode,
    create_node_id,
)
from traceai.logger import logger
from traceai.parsers.base import ParsedDocument


class KnowledgeGraphBuilder:
    """Build a NetworkX knowledge graph from parsed documents (format-agnostic)."""

    def __init__(self) -> None:
        """Initialize the graph builder."""
        self.graph = nx.DiGraph()  # Directed graph for relationships

    def add_document(self, parsed_document: ParsedDocument) -> str:
        """
        Add a parsed document to the knowledge graph.

        Works with any document type: SSIS packages, Excel workbooks, Mainframe jobs, etc.

        Args:
            parsed_document: Parsed document data

        Returns:
            Document node ID
        """
        # Backward compatibility: Check if this is an old ParsedPackage
        if not isinstance(parsed_document, ParsedDocument):
            # Convert old ParsedPackage to ParsedDocument
            parsed_document = self._convert_legacy_package(parsed_document)

        metadata = parsed_document.metadata

        # Create document node (package node for now, can be extended)
        document_id = create_node_id(NodeType.PACKAGE, metadata.document_id)

        # Parse version if available (format: "major.minor")
        version_major = None
        version_minor = None
        if metadata.version:
            parts = metadata.version.split(".")
            if len(parts) >= 1:
                version_major = int(parts[0]) if parts[0].isdigit() else None
            if len(parts) >= 2:
                version_minor = int(parts[1]) if parts[1].isdigit() else None

        document_attrs = PackageNode(
            id=document_id,
            name=metadata.name,
            description=metadata.description,
            version_major=version_major,
            version_minor=version_minor,
            creator_name=metadata.creator,
            creation_date=metadata.created_date,
            file_path=str(metadata.file_path) if metadata.file_path else None,
        )

        self.graph.add_node(document_id, **document_attrs.__dict__)

        # Add data sources (connections, files, etc.)
        # Create ID map for dependencies (includes both components and data sources)
        id_map = {}  # Map original IDs to graph node IDs

        for data_source in parsed_document.data_sources:
            source_id = self._add_data_source(data_source, document_id)
            # Map data source ID for dependency resolution
            id_map[data_source.source_id] = source_id
            # Create CONTAINS edge from document to data source
            self._add_edge(
                document_id, source_id, EdgeType.CONTAINS, f"Document contains {data_source.source_type}"
            )

        # Add parameters (variables, named ranges, env vars, etc.)
        for param in parsed_document.parameters:
            param_id = self._add_parameter(param, document_id)
            # Create CONTAINS edge from document to parameter
            self._add_edge(document_id, param_id, EdgeType.CONTAINS, "Document contains Parameter")

        # Add components (tasks, steps, formulas, etc.)
        for component in parsed_document.components:
            component_node_id = self._add_component(component, document_id)
            # Map component ID for dependency resolution
            id_map[component.component_id] = component_node_id

            # Create CONTAINS edge from document to component
            self._add_edge(document_id, component_node_id, EdgeType.CONTAINS, "Document contains Component")

            # Extract and link data entities (tables, sheets, files, etc.) from source code
            if component.source_code:
                self._extract_and_link_entities(component.source_code, component_node_id)

        # Add data entities that were already extracted
        for entity in parsed_document.data_entities:
            entity_id = self._get_or_create_entity_node(entity.name, entity.schema_name)
            # Map entity name for dependency resolution
            id_map[entity.name] = entity_id

        # Add dependencies (precedence constraints, references, etc.)
        for dep in parsed_document.dependencies:
            from_node_id = id_map.get(dep.from_id)
            to_node_id = id_map.get(dep.to_id)

            if from_node_id and to_node_id:
                # Map dependency type to edge type
                edge_type_map = {
                    "PRECEDES": EdgeType.PRECEDES,
                    "READS_FROM": EdgeType.READS_FROM,
                    "WRITES_TO": EdgeType.WRITES_TO,
                    "DEPENDS_ON": EdgeType.DEPENDS_ON,
                }
                edge_type = edge_type_map.get(dep.dependency_type, EdgeType.PRECEDES)

                edge_attrs = EdgeAttributes(
                    edge_type=edge_type,
                    constraint_type=dep.condition,
                    expression=dep.expression,
                )
                self.graph.add_edge(from_node_id, to_node_id, **edge_attrs.__dict__)

        logger.info(
            f"Added document '{metadata.name}' ({metadata.document_type}) to graph: "
            f"{len(parsed_document.data_sources)} data sources, "
            f"{len(parsed_document.parameters)} parameters, "
            f"{len(parsed_document.components)} components, "
            f"{len(parsed_document.data_entities)} data entities, "
            f"{len(parsed_document.dependencies)} dependencies"
        )

        return document_id

    def _add_data_source(self, data_source: Any, document_id: str) -> str:
        """Add a data source node to the graph (connection, file, dataset, etc.)."""
        # Datasets, files, and tables should be TABLE nodes (data entities)
        # Actual connections (OLEDB, ODBC) should be CONNECTION nodes
        if data_source.source_type in ["FILE", "DATABASE", "TAPE", "DATASET"]:
            # This is a data entity (table, file, dataset)
            source_id = create_node_id(NodeType.TABLE, data_source.source_id)

            source_attrs = TableNode(
                id=source_id,
                name=data_source.name,
                schema_name=None,  # Mainframe datasets don't have schemas
                database_name=data_source.database if data_source.database else None,
                server_name=data_source.server if data_source.server else None,
            )
        else:
            # This is an actual connection (OLEDB, ODBC, etc.)
            source_id = create_node_id(NodeType.CONNECTION, data_source.source_id)

            source_attrs = ConnectionNode(
                id=source_id,
                name=data_source.name,
                connection_type=data_source.source_type,
                server_name=data_source.server,
                database_name=data_source.database,
                connection_string=data_source.connection_string,
                description=data_source.description,
            )

        self.graph.add_node(source_id, **source_attrs.__dict__)
        return source_id

    def _add_parameter(self, parameter: Any, document_id: str) -> str:
        """Add a parameter node to the graph (variable, named range, env var, etc.)."""
        namespace = parameter.namespace or "default"
        param_id = create_node_id(
            NodeType.VARIABLE, f"{document_id}:{namespace}:{parameter.name}"
        )

        param_attrs = VariableNode(
            id=param_id,
            name=parameter.name,
            namespace=namespace,
            data_type=parameter.data_type,
            value=parameter.value,
            description=parameter.description,
        )

        self.graph.add_node(param_id, **param_attrs.__dict__)
        return param_id

    def _add_component(self, component: Any, document_id: str) -> str:
        """Add a component node to the graph (task, step, formula, etc.)."""
        component_node_id = create_node_id(NodeType.TASK, component.component_id)

        component_attrs = TaskNode(
            id=component_node_id,
            name=component.name,
            task_type=component.component_type,
            description=component.description,
            sql_statement=component.source_code,
        )

        self.graph.add_node(component_node_id, **component_attrs.__dict__)
        return component_node_id

    def _extract_and_link_entities(self, source_code: str, component_node_id: str) -> None:
        """
        Extract data entity references from source code and create entity nodes + relationships.

        Works with SQL, Excel formulas, or other code types.

        Args:
            source_code: Source code to parse (SQL, formula, script, etc.)
            component_node_id: Component node that contains this source code
        """
        # For now, only handle SQL-based extraction
        # Future: Add Excel formula parsing, JSON path extraction, etc.
        if not any(keyword in source_code.upper() for keyword in ["SELECT", "FROM", "INSERT", "UPDATE", "MERGE", "DELETE"]):
            return  # Not SQL, skip for now

        # SQL table extraction patterns
        patterns = [
            r"FROM\s+([a-zA-Z_][\w\.]*)",  # FROM table
            r"JOIN\s+([a-zA-Z_][\w\.]*)",  # JOIN table
            r"INTO\s+([a-zA-Z_][\w\.]*)",  # INSERT INTO table
            r"UPDATE\s+([a-zA-Z_][\w\.]*)",  # UPDATE table
            r"MERGE\s+([a-zA-Z_][\w\.]*)",  # MERGE table
            r"DELETE\s+FROM\s+([a-zA-Z_][\w\.]*)",  # DELETE FROM table
        ]

        entities_read = set()
        entities_written = set()

        source_upper = source_code.upper()

        # Extract entities being read
        if any(keyword in source_upper for keyword in ["SELECT", "FROM", "JOIN"]):
            for pattern in patterns[:2]:  # FROM and JOIN patterns
                matches = re.finditer(pattern, source_code, re.IGNORECASE)
                for match in matches:
                    entity_name = match.group(1).strip()
                    entities_read.add(entity_name)

        # Extract entities being written
        if any(keyword in source_upper for keyword in ["INSERT", "UPDATE", "MERGE", "DELETE"]):
            for pattern in patterns[2:]:  # INSERT, UPDATE, MERGE, DELETE patterns
                matches = re.finditer(pattern, source_code, re.IGNORECASE)
                for match in matches:
                    entity_name = match.group(1).strip()
                    entities_written.add(entity_name)

        # Special case: MERGE reads from source and writes to target
        if "MERGE" in source_upper:
            # MERGE target USING source pattern
            merge_pattern = r"MERGE\s+([a-zA-Z_][\w\.]*)\s+.*?USING\s+([a-zA-Z_][\w\.]*)"
            merge_matches = re.search(merge_pattern, source_code, re.IGNORECASE)
            if merge_matches:
                target_entity = merge_matches.group(1).strip()
                source_entity = merge_matches.group(2).strip()
                entities_written.add(target_entity)
                entities_read.add(source_entity)

        # Create entity nodes and relationships
        for entity_name in entities_read:
            entity_id = self._get_or_create_entity_node(entity_name)
            self._add_edge(
                component_node_id, entity_id, EdgeType.READS_FROM, f"Component reads from {entity_name}"
            )

        for entity_name in entities_written:
            entity_id = self._get_or_create_entity_node(entity_name)
            self._add_edge(
                component_node_id, entity_id, EdgeType.WRITES_TO, f"Component writes to {entity_name}"
            )

    def _get_or_create_entity_node(self, entity_name: str, schema_name: str = None) -> str:
        """Get existing entity node or create new one (table, sheet, dataset, file, etc.)."""
        # Parse schema.entity or database.schema.entity format if schema not provided
        if not schema_name:
            parts = entity_name.split(".")
            actual_entity_name = entity_name

            if len(parts) == 2:
                schema_name = parts[0]
                actual_entity_name = parts[1]
            elif len(parts) == 3:
                # database.schema.entity
                schema_name = parts[1]
                actual_entity_name = parts[2]
            else:
                actual_entity_name = entity_name
        else:
            actual_entity_name = entity_name

        entity_id = create_node_id(NodeType.TABLE, entity_name)

        if not self.graph.has_node(entity_id):
            from traceai.graph.schema import TableNode

            entity_attrs = TableNode(
                id=entity_id, name=actual_entity_name, schema_name=schema_name
            )
            self.graph.add_node(entity_id, **entity_attrs.__dict__)

        return entity_id

    def _add_edge(self, from_id: str, to_id: str, edge_type: EdgeType, label: str = "") -> None:
        """Add an edge to the graph."""
        edge_attrs = EdgeAttributes(edge_type=edge_type)
        self.graph.add_edge(from_id, to_id, label=label, **edge_attrs.__dict__)

    def get_graph(self) -> nx.DiGraph:
        """Get the constructed graph."""
        return self.graph

    def get_stats(self) -> dict[str, int]:
        """Get graph statistics."""
        stats = {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
        }

        # Count nodes by type
        for node_type in NodeType:
            count = sum(
                1
                for _, data in self.graph.nodes(data=True)
                if data.get("node_type") == node_type
            )
            stats[f"{node_type.value.lower()}_nodes"] = count

        # Count edges by type
        for edge_type in EdgeType:
            count = sum(
                1
                for _, _, data in self.graph.edges(data=True)
                if data.get("edge_type") == edge_type
            )
            stats[f"{edge_type.value.lower()}_edges"] = count

        return stats

    def _convert_legacy_package(self, legacy_package: Any) -> ParsedDocument:
        """
        Convert old ParsedPackage format to new ParsedDocument format.

        This provides backward compatibility with existing code.

        Args:
            legacy_package: Old ParsedPackage object

        Returns:
            ParsedDocument with converted data
        """
        from traceai.parsers.base import (
            Component,
            DataSource,
            Dependency,
            DocumentMetadata,
            DocumentType,
            Parameter,
        )

        # Convert metadata
        old_meta = legacy_package.metadata
        version = None
        if old_meta.version_major is not None:
            version = f"{old_meta.version_major}.{old_meta.version_minor or 0}"

        metadata = DocumentMetadata(
            name=old_meta.name,
            document_id=old_meta.package_id,
            document_type=DocumentType.SSIS_PACKAGE,
            description=old_meta.description,
            version=version,
            creator=old_meta.creator_name,
            created_date=old_meta.creation_date,
            file_path=old_meta.file_path,
        )

        # Convert connections to data sources
        data_sources = [
            DataSource(
                name=conn.name,
                source_id=conn.connection_id,
                source_type=conn.connection_type,
                connection_string=conn.connection_string,
                server=conn.server_name,
                database=conn.database_name,
                description=conn.description,
            )
            for conn in legacy_package.connections
        ]

        # Convert variables to parameters
        parameters = [
            Parameter(
                name=var.name,
                namespace=var.namespace,
                data_type=var.data_type,
                value=var.value,
                description=var.description,
            )
            for var in legacy_package.variables
        ]

        # Convert tasks to components
        components = [
            Component(
                name=task.name,
                component_id=task.task_id,
                component_type=task.task_type,
                description=task.description,
                source_code=task.sql_statement,
                properties=task.properties,
            )
            for task in legacy_package.tasks
        ]

        # Convert precedence constraints to dependencies
        dependencies = [
            Dependency(
                from_id=pc.from_task,
                to_id=pc.to_task,
                dependency_type="executes_before",
                condition=pc.constraint_type.lower() if pc.constraint_type else "success",
                expression=pc.expression,
            )
            for pc in legacy_package.precedence_constraints
        ]

        return ParsedDocument(
            metadata=metadata,
            data_sources=data_sources,
            parameters=parameters,
            components=components,
            dependencies=dependencies,
        )


def build_graph_from_documents(documents: list[ParsedDocument]) -> nx.DiGraph:
    """
    Build a knowledge graph from multiple parsed documents.

    Works with any document type: SSIS packages, Excel workbooks, Mainframe jobs, etc.

    Args:
        documents: List of parsed documents

    Returns:
        NetworkX directed graph
    """
    builder = KnowledgeGraphBuilder()

    for document in documents:
        builder.add_document(document)

    stats = builder.get_stats()
    logger.info(f"Built knowledge graph with {stats['total_nodes']} nodes and {stats['total_edges']} edges")

    return builder.get_graph()


# Backward compatibility alias for SSIS-specific code
def build_graph_from_packages(packages: list[ParsedDocument]) -> nx.DiGraph:
    """
    Legacy function for backward compatibility.

    Args:
        packages: List of parsed documents (previously SSIS packages)

    Returns:
        NetworkX directed graph
    """
    return build_graph_from_documents(packages)
