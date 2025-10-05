"""JSON parser for configuration files and data pipeline definitions.

Parses JSON documents that define:
- Data pipeline configurations
- ETL job definitions
- Data schema definitions
- API configurations
"""

import json
from pathlib import Path
from typing import Any

from traceai.parsers.base import (
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


class JSONParser(BaseParser):
    """Parser for JSON configuration files."""

    def supported_extensions(self) -> list[str]:
        """Returns list of supported file extensions."""
        return [".json", ".jsonc"]

    def document_type(self) -> DocumentType:
        """Returns the document type this parser handles."""
        return DocumentType.JSON_CONFIG

    def validate(self, file_path: Path) -> bool:
        """Validates if the file is a valid JSON document."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                json.load(f)
            return True
        except (json.JSONDecodeError, OSError):
            return False

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parses a JSON configuration file.

        Supports various JSON schemas:
        1. Pipeline configuration (with 'pipeline' or 'stages' key)
        2. ETL job definition (with 'jobs' or 'tasks' key)
        3. Data schema (with 'schema' or 'tables' key)
        4. Generic JSON (extracts structure as components)
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Extract metadata
        metadata = self._extract_metadata(file_path, data)

        # Extract components, data sources, and dependencies based on schema
        components: list[Component] = []
        data_sources: list[DataSource] = []
        parameters: list[Parameter] = []
        data_entities: list[DataEntity] = []
        dependencies: list[Dependency] = []

        # Detect schema type and parse accordingly
        if "pipeline" in data or "stages" in data:
            # Pipeline configuration
            result = self._parse_pipeline(data, metadata.document_id)
            components.extend(result["components"])
            dependencies.extend(result["dependencies"])
        elif "jobs" in data or "tasks" in data:
            # ETL job definition
            result = self._parse_etl_jobs(data, metadata.document_id)
            components.extend(result["components"])
            dependencies.extend(result["dependencies"])
        elif "schema" in data or "tables" in data:
            # Data schema definition
            result = self._parse_schema(data)
            data_entities.extend(result["entities"])
        elif "connections" in data or "datasources" in data:
            # Data source configuration
            data_sources.extend(self._parse_datasources(data))
        else:
            # Generic JSON - extract structure
            result = self._parse_generic(data, metadata.document_id)
            components.extend(result["components"])

        # Extract parameters (common across all types)
        if "parameters" in data or "variables" in data:
            parameters.extend(self._parse_parameters(data))

        return ParsedDocument(
            metadata=metadata,
            components=components,
            data_sources=data_sources,
            parameters=parameters,
            data_entities=data_entities,
            dependencies=dependencies,
        )

    def _extract_metadata(self, file_path: Path, data: dict[str, Any]) -> DocumentMetadata:
        """Extracts metadata from JSON document."""
        name = data.get("name", file_path.stem)
        document_id = data.get("id", f"json_{file_path.stem}")

        return DocumentMetadata(
            name=name,
            document_id=document_id,
            document_type=self.document_type(),
            description=data.get("description"),
            version=data.get("version"),
            creator=data.get("author") or data.get("creator"),
            file_path=file_path,
            custom_attributes={
                k: v
                for k, v in data.items()
                if k not in ["name", "id", "description", "version", "author", "creator"]
            },
        )

    def _parse_pipeline(self, data: dict[str, Any], doc_id: str) -> dict[str, Any]:
        """Parses pipeline configuration."""
        components: list[Component] = []
        dependencies: list[Dependency] = []

        # Extract stages from 'pipeline' or 'stages' key
        stages = data.get("pipeline", data.get("stages", []))

        for idx, stage in enumerate(stages):
            if isinstance(stage, dict):
                stage_id = f"{doc_id}_stage_{idx}"
                component = Component(
                    name=stage.get("name", f"Stage{idx}"),
                    component_id=stage_id,
                    component_type=stage.get("type", "stage"),
                    description=stage.get("description"),
                    properties=stage,
                )
                components.append(component)

                # Add dependency to previous stage
                if idx > 0:
                    prev_stage_id = f"{doc_id}_stage_{idx-1}"
                    dependencies.append(
                        Dependency(
                            from_id=prev_stage_id,
                            to_id=stage_id,
                            dependency_type="sequential",
                        )
                    )

        return {"components": components, "dependencies": dependencies}

    def _parse_etl_jobs(self, data: dict[str, Any], doc_id: str) -> dict[str, Any]:
        """Parses ETL job definitions."""
        components: list[Component] = []
        dependencies: list[Dependency] = []

        jobs = data.get("jobs", data.get("tasks", []))

        for job in jobs:
            if isinstance(job, dict):
                job_id = job.get("id", f"{doc_id}_{job.get('name', 'unknown')}")
                component = Component(
                    name=job.get("name", "Unknown Job"),
                    component_id=job_id,
                    component_type=job.get("type", "etl_job"),
                    description=job.get("description"),
                    source_code=job.get("sql") or job.get("script"),
                    properties=job,
                )
                components.append(component)

                # Extract dependencies
                depends_on = job.get("depends_on", job.get("dependencies", []))
                for dep in depends_on:
                    dep_id = dep if isinstance(dep, str) else dep.get("id")
                    if dep_id:
                        dependencies.append(
                            Dependency(
                                from_id=dep_id,
                                to_id=job_id,
                                dependency_type="depends_on",
                            )
                        )

        return {"components": components, "dependencies": dependencies}

    def _parse_schema(self, data: dict[str, Any]) -> dict[str, Any]:
        """Parses data schema definitions."""
        entities: list[DataEntity] = []

        schema = data.get("schema", {})
        tables = schema.get("tables", data.get("tables", []))

        for table in tables:
            if isinstance(table, dict):
                entity = DataEntity(
                    name=table.get("name", "Unknown"),
                    entity_type="table",
                    schema_name=table.get("schema"),
                    database_name=table.get("database"),
                    description=table.get("description"),
                    columns=[
                        col.get("name") if isinstance(col, dict) else col
                        for col in table.get("columns", [])
                    ],
                    properties=table,
                )
                entities.append(entity)

        return {"entities": entities}

    def _parse_datasources(self, data: dict[str, Any]) -> list[DataSource]:
        """Parses data source configurations."""
        sources: list[DataSource] = []

        datasources = data.get("connections", data.get("datasources", []))

        for ds in datasources:
            if isinstance(ds, dict):
                source = DataSource(
                    name=ds.get("name", "Unknown"),
                    source_id=ds.get("id", ds.get("name", "unknown")),
                    source_type=ds.get("type", "database"),
                    connection_string=ds.get("connection_string") or ds.get("url"),
                    server=ds.get("server") or ds.get("host"),
                    database=ds.get("database"),
                    description=ds.get("description"),
                    properties=ds,
                )
                sources.append(source)

        return sources

    def _parse_parameters(self, data: dict[str, Any]) -> list[Parameter]:
        """Parses parameters/variables."""
        params: list[Parameter] = []

        parameters = data.get("parameters", data.get("variables", {}))

        if isinstance(parameters, dict):
            for key, value in parameters.items():
                param = Parameter(
                    name=key,
                    value=value if not isinstance(value, dict) else value.get("value"),
                    data_type=value.get("type") if isinstance(value, dict) else type(value).__name__,
                    description=value.get("description") if isinstance(value, dict) else None,
                )
                params.append(param)

        return params

    def _parse_generic(self, data: dict[str, Any], doc_id: str) -> dict[str, Any]:
        """Parses generic JSON structure."""
        components: list[Component] = []

        # Create a component for the root document
        component = Component(
            name=data.get("name", "Root"),
            component_id=f"{doc_id}_root",
            component_type="json_object",
            description="Root JSON object",
            properties=data,
        )
        components.append(component)

        return {"components": components}

    def extract_data_entities(self, component: Component) -> list[DataEntity]:
        """Extracts data entities referenced in component properties."""
        entities: list[DataEntity] = []

        # Check for table references in properties
        if "tables" in component.properties:
            tables = component.properties["tables"]
            if isinstance(tables, list):
                for table in tables:
                    if isinstance(table, str):
                        entities.append(
                            DataEntity(
                                name=table,
                                entity_type="table",
                            )
                        )

        return entities
