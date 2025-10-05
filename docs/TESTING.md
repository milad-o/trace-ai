# Testing Guide

Comprehensive testing suite for TraceAI covering all APIs, parsers, tools, and performance benchmarks.

## Test Structure

```
tests/
├── test_enterprise_agent.py          # Sync agent API tests (21 tests)
├── test_async_enterprise_agent.py    # Async agent API tests (20 tests)
├── test_all_parsers.py               # All parser tests (30 tests)
├── test_code_generation.py           # Code generation tools (15 tests)
├── test_ai_integration.py            # AI-enabled integration tests (20 tests)
├── test_performance.py               # Performance benchmarks (10 tests)
├── test_comprehensive_summary.py     # End-to-end validation (7 tests)
├── test_graph.py                     # Graph operations (existing)
├── test_graph_tools.py               # Graph tools (existing)
├── test_ssis_parser.py               # SSIS parser (existing)
├── test_visualization.py             # Visualization (existing)
├── test_middlewares.py               # Middlewares (existing)
├── test_memory_stores.py             # Memory stores (existing)
└── test_real_scenarios.py            # Realistic scenarios (existing)
```

**Total: 207 tests**

## Running Tests

### Quick Test (No API Key Required)

Run tests that don't need AI:

```bash
# Run all non-AI tests
uv run pytest tests/ -v --no-cov -m "not slow" -k "not ai_integration"

# Run specific test suites
uv run pytest tests/test_enterprise_agent.py -v
uv run pytest tests/test_async_enterprise_agent.py -v
uv run pytest tests/test_all_parsers.py -v
uv run pytest tests/test_code_generation.py -v
```

### AI-Enabled Tests (Requires API Key)

```bash
# Set API key
export ANTHROPIC_API_KEY=your_key_here
# or
export OPENAI_API_KEY=your_key_here

# Run AI integration tests
uv run pytest tests/test_ai_integration.py -v

# Run realistic scenarios
uv run pytest tests/test_real_scenarios.py -v
```

### Performance Benchmarks

Compare sync vs async performance:

```bash
# Run performance tests
uv run pytest tests/test_performance.py -v

# Run with benchmark plugin for detailed stats
uv run pytest tests/test_performance.py -v --benchmark-only
```

### All Tests with Coverage

```bash
# Run all tests with coverage report
uv run pytest --cov=traceai --cov-report=term-missing

# Generate HTML coverage report
uv run pytest --cov=traceai --cov-report=html
```

## Test Categories

### 1. API Tests

**Sync Agent Tests** (`test_enterprise_agent.py`):
- Agent initialization (with/without API key)
- Document loading (single/multiple formats)
- Graph statistics and queries
- Vector store indexing
- Pattern-based file loading
- Error handling
- Middleware configuration
- Incremental loading

**Async Agent Tests** (`test_async_enterprise_agent.py`):
- Async initialization
- Concurrent document loading
- Streaming responses
- Configurable concurrency limits
- Large dataset handling

### 2. Parser Tests

**All Parsers** (`test_all_parsers.py`):
- ✅ SSIS Parser - .dtsx packages
- ✅ JSON Parser - .json configs
- ✅ CSV Parser - .csv lineage mappings
- ✅ Excel Parser - .xlsx workbooks
- ✅ COBOL Parser - .cbl programs
- ✅ JCL Parser - .jcl job control

Each parser test validates:
- Initialization and registration
- File parsing
- Component extraction
- Property decorators

### 3. Code Generation Tests

**Generation Tools** (`test_code_generation.py`):
- ✅ JSON export - Graph to JSON with metadata
- ✅ CSV export - Lineage/nodes/edges to CSV
- ✅ Excel export - Multi-sheet reports
- ✅ Python generator - COBOL/JCL to Python

Tests validate:
- Tool initialization
- File generation
- Data consistency
- Export formats

### 4. AI Integration Tests

**AI-Enabled Workflows** (`test_ai_integration.py`):
- Basic queries and document listing
- Data lineage tracing
- Impact analysis
- Multi-step reasoning
- Semantic search
- Conversational memory
- Tool usage verification
- Error handling

**Note**: These tests require an API key and are automatically skipped if none is available.

### 5. Performance Tests

**Benchmarks** (`test_performance.py`):
- Sync vs async loading comparison
- Single directory performance
- Multiple directory performance
- Large dataset handling (50+ files)
- Memory usage validation
- Concurrency level optimization

**Expected Results**:
- Async 5-10x faster for large datasets
- Similar performance for small datasets
- Linear scaling with concurrency

### 6. Comprehensive Summary

**End-to-End Validation** (`test_comprehensive_summary.py`):
- All parsers registered correctly
- Sync agent complete workflow
- Async agent complete workflow
- Parser properties validation
- Graph tools availability
- Code generation tools instantiation
- Export formats verification

## Test Data

Sample data is located in `examples/inputs/`:

```
examples/inputs/
├── ssis/          # 2 SSIS packages
├── cobol/         # 42 COBOL programs
├── jcl/           # 36 JCL jobs
├── json/          # 3 JSON configs
├── csv/           # 3 CSV lineage files
└── excel/         # 2 Excel workbooks
```

## Writing New Tests

### Test Template

```python
import pytest
from pathlib import Path
import tempfile

from traceai.agents import EnterpriseAgent

@pytest.fixture
def temp_persist_dir():
    """Create temporary directory for agent data."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

def test_my_feature(temp_persist_dir):
    """Test description."""
    agent = EnterpriseAgent(persist_dir=temp_persist_dir)

    # Test logic here
    assert True
```

### Async Test Template

```python
import pytest
from traceai.agents import AsyncEnterpriseAgent

@pytest.mark.asyncio
async def test_async_feature():
    """Test async feature."""
    agent = AsyncEnterpriseAgent()
    await agent.load_documents("path/to/docs")

    assert agent.graph is not None
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install uv
      - run: uv sync
      - run: uv run pytest --cov=traceai
```

## Troubleshooting

### Common Issues

**Issue**: `No API key found`
- **Solution**: Set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` environment variable
- **Note**: Graph-only tests work without API keys

**Issue**: `Sample file not found`
- **Solution**: Ensure you're running from project root: `uv run pytest tests/`

**Issue**: `Import errors`
- **Solution**: Reinstall dependencies: `uv sync`

**Issue**: Performance tests fail
- **Solution**: Ensure sufficient sample data in `examples/inputs/`

## Test Coverage Goals

Target coverage by module:

| Module | Target | Current |
|--------|--------|---------|
| Parsers | 90% | TBD |
| Graph Tools | 85% | TBD |
| Agents | 80% | TBD |
| Code Generation | 75% | TBD |
| Overall | 80% | TBD |

## Performance Baselines

Expected performance on standard hardware:

| Operation | Sync | Async | Speedup |
|-----------|------|-------|---------|
| Load 2 SSIS files | ~0.5s | ~0.3s | 1.7x |
| Load 50 COBOL files | ~10s | ~2s | 5x |
| Load 100 mixed files | ~20s | ~3s | 6.7x |

## Next Steps

- [ ] Add integration tests for all parsers with real-world files
- [ ] Add stress tests for 1000+ files
- [ ] Add memory profiling tests
- [ ] Add concurrent query benchmarks
- [ ] Add visualization output validation
