"""Custom middleware for enterprise agent capabilities with persistent storage."""

from pathlib import Path
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware

from traceai.logger import logger
from traceai.memory.conversation_store import (
    ConversationStore,
    SQLiteConversationStore,
)
from traceai.memory.vector_store import (
    ChromaVectorStore,
    PineconeVectorStore,
    VectorMemoryStore,
)


class ConversationMemoryMiddleware(AgentMiddleware):
    """
    Middleware to manage conversation history using persistent SQLite storage.

    Features:
    - SQLite persistent storage for full conversation history
    - Context window management (condensing old messages)
    - Full-text search over conversations
    - Configurable ephemeral (in-memory) or persistent storage
    """

    def __init__(
        self,
        max_messages: int = 30,
        keep_system_messages: int = 1,
        storage: ConversationStore | None = None,
        db_path: Path | str = "./data/conversation.db",
        ephemeral: bool = False,
    ):
        """
        Initialize conversation memory middleware.

        Args:
            max_messages: Maximum number of messages to keep in context (default: 30)
            keep_system_messages: Number of system messages to preserve from start (default: 1)
            storage: Optional custom ConversationStore (defaults to SQLiteConversationStore)
            db_path: Path to SQLite database (if using default storage)
            ephemeral: If True, use in-memory storage (non-persistent)
        """
        self.max_messages = max_messages
        self.keep_system_messages = keep_system_messages
        self.total_messages_processed = 0
        self._seen_ids = set()  # Track which messages we've already persisted

        # Initialize storage
        self.storage = storage or SQLiteConversationStore(db_path=db_path, ephemeral=ephemeral)

    def before_model(self, state: dict) -> dict | None:
        """
        Manage conversation length before each model call.
        Persists new messages to storage.

        Args:
            state: Current agent state

        Returns:
            Updated state with condensed messages, or None if no changes needed
        """
        messages = state.get("messages", [])
        self.total_messages_processed = len(messages)

        # Persist only NEW messages to storage
        for msg in messages:
            msg_id = id(msg)  # Use Python object ID to track uniqueness
            if msg_id not in self._seen_ids:
                if hasattr(msg, "type") and hasattr(msg, "content"):
                    role = msg.type  # 'human', 'ai', 'system', 'tool'
                    content = msg.content if msg.content else ""
                    metadata = {"message_type": msg.type}
                    self.storage.add_message(role=role, content=content, metadata=metadata)
                    self._seen_ids.add(msg_id)

        # If within limits, no action needed
        if len(messages) <= self.max_messages:
            return None

        logger.info(
            f"Conversation memory: Condensing {len(messages)} messages to {self.max_messages}"
        )

        # Preserve system messages from the start
        system_messages = messages[: self.keep_system_messages]

        # Keep recent messages
        recent_messages = messages[-(self.max_messages - self.keep_system_messages) :]

        # Combine
        condensed_messages = system_messages + recent_messages

        logger.debug(
            f"Memory condensed: kept {len(system_messages)} system + {len(recent_messages)} recent messages"
        )

        return {"messages": condensed_messages}

    def after_model(self, state: dict) -> dict | None:
        """
        Track metadata after model execution.

        Args:
            state: Current agent state

        Returns:
            Optional state updates (metadata)
        """
        stats = self.storage.get_stats()

        # Add conversation metadata
        return {
            "conversation_metadata": {
                "total_messages_seen": self.total_messages_processed,
                "current_message_count": len(state.get("messages", [])),
                "memory_active": self.total_messages_processed > self.max_messages,
                "storage_stats": stats,
            }
        }

    def search_history(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search conversation history using full-text search."""
        return self.storage.search(query, limit=limit)

    def get_recent(self, limit: int = 30) -> list[dict[str, Any]]:
        """Get recent conversation messages from storage."""
        return self.storage.get_recent_messages(limit=limit)


class LongTermMemoryMiddleware(AgentMiddleware):
    """
    Middleware to implement long-term memory using vector storage.

    Features:
    - ChromaDB or Pinecone for semantic memory
    - Automatic fact extraction from important messages
    - Semantic search over historical insights
    - Configurable ephemeral or persistent storage
    """

    def __init__(
        self,
        vector_store: VectorMemoryStore | None = None,
        backend: str = "chroma",
        persist_dir: Path | str = "./data/long_term_memory",
        ephemeral: bool = False,
        pinecone_api_key: str | None = None,
    ):
        """
        Initialize long-term memory middleware.

        Args:
            vector_store: Optional custom VectorMemoryStore
            backend: 'chroma' or 'pinecone' (default: 'chroma')
            persist_dir: Directory for ChromaDB persistence
            ephemeral: If True, use in-memory storage (non-persistent)
            pinecone_api_key: Pinecone API key (required if backend='pinecone')
        """
        self.facts_added = 0

        # Initialize vector store
        if vector_store:
            self.vector_store = vector_store
        elif backend == "chroma":
            self.vector_store = ChromaVectorStore(
                persist_directory=persist_dir,
                collection_name="long_term_memory",
                ephemeral=ephemeral,
            )
        elif backend == "pinecone":
            if not pinecone_api_key:
                raise ValueError("Pinecone API key required when backend='pinecone'")
            self.vector_store = PineconeVectorStore(
                api_key=pinecone_api_key, index_name="long-term-memory"
            )
        else:
            raise ValueError(f"Unknown backend: {backend}")

    def before_model(self, state: dict) -> dict | None:
        """
        Inject relevant long-term memories into context before model call.

        Args:
            state: Current agent state

        Returns:
            None (or state update with relevant memories)
        """
        messages = state.get("messages", [])

        # Get latest user message to find relevant memories
        if messages:
            latest_user_msg = None
            for msg in reversed(messages):
                if hasattr(msg, "type") and msg.type == "human":
                    latest_user_msg = msg
                    break

            if latest_user_msg and hasattr(latest_user_msg, "content"):
                # Search for relevant memories
                relevant_memories = self.vector_store.search(
                    query=latest_user_msg.content, n_results=3
                )

                if relevant_memories:
                    logger.debug(
                        f"Found {len(relevant_memories)} relevant long-term memories"
                    )

        return None

    def after_model(self, state: dict) -> dict | None:
        """
        Update long-term memory after model execution.

        Args:
            state: Current agent state

        Returns:
            Updated state with memory metadata
        """
        messages = state.get("messages", [])

        # Check if the latest message contains important information
        if messages:
            latest = messages[-1]

            # Look for key phrases that indicate important information
            if hasattr(latest, "content") and latest.content:
                content = latest.content.lower()

                # Simple heuristics for important information
                important_indicators = [
                    "important:",
                    "note:",
                    "remember:",
                    "key finding:",
                    "decision:",
                    "conclusion:",
                ]

                if any(indicator in content for indicator in important_indicators):
                    # Add to vector memory
                    self.vector_store.add(
                        texts=[latest.content],
                        metadatas=[
                            {
                                "type": "important_fact",
                                "source": "assistant",
                                "entry_number": self.facts_added + 1,
                            }
                        ],
                    )

                    self.facts_added += 1
                    logger.info(f"Added fact #{self.facts_added} to long-term vector memory")

        return {
            "long_term_memory_metadata": {
                "facts_added": self.facts_added,
                "storage_stats": self.vector_store.get_stats(),
            }
        }

    def search_memory(self, query: str, n_results: int = 5) -> list[dict[str, Any]]:
        """Search long-term memory for relevant facts."""
        return self.vector_store.search(query, n_results=n_results)


class AuditMiddleware(AgentMiddleware):
    """
    Middleware to log all agent actions for auditing and debugging.

    Logs:
    - Tool calls
    - Model requests
    - Decisions made
    """

    def __init__(self, log_level: str = "INFO"):
        """
        Initialize audit middleware.

        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.log_level = log_level
        self.tool_calls = []
        self.model_calls = 0

    def before_model(self, state: dict) -> dict | None:
        """
        Log before model call.

        Args:
            state: Current agent state

        Returns:
            None
        """
        self.model_calls += 1
        messages = state.get("messages", [])

        if messages:
            latest = messages[-1]
            if hasattr(latest, "content"):
                logger.debug(f"[AUDIT] Model call #{self.model_calls}")

        return None

    def after_model(self, state: dict) -> dict | None:
        """
        Log tool calls after model execution.

        Args:
            state: Current agent state

        Returns:
            Audit metadata
        """
        messages = state.get("messages", [])

        if messages:
            latest = messages[-1]

            # Check for tool calls
            if hasattr(latest, "tool_calls") and latest.tool_calls:
                for tc in latest.tool_calls:
                    tool_name = tc.get("name", "unknown")
                    tool_args = tc.get("args", {})
                    self.tool_calls.append(tool_name)
                    
                    # Log tool name and arguments
                    if tool_args:
                        # Format arguments for logging
                        args_str = ", ".join([f"{k}={v}" for k, v in tool_args.items()])
                        logger.info(f"[AUDIT] Tool call: {tool_name}({args_str})")
                        
                        # Also log in a more readable format
                        logger.info(f"🔧 TOOL: {tool_name}")
                        for arg_key, arg_value in tool_args.items():
                            logger.info(f"   📝 {arg_key}: {arg_value}")
                    else:
                        logger.info(f"[AUDIT] Tool call: {tool_name}")
                        logger.info(f"🔧 TOOL: {tool_name}")

        return {
            "audit_metadata": {
                "total_model_calls": self.model_calls,
                "total_tool_calls": len(self.tool_calls),
                "tools_used": list(set(self.tool_calls)),
            }
        }


class ProgressTrackingMiddleware(AgentMiddleware):
    """
    Middleware to track and display progress during multi-step operations.

    Works with write_todos to show what step the agent is currently on.
    """

    def __init__(self, show_progress: bool = True):
        """
        Initialize progress tracking middleware.

        Args:
            show_progress: Whether to log progress updates (default: True)
        """
        self.show_progress = show_progress
        self.current_step = 0
        self.total_steps = 0
        self.todos = []

    def before_model(self, state: dict) -> dict | None:
        """
        Track progress before model call.

        Args:
            state: Current agent state

        Returns:
            None
        """
        # Check if todos were created
        files = state.get("files", {})

        if "todos.json" in files:
            import json

            try:
                todos_data = json.loads(files["todos.json"])
                if isinstance(todos_data, list):
                    self.todos = todos_data
                    self.total_steps = len(todos_data)

                    if self.show_progress:
                        logger.info(f"[PROGRESS] Plan created with {self.total_steps} steps")

            except json.JSONDecodeError:
                pass

        return None

    def after_model(self, state: dict) -> dict | None:
        """
        Update progress after model execution.

        Args:
            state: Current agent state

        Returns:
            Progress metadata
        """
        messages = state.get("messages", [])

        if messages and self.todos:
            latest = messages[-1]

            # Simple heuristic: if tool calls happened, increment step
            if hasattr(latest, "tool_calls") and latest.tool_calls:
                if self.current_step < self.total_steps:
                    self.current_step += 1

                    if self.show_progress:
                        progress_pct = (self.current_step / self.total_steps) * 100
                        logger.info(
                            f"[PROGRESS] Step {self.current_step}/{self.total_steps} ({progress_pct:.0f}%)"
                        )

        return {
            "progress_metadata": {
                "current_step": self.current_step,
                "total_steps": self.total_steps,
                "progress_percentage": (self.current_step / self.total_steps * 100) if self.total_steps > 0 else 0,
            }
        }
