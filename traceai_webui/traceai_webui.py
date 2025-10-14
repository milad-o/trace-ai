"""TraceAI Web UI - Modern chat interface with dashboards and observability.

Built with Reflex (Pure Python → React).
"""

import asyncio
from datetime import datetime
from pathlib import Path

import reflex as rx

from traceai.agents import TraceAI
from traceai.graph.queries import GraphQueries


# Theme configuration
THEME = {
    "primary": "#2563eb",  # Blue
    "secondary": "#7c3aed",  # Purple
    "success": "#10b981",  # Green
    "warning": "#f59e0b",  # Orange
    "danger": "#ef4444",  # Red
    "bg": "#0f172a",  # Dark blue-gray
    "surface": "#1e293b",
    "text": "#f1f5f9",
}


class Message(rx.Base):
    """Chat message model."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = datetime.now()
    tool_calls: list[dict] = []


# Global agent instance (not stored in State due to serialization)
_agent: TraceAI | None = None


def get_agent() -> TraceAI:
    """Get or create the global agent instance."""
    global _agent
    if _agent is None:
        _agent = TraceAI(
            model_provider="anthropic",
            persist_dir="./data",
            max_concurrent_parsers=20
        )
    return _agent


class State(rx.State):
    """Application state."""

    # Chat state
    messages: list[Message] = []
    current_input: str = ""
    is_processing: bool = False

    # Agent state
    agent_initialized: bool = False
    documents_loaded: int = 0
    graph_nodes: int = 0
    graph_edges: int = 0

    # Observability
    total_queries: int = 0
    total_tokens: int = 0
    avg_response_time: float = 0.0

    # Settings
    model_provider: str = "anthropic"
    model_name: str = "claude-3-5-sonnet-20241022"
    max_concurrent: int = 20

    # Upload state
    uploaded_files: list[str] = []

    async def initialize_agent(self):
        """Initialize the TraceAI agent."""
        agent = get_agent()
        self.agent_initialized = True

    async def load_sample_data(self):
        """Load sample data for demo."""
        await self.initialize_agent()
        agent = get_agent()

        # Load sample documents
        ssis_dir = Path("examples/inputs/ssis")
        if ssis_dir.exists():
            await agent.load_documents(ssis_dir)

            # Update stats
            if agent.graph:
                self.graph_nodes = agent.graph.number_of_nodes()
                self.graph_edges = agent.graph.number_of_edges()
                self.documents_loaded = len(agent.parsed_documents)

        return rx.toast.success("Sample data loaded successfully!")

    def set_input(self, value: str):
        """Set current input value."""
        self.current_input = value

    async def send_message(self):
        """Send a message to the agent."""
        if not self.current_input.strip():
            return

        # Add user message
        user_msg = Message(role="user", content=self.current_input)
        self.messages.append(user_msg)
        query = self.current_input
        self.current_input = ""
        self.is_processing = True

        # Initialize agent if needed
        await self.initialize_agent()
        agent = get_agent()

        # Check if agent has data
        if not agent or not agent.graph:
            assistant_msg = Message(
                role="assistant",
                content="No documents loaded yet. Please load some data first using the 'Load Sample Data' button or upload your own files."
            )
            self.messages.append(assistant_msg)
            self.is_processing = False
            return

        try:
            # Query the agent
            start_time = datetime.now()

            # For now, use graph queries (non-AI)
            response = await self._handle_query(query)

            # Update metrics
            elapsed = (datetime.now() - start_time).total_seconds()
            self.total_queries += 1
            self.avg_response_time = (
                (self.avg_response_time * (self.total_queries - 1) + elapsed)
                / self.total_queries
            )

            # Add assistant response
            assistant_msg = Message(role="assistant", content=response)
            self.messages.append(assistant_msg)

        except Exception as e:
            error_msg = Message(
                role="assistant",
                content=f"Error: {str(e)}"
            )
            self.messages.append(error_msg)

        finally:
            self.is_processing = False

    async def _handle_query(self, query: str) -> str:
        """Handle a query using graph queries or AI."""
        agent = get_agent()
        queries = GraphQueries(agent.graph)

        # Simple keyword matching for demo
        query_lower = query.lower()

        if "statistics" in query_lower or "stats" in query_lower or "summary" in query_lower:
            stats = queries.get_graph_stats()
            return f"""📊 **Graph Statistics**

- Total Nodes: {stats['total_nodes']}
- Total Edges: {stats['total_edges']}
- Documents: {stats.get('documents', 0)}
- Components: {stats.get('components', 0)}
- Data Sources: {stats.get('data_sources', 0)}
- Data Entities: {stats.get('data_entities', 0)}
"""

        elif "documents" in query_lower or "packages" in query_lower:
            docs = queries.find_all_documents()
            doc_list = "\n".join([f"- {data['name']}" for _, data in docs[:10]])
            return f"**Found {len(docs)} documents:**\n\n{doc_list}"

        elif "lineage" in query_lower and "customer" in query_lower:
            lineage = queries.trace_data_lineage("Customer", direction="both")
            upstream = "\n".join([f"- {data['name']}" for _, data in lineage["upstream"][:5]])
            downstream = "\n".join([f"- {data['name']}" for _, data in lineage["downstream"][:5]])
            return f"""**Customer Table Lineage:**

**Upstream Sources:**
{upstream if upstream else "None"}

**Downstream Consumers:**
{downstream if downstream else "None"}
"""

        else:
            # If AI agent available, use it
            if agent.agent:
                response = await agent.query(query)
                return response
            else:
                return """I can help you with:
