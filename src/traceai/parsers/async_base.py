"""Async base parser for concurrent file processing.

This module provides async versions of parsers for improved performance
when processing multiple files concurrently.
"""

import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import aiofiles

from traceai.parsers.base import ParsedDocument


class AsyncBaseParser(ABC):
    """
    Abstract base class for async parsers.

    Provides async file reading and parsing capabilities for concurrent processing.
    """

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of file extensions this parser supports (e.g., ['.dtsx', '.json'])."""
        pass

    @property
    @abstractmethod
    def document_type(self):
        """Return the DocumentType this parser handles."""
        pass

    async def parse(self, file_path: Path | str) -> ParsedDocument:
        """
        Parse a document asynchronously.

        Args:
            file_path: Path to the file to parse

        Returns:
            ParsedDocument object with metadata, components, and dependencies
        """
        file_path = Path(file_path)

        # Read file content asynchronously
        content = await self._read_file(file_path)

        # Parse content (subclasses override this)
        return await self._parse_content(content, file_path)

    async def _read_file(self, file_path: Path) -> str | bytes:
        """
        Read file content asynchronously.

        Args:
            file_path: Path to file

        Returns:
            File content as string or bytes
        """
        # For text files
        if file_path.suffix in ['.json', '.csv', '.jcl', '.cbl', '.CBL', '.sql', '.py']:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                return await f.read()

        # For binary files (Excel, etc.)
        async with aiofiles.open(file_path, 'rb') as f:
            return await f.read()

    @abstractmethod
    async def _parse_content(self, content: str | bytes, file_path: Path) -> ParsedDocument:
        """
        Parse file content into ParsedDocument.

        Subclasses must implement this method.

        Args:
            content: File content (string or bytes)
            file_path: Path to the file

        Returns:
            ParsedDocument object
        """
        pass


async def parse_files_concurrently(
    file_paths: list[Path],
    parser_registry: Any,
    max_concurrent: int = 10
) -> list[ParsedDocument]:
    """
    Parse multiple files concurrently using appropriate parsers.

    Args:
        file_paths: List of file paths to parse
        parser_registry: Parser registry to get parsers from
        max_concurrent: Maximum number of concurrent parse operations

    Returns:
        List of ParsedDocument objects
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def parse_with_semaphore(file_path: Path) -> ParsedDocument | None:
        async with semaphore:
            parser = parser_registry.get_parser_for_file(file_path)
            if parser and hasattr(parser, 'parse_async'):
                try:
                    return await parser.parse_async(file_path)
                except Exception as e:
                    print(f"Error parsing {file_path}: {e}")
                    return None
            elif parser:
                # Fallback to sync parser in executor
                loop = asyncio.get_event_loop()
                try:
                    return await loop.run_in_executor(None, parser.parse, file_path)
                except Exception as e:
                    print(f"Error parsing {file_path}: {e}")
                    return None
            return None

    tasks = [parse_with_semaphore(fp) for fp in file_paths]
    results = await asyncio.gather(*tasks)

    return [r for r in results if r is not None]
