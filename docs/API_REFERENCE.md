# TraceAI API Reference
### TraceAI

**Path**: `traceai.agents.TraceAI`

Async-first intelligent agent that powers the entire TraceAI platform. Provides concurrent document parsing, semantic search, graph tooling, and LLM-backed reasoning in a single interface.

#### Constructor

```python
TraceAI(
    model_provider: str = "anthropic",
    model_name: str | None = None,
    persist_dir: Path | str = "./examples/outputs/data",
    enable_memory: bool = True,
    enable_audit: bool = True,
    enable_progress: bool = True,
    max_conversation_messages: int = 30,
    max_concurrent_parsers: int = 10
)
```

**Parameters**:
- `model_provider` (str): LLM provider - "anthropic" or "openai"
- `model_name` (str | None): Override default model name.
- `persist_dir` (Path | str): Directory for persisting vector store and cache data.
- `enable_memory` (bool): Enable conversation memory middleware for follow-up context.
- `enable_audit` (bool): Enable audit logging middleware.
- `enable_progress` (bool): Enable progress tracking middleware.
- `max_conversation_messages` (int): Maximum messages to retain in memory.
- `max_concurrent_parsers` (int): Maximum concurrent parsing operations.

**Attributes**:
- `graph` (nx.DiGraph | None): Knowledge graph built from parsed documents.
- `vector_store` (Chroma): Persistent semantic search index.
- `parsed_documents` (list): List of parsed document objects with metadata/components.
- `llm` (ChatAnthropic | ChatOpenAI | None): Backing LLM client (None when no API key).
- `agent`: DeepAgents-based orchestrator created after documents load.

#### Methods

##### load_documents

```python
async def load_documents(
    directory: Path | str,
    pattern: str | list[str] = "**/*.dtsx"
) -> None
```

Load and parse documents concurrently. Accepts a single glob pattern or a list of patterns.

**Example**:
```python
agent = TraceAI(max_concurrent_parsers=20)

await agent.load_documents("./examples/inputs/ssis")
await agent.load_documents("./examples/inputs/json", pattern="*.json")

stats = agent.get_graph_stats()
print(stats)
```

##### query

```python
async def query(question: str) -> str
```

Execute a natural-language question using the graph, semantic search, and LLM toolchain.

**Raises**:
- `ValueError`: If documents are not loaded or no LLM is configured.

**Example**:
```python
answer = await agent.query("Trace the lineage for the Customer table")
print(answer)
```

##### query_stream

```python
async def query_stream(question: str) -> AsyncIterator[str]
```

Stream the response incrementally for UI or CLI use.

**Example**:
```python
async for chunk in agent.query_stream("List key metrics for SalesETL"):
    print(chunk, end="")
```

##### get_graph_stats

```python
def get_graph_stats() -> dict[str, Any]
```

Return aggregate statistics about the knowledge graph (nodes, edges, components, etc.).

##### vector_store

TraceAI exposes a `vector_store` attribute (Chroma) for advanced semantic search or downstream tooling.

**Example**:
```python
results = agent.vector_store.similarity_search("customer lineage", k=5)
for doc in results:
    print(doc.page_content)
```

##### parsed_documents

List of parsed document objects with metadata, components, and data sources. Useful for building custom reports.

##### Example End-to-End Workflow

```python
import asyncio
from traceai.agents import TraceAI


async def main():
    agent = TraceAI(persist_dir="./.traceai", max_concurrent_parsers=15)
    await agent.load_documents("./examples/inputs/ssis")

    stats = agent.get_graph_stats()
    print(stats)

    answer = await agent.query("Which packages load customer data?")
    print(answer)


asyncio.run(main())
```

---
**Parameters**:
- `question` (str): Natural language question

**Returns**:
- `str`: Agent's response

**Example**:
```python
response = await agent.query("List all documents")
```

##### query_stream

```python
async def query_stream(question: str) -> AsyncIterator[str]
```

