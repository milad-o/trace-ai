"""Conversation memory storage using SQLite."""

import json
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

from enterprise_assistant.logger import logger


class ConversationStore(ABC):
    """Abstract base class for conversation memory storage."""

    @abstractmethod
    def add_message(self, role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Add a message to conversation history."""
        pass

    @abstractmethod
    def get_recent_messages(self, limit: int = 30) -> list[dict[str, Any]]:
        """Get recent messages from conversation history."""
        pass

    @abstractmethod
    def get_all_messages(self) -> list[dict[str, Any]]:
        """Get all messages in conversation history."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all conversation history."""
        pass

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search conversation history."""
        pass


class SQLiteConversationStore(ConversationStore):
    """SQLite-based conversation memory storage.

    Features:
    - Persistent storage to disk
    - Full conversation history
    - Search capabilities
    - Metadata support
    - Thread-safe operations
    """

    def __init__(self, db_path: Path | str = "./data/conversation.db", ephemeral: bool = False):
        """
        Initialize SQLite conversation store.

        Args:
            db_path: Path to SQLite database file
            ephemeral: If True, use in-memory database (non-persistent)
        """
        self.ephemeral = ephemeral
        self.db_path = ":memory:" if ephemeral else str(Path(db_path))

        # For ephemeral, keep connection alive
        self._conn = None
        if ephemeral:
            self._conn = sqlite3.connect(":memory:")

        if not ephemeral:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self._init_db()
        logger.info(
            f"Initialized {'ephemeral' if ephemeral else 'persistent'} SQLite conversation store "
            f"at {self.db_path}"
        )

    def _get_conn(self):
        """Get database connection."""
        if self._conn:
            return self._conn
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_conn()
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp DESC)
            """)
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts
                USING fts5(content, content='messages', content_rowid='id')
            """)
            conn.commit()

    def add_message(self, role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        """
        Add a message to conversation history.

        Args:
            role: Message role (system, user, assistant, tool)
            content: Message content
            metadata: Optional metadata dict
        """
        metadata_json = json.dumps(metadata) if metadata else None

        conn = self._get_conn()
        with conn:
            cursor = conn.execute(
                "INSERT INTO messages (role, content, metadata) VALUES (?, ?, ?)",
                (role, content, metadata_json),
            )
            message_id = cursor.lastrowid

            # Update FTS index
            conn.execute(
                "INSERT INTO messages_fts (rowid, content) VALUES (?, ?)", (message_id, content)
            )
            conn.commit()

        logger.debug(f"Added {role} message to conversation store (id={message_id})")

    def get_recent_messages(self, limit: int = 30) -> list[dict[str, Any]]:
        """
        Get recent messages from conversation history.

        Args:
            limit: Number of recent messages to return

        Returns:
            List of message dicts with id, role, content, metadata, timestamp
        """
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            """
            SELECT id, role, content, metadata, timestamp
            FROM messages
            ORDER BY id DESC
            LIMIT ?
        """,
            (limit,),
        )
        messages = [dict(row) for row in cursor.fetchall()]

        # Parse metadata JSON
        for msg in messages:
            if msg["metadata"]:
                msg["metadata"] = json.loads(msg["metadata"])

        # Return in chronological order (oldest first)
        messages.reverse()

        logger.debug(f"Retrieved {len(messages)} recent messages")
        return messages

    def get_all_messages(self) -> list[dict[str, Any]]:
        """
        Get all messages in conversation history.

        Returns:
            List of all message dicts
        """
        conn = self._get_conn()
        with conn as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT id, role, content, metadata, timestamp FROM messages ORDER BY id ASC"
            )
            messages = [dict(row) for row in cursor.fetchall()]

        # Parse metadata JSON
        for msg in messages:
            if msg["metadata"]:
                msg["metadata"] = json.loads(msg["metadata"])

        logger.debug(f"Retrieved {len(messages)} total messages")
        return messages

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Search conversation history using full-text search.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching message dicts, ranked by relevance
        """
        conn = self._get_conn()
        with conn as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT m.id, m.role, m.content, m.metadata, m.timestamp,
                       bm25(messages_fts) as rank
                FROM messages_fts
                JOIN messages m ON messages_fts.rowid = m.id
                WHERE messages_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """,
                (query, limit),
            )
            messages = [dict(row) for row in cursor.fetchall()]

        # Parse metadata JSON
        for msg in messages:
            if msg["metadata"]:
                msg["metadata"] = json.loads(msg["metadata"])

        logger.debug(f"Found {len(messages)} messages matching '{query}'")
        return messages

    def clear(self) -> None:
        """Clear all conversation history."""
        conn = self._get_conn()
        with conn as conn:
            conn.execute("DELETE FROM messages")
            conn.execute("DELETE FROM messages_fts")
            conn.commit()

        logger.info("Cleared all conversation history")

    def get_stats(self) -> dict[str, Any]:
        """Get conversation store statistics."""
        conn = self._get_conn()
        with conn as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM messages")
            total_messages = cursor.fetchone()[0]

            cursor = conn.execute(
                "SELECT COUNT(DISTINCT role) as role_count FROM messages"
            )
            role_count = cursor.fetchone()[0]

            cursor = conn.execute(
                "SELECT MIN(timestamp) as first, MAX(timestamp) as last FROM messages"
            )
            row = cursor.fetchone()
            first_timestamp = row[0]
            last_timestamp = row[1]

        return {
            "total_messages": total_messages,
            "role_count": role_count,
            "first_message": first_timestamp,
            "last_message": last_timestamp,
            "storage_type": "ephemeral" if self.ephemeral else "persistent",
            "db_path": self.db_path,
        }
