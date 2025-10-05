"""Comprehensive tests for all parsers (JSON, CSV, Excel, COBOL, JCL)."""

from pathlib import Path

import pytest

from traceai.parsers import parser_registry
from traceai.parsers.json_parser import JSONParser
from traceai.parsers.csv_parser import CSVParser
from traceai.parsers.excel_parser import ExcelParser
from traceai.parsers.cobol_parser import COBOLParser
from traceai.parsers.jcl_parser import JCLParser


@pytest.fixture
def sample_json_file():
    """Path to sample JSON file."""
    return Path(__file__).parent.parent / "examples" / "inputs" / "json" / "sample_etl_config.json"


@pytest.fixture
def sample_csv_file():
    """Path to sample CSV file."""
    return Path(__file__).parent.parent / "examples" / "inputs" / "csv" / "sample_lineage_mapping.csv"


@pytest.fixture
def sample_excel_file():
    """Path to sample Excel file."""
    return Path(__file__).parent.parent / "examples" / "inputs" / "excel" / "sales_report.xlsx"


@pytest.fixture
def sample_cobol_file():
    """Path to sample COBOL file."""
    cobol_dir = Path(__file__).parent.parent / "examples" / "inputs" / "cobol"
    # Get first .cbl file
    files = list(cobol_dir.glob("*.cbl"))
    if files:
        return files[0]
    return cobol_dir / "CUST001.cbl"


@pytest.fixture
def sample_jcl_file():
    """Path to sample JCL file."""
    jcl_dir = Path(__file__).parent.parent / "examples" / "inputs" / "jcl"
    files = list(jcl_dir.glob("*.jcl"))
    if files:
        return files[0]
    return jcl_dir / "HELLO.jcl"


class TestJSONParser:
    """Test JSON parser functionality."""

    def test_parser_initialization(self):
        """Test JSON parser can be initialized."""
        parser = JSONParser()
        assert parser.supported_extensions == [".json", ".jsonc"]
        assert parser.document_type.value == "json_config"

    def test_parser_registration(self):
        """Test JSON parser is registered."""
        parser = parser_registry.get_parser_for_file(Path("test.json"))
        assert isinstance(parser, JSONParser)

    def test_parse_json_file(self, sample_json_file):
        """Test parsing a JSON file."""
        if not sample_json_file.exists():
            pytest.skip(f"Sample file not found: {sample_json_file}")

        parser = JSONParser()
        parsed = parser.parse(sample_json_file)

        assert parsed is not None
        assert parsed.metadata.document_type.value == "json_config"
        assert parsed.metadata.name
        assert parsed.metadata.file_path == sample_json_file

    def test_json_parser_extracts_components(self, sample_json_file):
        """Test JSON parser extracts components."""
        if not sample_json_file.exists():
            pytest.skip(f"Sample file not found: {sample_json_file}")

        parser = JSONParser()
        parsed = parser.parse(sample_json_file)

        # Should have some components or data entities
        assert len(parsed.components) + len(parsed.data_entities) > 0


class TestCSVParser:
    """Test CSV parser functionality."""

    def test_parser_initialization(self):
        """Test CSV parser can be initialized."""
        parser = CSVParser()
        assert parser.supported_extensions == [".csv"]
        assert parser.document_type.value == "csv_metadata"

    def test_parser_registration(self):
        """Test CSV parser is registered."""
        parser = parser_registry.get_parser_for_file(Path("test.csv"))
        assert isinstance(parser, CSVParser)

    def test_parse_csv_file(self, sample_csv_file):
        """Test parsing a CSV file."""
        if not sample_csv_file.exists():
            pytest.skip(f"Sample file not found: {sample_csv_file}")

        parser = CSVParser()
        parsed = parser.parse(sample_csv_file)

        assert parsed is not None
        assert parsed.metadata.document_type.value == "csv_metadata"
        assert parsed.metadata.name
        assert parsed.metadata.file_path == sample_csv_file

    def test_csv_parser_extracts_lineage(self, sample_csv_file):
        """Test CSV parser extracts lineage mappings."""
        if not sample_csv_file.exists():
            pytest.skip(f"Sample file not found: {sample_csv_file}")

        parser = CSVParser()
        parsed = parser.parse(sample_csv_file)

        # Should have dependencies or data entities
        assert len(parsed.dependencies) + len(parsed.data_entities) > 0


class TestExcelParser:
    """Test Excel parser functionality."""

    def test_parser_initialization(self):
        """Test Excel parser can be initialized."""
        parser = ExcelParser()
        assert parser.supported_extensions == [".xlsx", ".xlsm"]
        assert parser.document_type.value == "excel_workbook"

    def test_parser_registration(self):
        """Test Excel parser is registered."""
        parser = parser_registry.get_parser_for_file(Path("test.xlsx"))
        assert isinstance(parser, ExcelParser)

    def test_parse_excel_file(self, sample_excel_file):
        """Test parsing an Excel file."""
        if not sample_excel_file.exists():
            pytest.skip(f"Sample file not found: {sample_excel_file}")

        parser = ExcelParser()
        parsed = parser.parse(sample_excel_file)

        assert parsed is not None
        assert parsed.metadata.document_type.value == "excel_workbook"
        assert parsed.metadata.name
        assert parsed.metadata.file_path == sample_excel_file

    def test_excel_parser_extracts_sheets(self, sample_excel_file):
        """Test Excel parser extracts sheets as components."""
        if not sample_excel_file.exists():
            pytest.skip(f"Sample file not found: {sample_excel_file}")

        parser = ExcelParser()
        parsed = parser.parse(sample_excel_file)

        # Should have components for sheets
        assert len(parsed.components) > 0