Query with streaming response.

**Returns**:
- AsyncIterator[str]: Async generator yielding response chunks

**Example**:
```python
async for chunk in agent.query_stream("Analyze data flow"):
    print(chunk, end="", flush=True)
```

##### get_graph_stats

```python
def get_graph_stats() -> dict[str, Any]
```

Get knowledge graph statistics.

**Returns**:
- `dict`: Statistics including total_nodes, total_edges, documents, components, etc.

---

## Parsers

All parsers inherit from `BaseParser` and use `@property` decorators.

### SSISParser

**Path**: `traceai.parsers.SSISParser`

Parse SSIS (.dtsx) packages.

**Supported Extensions**: `.dtsx`

**Document Type**: `DocumentType.SSIS_PACKAGE`

#### Methods

```python
def parse(file_path: Path) -> ParsedDocument
```

Parse an SSIS package file.

**Extracts**:
- Data sources (connections)
- Parameters (variables)
- Components (Data Flow tasks, Execute SQL tasks, etc.)
- Dependencies (precedence constraints)
- Data entities (tables from SQL queries)

**Example**:
```python
from traceai.parsers import SSISParser

parser = SSISParser()
parsed = parser.parse(Path("CustomerETL.dtsx"))

print(f"Components: {len(parsed.components)}")
print(f"Data sources: {len(parsed.data_sources)}")
```

---

### JSONParser

**Path**: `traceai.parsers.JSONParser`

Parse JSON configuration files.

**Supported Extensions**: `.json`, `.jsonc`

**Document Type**: `DocumentType.JSON_CONFIG`

#### Methods

```python
def parse(file_path: Path) -> ParsedDocument
```

Parse JSON configuration or pipeline definition.

**Supports**:
- Pipeline configurations (jobs with dependencies)
- Data schemas
- Transformation definitions
- API configurations

**Example**:
```python
from traceai.parsers import JSONParser

parser = JSONParser()
parsed = parser.parse(Path("pipeline.json"))

# Access extracted components
for component in parsed.components:
    print(f"Job: {component.name}")
```

---

### CSVParser

**Path**: `traceai.parsers.CSVParser`

Parse CSV lineage mapping files.

**Supported Extensions**: `.csv`

**Document Type**: `DocumentType.CSV_METADATA`

#### Methods

```python
def parse(file_path: Path) -> ParsedDocument
```

Parse CSV file containing lineage mappings or field transformations.

**Auto-detects Schema Types**:
- Lineage mapping (source/target columns)
- Field mapping (source_field/target_field)
- Transformation (source_table/target_table/transformation_logic)

**Example**:
```python
from traceai.parsers import CSVParser

parser = CSVParser()
parsed = parser.parse(Path("lineage.csv"))

# Access dependencies
for dep in parsed.dependencies:
    print(f"{dep.from_id} -> {dep.to_id}")
```

---

### ExcelParser

**Path**: `traceai.parsers.ExcelParser`

Parse Excel workbooks with formula dependencies.

**Supported Extensions**: `.xlsx`, `.xlsm`

**Document Type**: `DocumentType.EXCEL_WORKBOOK`

#### Methods

```python
def parse(file_path: Path) -> ParsedDocument
```

Parse Excel workbook, extracting sheets, named ranges, and formula dependencies.

**Extracts**:
- Sheets as components
- Named ranges as parameters
- Tables as data entities
- Formula dependencies (cross-sheet references)

**Example**:
```python
from traceai.parsers import ExcelParser

parser = ExcelParser()
parsed = parser.parse(Path("report.xlsx"))

# Access sheets
for component in parsed.components:
    print(f"Sheet: {component.name}")
```

---

### COBOLParser

**Path**: `traceai.parsers.COBOLParser`

Parse COBOL programs.

**Supported Extensions**: `.cbl`, `.CBL`, `.cob`, `.COB`

