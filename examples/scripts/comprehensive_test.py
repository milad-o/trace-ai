"""Comprehensive real-world test of all parsers and tools with the AI agent.

This script tests:
1. All 6 parsers (SSIS, COBOL, JCL, JSON, Excel, CSV)
2. All 11 agent tools
3. Code generation capabilities
4. End-to-end workflow
"""

import json
import os
from pathlib import Path

import openpyxl
import pandas as pd
from dotenv import load_dotenv

from traceai.agents import create_enterprise_agent

# Load API key
load_dotenv()


def create_test_data():
    """Creates comprehensive test data for all parsers."""
    test_dir = Path("../outputs/test_data")
    test_dir.mkdir(parents=True, exist_ok=True)

    # 1. Create JSON ETL config
    json_config = {
        "name": "SalesDataPipeline",
        "description": "Daily sales data processing pipeline",
        "version": "3.0",
        "jobs": [
            {
                "id": "extract_sales",
                "name": "Extract Sales Data",
                "type": "extract",
                "sql": "SELECT * FROM raw.sales WHERE date = CURRENT_DATE",
                "depends_on": [],
            },
            {
                "id": "transform_sales",
                "name": "Transform Sales Data",
                "type": "transform",
                "script": "df['revenue'] = df['quantity'] * df['price']",
                "depends_on": ["extract_sales"],
            },
            {
                "id": "load_sales",
                "name": "Load to Warehouse",
                "type": "load",
                "sql": "INSERT INTO dwh.fact_sales SELECT * FROM staging.sales",
                "depends_on": ["transform_sales"],
            },
        ],
    }

    json_file = test_dir / "sales_pipeline.json"
    with open(json_file, "w") as f:
        json.dump(json_config, f, indent=2)
    print(f"✓ Created JSON config: {json_file}")

    # 2. Create CSV lineage mapping
    lineage_df = pd.DataFrame(
        {
            "source_table": ["raw.sales", "raw.customers", "raw.products"],
            "target_table": ["staging.sales", "staging.customers", "staging.products"],
            "transformation": ["Validate and clean", "Deduplicate", "Normalize"],
        }
    )

    csv_file = test_dir / "lineage_mapping.csv"
    lineage_df.to_csv(csv_file, index=False)
    print(f"✓ Created CSV lineage: {csv_file}")

    # 3. Create Excel workbook with formulas
    wb = openpyxl.Workbook()

    # Sales sheet
    ws_sales = wb.active
    ws_sales.title = "Sales"
    ws_sales["A1"] = "Product"
    ws_sales["B1"] = "Quantity"
    ws_sales["C1"] = "Price"
    ws_sales["D1"] = "Revenue"
    ws_sales["A2"] = "Widget A"
    ws_sales["B2"] = 100
    ws_sales["C2"] = 10
    ws_sales["D2"] = "=B2*C2"

    # Summary sheet with formula references
    ws_summary = wb.create_sheet("Summary")
    ws_summary["A1"] = "Total Revenue"
    ws_summary["B1"] = "=SUM(Sales!D:D)"  # References Sales sheet

    excel_file = test_dir / "sales_report.xlsx"
    wb.save(excel_file)
    print(f"✓ Created Excel workbook: {excel_file}")

    # Also use existing COBOL/JCL samples
    print(f"✓ Using existing COBOL files: ../inputs/")
    print(f"✓ Using existing SSIS files: ../inputs/ssis/")

    return test_dir


