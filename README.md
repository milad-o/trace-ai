# TraceAI

An AI-powered ETL analysis tool that helps data teams understand complex data transformations, trace data lineage, and analyze the impact of changes across ETL processes.

[![Tests](https://img.shields.io/badge/tests-80%20passing-brightgreen)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-70%25-yellow)](tests/)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

---

## ✨ Features

### 🆓 Works Without API Key (Graph-Only Mode)
- ✅ Parse SSIS packages into knowledge graphs
- ✅ Trace data lineage (upstream/downstream)
- ✅ Analyze impact of table changes
- ✅ Semantic search over documents
- ✅ Find task dependencies
- ✅ Generate graph statistics
- ✅ Export visualizations (SVG/PNG)

### 🤖 AI-Powered (Requires API Key)
- ✅ Natural language queries
- ✅ Multi-step planning with write_todos
- ✅ Complex analysis and reasoning
- ✅ Conversational interface
- ✅ Memory persistence across sessions
- ✅ Audit logging and progress tracking

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
from enterprise_assistant.agents import EnterpriseAgent
from enterprise_assistant.graph.queries import GraphQueries

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
from enterprise_assistant.agents import create_enterprise_agent

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
- **SSIS Parser** - Parse .dtsx XML into structured knowledge graphs
- **Graph Tools** - Lineage tracing, impact analysis, dependency mapping
- **Enterprise Middlewares** - Audit logging, memory persistence, progress tracking
- **Memory Stores** - SQLite + FTS5 for conversations, ChromaDB/Pinecone for vectors
- **Visualization** - Generate enterprise system diagrams (SVG/PNG)

### What We Use from LangChain
- **Vector Stores** - Chroma integration for semantic search
- **Embeddings** - HuggingFaceEmbeddings for document indexing
- **Chat Models** - ChatAnthropic, ChatOpenAI for AI reasoning
- **Base Classes** - BaseTool, AgentMiddleware for extensibility

---

## 📊 Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Parse SSIS package | ~100ms | Per .dtsx file |
| Build knowledge graph | ~50ms | 35 nodes, 40 edges |
| Query graph | <1ms | Find nodes, trace lineage |
| Impact analysis | <10ms | Find affected tasks |
| Semantic search | ~50ms | Vector similarity search |
| AI simple query | 2-5s | With API key |
| AI complex analysis | 10-30s | Multi-step planning |

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

- [Realistic Scenarios Guide](docs/REALISTIC_SCENARIOS.md) - 7 real-world use cases
- [Phase 9 Summary](docs/PHASE_9_SUMMARY.md) - Memory architecture
- [Phase 10 Summary](docs/PHASE_10_SUMMARY.md) - LangChain cleanup
- [Phase 11 Summary](docs/PHASE_11_SUMMARY.md) - Realistic scenarios
- [Memory Architecture](docs/MEMORY_ARCHITECTURE.md) - SQLite + Vector stores
- [Workboard](docs/WORKBOARD.md) - Project roadmap

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
- [x] SSIS package parsing
- [x] Knowledge graph construction
- [x] Data lineage tracing
- [x] Impact analysis
- [x] Semantic search
- [x] Graph visualization
- [x] AI-powered analysis
- [x] Memory persistence
- [x] Audit logging
- [x] Graph-only mode (no API key)

### Planned 🔮
- [ ] Excel workbook parser (formulas → graph)
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
