"""Abstract base classes for multi-format parsing.

This module provides the foundation for parsing different document formats
(SSIS, Excel, Mainframe, JSON, etc.) into a common graph representation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class DocumentType(str, Enum):
    """Types of documents that can be parsed."""

    SSIS_PACKAGE = "ssis_package"
    EXCEL_WORKBOOK = "excel_workbook"
    MAINFRAME_JOB = "mainframe_job"
    MAINFRAME_JCL = "mainframe_jcl"
    COBOL_PROGRAM = "cobol_program"
    JSON_CONFIG = "json_config"
    PYTHON_SCRIPT = "python_script"
    SQL_SCRIPT = "sql_script"


@dataclass
class DocumentMetadata:
    """Base metadata for any parsed document."""

    name: str
    document_id: str
    document_type: DocumentType
    description: Optional[str] = None
    version: Optional[str] = None
    creator: Optional[str] = None
    created_date: Optional[str] = None
    modified_date: Optional[str] = None
    file_path: Optional[Path] = None
    custom_attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class Component:
    """Base class for document components (tasks, steps, formulas, etc.)."""

    name: str
    component_id: str
    component_type: str
    description: Optional[str] = None
    source_code: Optional[str] = None  # SQL, formula, script, etc.
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class DataSource:
    """Base class for data sources (connections, files, datasets, etc.)."""

    name: str
    source_id: str
    source_type: str
    connection_string: Optional[str] = None
    server: Optional[str] = None
    database: Optional[str] = None
    file_path: Optional[str] = None
    description: Optional[str] = None
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class Parameter:
    """Base class for parameters (variables, named ranges, env vars, etc.)."""

    name: str
    namespace: Optional[str] = None
    data_type: Optional[str] = None
    value: Any = None
    description: Optional[str] = None
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class DataEntity:
    """Base class for data entities (tables, sheets, datasets, files)."""

    name: str
    entity_type: str  # table, sheet, dataset, file, etc.
    schema_name: Optional[str] = None
    database_name: Optional[str] = None
    description: Optional[str] = None
    columns: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class Dependency:
    """Represents a dependency/relationship between components."""

    from_id: str
    to_id: str
    dependency_type: str  # executes_before, reads_from, writes_to, etc.
    condition: Optional[str] = None  # success, failure, always, etc.
    description: Optional[str] = None
    expression: Optional[str] = None
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedDocument:
    """
    Universal parsed document structure.

    This is the common output format for all parsers, regardless of source.
    """

    metadata: DocumentMetadata
    components: list[Component] = field(default_factory=list)
    data_sources: list[DataSource] = field(default_factory=list)
    parameters: list[Parameter] = field(default_factory=list)
    data_entities: list[DataEntity] = field(default_factory=list)
    dependencies: list[Dependency] = field(default_factory=list)


class BaseParser(ABC):
    """Abstract base parser for all document formats."""

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions."""
        pass

    @property
    @abstractmethod
    def document_type(self) -> DocumentType:
        """Return the document type this parser handles."""
        pass

    @abstractmethod
    def parse(self, file_path: Path) -> ParsedDocument:
        """
        Parse a file into a ParsedDocument.

        Args:
            file_path: Path to the file to parse

        Returns:
            ParsedDocument with extracted information

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        pass

    @abstractmethod
    def validate(self, file_path: Path) -> bool:
        """
        Validate if a file can be parsed by this parser.

        Args:
            file_path: Path to validate

        Returns:
            True if file can be parsed, False otherwise
        """
        pass

    def extract_data_entities(self, component: Component) -> list[DataEntity]:
        """
        Extract data entities (tables, files, etc.) from component source code.

        Override this in subclasses to implement format-specific extraction.

        Args:
            component: Component to analyze

        Returns:
            List of extracted data entities
        """
        return []


class ParserRegistry:
    """Registry for managing multiple parsers."""

    def __init__(self) -> None:
        """Initialize parser registry."""
        self._parsers: dict[DocumentType, BaseParser] = {}

    def register(self, parser: BaseParser) -> None:
        """
        Register a parser.

        Args:
            parser: Parser instance to register
        """
        self._parsers[parser.document_type] = parser

    def get_parser(self, document_type: DocumentType) -> BaseParser:
        """
        Get parser for a document type.

        Args:
            document_type: Type of document

        Returns:
            Parser instance

        Raises:
            ValueError: If no parser registered for type
        """
        if document_type not in self._parsers:
            raise ValueError(f"No parser registered for {document_type}")
        return self._parsers[document_type]

    def get_parser_for_file(self, file_path: Path) -> BaseParser:
        """
        Get appropriate parser for a file based on extension.

        Args:
            file_path: Path to file

        Returns:
            Parser instance

        Raises:
            ValueError: If no parser can handle the file
        """
        extension = file_path.suffix.lower()

        for parser in self._parsers.values():
            if extension in parser.supported_extensions:
                return parser

        raise ValueError(f"No parser available for extension: {extension}")

    def list_supported_formats(self) -> dict[str, list[str]]:
        """
        List all supported formats and their extensions.

        Returns:
            Dict mapping document type to extensions
        """
        return {
            parser.document_type.value: parser.supported_extensions
            for parser in self._parsers.values()
        }


# Global registry instance
parser_registry = ParserRegistry()
