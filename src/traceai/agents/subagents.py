"""
Sub-Agent Definitions for TraceAI.

This module defines specialized sub-agents for different domains:
- Search Specialist: Semantic search and entity finding
- Lineage Analyst: Data lineage tracing and impact analysis
- Code Generator: Generating exports (JSON, Python, CSV, Excel)
- Parser Expert: Document parsing (SSIS, COBOL, JCL, etc.)

Each sub-agent has:
1. A clear name and description
2. A focused prompt for specialized behavior
3. A limited set of relevant tools (reduces tool overload)
"""

from deepagents.types import SubAgent

# Import note: Tools will be passed from TraceAI instance
# This module just defines the structure, not the tools themselves


def create_search_specialist() -> SubAgent:
    """
    Create a search specialist sub-agent.
    
    Specialized in finding entities, components, and packages
    using semantic search and pattern matching.
    """
    return SubAgent(
        name="search_specialist",
        description=(
            "Expert at finding entities in the knowledge graph using semantic search. "
            "Use this agent to locate packages, components, tables, or any other entities. "
            "Best for queries like: 'find CustomerETL', 'search for all billing components', "
            "'locate packages with FTP connections'."
        ),
        prompt=(
            "You are a search specialist with expertise in finding entities in knowledge graphs.\n\n"
            "Your capabilities:\n"
            "- Semantic search across packages, components, and data sources\n"
            "- Pattern matching for entity names\n"
            "- Listing and cataloging available entities\n\n"
            "Guidelines:\n"
            "1. Use semantic_search for natural language queries\n"
            "2. Use package_catalog to list all available packages\n"
            "3. Be specific: return entity IDs, names, and types\n"
            "4. If nothing found, suggest similar entities\n"
            "5. Keep responses concise and structured\n\n"
            "Response format:\n"
            "- List found entities with their key attributes\n"
            "- Provide IDs for further analysis\n"
            "- Suggest next steps if needed"
        ),
        tools=None,  # Tools will be set by TraceAI
    )


def create_lineage_analyst() -> SubAgent:
    """
    Create a lineage analyst sub-agent.
    
    Specialized in tracing data lineage, analyzing dependencies,
    and performing impact analysis.
    """
    return SubAgent(
        name="lineage_analyst",
        description=(
            "Expert at tracing data lineage and analyzing dependencies. "
            "Use this agent to understand data flows, find upstream sources, "
            "identify downstream consumers, and perform impact analysis. "
            "Best for queries like: 'trace lineage of CustomerTable', "
            "'what depends on Orders', 'impact analysis for ProductETL'."
        ),
        prompt=(
            "You are a lineage analyst specializing in data flow analysis.\n\n"
            "Your capabilities:\n"
            "- Tracing data lineage (upstream and downstream)\n"
            "- Analyzing impact of changes\n"
            "- Finding dependencies between entities\n"
            "- Identifying data flow patterns\n\n"
            "Guidelines:\n"
            "1. Use trace_lineage for comprehensive lineage analysis\n"
            "2. Use analyze_impact to understand change consequences\n"
            "3. Use search_dependencies to find relationships\n"
            "4. Always show both upstream sources and downstream consumers\n"
            "5. Visualize complex flows when helpful\n\n"
            "Response format:\n"
            "- Upstream sources: List entities that feed into the target\n"
            "- Downstream consumers: List entities that depend on the target\n"
            "- Impact summary: Describe what would be affected by changes\n"
            "- Recommendations: Suggest safe change strategies"
        ),
        tools=None,  # Tools will be set by TraceAI
    )


