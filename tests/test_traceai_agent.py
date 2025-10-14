"""Comprehensive API tests for the TraceAI async agent."""

import asyncio
import os
from pathlib import Path
import tempfile
import shutil

import pytest

from traceai.agents import TraceAI
from traceai.graph.queries import GraphQueries


pytestmark = pytest.mark.asyncio


@pytest.fixture
def temp_persist_dir():
    """Create a temporary directory for agent data."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_ssis_dir():
    """Path to sample SSIS packages."""
    return Path(__file__).parent.parent / "examples" / "inputs" / "ssis"


@pytest.fixture
def sample_json_dir():
    """Path to sample JSON files."""
    return Path(__file__).parent.parent / "examples" / "inputs" / "json"


@pytest.fixture
def sample_csv_dir():
    """Path to sample CSV files."""
    return Path(__file__).parent.parent / "examples" / "inputs" / "csv"
"""Comprehensive API tests for the TraceAI async agent."""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

from traceai.agents import TraceAI
from traceai.graph.queries import GraphQueries


pytestmark = pytest.mark.asyncio


@pytest.fixture
def temp_persist_dir():
    """Create a temporary directory for agent data."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_ssis_dir():
    """Path to sample SSIS packages."""
    return Path(__file__).parent.parent / "examples" / "inputs" / "ssis"


@pytest.fixture
def sample_json_dir():
    """Path to sample JSON files."""
    return Path(__file__).parent.parent / "examples" / "inputs" / "json"


@pytest.fixture
def sample_csv_dir():
    """Path to sample CSV files."""
    return Path(__file__).parent.parent / "examples" / "inputs" / "csv"


@pytest.fixture
def sample_excel_dir():
    """Path to sample Excel files."""
    return Path(__file__).parent.parent / "examples" / "inputs" / "excel"


