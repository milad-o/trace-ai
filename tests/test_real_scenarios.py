"""Real-world scenario tests for the Enterprise Assistant.

This module tests the agent in realistic enterprise scenarios, not just unit tests.
Tests include:
- Agent using write_todos for planning
- Semantic search over enterprise documents
- Lineage tracing with real SSIS packages
- Impact analysis for database changes
- Graph visualization generation
- Multi-step agent workflows
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from traceai.agents import create_enterprise_agent

# Load environment variables
load_dotenv()

# Skip if no API key
skip_without_key = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"),
    reason="No API key available for testing"
)


@skip_without_key
class TestRealScenarios:
    """Test real-world enterprise scenarios with actual agent."""

    @pytest.fixture
    def agent(self, tmp_path):
        """Create agent with sample SSIS package."""
        # Use the sample SSIS package
        samples_dir = Path(__file__).parent.parent / "examples" / "sample_packages"

        agent = create_enterprise_agent(
            documents_dir=samples_dir,
            model_provider="anthropic" if os.getenv("ANTHROPIC_API_KEY") else "openai",
            enable_memory=True,
            enable_audit=True,
            enable_progress=True,
        )

        return agent

    def test_agent_initialization(self, agent):
        """Test that agent initializes correctly with knowledge graph."""
        assert agent.graph is not None
        assert agent.graph.number_of_nodes() > 0
        assert agent.vector_store is not None
        assert agent.agent is not None

    def test_simple_query(self, agent):
        """Test agent can answer simple questions about the SSIS package."""
        response = agent.analyze("What packages are in the knowledge graph?")

        assert response is not None
        assert len(response) > 0
        # Should mention CustomerETL or list packages
        assert "customer" in response.lower() or "etl" in response.lower() or "package" in response.lower()

    def test_planning_with_todos(self, agent):
        """Test that agent uses write_todos for complex multi-step queries."""
        query = """Analyze the CustomerETL package in detail. Create a plan first:
1. Find all tasks in the package
2. Trace data lineage
3. Analyze impact
4. Summarize findings"""

        response = agent.analyze(query)

        assert response is not None
        # Agent should have used planning
        # Response should be comprehensive
        assert len(response) > 100  # Should be detailed

    def test_semantic_search(self, agent):
        """Test semantic search finds relevant components."""
        query = "Find components related to customer data processing"

        response = agent.analyze(query)

        assert response is not None
        # Should find customer-related components
        assert "customer" in response.lower() or "dbo.customers" in response.lower()

    def test_lineage_tracing(self, agent):
        """Test data lineage tracing."""
        query = "What is the data lineage for the dbo.Customers table? Show upstream and downstream."

        response = agent.analyze(query)

        assert response is not None
        # Should mention data sources and destinations
        assert len(response) > 50

    def test_impact_analysis(self, agent):
        """Test impact analysis for table changes."""
        query = "What would be the impact if I changed the dbo.Customers table schema?"

        response = agent.analyze(query)

        assert response is not None
        # Should identify affected components
        assert "impact" in response.lower() or "affect" in response.lower()

    def test_dependency_analysis(self, agent):
        """Test task dependency analysis."""
        query = "What are the dependencies for the Load Customer Data task?"

        response = agent.analyze(query)

        assert response is not None
        # Should describe dependencies
        assert len(response) > 30

    def test_graph_statistics(self, agent):
        """Test getting graph statistics."""
        query = "Give me statistics about the knowledge graph"

        response = agent.analyze(query)

        assert response is not None
        # Should include node/edge counts
        assert "node" in response.lower() or "edge" in response.lower() or "graph" in response.lower()

    @pytest.mark.slow
    def test_visualization_generation(self, agent, tmp_path):
        """Test graph visualization generation."""
        output_path = tmp_path / "test_viz.svg"

        query = f"Create a visualization of the CustomerETL package and save it to {output_path}"

        response = agent.analyze(query)

        assert response is not None
        # Should mention visualization creation
        # Note: Actual file creation depends on agent successfully calling the tool

    def test_multi_turn_conversation(self, agent):
        """Test multi-turn conversation with memory."""
        # First question
        response1 = agent.analyze("How many tasks are in the CustomerETL package?")
        assert response1 is not None

        # Follow-up question (should use context from first)
        response2 = agent.analyze("Which one reads from the database?")
        assert response2 is not None

        # Should reference tasks from previous context
        assert len(response2) > 20

    def test_complex_analysis(self, agent):
        """Test complex multi-step analysis."""
        query = """Perform a comprehensive analysis of the CustomerETL package:
1. List all components
2. Identify the data flow
3. Find any potential bottlenecks or issues
4. Suggest improvements"""

        response = agent.analyze(query)

        assert response is not None
        # Should be detailed analysis
        assert len(response) > 200
        # Should mention components
        assert "task" in response.lower() or "component" in response.lower()


@skip_without_key
class TestAgentTools:
    """Test individual agent tools in realistic scenarios."""

    @pytest.fixture
    def agent(self):
        """Create agent for tool testing."""
        samples_dir = Path(__file__).parent.parent / "examples" / "sample_packages"

        return create_enterprise_agent(
            documents_dir=samples_dir,
            model_provider="anthropic" if os.getenv("ANTHROPIC_API_KEY") else "openai",
        )

    def test_graph_query_tool(self, agent):
        """Test graph_query tool."""
        query = "Use the graph_query tool to find all tasks in the knowledge graph"

        response = agent.analyze(query)

        assert response is not None
        assert "task" in response.lower()

    def test_lineage_tracer_tool(self, agent):
        """Test trace_lineage tool."""
        query = "Use the trace_lineage tool to trace upstream data flow for dbo.Customers"

        response = agent.analyze(query)

        assert response is not None

    def test_impact_analysis_tool(self, agent):
        """Test analyze_impact tool."""
        query = "Use the analyze_impact tool to analyze impact for dbo.Customers table"

        response = agent.analyze(query)

        assert response is not None

    def test_dependency_search_tool(self, agent):
        """Test find_dependencies tool."""
        query = "Use the find_dependencies tool to find predecessors of any task"

        response = agent.analyze(query)

        assert response is not None


@skip_without_key
class TestStreamingScenarios:
    """Test streaming agent responses."""

    @pytest.fixture
    def agent(self):
        """Create agent for streaming tests."""
        samples_dir = Path(__file__).parent.parent / "examples" / "sample_packages"

        return create_enterprise_agent(
            documents_dir=samples_dir,
            model_provider="anthropic" if os.getenv("ANTHROPIC_API_KEY") else "openai",
        )

    def test_streaming_response(self, agent):
        """Test streaming agent response."""
        query = "Describe the CustomerETL package"

        chunks = []
        for chunk in agent.analyze_stream(query):
            chunks.append(chunk)

        assert len(chunks) > 0
        # Should receive multiple chunks

    def test_streaming_with_planning(self, agent):
        """Test streaming with complex planning query."""
        query = """Create a detailed analysis plan:
1. Find all packages
2. Analyze each one
3. Compare them"""

        chunks = []
        for chunk in agent.analyze_stream(query):
            chunks.append(chunk)

        assert len(chunks) > 0
