"""Tests for memory storage backends."""

import tempfile
from pathlib import Path

import pytest

from traceai.memory.conversation_store import SQLiteConversationStore
from traceai.memory.vector_store import ChromaVectorStore


class TestSQLiteConversationStore:
    """Tests for SQLite conversation storage."""

    def test_ephemeral_store(self):
        """Test in-memory ephemeral storage."""
        store = SQLiteConversationStore(ephemeral=True)

        # Add messages
        store.add_message("user", "Hello, how are you?")
        store.add_message("assistant", "I'm doing well, thank you!")

        # Get recent
        messages = store.get_recent_messages(limit=10)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"

    def test_persistent_store(self):
        """Test persistent storage to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Create store and add messages
            store1 = SQLiteConversationStore(db_path=db_path, ephemeral=False)
            store1.add_message("user", "Test message 1")
            store1.add_message("assistant", "Response 1")

            # Create new store instance (same DB)
            store2 = SQLiteConversationStore(db_path=db_path, ephemeral=False)
            messages = store2.get_all_messages()

            assert len(messages) == 2
            assert messages[0]["content"] == "Test message 1"

    def test_search(self):
        """Test full-text search."""
        store = SQLiteConversationStore(ephemeral=True)

        store.add_message("user", "What is machine learning?")
        store.add_message("assistant", "Machine learning is a subset of AI...")
        store.add_message("user", "Tell me about neural networks")
        store.add_message("assistant", "Neural networks are computational models...")

        # Search for "machine learning"
        results = store.search("machine learning", limit=5)
        assert len(results) >= 1
        assert any("machine learning" in r["content"].lower() for r in results)

    def test_metadata(self):
        """Test message metadata storage."""
        store = SQLiteConversationStore(ephemeral=True)

        store.add_message("user", "Test", metadata={"source": "web", "priority": "high"})

        messages = store.get_all_messages()
        assert len(messages) == 1
        assert messages[0]["metadata"]["source"] == "web"
        assert messages[0]["metadata"]["priority"] == "high"

    def test_clear(self):
        """Test clearing all messages."""
        store = SQLiteConversationStore(ephemeral=True)

        store.add_message("user", "Message 1")
        store.add_message("user", "Message 2")

        assert len(store.get_all_messages()) == 2

        store.clear()

        assert len(store.get_all_messages()) == 0

    def test_stats(self):
        """Test getting store statistics."""
        store = SQLiteConversationStore(ephemeral=True)

        store.add_message("user", "Hello")
        store.add_message("assistant", "Hi there")

        stats = store.get_stats()
        assert stats["total_messages"] == 2
        assert stats["storage_type"] == "ephemeral"


class TestChromaVectorStore:
    """Tests for ChromaDB vector storage."""

    def test_ephemeral_store(self):
        """Test in-memory ephemeral storage."""
        store = ChromaVectorStore(ephemeral=True, collection_name="test_ephemeral")

        # Add vectors
        store.add(
            texts=["Hello world", "Python programming"],
            metadatas=[{"type": "greeting"}, {"type": "tech"}],
        )

        # Search
        results = store.search("hello", n_results=2)
        assert len(results) > 0
        assert "hello" in results[0]["document"].lower()

    def test_persistent_store(self):
        """Test persistent storage to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persist_dir = Path(tmpdir) / "chroma"

            # Create store and add vectors
            store1 = ChromaVectorStore(persist_directory=persist_dir, ephemeral=False, collection_name="test_persistent")
            store1.add(texts=["Test document"], ids=["test_1"])

            # Create new store instance (same dir)
            store2 = ChromaVectorStore(persist_directory=persist_dir, ephemeral=False, collection_name="test_persistent")
            results = store2.search("test", n_results=5)

            assert len(results) >= 1

    def test_search_with_filter(self):
        """Test search with metadata filtering."""
        store = ChromaVectorStore(ephemeral=True, collection_name="test_filter")

        store.add(
            texts=["Python is great", "Java is enterprise", "JavaScript runs in browsers"],
            metadatas=[{"lang": "python"}, {"lang": "java"}, {"lang": "js"}],
        )

        # Search with filter
        results = store.search("programming language", n_results=5, filter_metadata={"lang": "python"})

        assert len(results) >= 1
        if results[0]["metadata"]:
            assert results[0]["metadata"]["lang"] == "python"

    def test_clear(self):
        """Test clearing all vectors."""
        store = ChromaVectorStore(ephemeral=True, collection_name="test_clear_unique")

        store.add(texts=["Doc 1", "Doc 2"])

        assert store.get_stats()["total_vectors"] == 2

        store.clear()

        assert store.get_stats()["total_vectors"] == 0

    def test_stats(self):
        """Test getting store statistics."""
        store = ChromaVectorStore(ephemeral=True, collection_name="test_collection")

        store.add(texts=["Vector 1", "Vector 2", "Vector 3"])

        stats = store.get_stats()
        assert stats["total_vectors"] == 3
        assert stats["collection_name"] == "test_collection"
        assert stats["storage_type"] == "ephemeral"


# Note: Pinecone tests are skipped as they require API key and actual cloud instance
# To test Pinecone, add:
#
# @pytest.mark.skipif(not os.getenv("PINECONE_API_KEY"), reason="Pinecone API key not set")
# class TestPineconeVectorStore:
#     def test_pinecone_operations(self):
#         ...
