"""JCL (Job Control Language) parser for mainframe batch jobs.

Parses JCL files (.jcl, .JCL) to extract:
- Job definition (//JOBNAME JOB)
- Steps (//STEPNAME EXEC)
- Programs executed (PGM=)
- Datasets (DD statements)
- Dependencies between steps
- File I/O (INPUT, OUTPUT datasets)
"""

import re
from pathlib import Path
from typing import Any

from traceai.logger import logger
from traceai.parsers.base import (
    BaseParser,
    Component,
    DataEntity,
    DataSource,
    Dependency,
    DocumentMetadata,
    DocumentType,
    ParsedDocument,
)


class JCLParser(BaseParser):
    """Parser for JCL (Job Control Language) files."""

    @property
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions."""
        return [".jcl", ".JCL", ".txt"]

    @property
    def document_type(self) -> DocumentType:
        """Return the document type this parser handles."""
        return DocumentType.MAINFRAME_JCL

    def validate(self, file_path: Path) -> bool:
        """
        Validate if file is JCL.

        Args:
            file_path: Path to the file

        Returns:
            True if file is JCL, False otherwise
        """
        if file_path.suffix.lower() not in [".jcl", ".txt"]:
            return False

        # Check if content starts with // (JCL indicator)
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                first_line = f.readline().strip()
                return first_line.startswith("//")
        except:
            return False

    def parse(self, file_path: Path) -> ParsedDocument:
        """
        Parse JCL file into structured format.

        Args:
            file_path: Path to JCL file

        Returns:
            ParsedDocument with extracted information
        """
        logger.info(f"Parsing JCL file: {file_path}")

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Extract job name
        job_name = self._extract_job_name(content)

        # Parse job steps
        steps = self._parse_steps(content)

        # Extract datasets (DD statements)
        datasets = self._extract_datasets(content)

        # Extract dependencies between steps
        dependencies = self._extract_dependencies(steps)

        # Build metadata
        metadata = DocumentMetadata(
            document_id=job_name or file_path.stem,
            name=job_name or file_path.stem,
            document_type=DocumentType.MAINFRAME_JCL,
            file_path=str(file_path),
            description=f"JCL batch job: {job_name or file_path.stem}",
        )

        logger.info(
            f"Parsed {job_name}: {len(steps)} steps, "
            f"{len(datasets)} datasets, {len(dependencies)} dependencies"
        )

        return ParsedDocument(
            metadata=metadata,
            components=steps,
            data_sources=datasets,
            data_entities=[],
            dependencies=dependencies,
        )

    def _extract_job_name(self, content: str) -> str | None:
        """Extract job name from //JOBNAME JOB statement."""
        match = re.search(r"^//([A-Z0-9]+)\s+JOB\s", content, re.MULTILINE | re.IGNORECASE)
        return match.group(1) if match else None

    def _parse_steps(self, content: str) -> list[Component]:
        """
        Parse job steps (//STEPNAME EXEC).

        Returns:
            List of Component objects (each step is a component)
        """
        steps = []

        # Find all EXEC statements
        for match in re.finditer(
            r"^//([A-Z0-9]+)\s+EXEC\s+(PGM=([A-Z0-9]+)|PROC=([A-Z0-9]+))",
            content,
            re.MULTILINE | re.IGNORECASE,
        ):
            step_name = match.group(1)
            program = match.group(3) or match.group(4)  # PGM or PROC

            # Find all DD statements for this step
            # Look ahead from current position until next EXEC or end
            step_pos = match.end()
            next_exec = re.search(r"^//[A-Z0-9]+\s+EXEC\s", content[step_pos:], re.MULTILINE)
            step_end = step_pos + next_exec.start() if next_exec else len(content)

            step_content = content[match.start():step_end]

            # Extract DD statements in this step
            # Support DD names with dots like COBOL.SYSIN
            dd_statements = []
            for dd_match in re.finditer(
                r"^//([A-Z0-9.]+)\s+DD\s+(.+)$",
                step_content,
                re.MULTILINE | re.IGNORECASE,
            ):
                dd_name = dd_match.group(1)
                dd_params = dd_match.group(2)
                dd_statements.append({"name": dd_name, "params": dd_params})

            # Determine operation type from DD statements
            operations = []
            for dd in dd_statements:
                if "DSN=" in dd["params"].upper():
                    # Support datasets with &SYSUID, dots, and parentheses
                    dsn_match = re.search(r"DSN=([A-Z0-9.&()]+)", dd["params"], re.IGNORECASE)
                    if dsn_match:
                        dataset = dsn_match.group(1)
                        if "DISP=(,CATLG" in dd["params"].upper() or "DISP=(NEW" in dd["params"].upper():
                            operations.append(f"WRITE {dataset}")
                        else:
                            operations.append(f"READ {dataset}")

            steps.append(
                Component(
                    component_id=f"step_{step_name}",
                    name=step_name,
                    component_type="JCL_STEP",
                    description=f"JCL step executing {program}",
                    source_code=step_content.strip()[:500],
                    properties={
                        "program": program,
                        "dd_count": len(dd_statements),
                        "operations": operations,
                    },
                )
            )

        return steps

    def _extract_datasets(self, content: str) -> list[DataSource]:
        """
        Extract dataset definitions (DD statements).

        Returns:
            List of DataSource objects
        """
        datasets = []
        seen_datasets = set()

        # Find all DSN= parameters in DD statements
        # Support: SALES.INPUT.TRANS, &SYSUID..CBL(CBL0001), DB2.SCHEMA.TABLE
        # DD names can be: //STEP001 or //COBOL.SYSIN (with dots)
        for match in re.finditer(
            r"^//[A-Z0-9.]+\s+DD\s+.*DSN=([A-Z0-9.&()]+)",
            content,
            re.MULTILINE | re.IGNORECASE,
        ):
            dataset_name = match.group(1)

            # Avoid duplicates
            if dataset_name in seen_datasets:
                continue

            seen_datasets.add(dataset_name)

            # Determine if it's a file, database, or tape
            source_type = "FILE"
            if dataset_name.startswith("DB2."):
                source_type = "DATABASE"
            elif "TAPE" in dataset_name.upper():
                source_type = "TAPE"

            datasets.append(
                DataSource(
                    source_id=f"dataset_{dataset_name.replace('.', '_')}",
                    name=dataset_name,
                    source_type=source_type,
                    connection_string=dataset_name,
                    description=f"Mainframe dataset: {dataset_name}",
                )
            )

        return datasets

    def _extract_dependencies(self, steps: list[Component]) -> list[Dependency]:
        """
        Extract dependencies between steps and datasets.

        Args:
            steps: Parsed job steps

        Returns:
            List of Dependency objects
        """
        dependencies = []

        # Sequential dependencies (each step depends on previous)
        for i in range(len(steps) - 1):
            dependencies.append(
                Dependency(
                    from_id=steps[i].component_id,
                    to_id=steps[i + 1].component_id,
                    dependency_type="PRECEDES",
                    description=f"{steps[i].name} must complete before {steps[i + 1].name}",
                )
            )

        # Dataset dependencies (READ/WRITE)
        for step in steps:
            if not step.properties or "operations" not in step.properties:
                continue

            for operation in step.properties["operations"]:
                if operation.startswith("READ "):
                    dataset = operation.split()[1]
                    dependencies.append(
                        Dependency(
                            from_id=step.component_id,
                            to_id=f"dataset_{dataset.replace('.', '_')}",
                            dependency_type="READS_FROM",
                            description=f"{step.name} reads from {dataset}",
                        )
                    )

                elif operation.startswith("WRITE "):
                    dataset = operation.split()[1]
                    dependencies.append(
                        Dependency(
                            from_id=step.component_id,
                            to_id=f"dataset_{dataset.replace('.', '_')}",
                            dependency_type="WRITES_TO",
                            description=f"{step.name} writes to {dataset}",
                        )
                    )

        return dependencies
