"""TraceAI - Async-first AI Agent for Enterprise Data Analysis.

This module provides the main TraceAI agent with:
- Concurrent document parsing (10x faster)
- Async LLM calls with streaming
- Parallel vector store operations
- Background graph building
- LangGraph + DeepAgents integration
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

# Import existing modular components
from traceai.graph.builder import build_graph_from_documents
from traceai.graph.queries import GraphQueries
from traceai.graph.schema import EdgeType, NodeType
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


class TraceAI:
    """
    TraceAI - Async-first intelligent agent for enterprise data analysis.

    Provides concurrent processing capabilities for:
    - Document parsing (10x faster for large codebases)
    - LLM queries (parallel execution)
    - Vector store operations (background indexing)
    - Streaming responses
    - Multi-graph support (lineage, schema, execution)
    """

    def __init__(
        self,
        model_provider: str | None = "anthropic",
        model_name: str | None = None,
        llm: Any | None = None,
        embeddings: Any | None = None,
        persist_dir: Path | str = "./examples/outputs/data",
        enable_memory: bool = True,
        enable_audit: bool = True,
        enable_progress: bool = True,
        enable_filesystem: bool = False,
        enable_subagents: bool = False,
        max_conversation_messages: int = 30,
        max_concurrent_parsers: int = 10,
        recursion_limit: int = 35,
    ):
        """
    Initialize the async TraceAI agent.

        Args:
            model_provider: "anthropic" or "openai"
            model_name: Model name to use
            persist_dir: Directory for persisting data
            enable_memory: Enable conversation memory middleware
            enable_audit: Enable audit logging middleware
            enable_progress: Enable progress tracking middleware
            enable_filesystem: Enable DeepAgents filesystem tools (ls, read_file, write_file, edit_file)
            max_conversation_messages: Max messages to keep in memory
            max_concurrent_parsers: Max concurrent file parsing operations
            recursion_limit: Maximum LangGraph recursion depth (default 35 to prevent infinite loops)
        """
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # Store configuration
        self.enable_memory = enable_memory
        self.enable_audit = enable_audit
        self.enable_progress = enable_progress
        self.enable_filesystem = enable_filesystem
        self.enable_subagents = enable_subagents
        self.max_conversation_messages = max_conversation_messages
        self.max_concurrent_parsers = max_concurrent_parsers
        self.recursion_limit = recursion_limit

        # Initialize components (using existing modular architecture)
        self.graph: nx.DiGraph | None = None
        self.parsed_documents: list[Any] = []
        
        # Initialize embeddings and vector store
        self.embeddings = embeddings or HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
        )
        self.vector_store = Chroma(
            persist_directory=str(self.persist_dir / "chroma"),
            embedding_function=self.embeddings,
            collection_name="traceai_documents",
        )

        # Initialize LLM
        self.model_provider = model_provider
        self.model_name = model_name
        self.llm = llm

        # Normalize "provider:model" semantic strings
        provider = model_provider or ""
        normalized_name = model_name
        if provider and ":" in provider:
            provider, inferred_model = provider.split(":", 1)
            if not normalized_name:
                normalized_name = inferred_model or None

        # Setup LLM if one was not directly provided
        if self.llm is None:
            api_key = None
            if provider == "anthropic":
                api_key = os.getenv("ANTHROPIC_API_KEY")
                default_model = normalized_name or "claude-3-5-sonnet-20241022"
                if api_key:
                    self.llm = ChatAnthropic(model=default_model, temperature=0, anthropic_api_key=api_key)
                self.model_name = default_model
                self.model_provider = provider
            elif provider == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
                default_model = normalized_name or "gpt-4o-mini"
                if api_key:
                    self.llm = ChatOpenAI(model=default_model, temperature=0, openai_api_key=api_key)
                self.model_name = default_model
                self.model_provider = provider
            elif provider in {"", None}:
                self.model_provider = None
                self.model_name = normalized_name
            else:
                raise ValueError(f"Unknown model provider: {provider}")
        else:
            # When an LLM instance is supplied, best effort to derive provider/model metadata
            self.model_provider = provider or getattr(self.llm, "__module__", "custom").split(".")[0]
            self.model_name = normalized_name or getattr(self.llm, "model_name", None)

        # Agent created after loading documents
        self.agent = None

        if self.llm:
            logger.info(f"Initialized TraceAI with {model_provider}/{self.model_name}")
        else:
            logger.warning(f"No API key found for {model_provider}. TraceAI will work in graph-only mode.")

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
        
        # Collect all files
        files = []
        for pat in patterns:
            files.extend(directory.glob(pat))
        files = list(set(files))
        
        if not files:
            logger.warning(f"No files found matching patterns {patterns} in {directory}")
            return
        
        logger.info(f"Loading {len(files)} documents from {directory}")
        
        # Parse files concurrently using existing parsers module
        parsed_docs = await parse_files_concurrently(
            files,
            parser_registry,
            max_concurrent=self.max_concurrent_parsers
        )
        
        if not parsed_docs:
            logger.warning("No documents parsed successfully")
            return
        
        self.parsed_documents.extend(parsed_docs)
        logger.info(f"Parsed {len(parsed_docs)} documents")
        
        # Build knowledge graph using existing graph.builder module
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
        
        # Index documents in vector store
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
        """Add a single parsed document to vector store."""
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
        
        # Add to vector store
        if texts:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.vector_store.add_texts,
                texts,
                metadatas
            )
            logger.info(f"Indexed {len(texts)} items from '{parsed_doc.metadata.name}'")

    async def _create_agent_async(self) -> None:
        """Create the deep agent with all tools (async version)."""
        if not self.graph:
            raise ValueError("Knowledge graph not built. Load documents first.")

        # Create all tools using existing tools module
        graph_tools = create_graph_tools(self.graph)
        viz_tool = create_graph_visualization_tool(self.graph)
        
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
        
        all_tools = graph_tools + [viz_tool, semantic_tool]

        # Create middleware using existing middleware classes
        middlewares = []
        if self.enable_memory:
            middlewares.append(
                ConversationMemoryMiddleware(
                    max_messages=self.max_conversation_messages,
                    db_path=self.persist_dir / "conversation.db"
                )
            )
        if self.enable_audit:
            middlewares.append(AuditMiddleware())
        if self.enable_progress:
            middlewares.append(ProgressTrackingMiddleware())

        # Build instructions dynamically based on enabled features
        base_instructions = (
            "You are TraceAI, an expert AI assistant for analyzing ETL pipelines, data lineage, "
            "and enterprise transformations. You have access to a knowledge graph and semantic search "
            "to help answer questions about data flows, dependencies, and impact analysis.\n\n"
        )

        planning_instructions = (
            "PLANNING-FIRST WORKFLOW (for complex queries):\n"
            "For multi-step queries requiring multiple analyses, USE write_todos to create a plan:\n"
            "1. Call write_todos with 3-5 clear steps, each with title, description, and 'not-started' status\n"
            "2. Execute steps one at a time, referencing your plan (e.g., 'Executing step 1: parsing files...')\n"
            "3. After each step, update todos with status='completed' for that step\n"
            "4. Provide progress updates: 'Working on step 2 of 4: analyzing lineage...'\n\n"
            "Examples of when to use write_todos:\n"
            "- 'Analyze CustomerETL and generate a report' (multi-step: parse → analyze → generate)\n"
            "- 'Find all dependencies and trace their lineage' (multi-step: find → trace → summarize)\n"
            "- 'Compare two packages and identify differences' (multi-step: load → compare → report)\n\n"
        )

        filesystem_instructions = ""
        if self.enable_filesystem:
            filesystem_instructions = (
                "FILESYSTEM TOOLS (enabled):\n"
                "You have access to filesystem tools for working with generated files:\n"
                "- ls(path): List files and directories\n"
                "- read_file(path): Read file contents (use this to verify generated code)\n"
                "- write_file(path, content): Create new files\n"
                "- edit_file(path, old_string, new_string): Edit existing files\n\n"
                "Use cases:\n"
                "- After generating code: Use read_file to show the user what was created\n"
                "- User asks 'what files exist': Use ls to list output directories\n"
                "- User asks 'show me the generated Python code': Use read_file on the file\n"
                "- Create configuration files dynamically with write_file\n\n"
            )

        execution_instructions = (
            "CRITICAL EXECUTION GUIDELINES:\n"
            "1. SIMPLE QUERIES (single action): Skip planning, directly use 1-2 tools and respond\n"
            "   - 'List packages' → package_catalog → respond\n"
            "   - 'Find CustomerETL' → semantic_search → respond\n"
            "   - 'Trace lineage of Orders' → trace_lineage → respond\n\n"
            "2. COMPLEX QUERIES (multiple steps): Use write_todos FIRST, then execute plan\n"
            "   - Creates visibility for user (they see your plan)\n"
            "   - Prevents infinite loops (clear stopping point)\n"
            "   - Better error recovery (can restart from failed step)\n\n"
            "3. MAXIMUM 3 TOOL CALLS PER STEP: Each todo step can call at most 3 tools.\n\n"
            "4. STOP WHEN PLAN COMPLETE: Once all todos are 'completed', respond with final summary.\n\n"
            "5. PREFER DIRECT TOOLS:\n"
            "   - For 'find components': Use semantic_search ONCE\n"
            "   - For 'impact analysis': Use analyze_impact ONCE with entity name\n"
            "   - For 'lineage': Use trace_lineage ONCE with table name\n"
            "   - For 'list packages': Use package_catalog ONCE\n"
            "   - For 'dependencies': Use search_dependencies ONCE\n\n"
            "6. NO UNNECESSARY EXPLORATION: Trust first result, don't verify or re-check.\n\n"
            "TERMINATION RULES:\n"
            "- Simple query: After 1-2 tool calls, respond immediately\n"
            "- Complex query: After completing all todos, respond with summary\n"
            "- If tool returns useful data: Use it and move to next step (or respond if done)\n\n"
            "Be efficient, decisive, and planning-oriented for complex tasks."
        )

        full_instructions = base_instructions + planning_instructions + filesystem_instructions + execution_instructions

        # Create agent using deepagents
        self.agent = create_deep_agent(
            model=self.llm,
            tools=all_tools,
            instructions=full_instructions,
            middleware=middlewares if middlewares else None,
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
        if not self.graph:
            raise ValueError("No knowledge graph available. Load documents first.")

        if not self.agent:
            if self.llm is None:
                return await self._offline_answer(question)
            raise ValueError("Agent not initialized. Load documents first.")

        # Use ainvoke for async execution
        try:
            response = await self.agent.ainvoke(
                {"messages": [{"role": "user", "content": question}]},
                config={"recursion_limit": self.recursion_limit},
            )
        except Exception as e:
            if "recursion" in str(e).lower():
                return (
                    "I apologize, but I couldn't complete this analysis within the allowed steps. "
                    "The query appears to be too complex. Please try:\n"
                    "1. Breaking it into smaller, more specific questions\n"
                    "2. Being more specific about what you need (e.g., a single package name)\n"
                    "3. Asking for one analysis at a time"
                )
            raise

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
        if not self.graph:
            raise ValueError("No knowledge graph available. Load documents first.")

        if not self.agent:
            if self.llm is None:
                yield await self._offline_answer(question)
                return
            raise ValueError("Agent not initialized. Load documents first.")

        # Use astream for streaming
        try:
            async for chunk in self.agent.astream(
                {"messages": [{"role": "user", "content": question}]},
                config={"recursion_limit": self.recursion_limit},
                stream_mode="values",
            ):
                # Extract the latest message content
                if isinstance(chunk, dict) and "messages" in chunk:
                    messages = chunk["messages"]
                    if messages and len(messages) > 0:
                        last_msg = messages[-1]
                        if hasattr(last_msg, 'content') and last_msg.content:
                            yield last_msg.content
        except Exception as e:
            if "recursion" in str(e).lower():
                yield (
                    "I apologize, but I couldn't complete this analysis within the allowed steps. "
                    "The query appears to be too complex. Please try:\n"
                    "1. Breaking it into smaller, more specific questions\n"
                    "2. Being more specific about what you need (e.g., a single package name)\n"
                    "3. Asking for one analysis at a time"
                )
            else:
                raise

    def get_graph_stats(self) -> dict[str, Any]:
        """Get knowledge graph statistics."""
        if not self.graph or self.graph.number_of_nodes() == 0:
            stats: dict[str, Any] = {
                "total_nodes": 0,
                "total_edges": 0,
                "is_directed": True,
                "is_connected": False,
            }

            for node_type in NodeType:
                stats[f"{node_type.value.lower()}_count"] = 0

            for edge_type in EdgeType:
                stats[f"{edge_type.value.lower()}_count"] = 0

            return stats

        queries = GraphQueries(self.graph)
        return queries.get_graph_stats()

    async def _offline_answer(self, question: str) -> str:
        """Generate a deterministic fallback answer when no LLM is configured."""
        question_lower = question.lower()
        queries = GraphQueries(self.graph)
        stats = queries.get_graph_stats()
        packages = queries.find_nodes_by_type(NodeType.PACKAGE)
        package_names = [data.get("name") for _, data in packages if data.get("name")]

        if "list" in question_lower or "package" in question_lower:
            if not package_names:
                return "No packages were loaded into the knowledge graph."
            limited_names = ", ".join(sorted(package_names)[:10])
            count = len(package_names)
            if count > 10:
                return (
                    f"Offline mode: Loaded {count} packages. First 10: {limited_names}."
                )
            return f"Offline mode: Loaded packages -> {limited_names}."

        if "stat" in question_lower or "overview" in question_lower or "summary" in question_lower:
            return (
                "Offline mode summary: "
                f"{stats['total_nodes']} nodes, {stats['total_edges']} edges, "
                f"packages={len(package_names)}."
            )

        if package_names:
            primary = sorted(package_names)[0]
            return (
                "Offline mode: TraceAI is running without an LLM. "
                f"The knowledge graph includes {len(package_names)} packages such as '{primary}'."
            )

        return (
            "Offline mode: TraceAI is running without an LLM and no packages were parsed. "
            "Load supported documents to build a knowledge graph."
        )
