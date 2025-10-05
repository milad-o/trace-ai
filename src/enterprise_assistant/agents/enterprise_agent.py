"""Enterprise Analysis Agent using deepagents and LangChain.

This module creates an intelligent agent that can analyze enterprise documents,
answer questions, and provide insights using the knowledge graph and vector store.
"""

import os
from pathlib import Path
from typing import Any

import networkx as nx
from deepagents import create_deep_agent
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()

# Fix HuggingFace tokenizer parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from enterprise_assistant.graph.builder import build_graph_from_documents
from enterprise_assistant.graph.queries import GraphQueries
from enterprise_assistant.logger import logger
from enterprise_assistant.parsers import parser_registry
from enterprise_assistant.tools import create_graph_tools, create_graph_visualization_tool
from enterprise_assistant.agents.middlewares import (
    ConversationMemoryMiddleware,
    AuditMiddleware,
    ProgressTrackingMiddleware,
)

# LangChain vector store and embeddings (using new packages to avoid deprecation warnings)
try:
    from langchain_chroma import Chroma
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    # Fallback to community packages if new ones not installed
    from langchain_community.vectorstores import Chroma
    from langchain_community.embeddings import HuggingFaceEmbeddings


class EnterpriseAgent:
    """
    Intelligent agent for enterprise document analysis.

    Combines knowledge graph, vector search, and LLM reasoning to provide
    deep insights into enterprise documents.
    """

    def __init__(
        self,
        model_provider: str = "anthropic",
        model_name: str | None = None,
        persist_dir: Path | str = "./data",
        enable_memory: bool = True,
        enable_audit: bool = True,
        enable_progress: bool = True,
        max_conversation_messages: int = 30,
    ):
        """
        Initialize the enterprise agent.

        Args:
            model_provider: "anthropic" or "openai"
            model_name: Model name to use
            persist_dir: Directory for persisting data
            enable_memory: Enable conversation memory middleware (default: True)
            enable_audit: Enable audit logging middleware (default: True)
            enable_progress: Enable progress tracking middleware (default: True)
            max_conversation_messages: Max messages to keep in memory (default: 30)
        """
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.graph: nx.DiGraph | None = None

        # Initialize LangChain Chroma vector store with embeddings
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

        # Initialize LLM with default models if not specified
        # Allow None for graph-only operations (no AI needed)
        self.model_provider = model_provider
        self.model_name = model_name
        self.llm = None

        # Only initialize LLM if API key is available
        api_key = None
        if model_provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            default_model = model_name or "claude-3-5-sonnet-20241022"
            if api_key:
                self.llm = ChatAnthropic(model=default_model, temperature=0, anthropic_api_key=api_key)
                self.model_name = default_model
            else:
                self.model_name = default_model  # Store even if no key
        elif model_provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            default_model = model_name or "gpt-4o-mini"
            if api_key:
                self.llm = ChatOpenAI(model=default_model, temperature=0, openai_api_key=api_key)
                self.model_name = default_model
            else:
                self.model_name = default_model  # Store even if no key
        else:
            raise ValueError(f"Unknown model provider: {model_provider}")

        # Agent will be created after loading documents (only if LLM available)
        self.agent = None

        if self.llm:
            logger.info(f"Initialized EnterpriseAgent with {model_provider}/{self.model_name}")
        else:
            logger.warning(f"No API key found for {model_provider}. Agent will work in graph-only mode (no AI capabilities).")

    def load_documents(self, directory: Path | str, pattern: str | list[str] = "**/*.dtsx") -> None:
        """
        Load and parse documents from a directory.

        Args:
            directory: Directory containing documents
            pattern: Glob pattern(s) for files to load (string or list of strings)
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

        logger.info(f"Loading {len(files)} documents from {directory}")

        # Parse documents (accumulate, don't reset)
        if not hasattr(self, 'parsed_documents') or self.parsed_documents is None:
            self.parsed_documents = []

        for file_path in files:
            # Get appropriate parser
            parser = parser_registry.get_parser_for_file(file_path)
            if parser:
                try:
                    parsed = parser.parse(file_path)
                    self.parsed_documents.append(parsed)
                    logger.info(f"Parsed {file_path.name}")
                except Exception as e:
                    logger.error(f"Failed to parse {file_path.name}: {e}")
            else:
                logger.warning(f"No parser found for {file_path.name}")

        # Build knowledge graph
        if self.parsed_documents:
            self.graph = build_graph_from_documents(self.parsed_documents)
            logger.info(
                f"Built knowledge graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges"
            )

            # Index in vector store (convert parsed docs to LangChain format)
            for doc in self.parsed_documents:
                self._add_parsed_document_to_vectorstore(doc)

            # Create agent with tools (only if LLM is available)
            if self.llm:
                self._create_agent()
            else:
                logger.info("Skipping agent creation (no LLM available). Use graph/vector store methods directly.")

    def _add_parsed_document_to_vectorstore(self, parsed_doc) -> None:
        """Add a parsed document to LangChain Chroma vector store."""
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

        # Add components with source code
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

        # Add to vector store (LangChain handles embeddings automatically)
        if texts:
            self.vector_store.add_texts(texts=texts, metadatas=metadatas)
            logger.info(f"Added {len(texts)} items from '{parsed_doc.metadata.name}' to vector store")

    def _create_agent(self) -> None:
        """Create the deep agent with all tools."""
        if not self.graph:
            raise ValueError("No knowledge graph available. Load documents first.")

        # Create graph tools
        graph_tools = create_graph_tools(self.graph)

        # Create semantic search tool (using LangChain Chroma)
        def semantic_search(query: str, max_results: int = 5) -> str:
            """
            Search for documents and components semantically similar to the query.

            Use this when you need to find relevant documents or code based on
            description or functionality rather than exact names.

            Args:
                query: What to search for (e.g., "customer data processing")
                max_results: Maximum results to return (default: 5)

            Returns:
                Formatted search results with relevance scores
            """
            # Use LangChain's similarity_search_with_score
            results = self.vector_store.similarity_search_with_score(query, k=max_results)
            if not results:
                return f"No results found for query: '{query}'"

            lines = [f"Found {len(results)} results for '{query}':\n"]
            for i, (doc, score) in enumerate(results, 1):
                metadata = doc.metadata
                # LangChain Chroma returns similarity scores (higher = more similar)
                similarity = 1 - score if score else "N/A"

                lines.append(f"{i}. {metadata.get('name', 'Unknown')}")
                lines.append(f"   Type: {metadata.get('type', 'unknown')}")
                lines.append(f"   Similarity: {similarity:.2%}" if isinstance(similarity, float) else "   Similarity: N/A")
                lines.append(f"   Content: {doc.page_content[:150]}...")
                lines.append("")

            return "\n".join(lines)

        # Create graph statistics tool
        def get_graph_statistics() -> str:
            """
            Get statistics about the knowledge graph.

            Returns summary of nodes, edges, and graph structure.
            """
            if not self.graph:
                return "No knowledge graph available"

            queries = GraphQueries(self.graph)
            stats = queries.get_graph_stats()

            lines = ["Knowledge Graph Statistics:", ""]
            lines.append(f"Total Nodes: {stats.get('total_nodes', 0)}")
            lines.append(f"Total Edges: {stats.get('total_edges', 0)}")
            lines.append("")
            lines.append("Node Types:")
            for key, value in stats.items():
                if key.endswith("_nodes") and value > 0:
                    node_type = key.replace("_nodes", "").title()
                    lines.append(f"  {node_type}: {value}")

            return "\n".join(lines)

        # Create visualization tool
        visualization_tool = create_graph_visualization_tool(self.graph)

        # Combine all tools
        all_tools = graph_tools + [semantic_search, get_graph_statistics, visualization_tool]

        # Configure middlewares
        middlewares = []
        if self.enable_memory:
            middlewares.append(ConversationMemoryMiddleware(max_messages=self.max_conversation_messages))
            logger.info(f"Enabled conversation memory (max {self.max_conversation_messages} messages)")

        if self.enable_audit:
            middlewares.append(AuditMiddleware())
            logger.info("Enabled audit logging")

        if self.enable_progress:
            middlewares.append(ProgressTrackingMiddleware())
            logger.info("Enabled progress tracking")

        # Create deep agent
        self.agent = create_deep_agent(
            model=self.llm,
            tools=all_tools,
            middleware=middlewares if middlewares else None,
            instructions="""You are an expert enterprise document analyst with deep knowledge of:
