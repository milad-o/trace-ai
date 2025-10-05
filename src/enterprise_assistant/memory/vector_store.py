"""Vector memory storage with ChromaDB and Pinecone backends."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings

from enterprise_assistant.logger import logger


class VectorMemoryStore(ABC):
    """Abstract base class for vector memory storage."""

    @abstractmethod
    def add(
        self,
        texts: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids: list[str] | None = None,
    ) -> None:
        """Add vectors to memory."""
        pass

    @abstractmethod
    def search(
        self, query: str, n_results: int = 5, filter_metadata: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Search vector memory."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all vectors."""
        pass

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        pass


class ChromaVectorStore(VectorMemoryStore):
    """ChromaDB-based vector memory storage.

    Features:
    - Local or persistent storage
    - Built-in embeddings (no HuggingFace needed)
    - Fast similarity search
    - Metadata filtering
    """

    def __init__(
        self,
        persist_directory: Path | str = "./data/vector_memory",
        collection_name: str = "conversation_memory",
        ephemeral: bool = False,
    ):
        """
        Initialize ChromaDB vector store.

        Args:
            persist_directory: Directory for persistent storage
            collection_name: Name of the collection
            ephemeral: If True, use in-memory storage (non-persistent)
        """
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.ephemeral = ephemeral

        if not ephemeral:
            self.persist_directory.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        if ephemeral:
            self.client = chromadb.Client(Settings(anonymized_telemetry=False))
        else:
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory), settings=Settings(anonymized_telemetry=False)
            )

        # Get or create collection with default embedding function
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        logger.info(
            f"Initialized {'ephemeral' if ephemeral else 'persistent'} ChromaDB vector store "
            f"at {persist_directory if not ephemeral else 'memory'}"
        )

    def add(
        self,
        texts: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids: list[str] | None = None,
    ) -> None:
        """
        Add texts to vector memory.

        Args:
            texts: List of text strings to embed and store
            metadatas: Optional list of metadata dicts
            ids: Optional list of IDs (will generate if not provided)
        """
        if not texts:
            return

        # Generate IDs if not provided
        if ids is None:
            import uuid

            ids = [str(uuid.uuid4()) for _ in texts]

        # Add to collection (ChromaDB will auto-embed)
        self.collection.add(documents=texts, metadatas=metadatas, ids=ids)

        logger.debug(f"Added {len(texts)} vectors to memory")

    def search(
        self, query: str, n_results: int = 5, filter_metadata: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Search vector memory for similar texts.

        Args:
            query: Query text
            n_results: Number of results to return
            filter_metadata: Optional metadata filter

        Returns:
            List of result dicts with id, document, metadata, distance
        """
        where = filter_metadata if filter_metadata else None

        results = self.collection.query(
            query_texts=[query], n_results=n_results, where=where, include=["documents", "metadatas", "distances"]
        )

        # Format results
        formatted_results = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                formatted_results.append(
                    {
                        "id": doc_id,
                        "document": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else None,
                        "distance": results["distances"][0][i] if results.get("distances") else None,
                    }
                )

        logger.debug(f"Found {len(formatted_results)} similar vectors for query")
        return formatted_results

    def clear(self) -> None:
        """Clear all vectors from memory."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name, metadata={"hnsw:space": "cosine"}
        )
        logger.info("Cleared vector memory")

    def get_stats(self) -> dict[str, Any]:
        """Get vector store statistics."""
        count = self.collection.count()
        return {
            "total_vectors": count,
            "collection_name": self.collection_name,
            "storage_type": "ephemeral" if self.ephemeral else "persistent",
            "persist_directory": str(self.persist_directory) if not self.ephemeral else "memory",
        }


