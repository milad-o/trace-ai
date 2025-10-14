"""Demo to test all TraceAI middleware capabilities."""

import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

from traceai.agents import TraceAI


async def test_conversation_memory():
    """Test ConversationMemoryMiddleware with persistent storage."""
    print("\n" + "=" * 80)
    print("TEST 1: Conversation Memory Middleware")
    print("=" * 80)
    
    load_dotenv(Path.cwd() / ".env")
    
    agent = TraceAI(
        model_provider="openai",
        enable_memory=True,  # ConversationMemoryMiddleware
        enable_audit=False,
        enable_progress=False,
        max_conversation_messages=10  # Small limit to test condensing
    )
    
    # Load some data
    ssis_dir = Path(__file__).parent.parent / "inputs/ssis"
    await agent.load_documents(ssis_dir, pattern="*.dtsx")
    
    print("\n📝 Sending multiple messages to test memory...")
    
    # Send several messages
    questions = [
        "What packages are loaded?",
        "Tell me about CustomerETL",
        "What tasks does it have?",
        "What data sources does it use?",
    ]
    
    for i, q in enumerate(questions, 1):
        print(f"\n[{i}] Question: {q}")
        response = await agent.query(q)
        print(f"    Response: {response[:100]}...")
    
    # Search conversation history
    print("\n🔍 Searching conversation history for 'CustomerETL'...")
    if hasattr(agent, '_middlewares') and agent._middlewares:
        for mw in agent._middlewares:
            if hasattr(mw, 'search_history'):
                results = mw.search_history("CustomerETL", limit=3)
                print(f"   Found {len(results)} matching messages")
                for r in results[:2]:
                    print(f"   - {r.get('role')}: {r.get('content', '')[:50]}...")
                break
    
    print("\n✅ Conversation memory test complete!")


async def test_long_term_memory():
    """Test LongTermMemoryMiddleware with vector storage."""
    print("\n" + "=" * 80)
    print("TEST 2: Long-Term Memory Middleware")
    print("=" * 80)
    
    load_dotenv(Path.cwd() / ".env")
    
    agent = TraceAI(
        model_provider="openai",
        enable_memory=False,
        enable_audit=False,
        enable_progress=False,
    )
    
    # Manually create and add long-term memory middleware
    from traceai.agents.middlewares import LongTermMemoryMiddleware
    
    ltm = LongTermMemoryMiddleware(
        backend="chroma",
        persist_dir="./data/test_ltm",
        ephemeral=True  # In-memory for testing
    )
    
    print("\n💾 Adding important facts to long-term memory...")
    
    # Simulate adding facts
    facts = [
        "Important: CustomerETL processes customer data from source database",
        "Note: SalesAggregation runs daily at midnight",
        "Remember: dbo.Customers table has 50,000 records",
    ]
    
    for fact in facts:
        ltm.vector_store.add(
            texts=[fact],
            metadatas=[{"type": "important_fact"}]
        )
        print(f"   ✓ Added: {fact[:60]}...")
    
    print("\n🔎 Searching long-term memory...")
    results = ltm.search_memory("customer database", n_results=2)
    print(f"   Found {len(results)} relevant memories:")
    for r in results:
        print(f"   - {r.get('text', '')[:70]}...")
    
    print("\n✅ Long-term memory test complete!")


async def test_audit_middleware():
    """Test AuditMiddleware logging capabilities."""
    print("\n" + "=" * 80)
    print("TEST 3: Audit Middleware")
    print("=" * 80)
    
    load_dotenv(Path.cwd() / ".env")
    
    agent = TraceAI(
        model_provider="openai",
        enable_memory=False,
        enable_audit=True,  # AuditMiddleware
        enable_progress=False,
    )
    
    # Load data
    ssis_dir = Path(__file__).parent.parent / "inputs/ssis"
    await agent.load_documents(ssis_dir, pattern="*.dtsx")
    
    print("\n🔍 Running query to trigger tool calls...")
    print("   (Watch for [AUDIT] logs showing tool calls)")
    
    response = await agent.query("List all packages")
    
    print("\n📊 Checking audit logs...")
    if hasattr(agent, '_middlewares') and agent._middlewares:
        for mw in agent._middlewares:
            if hasattr(mw, 'tool_calls'):
                print(f"   Total model calls: {mw.model_calls}")
                print(f"   Total tool calls: {len(mw.tool_calls)}")
                print(f"   Tools used: {list(set(mw.tool_calls))}")
                break
    
    print("\n✅ Audit middleware test complete!")