- SSIS packages and ETL workflows
- Data lineage and dependency analysis
- Impact assessment of system changes
- Database schemas and data flows

Your capabilities:
1. **Graph Analysis**: Query structure, relationships, and dependencies using graph_query, lineage_tracer, impact_analysis, dependency_search
2. **Semantic Search**: Find relevant documents using semantic_search
3. **Visualization**: Create visual diagrams with create_graph_visualization (SVG/PNG/PDF)
4. **Statistics**: Get graph metrics with get_graph_statistics
5. **Planning**: For complex multi-step tasks, use write_todos to create a plan before executing

## Planning for Complex Tasks
For queries requiring multiple steps (e.g., "analyze all packages and create visualizations"):
1. First use write_todos to break down the task into steps
2. Show the plan to the user
3. Execute each step systematically
4. Update progress as you complete each todo

Example:
User: "Create visualizations for each package"
You: [Call write_todos with: ["Find all packages", "Create visualization for CustomerETL", "Create visualization for SalesAggregation"]]
Then: Execute each step and report progress

## Visualization Guidelines
When asked to visualize:
- Use create_graph_visualization with appropriate layout (hierarchical for packages, spring for relationships)
- For package structure: use hierarchical layout to show containment
- For data flow: use spring layout to show connections
- Always specify the package_name for focused views
- SVG format is best for scalability, PNG for compatibility

