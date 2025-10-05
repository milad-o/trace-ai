"""Comprehensive API tests for EnterpriseAgent (sync version)."""

import os
from pathlib import Path
import tempfile
import shutil

import pytest

from traceai.agents import EnterpriseAgent
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


class TestEnterpriseAgentAPI:
    """Test EnterpriseAgent API functionality."""

    def test_agent_initialization_no_api_key(self, temp_persist_dir):
        """Test agent can initialize without API key (graph-only mode)."""
        # Clear API keys
        old_anthropic = os.environ.pop("ANTHROPIC_API_KEY", None)
        old_openai = os.environ.pop("OPENAI_API_KEY", None)

        try:
            agent = EnterpriseAgent(
                model_provider="anthropic",
                persist_dir=temp_persist_dir
            )

            assert agent.llm is None
            assert agent.model_provider == "anthropic"
            assert agent.graph is None
            assert agent.agent is None
        finally:
            # Restore API keys
            if old_anthropic:
                os.environ["ANTHROPIC_API_KEY"] = old_anthropic
            if old_openai:
                os.environ["OPENAI_API_KEY"] = old_openai

    def test_load_single_ssis_package(self, temp_persist_dir, sample_ssis_dir):
        """Test loading a single SSIS package."""
        agent = EnterpriseAgent(persist_dir=temp_persist_dir)
        agent.load_documents(sample_ssis_dir)

        assert agent.graph is not None
        assert agent.graph.number_of_nodes() > 0
        assert agent.graph.number_of_edges() > 0
        assert len(agent.parsed_documents) == 2  # CustomerETL and SalesAggregation

    def test_load_multiple_file_types(self, temp_persist_dir, sample_ssis_dir, sample_json_dir):
        """Test loading multiple file types."""
        agent = EnterpriseAgent(persist_dir=temp_persist_dir)

        # Load SSIS
        agent.load_documents(sample_ssis_dir)
        ssis_count = len(agent.parsed_documents)

        # Load JSON
        agent.load_documents(sample_json_dir, pattern="*.json")
        total_count = len(agent.parsed_documents)

        assert total_count > ssis_count
        assert agent.graph is not None

    def test_graph_statistics(self, temp_persist_dir, sample_ssis_dir):
        """Test getting graph statistics."""
        agent = EnterpriseAgent(persist_dir=temp_persist_dir)
        agent.load_documents(sample_ssis_dir)

        stats = agent.get_graph_stats()

        assert "total_nodes" in stats
        assert "total_edges" in stats
        assert "documents" in stats
        assert "components" in stats
        assert stats["total_nodes"] > 0
        assert stats["total_edges"] > 0

    def test_graph_queries_lineage(self, temp_persist_dir, sample_ssis_dir):
        """Test data lineage tracing."""
        agent = EnterpriseAgent(persist_dir=temp_persist_dir)
        agent.load_documents(sample_ssis_dir)

        queries = GraphQueries(agent.graph)

        # Trace lineage for a known table
        lineage = queries.trace_data_lineage("Customer", direction="both")

        assert "upstream" in lineage
        assert "downstream" in lineage
        assert isinstance(lineage["upstream"], list)
        assert isinstance(lineage["downstream"], list)

    def test_graph_queries_impact_analysis(self, temp_persist_dir, sample_ssis_dir):
        """Test impact analysis for table changes."""
        agent = EnterpriseAgent(persist_dir=temp_persist_dir)
        agent.load_documents(sample_ssis_dir)

        queries = GraphQueries(agent.graph)

        # Find tasks reading from Customer table
        readers = queries.find_tasks_reading_from_table("Customer")
        writers = queries.find_tasks_writing_to_table("Customer")

        assert isinstance(readers, list)
        assert isinstance(writers, list)

    def test_vector_store_indexing(self, temp_persist_dir, sample_ssis_dir):
        """Test that documents are indexed in vector store."""
        agent = EnterpriseAgent(persist_dir=temp_persist_dir)
        agent.load_documents(sample_ssis_dir)

        # Search for something we know exists
        results = agent.vector_store.similarity_search("customer", k=5)

        assert len(results) > 0
        assert any("customer" in doc.page_content.lower() for doc in results)

    def test_load_with_patterns(self, temp_persist_dir, sample_json_dir):
        """Test loading documents with specific patterns."""
        agent = EnterpriseAgent(persist_dir=temp_persist_dir)

        # Load only .json files
        agent.load_documents(sample_json_dir, pattern="*.json")

        assert len(agent.parsed_documents) > 0
        assert all(doc.metadata.file_path.suffix == ".json" for doc in agent.parsed_documents)

    def test_load_multiple_patterns(self, temp_persist_dir):
        """Test loading with multiple file patterns."""
        agent = EnterpriseAgent(persist_dir=temp_persist_dir)

        inputs_dir = Path(__file__).parent.parent / "examples" / "inputs"

        # Load JSON and CSV files
        agent.load_documents(inputs_dir / "json", pattern=["*.json"])
        json_count = len(agent.parsed_documents)

        agent.load_documents(inputs_dir / "csv", pattern=["*.csv"])
        total_count = len(agent.parsed_documents)

        assert total_count > json_count

    def test_empty_directory_handling(self, temp_persist_dir):
        """Test handling of empty directories."""
        agent = EnterpriseAgent(persist_dir=temp_persist_dir)

        # Create empty temp directory
        empty_dir = temp_persist_dir / "empty"
        empty_dir.mkdir()

        # Should not raise error
        agent.load_documents(empty_dir)

        assert agent.graph is None or agent.graph.number_of_nodes() == 0

    def test_persistence_directory_creation(self):
        """Test that persistence directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            persist_path = Path(temp_dir) / "new_dir" / "agent_data"

            agent = EnterpriseAgent(persist_dir=persist_path)

            assert persist_path.exists()
            assert persist_path.is_dir()

    def test_model_provider_validation(self, temp_persist_dir):
        """Test that invalid model provider raises error."""
        with pytest.raises(ValueError, match="Unknown model provider"):
            EnterpriseAgent(
                model_provider="invalid_provider",
                persist_dir=temp_persist_dir
            )

    def test_middleware_configuration(self, temp_persist_dir):
        """Test middleware can be disabled."""
        agent = EnterpriseAgent(
            persist_dir=temp_persist_dir,
            enable_memory=False,
            enable_audit=False,
            enable_progress=False
        )

        assert agent.enable_memory is False
        assert agent.enable_audit is False
        assert agent.enable_progress is False

    def test_incremental_document_loading(self, temp_persist_dir, sample_ssis_dir, sample_json_dir):
        """Test that documents can be loaded incrementally."""
        agent = EnterpriseAgent(persist_dir=temp_persist_dir)

        # Load first batch
        agent.load_documents(sample_ssis_dir)
        first_count = len(agent.parsed_documents)
        first_nodes = agent.graph.number_of_nodes()

        # Load second batch
        agent.load_documents(sample_json_dir, pattern="*.json")
        second_count = len(agent.parsed_documents)
        second_nodes = agent.graph.number_of_nodes()

        # Should accumulate, not replace
        assert second_count > first_count
        assert second_nodes >= first_nodes


class TestEnterpriseAgentParsers:
    """Test that all parsers work correctly through the agent."""

    def test_ssis_parser(self, temp_persist_dir, sample_ssis_dir):
        """Test SSIS parser through agent."""
        agent = EnterpriseAgent(persist_dir=temp_persist_dir)
        agent.load_documents(sample_ssis_dir)

        assert len(agent.parsed_documents) == 2
        assert all(doc.metadata.document_type.value == "ssis_package" for doc in agent.parsed_documents)

    def test_json_parser(self, temp_persist_dir, sample_json_dir):
        """Test JSON parser through agent."""
        agent = EnterpriseAgent(persist_dir=temp_persist_dir)
        agent.load_documents(sample_json_dir, pattern="*.json")

        assert len(agent.parsed_documents) > 0
        assert all(doc.metadata.document_type.value == "json_config" for doc in agent.parsed_documents)

    def test_csv_parser(self, temp_persist_dir, sample_csv_dir):
        """Test CSV parser through agent."""
        agent = EnterpriseAgent(persist_dir=temp_persist_dir)
        agent.load_documents(sample_csv_dir, pattern="*.csv")

        assert len(agent.parsed_documents) > 0
        assert all(doc.metadata.document_type.value == "csv_metadata" for doc in agent.parsed_documents)

    def test_excel_parser(self, temp_persist_dir, sample_excel_dir):
        """Test Excel parser through agent."""
        agent = EnterpriseAgent(persist_dir=temp_persist_dir)
        agent.load_documents(sample_excel_dir, pattern="*.xlsx")

        assert len(agent.parsed_documents) > 0
        assert all(doc.metadata.document_type.value == "excel_workbook" for doc in agent.parsed_documents)


class TestEnterpriseAgentGraphOperations:
    """Test graph-specific operations through the agent."""

    def test_find_all_documents(self, temp_persist_dir, sample_ssis_dir):
        """Test finding all documents in the graph."""
        agent = EnterpriseAgent(persist_dir=temp_persist_dir)
        agent.load_documents(sample_ssis_dir)

        queries = GraphQueries(agent.graph)
        docs = queries.find_all_documents()

        assert len(docs) == 2
        assert all(node_data["node_type"] == "document" for _, node_data in docs)

    def test_find_all_components(self, temp_persist_dir, sample_ssis_dir):
        """Test finding all components in the graph."""
        agent = EnterpriseAgent(persist_dir=temp_persist_dir)
        agent.load_documents(sample_ssis_dir)

        queries = GraphQueries(agent.graph)
        components = queries.find_all_components()

        assert len(components) > 0
        assert all(node_data["node_type"] == "component" for _, node_data in components)

    def test_find_all_data_sources(self, temp_persist_dir, sample_ssis_dir):
        """Test finding all data sources in the graph."""
        agent = EnterpriseAgent(persist_dir=temp_persist_dir)
        agent.load_documents(sample_ssis_dir)

        queries = GraphQueries(agent.graph)
        data_sources = queries.find_all_data_sources()

        assert len(data_sources) > 0
        assert all(node_data["node_type"] == "data_source" for _, node_data in data_sources)