**Document Type**: `DocumentType.COBOL_PROGRAM`

#### Methods

```python
def parse(file_path: Path) -> ParsedDocument
```

Parse COBOL program, extracting divisions, paragraphs, and file I/O.

**Extracts**:
- Identification Division metadata
- Data Division (FD file definitions)
- Procedure Division (paragraphs as components)
- File I/O operations (as data sources)
- CALL dependencies

**Example**:
```python
from traceai.parsers import COBOLParser

parser = COBOLParser()
parsed = parser.parse(Path("CUSTOMER.cbl"))

# Access file operations
for source in parsed.data_sources:
    print(f"File: {source.name}, Type: {source.source_type}")
```

---

### JCLParser

**Path**: `traceai.parsers.JCLParser`

Parse JCL (Job Control Language) jobs.

**Supported Extensions**: `.jcl`, `.JCL`

**Document Type**: `DocumentType.MAINFRAME_JCL`

#### Methods

```python
def parse(file_path: Path) -> ParsedDocument
```

Parse JCL job, extracting steps, programs, and datasets.

**Extracts**:
- Job metadata
- Job steps as components
- DD (Data Definition) statements as data sources
- EXEC PGM= as dependencies
- Dataset references

**Example**:
```python
from traceai.parsers import JCLParser

parser = JCLParser()
parsed = parser.parse(Path("PAYROLL.jcl"))

# Access job steps
for component in parsed.components:
    print(f"Step: {component.name}, Type: {component.component_type}")
```

---

## Graph

### GraphQueries

**Path**: `traceai.graph.GraphQueries`

Query and analyze the knowledge graph.

#### Constructor

```python
GraphQueries(graph: nx.DiGraph)
```

**Parameters**:
- `graph` (nx.DiGraph): NetworkX directed graph

#### Methods

##### get_graph_stats

```python
def get_graph_stats() -> dict[str, Any]
```

Get comprehensive graph statistics.

**Returns**:
```python
{
    "total_nodes": int,
    "total_edges": int,
    "documents": int,
    "components": int,
    "data_sources": int,
    "data_entities": int,
    "parameters": int,
    "node_types": dict,
    "document_types": dict
}
```

##### find_all_documents

```python
def find_all_documents() -> list[tuple[str, dict]]
```

Find all document nodes in the graph.

**Returns**:
- `list[tuple[str, dict]]`: List of (node_id, node_data) tuples

##### find_all_components

```python
def find_all_components() -> list[tuple[str, dict]]
```

Find all component nodes (tasks, jobs, etc.).

##### find_all_data_sources

```python
def find_all_data_sources() -> list[tuple[str, dict]]
```

Find all data source nodes (connections, files, databases).

##### find_all_data_entities

```python
def find_all_data_entities() -> list[tuple[str, dict]]
```

Find all data entity nodes (tables, datasets, files).

##### trace_data_lineage

```python
def trace_data_lineage(
    entity_name: str,
    direction: str = "both"
) -> dict[str, list[tuple[str, dict]]]
```

Trace data lineage for a specific entity.

**Parameters**:
- `entity_name` (str): Name of the data entity (table, file, etc.)
- `direction` (str): "upstream", "downstream", or "both"

**Returns**:
```python
{
    "upstream": [(node_id, node_data), ...],
    "downstream": [(node_id, node_data), ...]
}
```

**Example**:
```python
queries = GraphQueries(agent.graph)
lineage = queries.trace_data_lineage("Customer", direction="both")

print("Upstream sources:")
for node_id, data in lineage["upstream"]:
    print(f"  - {data['name']}")
```

##### find_tasks_reading_from_table

```python
def find_tasks_reading_from_table(table_name: str) -> list[tuple[str, dict]]
```

Find all tasks that read from a specific table.

**Parameters**:
- `table_name` (str): Table name to search for

**Returns**:
- `list[tuple[str, dict]]`: Tasks reading from the table