def test_agent_comprehensive():
    """Test agent with all parsers and tools."""
    print("\n" + "=" * 70)
    print("COMPREHENSIVE AGENT TEST - All Parsers & Tools")
    print("=" * 70)

    # Create test data
    test_dir = create_test_data()

    # Create agent and load documents from multiple sources
    print("\n📚 Loading documents from multiple formats...")
    agent = create_enterprise_agent(
        documents_dir="../inputs/ssis",  # Start with SSIS
        model_provider="openai",
        model_name="gpt-4o",
    )

    # Load additional documents
    print("  Loading COBOL/JCL files...")
    agent.load_documents("../inputs", pattern=["**/*.cbl", "**/*.jcl"])

    print("  Loading JSON/CSV/Excel files...")
    agent.load_documents(str(test_dir), pattern=["*.json", "*.csv", "*.xlsx"])

    print(f"\n✅ Agent initialized with knowledge graph")

    # Test queries for each parser and tool
    test_queries = [
        # Test 1: Graph queries (existing tools)
        {
            "name": "Graph Statistics",
            "query": "Show me statistics about the knowledge graph. How many nodes and edges do we have?",
            "tests_tool": "get_graph_statistics",
        },
        # Test 2: JSON parser
        {
            "name": "JSON Parser",
            "query": "What ETL jobs are defined in the SalesDataPipeline JSON configuration?",
            "tests_tool": "graph_query (JSON data)",
        },
        # Test 3: CSV lineage parser
        {
            "name": "CSV Lineage",
            "query": "What lineage mappings are defined in the CSV files? Show source and target tables.",
            "tests_tool": "graph_query (CSV data)",
        },
        # Test 4: Excel parser
        {
            "name": "Excel Parser",
            "query": "What sheets are in the Excel workbooks and do any have formula dependencies?",
            "tests_tool": "graph_query (Excel data)",
        },
        # Test 5: Generate JSON export
        {
            "name": "JSON Export Tool",
            "query": "Export the complete knowledge graph to a JSON file at output/graph_export.json",
            "tests_tool": "generate_json",
        },
        # Test 6: Generate CSV lineage report
        {
            "name": "CSV Export Tool",
            "query": "Generate a CSV lineage report and save it to output/lineage_report.csv",
            "tests_tool": "generate_csv",
        },
        # Test 7: Generate Excel workbook
        {
            "name": "Excel Export Tool",
            "query": "Create an Excel workbook with summary, nodes, and lineage sheets. Save to output/analysis.xlsx",
            "tests_tool": "generate_excel",
        },
        # Test 8: Python code generation from COBOL
        {
            "name": "Python Generator",
            "query": "Find a COBOL program in the graph and generate Python code for it. Save to output/converted_cobol.py",
            "tests_tool": "generate_python_from_cobol",
        },
        # Test 9: Impact analysis (test integration)
        {
            "name": "Impact Analysis",
            "query": "What would be impacted if I change the raw.sales table?",
            "tests_tool": "analyze_impact",
        },
        # Test 10: Semantic search across all formats
        {
            "name": "Semantic Search",
            "query": "Search for all components related to 'sales data' across all document types",
            "tests_tool": "semantic_search",
        },
    ]

    results = []
    output_dir = Path("../outputs")
    output_dir.mkdir(exist_ok=True)

    for idx, test_case in enumerate(test_queries, 1):
        print(f"\n{'─' * 70}")
        print(f"Test {idx}/{len(test_queries)}: {test_case['name']}")
        print(f"Testing: {test_case['tests_tool']}")
        print(f"{'─' * 70}")
        print(f"\n💬 Query: {test_case['query']}")

        try:
            print(f"\n🤖 Agent thinking...")
            response = agent.analyze(test_case["query"])

            print(f"\n📋 Response:")
            print(response[:500])
            if len(response) > 500:
                print(f"... (truncated, total length: {len(response)} chars)")

            results.append(
                {
                    "test": test_case["name"],
                    "tool": test_case["tests_tool"],
                    "status": "✅ PASS",
                    "response_length": len(response),
                }
            )

        except Exception as e:
            print(f"\n❌ Error: {e}")
            results.append(
                {"test": test_case["name"], "tool": test_case["tests_tool"], "status": f"❌ FAIL: {e}"}
            )

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for result in results:
        status_icon = "✅" if "PASS" in result["status"] else "❌"
        print(f"{status_icon} {result['test']}")
        print(f"   Tool: {result['tool']}")
        print(f"   Status: {result['status']}")
        print()

    passed = sum(1 for r in results if "PASS" in r["status"])
    total = len(results)
    print(f"Results: {passed}/{total} tests passed ({passed/total*100:.0f}%)")

    # Check generated files
    print("\n" + "=" * 70)
    print("GENERATED FILES")
    print("=" * 70)

    expected_files = [
        "../outputs/graph_export.json",
        "../outputs/lineage_report.csv",
        "../outputs/analysis.xlsx",
        "../outputs/converted_cobol.py",
    ]

    for file_path in expected_files:
        if Path(file_path).exists():
            size = Path(file_path).stat().st_size
            print(f"✅ {file_path} ({size:,} bytes)")
        else:
            print(f"❌ {file_path} (not found)")

    print("\n" + "=" * 70)
    print("All parsers and tools tested!")
    print("=" * 70)


if __name__ == "__main__":
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ No OPENAI_API_KEY found!")
        print("Set OPENAI_API_KEY environment variable")
        exit(1)

    test_agent_comprehensive()
