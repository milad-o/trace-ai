"""SSIS DTSX package parser implementing the BaseParser interface.

This module parses SSIS .dtsx XML files and converts them into the universal
ParsedDocument format for multi-format compatibility.
"""

import re
from pathlib import Path
from typing import Any

from lxml import etree

from enterprise_assistant.logger import logger
from enterprise_assistant.parsers.base import (
    BaseParser,
    Component,
    DataEntity,
    DataSource,
    Dependency,
    DocumentMetadata,
    DocumentType,
    Parameter,
    ParsedDocument,
)


# DTSX XML Namespaces
class DTSXNamespaces:
    """DTSX XML namespace definitions."""

    DTS = "www.microsoft.com/SqlServer/Dts"
    SQL_TASK = "www.microsoft.com/sqlserver/dts/tasks/sqltask"
    PIPELINE = "www.microsoft.com/SqlServer/Dts/Pipeline"
    DESIGN = "www.microsoft.com/SqlServer/Dts/Design"

    @classmethod
    def get_prefix(cls, namespace: str) -> str:
        """Get namespace prefix for XPath queries."""
        return f"{{{namespace}}}"

    @classmethod
    def get_nsmap(cls) -> dict[str, str]:
        """Get namespace mapping for XPath queries."""
        return {
            "DTS": cls.DTS,
            "SQLTask": cls.SQL_TASK,
            "pipeline": cls.PIPELINE,
            "design": cls.DESIGN,
        }


