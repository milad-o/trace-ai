# TraceAI Web UI

Modern web interface for TraceAI built with Reflex (Pure Python → React).

## Features

- 💬 **Chat Interface** - Stream responses from TraceAI agent
- 📊 **Live Dashboard** - Real-time graph statistics and metrics
- 🔍 **Graph Explorer** - Interactive visualization (coming soon)
- 📈 **Observability** - Token usage, response times, tool calls
- ⚡ **Async Mode** - Concurrent document processing
- 🎨 **Dark Theme** - Modern, professional UI

## Quick Start

```bash
# From project root
cd webui

# Run the web UI
reflex run
```

The UI will be available at [http://localhost:3000](http://localhost:3000)

## Usage

### 1. Load Data

Click **"Load Sample Data"** to load example SSIS packages, or upload your own files.

### 2. Chat

Ask questions about your data:
- "Show statistics"
- "List all documents"
- "Trace lineage for Customer table"

### 3. Monitor

View real-time metrics in the dashboard:
- Graph nodes/edges
- Documents loaded
- Query performance
- Response times

## Architecture

```
webui/
├── webui/
│   ├── __init__.py
│   └── webui.py          # Main application
├── rxconfig.py           # Reflex configuration
├── data/                 # Sqlite DB and vector store
└── README.md
```

## State Management

The app uses Reflex's state management:

```python
class State(rx.State):
    messages: list[Message]  # Chat history
    agent: TraceAI           # Async TraceAI agent
    graph_nodes: int         # Graph statistics
    total_queries: int       # Observability metrics
```

## Components

### Chat Panel
- Message history
- User input
- Streaming responses
- Tool call visualization

### Dashboard Panel
- Graph statistics cards
- Performance metrics
- Document summary
- Query history

## Customization

### Theme

Edit `THEME` in `webui/webui.py`:

```python
THEME = {
    "primary": "#2563eb",    # Change primary color
    "bg": "#0f172a",         # Background
    "surface": "#1e293b",    # Card backgrounds
}
```

### Model

Change model in settings or directly in state:

```python
model_provider: str = "anthropic"  # or "openai"
model_name: str = "claude-3-5-sonnet-20241022"
```

## Development

```bash
# Hot reload during development
reflex run --loglevel debug

# Export static site
reflex export

# Deploy
reflex deploy
```

## Coming Soon

- [ ] Interactive graph visualization with Plotly
- [ ] File upload interface
- [ ] Export functionality (JSON/CSV/Excel)
- [ ] Advanced filtering and search
- [ ] Multi-tab interface
- [ ] Settings panel
- [ ] Dark/light theme toggle
- [ ] User authentication

## Requirements

- Python 3.11+
- Node.js 16+ (for Reflex frontend compilation)
- TraceAI installed (`pip install -e ..`)

## Troubleshooting

**Issue**: `reflex: command not found`
- **Solution**: Ensure Reflex is installed: `uv add reflex`

**Issue**: Frontend compilation fails
- **Solution**: Install Node.js: `brew install node` (macOS) or visit [nodejs.org](https://nodejs.org)

**Issue**: No data loaded
- **Solution**: Click "Load Sample Data" or check `examples/inputs/` directory exists

## Performance

- Async mode with 20 concurrent parsers
- Real-time updates without page refresh
- Optimized state management
- WebSocket streaming for chat

## License

MIT License - Part of TraceAI project