##### find_tasks_writing_to_table

```python
def find_tasks_writing_to_table(table_name: str) -> list[tuple[str, dict]]
```

Find all tasks that write to a specific table.

##### find_component_dependencies

```python
def find_component_dependencies(component_id: str) -> dict[str, list]
```

Find upstream and downstream dependencies for a component.

**Returns**:
```python
{
    "upstream": [component_ids],
    "downstream": [component_ids]
}
```

##### search_nodes_by_name

```python
def search_nodes_by_name(name_pattern: str) -> list[tuple[str, dict]]
```

Search for nodes by name (case-insensitive substring match).

**Parameters**:
- `name_pattern` (str): Pattern to search for

---

### Graph Builder

**Path**: `traceai.graph.builder`

#### build_graph_from_documents

```python
def build_graph_from_documents(
    documents: list[ParsedDocument]
) -> nx.DiGraph
```

Build a NetworkX directed graph from parsed documents.

**Parameters**:
- `documents` (list[ParsedDocument]): List of parsed documents

**Returns**:
- `nx.DiGraph`: Knowledge graph with nodes and edges

**Node Types**:
- `document`: Top-level document
- `component`: Task, job step, paragraph, etc.
- `data_source`: Connection, file, database
- `data_entity`: Table, dataset, file
- `parameter`: Variable, named range

**Edge Types**:
- `contains`: Document contains component
- `uses`: Component uses data source
- `reads_from`: Component reads from entity
- `writes_to`: Component writes to entity
- `depends_on`: Component depends on another component

---

## Tools

### Graph Tools

**Path**: `traceai.tools.graph_tools`

#### create_graph_tools

```python
def create_graph_tools(graph: nx.DiGraph) -> list[Tool]
```

Create LangChain tools for graph querying.

**Returns**: List of tools including:
- `get_graph_statistics`: Get graph stats
- `find_documents`: Find all documents
- `find_components`: Find all components
- `trace_lineage`: Trace data lineage
- `find_dependencies`: Find component dependencies
- `search_by_name`: Search nodes by name

---

### Code Generation Tools

**Path**: `traceai.tools.code_generation_tools`

#### GenerateJSONTool

```python
class GenerateJSONTool(BaseTool):
    def __init__(self, graph: nx.DiGraph)
```

Generate JSON export of the knowledge graph.

**Method**:
```python
def _run(self, output_path: str) -> str
```

**Output Format**:
```json
{
    "metadata": {
        "total_nodes": int,
        "total_edges": int,
        "export_date": str
    },
    "nodes": [
        {
            "id": str,
            "type": str,
            "name": str,
            "properties": dict
        }
    ],
    "edges": [
        {
            "source": str,
            "target": str,
            "type": str
        }
    ]
}
```

#### GenerateCSVTool

```python
class GenerateCSVTool(BaseTool):
    def __init__(self, graph: nx.DiGraph)
```

Generate CSV export of lineage or nodes.

**Method**:
```python
def _run(
    self,
    output_path: str,
    export_type: str = "lineage"  # "lineage", "nodes", or "edges"
) -> str
```

**Export Types**:
- `lineage`: Source-target relationships
- `nodes`: All nodes with properties
- `edges`: All edges with metadata

#### GenerateExcelTool

```python
class GenerateExcelTool(BaseTool):
    def __init__(self, graph: nx.DiGraph)
```

Generate multi-sheet Excel report.

**Method**:
```python
def _run(self, output_path: str) -> str
```

**Sheets**:
- Summary: Graph statistics
- Nodes: All nodes with properties
- Edges: All edges with relationships
- Lineage: Data lineage mappings

#### GeneratePythonTool

```python
class GeneratePythonTool(BaseTool):
    def __init__(self)
```

Generate Python code from COBOL/JCL.

**Method**:
```python
def _run(
    self,
    source_code: str,
    output_path: str,
    source_type: str = "cobol"  # "cobol" or "jcl"
) -> str
```

