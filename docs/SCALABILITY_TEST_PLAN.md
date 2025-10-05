# Scalability Testing Plan - COBOL/Mainframe Files

## Open-Source Technologies

### Graph Databases (Free & Open Source)

**1. ArangoDB (Recommended)**
- **License:** Apache 2.0
- **Why:** Multi-model (graph + document), easy setup, great for development
- **Install:** `docker run -p 8529:8529 -e ARANGO_ROOT_PASSWORD=test arangodb/arangodb`
- **Query:** AQL (SQL-like, easy to learn)
- **Scale:** Billions of nodes, distributed clustering

**2. JanusGraph (For Massive Scale)**
- **License:** Apache 2.0
- **Why:** Linux Foundation project, designed for billions of nodes
- **Install:** Via Docker Compose with Cassandra backend
- **Query:** Gremlin (graph traversal language)
- **Scale:** Multi-machine clusters, unlimited

**3. Memgraph (Alternative)**
- **License:** Source-available (community edition free)
- **Why:** In-memory, very fast, Cypher queries
- **Install:** `docker run -p 7687:7687 memgraph/memgraph`

**Decision:** Start with **ArangoDB** (easiest), test with **JanusGraph** for massive scale

---

## Test Data Sources (Open Source COBOL)

### 1. Open Mainframe Project - COBOL Programming Course
**URL:** https://github.com/openmainframeproject/cobol-programming-course

**Contents:**
- ~20 COBOL programs
- Copybooks (COPY statements)
- JCL (Job Control Language)
- Sample data files

**Example Programs:**
- Customer data processing
- Inventory management
- Banking transactions
- Report generation

### 2. writ3it/cobol-examples
**URL:** https://github.com/writ3it/cobol-examples

**Contents:**
- Various COBOL program examples
- File I/O operations
- Database access (DB2)
- Batch processing

### 3. Martinfx/Cobol
**URL:** https://github.com/Martinfx/Cobol

**Contents:**
- OpenCobol/GnuCobol programs
- AS/400 COBOL
- CL/CLP/CLLE programs

---

## Implementation Plan

### Phase 1: COBOL Parser (Week 1)

Create parser for COBOL programs to extract:

```python
class COBOLParser(BaseParser):
    """Parse COBOL programs into knowledge graph."""

    def parse(self, file_path: Path) -> ParsedDocument:
        """
        Extract from COBOL:
        - IDENTIFICATION DIVISION → Package metadata
        - DATA DIVISION → Variables, files, database tables
        - PROCEDURE DIVISION → Program flow, paragraphs
        - COPY statements → Dependencies
        - CALL statements → Subprogram calls
        - File I/O → READ/WRITE operations
        - SQL statements → Database access (if embedded SQL)
        """
```

**What to Extract:**

```cobol
IDENTIFICATION DIVISION.
PROGRAM-ID. CUSTOMER-UPDATE.     → Package name

DATA DIVISION.
FILE-CONTROL.
    SELECT CUSTOMER-FILE          → Data source
        ASSIGN TO 'CUSTFILE.DAT'.

WORKING-STORAGE SECTION.
01 CUSTOMER-RECORD.               → Data entity
   05 CUST-ID PIC 9(6).           → Field
   05 CUST-NAME PIC X(30).        → Field

PROCEDURE DIVISION.
MAIN-PARA.                        → Task/Paragraph
    OPEN INPUT CUSTOMER-FILE.     → Reads from CUSTOMER-FILE
    READ CUSTOMER-FILE.           → Data flow
    CALL 'VALIDATION-MODULE'.     → Dependency
```

**Graph Structure:**

```
(Package: CUSTOMER-UPDATE)
    ├─> (Task: MAIN-PARA)
    │   ├─> READS_FROM → (File: CUSTOMER-FILE)
    │   └─> CALLS → (Package: VALIDATION-MODULE)
    │
    └─> (DataEntity: CUSTOMER-RECORD)
        ├─> (Field: CUST-ID)
        └─> (Field: CUST-NAME)
```

### Phase 2: ArangoDB Integration (Week 2)

Replace NetworkX with ArangoDB:

```python
from arango import ArangoClient

class ArangoKnowledgeGraph:
    """ArangoDB-backed knowledge graph."""

    def __init__(self, host='localhost', port=8529):
        client = ArangoClient(hosts=f'http://{host}:{port}')
        self.db = client.db('enterprise_graph', username='root', password='test')

        # Create collections (if not exist)
        if not self.db.has_collection('packages'):
            self.db.create_collection('packages')
        if not self.db.has_collection('tasks'):
            self.db.create_collection('tasks')
        if not self.db.has_collection('reads_from'):
            self.db.create_collection('reads_from', edge=True)

    def add_package(self, name, metadata):
        """Add package node."""
        self.db.collection('packages').insert({
            '_key': name,
            'name': name,
            'type': 'COBOL',
            **metadata
        })

    def add_reads_from(self, task_id, file_id):
        """Add READS_FROM edge."""
        self.db.collection('reads_from').insert({
            '_from': f'tasks/{task_id}',
            '_to': f'files/{file_id}',
            'type': 'READS_FROM'
        })

    def find_tasks_reading_from(self, file_name):
        """AQL query - O(log n) indexed."""
        aql = """
        FOR file IN files
            FILTER file.name == @file_name
            FOR v, e, p IN 1..1 INBOUND file reads_from
                RETURN {id: v._key, name: v.name, type: v.type}
        """
        cursor = self.db.aql.execute(aql, bind_vars={'file_name': file_name})
        return [(doc['id'], doc) for doc in cursor]

    def trace_lineage(self, entity_name, direction='both', max_depth=5):
        """Efficient graph traversal."""
        if direction == 'upstream':
            aql = f"""
            FOR entity IN files
                FILTER entity.name == @entity_name
                FOR v, e, p IN 1..{max_depth} OUTBOUND entity reads_from, writes_to
                    RETURN DISTINCT {{
                        id: v._key,
                        name: v.name,
                        depth: LENGTH(p.edges)
                    }}
            """
        # Similar for downstream and both

        cursor = self.db.aql.execute(aql, bind_vars={'entity_name': entity_name})
        return self._format_results(cursor)
```

### Phase 3: Scalability Testing (Week 3)

**Test Scenarios:**

#### Small Scale (Baseline)
- **Input:** 20 COBOL programs from Open Mainframe Project
- **Expected:** ~500 nodes, ~1,000 edges
- **Metrics:** Query time, memory usage

#### Medium Scale
- **Input:** 200 COBOL programs (replicate with variations)
- **Expected:** ~5,000 nodes, ~10,000 edges
- **Test:**
  - Impact analysis queries
  - Lineage tracing (depth=5)
  - Search by pattern
- **Target:** <100ms per query

#### Large Scale (Stress Test)
- **Input:** 2,000 COBOL programs (replicate + randomize)
- **Expected:** ~50,000 nodes, ~100,000 edges
- **Test:**
  - Concurrent queries (10 agents)
  - Complex graph traversals
  - Agent reasoning with planning
- **Target:** <500ms per query

#### Massive Scale (ArangoDB Cluster)
- **Input:** 20,000 COBOL programs
- **Expected:** ~500,000 nodes, ~1,000,000 edges
- **Setup:** 3-node ArangoDB cluster
- **Test:**
  - Distributed queries
  - Sharding across nodes
  - Replication factor 2
- **Target:** <1s per query

---

## Test Metrics

### Performance Metrics

```python
import time

class PerformanceTest:
    def test_impact_analysis(self, graph, file_name):
        """Measure impact analysis performance."""
        start = time.time()

        readers = graph.find_tasks_reading_from(file_name)
        writers = graph.find_tasks_writing_to(file_name)

        elapsed = time.time() - start

        return {
            'query_time_ms': elapsed * 1000,
            'results_count': len(readers) + len(writers),
            'throughput_qps': 1 / elapsed if elapsed > 0 else float('inf')
        }

    def test_lineage_trace(self, graph, entity_name, max_depth=5):
        """Measure lineage tracing performance."""
        start = time.time()

        lineage = graph.trace_lineage(entity_name, direction='both', max_depth=max_depth)

        elapsed = time.time() - start

        return {
            'query_time_ms': elapsed * 1000,
            'depth': max_depth,
            'nodes_traversed': len(lineage.get('upstream', [])) + len(lineage.get('downstream', [])),
            'throughput_qps': 1 / elapsed if elapsed > 0 else float('inf')
        }

    def test_agent_reasoning(self, agent, query):
        """Measure agent + graph query performance."""
        start = time.time()

        response = agent.analyze(query)

        elapsed = time.time() - start

        # Extract tool calls from audit log
        tool_calls = self._count_tool_calls(agent.audit_log)

        return {
            'total_time_ms': elapsed * 1000,
            'llm_time_ms': self._extract_llm_time(agent.audit_log),
            'graph_time_ms': self._extract_graph_time(agent.audit_log),
            'tool_calls': tool_calls,
            'response_length': len(response)
        }
```

