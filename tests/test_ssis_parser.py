"""Tests for SSIS parser (new multi-format architecture)."""

from pathlib import Path

import pytest

from traceai.parsers.base import DocumentType, ParsedDocument
from traceai.parsers.ssis_parser import SSISParser, parse_ssis


@pytest.fixture
def ssis_parser() -> SSISParser:
    """Create an SSIS parser instance."""
    return SSISParser()


def test_ssis_parser_properties(ssis_parser: SSISParser):
    """Test SSIS parser properties."""
    assert ssis_parser.supported_extensions == [".dtsx"]
    assert ssis_parser.document_type == DocumentType.SSIS_PACKAGE


def test_ssis_parser_validation(ssis_parser: SSISParser, tmp_path: Path):
    """Test SSIS parser file validation."""
    # Valid DTSX file
    valid_dtsx = tmp_path / "test.dtsx"
    valid_dtsx.write_text(
        """<?xml version="1.0"?>
<Executable xmlns:DTS="www.microsoft.com/SqlServer/Dts" DTS:ExecutableType="Package">
</Executable>"""
    )
    assert ssis_parser.validate(valid_dtsx) is True

    # Invalid extension
    invalid_file = tmp_path / "test.txt"
    invalid_file.write_text("not a dtsx")
    assert ssis_parser.validate(invalid_file) is False

    # Non-existent file
    assert ssis_parser.validate(tmp_path / "nonexistent.dtsx") is False

    # Invalid XML
    invalid_xml = tmp_path / "invalid.dtsx"
    invalid_xml.write_text("not valid xml")
    assert ssis_parser.validate(invalid_xml) is False


def test_parse_ssis_returns_parsed_document(ssis_parser: SSISParser, tmp_path: Path):
    """Test that SSIS parser returns a ParsedDocument."""
    dtsx_file = tmp_path / "test.dtsx"
    dtsx_file.write_text(
        """<?xml version="1.0"?>
<Executable xmlns:DTS="www.microsoft.com/SqlServer/Dts"
  DTS:ExecutableType="Package"
  DTS:ObjectName="TestPackage"
  DTS:DTSID="{TEST-ID}"
  DTS:Description="Test package"
  DTS:VersionMajor="1"
  DTS:VersionMinor="0">
</Executable>"""
    )

    result = ssis_parser.parse(dtsx_file)

    assert isinstance(result, ParsedDocument)
    assert result.metadata.name == "TestPackage"
    assert result.metadata.document_type == DocumentType.SSIS_PACKAGE
    assert result.metadata.document_id == "{TEST-ID}"
    assert result.metadata.version == "1.0"


def test_parse_ssis_with_components(ssis_parser: SSISParser, tmp_path: Path):
    """Test parsing SSIS file with components (tasks)."""
    dtsx_file = tmp_path / "with_tasks.dtsx"
    dtsx_file.write_text(
        """<?xml version="1.0"?>
<Executable xmlns:DTS="www.microsoft.com/SqlServer/Dts"
  xmlns:SQLTask="www.microsoft.com/sqlserver/dts/tasks/sqltask"
  DTS:ExecutableType="Package"
  DTS:ObjectName="TaskPackage"
  DTS:DTSID="{PKG-1}">

  <DTS:Executables>
    <DTS:Executable
      DTS:ObjectName="SQL Task 1"
      DTS:DTSID="{TASK-1}"
      DTS:ExecutableType="SQLTask"
      DTS:Description="Execute SQL">
      <DTS:ObjectData>
        <SQLTask:SqlTaskData SQLTask:SqlStatementSource="SELECT * FROM Customers" />
      </DTS:ObjectData>
    </DTS:Executable>
  </DTS:Executables>
</Executable>"""
    )

    result = ssis_parser.parse(dtsx_file)

    assert len(result.components) == 1
    component = result.components[0]
    assert component.name == "SQL Task 1"
    assert component.component_id == "{TASK-1}"
    assert component.component_type == "SQLTask"
    assert component.source_code == "SELECT * FROM Customers"


def test_parse_ssis_with_data_sources(ssis_parser: SSISParser, tmp_path: Path):
    """Test parsing SSIS file with data sources (connections)."""
    dtsx_file = tmp_path / "with_connections.dtsx"
    dtsx_file.write_text(
        """<?xml version="1.0"?>
<Executable xmlns:DTS="www.microsoft.com/SqlServer/Dts"
  DTS:ExecutableType="Package"
  DTS:ObjectName="ConnPackage"
  DTS:DTSID="{PKG-1}">

  <DTS:ConnectionManagers>
    <DTS:ConnectionManager
      DTS:ObjectName="SourceDB"
      DTS:DTSID="{CONN-1}"
      DTS:CreationName="OLEDB"
      DTS:Description="Source connection">
      <DTS:ObjectData>
        <DTS:ConnectionManager ConnectionString="Data Source=server1;Initial Catalog=SourceDB;" />
      </DTS:ObjectData>
    </DTS:ConnectionManager>
  </DTS:ConnectionManagers>
</Executable>"""
    )

    result = ssis_parser.parse(dtsx_file)

    assert len(result.data_sources) == 1
    source = result.data_sources[0]
    assert source.name == "SourceDB"
    assert source.source_id == "{CONN-1}"
    assert source.source_type == "OLEDB"
    assert source.server == "server1"
    assert source.database == "SourceDB"


