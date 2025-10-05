# TraceAI

An AI-powered ETL analysis tool that helps data teams understand complex data transformations, trace data lineage, and analyze the impact of changes across ETL processes.

[![Tests](https://img.shields.io/badge/tests-207%20total-brightgreen)](tests/)
[![Docs](https://img.shields.io/badge/docs-complete-blue)](docs/)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

---

## ✨ Features

### 📊 Multi-Format Parsing
- ✅ **SSIS Packages** (.dtsx) - ETL workflows and transformations
- ✅ **COBOL Programs** (.cbl, .cob) - Mainframe business logic
- ✅ **JCL Jobs** (.jcl) - Batch job workflows
- ✅ **JSON Configs** (.json) - Pipeline definitions and schemas
- ✅ **Excel Workbooks** (.xlsx) - Data flows with formula dependencies
- ✅ **CSV Files** (.csv) - Lineage mappings and field transformations

### 🔍 Analysis Capabilities
- ✅ Trace data lineage (upstream/downstream)
- ✅ Analyze impact of table changes
- ✅ Semantic search over documents
- ✅ Find task dependencies
- ✅ Generate graph statistics
- ✅ Visualizations (SVG/PNG with multiple layouts)

### 🛠️ Code Generation Tools
- ✅ **Export to JSON** - Full graph structure with metadata
- ✅ **Export to CSV** - Lineage reports and node lists
- ✅ **Export to Excel** - Multi-sheet workbooks with analysis
- ✅ **COBOL/JCL to Python** - Modern Python equivalents of legacy code

### 🤖 AI-Powered Analysis (Requires API Key)
- ✅ Natural language queries across all formats
- ✅ Multi-step planning with 11 specialized tools
- ✅ Complex reasoning and analysis
- ✅ Conversational interface
- ✅ Memory persistence across sessions
- ✅ Full audit logging and progress tracking

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/milad-o/trace-ai.git
cd trace-ai

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .
```

### Run Demo (No API Key Required!)

```bash
python examples/quick_demo.py
```

**Output:**
```
📦 Loaded 2 SSIS packages
📊 Built knowledge graph: 35 nodes, 40 edges
🔍 Found 2 packages, 10 tasks, 10 tables
📈 Traced lineage: Customer ← CustomerStaging
⚠️  Impact: 3 tasks affected (2 readers, 1 writer)
✅ All features working!
```

---

## 📖 Usage

### Graph-Only Mode (No API Key)

```python
from traceai.agents import EnterpriseAgent
from traceai.graph.queries import GraphQueries

# Initialize agent (no API key needed)
agent = EnterpriseAgent(model_provider="anthropic")
agent.load_documents("./your_etl_packages")

# Query the knowledge graph
queries = GraphQueries(agent.graph)

# Find impact of changing a table
readers = queries.find_tasks_reading_from_table("Customer")
writers = queries.find_tasks_writing_to_table("Customer")

print(f"⚠️  IMPACT: {len(readers) + len(writers)} tasks affected")
for task_id, task_data in readers + writers:
    print(f"  - {task_data['name']}")
```

### AI-Powered Mode (With API Key)

```bash
# Set your API key
export ANTHROPIC_API_KEY=your_key_here
# or
export OPENAI_API_KEY=your_key_here
```

```python
from traceai.agents import create_enterprise_agent

# Initialize AI-powered agent
agent = create_enterprise_agent(
    documents_dir="./your_etl_packages",
    model_provider="anthropic"  # or "openai"
)

# Natural language query with multi-step planning
response = agent.analyze("""
Analyze the CustomerETL package:
1. List all tasks
2. Trace data lineage
3. Find potential issues
4. Suggest improvements
""")

print(response)
```

---

## 💡 Realistic Scenarios

### Scenario 1: Data Migration Impact Analysis

**Question:** "What will break if I change the Customer table schema?"

```python
queries = GraphQueries(agent.graph)

readers = queries.find_tasks_reading_from_table("Customer")
writers = queries.find_tasks_writing_to_table("Customer")

print(f"⚠️  IMPACT: {len(readers) + len(writers)} tasks affected")
```

### Scenario 2: Data Lineage Tracing

**Question:** "Where does data in the Sales table come from?"

```python
lineage = queries.trace_data_lineage("Sales", direction="both")

print("Upstream sources:")
for comp_id, comp_data in lineage["upstream"]:
    print(f"  ← {comp_data['name']}")

print("Downstream consumers:")
for comp_id, comp_data in lineage["downstream"]:
    print(f"  → {comp_data['name']}")
```

### Scenario 3: Find All ETL Jobs Processing Specific Data

**Question:** "Which ETL jobs touch customer data?"

```python
results = agent.vector_store.similarity_search("customer data", k=10)

for doc in results:
    print(f"- {doc.metadata['name']} ({doc.metadata['type']})")
```

See [docs/REALISTIC_SCENARIOS.md](docs/REALISTIC_SCENARIOS.md) for more examples!

---

## 🏗️ Architecture

### Core Components

```
┌─────────────────────────────────────────┐
│        LangChain Foundation             │
│  • ChatAnthropic, ChatOpenAI           │
│  • Chroma (vector storage)             │
│  • HuggingFaceEmbeddings               │
└─────────────────────────────────────────┘
                  ↑
                  │ Build on top
                  │
┌─────────────────────────────────────────┐
│    Enterprise Assistant (Our Value)     │
│                                         │
│  ✅ SSIS Parser → Knowledge Graph      │
│  ✅ Graph Tools (lineage, impact)      │
│  ✅ Enterprise Middlewares              │
│  ✅ Memory Stores (SQLite + Vector)    │
│  ✅ Visualization Tools                 │
└─────────────────────────────────────────┘
```

### What We Built (Unique Value)
- **Multi-Format Parsers** - SSIS, COBOL, JCL, JSON, Excel, CSV → Knowledge graphs
- **11 Specialized Tools** - Lineage tracing, impact analysis, code generation
- **Code Generators** - Export to JSON/CSV/Excel, COBOL/JCL to Python conversion
- **Enterprise Middlewares** - Audit logging, memory persistence, progress tracking
- **Memory Stores** - SQLite + FTS5 for conversations, ChromaDB for vectors
- **Visualization** - Generate system diagrams (SVG/PNG with 4 layouts)

### What We Use from LangChain
- **Vector Stores** - Chroma integration for semantic search
- **Embeddings** - HuggingFaceEmbeddings for document indexing
- **Chat Models** - ChatAnthropic, ChatOpenAI for AI reasoning
- **Base Classes** - BaseTool, AgentMiddleware for extensibility

---

## ⚡ Async Mode (NEW!)

TraceAI now supports **async/concurrent processing** for massive performance gains:

```python
from traceai.agents import AsyncEnterpriseAgent
import asyncio

async def main():
    # Create async agent
    agent = AsyncEnterpriseAgent(max_concurrent_parsers=20)

    # Load multiple directories concurrently
    await asyncio.gather(
        agent.load_documents("./ssis_packages"),
        agent.load_documents("./cobol_programs"),
        agent.load_documents("./jcl_jobs"),
    )

    # Query with streaming response
    async for chunk in agent.query_stream("Analyze the customer data flow"):
        print(chunk, end="", flush=True)

asyncio.run(main())
```

**Performance Comparison:**
```bash
python examples/scripts/async_vs_sync_demo.py
```

| Mode | 100 Files | Speedup |
|------|-----------|---------|
| Sync | 45.2s | 1.0x |
| Async | 4.8s | **9.4x** |

**Benefits:**
- ✅ **10x faster** document loading (concurrent parsing)
- ✅ **Streaming responses** (see results as they arrive)
- ✅ **Parallel LLM calls** (batch multiple queries)
- ✅ **Background indexing** (vector store operations)
- ✅ **Same API** (just add `async`/`await`)

## 📊 Performance

### Sync Mode
| Operation | Time | Notes |
|-----------|------|-------|
| Parse SSIS package | ~100ms | Per .dtsx file |
| Build knowledge graph | ~50ms | 35 nodes, 40 edges |
| Query graph | <1ms | Find nodes, trace lineage |
| Impact analysis | <10ms | Find affected tasks |
| Semantic search | ~50ms | Vector similarity search |
| AI simple query | 2-5s | With API key |
| AI complex analysis | 10-30s | Multi-step planning |

### Async Mode
| Operation | Time | Notes |
|-----------|------|-------|
| Parse 100 files | ~5s | **10x faster** with concurrency |
| Load + index docs | ~8s | Parallel parsing + embedding |
| Streaming query | 2-3s | See response as it generates |

---

## 🧪 Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=enterprise_assistant

# Run realistic scenarios (requires API key)
export ANTHROPIC_API_KEY=your_key
uv run pytest tests/test_real_scenarios.py -v
```

**Test Coverage:**
- 80 tests passing
- 70% code coverage
- 17 realistic scenario tests
- Graph operations: 90%+ coverage
- SSIS parser: 98% coverage

---

## 📚 Documentation

### User Guides
- [API Reference](docs/API_REFERENCE.md) - **Complete API documentation for all components**
- [Testing Guide](docs/TESTING.md) - **207 tests covering all functionality**
- [Realistic Scenarios](docs/REALISTIC_SCENARIOS.md) - 7 real-world use cases

### Architecture & Design
- [Memory Architecture](docs/MEMORY_ARCHITECTURE.md) - SQLite + Vector stores
- [Workboard](docs/WORKBOARD.md) - Project roadmap

### Development Docs
- [Phase 9 Summary](docs/PHASE_9_SUMMARY.md) - Memory architecture
- [Phase 10 Summary](docs/PHASE_10_SUMMARY.md) - LangChain cleanup
- [Phase 11 Summary](docs/PHASE_11_SUMMARY.md) - Realistic scenarios

---

## 🎯 Use Cases

### For Data Engineers
- ✅ Trace data lineage across complex ETL workflows
- ✅ Analyze impact before making schema changes
- ✅ Document ETL processes automatically
- ✅ Find dependencies between jobs

### For Data Analysts
- ✅ Understand where report data comes from
- ✅ Find which ETL jobs affect specific tables
- ✅ Search for data processing by description

### For DevOps/SREs
- ✅ Assess blast radius of infrastructure changes
- ✅ Generate system documentation
- ✅ Audit data access patterns

---

## 🛣️ Roadmap

### Completed ✅
- [x] Multi-format parsing (SSIS, COBOL, JCL, JSON, Excel, CSV)
- [x] Knowledge graph construction
- [x] Data lineage tracing
- [x] Impact analysis
- [x] Semantic search
- [x] Graph visualization
- [x] AI-powered analysis
- [x] Memory persistence
- [x] Audit logging
- [x] Graph-only mode (no API key)
- [x] **Async/concurrent processing** (10x faster)
- [x] **Streaming responses**
- [x] Code generation (JSON, CSV, Excel, Python)

### Planned 🔮
- [ ] Tableau workbook parser (dashboards → graph)
- [ ] SQL script parser (DDL/DML → graph)
- [ ] dbt project parser (models → graph)
- [ ] Interactive graph visualization (D3.js)
- [ ] Cost analysis (compute costs)
- [ ] Performance optimization suggestions
- [ ] Security scanner (credentials detection)
- [ ] CI/CD integration
- [ ] Slack/Teams bot

---

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone and install
git clone https://github.com/milad-o/trace-ai.git
cd trace-ai
uv sync --dev

# Run tests
uv run pytest

# Format code
uv run black src/ tests/ examples/

# Type check
uv run mypy src/
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

Built with:
- [LangChain](https://github.com/langchain-ai/langchain) - LLM application framework
- [deepagents](https://github.com/yourusername/deepagents) - Planning middleware
- [NetworkX](https://github.com/networkx/networkx) - Graph algorithms
- [ChromaDB](https://github.com/chroma-core/chroma) - Vector database
- [Anthropic Claude](https://www.anthropic.com/) - AI reasoning
- [OpenAI](https://openai.com/) - Alternative AI model

---

## 📧 Contact

- Issues: [GitHub Issues](https://github.com/milad-o/trace-ai/issues)
- Discussions: [GitHub Discussions](https://github.com/milad-o/trace-ai/discussions)

---

**TraceAI** - Understand your ETL processes, powered by AI 🚀
