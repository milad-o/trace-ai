"""Python code generator from COBOL/JCL programs.

Generates modern Python equivalents of legacy mainframe code:
- COBOL file operations -> pandas DataFrames
- COBOL calculations -> Python functions
- JCL job workflows -> Python scripts/DAGs
"""

from pathlib import Path
from typing import Any

import networkx as nx
from jinja2 import Template
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from traceai.graph.queries import GraphQueries


class GeneratePythonInput(BaseModel):
    """Input for Python code generation tool."""

    node_id: str = Field(description="ID of the COBOL program or JCL job to convert")
    output_path: str = Field(description="Where to save the generated Python file")
    include_comments: bool = Field(default=True, description="Include explanatory comments")
    style: str = Field(
        default="script", description="Output style: 'script' (standalone) or 'function' (reusable)"
    )


class GeneratePythonTool(BaseTool):
    """Tool to generate Python code from COBOL/JCL."""

    name: str = "generate_python_from_cobol"
    description: str = """Generates Python code equivalent to COBOL programs or JCL jobs.

    Converts:
    - COBOL file I/O -> pandas read_csv/to_csv
    - COBOL calculations -> Python functions
    - COBOL paragraphs -> Python functions
    - JCL job steps -> Python script workflow

    Args:
        node_id: ID of COBOL program or JCL job to convert
        output_path: Where to save .py file (e.g., "output/customer_etl.py")
        include_comments: Add explanatory comments (default: true)
        style: 'script' for standalone or 'function' for reusable (default: script)

    Returns:
        Generated Python code and file path
    """
    args_schema: type[BaseModel] = GeneratePythonInput
    queries: GraphQueries

    def __init__(self, queries: GraphQueries | nx.DiGraph | None = None):
        # Accept both GraphQueries and raw DiGraph for flexibility
        # Allow None for backward compatibility (will fail at runtime if actually used)
        if queries is None:
            # Create a dummy empty graph for tests that don't need actual graph operations
            queries = GraphQueries(nx.DiGraph())
        elif isinstance(queries, nx.DiGraph):
            queries = GraphQueries(queries)
        super().__init__(queries=queries)

    def _run(
        self,
        node_id: str,
        output_path: str,
        include_comments: bool = True,
        style: str = "script",
    ) -> str:
        """Generates Python code from COBOL/JCL."""
        graph = self.queries.graph

        # Find the node
        if node_id not in graph:
            return f"❌ Node '{node_id}' not found in graph"

        node_data = graph.nodes[node_id]
        node_type = node_data.get("type")

        # Generate based on type
        if node_type == "package":
            program_type = node_data.get("description", "")
            if "COBOL" in program_type.upper():
                code = self._generate_from_cobol(node_id, node_data, include_comments, style)
            elif "JCL" in program_type.upper():
                code = self._generate_from_jcl(node_id, node_data, include_comments, style)
            else:
                return f"❌ Unknown program type for node '{node_id}'"
        else:
            return f"❌ Node '{node_id}' is not a program/job (type: {node_type})"

        # Save to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(code)

        return f"✅ Python code generated: {output_path}\n\n{code[:500]}...\n\n(Full code saved to file)"

    def _generate_from_cobol(
        self, node_id: str, node_data: dict, include_comments: bool, style: str
    ) -> str:
        """Generates Python from COBOL program."""
        graph = self.queries.graph
        program_name = node_data.get("name", "unknown")

        # Find paragraphs (tasks)
        paragraphs = []
        for succ in graph.successors(node_id):
            succ_data = graph.nodes[succ]
            if succ_data.get("type") == "task":
                paragraphs.append(succ_data)

        # Find file I/O operations (connections to tables)
        input_files = []
        output_files = []

        for neighbor in graph.neighbors(node_id):
            neighbor_data = graph.nodes[neighbor]
            if neighbor_data.get("type") == "table":
                # Check edge type
                edge_data = graph.get_edge_data(node_id, neighbor) or graph.get_edge_data(
                    neighbor, node_id
                )
                if edge_data:
                    edge_type = edge_data.get("edge_type", "")
                    if "READS" in edge_type.upper():
                        input_files.append(neighbor_data.get("name"))
                    elif "WRITES" in edge_type.upper():
                        output_files.append(neighbor_data.get("name"))

        # Generate code using template
        template = Template(COBOL_TO_PYTHON_TEMPLATE)
        code = template.render(
            program_name=program_name,
            input_files=input_files,
            output_files=output_files,
            paragraphs=paragraphs,
            include_comments=include_comments,
            style=style,
        )

        return code

    def _generate_from_jcl(
        self, node_id: str, node_data: dict, include_comments: bool, style: str
    ) -> str:
        """Generates Python from JCL job."""
        graph = self.queries.graph
        job_name = node_data.get("name", "unknown")

        # Find job steps (tasks)
        steps = []
        for succ in graph.successors(node_id):
            succ_data = graph.nodes[succ]
            if succ_data.get("type") == "task":
                steps.append(
                    {
                        "name": succ_data.get("name"),
                        "program": succ_data.get("source_code", "unknown"),
                    }
                )

        # Generate code using template
        template = Template(JCL_TO_PYTHON_TEMPLATE)
        code = template.render(
            job_name=job_name,
            steps=steps,
            include_comments=include_comments,
            style=style,
        )

        return code