class PineconeVectorStore(VectorMemoryStore):
    """Pinecone-based vector memory storage.

    Features:
    - Cloud-hosted vector database
    - Serverless or pod-based
    - Production-grade performance
    - Built-in metadata filtering
    """

    def __init__(
        self,
        api_key: str,
        index_name: str = "conversation-memory",
        dimension: int = 384,
        metric: str = "cosine",
        cloud: str = "aws",
        region: str = "us-east-1",
    ):
        """
        Initialize Pinecone vector store.

        Args:
            api_key: Pinecone API key
            index_name: Name of the Pinecone index
            dimension: Vector dimension (default 384 for all-MiniLM-L6-v2)
            metric: Distance metric (cosine, euclidean, dotproduct)
            cloud: Cloud provider (aws, gcp, azure)
            region: Cloud region
        """
        try:
            from pinecone import Pinecone, ServerlessSpec
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "Pinecone and sentence-transformers required. Install with: "
                "pip install pinecone-client sentence-transformers"
            )

        self.api_key = api_key
        self.index_name = index_name
        self.dimension = dimension

        # Initialize Pinecone
        self.pc = Pinecone(api_key=api_key)

        # Create index if it doesn't exist
        existing_indexes = [idx.name for idx in self.pc.list_indexes()]
        if index_name not in existing_indexes:
            self.pc.create_index(
                name=index_name,
                dimension=dimension,
                metric=metric,
                spec=ServerlessSpec(cloud=cloud, region=region),
            )
            logger.info(f"Created Pinecone index '{index_name}'")

        self.index = self.pc.Index(index_name)

        # Initialize embedding model
        self.embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

        logger.info(f"Initialized Pinecone vector store with index '{index_name}'")

    def add(
        self,
        texts: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids: list[str] | None = None,
    ) -> None:
        """
        Add texts to Pinecone vector memory.

        Args:
            texts: List of text strings to embed and store
            metadatas: Optional list of metadata dicts
            ids: Optional list of IDs (will generate if not provided)
        """
        if not texts:
            return

        # Generate IDs if not provided
        if ids is None:
            import uuid

            ids = [str(uuid.uuid4()) for _ in texts]

        # Generate embeddings
        embeddings = self.embedder.encode(texts).tolist()

        # Prepare vectors for Pinecone
        vectors = []
        for i, (id_, embedding, text) in enumerate(zip(ids, embeddings, texts)):
            metadata = metadatas[i] if metadatas else {}
            metadata["text"] = text  # Store text in metadata
            vectors.append({"id": id_, "values": embedding, "metadata": metadata})

        # Upsert to Pinecone
        self.index.upsert(vectors=vectors)

        logger.debug(f"Added {len(texts)} vectors to Pinecone")

    def search(
        self, query: str, n_results: int = 5, filter_metadata: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Search Pinecone vector memory.

        Args:
            query: Query text
            n_results: Number of results to return
            filter_metadata: Optional metadata filter

        Returns:
            List of result dicts with id, document, metadata, distance
        """
        # Generate query embedding
        query_embedding = self.embedder.encode([query])[0].tolist()

        # Query Pinecone
        results = self.index.query(
            vector=query_embedding, top_k=n_results, filter=filter_metadata, include_metadata=True
        )

        # Format results
        formatted_results = []
        for match in results.matches:
            formatted_results.append(
                {
                    "id": match.id,
                    "document": match.metadata.get("text", ""),
                    "metadata": {k: v for k, v in match.metadata.items() if k != "text"},
                    "distance": match.score,
                }
            )

        logger.debug(f"Found {len(formatted_results)} similar vectors in Pinecone")
        return formatted_results

    def clear(self) -> None:
        """Clear all vectors from Pinecone index."""
        self.index.delete(delete_all=True)
        logger.info("Cleared all vectors from Pinecone")

    def get_stats(self) -> dict[str, Any]:
        """Get Pinecone index statistics."""
        stats = self.index.describe_index_stats()
        return {
            "total_vectors": stats.total_vector_count,
            "index_name": self.index_name,
            "dimension": self.dimension,
            "storage_type": "cloud (Pinecone)",
            "namespaces": list(stats.namespaces.keys()) if stats.namespaces else [],
        }
