"""Parsers for various document formats.

This module provides parsers for different document types (SSIS, Excel, Mainframe, etc.)
that all implement the BaseParser interface and produce ParsedDocument outputs.
"""

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
    ParserRegistry,
    parser_registry,
)
from enterprise_assistant.parsers.ssis_parser import SSISParser, parse_ssis
from enterprise_assistant.parsers.cobol_parser import COBOLParser
from enterprise_assistant.parsers.jcl_parser import JCLParser

# Register parsers
parser_registry.register(SSISParser())
parser_registry.register(COBOLParser())
parser_registry.register(JCLParser())

__all__ = [
    # Base classes
    "BaseParser",
    "ParsedDocument",
    "DocumentType",
    "DocumentMetadata",
    "Component",
    "DataSource",
    "Parameter",
    "DataEntity",
    "Dependency",
    "ParserRegistry",
    "parser_registry",
    # Parsers
    "SSISParser",
    "parse_ssis",
    "COBOLParser",
    "JCLParser",
]
