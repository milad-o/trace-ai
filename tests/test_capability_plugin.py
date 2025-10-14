"""
Unit tests for TraceAI capability plugin.

Tests the new plugin architecture where TraceAI is a capability module
that can be plugged into any DeepAgent system.
"""

import asyncio
from pathlib import Path

import pytest

from traceai.capabilities import TraceAICapability


@pytest.fixture
def temp_persist_dir(tmp_path):
    """Create temporary directory for testing."""
    return tmp_path / "traceai_test"


@pytest.fixture
def sample_ssis_dir():
    """Return path to sample SSIS files."""
    return Path(__file__).parent.parent / "examples" / "inputs" / "ssis"


class TestTraceAICapability:
    """Test TraceAI capability plugin."""
    
    def test_initialization(self, temp_persist_dir):
        """Test capability initialization."""
        cap = TraceAICapability(persist_dir=temp_persist_dir)
        
        assert cap.persist_dir == temp_persist_dir
        assert cap.graph is None  # No documents loaded yet
        assert cap.parsed_documents == []
        assert cap.vector_store is not None
        assert cap.embeddings is not None
    
    @pytest.mark.asyncio
    async def test_load_documents(self, temp_persist_dir, sample_ssis_dir):
        """Test loading documents builds graph."""
        if not sample_ssis_dir.exists():
            pytest.skip("Sample SSIS files not found")
        
        cap = TraceAICapability(persist_dir=temp_persist_dir)
        await cap.load_documents(sample_ssis_dir, pattern="**/*.dtsx")
        
        assert cap.graph is not None
        assert cap.graph.number_of_nodes() > 0
        assert cap.graph.number_of_edges() > 0
        assert len(cap.parsed_documents) > 0
    
    @pytest.mark.asyncio
    async def test_get_tools_before_load(self, temp_persist_dir):
        """Test get_tools() before loading documents."""
        cap = TraceAICapability(persist_dir=temp_persist_dir)
        tools = cap.get_tools()
        
        # Should return empty list and log warning
        assert tools == []
    
    @pytest.mark.asyncio
    async def test_get_tools_after_load(self, temp_persist_dir, sample_ssis_dir):
        """Test get_tools() returns all TraceAI tools."""
        if not sample_ssis_dir.exists():
            pytest.skip("Sample SSIS files not found")
        
        cap = TraceAICapability(persist_dir=temp_persist_dir)
        await cap.load_documents(sample_ssis_dir, pattern="**/*.dtsx")
        
        tools = cap.get_tools()
        
        assert len(tools) > 0
        tool_names = [t.name for t in tools]
        
        # Check for key tools
        assert "semantic_search" in tool_names
        assert "trace_lineage" in tool_names or "search_dependencies" in tool_names
        assert "graph_query" in tool_names or any("graph" in n for n in tool_names)
    
    @pytest.mark.asyncio
    async def test_get_subagents(self, temp_persist_dir, sample_ssis_dir):
        """Test get_subagents() returns specialized sub-agents."""
        if not sample_ssis_dir.exists():
            pytest.skip("Sample SSIS files not found")
        
        cap = TraceAICapability(persist_dir=temp_persist_dir)
        await cap.load_documents(sample_ssis_dir, pattern="**/*.dtsx")
        
        subagents = cap.get_subagents()
        
        assert len(subagents) > 0
        # SubAgent is a TypedDict, access with dict syntax
        subagent_names = [sa["name"] for sa in subagents]
        
        # Check for expected sub-agents
        expected = ["search_specialist", "lineage_analyst", "code_generator", "parser_expert"]
        for name in expected:
            assert name in subagent_names
    
    @pytest.mark.asyncio
    async def test_get_middleware(self, temp_persist_dir):
        """Test get_middleware() returns custom middleware."""
        cap = TraceAICapability(persist_dir=temp_persist_dir)
        
        # Test with all enabled
        middleware = cap.get_middleware(
            enable_memory=True,
            enable_audit=True,
            enable_progress=True,
        )
        
        assert len(middleware) > 0
        
        # Test with selective enabling
        middleware_minimal = cap.get_middleware(
            enable_memory=False,
            enable_audit=False,
            enable_progress=True,
        )
        
        assert len(middleware_minimal) < len(middleware)
    
    @pytest.mark.asyncio
    async def test_get_graph_stats(self, temp_persist_dir, sample_ssis_dir):
        """Test get_graph_stats() returns statistics."""
        if not sample_ssis_dir.exists():
            pytest.skip("Sample SSIS files not found")
        
        cap = TraceAICapability(persist_dir=temp_persist_dir)
        
        # Before loading
        stats_empty = cap.get_graph_stats()
        assert "error" in stats_empty
        
        # After loading
        await cap.load_documents(sample_ssis_dir, pattern="**/*.dtsx")
        stats = cap.get_graph_stats()
        
        assert "error" not in stats
        assert "total_nodes" in stats or "nodes" in stats
    
    @pytest.mark.asyncio
    async def test_multiple_load_calls(self, temp_persist_dir, sample_ssis_dir):
        """Test loading documents multiple times accumulates."""
        if not sample_ssis_dir.exists():
            pytest.skip("Sample SSIS files not found")
        
        cap = TraceAICapability(persist_dir=temp_persist_dir)
        
        # Load once
        await cap.load_documents(sample_ssis_dir, pattern="**/*.dtsx")
        initial_count = len(cap.parsed_documents)
        
        # Load again (should accumulate)
        await cap.load_documents(sample_ssis_dir, pattern="**/*.dtsx")
        final_count = len(cap.parsed_documents)
        
        assert final_count >= initial_count
    
    @pytest.mark.asyncio
    async def test_multiple_patterns(self, temp_persist_dir):
        """Test loading with multiple file patterns."""
        # Use current directory as test (no files expected)
        cap = TraceAICapability(persist_dir=temp_persist_dir)
        
        # Should handle list of patterns
        await cap.load_documents(
            directory=temp_persist_dir,
            pattern=["**/*.dtsx", "**/*.cbl", "**/*.jcl"]
        )
        
        # No error should be raised even if no files found


class TestCapabilityIntegration:
    """Integration tests for capability plugin."""
    
    @pytest.mark.asyncio
    async def test_tools_are_callable(self, temp_persist_dir, sample_ssis_dir):
        """Test that returned tools are actually callable."""
        if not sample_ssis_dir.exists():
            pytest.skip("Sample SSIS files not found")
        
        cap = TraceAICapability(persist_dir=temp_persist_dir)
        await cap.load_documents(sample_ssis_dir, pattern="**/*.dtsx")
        
        tools = cap.get_tools()
        
        # Find semantic_search tool
        semantic_search = next((t for t in tools if t.name == "semantic_search"), None)
        assert semantic_search is not None
        
        # Try invoking it
        result = semantic_search.invoke({"query": "customer", "max_results": 5})
        assert result is not None
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_subagents_have_tools(self, temp_persist_dir, sample_ssis_dir):
        """Test that sub-agents are assigned tools."""
        if not sample_ssis_dir.exists():
            pytest.skip("Sample SSIS files not found")
        
        cap = TraceAICapability(persist_dir=temp_persist_dir)
        await cap.load_documents(sample_ssis_dir, pattern="**/*.dtsx")
        
        subagents = cap.get_subagents()
        
        # Each sub-agent should have tools key (SubAgent is TypedDict)
        # Some may have empty lists if no matching tools
        for subagent in subagents:
            assert "tools" in subagent
            assert subagent["tools"] is not None
        
        # At least one sub-agent should have tools
        total_tools = sum(len(sa["tools"]) for sa in subagents)
        assert total_tools > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
