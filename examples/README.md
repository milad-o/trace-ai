# TraceAI Examples

This folder contains example data, test scripts, and demonstrations of TraceAI capabilities.

## 📁 Folder Structure

```
examples/
├── inputs/                    # Sample input files (committed to git)
│   ├── ssis/                 # SSIS package samples (.dtsx)
│   ├── cobol/                # COBOL program samples (.cbl, .CBL)
│   ├── jcl/                  # JCL job samples (.jcl)
│   ├── json/                 # JSON config samples
│   ├── csv/                  # CSV lineage mapping samples
│   └── excel/                # Excel workbook samples (.xlsx)
│
├── outputs/                   # Generated outputs (gitignored)
│   ├── graphs/               # Exported JSON/CSV graph data
│   ├── visualizations/       # Generated SVG/PNG diagrams
│   ├── reports/              # Excel analysis reports
│   └── generated_code/       # Python code from COBOL/JCL
│
└── scripts/                   # Example and test scripts
    ├── test_parsers_only.py  # Test all parsers (no API key)
    └── [other demo scripts]
```

## 🚀 Quick Start

### Test All Parsers (No API Key Required)

```bash
cd examples/scripts
uv run python test_parsers_only.py
```

## 📊 Sample Data

- **SSIS**: 2 packages (CustomerETL, SalesAggregation)
- **COBOL**: 40+ programs (financial, inventory, sales)
- **JCL**: 35+ batch jobs (daily/weekly/monthly)
- **JSON**: Pipeline configs and schemas
- **CSV**: Lineage mappings
- **Excel**: Reports with formulas

See the [main README](../README.md) for full documentation.
