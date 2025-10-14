#!/usr/bin/env python3
"""
Unit test for ProgressTrackingMiddleware reading DeepAgents' todos.json format.
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from traceai.agents.middlewares import ProgressTrackingMiddleware


def test_progress_tracking_with_todos():
    """Test that middleware correctly reads and tracks DeepAgents' todos."""
    print("\n" + "=" * 80)
    print("UNIT TEST: ProgressTrackingMiddleware with DeepAgents' todos.json")
    print("=" * 80)
    
    middleware = ProgressTrackingMiddleware(show_progress=True)
    
    # Simulate DeepAgents' todos.json structure (uses 'content' field)
    todos = [
        {"content": "Find all data sources", "status": "not-started"},
        {"content": "Trace lineage", "status": "not-started"},
        {"content": "Generate report", "status": "not-started"},
    ]
    
    # Test 1: Initial state with plan
    print("\n📋 TEST 1: Plan Created")
    state1 = {
        "files": {
            "todos.json": json.dumps(todos)
        },
        "messages": []
    }
    
    result1 = middleware.after_model(state1)
    print(f"Result: {result1}")
    assert result1["progress_metadata"]["total"] == 3
    assert result1["progress_metadata"]["completed"] == 0
    print("✅ PASSED: Plan detected with 3 steps")
    
    # Test 2: First step in progress
    print("\n🔄 TEST 2: First Step In Progress")
    todos[0]["status"] = "in-progress"
    state2 = {
        "files": {
            "todos.json": json.dumps(todos)
        },
        "messages": []
    }
    
    result2 = middleware.after_model(state2)
    print(f"Result: {result2}")
    assert result2["progress_metadata"]["in_progress"] == "Find all data sources"
    print("✅ PASSED: Current step identified")
    
    # Test 3: First step completed
    print("\n✅ TEST 3: First Step Completed")
    todos[0]["status"] = "completed"
    todos[1]["status"] = "in-progress"
    state3 = {
        "files": {
            "todos.json": json.dumps(todos)
        },
        "messages": []
    }
    
    result3 = middleware.after_model(state3)
    print(f"Result: {result3}")
    assert result3["progress_metadata"]["completed"] == 1
    assert result3["progress_metadata"]["progress_percentage"] == 33.33333333333333
    print("✅ PASSED: Progress updated to 1/3 (33%)")
    
    # Test 4: All steps completed
    print("\n🎉 TEST 4: All Steps Completed")
    todos[0]["status"] = "completed"
    todos[1]["status"] = "completed"
    todos[2]["status"] = "completed"
    state4 = {
        "files": {
            "todos.json": json.dumps(todos)
        },
        "messages": []
    }
    
    result4 = middleware.after_model(state4)
    print(f"Result: {result4}")
    assert result4["progress_metadata"]["completed"] == 3
    assert result4["progress_metadata"]["all_completed"] is True
    print("✅ PASSED: All steps completed")
    
    # Test 5: No todos.json (simple query)
    print("\n⭕ TEST 5: No Planning (Simple Query)")
    state5 = {
        "files": {},
        "messages": []
    }
    
    result5 = middleware.after_model(state5)
    print(f"Result: {result5}")
    assert result5["progress_metadata"]["has_plan"] is False
    assert result5["progress_metadata"]["completed"] == 0
    print("✅ PASSED: No progress tracking without plan")
    
    print("\n" + "=" * 80)
    print("✅ ALL UNIT TESTS PASSED")
    print("=" * 80)
    print("\nKey Validations:")
    print("1. ✅ Reads state['files']['todos.json'] from DeepAgents")
    print("2. ✅ Supports 'content' field (DeepAgents format)")
    print("3. ✅ Tracks completed vs total todos")
    print("4. ✅ Calculates progress percentage")
    print("5. ✅ Identifies current in-progress step")
    print("6. ✅ Detects plan completion")
    print("7. ✅ Handles missing todos.json gracefully")


if __name__ == "__main__":
    test_progress_tracking_with_todos()
