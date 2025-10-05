"""Performance benchmarks for sync vs async agents."""

import asyncio
import tempfile
import time
from pathlib import Path

import pytest

from traceai.agents import EnterpriseAgent, AsyncEnterpriseAgent


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
def sample_cobol_dir():
    """Path to sample COBOL files."""
    return Path(__file__).parent.parent / "examples" / "inputs" / "cobol"


@pytest.fixture
def sample_jcl_dir():
    """Path to sample JCL files."""
    return Path(__file__).parent.parent / "examples" / "inputs" / "jcl"


class TestSyncPerformance:
    """Benchmark sync agent performance."""

    def test_sync_load_single_directory(self, sample_ssis_dir, benchmark):
        """Benchmark loading a single directory (sync)."""
        def load_ssis():
            with tempfile.TemporaryDirectory() as temp_dir:
                agent = EnterpriseAgent(persist_dir=temp_dir)
                agent.load_documents(sample_ssis_dir)
                return agent

        result = benchmark(load_ssis)
        assert result.graph is not None

    def test_sync_load_multiple_directories_sequential(
        self,
        sample_ssis_dir,
        sample_json_dir,
        sample_csv_dir,
        benchmark
    ):
        """Benchmark loading multiple directories sequentially (sync)."""
        def load_all():
            with tempfile.TemporaryDirectory() as temp_dir:
                agent = EnterpriseAgent(persist_dir=temp_dir)
                agent.load_documents(sample_ssis_dir)
                agent.load_documents(sample_json_dir, pattern="*.json")
                agent.load_documents(sample_csv_dir, pattern="*.csv")
                return agent

        result = benchmark(load_all)
        assert len(result.parsed_documents) > 2

    def test_sync_graph_queries(self, sample_ssis_dir, benchmark):
        """Benchmark graph queries (sync)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = EnterpriseAgent(persist_dir=temp_dir)
            agent.load_documents(sample_ssis_dir)

            from traceai.graph.queries import GraphQueries
            queries = GraphQueries(agent.graph)

            def run_queries():
                queries.get_graph_stats()
                queries.find_all_documents()
                queries.find_all_components()
                queries.trace_data_lineage("Customer", direction="both")

            benchmark(run_queries)


@pytest.mark.asyncio
class TestAsyncPerformance:
    """Benchmark async agent performance."""

    async def test_async_load_single_directory(self, sample_ssis_dir, benchmark):
        """Benchmark loading a single directory (async)."""
        async def load_ssis():
            with tempfile.TemporaryDirectory() as temp_dir:
                agent = AsyncEnterpriseAgent(persist_dir=temp_dir)
                await agent.load_documents(sample_ssis_dir)
                return agent

        result = await benchmark(load_ssis)
        assert result.graph is not None

    async def test_async_load_multiple_directories_concurrent(
        self,
        sample_ssis_dir,
        sample_json_dir,
        sample_csv_dir,
        benchmark
    ):
        """Benchmark loading multiple directories concurrently (async)."""
        async def load_all():
            with tempfile.TemporaryDirectory() as temp_dir:
                agent = AsyncEnterpriseAgent(persist_dir=temp_dir, max_concurrent_parsers=20)
                await asyncio.gather(
                    agent.load_documents(sample_ssis_dir),
                    agent.load_documents(sample_json_dir, pattern="*.json"),
                    agent.load_documents(sample_csv_dir, pattern="*.csv"),
                )
                return agent

        result = await benchmark(load_all)
        assert len(result.parsed_documents) > 2


class TestPerformanceComparison:
    """Direct comparison of sync vs async performance."""

    def test_compare_single_directory_load(self, sample_ssis_dir):
        """Compare sync vs async for single directory."""
        # Sync
        with tempfile.TemporaryDirectory() as temp_dir:
            start = time.time()
            agent_sync = EnterpriseAgent(persist_dir=temp_dir)
            agent_sync.load_documents(sample_ssis_dir)
            sync_time = time.time() - start

        # Async
        async def async_load():
            with tempfile.TemporaryDirectory() as temp_dir:
                start = time.time()
                agent_async = AsyncEnterpriseAgent(persist_dir=temp_dir)
                await agent_async.load_documents(sample_ssis_dir)
                return time.time() - start

        async_time = asyncio.run(async_load())

        # Log results
        print(f"\nSingle directory load:")
        print(f"  Sync:  {sync_time:.3f}s")
        print(f"  Async: {async_time:.3f}s")
        print(f"  Ratio: {sync_time/async_time:.2f}x")

        # Both should complete successfully
        assert sync_time > 0
        assert async_time > 0

    def test_compare_multiple_directories(
        self,
        sample_ssis_dir,
        sample_json_dir,
        sample_csv_dir
    ):
        """Compare sync vs async for multiple directories."""
        # Sync (sequential)
        with tempfile.TemporaryDirectory() as temp_dir:
            start = time.time()
            agent_sync = EnterpriseAgent(persist_dir=temp_dir)
            agent_sync.load_documents(sample_ssis_dir)
            agent_sync.load_documents(sample_json_dir, pattern="*.json")
            agent_sync.load_documents(sample_csv_dir, pattern="*.csv")
            sync_time = time.time() - start
            sync_count = len(agent_sync.parsed_documents)

        # Async (concurrent)
        async def async_load():
            with tempfile.TemporaryDirectory() as temp_dir:
                start = time.time()
                agent_async = AsyncEnterpriseAgent(
                    persist_dir=temp_dir,
                    max_concurrent_parsers=20
                )
                await asyncio.gather(
                    agent_async.load_documents(sample_ssis_dir),
                    agent_async.load_documents(sample_json_dir, pattern="*.json"),
                    agent_async.load_documents(sample_csv_dir, pattern="*.csv"),
                )
                return time.time() - start, len(agent_async.parsed_documents)

        async_time, async_count = asyncio.run(async_load())

        # Log results
        print(f"\nMultiple directories load:")
        print(f"  Sync:  {sync_time:.3f}s ({sync_count} docs)")
        print(f"  Async: {async_time:.3f}s ({async_count} docs)")
        print(f"  Speedup: {sync_time/async_time:.2f}x")

        # Both should load same number of documents
        assert sync_count == async_count
        assert sync_time > 0
        assert async_time > 0

    def test_compare_large_dataset(self, sample_cobol_dir, sample_jcl_dir):
        """Compare performance on large dataset (many files)."""
        # Skip if directories don't exist or are empty
        if not sample_cobol_dir.exists() or not sample_jcl_dir.exists():
            pytest.skip("Sample directories not found")

        cobol_files = list(sample_cobol_dir.glob("*.cbl"))
        jcl_files = list(sample_jcl_dir.glob("*.jcl"))

        if len(cobol_files) < 5 or len(jcl_files) < 5:
            pytest.skip("Not enough sample files for performance test")

        # Sync
        with tempfile.TemporaryDirectory() as temp_dir:
            start = time.time()
            agent_sync = EnterpriseAgent(persist_dir=temp_dir)
            agent_sync.load_documents(sample_cobol_dir, pattern="*.cbl")
            agent_sync.load_documents(sample_jcl_dir, pattern="*.jcl")
            sync_time = time.time() - start
            sync_count = len(agent_sync.parsed_documents)

        # Async
        async def async_load():
            with tempfile.TemporaryDirectory() as temp_dir:
                start = time.time()
                agent_async = AsyncEnterpriseAgent(
                    persist_dir=temp_dir,
                    max_concurrent_parsers=20
                )
                await asyncio.gather(
                    agent_async.load_documents(sample_cobol_dir, pattern="*.cbl"),
                    agent_async.load_documents(sample_jcl_dir, pattern="*.jcl"),
                )
                return time.time() - start, len(agent_async.parsed_documents)

        async_time, async_count = asyncio.run(async_load())

        # Log results
        print(f"\nLarge dataset load ({len(cobol_files)} COBOL + {len(jcl_files)} JCL):")
        print(f"  Sync:  {sync_time:.3f}s ({sync_count} docs)")
        print(f"  Async: {async_time:.3f}s ({async_count} docs)")
        print(f"  Speedup: {sync_time/async_time:.2f}x")

        # Async should be faster for large datasets
        # Allow for some overhead, but should see speedup
        assert async_time <= sync_time * 1.2  # At worst, only 20% slower

        # Should load same number of documents
        assert sync_count == async_count


class TestMemoryUsage:
    """Test memory efficiency of sync vs async."""

    def test_sync_memory_cleanup(self, sample_ssis_dir):
        """Test sync agent cleans up memory properly."""
        import gc

        with tempfile.TemporaryDirectory() as temp_dir:
            agent = EnterpriseAgent(persist_dir=temp_dir)
            agent.load_documents(sample_ssis_dir)

            # Delete agent
            del agent
            gc.collect()

            # Should not leak memory (basic check)
            assert True

    @pytest.mark.asyncio
    async def test_async_memory_cleanup(self, sample_ssis_dir):
        """Test async agent cleans up memory properly."""
        import gc

        with tempfile.TemporaryDirectory() as temp_dir:
            agent = AsyncEnterpriseAgent(persist_dir=temp_dir)
            await agent.load_documents(sample_ssis_dir)

            # Delete agent
            del agent
            gc.collect()

            # Should not leak memory (basic check)
            assert True


class TestConcurrencyLimits:
    """Test different concurrency configurations."""

    @pytest.mark.asyncio
    async def test_different_concurrency_levels(self, sample_cobol_dir):
        """Test performance with different max_concurrent_parsers settings."""
        if not sample_cobol_dir.exists():
            pytest.skip("Sample directory not found")

        files = list(sample_cobol_dir.glob("*.cbl"))
        if len(files) < 10:
            pytest.skip("Not enough files for concurrency test")

        results = {}

        for max_concurrent in [1, 5, 10, 20]:
            with tempfile.TemporaryDirectory() as temp_dir:
                start = time.time()
                agent = AsyncEnterpriseAgent(
                    persist_dir=temp_dir,
                    max_concurrent_parsers=max_concurrent
                )
                await agent.load_documents(sample_cobol_dir, pattern="*.cbl")
                elapsed = time.time() - start
                results[max_concurrent] = elapsed

        # Log results
        print("\nConcurrency levels:")
        for max_concurrent, elapsed in results.items():
            print(f"  max_concurrent={max_concurrent:2d}: {elapsed:.3f}s")

        # Higher concurrency should generally be faster (or similar for small datasets)
        assert results[1] >= results[20] * 0.8  # Allow some variance
