"""Quick test of new parsers and code generation features."""

from pathlib import Path

from enterprise_assistant.parsers import JSONParser, ExcelParser, CSVParser
from enterprise_assistant.parsers.base import DocumentMetadata, DocumentType


def test_json_parser():
    """Test JSON parser with a sample config."""
    print("Testing JSON parser...")

    # Create a sample JSON file
    import json

    sample_data = {
        "name": "SamplePipeline",
        "description": "Test ETL pipeline",
        "version": "1.0",
        "jobs": [
            {
                "name": "ExtractCustomers",
                "type": "extract",
                "sql": "SELECT * FROM customers",
                "depends_on": [],
            },
            {
                "name": "TransformCustomers",
                "type": "transform",
                "script": "df['full_name'] = df['first'] + ' ' + df['last']",
                "depends_on": ["ExtractCustomers"],
            },
        ],
    }

    test_file = Path("test_pipeline.json")
    with open(test_file, "w") as f:
        json.dump(sample_data, f, indent=2)

    # Parse it
    parser = JSONParser()
    doc = parser.parse(test_file)

    print(f"  ✓ Parsed: {doc.metadata.name}")
    print(f"  ✓ Components: {len(doc.components)}")
    print(f"  ✓ Dependencies: {len(doc.dependencies)}")

    # Clean up
    test_file.unlink()
    print()


def test_csv_parser():
    """Test CSV parser with lineage mapping."""
    print("Testing CSV parser...")

    # Create a sample lineage CSV
    import pandas as pd

    lineage_data = pd.DataFrame(
        {
            "source_table": ["customers_raw", "orders_raw", "products_raw"],
            "target_table": ["customers_clean", "orders_clean", "products_clean"],
            "transformation": ["Remove duplicates", "Validate dates", "Normalize prices"],
        }
    )

    test_file = Path("test_lineage.csv")
    lineage_data.to_csv(test_file, index=False)

    # Parse it
    parser = CSVParser()
    doc = parser.parse(test_file)

    print(f"  ✓ Parsed: {doc.metadata.name}")
    print(f"  ✓ Data entities: {len(doc.data_entities)}")
    print(f"  ✓ Dependencies: {len(doc.dependencies)}")

    # Clean up
    test_file.unlink()
    print()


def test_excel_parser():
    """Test Excel parser with a sample workbook."""
    print("Testing Excel parser...")

    # Create a sample Excel file
    import openpyxl

    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "Data"
    ws1["A1"] = "Name"
    ws1["B1"] = "Value"
    ws1["A2"] = "Customer"
    ws1["B2"] = 100

    ws2 = wb.create_sheet("Summary")
    ws2["A1"] = "Total"
    ws2["B1"] = "=Data!B2"  # Formula reference to Data sheet

    test_file = Path("test_workbook.xlsx")
    wb.save(test_file)

    # Parse it
    parser = ExcelParser()
    doc = parser.parse(test_file)

    print(f"  ✓ Parsed: {doc.metadata.name}")
    print(f"  ✓ Components (sheets): {len(doc.components)}")
    print(f"  ✓ Dependencies (formulas): {len(doc.dependencies)}")

    # Clean up
    test_file.unlink()
    print()


def test_code_generation_tools():
    """Test that code generation tools are properly imported."""
    print("Testing code generation tools import...")

    from enterprise_assistant.tools import (
        GenerateJSONTool,
        GenerateCSVTool,
        GenerateExcelTool,
        GeneratePythonTool,
    )

    print("  ✓ GenerateJSONTool imported")
    print("  ✓ GenerateCSVTool imported")
    print("  ✓ GenerateExcelTool imported")
    print("  ✓ GeneratePythonTool imported")
    print()


if __name__ == "__main__":
    print("=" * 60)
    print("Testing New TraceAI Features")
    print("=" * 60)
    print()

    try:
        test_json_parser()
        test_csv_parser()
        test_excel_parser()
        test_code_generation_tools()

        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
