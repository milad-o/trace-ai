# Advanced Agent Features

This document explains advanced capabilities of the Enterprise Assistant agent system.

## 1. Streaming Agent Responses

See the agent's thinking process in real-time, including tool calls and intermediate reasoning.

### Usage

```python
from enterprise_assistant.agents import create_enterprise_agent

agent = create_enterprise_agent(documents_dir="./examples/sample_packages")

# Stream the response
for chunk in agent.analyze_stream("What documents do we have?"):
    messages = chunk.get("messages", [])
    if messages:
        latest = messages[-1]

        # Show tool calls
        if hasattr(latest, "tool_calls") and latest.tool_calls:
            for tc in latest.tool_calls:
                print(f"🔧 Calling tool: {tc['name']}")

        # Show final response
        if hasattr(latest, "content") and latest.content:
            print(f"✨ Response: {latest.content}")
```

### Example Output

```
🔧 Calling tool: graph_query
🔧 Calling tool: semantic_search
✨ Response: We have the following documents:
1. CustomerETL - Extract, transform, and load customer data
2. SalesAggregation - Daily sales aggregation and reporting
```

### Demo Script

Run the streaming demo to see it in action:

```bash
uv run python examples/streaming_demo.py
```

## 2. Middleware for Memory Management

Middleware allows you to intercept and modify agent behavior at different stages.

### Short-Term Memory

Manages conversation history to prevent context overflow:

```python
from langchain.agents.middleware.types import AgentMiddleware

class ConversationMemoryMiddleware(AgentMiddleware):
    def __init__(self, max_messages: int = 20):
        self.max_messages = max_messages

    def before_model(self, state: dict) -> dict | None:
        """Condense conversation if too long."""
        messages = state.get("messages", [])

        if len(messages) > self.max_messages:
            # Keep system message + recent history
            condensed = [messages[0]] + messages[-(self.max_messages - 1):]
            return {"messages": condensed}

        return None
```

### Long-Term Memory

Persists important information across sessions using the "files" state:

```python
class LongTermMemoryMiddleware(AgentMiddleware):
    def __init__(self):
        self.memory_file = "long_term_memory.txt"

    def before_model(self, state: dict) -> dict | None:
        """Inject long-term memory into context."""
        files = state.get("files", {})
        if self.memory_file in files:
            memory = files[self.memory_file]
            # Memory is now available to agent
        return None

    def after_model(self, state: dict) -> dict | None:
        """Update long-term memory."""
        messages = state.get("messages", [])
        if messages:
            latest = messages[-1]
            files = state.get("files", {})

            # Append to memory
            existing = files.get(self.memory_file, "")
            updated = existing + f"\n{latest.content[:100]}"

            return {"files": {**files, self.memory_file: updated}}
        return None
```

### Usage

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    tools=my_tools,
    middleware=[
        ConversationMemoryMiddleware(max_messages=20),
        LongTermMemoryMiddleware()
    ],
    instructions="You are a helpful assistant with memory."
)
```

## 3. Subagents for Specialized Tasks

Delegate complex tasks to specialized sub-agents with domain expertise.

### Example: Data Analyst Subagent

```python
data_analyst_subagent = {
    "name": "data-analyst",
    "description": "Expert at analyzing data lineage, dependencies, and impact analysis",
    "prompt": """You are a data analyst specializing in ETL workflows.

    When analyzing systems:
    - Focus on data flow and dependencies
    - Identify potential bottlenecks
    - Assess impact of changes
    - Trace data lineage from source to destination""",
    "tools": [lineage_tracer, impact_analyzer],  # Specialized tools
}

documentation_writer_subagent = {
    "name": "documentation-writer",
    "description": "Expert at writing clear technical documentation",
    "prompt": """You are a technical writer for enterprise systems.

    When documenting:
    - Write clear, concise descriptions
    - Use proper formatting
    - Include examples and use cases""",
    "tools": [write_file, edit_file],  # File editing tools
}

# Main agent delegates to specialists
main_agent = create_deep_agent(
    tools=general_tools,
    subagents=[data_analyst_subagent, documentation_writer_subagent],
    instructions="""You are a project manager.

    Delegate tasks to specialists:
    - data-analyst: For analyzing data flows
    - documentation-writer: For creating docs"""
)
```

### How It Works

1. User asks: "Analyze the ETL system and document it"
2. Main agent recognizes this needs both analysis and documentation
3. Calls `data-analyst` subagent to analyze
4. Calls `documentation-writer` subagent to document
5. Synthesizes results and returns comprehensive answer

## 4. Human-in-the-Loop Approval

Require human approval for dangerous or sensitive operations.

### Configuration

```python
from langgraph.checkpoint.memory import MemorySaver

def delete_table(table_name: str) -> str:
    """Delete a table. DANGEROUS!"""
    return f"Deleted {table_name}"

def read_table(table_name: str) -> str:
    """Read from table. SAFE."""
    return f"Reading {table_name}"