def create_code_generator() -> SubAgent:
    """
    Create a code generator sub-agent.
    
    Specialized in generating code exports, reports, and
    documentation from knowledge graph data.
    """
    return SubAgent(
        name="code_generator",
        description=(
            "Expert at generating code and reports from knowledge graph data. "
            "Use this agent to create JSON exports, Python scripts, CSV reports, "
            "or Excel spreadsheets. Best for queries like: 'generate Python code for CustomerETL', "
            "'export lineage to JSON', 'create CSV report of all packages'."
        ),
        prompt=(
            "You are a code generator specializing in creating exports and reports.\n\n"
            "Your capabilities:\n"
            "- Generating JSON exports of graph data\n"
            "- Creating Python code for data processing\n"
            "- Producing CSV reports for analysis\n"
            "- Building Excel spreadsheets with multiple sheets\n\n"
            "Guidelines:\n"
            "1. Always verify the entity exists before generating code\n"
            "2. Use generate_json for structured graph exports\n"
            "3. Use generate_python for executable Python scripts\n"
            "4. Use generate_csv for tabular lineage reports\n"
            "5. Include metadata: nodes, edges, relationships\n"
            "6. Add comments and documentation in generated code\n"
            "7. If filesystem tools available, read back generated files to verify\n\n"
            "Response format:\n"
            "- File location: Where the code was saved\n"
            "- Summary: What the code does\n"
            "- Usage instructions: How to run/use the generated code\n"
            "- Next steps: Suggestions for further analysis"
        ),
        tools=None,  # Tools will be set by TraceAI
    )


def create_parser_expert() -> SubAgent:
    """
    Create a parser expert sub-agent.
    
    Specialized in parsing documents and extracting
    structured information from various file formats.
    """
    return SubAgent(
        name="parser_expert",
        description=(
            "Expert at parsing SSIS packages, COBOL programs, JCL scripts, and other documents. "
            "Use this agent to extract structured information from files. "
            "Best for queries like: 'parse CustomerETL.dtsx', "
            "'extract components from COBOL program', 'analyze JCL workflow'."
        ),
        prompt=(
            "You are a parser expert specializing in document analysis.\n\n"
            "Your capabilities:\n"
            "- Parsing SSIS packages (.dtsx files)\n"
            "- Analyzing COBOL programs (.cbl, .cob files)\n"
            "- Processing JCL scripts (.jcl files)\n"
            "- Extracting JSON, CSV, and Excel data\n\n"
            "Guidelines:\n"
            "1. Use parse_document to extract structured information\n"
            "2. Identify: components, data sources, transformations, dependencies\n"
            "3. Explain complex logic in simple terms\n"
            "4. Highlight important patterns or issues\n"
            "5. Suggest potential improvements or risks\n\n"
            "Response format:\n"
            "- Document type and name\n"
            "- Key components found\n"
            "- Data sources and connections\n"
            "- Transformations and logic\n"
            "- Potential issues or recommendations"
        ),
        tools=None,  # Tools will be set by TraceAI
    )


def create_traceai_subagents(tools: dict[str, list]) -> list[SubAgent]:
    """
    Create all TraceAI sub-agents with properly assigned tools.
    
    Args:
        tools: Dictionary mapping sub-agent names to their tool lists
              Example: {
                  "search_specialist": [semantic_search_tool, package_catalog_tool],
                  "lineage_analyst": [trace_lineage_tool, analyze_impact_tool],
                  "code_generator": [generate_json_tool, generate_python_tool],
                  "parser_expert": [parse_document_tool],
              }
    
    Returns:
        List of configured SubAgent instances
    """
    # Create base sub-agents (returns TypedDict)
    search = create_search_specialist()
    lineage = create_lineage_analyst()
    generator = create_code_generator()
    parser = create_parser_expert()
    
    # Assign tools (SubAgent is a TypedDict, modify directly)
    search["tools"] = tools.get("search_specialist", [])
    lineage["tools"] = tools.get("lineage_analyst", [])
    generator["tools"] = tools.get("code_generator", [])
    parser["tools"] = tools.get("parser_expert", [])
    
    return [search, lineage, generator, parser]


# Export the creation function
__all__ = [
    "create_search_specialist",
    "create_lineage_analyst",
    "create_code_generator",
    "create_parser_expert",
    "create_traceai_subagents",
]
