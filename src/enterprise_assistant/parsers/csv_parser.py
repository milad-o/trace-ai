"""CSV parser for data lineage metadata and mapping files.

Parses CSV files that contain:
- Data lineage mappings (source -> target)
- Field-level transformations
- Data quality rules
- ETL metadata
"""

from pathlib import Path
from typing import Any

import pandas as pd

from enterprise_assistant.parsers.base import (
    BaseParser,
    Component,
    DataEntity,
    DataSource,
    Dependency,
    DocumentMetadata,
    DocumentType,
    Parameter,
    ParsedDocument,
)


class CSVParser(BaseParser):
    """Parser for CSV files containing ETL metadata."""

    def supported_extensions(self) -> list[str]:
        """Returns list of supported file extensions."""
        return [".csv", ".tsv"]

    def document_type(self) -> DocumentType:
        """Returns the document type this parser handles."""
        return DocumentType.JSON_CONFIG  # Reuse for now, could add CSV_METADATA

    def validate(self, file_path: Path) -> bool:
        """Validates if the file is a valid CSV."""
        try:
            separator = "\t" if file_path.suffix == ".tsv" else ","
            pd.read_csv(file_path, sep=separator, nrows=1)
            return True
        except Exception:
            return False

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parses a CSV file.

        Supports various CSV schemas:
        1. Lineage mapping (source_table, target_table, transformation)
        2. Field mapping (source_field, target_field, mapping_logic)
        3. ETL metadata (job_name, description, schedule, etc.)
        4. Generic CSV (each row becomes a component)
        """
        separator = "\t" if file_path.suffix == ".tsv" else ","
        df = pd.read_csv(file_path, sep=separator)

        # Extract metadata
        metadata = self._extract_metadata(file_path, df)

        # Detect CSV type based on columns
        components: list[Component] = []
        dependencies: list[Dependency] = []
        data_entities: list[DataEntity] = []

        columns_lower = [col.lower() for col in df.columns]

        if self._is_lineage_mapping(columns_lower):
            # Parse as lineage mapping
            result = self._parse_lineage_mapping(df, metadata.document_id)
            dependencies.extend(result["dependencies"])
            data_entities.extend(result["entities"])
        elif self._is_field_mapping(columns_lower):
            # Parse as field mapping
            result = self._parse_field_mapping(df, metadata.document_id)
            components.extend(result["components"])
        elif self._is_etl_metadata(columns_lower):
            # Parse as ETL metadata
            components.extend(self._parse_etl_metadata(df, metadata.document_id))
        else:
            # Generic CSV - each row is a component
            components.extend(self._parse_generic(df, metadata.document_id))

        return ParsedDocument(
            metadata=metadata,
            components=components,
            data_sources=[],
            parameters=[],
            data_entities=data_entities,
            dependencies=dependencies,
        )

    def _extract_metadata(self, file_path: Path, df: pd.DataFrame) -> DocumentMetadata:
        """Extracts metadata from CSV file."""
        return DocumentMetadata(
            name=file_path.stem,
            document_id=f"csv_{file_path.stem}",
            document_type=self.document_type(),
            description=f"CSV file with {len(df)} rows",
            file_path=file_path,
            custom_attributes={
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": list(df.columns),
            },
        )

    def _is_lineage_mapping(self, columns: list[str]) -> bool:
        """Checks if CSV is a lineage mapping."""
        lineage_keywords = {"source_table", "target_table", "source", "target", "from_table", "to_table"}
        return any(kw in col for col in columns for kw in lineage_keywords)

    def _is_field_mapping(self, columns: list[str]) -> bool:
        """Checks if CSV is a field mapping."""
        field_keywords = {"source_field", "target_field", "source_column", "target_column"}
        return any(kw in col for col in columns for kw in field_keywords)

    def _is_etl_metadata(self, columns: list[str]) -> bool:
        """Checks if CSV is ETL metadata."""
        etl_keywords = {"job_name", "etl_name", "pipeline", "schedule", "description"}
        return any(kw in col for col in columns for kw in etl_keywords)

    def _parse_lineage_mapping(self, df: pd.DataFrame, doc_id: str) -> dict[str, Any]:
        """Parses lineage mapping CSV."""
        dependencies: list[Dependency] = []
        entities: list[DataEntity] = []
        seen_entities: set[str] = set()

        # Find source and target columns
        source_col = self._find_column(df, ["source_table", "source", "from_table"])
        target_col = self._find_column(df, ["target_table", "target", "to_table"])
        transform_col = self._find_column(df, ["transformation", "transform", "logic"])

        if not source_col or not target_col:
            return {"dependencies": [], "entities": []}

        for idx, row in df.iterrows():
            source = row[source_col]
            target = row[target_col]

            if pd.notna(source) and pd.notna(target):
                source_str = str(source)
                target_str = str(target)

                # Create entities
                if source_str not in seen_entities:
                    entities.append(
                        DataEntity(
                            name=source_str,
                            entity_type="table",
                        )
                    )
                    seen_entities.add(source_str)

                if target_str not in seen_entities:
                    entities.append(
                        DataEntity(
                            name=target_str,
                            entity_type="table",
                        )
                    )
                    seen_entities.add(target_str)

                # Create dependency
                transform = row[transform_col] if transform_col and pd.notna(row[transform_col]) else None
                dependencies.append(
                    Dependency(
                        from_id=source_str,
                        to_id=target_str,
                        dependency_type="data_flow",
                        properties={"transformation": str(transform)} if transform else {},
                    )
                )

        return {"dependencies": dependencies, "entities": entities}

    def _parse_field_mapping(self, df: pd.DataFrame, doc_id: str) -> dict[str, Any]:
        """Parses field mapping CSV."""
        components: list[Component] = []

        source_col = self._find_column(df, ["source_field", "source_column", "source"])
        target_col = self._find_column(df, ["target_field", "target_column", "target"])
        logic_col = self._find_column(df, ["mapping_logic", "transformation", "logic"])

        if not source_col or not target_col:
            return {"components": []}

        for idx, row in df.iterrows():
            source = row[source_col]
            target = row[target_col]

            if pd.notna(source) and pd.notna(target):
                component = Component(
                    name=f"{source} -> {target}",
                    component_id=f"{doc_id}_mapping_{idx}",
                    component_type="field_mapping",
                    description=f"Maps {source} to {target}",
                    source_code=str(row[logic_col]) if logic_col and pd.notna(row[logic_col]) else None,
                    properties=row.to_dict(),
                )
                components.append(component)

        return {"components": components}

    def _parse_etl_metadata(self, df: pd.DataFrame, doc_id: str) -> list[Component]:
        """Parses ETL metadata CSV."""
        components: list[Component] = []

        name_col = self._find_column(df, ["job_name", "etl_name", "name", "pipeline"])
        desc_col = self._find_column(df, ["description", "desc"])

        if not name_col:
            return []

        for idx, row in df.iterrows():
            name = row[name_col]

            if pd.notna(name):
                component = Component(
                    name=str(name),
                    component_id=f"{doc_id}_etl_{idx}",
                    component_type="etl_job",
                    description=str(row[desc_col]) if desc_col and pd.notna(row[desc_col]) else None,
                    properties=row.to_dict(),
                )
                components.append(component)

        return components

    def _parse_generic(self, df: pd.DataFrame, doc_id: str) -> list[Component]:
        """Parses generic CSV - each row becomes a component."""
        components: list[Component] = []

        # Use first column as name if available
        name_col = df.columns[0] if len(df.columns) > 0 else None

        for idx, row in df.iterrows():
            name = str(row[name_col]) if name_col and pd.notna(row[name_col]) else f"Row{idx}"

            component = Component(
                name=name,
                component_id=f"{doc_id}_row_{idx}",
                component_type="csv_row",
                description=f"CSV row {idx}",
                properties=row.to_dict(),
            )
            components.append(component)

        return components

    def _find_column(self, df: pd.DataFrame, candidates: list[str]) -> str | None:
        """Finds a column matching one of the candidate names (case-insensitive)."""
        columns_lower = {col.lower(): col for col in df.columns}

        for candidate in candidates:
            if candidate.lower() in columns_lower:
                return columns_lower[candidate.lower()]

        return None

    def extract_data_entities(self, component: Component) -> list[DataEntity]:
        """Extracts data entities from component properties."""
        entities: list[DataEntity] = []

        # Check for table references in properties
        for key, value in component.properties.items():
            if "table" in key.lower() and value:
                entities.append(
                    DataEntity(
                        name=str(value),
                        entity_type="table",
                    )
                )

        return entities
