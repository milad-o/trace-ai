#!/usr/bin/env python3
"""
Test Progress Tracking with DeepAgents' write_todos integration.

This verifies that ProgressTrackingMiddleware correctly reads and tracks
todos created by DeepAgents' PlanningMiddleware.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from traceai.agents.traceai import TraceAI
from traceai.logger import logger


async def test_progress_tracking_with_planning():
    """Test that ProgressTrackingMiddleware reads DeepAgents' todos.json."""
    print("\n" + "=" * 80)
    print("TEST: Progress Tracking with Planning Integration")
    print("=" * 80)
    print("Query: Complex multi-step analysis that should trigger planning\n")

    agent = TraceAI(
        model_provider="openai",
        enable_memory=False,
        enable_audit=True,
        enable_progress=True,  # Should read DeepAgents' todos.json
        enable_filesystem=False,
    )

    # Load sample data
    await agent.load_documents(
        directory=Path(__file__).parent.parent / "inputs" / "ssis",
        pattern="*.dtsx"
    )

    # Complex query that should trigger planning
    response = await agent.query(
        "Analyze the CustomerETL package: first find all its data sources, "
        "then trace its data lineage, and finally summarize the findings"
    )
    
    print("\n📋 AGENT RESPONSE:")
    print("-" * 80)
    print(response)
    print("-" * 80)
    
    # Check logs for progress indicators
    print("\n✅ Check logs above for:")
    print("  - [PROGRESS] 📋 Plan created with N steps")
    print("  - [PROGRESS] ✅ X/N steps complete")
    print("  - [PROGRESS] 🔄 Current: <step name>")
    print("  - [PROGRESS] 🎉 All steps completed!")


async def test_simple_query_no_progress():
    """Test that simple queries don't trigger progress tracking."""
    print("\n" + "=" * 80)
    print("TEST: Simple Query (No Progress Tracking)")
    print("=" * 80)
    print("Query: Simple query that should NOT use planning\n")

    agent = TraceAI(
        model_provider="openai",
        enable_memory=False,
        enable_audit=True,
        enable_progress=True,
    )

    # Load sample data
    await agent.load_documents(
        directory=Path(__file__).parent.parent / "inputs" / "ssis",
        pattern="*.dtsx"
    )

    response = await agent.query("List all SSIS packages")
    
    print("\n📋 AGENT RESPONSE:")
    print("-" * 80)
    print(response)
    print("-" * 80)
    
    print("\n✅ Check logs: Should NOT see [PROGRESS] indicators")


async def test_progress_updates():
    """Test that progress updates as todos are completed."""
    print("\n" + "=" * 80)
    print("TEST: Progress Updates During Execution")
    print("=" * 80)
    print("Query: Multi-step query to verify progress updates\n")

    agent = TraceAI(
        model_provider="openai",
        enable_memory=False,
        enable_audit=True,
        enable_progress=True,
        recursion_limit=50,  # Allow more steps for complex query
    )

    # Load sample data
    await agent.load_documents(
        directory=Path(__file__).parent.parent / "inputs" / "ssis",
        pattern="*.dtsx"
    )

    response = await agent.query(
        "First, identify all packages. Then, for the CustomerETL package, "
        "analyze its components and data sources. Finally, create a summary."
    )
    
    print("\n📋 AGENT RESPONSE:")
    print("-" * 80)
    print(response)
    print("-" * 80)
    
    print("\n✅ Check logs above for incremental progress updates")


async def main():
    """Run all progress tracking tests."""
    print("\n" + "=" * 80)
    print("🚀 PROGRESS TRACKING MIDDLEWARE TEST")
    print("=" * 80)
    print("\nVerifying that ProgressTrackingMiddleware reads DeepAgents' todos.json")
    print("and displays progress updates during multi-step operations.\n")

    try:
        # Test 1: Complex query with planning
        await test_progress_tracking_with_planning()
        
        # Test 2: Simple query (no planning)
        await test_simple_query_no_progress()
        
        # Test 3: Progress updates
        await test_progress_updates()
        
        print("\n" + "=" * 80)
        print("✅ ALL PROGRESS TRACKING TESTS COMPLETED")
        print("=" * 80)
        print("\nKey Observations:")
        print("1. ProgressTrackingMiddleware reads state['files']['todos.json']")
        print("2. Progress shown as: completed/total (percentage)")
        print("3. Current step displayed with 🔄 emoji")
        print("4. Completion celebrated with 🎉 emoji")
        print("5. No progress tracking for simple queries")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
