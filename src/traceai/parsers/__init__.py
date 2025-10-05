"""Parsers for various document formats.

This module provides parsers for different document types (SSIS, Excel, Mainframe, etc.)
that all implement the BaseParser interface and produce ParsedDocument outputs.
"""

from traceai.parsers.base import (
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
from traceai.parsers.ssis_parser import SSISParser, parse_ssis
from traceai.parsers.cobol_parser import COBOLParser
from traceai.parsers.jcl_parser import JCLParser
from traceai.parsers.json_parser import JSONParser
from traceai.parsers.excel_parser import ExcelParser
from traceai.parsers.csv_parser import CSVParser

# Register parsers
parser_registry.register(SSISParser())
parser_registry.register(COBOLParser())
parser_registry.register(JCLParser())
parser_registry.register(JSONParser())
parser_registry.register(ExcelParser())
parser_registry.register(CSVParser())

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
    "JSONParser",
    "ExcelParser",
    "CSVParser",
]