When answering questions:
- Use appropriate tools to gather accurate information
- Provide specific examples from actual documents
- Explain dependencies and potential impacts clearly
- Reference actual component names, tables, and connections
- For complex queries, plan first with write_todos
- Offer to create visualizations when helpful

Always verify information using tools before making statements.""",
        )

        logger.info(f"Created deep agent with {len(all_tools)} tools")

    def analyze(self, query: str) -> str:
        """
        Analyze documents and answer a query using AI.

        Args:
            query: User question or analysis request

        Returns:
            Agent's response

        Note:
            Requires API key. For graph-only operations without AI,
            use the graph and vector_store attributes directly.
        """
        if not self.llm:
            return "Error: No LLM available. Set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable to use AI features."

        if not self.agent:
            return "Error: Agent not initialized. Load documents first using load_documents()"

        try:
            # Invoke the agent with increased recursion limit
            result = self.agent.invoke(
                {"messages": [{"role": "user", "content": query}]}, {"recursion_limit": 150}
            )

            # Extract response from agent output
            if isinstance(result, dict) and "messages" in result:
                messages = result["messages"]
                # Get the last message from the agent
                for msg in reversed(messages):
                    if hasattr(msg, "content") and msg.content:
                        return msg.content
                    elif isinstance(msg, dict) and "content" in msg:
                        return msg["content"]

            return str(result)

        except Exception as e:
            logger.error(f"Error during analysis: {e}")
            return f"Error during analysis: {str(e)}"

    def analyze_stream(self, query: str, stream_mode: str = "values"):
        """
        Analyze documents and stream the response in real-time.

        Args:
            query: User question or analysis request
            stream_mode: Streaming mode - "values", "updates", or "messages"

        Yields:
            Stream chunks showing agent's thinking process
        """
        if not self.agent:
            yield {"error": "Agent not initialized. Load documents first using load_documents()"}
            return

        try:
            # Stream the agent response
            for chunk in self.agent.stream(
                {"messages": [{"role": "user", "content": query}]},
                {"recursion_limit": 150},
                stream_mode=stream_mode,
            ):
                yield chunk

        except Exception as e:
            logger.error(f"Error during streaming analysis: {e}")
            yield {"error": f"Error during analysis: {str(e)}"}

    def interactive_session(self) -> None:
        """Start an interactive Q&A session with the agent."""
        if not self.agent:
            print("Error: Agent not initialized. Load documents first.")
            return

        print("\n" + "=" * 80)
        print("Enterprise Document Analysis - Interactive Session")
        print("=" * 80)
        print("\nType your questions below. Type 'quit', 'exit', or 'q' to end the session.\n")

        while True:
            try:
                query = input("\n🔍 Your question: ").strip()

                if query.lower() in ["quit", "exit", "q"]:
                    print("\nEnding session. Goodbye!")
                    break

                if not query:
                    continue

                print("\n🤖 Agent: ", end="", flush=True)
                response = self.analyze(query)
                print(response)

            except KeyboardInterrupt:
                print("\n\nSession interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}")


def create_enterprise_agent(
    documents_dir: Path | str,
    model_provider: str = "anthropic",
    model_name: str | None = None,  # Let each provider use its default
    enable_memory: bool = True,
    enable_audit: bool = True,
    enable_progress: bool = True,
    max_conversation_messages: int = 30,
) -> EnterpriseAgent:
    """
    Factory function to create and initialize an enterprise agent.

    Args:
        documents_dir: Directory containing documents to analyze
        model_provider: "anthropic" or "openai"
        model_name: Model name to use
        enable_memory: Enable conversation memory middleware (default: True)
        enable_audit: Enable audit logging middleware (default: True)
        enable_progress: Enable progress tracking middleware (default: True)
        max_conversation_messages: Max messages to keep in memory (default: 30)

    Returns:
        Initialized EnterpriseAgent ready for queries
    """
    agent = EnterpriseAgent(
        model_provider=model_provider,
        model_name=model_name,
        enable_memory=enable_memory,
        enable_audit=enable_audit,
        enable_progress=enable_progress,
        max_conversation_messages=max_conversation_messages,
    )

    # Auto-detect file types and load with appropriate patterns
    patterns = ["**/*.dtsx", "**/*.cbl", "**/*.cob", "**/*.jcl", "**/*.JCL"]
    agent.load_documents(documents_dir, pattern=patterns)
    return agent
