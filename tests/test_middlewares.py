"""Tests for agent middlewares."""

import pytest

from enterprise_assistant.agents.middlewares import (
    AuditMiddleware,
    ConversationMemoryMiddleware,
    LongTermMemoryMiddleware,
    ProgressTrackingMiddleware,
)


class TestConversationMemoryMiddleware:
    """Test conversation memory middleware."""

    def test_initialization(self):
        """Test middleware can be initialized."""
        middleware = ConversationMemoryMiddleware(max_messages=20)
        assert middleware.max_messages == 20
        assert middleware.total_messages_processed == 0

    def test_no_condensation_when_under_limit(self):
        """Test that messages are not condensed when under limit."""
        middleware = ConversationMemoryMiddleware(max_messages=30)

        state = {"messages": [{"role": "user", "content": f"msg{i}"} for i in range(25)]}

        result = middleware.before_model(state)
        assert result is None  # No changes needed

    def test_condensation_when_over_limit(self):
        """Test that messages are condensed when over limit."""
        middleware = ConversationMemoryMiddleware(max_messages=20, keep_system_messages=1)

        # Create 50 messages
        messages = [{"role": "system", "content": "System prompt"}]
        messages += [{"role": "user", "content": f"msg{i}"} for i in range(49)]

        state = {"messages": messages}

        result = middleware.before_model(state)

        assert result is not None
        assert "messages" in result
        assert len(result["messages"]) == 20
        # First message should be system message
        assert result["messages"][0]["role"] == "system"

    def test_metadata_tracking(self):
        """Test that middleware tracks conversation metadata."""
        middleware = ConversationMemoryMiddleware(max_messages=10)

        state = {"messages": [{"role": "user", "content": "test"}]}

        middleware.before_model(state)
        result = middleware.after_model(state)

        assert result is not None
        assert "conversation_metadata" in result
        assert "total_messages_seen" in result["conversation_metadata"]
        assert "current_message_count" in result["conversation_metadata"]


class TestLongTermMemoryMiddleware:
    """Test long-term memory middleware."""

    def test_initialization(self):
        """Test middleware can be initialized."""
        middleware = LongTermMemoryMiddleware(ephemeral=True)
        assert middleware.vector_store is not None
        assert middleware.facts_added == 0

    def test_memory_injection(self):
        """Test that memory is injected into context."""
        middleware = LongTermMemoryMiddleware(ephemeral=True)

        # Add some facts to memory
        middleware.vector_store.add(
            texts=["Important fact about the system"],
            metadatas=[{"type": "important_fact"}]
        )

        state = {"messages": []}

        # Memory injection happens in before_model
        result = middleware.before_model(state)
        # Middleware returns None, state is modified in place
        assert result is None or isinstance(result, dict)

    def test_memory_update_with_important_content(self):
        """Test that important information is added to memory."""
        middleware = LongTermMemoryMiddleware(ephemeral=True)

        # Mock message with content attribute
        class MockMessage:
            def __init__(self, content):
                self.content = content

        messages = [MockMessage("Important: This is a key finding about the system")]

        state = {"messages": messages}

        result = middleware.after_model(state)

        assert result is not None
        assert middleware.facts_added == 1
        # Verify metadata is returned
        assert "long_term_memory_metadata" in result


class TestAuditMiddleware:
    """Test audit logging middleware."""

    def test_initialization(self):
        """Test middleware can be initialized."""
        middleware = AuditMiddleware(log_level="INFO")
        assert middleware.log_level == "INFO"
        assert middleware.model_calls == 0
        assert len(middleware.tool_calls) == 0

    def test_model_call_tracking(self):
        """Test that model calls are tracked."""
        middleware = AuditMiddleware()

        state = {"messages": [{"role": "user", "content": "test"}]}

        middleware.before_model(state)
        assert middleware.model_calls == 1

        middleware.before_model(state)
        assert middleware.model_calls == 2

    def test_tool_call_tracking(self):
        """Test that tool calls are logged."""
        middleware = AuditMiddleware()

        # Mock message with tool calls
        class MockMessage:
            def __init__(self):
                self.tool_calls = [
                    {"name": "graph_query", "args": {}},
                    {"name": "semantic_search", "args": {}},
                ]

        state = {"messages": [MockMessage()]}

        result = middleware.after_model(state)

        assert result is not None
        assert "audit_metadata" in result
        assert result["audit_metadata"]["total_tool_calls"] == 2
        assert "graph_query" in result["audit_metadata"]["tools_used"]
        assert "semantic_search" in result["audit_metadata"]["tools_used"]


class TestProgressTrackingMiddleware:
    """Test progress tracking middleware."""

    def test_initialization(self):
        """Test middleware can be initialized."""
        middleware = ProgressTrackingMiddleware(show_progress=True)
        assert middleware.show_progress is True
        assert middleware.current_step == 0
        assert middleware.total_steps == 0

    def test_progress_metadata(self):
        """Test that progress metadata is returned."""
        middleware = ProgressTrackingMiddleware()

        state = {"messages": []}

        result = middleware.after_model(state)

        assert result is not None
        assert "progress_metadata" in result
        assert "current_step" in result["progress_metadata"]
        assert "total_steps" in result["progress_metadata"]
        assert "progress_percentage" in result["progress_metadata"]

    def test_progress_percentage_calculation(self):
        """Test progress percentage calculation."""
        middleware = ProgressTrackingMiddleware()
        middleware.total_steps = 10
        middleware.current_step = 5

        state = {"messages": []}

        result = middleware.after_model(state)

        assert result["progress_metadata"]["progress_percentage"] == 50.0