class TestCOBOLParser:
    """Test COBOL parser functionality."""

    def test_parser_initialization(self):
        """Test COBOL parser can be initialized."""
        parser = COBOLParser()
        assert ".cbl" in parser.supported_extensions or ".CBL" in parser.supported_extensions
        assert parser.document_type.value == "cobol_program"

    def test_parser_registration(self):
        """Test COBOL parser is registered."""
        parser = parser_registry.get_parser_for_file(Path("test.cbl"))
        assert isinstance(parser, COBOLParser)

    def test_parse_cobol_file(self, sample_cobol_file):
        """Test parsing a COBOL file."""
        if not sample_cobol_file.exists():
            pytest.skip(f"Sample file not found: {sample_cobol_file}")

        parser = COBOLParser()
        parsed = parser.parse(sample_cobol_file)

        assert parsed is not None
        assert parsed.metadata.document_type.value == "cobol_program"
        assert parsed.metadata.name
        assert parsed.metadata.file_path == sample_cobol_file

    def test_cobol_parser_extracts_divisions(self, sample_cobol_file):
        """Test COBOL parser extracts divisions/paragraphs."""
        if not sample_cobol_file.exists():
            pytest.skip(f"Sample file not found: {sample_cobol_file}")

        parser = COBOLParser()
        parsed = parser.parse(sample_cobol_file)

        # Should have some structure
        assert len(parsed.components) + len(parsed.data_sources) > 0


class TestJCLParser:
    """Test JCL parser functionality."""

    def test_parser_initialization(self):
        """Test JCL parser can be initialized."""
        parser = JCLParser()
        assert ".jcl" in parser.supported_extensions or ".JCL" in parser.supported_extensions
        assert parser.document_type.value in ["mainframe_jcl", "mainframe_job"]

    def test_parser_registration(self):
        """Test JCL parser is registered."""
        parser = parser_registry.get_parser_for_file(Path("test.jcl"))
        assert isinstance(parser, JCLParser)

    def test_parse_jcl_file(self, sample_jcl_file):
        """Test parsing a JCL file."""
        if not sample_jcl_file.exists():
            pytest.skip(f"Sample file not found: {sample_jcl_file}")

        parser = JCLParser()
        parsed = parser.parse(sample_jcl_file)

        assert parsed is not None
        assert parsed.metadata.document_type.value in ["mainframe_jcl", "mainframe_job"]
        assert parsed.metadata.name
        assert parsed.metadata.file_path == sample_jcl_file

    def test_jcl_parser_extracts_steps(self, sample_jcl_file):
        """Test JCL parser extracts job steps."""
        if not sample_jcl_file.exists():
            pytest.skip(f"Sample file not found: {sample_jcl_file}")

        parser = JCLParser()
        parsed = parser.parse(sample_jcl_file)

        # Should have components for steps
        assert len(parsed.components) + len(parsed.data_sources) > 0


class TestParserRegistry:
    """Test parser registry functionality."""

    def test_registry_finds_json_parser(self):
        """Test registry can find JSON parser."""
        parser = parser_registry.get_parser_for_file(Path("test.json"))
        assert isinstance(parser, JSONParser)

    def test_registry_finds_csv_parser(self):
        """Test registry can find CSV parser."""
        parser = parser_registry.get_parser_for_file(Path("test.csv"))
        assert isinstance(parser, CSVParser)

    def test_registry_finds_excel_parser(self):
        """Test registry can find Excel parser."""
        parser = parser_registry.get_parser_for_file(Path("test.xlsx"))
        assert isinstance(parser, ExcelParser)

    def test_registry_finds_cobol_parser(self):
        """Test registry can find COBOL parser."""
        parser = parser_registry.get_parser_for_file(Path("test.cbl"))
        assert isinstance(parser, COBOLParser)

    def test_registry_finds_jcl_parser(self):
        """Test registry can find JCL parser."""
        parser = parser_registry.get_parser_for_file(Path("test.jcl"))
        assert isinstance(parser, JCLParser)

    def test_registry_returns_none_for_unknown(self):
        """Test registry returns None for unknown file type."""
        parser = parser_registry.get_parser_for_file(Path("test.unknown"))
        assert parser is None

    def test_all_parsers_have_property_decorators(self):
        """Test all parsers use @property for supported_extensions and document_type."""
        parsers = [JSONParser(), CSVParser(), ExcelParser(), COBOLParser(), JCLParser()]

        for parser in parsers:
            # These should not raise AttributeError
            _ = parser.supported_extensions
            _ = parser.document_type

            # Should return correct types
            assert isinstance(parser.supported_extensions, list)
            assert all(isinstance(ext, str) for ext in parser.supported_extensions)