- **"Show statistics"** - View graph statistics
- **"List documents"** - See all loaded documents
- **"Trace lineage for Customer"** - View data lineage

For AI-powered queries, please set your API key in the settings."""

    def clear_chat(self):
        """Clear chat history."""
        self.messages = []
        return rx.toast.info("Chat cleared")

    def get_graph_stats_dict(self) -> dict:
        """Get graph statistics for dashboard."""
        agent = get_agent()
        if not agent or not agent.graph:
            return {
                "total_nodes": 0,
                "total_edges": 0,
                "documents": 0,
                "components": 0
            }

        queries = GraphQueries(agent.graph)
        return queries.get_graph_stats()


def chat_message(message: Message) -> rx.Component:
    """Render a chat message."""
    is_user = message.role == "user"

    return rx.box(
        rx.hstack(
            rx.avatar(
                fallback="U" if is_user else "AI",
                size="2",
                color_scheme="blue" if is_user else "purple",
            ),
            rx.box(
                rx.text(
                    message.content,
                    size="2",
                    white_space="pre-wrap",
                ),
                rx.text(
                    message.timestamp.strftime("%H:%M"),
                    size="1",
                    color="gray",
                ),
                background=THEME["surface"] if not is_user else THEME["primary"],
                padding="12px",
                border_radius="8px",
                max_width="70%",
            ),
            justify="end" if is_user else "start",
            width="100%",
            spacing="3",
        ),
        width="100%",
        padding_y="8px",
    )


def chat_panel() -> rx.Component:
    """Chat interface panel."""
    return rx.box(
        # Header
        rx.hstack(
            rx.heading("💬 Chat", size="6"),
            rx.spacer(),
            rx.button(
                "Clear",
                on_click=State.clear_chat,
                size="2",
                variant="soft",
            ),
            padding="16px",
            border_bottom=f"1px solid {THEME['surface']}",
        ),
        # Messages
        rx.box(
            rx.foreach(
                State.messages,
                chat_message,
            ),
            id="chat-messages",
            height="calc(100vh - 200px)",
            overflow_y="auto",
            padding="16px",
        ),
        # Input
        rx.hstack(
            rx.input(
                placeholder="Ask about your data...",
                value=State.current_input,
                on_change=State.set_input,
                size="3",
                flex="1",
            ),
            rx.button(
                "Send",
                on_click=State.send_message,
                loading=State.is_processing,
                size="3",
            ),
            padding="16px",
            spacing="3",
        ),
        height="100%",
        background=THEME["bg"],
        border_right=f"1px solid {THEME['surface']}",
    )


def stat_card(title: str, value: str | int, icon: str, color: str = "blue") -> rx.Component:
    """Render a statistic card."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.text(icon, size="6"),
                rx.spacer(),
                rx.badge(title, color_scheme=color, size="2"),
            ),
            rx.heading(str(value), size="8"),
            spacing="2",
        ),
        width="100%",
    )


def dashboard_panel() -> rx.Component:
    """Dashboard panel with metrics and visualizations."""
    return rx.box(
        # Header
        rx.hstack(
            rx.heading("📊 Dashboard", size="6"),
            rx.spacer(),
            rx.button(
                "Load Sample Data",
                on_click=State.load_sample_data,
                size="2",
                color_scheme="green",
            ),
            padding="16px",
            border_bottom=f"1px solid {THEME['surface']}",
        ),
        # Stats Grid
        rx.box(
            rx.grid(
                stat_card("Nodes", State.graph_nodes, "🔵", "blue"),
                stat_card("Edges", State.graph_edges, "🔗", "purple"),
                stat_card("Documents", State.documents_loaded, "📄", "green"),
                stat_card("Queries", State.total_queries, "💬", "orange"),
                columns="2",
                spacing="4",
            ),
            padding="16px",
        ),
        # Metrics
        rx.box(
            rx.vstack(
                rx.heading("Performance Metrics", size="4"),
                rx.hstack(
                    rx.text("Avg Response Time:", weight="bold"),
                    rx.text(f"{State.avg_response_time:.2f}s"),
                ),
                rx.hstack(
                    rx.text("Concurrent Parsers:", weight="bold"),
                    rx.text(State.max_concurrent),
                ),
                spacing="2",
            ),
            padding="16px",
        ),
        height="100%",
        overflow_y="auto",
        background=THEME["bg"],
    )


def index() -> rx.Component:
    """Main application layout."""
    return rx.box(
        # Top Bar
        rx.hstack(
            rx.heading("🔍 TraceAI", size="7", color=THEME["primary"]),
            rx.spacer(),
            rx.badge(
                State.model_provider,
                size="2",
                color_scheme="purple",
            ),
            rx.badge(
                "Async Mode",
                size="2",
                color_scheme="green",
            ),
            padding="16px",
            border_bottom=f"2px solid {THEME['primary']}",
            background=THEME["surface"],
        ),
        # Main Content
        rx.grid(
            chat_panel(),
            dashboard_panel(),
            columns="2",
            height="calc(100vh - 64px)",
        ),
        width="100%",
        height="100vh",
        background=THEME["bg"],
        color=THEME["text"],
    )


# Configure app
app = rx.App(
    theme=rx.theme(
        appearance="dark",
        accent_color="blue",
    ),
)
app.add_page(index, route="/", title="TraceAI - ETL Lineage Analysis")
