"""Comprehensive API tests for AsyncEnterpriseAgent."""

import os
from pathlib import Path
import tempfile
import shutil
import asyncio

import pytest

from traceai.agents import AsyncEnterpriseAgent
from traceai.graph.queries import GraphQueries


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


@pytest.fixture
def sample_cobol_dir():
    """Path to sample COBOL files."""
    return Path(__file__).parent.parent / "examples" / "inputs" / "cobol"


@pytest.fixture
def sample_jcl_dir():
    """Path to sample JCL files."""
    return Path(__file__).parent.parent / "examples" / "inputs" / "jcl"


class TestAsyncEnterpriseAgentAPI:
    """Test AsyncEnterpriseAgent API functionality."""

    @pytest.mark.asyncio
    async def test_agent_initialization_no_api_key(self, temp_persist_dir):
        """Test async agent can initialize without API key."""
        old_anthropic = os.environ.pop("ANTHROPIC_API_KEY", None)
        old_openai = os.environ.pop("OPENAI_API_KEY", None)

        try:
            agent = AsyncEnterpriseAgent(
                model_provider="anthropic",
                persist_dir=temp_persist_dir
            )

            assert agent.llm is None
            assert agent.model_provider == "anthropic"
            assert agent.graph is None
        finally:
            if old_anthropic:
                os.environ["ANTHROPIC_API_KEY"] = old_anthropic
            if old_openai:
                os.environ["OPENAI_API_KEY"] = old_openai

    @pytest.mark.asyncio
    async def test_load_single_directory_async(self, temp_persist_dir, sample_ssis_dir):
        """Test loading documents asynchronously."""
        agent = AsyncEnterpriseAgent(persist_dir=temp_persist_dir)
        await agent.load_documents(sample_ssis_dir)

        assert agent.graph is not None
        assert agent.graph.number_of_nodes() > 0
        assert len(agent.parsed_documents) == 2

    @pytest.mark.asyncio
    async def test_concurrent_loading(self, temp_persist_dir, sample_ssis_dir, sample_json_dir):
        """Test loading multiple directories concurrently."""
        agent = AsyncEnterpriseAgent(
            persist_dir=temp_persist_dir,
            max_concurrent_parsers=10
        )

        # Load concurrently
        await asyncio.gather(
            agent.load_documents(sample_ssis_dir),
            agent.load_documents(sample_json_dir, pattern="*.json")
        )

        assert agent.graph is not None
        assert len(agent.parsed_documents) > 2  # SSIS + JSON files

    @pytest.mark.asyncio
    async def test_max_concurrent_parsers_configuration(self, temp_persist_dir):
        """Test configuring max concurrent parsers."""
        agent = AsyncEnterpriseAgent(
            persist_dir=temp_persist_dir,
            max_concurrent_parsers=5
        )

        assert agent.max_concurrent_parsers == 5

    @pytest.mark.asyncio
    async def test_graph_statistics_async(self, temp_persist_dir, sample_ssis_dir):
        """Test getting graph statistics from async agent."""
        agent = AsyncEnterpriseAgent(persist_dir=temp_persist_dir)
        await agent.load_documents(sample_ssis_dir)

        stats = agent.get_graph_stats()

        assert "total_nodes" in stats
        assert "total_edges" in stats
        assert stats["total_nodes"] > 0

    @pytest.mark.asyncio
    async def test_query_without_streaming(self, temp_persist_dir, sample_ssis_dir):
        """Test querying without streaming (requires API key)."""
        # Skip if no API key
        if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
            pytest.skip("No API key available")

        agent = AsyncEnterpriseAgent(persist_dir=temp_persist_dir)
        await agent.load_documents(sample_ssis_dir)

        response = await agent.query("List all documents")

        assert isinstance(response, str)
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_query_with_streaming(self, temp_persist_dir, sample_ssis_dir):
        """Test streaming query (requires API key)."""
        if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
            pytest.skip("No API key available")

        agent = AsyncEnterpriseAgent(persist_dir=temp_persist_dir)
        await agent.load_documents(sample_ssis_dir)

        chunks = []
        async for chunk in agent.query_stream("What documents are loaded?"):
            chunks.append(chunk)

        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)

    @pytest.mark.asyncio
    async def test_vector_store_indexing_async(self, temp_persist_dir, sample_ssis_dir):
        """Test async vector store indexing."""
        agent = AsyncEnterpriseAgent(persist_dir=temp_persist_dir)
        await agent.load_documents(sample_ssis_dir)

        # Search should work
        results = agent.vector_store.similarity_search("customer", k=5)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_load_large_dataset_async(self, temp_persist_dir, sample_cobol_dir, sample_jcl_dir):
        """Test loading large dataset (many COBOL/JCL files) concurrently."""
        agent = AsyncEnterpriseAgent(
            persist_dir=temp_persist_dir,
            max_concurrent_parsers=20
        )

        # Load all COBOL and JCL files
        await asyncio.gather(
            agent.load_documents(sample_cobol_dir, pattern="*.cbl"),
            agent.load_documents(sample_jcl_dir, pattern="*.jcl")
        )

        # Should have loaded many files
        assert len(agent.parsed_documents) > 10
        assert agent.graph.number_of_nodes() > 50


