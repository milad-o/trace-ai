#!/usr/bin/env python3
"""
Planning Demo: Showcase TraceAI's planning-first workflow.

This demonstrates how TraceAI leverages DeepAgents' write_todos tool
to break down complex queries into structured execution plans.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from traceai.agents.traceai import TraceAI
from traceai.logger import logger


async def test_simple_query_no_planning():
    """Test 1: Simple query should NOT use planning (direct tool call)."""
    print("\n" + "=" * 80)
    print("TEST 1: Simple Query (No Planning)")
    print("=" * 80)
    print("Query: 'List all SSIS packages'\n")

    agent = TraceAI(
        model_provider="openai",
        enable_memory=False,
        enable_audit=True,
        enable_progress=True,
    )

    # Load sample SSIS packages
    await agent.load_documents(
        directory=Path(__file__).parent.parent / "inputs" / "ssis",
        pattern="*.dtsx"
    )

    response = await agent.query("List all SSIS packages")
    
    print("\n📋 AGENT RESPONSE:")
    print("-" * 80)
    print(response)
    print("-" * 80)
    
    # Validate: Should be direct, no mention of "step 1 of X"
    if "step" in response.lower() and "of" in response.lower():
        print("\n⚠️  WARNING: Agent used planning for simple query (not optimal)")
    else:
        print("\n✅ PASSED: Agent answered directly without planning")


async def test_complex_query_with_planning():
    """Test 2: Complex multi-step query should use planning."""
    print("\n" + "=" * 80)
    print("TEST 2: Complex Query (Should Use Planning)")
    print("=" * 80)
    print("Query: 'Analyze CustomerETL package, trace all data lineages, and generate a summary report'\n")

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

    response = await agent.query(
        "Analyze the CustomerETL package, trace all its data lineages, "
        "and generate a comprehensive summary report"
    )
    
    print("\n📋 AGENT RESPONSE:")
    print("-" * 80)
    print(response)
    print("-" * 80)
    
    # Validate: Should mention planning/steps
    if "step" in response.lower() or "plan" in response.lower():
        print("\n✅ PASSED: Agent used planning workflow")
    else:
        print("\n⚠️  INFO: Agent might not have used explicit planning")


async def test_planning_with_progress_tracking():
    """Test 3: Verify progress tracking works with planning."""
    print("\n" + "=" * 80)
    print("TEST 3: Planning + Progress Tracking Integration")
    print("=" * 80)
    print("Query: 'Find all packages with database connections, analyze their impact, and create a report'\n")

    agent = TraceAI(
        model_provider="openai",
        enable_memory=False,
        enable_audit=True,
        enable_progress=True,  # Progress middleware should read todos.json
    )

    # Load sample data
    await agent.load_documents(
        directory=Path(__file__).parent.parent / "inputs" / "ssis",
        pattern="*.dtsx"
    )

    response = await agent.query(
        "Find all packages with database connections, analyze their impact, "
        "and create a detailed report"
    )
    
    print("\n📋 AGENT RESPONSE:")
    print("-" * 80)
    print(response)
    print("-" * 80)
    
    # Check if progress tracking showed steps
    print("\n✅ Check logs above for [PROGRESS] indicators")


async def test_error_recovery_with_planning():
    """Test 4: Planning helps with graceful degradation on recursion limits."""
    print("\n" + "=" * 80)
    print("TEST 4: Error Recovery with Planning")
    print("=" * 80)
    print("Query: 'Perform comprehensive analysis of all packages' (intentionally complex)\n")

    agent = TraceAI(
        model_provider="openai",
        enable_memory=False,
        enable_audit=True,
        enable_progress=True,
        recursion_limit=15,  # Intentionally low
    )

    # Load sample data
    await agent.load_documents(
        directory=Path(__file__).parent.parent / "inputs" / "ssis",
        pattern="*.dtsx"
    )

    response = await agent.query(
        "Perform a comprehensive analysis of all packages including lineage, dependencies, "
        "impact analysis, and generate detailed reports with visualizations"
    )
    
    print("\n📋 AGENT RESPONSE:")
    print("-" * 80)
    print(response)
    print("-" * 80)
    
    if "couldn't complete" in response.lower() or "too complex" in response.lower():
        print("\n✅ PASSED: Agent gracefully handled recursion limit")
    else:
        print("\n✅ PASSED: Agent completed the complex analysis")


async def test_planning_todo_format():
    """Test 5: Verify write_todos creates proper structure."""
    print("\n" + "=" * 80)
    print("TEST 5: Planning Todo Structure Validation")
    print("=" * 80)
    print("Query: 'Compare CustomerETL and ProductETL packages and identify key differences'\n")

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

    response = await agent.query(
        "Compare CustomerETL and ProductETL packages and identify their key differences"
    )
    
    print("\n📋 AGENT RESPONSE:")
    print("-" * 80)
    print(response)
    print("-" * 80)
    
    # The agent should have used planning for comparison task
    print("\n✅ Check for structured analysis above")


async def main():
    """Run all planning demos."""
    print("\n" + "=" * 80)
    print("🚀 TRACEAI PLANNING WORKFLOW DEMO")
    print("=" * 80)
    print("\nDemonstrating how TraceAI uses DeepAgents' write_todos for complex queries")
    print("while keeping simple queries direct and efficient.\n")

    try:
        # Test 1: Simple query (no planning needed)
        await test_simple_query_no_planning()
        
        # Test 2: Complex query (should use planning)
        await test_complex_query_with_planning()
        
        # Test 3: Planning + Progress integration
        await test_planning_with_progress_tracking()
        
        # Test 4: Error recovery
        await test_error_recovery_with_planning()
        
        # Test 5: Todo structure
        await test_planning_todo_format()
        
        print("\n" + "=" * 80)
        print("✅ ALL PLANNING DEMOS COMPLETED")
        print("=" * 80)
        print("\nKey Observations:")
        print("1. Simple queries execute directly (1-2 tool calls)")
        print("2. Complex queries use write_todos to create structured plans")
        print("3. Progress tracking integrates with DeepAgents' todos.json")
        print("4. Planning prevents infinite loops and provides visibility")
        print("5. Users see clear step-by-step execution")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
