"""COBOL program parser for enterprise analysis.

Parses COBOL programs (.cbl, .cob, .CBL) to extract:
- Program structure (IDENTIFICATION, DATA, PROCEDURE divisions)
- Paragraphs and sections (tasks)
- Data definitions (working storage, file section)
- Program flow (PERFORM calls, CALL statements)
- File I/O operations (READ, WRITE)
- Database operations (EXEC SQL)
"""

import re
from pathlib import Path
from typing import Any

from enterprise_assistant.logger import logger
from enterprise_assistant.parsers.base import (
    BaseParser,
    Component,
    DataEntity,
    DataSource,
    Dependency,
    DocumentMetadata,
    DocumentType,
    ParsedDocument,
)


class COBOLParser(BaseParser):
    """Parser for COBOL programs."""

    @property
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions."""
        return [".cbl", ".cob", ".CBL", ".COB"]

    @property
    def document_type(self) -> DocumentType:
        """Return the document type this parser handles."""
        return DocumentType.COBOL_PROGRAM

    def validate(self, file_path: Path) -> bool:
        """
        Validate if file is a COBOL program.

        Args:
            file_path: Path to the file

        Returns:
            True if file is COBOL, False otherwise
        """
        return file_path.suffix.lower() in [".cbl", ".cob", ".cobol"]

    def parse(self, file_path: Path) -> ParsedDocument:
        """
        Parse COBOL program into structured format.

        Args:
            file_path: Path to COBOL file

        Returns:
            ParsedDocument with extracted information
        """
        logger.info(f"Parsing COBOL program: {file_path}")

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Extract program ID
        program_id = self._extract_program_id(content)

        # Extract author for metadata
        author = self._extract_author(content)

        # Parse divisions
        data_division = self._parse_data_division(content)
        procedure_division = self._parse_procedure_division(content)

        # Extract dependencies (PERFORM, CALL)
        dependencies = self._extract_dependencies(content, procedure_division)

        # Build metadata
        metadata = DocumentMetadata(
            document_id=program_id or file_path.stem,
            name=program_id or file_path.stem,
            document_type=DocumentType.COBOL_PROGRAM,
            file_path=str(file_path),
            description=f"COBOL program: {program_id}" + (f" by {author}" if author else ""),
        )

        # Count statistics
        num_paragraphs = len(procedure_division)
        num_data_items = len(data_division["data_items"])
        num_files = len(data_division["files"])

        logger.info(
            f"Parsed {program_id}: {num_paragraphs} paragraphs, "
            f"{num_data_items} data items, {num_files} files, "
            f"{len(dependencies)} dependencies"
        )

        return ParsedDocument(
            metadata=metadata,
            components=procedure_division,
            data_sources=data_division["files"],
            data_entities=data_division["data_items"],
            dependencies=dependencies,
        )

    def _extract_program_id(self, content: str) -> str | None:
        """Extract PROGRAM-ID from IDENTIFICATION DIVISION."""
        match = re.search(r"PROGRAM-ID\.\s+([A-Z0-9\-]+)", content, re.IGNORECASE)
        return match.group(1) if match else None

    def _extract_author(self, content: str) -> str | None:
        """Extract AUTHOR from IDENTIFICATION DIVISION."""
        match = re.search(r"AUTHOR\.\s+(.+?)(?:\.|$)", content, re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _parse_data_division(self, content: str) -> dict[str, Any]:
        """
        Parse DATA DIVISION to extract files and data items.

        Returns:
            Dict with 'files' (DataSource list) and 'data_items' (DataEntity list)
        """
        files = []
        data_items = []

        # Extract FILE-CONTROL section (files)
        file_control_match = re.search(
            r"FILE-CONTROL\.(.*?)(?:WORKING-STORAGE|DATA DIVISION|PROCEDURE DIVISION|$)",
            content,
            re.DOTALL | re.IGNORECASE,
        )

        if file_control_match:
            file_section = file_control_match.group(1)

            # Find SELECT statements
            for select_match in re.finditer(
                r"SELECT\s+([A-Z0-9\-]+)\s+ASSIGN\s+TO\s+['\"]?([^'\"\s.]+)",
                file_section,
                re.IGNORECASE,
            ):
                file_name = select_match.group(1)
                file_path = select_match.group(2)

                files.append(
                    DataSource(
                        source_id=f"file_{file_name}",
                        name=file_name,
                        source_type="FILE",
                        connection_string=file_path,
                        description=f"COBOL file: {file_name}",
                    )
                )

        # Extract WORKING-STORAGE section (data items)
        ws_match = re.search(
            r"WORKING-STORAGE SECTION\.(.*?)(?:PROCEDURE DIVISION|$)",
            content,
            re.DOTALL | re.IGNORECASE,
        )

        if ws_match:
            ws_section = ws_match.group(1)

            # Find 01-level data items (records)
            for record_match in re.finditer(
                r"^\s*01\s+([A-Z0-9\-]+)\.?\s*$", ws_section, re.MULTILINE | re.IGNORECASE
            ):
                record_name = record_match.group(1)

                # Extract fields (05, 10, 15 levels) following this record
                record_pos = record_match.end()
                next_01 = re.search(r"^\s*01\s+", ws_section[record_pos:], re.MULTILINE)
                record_end = record_pos + next_01.start() if next_01 else len(ws_section)

                record_content = ws_section[record_pos:record_end]

                # Find all field definitions
                fields = []
                for field_match in re.finditer(
                    r"^\s*(\d+)\s+([A-Z0-9\-]+)\s+PIC\s+([X9V\(\)]+)",
                    record_content,
                    re.MULTILINE | re.IGNORECASE,
                ):
                    level = field_match.group(1)
                    field_name = field_match.group(2)
                    pic_clause = field_match.group(3)
                    fields.append({"level": level, "name": field_name, "type": pic_clause})

                data_items.append(
                    DataEntity(
                        name=record_name,
                        entity_type="RECORD",
                        description=f"COBOL data record with {len(fields)} fields",
                        columns=[f["name"] for f in fields] if fields else [],
                        properties={"fields": fields} if fields else {},
                    )
                )

        return {"files": files, "data_items": data_items}

    def _parse_procedure_division(self, content: str) -> list[Component]:
        """
        Parse PROCEDURE DIVISION to extract paragraphs and sections.

        Returns:
            List of Component objects (each paragraph is a component)
        """
        components = []

        # Find PROCEDURE DIVISION
        proc_match = re.search(
            r"PROCEDURE DIVISION\.(.*?)$", content, re.DOTALL | re.IGNORECASE
        )

        if not proc_match:
            return components

        proc_section = proc_match.group(1)

        # Find all paragraphs (labels at start of line followed by .)
        # Paragraphs are identifiers followed by period at start of line
        paragraph_pattern = r"^\s*([A-Z][A-Z0-9\-]*)\.\s*$"

        matches = list(re.finditer(paragraph_pattern, proc_section, re.MULTILINE | re.IGNORECASE))

        for i, match in enumerate(matches):
            para_name = match.group(1)

            # Skip if this looks like a COBOL keyword
            if para_name.upper() in ["STOP", "EXIT", "GOBACK"]:
                continue

            # Get paragraph content (from this match to next paragraph or end)
            start_pos = match.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(proc_section)
            para_content = proc_section[start_pos:end_pos]

            # Extract operations performed
            operations = []

            # PERFORM statements
            for perf in re.finditer(r"PERFORM\s+([A-Z0-9\-]+)", para_content, re.IGNORECASE):
                operations.append(f"PERFORM {perf.group(1)}")

            # CALL statements
            for call in re.finditer(r"CALL\s+['\"]([^'\"]+)['\"]", para_content, re.IGNORECASE):
                operations.append(f"CALL {call.group(1)}")

            # READ statements
            for read in re.finditer(r"READ\s+([A-Z0-9\-]+)", para_content, re.IGNORECASE):
                operations.append(f"READ {read.group(1)}")

            # WRITE statements
            for write in re.finditer(r"WRITE\s+([A-Z0-9\-]+)", para_content, re.IGNORECASE):
                operations.append(f"WRITE {write.group(1)}")

            # EXEC SQL (database operations)
            for sql in re.finditer(
                r"EXEC\s+SQL\s+(.*?)\s+END-EXEC", para_content, re.IGNORECASE | re.DOTALL
            ):
                sql_stmt = sql.group(1).strip()[:50]  # First 50 chars
                operations.append(f"SQL: {sql_stmt}")

            components.append(
                Component(
                    component_id=f"para_{para_name}",
                    name=para_name,
                    component_type="COBOL_PARAGRAPH",
                    description=f"COBOL paragraph with {len(operations)} operations",
                    source_code=para_content.strip()[:500],  # First 500 chars
                    properties={"operations": operations} if operations else None,
                )
            )

        return components

    def _extract_dependencies(
        self, content: str, components: list[Component]
    ) -> list[Dependency]:
        """
        Extract dependencies between paragraphs and external programs.

        Args:
            content: Full COBOL source
            components: Parsed components (paragraphs)

        Returns:
            List of Dependency objects
        """
        dependencies = []
        component_names = {c.name for c in components}

        # For each component, find what it depends on
        for component in components:
            if not component.properties or "operations" not in component.properties:
                continue

            for operation in component.properties["operations"]:
                # PERFORM dependencies (internal)
                if operation.startswith("PERFORM "):
                    target = operation.split()[1]
                    if target in component_names:
                        dependencies.append(
                            Dependency(
                                from_id=component.component_id,
                                to_id=f"para_{target}",
                                dependency_type="PERFORMS",
                                description=f"{component.name} performs {target}",
                            )
                        )

                # CALL dependencies (external)
                elif operation.startswith("CALL "):
                    target = operation.split()[1]
                    dependencies.append(
                        Dependency(
                            from_id=component.component_id,
                            to_id=f"prog_{target}",
                            dependency_type="CALLS",
                            description=f"{component.name} calls external program {target}",
                        )
                    )

                # READ/WRITE dependencies (file I/O)
                elif operation.startswith("READ "):
                    file_name = operation.split()[1]
                    dependencies.append(
                        Dependency(
                            from_id=component.component_id,
                            to_id=f"file_{file_name}",
                            dependency_type="READS_FROM",
                            description=f"{component.name} reads from {file_name}",
                        )
                    )

                elif operation.startswith("WRITE "):
                    file_name = operation.split()[1]
                    dependencies.append(
                        Dependency(
                            from_id=component.component_id,
                            to_id=f"file_{file_name}",
                            dependency_type="WRITES_TO",
                            description=f"{component.name} writes to {file_name}",
                        )
                    )

        return dependencies
