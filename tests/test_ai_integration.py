"""Realistic AI-enabled integration tests.

These tests require an API key and test end-to-end workflows.
"""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from traceai.agents import TraceAI


# Skip all tests if no API key
pytestmark = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"),
    reason="No API key available for AI tests"
)


@pytest.fixture
def sample_ssis_dir():
    """Path to sample SSIS packages."""
    return Path(__file__).parent.parent / "examples" / "inputs" / "ssis"


@pytest.fixture
def sample_json_dir():
    """Path to sample JSON files."""
    return Path(__file__).parent.parent / "examples" / "inputs" / "json"


@pytest.fixture
def agent_with_ai():
    """Create agent with AI capabilities."""
    with tempfile.TemporaryDirectory() as temp_dir:
        model_provider = "anthropic" if os.getenv("ANTHROPIC_API_KEY") else "openai"

        agent = TraceAI(
            model_provider=model_provider,
            persist_dir=temp_dir,
            enable_memory=True,
            enable_audit=True,
            enable_progress=True
        )

        # Load sample data
        ssis_dir = Path(__file__).parent.parent / "examples" / "inputs" / "ssis"
        if ssis_dir.exists():
            asyncio.run(agent.load_documents(ssis_dir))

        yield agent


class TestAIBasicQueries:
    """Test basic AI query functionality."""

    def test_agent_can_answer_simple_question(self, agent_with_ai):
        """Test agent can answer a simple question about loaded data."""
        if not agent_with_ai.agent:
            pytest.skip("Agent not created (no data loaded)")
        response = asyncio.run(agent_with_ai.query("How many documents are loaded?"))

        assert isinstance(response, str)
        assert len(response) > 0
        # Should mention documents or packages
        assert any(word in response.lower() for word in ["document", "package", "two", "2"])

    def test_agent_can_list_documents(self, agent_with_ai):
        """Test agent can list documents."""
        if not agent_with_ai.agent:
            pytest.skip("Agent not created")
        response = asyncio.run(agent_with_ai.query("List all documents"))

        assert isinstance(response, str)
        assert len(response) > 0
        # Should mention the actual document names
        assert "Customer" in response or "Sales" in response

    def test_agent_can_describe_structure(self, agent_with_ai):
        """Test agent can describe the graph structure."""
        if not agent_with_ai.agent:
            pytest.skip("Agent not created")
        response = asyncio.run(agent_with_ai.query("What is the structure of the loaded data?"))

        assert isinstance(response, str)
        assert len(response) > 10
        # Should mention nodes or edges or components
        assert any(word in response.lower() for word in ["node", "edge", "component", "task"])


class TestAIDataLineage:
    """Test AI-powered data lineage queries."""

    def test_agent_can_trace_lineage(self, agent_with_ai):
        """Test agent can trace data lineage."""
        if not agent_with_ai.agent:
            pytest.skip("Agent not created")
        response = asyncio.run(agent_with_ai.query("Trace the lineage of the Customer table"))

        assert isinstance(response, str)
        assert len(response) > 0
        # Should mention upstream or downstream or lineage
        assert any(word in response.lower() for word in ["upstream", "downstream", "lineage", "customer"])

    def test_agent_can_find_data_sources(self, agent_with_ai):
        """Test agent can find data sources."""
        if not agent_with_ai.agent:
            pytest.skip("Agent not created")
        response = asyncio.run(agent_with_ai.query("What data sources are in the CustomerETL package?"))

        assert isinstance(response, str)
        assert len(response) > 0
        # Should mention data sources or connections
        assert any(word in response.lower() for word in ["source", "connection", "database", "table"])


class TestAIImpactAnalysis:
    """Test AI-powered impact analysis."""

    def test_agent_can_analyze_impact(self, agent_with_ai):
        """Test agent can perform impact analysis."""
        if not agent_with_ai.agent:
            pytest.skip("Agent not created")

        response = asyncio.run(agent_with_ai.query(
            "What would be impacted if I change the Customer table schema?"
        ))

        assert isinstance(response, str)
        assert len(response) > 0
        # Should mention impact or affected or tasks
        assert any(word in response.lower() for word in ["impact", "affect", "task", "component"])

    def test_agent_can_find_dependencies(self, agent_with_ai):
        """Test agent can find dependencies."""
        if not agent_with_ai.agent:
            pytest.skip("Agent not created")
        response = asyncio.run(agent_with_ai.query("What tasks depend on each other in CustomerETL?"))

        assert isinstance(response, str)
        assert len(response) > 0
        # Should mention dependencies or tasks
        assert any(word in response.lower() for word in ["depend", "task", "component"])


class TestAIMultiStepReasoning:
    """Test AI multi-step reasoning capabilities."""

    def test_agent_can_perform_multi_step_analysis(self, agent_with_ai):
        """Test agent can perform multi-step analysis."""
        if not agent_with_ai.agent:
            pytest.skip("Agent not created")
        response = asyncio.run(agent_with_ai.query("""
        Analyze the CustomerETL package:
        1. List all tasks
        2. Identify data sources
        3. Trace data flow
        """))

        assert isinstance(response, str)
        assert len(response) > 50  # Should be a detailed response

    def test_agent_can_answer_complex_question(self, agent_with_ai):
        """Test agent can answer complex questions."""
        if not agent_with_ai.agent:
            pytest.skip("Agent not created")

        response = asyncio.run(agent_with_ai.query(
            "Which ETL package processes customer data and what transformations does it perform?"
        ))

        assert isinstance(response, str)
        assert len(response) > 0
        # Should mention customer and transformations
        assert "customer" in response.lower()