Converts COBOL/JCL to modern Python using Jinja2 templates.

---

### Visualization Tools

**Path**: `traceai.tools.visualization_tools`

#### create_graph_visualization_tool

```python
def create_graph_visualization_tool(graph: nx.DiGraph) -> Tool
```

Create tool for generating graph visualizations.

**Tool Method**:
```python
def visualize_graph(
    package_name: str = None,
    output_format: str = "svg",  # "svg" or "png"
    layout: str = "hierarchical",  # "hierarchical", "spring", "circular", "kamada_kawai"
    output_path: str = None,
    node_size: int = 3000,
    font_size: int = 10,
    edge_labels: bool = True
) -> str
```

Generate SVG or PNG visualization of the graph.

**Layouts**:
- `hierarchical`: Top-down tree layout
- `spring`: Force-directed layout
- `circular`: Circular layout
- `kamada_kawai`: Balanced aesthetic layout

---

## Data Models

**Path**: `traceai.parsers.base`

### DocumentType

```python
class DocumentType(str, Enum):
    SSIS_PACKAGE = "ssis_package"
    EXCEL_WORKBOOK = "excel_workbook"
    MAINFRAME_JOB = "mainframe_job"
    MAINFRAME_JCL = "mainframe_jcl"
    COBOL_PROGRAM = "cobol_program"
    JSON_CONFIG = "json_config"
    PYTHON_SCRIPT = "python_script"
    SQL_SCRIPT = "sql_script"
    CSV_METADATA = "csv_metadata"
```

### DocumentMetadata

```python
@dataclass
class DocumentMetadata:
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
```

### Component

```python
@dataclass
class Component:
    name: str
    component_id: str
    component_type: str
    description: Optional[str] = None
    source_code: Optional[str] = None
    properties: dict[str, Any] = field(default_factory=dict)
```

### DataSource

```python
@dataclass
class DataSource:
    name: str
    source_id: str
    source_type: str
    connection_string: Optional[str] = None
    server: Optional[str] = None
    database: Optional[str] = None
    file_path: Optional[str] = None
    description: Optional[str] = None
    properties: dict[str, Any] = field(default_factory=dict)
```

### DataEntity

```python
@dataclass
class DataEntity:
    name: str
    entity_type: str  # "table", "sheet", "dataset", "file"
    schema_name: Optional[str] = None
    database_name: Optional[str] = None
    description: Optional[str] = None
    columns: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
```

### Dependency

```python
@dataclass
class Dependency:
    from_id: str
    to_id: str
    dependency_type: str
    properties: dict[str, Any] = field(default_factory=dict)
```

### Parameter

```python
@dataclass
class Parameter:
    name: str
    namespace: Optional[str] = None
    data_type: Optional[str] = None
    value: Any = None
    description: Optional[str] = None
    properties: dict[str, Any] = field(default_factory=dict)
```

### ParsedDocument

```python
@dataclass
class ParsedDocument:
    metadata: DocumentMetadata
    components: list[Component] = field(default_factory=list)
    data_sources: list[DataSource] = field(default_factory=list)
    data_entities: list[DataEntity] = field(default_factory=list)
    dependencies: list[Dependency] = field(default_factory=list)
    parameters: list[Parameter] = field(default_factory=list)
```

---

## Middlewares

**Path**: `traceai.agents.middlewares`

### ConversationMemoryMiddleware

Maintains conversation history using SQLite.

**Constructor**:
```python
ConversationMemoryMiddleware(
    max_messages: int = 30,
    db_path: str = "conversation_history.db"
)
```

### AuditMiddleware

Logs all tool calls and agent actions.

**Constructor**:
```python
AuditMiddleware(
    log_path: str = "audit.log"
)
```

### ProgressTrackingMiddleware

Tracks and displays progress for long operations.

**Constructor**:
```python
ProgressTrackingMiddleware()
```

---