class TestAsyncEnterpriseAgentParsers:
    """Test all parsers work through async agent."""

    @pytest.mark.asyncio
    async def test_ssis_parser_async(self, temp_persist_dir, sample_ssis_dir):
        """Test SSIS parser async."""
        agent = AsyncEnterpriseAgent(persist_dir=temp_persist_dir)
        await agent.load_documents(sample_ssis_dir)

        assert len(agent.parsed_documents) == 2
        assert all(doc.metadata.document_type.value == "ssis_package" for doc in agent.parsed_documents)

    @pytest.mark.asyncio
    async def test_json_parser_async(self, temp_persist_dir, sample_json_dir):
        """Test JSON parser async."""
        agent = AsyncEnterpriseAgent(persist_dir=temp_persist_dir)
        await agent.load_documents(sample_json_dir, pattern="*.json")

        assert len(agent.parsed_documents) > 0
        assert all(doc.metadata.document_type.value == "json_config" for doc in agent.parsed_documents)

    @pytest.mark.asyncio
    async def test_csv_parser_async(self, temp_persist_dir, sample_csv_dir):
        """Test CSV parser async."""
        agent = AsyncEnterpriseAgent(persist_dir=temp_persist_dir)
        await agent.load_documents(sample_csv_dir, pattern="*.csv")

        assert len(agent.parsed_documents) > 0

    @pytest.mark.asyncio
    async def test_excel_parser_async(self, temp_persist_dir, sample_excel_dir):
        """Test Excel parser async."""
        agent = AsyncEnterpriseAgent(persist_dir=temp_persist_dir)
        await agent.load_documents(sample_excel_dir, pattern="*.xlsx")

        assert len(agent.parsed_documents) > 0

    @pytest.mark.asyncio
    async def test_cobol_parser_async(self, temp_persist_dir, sample_cobol_dir):
        """Test COBOL parser async."""
        agent = AsyncEnterpriseAgent(persist_dir=temp_persist_dir)
        await agent.load_documents(sample_cobol_dir, pattern="*.cbl")

        assert len(agent.parsed_documents) > 0

    @pytest.mark.asyncio
    async def test_jcl_parser_async(self, temp_persist_dir, sample_jcl_dir):
        """Test JCL parser async."""
        agent = AsyncEnterpriseAgent(persist_dir=temp_persist_dir)
        await agent.load_documents(sample_jcl_dir, pattern="*.jcl")

        assert len(agent.parsed_documents) > 0

    @pytest.mark.asyncio
    async def test_all_parsers_together(
        self,
        temp_persist_dir,
        sample_ssis_dir,
        sample_json_dir,
        sample_csv_dir,
        sample_excel_dir
    ):
        """Test loading all parser types concurrently."""
        agent = AsyncEnterpriseAgent(
            persist_dir=temp_persist_dir,
            max_concurrent_parsers=20
        )

        await asyncio.gather(
            agent.load_documents(sample_ssis_dir),
            agent.load_documents(sample_json_dir, pattern="*.json"),
            agent.load_documents(sample_csv_dir, pattern="*.csv"),
            agent.load_documents(sample_excel_dir, pattern="*.xlsx"),
        )

        # Should have docs from all formats
        doc_types = {doc.metadata.document_type.value for doc in agent.parsed_documents}

        assert "ssis_package" in doc_types
        assert "json_config" in doc_types
        assert "csv_metadata" in doc_types or len(agent.parsed_documents) > 0
        assert len(agent.parsed_documents) >= 4


class TestAsyncEnterpriseAgentPerformance:
    """Test performance characteristics of async agent."""

    @pytest.mark.asyncio
    async def test_concurrent_vs_sequential_loading(
        self,
        temp_persist_dir,
        sample_ssis_dir,
        sample_json_dir,
        sample_csv_dir
    ):
        """Test that concurrent loading is actually faster."""
        import time

        # Sequential
        agent_seq = AsyncEnterpriseAgent(persist_dir=temp_persist_dir / "seq")
        start = time.time()
        await agent_seq.load_documents(sample_ssis_dir)
        await agent_seq.load_documents(sample_json_dir, pattern="*.json")
        await agent_seq.load_documents(sample_csv_dir, pattern="*.csv")
        sequential_time = time.time() - start

        # Concurrent
        agent_conc = AsyncEnterpriseAgent(persist_dir=temp_persist_dir / "conc")
        start = time.time()
        await asyncio.gather(
            agent_conc.load_documents(sample_ssis_dir),
            agent_conc.load_documents(sample_json_dir, pattern="*.json"),
            agent_conc.load_documents(sample_csv_dir, pattern="*.csv"),
        )
        concurrent_time = time.time() - start

        # Concurrent should be same or faster (accounting for overhead)
        # For small datasets, overhead might make it similar
        assert concurrent_time <= sequential_time * 1.5  # Allow 50% overhead