async def test_progress_tracking():
    """Test ProgressTrackingMiddleware."""
    print("\n" + "=" * 80)
    print("TEST 4: Progress Tracking Middleware")
    print("=" * 80)
    
    load_dotenv(Path.cwd() / ".env")
    
    agent = TraceAI(
        model_provider="openai",
        enable_memory=False,
        enable_audit=False,
        enable_progress=True,  # ProgressTrackingMiddleware
    )
    
    # Load data
    ssis_dir = Path(__file__).parent.parent / "inputs/ssis"
    await agent.load_documents(ssis_dir, pattern="*.dtsx")
    
    print("\n📈 Running query to track progress...")
    print("   (Watch for [PROGRESS] logs)")
    
    response = await agent.query("Describe the CustomerETL package structure")
    
    print("\n📊 Checking progress metadata...")
    if hasattr(agent, '_middlewares') and agent._middlewares:
        for mw in agent._middlewares:
            if hasattr(mw, 'current_step'):
                print(f"   Current step: {mw.current_step}")
                print(f"   Total steps: {mw.total_steps}")
                if mw.total_steps > 0:
                    pct = (mw.current_step / mw.total_steps) * 100
                    print(f"   Progress: {pct:.0f}%")
                break
    
    print("\n✅ Progress tracking test complete!")


async def test_all_middlewares():
    """Test all middlewares working together."""
    print("\n" + "=" * 80)
    print("TEST 5: All Middlewares Combined")
    print("=" * 80)
    
    load_dotenv(Path.cwd() / ".env")
    
    agent = TraceAI(
        model_provider="openai",
        enable_memory=True,      # Conversation memory
        enable_audit=True,        # Audit logging
        enable_progress=True,     # Progress tracking
        max_conversation_messages=15
    )
    
    # Load data
    cobol_dir = Path(__file__).parent.parent / "inputs/cobol"
    await agent.load_documents(cobol_dir, pattern="*.cbl")
    
    print("\n🚀 Running comprehensive test with all middlewares active...")
    
    questions = [
        "How many COBOL programs are loaded?",
        "Search for programs related to customer",
    ]
    
    for i, q in enumerate(questions, 1):
        print(f"\n[Query {i}] {q}")
        response = await agent.query(q)
        print(f"Response: {response[:150]}...")
    
    print("\n📊 Final Middleware Summary:")
    print("-" * 80)
    
    if hasattr(agent, '_middlewares') and agent._middlewares:
        for mw in agent._middlewares:
            mw_name = mw.__class__.__name__
            print(f"\n{mw_name}:")
            
            if hasattr(mw, 'total_messages_processed'):
                print(f"  - Messages processed: {mw.total_messages_processed}")
            
            if hasattr(mw, 'tool_calls'):
                print(f"  - Tool calls: {len(mw.tool_calls)}")
                print(f"  - Model calls: {mw.model_calls}")
            
            if hasattr(mw, 'current_step'):
                print(f"  - Steps completed: {mw.current_step}/{mw.total_steps}")
            
            if hasattr(mw, 'facts_added'):
                print(f"  - Facts stored: {mw.facts_added}")
    
    print("\n✅ All middlewares test complete!")


async def main():
    """Run all middleware tests."""
    print("=" * 80)
    print("TraceAI Middleware Test Suite")
    print("=" * 80)
    
    tests = [
        ("Conversation Memory", test_conversation_memory),
        ("Long-Term Memory", test_long_term_memory),
        ("Audit Logging", test_audit_middleware),
        ("Progress Tracking", test_progress_tracking),
        ("All Combined", test_all_middlewares),
    ]
    
    for name, test_func in tests:
        try:
            await test_func()
        except Exception as e:
            print(f"\n❌ Test '{name}' failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("🎉 All Middleware Tests Complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