## Helper Patterns

### Quick TraceAI Setup

```python
import asyncio
from pathlib import Path
from traceai.agents import TraceAI


async def bootstrap_agent() -> TraceAI:
    agent = TraceAI(persist_dir=Path("./.traceai"))
    await agent.load_documents("./examples/inputs/ssis")
    return agent
```

Use this pattern to spin up a TraceAI instance wherever synchronous helpers used to exist.

---

## Parser Registry

**Path**: `traceai.parsers.parser_registry`

### get_parser_for_file

```python
def get_parser_for_file(file_path: Path) -> BaseParser | None
```

Get the appropriate parser for a file based on its extension.

**Example**:
```python
from traceai.parsers import parser_registry

parser = parser_registry.get_parser_for_file(Path("package.dtsx"))
if parser:
    parsed = parser.parse(Path("package.dtsx"))
```

---

## Error Handling

### Common Exceptions

```python
# Agent not initialized
ValueError("Agent not initialized. Load documents first.")

# No API key
ValueError("No API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY")

# Invalid model provider
ValueError(f"Unknown model provider: {provider}")

# Parse error
Exception(f"Failed to parse {file_path}: {error}")
```

---

## Type Hints

TraceAI uses comprehensive type hints throughout:

```python
from pathlib import Path
from typing import Any, Optional, Iterator, AsyncIterator
import networkx as nx

# All public APIs are fully typed
def load_documents(directory: Path | str, pattern: str | list[str]) -> None:
    ...

async def query(question: str) -> str:
    ...
```

---

## Version Information

Get version information:

```python
import traceai
print(traceai.__version__)  # "0.1.0"
```

---

## Environment Variables

```bash
# LLM API Keys
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key

# Optional: Disable tokenizer warnings
TOKENIZERS_PARALLELISM=false
```

---

## Performance Tips

1. **Leverage TraceAI's concurrency** for loading 10+ files
2. **Set max_concurrent_parsers** based on CPU cores (default: 10)
3. **Use specific patterns** instead of `**/*` for faster globbing
4. **Enable only needed middlewares** to reduce overhead
5. **Reuse agents** instead of creating new instances

**Example**:
```python
# Good: Fast for large datasets
agent = TraceAI(
    max_concurrent_parsers=20,
    enable_progress=False  # Disable if not needed
)

# Load concurrently
await asyncio.gather(
    agent.load_documents("./cobol", pattern="*.cbl"),
    agent.load_documents("./jcl", pattern="*.jcl")
)
```

---

## Complete Example

```python
import asyncio
from traceai.agents import TraceAI
from traceai.graph.queries import GraphQueries

async def main():
    # 1. Create async agent
    agent = TraceAI(
        model_provider="anthropic",
        max_concurrent_parsers=20
    )

    # 2. Load documents concurrently
    await asyncio.gather(
        agent.load_documents("./ssis"),
        agent.load_documents("./cobol", pattern="*.cbl"),
        agent.load_documents("./json", pattern="*.json")
    )

    # 3. Get graph statistics
    stats = agent.get_graph_stats()
    print(f"Loaded {stats['total_nodes']} nodes, {stats['total_edges']} edges")

    # 4. Query the graph
    queries = GraphQueries(agent.graph)
    lineage = queries.trace_data_lineage("Customer", direction="both")

    print("Upstream:")
    for node_id, data in lineage["upstream"]:
        print(f"  - {data['name']}")

    # 5. AI query (if API key available)
    if agent.agent:
        response = await agent.query("Analyze the data flow for Customer table")
        print(response)

        # Stream response
        async for chunk in agent.query_stream("What transformations are applied?"):
            print(chunk, end="", flush=True)

asyncio.run(main())
```

---

For more examples, see:
- [TESTING.md](./TESTING.md) - Testing guide
- [README.md](../README.md) - Quick start guide
- [examples/scripts/](../examples/scripts/) - Example scripts
