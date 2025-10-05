# 🚀 Quick Start Guide

## Get Started in 3 Minutes

### 1. **Ask a Question**
```bash
uv run trace-ai ask ./examples/sample_packages \
  "What documents do we have?"
```

### 2. **Create a Visualization**
```bash
uv run trace-ai ask ./examples/sample_packages \
  "Create a hierarchical visualization of the CustomerETL package in SVG format"

# View the result
open data/visualizations/CustomerETL.svg
```

### 3. **Interactive Session**
```bash
uv run trace-ai analyze ./examples/sample_packages

# Then ask multiple questions:
# - "What tasks are in CustomerETL?"
# - "Trace the data lineage for the Customer table"
# - "Create visualizations for both packages"
# - "/stats" to see graph statistics
# - "/quit" to exit
```

## What Can I Do?

### 📊 **Visualizations**
```
"Create a hierarchical visualization of [package_name] in SVG format"
"Generate a spring layout diagram showing data flow connections"
"Create PNG images for all packages"
```

### 🔍 **Analysis**
```
"What tables are used in CustomerETL?"
"Trace data lineage for the Sales table"
"What will be impacted if I modify the Customer table?"
"Show me all task dependencies in SalesAggregation"
```

### 📋 **Complex Queries** (Agent uses planning)
```
"Create visualizations for all packages and compare their structures"
"Analyze all data flows and generate a comprehensive report"
"Find all tables accessed across all packages"
```

### 📈 **Statistics**
```
"Show me statistics about the knowledge graph"
"How many packages, tasks, and tables do we have?"
"/stats" (in interactive mode)
```

## Features

- ✅ **7 Tools:** graph queries, lineage tracing, impact analysis, semantic search, visualization
- ✅ **Planning:** Agent breaks down complex tasks with write_todos
- ✅ **Memory:** Manages conversation context (30 message limit)
- ✅ **Audit:** Logs all tool calls for transparency
- ✅ **Progress:** Shows progress through multi-step tasks

## Examples

See working examples in `examples/`:
- `demo_all_features.py` - Complete feature showcase
- `demo_graph_and_agent.py` - Graph + agent demonstration
- `streaming_demo.py` - See agent thinking process
- `test_agent.py` - Quick functionality test

## Documentation

- **[PHASE_8_COMPLETE.md](PHASE_8_COMPLETE.md)** - Full feature list
- **[CAPABILITY_ASSESSMENT.md](CAPABILITY_ASSESSMENT.md)** - What we can/can't do
- **[ADVANCED_FEATURES.md](ADVANCED_FEATURES.md)** - Advanced usage
- **[CONVERSATION_SUMMARY.md](CONVERSATION_SUMMARY.md)** - FAQ

## Need Help?

Run demos to see features in action:
```bash
# All features
uv run python examples/demo_all_features.py

# Graph visualization
uv run python examples/demo_graph_and_agent.py

# Streaming responses
uv run python examples/streaming_demo.py
```