agent = create_deep_agent(
    tools=[delete_table, read_table],
    tool_configs={
        "delete_table": {
            "allow_respond": True,   # Human can provide feedback
            "allow_edit": True,      # Human can edit arguments
            "allow_accept": True,    # Human can approve/reject
        }
        # read_table has no config = no approval needed
    },
    checkpointer=MemorySaver(),  # Required for interrupts
)
```

### Workflow

```
1. User: "Delete the old_data table"
2. Agent plans: delete_table("old_data")
3. [INTERRUPT] System pauses and asks human
4. Human options:
   - Approve: Tool executes
   - Reject: Agent re-plans
   - Edit: Human modifies args, then tool executes
   - Respond: Human provides feedback, agent re-plans
5. Agent continues based on human choice
```

### Approving Operations

```python
config = {"configurable": {"thread_id": "session-1"}}

# Start execution
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Delete old_data table"}]},
    config=config
):
    # ... execution pauses at delete_table ...
    pass

# Human approves
from langgraph.types import Command

for chunk in agent.stream(
    Command(resume=[{"type": "accept"}]),  # Accept the tool call
    config=config
):
    print(chunk)  # Continues execution
```

## 5. Built-in File System Tools

Deep agents automatically include virtual file system tools:

### Available Tools

- `ls` - List files in virtual workspace
- `read_file` - Read file contents
- `write_file` - Write to a file
- `edit_file` - Edit existing file
- `write_todos` - Create task lists

### Example: Agent Using File Tools

```python
agent = create_deep_agent(
    tools=[],  # Your tools here
    instructions="""You can use file tools to:
    - Store intermediate results
    - Create documentation
    - Plan tasks with write_todos

    Files persist across tool calls within a session."""
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Analyze the system and save findings to report.md"}]
})

# Agent can use write_file to create report.md
# Access the file from result
files = result.get("files", {})
report_content = files.get("report.md", "")
print(report_content)
```

## 6. Memory and State Management

### Session State

Each invocation maintains state across tool calls:

```python
result = agent.invoke({
    "messages": [...],
    "files": {"context.txt": "Previous session data"},
    "custom_state": {"user_preferences": {...}}
})

# State persists and is accessible to all tools
```

### Checkpointing for Persistence

Save state between sessions:

```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()

agent = create_deep_agent(
    tools=my_tools,
    checkpointer=checkpointer,
    instructions="..."
)

# Session 1
config = {"configurable": {"thread_id": "user-123"}}
result1 = agent.invoke({"messages": [...]}, config=config)

# Session 2 (later) - state is restored
result2 = agent.invoke({"messages": [...]}, config=config)
```

## 7. Complete Example: Enterprise Assistant with All Features

```python
from pathlib import Path
from enterprise_assistant.agents import create_enterprise_agent
from langchain.agents.middleware.types import AgentMiddleware

# Custom middleware
class AuditMiddleware(AgentMiddleware):
    def after_model(self, state: dict) -> dict | None:
        """Log all agent actions."""
        messages = state.get("messages", [])
        if messages:
            latest = messages[-1]
            if hasattr(latest, "tool_calls") and latest.tool_calls:
                for tc in latest.tool_calls:
                    print(f"AUDIT: Tool call - {tc['name']}")
        return None

# Create enhanced agent
agent = create_enterprise_agent(
    documents_dir=Path("./examples/sample_packages"),
    model_provider="openai",
    model_name="gpt-4o-mini"
)

# Stream with visualization
query = "What tables are used in CustomerETL?"

print("Streaming agent response...\n")

for chunk in agent.analyze_stream(query):
    messages = chunk.get("messages", [])
    if messages:
        latest = messages[-1]

        # Show tool usage
        if hasattr(latest, "tool_calls") and latest.tool_calls:
            for tc in latest.tool_calls:
                print(f"🔧 {tc['name']}")

        # Show answer
        if hasattr(latest, "content") and latest.content:
            if not hasattr(latest, "tool_calls") or not latest.tool_calls:
                print(f"\n✨ {latest.content}")
```

## Demo Scripts

Try these example scripts:

```bash
# Streaming visualization
uv run python examples/streaming_demo.py

# All advanced features
uv run python examples/advanced_agent_features.py

# Full system demo (graph + agent)
uv run python examples/demo_graph_and_agent.py
```

## Best Practices

1. **Streaming**: Use for long-running queries to show progress
2. **Middleware**: Implement memory management for long conversations
3. **Subagents**: Delegate to specialists for better quality
4. **Human-in-Loop**: Always require approval for destructive operations
5. **Checkpointing**: Enable for multi-session conversations
6. **File Tools**: Use virtual files for intermediate results

## References

- [LangChain Agents Documentation](https://docs.langchain.com/oss/python/langchain/agents)
- [Deep Agents GitHub](https://github.com/langchain-ai/deepagents)
- [LangGraph Middleware](https://docs.langchain.com/oss/python/langchain/middleware)