### Scalability Metrics

| Scale | Programs | Nodes | Edges | Query Time | Memory | Agent Planning |
|-------|----------|-------|-------|------------|--------|----------------|
| Small | 20 | 500 | 1K | <10ms | 50MB | <5s |
| Medium | 200 | 5K | 10K | <100ms | 200MB | <10s |
| Large | 2,000 | 50K | 100K | <500ms | 1GB | <30s |
| Massive | 20,000 | 500K | 1M | <1s | 5GB | <60s |

---

## Implementation Steps

### Step 1: Download COBOL Samples

```bash
# Clone Open Mainframe Project COBOL course
git clone https://github.com/openmainframeproject/cobol-programming-course.git

# Clone additional examples
git clone https://github.com/writ3it/cobol-examples.git
git clone https://github.com/Martinfx/Cobol.git
```

### Step 2: Create COBOL Parser

```python
# src/enterprise_assistant/parsers/cobol_parser.py

class COBOLParser(BaseParser):
    """Parse COBOL programs."""

    def parse(self, file_path: Path) -> ParsedDocument:
        """Extract COBOL structure."""
        with open(file_path, 'r') as f:
            content = f.read()

        # Extract divisions
        program_id = self._extract_program_id(content)
        data_division = self._parse_data_division(content)
        procedure_division = self._parse_procedure_division(content)

        # Build ParsedDocument
        return ParsedDocument(
            metadata=DocumentMetadata(
                document_id=program_id,
                name=program_id,
                document_type=DocumentType.COBOL_PROGRAM,
                ...
            ),
            components=procedure_division['paragraphs'],
            data_sources=data_division['files'],
            data_entities=data_division['records'],
            dependencies=self._extract_dependencies(content)
        )
```

### Step 3: Setup ArangoDB

```bash
# Start ArangoDB in Docker
docker run -d \
    --name arangodb \
    -p 8529:8529 \
    -e ARANGO_ROOT_PASSWORD=test \
    arangodb/arangodb:latest

# Access web UI: http://localhost:8529
# Username: root, Password: test
```

### Step 4: Run Scalability Tests

```bash
# Small scale test
python tests/test_scalability.py --scale=small --backend=arangodb

# Medium scale test
python tests/test_scalability.py --scale=medium --backend=arangodb

# Large scale test (generate synthetic data)
python tests/test_scalability.py --scale=large --backend=arangodb --generate

# Compare with NetworkX baseline
python tests/test_scalability.py --scale=medium --backend=networkx
python tests/test_scalability.py --scale=medium --backend=arangodb
```

---

## Expected Outcomes

### Performance Comparison

**NetworkX (In-Memory):**
- ✅ Fast for small graphs (<10K nodes)
- ⚠️ Slows down for medium graphs (10K-100K nodes)
- ❌ Fails for large graphs (>100K nodes, out of memory)

**ArangoDB (Indexed):**
- ✅ Consistent performance across all scales
- ✅ Indexed queries always O(log n)
- ✅ Handles millions of nodes
- ✅ Distributed clustering for massive scale

### Agent Reasoning Improvement

With hierarchical indexing + ArangoDB:

```
Query: "Find all COBOL programs that read from CUSTOMER-FILE"

NetworkX Approach:
1. Load all nodes (50K nodes)
2. Scan each node checking type
3. Check edges for READS_FROM
Time: ~10 seconds

ArangoDB Approach:
1. AQL query with index lookup
   FOR file IN files FILTER file.name == "CUSTOMER-FILE"
   FOR task IN INBOUND file reads_from
   RETURN task
Time: ~50 milliseconds

200x faster!
```

---

## Next Steps

1. ✅ **Week 1:** Implement COBOL parser
2. ✅ **Week 2:** Integrate ArangoDB backend
3. ✅ **Week 3:** Run scalability tests with real data
4. ✅ **Week 4:** Optimize agent query planning for large graphs

This will demonstrate:
- Enterprise-grade scalability (millions of nodes)
- Real-world data (COBOL/Mainframe)
- Open-source tech stack (no proprietary tools)
- Actual performance metrics

Ready to build this?