def test_parse_ssis_with_parameters(ssis_parser: SSISParser, tmp_path: Path):
    """Test parsing SSIS file with parameters (variables)."""
    dtsx_file = tmp_path / "with_vars.dtsx"
    dtsx_file.write_text(
        """<?xml version="1.0"?>
<Executable xmlns:DTS="www.microsoft.com/SqlServer/Dts"
  DTS:ExecutableType="Package"
  DTS:ObjectName="VarPackage"
  DTS:DTSID="{PKG-1}">

  <DTS:Variables>
    <DTS:Variable
      DTS:ObjectName="BatchSize"
      DTS:Namespace="User"
      DTS:DataType="Int32"
      DTS:Description="Batch size for processing">
      <DTS:VariableValue>1000</DTS:VariableValue>
    </DTS:Variable>
  </DTS:Variables>
</Executable>"""
    )

    result = ssis_parser.parse(dtsx_file)

    assert len(result.parameters) == 1
    param = result.parameters[0]
    assert param.name == "BatchSize"
    assert param.namespace == "User"
    assert param.data_type == "Int32"
    assert param.value == "1000"


def test_parse_ssis_with_dependencies(ssis_parser: SSISParser, tmp_path: Path):
    """Test parsing SSIS file with dependencies (precedence constraints)."""
    dtsx_file = tmp_path / "with_deps.dtsx"
    dtsx_file.write_text(
        """<?xml version="1.0"?>
<Executable xmlns:DTS="www.microsoft.com/SqlServer/Dts"
  DTS:ExecutableType="Package"
  DTS:ObjectName="DepPackage"
  DTS:DTSID="{PKG-1}">

  <DTS:Executables>
    <DTS:Executable DTS:ObjectName="Task1" DTS:DTSID="{TASK-1}" DTS:ExecutableType="SQLTask" />
    <DTS:Executable DTS:ObjectName="Task2" DTS:DTSID="{TASK-2}" DTS:ExecutableType="SQLTask" />
  </DTS:Executables>

  <DTS:PrecedenceConstraints>
    <DTS:PrecedenceConstraint
      DTS:From="{TASK-1}"
      DTS:To="{TASK-2}"
      DTS:Value="1"
      DTS:Expression="@[User::IsReady] == True" />
  </DTS:PrecedenceConstraints>
</Executable>"""
    )

    result = ssis_parser.parse(dtsx_file)

    assert len(result.dependencies) == 1
    dep = result.dependencies[0]
    assert dep.from_component == "{TASK-1}"
    assert dep.to_component == "{TASK-2}"
    assert dep.condition == "success"
    assert dep.expression == "@[User::IsReady] == True"


def test_extract_data_entities_from_sql(ssis_parser: SSISParser):
    """Test extracting data entities from SQL statements."""
    from traceai.parsers.base import Component

    # Component with SQL that reads and writes tables
    component = Component(
        name="ETL Task",
        component_id="task-1",
        component_type="SQLTask",
        source_code="""
            INSERT INTO dbo.TargetTable
            SELECT c.CustomerID, c.Name
            FROM dbo.Customers c
            JOIN dbo.Orders o ON c.CustomerID = o.CustomerID
        """,
    )

    entities = ssis_parser.extract_data_entities(component)

    # Should extract Customers, Orders, and TargetTable
    entity_names = {e.name for e in entities}
    assert "Customers" in entity_names
    assert "Orders" in entity_names
    assert "TargetTable" in entity_names

    # Check schema parsing
    for entity in entities:
        if entity.name in ["Customers", "Orders", "TargetTable"]:
            assert entity.schema_name == "dbo"


def test_parse_ssis_convenience_function(tmp_path: Path):
    """Test the convenience parse_ssis function."""
    dtsx_file = tmp_path / "convenience.dtsx"
    dtsx_file.write_text(
        """<?xml version="1.0"?>
<Executable xmlns:DTS="www.microsoft.com/SqlServer/Dts"
  DTS:ExecutableType="Package"
  DTS:ObjectName="ConvenienceTest"
  DTS:DTSID="{TEST}">
</Executable>"""
    )

    result = parse_ssis(dtsx_file)

    assert isinstance(result, ParsedDocument)
    assert result.metadata.name == "ConvenienceTest"
    assert result.metadata.document_type == DocumentType.SSIS_PACKAGE


def test_parse_ssis_real_package():
    """Test parsing a real sample SSIS package."""
    package_path = Path("examples/sample_packages/CustomerETL.dtsx")
    if not package_path.exists():
        pytest.skip("Sample package not found")

    result = parse_ssis(package_path)

    # Verify it returns ParsedDocument
    assert isinstance(result, ParsedDocument)
    assert result.metadata.document_type == DocumentType.SSIS_PACKAGE
    assert result.metadata.name == "CustomerETL"

    # Should have data sources (connections)
    assert len(result.data_sources) > 0

    # Should have components (tasks)
    assert len(result.components) > 0

    # Should have parameters (variables)
    assert len(result.parameters) > 0

    # Should have dependencies
    assert len(result.dependencies) > 0


def test_parse_ssis_error_handling(ssis_parser: SSISParser, tmp_path: Path):
    """Test error handling in SSIS parser."""
    # Non-existent file
    with pytest.raises(FileNotFoundError):
        ssis_parser.parse(tmp_path / "nonexistent.dtsx")

    # Invalid XML
    invalid_file = tmp_path / "invalid.dtsx"
    invalid_file.write_text("not xml")
    with pytest.raises(ValueError, match="Invalid DTSX XML format"):
        ssis_parser.parse(invalid_file)