# Jinja2 template for COBOL to Python conversion
COBOL_TO_PYTHON_TEMPLATE = """\"\"\"
Generated Python code from COBOL program: {{ program_name }}
{% if include_comments %}
This code is a modern Python equivalent of the original COBOL program.
It uses pandas for data processing instead of COBOL file I/O.
{% endif %}
\"\"\"

import pandas as pd
from pathlib import Path
{% if style == 'function' %}
from typing import Dict, List
{% endif %}

{% if include_comments %}
# Input files (COBOL READ operations)
{% endif %}
INPUT_FILES = [
{% for file in input_files %}
    "{{ file }}",
{% endfor %}
]

{% if include_comments %}
# Output files (COBOL WRITE operations)
{% endif %}
OUTPUT_FILES = [
{% for file in output_files %}
    "{{ file }}",
{% endfor %}
]

{% for paragraph in paragraphs %}

def {{ paragraph.name|lower|replace('-', '_') }}({% if style == 'function' %}data: pd.DataFrame{% endif %}) -> {% if style == 'function' %}pd.DataFrame{% else %}None{% endif %}:
    {% if include_comments %}\"\"\"
    Equivalent to COBOL paragraph: {{ paragraph.name }}
    Original COBOL description: {{ paragraph.get('description', 'N/A') }}
    \"\"\"{% endif %}
    {% if style == 'script' %}
    # TODO: Implement paragraph logic
    print(f"Executing: {{ paragraph.name }}")
    {% else %}
    # TODO: Implement transformation logic
    result = data.copy()
    return result
    {% endif %}
{% endfor %}

{% if style == 'script' %}
def main():
    {% if include_comments %}\"\"\"Main execution flow.\"\"\"{% endif %}

    # Load input files
{% for file in input_files %}
    df_{{ loop.index }} = pd.read_csv("{{ file }}")
    print(f"Loaded {{ file }}: {len(df_{{ loop.index }})} rows")
{% endfor %}

    # Execute paragraphs
{% for paragraph in paragraphs %}
    {{ paragraph.name|lower|replace('-', '_') }}()
{% endfor %}

    # Write output files
{% for file in output_files %}
    # TODO: Save results to {{ file }}
    # df_result.to_csv("{{ file }}", index=False)
{% endfor %}

    print("Processing complete")


if __name__ == "__main__":
    main()
{% endif %}
"""

# Jinja2 template for JCL to Python conversion
JCL_TO_PYTHON_TEMPLATE = """\"\"\"
Generated Python code from JCL job: {{ job_name }}
{% if include_comments %}
This code replicates the JCL job workflow as a Python script.
Each JCL step is represented as a function call.
{% endif %}
\"\"\"

import subprocess
from pathlib import Path
{% if style == 'function' %}
from typing import Dict
{% endif %}

{% for step in steps %}

def step_{{ step.name|lower|replace('.', '_') }}() -> int:
    {% if include_comments %}\"\"\"
    Executes JCL step: {{ step.name }}
    Original program: {{ step.program }}
    \"\"\"{% endif %}
    print(f"Executing step: {{ step.name }}")

    # TODO: Implement step logic
    # Original COBOL program: {{ step.program }}

    return 0  # Return code (0 = success)
{% endfor %}

{% if style == 'script' %}
def main():
    {% if include_comments %}\"\"\"Main job execution workflow.\"\"\"{% endif %}
    print(f"Starting job: {{ job_name }}")

    # Execute steps in sequence
{% for step in steps %}
    rc_{{ loop.index }} = step_{{ step.name|lower|replace('.', '_') }}()
    if rc_{{ loop.index }} != 0:
        print(f"Step {{ step.name }} failed with RC={rc_{{ loop.index }}}")
        return rc_{{ loop.index }}
{% endfor %}

    print(f"Job {{ job_name }} completed successfully")
    return 0


if __name__ == "__main__":
    exit(main())
{% endif %}
"""
