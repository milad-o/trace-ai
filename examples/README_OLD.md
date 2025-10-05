# Enterprise Assistant Examples

This directory contains examples and sample data for testing the Enterprise Assistant.

## Directory Structure

### `sample_databases/`
SQLite databases simulating enterprise data:
- `customer.db` - Customer records (5 customers)
- `sales.db` - Transactions and sales summary (8 transactions)
- `inventory.db` - Products, suppliers, movements (6 products, 3 suppliers, 6 movements)
- `employee.db` - Employees, departments, payroll (6 employees, 4 departments, 6 payroll records)

**Generate databases:**
```bash
cd sample_databases
uv run python create_sample_dbs.py
```

### `sample_mainframe/`
Mainframe COBOL and JCL files:

**Real samples** (5 COBOL programs from Open Mainframe Project):
- `EMPPAY.CBL` - Employee payroll calculation
- `DEPTPAY.CBL` - Department payroll
- `CBLDB21.cbl`, `CBLDB22.cbl`, `CBLDB23.cbl` - Database access examples

**JCL jobs** (`jcl/` subdirectory):
- 20+ real JCL job files from mainframe course samples

**Synthetic data** (`synthetic/` subdirectory):
- `cobol/` - 36 generated COBOL programs across 6 business domains
- `jcl/` - 13 generated JCL batch jobs (daily, weekly, monthly schedules)

**Generate synthetic mainframe data:**
```bash
uv run python generate_mainframe_data.py
```

This creates:
- 36 COBOL programs (CUSTOMER, SALES, INVENTORY, FINANCE, PAYROLL, BILLING domains)
- 13 JCL jobs orchestrating these programs
- Expected graph size: **~376 nodes**

## Running Examples

### Quick Demo
Simple demonstration of parsing and graph building:
```bash
uv run python quick_demo.py
```

### Transparent Demo
Shows every step of agent execution with rich formatting:
```bash
export OPENAI_API_KEY=your_key  # or ANTHROPIC_API_KEY
uv run python transparent_demo.py
```

### Complex ETL Demo
Parse the entire mainframe environment (COBOL + JCL) into a knowledge graph:
```bash
uv run python complex_etl_demo.py
```

This demo:
1. Parses all COBOL programs (real + synthetic)
2. Parses all JCL jobs (real + synthetic)
3. Builds a unified knowledge graph
4. Shows graph statistics and structure
5. Demonstrates lineage tracing and impact analysis

Expected output:
- **Total Nodes**: ~279
- **Total Edges**: ~423
- **Document Types**: COBOL programs, JCL jobs
- **Components**: Job steps, COBOL paragraphs
- **Data Sources**: Datasets, files
- **Dependencies**: Sequential, READ/WRITE, PERFORM/CALL

## Sample Queries

With the agent, you can ask questions like:

**Data Lineage:**
- "What are all the upstream sources for the CUSTOMER dataset?"
- "Show me the complete data flow for payroll processing"
- "Where does the SALES.OUTPUT file go?"

**Impact Analysis:**
- "If I modify CUSTOMER.INPUT.MASTER, what programs are affected?"
- "Which JCL jobs read from FINANCE datasets?"
- "Show me everything that touches the INVENTORY.OUTPUT file"

**Dependency Analysis:**
- "What must run before the DAILYSAL job?"
- "Show me the execution order for the MNTHPAY job"
- "Which COBOL programs does BILL001 depend on?"

**Discovery:**
- "List all COBOL programs in the PAYROLL domain"
- "Find all JCL jobs that run daily"
- "Show me all programs that perform database operations"

## Scaling Up

To test at larger scales, you can:

1. **Increase synthetic data volume**:
   Edit `generate_mainframe_data.py` to generate more programs:
   - Increase programs per domain (currently 6)
   - Add more business domains
   - Create more complex JCL workflows

2. **Add real mainframe codebases**:
   - Download more COBOL/JCL from Open Mainframe Project
   - Use your organization's legacy code (if permitted)
   - Parse actual DB2, IMS, or VSAM datasets

3. **Test graph database backends**:
   See `docs/SCALABILITY.md` for using ArangoDB or JanusGraph for 100K+ nodes

## File Sizes

Current data volume:
- Real COBOL: ~36KB (5 files)
- Synthetic COBOL: ~240KB (36 files)
- Real JCL: ~20KB (20+ files)
- Synthetic JCL: ~13KB (13 files)
- SQLite databases: ~20KB (4 databases)

**Total: ~329KB** of sample enterprise data for parsing and analysis