class SSISParser(BaseParser):
    """Parser for SSIS DTSX files implementing the BaseParser interface."""

    def __init__(self) -> None:
        """Initialize parser."""
        self.nsmap = DTSXNamespaces.get_nsmap()
        self.dts_prefix = DTSXNamespaces.get_prefix(DTSXNamespaces.DTS)

    @property
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions."""
        return [".dtsx"]

    @property
    def document_type(self) -> DocumentType:
        """Return the document type this parser handles."""
        return DocumentType.SSIS_PACKAGE

    def validate(self, file_path: Path) -> bool:
        """
        Validate if a file can be parsed by this parser.

        Args:
            file_path: Path to validate

        Returns:
            True if file can be parsed, False otherwise
        """
        if not file_path.exists():
            return False

        if file_path.suffix.lower() not in self.supported_extensions:
            return False

        try:
            # Try to parse as XML and check for SSIS namespace
            tree = etree.parse(str(file_path))
            root = tree.getroot()

            # Check if it has DTS namespace
            if DTSXNamespaces.DTS in str(etree.tostring(root)[:500]):
                return True

            return False
        except (etree.ParseError, OSError):
            return False

    def parse(self, file_path: Path) -> ParsedDocument:
        """
        Parse a DTSX file into a ParsedDocument.

        Args:
            file_path: Path to the .dtsx file to parse

        Returns:
            ParsedDocument with extracted information

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        if not file_path.exists():
            raise FileNotFoundError(f"DTSX file not found: {file_path}")

        logger.info(f"Parsing SSIS package: {file_path}")

        try:
            tree = etree.parse(str(file_path))
            root = tree.getroot()

            # Extract metadata
            metadata = self._extract_metadata(root, file_path)

            # Extract connections
            data_sources = self._extract_connections(root)

            # Extract variables
            parameters = self._extract_variables(root)

            # Extract tasks (components)
            components = self._extract_tasks(root)

            # Extract precedence constraints (dependencies)
            dependencies = self._extract_precedence_constraints(root)

            # Extract data entities (tables) from SQL statements
            data_entities = self._extract_data_entities_from_components(components)

            parsed = ParsedDocument(
                metadata=metadata,
                data_sources=data_sources,
                parameters=parameters,
                components=components,
                data_entities=data_entities,
                dependencies=dependencies,
            )

            logger.info(
                f"Parsed {file_path.name}: "
                f"{len(data_sources)} data sources, "
                f"{len(parameters)} parameters, "
                f"{len(components)} components, "
                f"{len(data_entities)} data entities, "
                f"{len(dependencies)} dependencies"
            )

            return parsed

        except etree.ParseError as e:
            logger.error(f"Failed to parse DTSX file {file_path}: {e}")
            raise ValueError(f"Invalid DTSX XML format: {e}")

    def _extract_metadata(self, root: etree._Element, file_path: Path) -> DocumentMetadata:
        """Extract package-level metadata."""
        package_elem = root

        name = package_elem.get(f"{self.dts_prefix}ObjectName", file_path.stem)
        package_id = package_elem.get(f"{self.dts_prefix}DTSID", "")
        description = package_elem.get(f"{self.dts_prefix}Description")
        creator = package_elem.get(f"{self.dts_prefix}CreatorName")
        created_date = package_elem.get(f"{self.dts_prefix}CreationDate")

        version_major_str = package_elem.get(f"{self.dts_prefix}VersionMajor")
        version_minor_str = package_elem.get(f"{self.dts_prefix}VersionMinor")

        version = None
        if version_major_str and version_minor_str:
            version = f"{version_major_str}.{version_minor_str}"

        return DocumentMetadata(
            name=name,
            document_id=package_id,
            document_type=self.document_type,
            description=description,
            version=version,
            creator=creator,
            created_date=created_date,
            file_path=file_path,
        )

    def _extract_connections(self, root: etree._Element) -> list[DataSource]:
        """Extract connection managers as data sources."""
        data_sources = []

        # Find all DTS:ConnectionManager elements
        conn_elements = root.xpath("./DTS:ConnectionManagers/DTS:ConnectionManager", namespaces=self.nsmap)

        for conn_elem in conn_elements:
            name = conn_elem.get(f"{self.dts_prefix}ObjectName", "")
            conn_id = conn_elem.get(f"{self.dts_prefix}DTSID", "")
            conn_type = conn_elem.get(f"{self.dts_prefix}CreationName", "")
            description = conn_elem.get(f"{self.dts_prefix}Description")

            # Extract connection string from DTS:ObjectData
            conn_string = None
            server = None
            database = None

            obj_data = conn_elem.find("DTS:ObjectData", namespaces=self.nsmap)
            if obj_data is not None:
                # Connection string might be on DTS:ObjectData itself or nested DTS:ConnectionManager
                conn_string = obj_data.get("ConnectionString")

                # If not found, check nested ConnectionManager element
                if not conn_string:
                    nested_conn = obj_data.find("DTS:ConnectionManager", namespaces=self.nsmap)
                    if nested_conn is not None:
                        conn_string = nested_conn.get("ConnectionString")

                # Try to parse server and database from connection string
                if conn_string:
                    if "Data Source=" in conn_string or "Server=" in conn_string:
                        parts = conn_string.split(";")
                        for part in parts:
                            if part.strip().startswith("Data Source=") or part.strip().startswith("Server="):
                                server = part.split("=", 1)[1].strip()
                            elif part.strip().startswith("Initial Catalog=") or part.strip().startswith("Database="):
                                database = part.split("=", 1)[1].strip()

            data_sources.append(
                DataSource(
                    name=name,
                    source_id=conn_id,
                    source_type=conn_type,
                    connection_string=conn_string,
                    server=server,
                    database=database,
                    description=description,
                )
            )

        return data_sources

    def _extract_variables(self, root: etree._Element) -> list[Parameter]:
        """Extract package variables as parameters."""
        parameters = []

        # Find all DTS:Variable elements using namespace-aware XPath
        var_elements = root.xpath(".//DTS:Variable", namespaces=self.nsmap)

        for var_elem in var_elements:
            name = var_elem.get(f"{self.dts_prefix}ObjectName", "")
            namespace = var_elem.get(f"{self.dts_prefix}Namespace", "User")
            data_type = var_elem.get(f"{self.dts_prefix}DataType", "")
            description = var_elem.get(f"{self.dts_prefix}Description")

            # Extract variable value from DTS:VariableValue
            value = None
            var_value_elem = var_elem.find(f"{self.dts_prefix}VariableValue", namespaces=self.nsmap)
            if var_value_elem is not None:
                value = var_value_elem.text

            parameters.append(
                Parameter(
                    name=name,
                    namespace=namespace,
                    data_type=data_type,
                    value=value,
                    description=description,
                )
            )

        return parameters

    def _extract_tasks(self, root: etree._Element) -> list[Component]:
        """Extract executable tasks as components."""
        components = []

        # Find all DTS:Executable elements using namespace-aware XPath
        exec_elements = root.xpath(".//DTS:Executable", namespaces=self.nsmap)

        for exec_elem in exec_elements:
            name = exec_elem.get(f"{self.dts_prefix}ObjectName", "")
            task_id = exec_elem.get(f"{self.dts_prefix}DTSID", "")
            task_type = exec_elem.get(f"{self.dts_prefix}ExecutableType", "")
            description = exec_elem.get(f"{self.dts_prefix}Description")

            # Extract SQL statement for SQL tasks
            sql_statement = None
            sql_task_data_list = exec_elem.xpath(
                ".//SQLTask:SqlTaskData",
                namespaces=self.nsmap,
            )
            if sql_task_data_list:
                sql_task_data = sql_task_data_list[0]
                sql_statement = (
                    sql_task_data.get(f"{DTSXNamespaces.get_prefix(DTSXNamespaces.SQL_TASK)}SqlStatementSource")
                    or sql_task_data.get("SqlStatementSource")
                )

            # Store additional properties
            properties: dict[str, Any] = {}
            if task_type:
                properties["task_type"] = task_type

            components.append(
                Component(
                    name=name,
                    component_id=task_id,
                    component_type=task_type or "Unknown",
                    description=description,
                    source_code=sql_statement,
                    properties=properties,
                )
            )

        return components

    def _extract_precedence_constraints(self, root: etree._Element) -> list[Dependency]:
        """Extract precedence constraints as dependencies."""
        dependencies = []

        # Find all DTS:PrecedenceConstraint elements using namespace-aware XPath
        pc_elements = root.xpath(".//DTS:PrecedenceConstraint", namespaces=self.nsmap)

        for pc_elem in pc_elements:
            from_task = pc_elem.get(f"{self.dts_prefix}From", "")
            to_task = pc_elem.get(f"{self.dts_prefix}To", "")
            value = pc_elem.get(f"{self.dts_prefix}Value", "")
            expression = pc_elem.get(f"{self.dts_prefix}Expression")

            # Map constraint type
            condition = "success"  # Default
            if value == "1":
                condition = "success"
            elif value == "2":
                condition = "failure"
            elif value == "3":
                condition = "completion"

            dependencies.append(
                Dependency(
                    from_id=from_task,
                    to_id=to_task,
                    dependency_type="executes_before",
                    condition=condition,
                    expression=expression,
                )
            )

        return dependencies

    def _extract_data_entities_from_components(self, components: list[Component]) -> list[DataEntity]:
        """Extract data entities (tables) from all components."""
        all_entities = []
        seen_tables = set()

        for component in components:
            entities = self.extract_data_entities(component)
            for entity in entities:
                # Avoid duplicates
                if entity.name not in seen_tables:
                    seen_tables.add(entity.name)
                    all_entities.append(entity)

        return all_entities

    def extract_data_entities(self, component: Component) -> list[DataEntity]:
        """
        Extract data entities (tables) from SQL statements in component source code.

        Args:
            component: Component to analyze

        Returns:
            List of extracted data entities
        """
        if not component.source_code:
            return []

        entities = []
        sql = component.source_code

        # SQL table extraction patterns
        patterns = [
            r"FROM\s+([a-zA-Z_][\w\.]*)",  # FROM table
            r"JOIN\s+([a-zA-Z_][\w\.]*)",  # JOIN table
            r"INTO\s+([a-zA-Z_][\w\.]*)",  # INSERT INTO table
            r"UPDATE\s+([a-zA-Z_][\w\.]*)",  # UPDATE table
            r"MERGE\s+([a-zA-Z_][\w\.]*)",  # MERGE INTO table (target)
            r"TRUNCATE\s+TABLE\s+([a-zA-Z_][\w\.]*)",  # TRUNCATE TABLE
        ]

        for pattern in patterns:
            matches = re.findall(pattern, sql, re.IGNORECASE)
            for match in matches:
                table_name = match.strip()

                # Parse schema.table if present
                schema_name = None
                if "." in table_name:
                    parts = table_name.split(".")
                    schema_name = parts[0]
                    table_name = parts[1]

                entities.append(
                    DataEntity(
                        name=table_name,
                        entity_type="table",
                        schema_name=schema_name,
                        description=f"Extracted from {component.name}",
                    )
                )

        return entities


def parse_ssis(file_path: Path) -> ParsedDocument:
    """
    Parse an SSIS DTSX file into a ParsedDocument.

    Args:
        file_path: Path to .dtsx file

    Returns:
        ParsedDocument with all extracted entities

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid
    """
    parser = SSISParser()
    return parser.parse(file_path)
