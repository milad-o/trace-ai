# TraceAI

**Pluggable ETL Intelligence for DeepAgents** 🚀

TraceAI provides domain-specific tools, knowledge graphs, and specialized sub-agents for ETL/lineage analysis. It's designed as a **capability plugin** that you can add to ANY DeepAgent system, not a standalone agent.

[![Tests](https://img.shields.io/badge/tests-207%20total-brightgreen)](tests/)
[![Docs](https://img.shields.io/badge/docs-complete-blue)](docs/)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

---

## 🎯 What is TraceAI?

TraceAI is a **capability module** that adds ETL/lineage analysis expertise to DeepAgents. Think of it as a plugin that provides:

- ✅ **Domain Tools**: Lineage tracing, impact analysis, semantic search
- ✅ **Knowledge Graph**: Parse SSIS/COBOL/JCL → NetworkX graph
- ✅ **Vector Search**: Semantic search over enterprise documents
- ✅ **Specialized Sub-Agents**: Search, lineage, code generation, parsing
- ✅ **Custom Middleware**: Audit logging, memory, progress tracking

**TraceAI provides domain expertise. DeepAgents provides orchestration. Together = Powerful!**

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

### Option 1: Web UI (Recommended) 🎨

Launch the modern web interface with chat, dashboards, and real-time monitoring:

```bash
reflex run
```

Open [http://localhost:3000](http://localhost:3000)

**Features:**
- 💬 Interactive chat with streaming responses
- 📊 Real-time dashboards and metrics
- 🔍 Graph visualization
- 📈 Performance monitoring
- ⚡ Async mode (10x faster)

See [docs/WEBUI.md](docs/WEBUI.md) for full documentation.

### Option 2: Python API

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

### Integration Pattern (Capability Plugin)

```python
import asyncio
from deepagents import create_deep_agent
from traceai.capabilities import TraceAICapability

async def main():
    # Initialize TraceAI capability
    traceai_cap = TraceAICapability()
    
    # Load your ETL documents (SSIS/COBOL/JCL)
    await traceai_cap.load_documents(
        directory="./your_etl_packages",
        pattern=["**/*.dtsx", "**/*.cbl", "**/*.jcl"]
    )
    
    # Plug into your DeepAgent
    agent = create_deep_agent(
        model=llm,
        tools=traceai_cap.get_tools(),           # ETL analysis tools
        subagents=traceai_cap.get_subagents(),   # Optional specialists
        middleware=traceai_cap.get_middleware(), # Custom middleware
        instructions="""
        You have ETL analysis capabilities from TraceAI:
        - semantic_search: Find documents/components
        - trace_lineage: Track data flows
        - analyze_impact: Assess change impact
        - graph_query: Query knowledge graph
        """
    )
    
    # Use natural language
    response = await agent.arun("""
    Analyze the CustomerETL pipeline:
    1. Find all data sources
    2. Trace lineage to target tables
    3. Identify potential issues
    """)
    
    print(response)

asyncio.run(main())
```

### Graph-Only Mode (No API Key)

```python
from traceai.capabilities import TraceAICapability
from traceai.graph.queries import GraphQueries

async def main():
    # Initialize capability
    traceai_cap = TraceAICapability()
    await traceai_cap.load_documents("./your_etl_packages")
    
    # Direct graph queries (no LLM needed)
    queries = GraphQueries(traceai_cap.graph)
    
    # Find tasks affected by table change
    readers = queries.find_tasks_reading_from_table("Customer")
    writers = queries.find_tasks_writing_to_table("Customer")
    
    print(f"⚠️  IMPACT: {len(readers) + len(writers)} tasks affected")
    for task_id, task_data in readers + writers:
        print(f"  - {task_data['name']}")

asyncio.run(main())
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

### Plugin Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       YOUR APPLICATION                           │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    DeepAgent System                        │ │
│  │                                                            │ │
│  │  Planning, Filesystem, Summarization (Auto-included)      │ │
│  │                                                            │ │
│  │  ┌────────────────────────────────────────────────────┐   │ │
│  │  │        🔌 TraceAI Capability Plugin 🔌            │   │ │
│  │  │                                                    │   │ │
│  │  │  Tools: semantic_search, trace_lineage,          │   │ │
│  │  │         analyze_impact, graph_query, ...         │   │ │
│  │  │                                                    │   │ │
│  │  │  Sub-Agents: search_specialist,                  │   │ │
│  │  │              lineage_analyst,                     │   │ │
│  │  │              code_generator,                      │   │ │
│  │  │              parser_expert                        │   │ │
│  │  │                                                    │   │ │
│  │  │  Middleware: Audit, Memory, Progress             │   │ │
│  │  └────────────────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   TraceAI Domain Knowledge                       │
│  Knowledge Graph (NetworkX) + Vector Store (Chroma)             │
│  Parsed Documents (SSIS/COBOL/JCL)                              │
└─────────────────────────────────────────────────────────────────┘
```

### What TraceAI Provides (Domain Expertise)
- **Multi-Format Parsers** - SSIS, COBOL, JCL, JSON, Excel, CSV → Knowledge graphs
- **11 Specialized Tools** - Lineage tracing, impact analysis, code generation
- **Knowledge Graph** - NetworkX graph of ETL components and data flows
- **Vector Search** - Semantic search over enterprise documents
- **Code Generators** - Export to JSON/CSV/Excel, COBOL/JCL to Python conversion
- **Custom Middleware** - Audit logging, memory persistence, progress tracking
- **Specialized Sub-Agents** - Search, lineage, code gen, parsing experts

### What DeepAgents Provides (Orchestration)
- **Planning** - Multi-step task planning and execution
- **Filesystem** - Read/write files during execution
- **Sub-Agent Framework** - Delegation to specialized agents
- **Summarization** - Context management
- **Prompt Caching** - Efficient token usage

**See [dev_docs/CAPABILITY_ARCHITECTURE.md](dev_docs/CAPABILITY_ARCHITECTURE.md) for detailed architecture.**

---

## ⚡ Async Mode (NEW!)

TraceAI now supports **async/concurrent processing** for massive performance gains:

```python
import asyncio

from traceai.agents import TraceAI


async def main():
    agent = TraceAI(max_concurrent_parsers=20)

    await asyncio.gather(
        agent.load_documents("./ssis_packages"),
        agent.load_documents("./cobol_programs"),
        agent.load_documents("./jcl_jobs"),
    )

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
| Sequential (await each load) | 45.2s | 1.0x |
| Concurrent (await gather) | 4.8s | **9.4x** |

**Benefits:**
- ✅ **10x faster** document loading (concurrent parsing)
- ✅ **Streaming responses** (see results as they arrive)
- ✅ **Parallel LLM calls** (batch multiple queries)
- ✅ **Background indexing** (vector store operations)
- ✅ **Same API** (just add `async`/`await`)

## 📊 Performance

### Sequential Mode
| Operation | Time | Notes |
|-----------|------|-------|
| Parse SSIS package | ~100ms | Per .dtsx file |
| Build knowledge graph | ~50ms | 35 nodes, 40 edges |
| Query graph | <1ms | Find nodes, trace lineage |
| Impact analysis | <10ms | Find affected tasks |
| Semantic search | ~50ms | Vector similarity search |
| AI simple query | 2-5s | With API key |
| AI complex analysis | 10-30s | Multi-step planning |

### Concurrent Mode
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
