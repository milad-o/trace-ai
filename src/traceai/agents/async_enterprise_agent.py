"""Async Enterprise Analysis Agent for concurrent document processing.

This module provides an async version of EnterpriseAgent that supports:
- Concurrent document parsing
- Async LLM calls with streaming
- Parallel vector store operations
- Background graph building
"""

import asyncio
import os
from pathlib import Path
from typing import Any, AsyncIterator

import networkx as nx
from deepagents import create_deep_agent
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()

# Fix HuggingFace tokenizer parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from traceai.graph.builder import build_graph_from_documents
from traceai.graph.queries import GraphQueries
from traceai.logger import logger
from traceai.parsers import parser_registry
from traceai.parsers.async_base import parse_files_concurrently
from traceai.tools import create_graph_tools, create_graph_visualization_tool
from traceai.agents.middlewares import (
    ConversationMemoryMiddleware,
    AuditMiddleware,
    ProgressTrackingMiddleware,
)

# LangChain vector store and embeddings
try:
    from langchain_chroma import Chroma
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.vectorstores import Chroma
    from langchain_community.embeddings import HuggingFaceEmbeddings


class AsyncEnterpriseAgent:
    """
    Async intelligent agent for enterprise document analysis.

    Provides concurrent processing capabilities for:
    - Document parsing (10x faster for large codebases)
    - LLM queries (parallel execution)
    - Vector store operations (background indexing)
    - Streaming responses
    """

    def __init__(
        self,
        model_provider: str = "anthropic",
        model_name: str | None = None,
        persist_dir: Path | str = "./examples/outputs/data",
        enable_memory: bool = True,
        enable_audit: bool = True,
        enable_progress: bool = True,
        max_conversation_messages: int = 30,
        max_concurrent_parsers: int = 10,
    ):
        """
        Initialize the async enterprise agent.

        Args:
            model_provider: "anthropic" or "openai"
            model_name: Model name to use
            persist_dir: Directory for persisting data
            enable_memory: Enable conversation memory middleware
            enable_audit: Enable audit logging middleware
            enable_progress: Enable progress tracking middleware
            max_conversation_messages: Max messages to keep in memory
            max_concurrent_parsers: Max concurrent file parsing operations
        """
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.graph: nx.DiGraph | None = None
        self.max_concurrent_parsers = max_concurrent_parsers

        # Initialize embeddings and vector store
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
        )
        self.vector_store = Chroma(
            persist_directory=str(self.persist_dir / "chroma"),
            embedding_function=embeddings,
            collection_name="enterprise_documents",
        )
        self.parsed_documents: list[Any] = []

        # Middleware configuration
        self.enable_memory = enable_memory
        self.enable_audit = enable_audit
        self.enable_progress = enable_progress
        self.max_conversation_messages = max_conversation_messages

        # Initialize LLM
        self.model_provider = model_provider
        self.model_name = model_name
        self.llm = None

        # Setup LLM
        api_key = None
        if model_provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            default_model = model_name or "claude-3-5-sonnet-20241022"
            if api_key:
                self.llm = ChatAnthropic(model=default_model, temperature=0, anthropic_api_key=api_key)
                self.model_name = default_model
            else:
                self.model_name = default_model
        elif model_provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            default_model = model_name or "gpt-4o-mini"
            if api_key:
                self.llm = ChatOpenAI(model=default_model, temperature=0, openai_api_key=api_key)
                self.model_name = default_model
            else:
                self.model_name = default_model
        else:
            raise ValueError(f"Unknown model provider: {model_provider}")

        # Agent created after loading documents
        self.agent = None

        if self.llm:
            logger.info(f"Initialized AsyncEnterpriseAgent with {model_provider}/{self.model_name}")
        else:
            logger.warning(f"No API key found for {model_provider}. Agent will work in graph-only mode.")

    async def load_documents(
        self,
        directory: Path | str,
        pattern: str | list[str] = "**/*.dtsx"
    ) -> None:
        """
        Load and parse documents concurrently from a directory.

        Args:
            directory: Directory containing documents
            pattern: Glob pattern(s) for files to load
        """
        directory = Path(directory)

        # Support multiple patterns
        patterns = [pattern] if isinstance(pattern, str) else pattern

        # Collect all files matching any pattern
        files = []
        for pat in patterns:
            files.extend(directory.glob(pat))

        # Remove duplicates
        files = list(set(files))

        if not files:
            logger.warning(f"No files found matching patterns {patterns} in {directory}")
            return

        logger.info(f"Loading {len(files)} documents from {directory} (async mode)")

        # Initialize parsed_documents if needed
        if not hasattr(self, 'parsed_documents') or self.parsed_documents is None:
            self.parsed_documents = []

        # Parse documents concurrently
        parsed_docs = await parse_files_concurrently(
            files,
            parser_registry,
            max_concurrent=self.max_concurrent_parsers
        )

        self.parsed_documents.extend(parsed_docs)
        logger.info(f"Parsed {len(parsed_docs)} documents concurrently")

        # Build knowledge graph (CPU-bound, run in executor)
        if self.parsed_documents:
            loop = asyncio.get_event_loop()
            self.graph = await loop.run_in_executor(
                None,
                build_graph_from_documents,
                self.parsed_documents
            )
            logger.info(
                f"Built knowledge graph: {self.graph.number_of_nodes()} nodes, "
                f"{self.graph.number_of_edges()} edges"
            )

            # Index in vector store concurrently
            await self._add_documents_to_vectorstore_async(parsed_docs)

            # Create agent with tools (only if LLM available)
            if self.llm:
                await self._create_agent_async()
            else:
                logger.info("Skipping agent creation (no LLM available).")

    async def _add_documents_to_vectorstore_async(self, parsed_docs: list[Any]) -> None:
        """Add parsed documents to vector store concurrently."""
        tasks = [self._add_parsed_document_to_vectorstore(doc) for doc in parsed_docs]
        await asyncio.gather(*tasks)

    async def _add_parsed_document_to_vectorstore(self, parsed_doc) -> None:
        """Add a single parsed document to vector store (async)."""
        texts = []
        metadatas = []

        # Add document metadata
        doc_text = f"{parsed_doc.metadata.name}: {parsed_doc.metadata.description or 'No description'}"
        texts.append(doc_text)
        metadatas.append({
            "type": "document",
            "doc_id": parsed_doc.metadata.document_id,
            "name": parsed_doc.metadata.name,
            "doc_type": str(parsed_doc.metadata.document_type),
        })

        # Add components
        for component in parsed_doc.components:
            if component.source_code:
                comp_text = f"{component.name}: {component.description or ''}\n{component.source_code}"
                texts.append(comp_text)
                metadatas.append({
                    "type": "component",
                    "doc_id": parsed_doc.metadata.document_id,
                    "component_id": component.component_id,
                    "name": component.name,
                    "component_type": component.component_type,
                })

        # Add data sources
        for source in parsed_doc.data_sources:
            source_text = f"{source.name}: {source.description or ''} ({source.source_type})"
            texts.append(source_text)
            metadatas.append({
                "type": "data_source",
                "doc_id": parsed_doc.metadata.document_id,
                "name": source.name,
                "source_type": source.source_type,
            })

        # Add to vector store (run in executor as it's not async)
        if texts:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.vector_store.add_texts,
                texts,
                metadatas
            )
            logger.info(f"Added {len(texts)} items from '{parsed_doc.metadata.name}' to vector store")

    async def _create_agent_async(self) -> None:
        """Create the deep agent with all tools (async version)."""
        if not self.graph:
            raise ValueError("No knowledge graph available. Load documents first.")

        # Create graph tools
        graph_tools = create_graph_tools(self.graph)

        # Create semantic search tool
        def semantic_search(query: str, max_results: int = 5) -> str:
            """Search for documents and components semantically similar to the query."""
            results = self.vector_store.similarity_search(query, k=max_results)
            if not results:
                return "No relevant documents found."

            output = []
            for i, doc in enumerate(results, 1):
                output.append(f"{i}. {doc.page_content}")
                if doc.metadata:
                    output.append(f"   Metadata: {doc.metadata}")

            return "\n".join(output)

        from langchain_core.tools import StructuredTool

        semantic_tool = StructuredTool.from_function(
            func=semantic_search,
            name="semantic_search",
            description="Search for documents, components, and data sources using semantic similarity. "
            "Use this to find relevant code, transformations, or data flows based on meaning."
        )

        # Combine all tools
        all_tools = graph_tools + [semantic_tool] + [create_graph_visualization_tool(self.graph)]

        # Create middlewares
        middlewares = []
        if self.enable_memory:
            middlewares.append(
                ConversationMemoryMiddleware(max_messages=self.max_conversation_messages)
            )
        if self.enable_audit:
            middlewares.append(AuditMiddleware())
        if self.enable_progress:
            middlewares.append(ProgressTrackingMiddleware())

        # Create agent using deepagents
        self.agent = create_deep_agent(
            llm=self.llm,
            tools=all_tools,
            system_message=(
                "You are TraceAI, an expert AI assistant for analyzing ETL pipelines, data lineage, "
                "and enterprise transformations. You have access to a knowledge graph and semantic search "
                "to help answer questions about data flows, dependencies, and impact analysis.\n\n"
                "Always use the available tools to provide accurate, data-driven answers."
            ),
            middlewares=middlewares if middlewares else None,
        )

        logger.info(f"Created async agent with {len(all_tools)} tools")

    async def query(self, question: str) -> str:
        """
        Query the agent asynchronously.

        Args:
            question: User question

        Returns:
            Agent's response
        """
        if not self.agent:
            raise ValueError("Agent not initialized. Load documents first.")

        # Use ainvoke for async execution
        response = await self.agent.ainvoke({"messages": [{"role": "user", "content": question}]})

        # Extract final response
        if isinstance(response, dict) and "messages" in response:
            return response["messages"][-1].content

        return str(response)

    async def query_stream(self, question: str) -> AsyncIterator[str]:
        """
        Query the agent with streaming response.

        Args:
            question: User question

        Yields:
            Chunks of the response as they arrive
        """
        if not self.agent:
            raise ValueError("Agent not initialized. Load documents first.")

        # Use astream for streaming
        async for chunk in self.agent.astream({"messages": [{"role": "user", "content": question}]}):
            if isinstance(chunk, dict) and "messages" in chunk:
                for msg in chunk["messages"]:
                    if hasattr(msg, 'content') and msg.content:
                        yield msg.content
            elif isinstance(chunk, str):
                yield chunk

    def get_graph_stats(self) -> dict[str, Any]:
        """Get knowledge graph statistics."""
        if not self.graph:
            return {"error": "No graph available"}

        queries = GraphQueries(self.graph)
        return queries.get_graph_stats()