class TestTraceAIAgentAPI:
    """Test TraceAI API functionality."""

    async def test_agent_initialization_no_api_key(self, temp_persist_dir):
        old_anthropic = os.environ.pop("ANTHROPIC_API_KEY", None)
        old_openai = os.environ.pop("OPENAI_API_KEY", None)

        try:
            agent = TraceAI(model_provider="anthropic", persist_dir=temp_persist_dir)

            assert agent.llm is None
            assert agent.model_provider == "anthropic"
            assert agent.graph is None
            assert agent.agent is None
        finally:
            if old_anthropic:
                os.environ["ANTHROPIC_API_KEY"] = old_anthropic
            if old_openai:
                os.environ["OPENAI_API_KEY"] = old_openai

    async def test_load_single_ssis_package(self, temp_persist_dir, sample_ssis_dir):
        agent = TraceAI(persist_dir=temp_persist_dir)
        await agent.load_documents(sample_ssis_dir)

        assert agent.graph is not None
        assert agent.graph.number_of_nodes() > 0
        assert agent.graph.number_of_edges() > 0
        assert len(agent.parsed_documents) >= 1

    async def test_load_multiple_file_types(self, temp_persist_dir, sample_ssis_dir, sample_json_dir):
        agent = TraceAI(persist_dir=temp_persist_dir)

        await agent.load_documents(sample_ssis_dir)
        ssis_count = len(agent.parsed_documents)

        await agent.load_documents(sample_json_dir, pattern="*.json")
        total_count = len(agent.parsed_documents)

        assert total_count > ssis_count

    async def test_graph_statistics(self, temp_persist_dir, sample_ssis_dir):
        agent = TraceAI(persist_dir=temp_persist_dir)
        await agent.load_documents(sample_ssis_dir)

        stats = agent.get_graph_stats()

        assert stats["total_nodes"] > 0
        assert stats["total_edges"] > 0

    async def test_graph_queries_lineage(self, temp_persist_dir, sample_ssis_dir):
        agent = TraceAI(persist_dir=temp_persist_dir)
        await agent.load_documents(sample_ssis_dir)

        queries = GraphQueries(agent.graph)
        lineage = queries.trace_data_lineage("Customer", direction="both")

        assert "upstream" in lineage and "downstream" in lineage

    async def test_vector_store_indexing(self, temp_persist_dir, sample_ssis_dir):
        agent = TraceAI(persist_dir=temp_persist_dir)
        await agent.load_documents(sample_ssis_dir)

        results = agent.vector_store.similarity_search("customer", k=3)

        assert isinstance(results, list)
        assert results

    async def test_load_with_patterns(self, temp_persist_dir, sample_json_dir):
        agent = TraceAI(persist_dir=temp_persist_dir)
        await agent.load_documents(sample_json_dir, pattern="*.json")

        assert agent.parsed_documents
        assert all(doc.metadata.file_path.suffix == ".json" for doc in agent.parsed_documents)

    async def test_load_multiple_patterns(self, temp_persist_dir):
        agent = TraceAI(persist_dir=temp_persist_dir)
        inputs_dir = Path(__file__).parent.parent / "examples" / "inputs"

        await agent.load_documents(inputs_dir / "json", pattern=["*.json"])
        json_count = len(agent.parsed_documents)

        await agent.load_documents(inputs_dir / "csv", pattern=["*.csv"])
        total_count = len(agent.parsed_documents)

        assert total_count > json_count

    async def test_empty_directory_handling(self, temp_persist_dir):
        agent = TraceAI(persist_dir=temp_persist_dir)

        empty_dir = temp_persist_dir / "empty"
        empty_dir.mkdir()

        await agent.load_documents(empty_dir)

        assert agent.graph is None or agent.graph.number_of_nodes() == 0

    async def test_persistence_directory_creation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            persist_path = Path(temp_dir) / "new_dir" / "agent_data"
            TraceAI(persist_dir=persist_path)

            assert persist_path.exists()
            assert persist_path.is_dir()

    async def test_model_provider_validation(self, temp_persist_dir):
        with pytest.raises(ValueError, match="Unknown model provider"):
            TraceAI(model_provider="invalid", persist_dir=temp_persist_dir)

    async def test_requires_documents_for_queries(self, temp_persist_dir):
        agent = TraceAI(persist_dir=temp_persist_dir)

        with pytest.raises(ValueError, match="Load documents first"):
            await agent.query("Test query")

    async def test_async_query_without_llm(self, temp_persist_dir, sample_ssis_dir):
        old_anthropic = os.environ.pop("ANTHROPIC_API_KEY", None)
        old_openai = os.environ.pop("OPENAI_API_KEY", None)

        try:
            agent = TraceAI(persist_dir=temp_persist_dir)
            await agent.load_documents(sample_ssis_dir)

            response = await agent.query("List documents")
            assert isinstance(response, str)
            assert response
        finally:
            if old_anthropic:
                os.environ["ANTHROPIC_API_KEY"] = old_anthropic
            if old_openai:
                os.environ["OPENAI_API_KEY"] = old_openai

    async def test_multiple_loads_accumulate_documents(self, temp_persist_dir, sample_ssis_dir, sample_json_dir):
        agent = TraceAI(persist_dir=temp_persist_dir)

        await agent.load_documents(sample_ssis_dir)
        first_count = len(agent.parsed_documents)

        await agent.load_documents(sample_json_dir, pattern="*.json")
        second_count = len(agent.parsed_documents)

        assert second_count > first_count

    async def test_graph_stats_no_documents(self, temp_persist_dir):
        agent = TraceAI(persist_dir=temp_persist_dir)
        stats = agent.get_graph_stats()

        assert stats["total_nodes"] == 0
        assert stats["total_edges"] == 0

    async def test_vector_search_before_loading(self, temp_persist_dir):
        agent = TraceAI(persist_dir=temp_persist_dir)
        results = agent.vector_store.similarity_search("anything", k=1)

        assert results == []

    async def test_vector_search_after_loading(self, temp_persist_dir, sample_ssis_dir):
        agent = TraceAI(persist_dir=temp_persist_dir)
        await agent.load_documents(sample_ssis_dir)

        results = agent.vector_store.similarity_search("Customer", k=1)
        assert results

    async def test_load_documents_handles_missing_directory(self, temp_persist_dir):
        agent = TraceAI(persist_dir=temp_persist_dir)
        missing_dir = temp_persist_dir / "missing"

        await agent.load_documents(missing_dir)

        assert agent.graph is None