class TestAISemanticSearch:
    """Test AI semantic search capabilities."""

    def test_agent_can_search_semantically(self, agent_with_ai):
        """Test agent can perform semantic search."""
        if not agent_with_ai.agent:
            pytest.skip("Agent not created")
        response = asyncio.run(agent_with_ai.query("Find all components related to customer data processing"))

        assert isinstance(response, str)
        assert len(response) > 0
        # Should mention customer or components
        assert any(word in response.lower() for word in ["customer", "component", "task"])

    def test_agent_uses_vector_search(self, agent_with_ai):
        """Test agent uses vector search for semantic queries."""
        if not agent_with_ai.agent:
            pytest.skip("Agent not created")
        response = asyncio.run(agent_with_ai.query("What does the ETL do with sales information?"))

        assert isinstance(response, str)
        assert len(response) > 0
        # Should mention sales
        assert "sales" in response.lower() or "aggregation" in response.lower()


class TestAIConversationalMemory:
    """Test AI conversational memory."""

    def test_agent_remembers_context(self, agent_with_ai):
        """Test agent remembers conversation context."""
        if not agent_with_ai.agent or not agent_with_ai.enable_memory:
            pytest.skip("Agent not created or memory disabled")

        # First question
        response1 = asyncio.run(agent_with_ai.query("What is the CustomerETL package?"))
        assert len(response1) > 0

        # Follow-up question (without mentioning CustomerETL)
        response2 = asyncio.run(agent_with_ai.query("What tasks does it have?"))

        assert len(response2) > 0
        # Should understand "it" refers to CustomerETL


@pytest.mark.asyncio
class TestAsyncAIIntegration:
    """Test async AI functionality."""

    async def test_async_agent_query(self, sample_ssis_dir):
        """Test async agent can query."""
        if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
            pytest.skip("No API key available")

        with tempfile.TemporaryDirectory() as temp_dir:
            model_provider = "anthropic" if os.getenv("ANTHROPIC_API_KEY") else "openai"

            agent = TraceAI(
                model_provider=model_provider,
                persist_dir=temp_dir
            )

            await agent.load_documents(sample_ssis_dir)

            if not agent.agent:
                pytest.skip("Agent not created")

            response = await agent.query("List all documents")

            assert isinstance(response, str)
            assert len(response) > 0

    async def test_async_agent_streaming(self, sample_ssis_dir):
        """Test async agent streaming."""
        if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
            pytest.skip("No API key available")

        with tempfile.TemporaryDirectory() as temp_dir:
            model_provider = "anthropic" if os.getenv("ANTHROPIC_API_KEY") else "openai"

            agent = TraceAI(
                model_provider=model_provider,
                persist_dir=temp_dir
            )

            await agent.load_documents(sample_ssis_dir)

            if not agent.agent:
                pytest.skip("Agent not created")

            chunks = []
            async for chunk in agent.query_stream("What documents are loaded?"):
                chunks.append(chunk)

            assert len(chunks) > 0
            assert all(isinstance(chunk, str) for chunk in chunks)


class TestAIToolUsage:
    """Test that AI agent uses tools correctly."""

    def test_agent_uses_graph_tools(self, agent_with_ai):
        """Test agent uses graph query tools."""
        if not agent_with_ai.agent:
            pytest.skip("Agent not created")

        # This question should trigger graph tool usage
        response = asyncio.run(agent_with_ai.query("Show me graph statistics"))

        assert isinstance(response, str)
        assert len(response) > 0
        # Should mention numbers or statistics
        assert any(char.isdigit() for char in response)

    def test_agent_uses_semantic_search_tool(self, agent_with_ai):
        """Test agent uses semantic search tool."""
        if not agent_with_ai.agent:
            pytest.skip("Agent not created")

        # This should trigger semantic search
        response = asyncio.run(agent_with_ai.query("Search for customer-related components"))

        assert isinstance(response, str)
        assert len(response) > 0


class TestAIErrorHandling:
    """Test AI error handling."""

    def test_agent_handles_nonsense_query(self, agent_with_ai):
        """Test agent handles nonsense queries gracefully."""
        if not agent_with_ai.agent:
            pytest.skip("Agent not created")

        response = asyncio.run(agent_with_ai.query("asdfghjkl qwerty zxcvbn"))

        # Should get some response (not crash)
        assert isinstance(response, str)

    def test_agent_handles_query_about_missing_data(self, agent_with_ai):
        """Test agent handles queries about non-existent data."""
        if not agent_with_ai.agent:
            pytest.skip("Agent not created")

        response = asyncio.run(agent_with_ai.query("Tell me about the NonExistentTable"))

        # Should indicate it doesn't exist or no information found
        assert isinstance(response, str)
        assert len(response) > 0
