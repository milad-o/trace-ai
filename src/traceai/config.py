"""Configuration management for Enterprise Assistant."""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM Configuration
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    default_model: str = Field(
        default="anthropic:claude-3-7-sonnet-latest", alias="DEFAULT_MODEL"
    )

    # Graph Storage Configuration (NetworkX - pure Python)
    graph_storage_path: Path = Field(
        default=Path("./data/graph.pkl"), alias="GRAPH_STORAGE_PATH"
    )

    # ChromaDB Configuration
    chroma_persist_dir: Path = Field(
        default=Path("./data/chromadb"), alias="CHROMA_PERSIST_DIR"
    )
    chroma_collection_name: str = Field(
        default="ssis_packages", alias="CHROMA_COLLECTION_NAME"
    )

    # Application Settings
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    ssis_packages_dir: Path = Field(
        default=Path("./examples/sample_packages"), alias="SSIS_PACKAGES_DIR"
    )

    # Agent Configuration
    max_iterations: int = Field(default=50, alias="MAX_ITERATIONS")
    agent_timeout: int = Field(default=300, alias="AGENT_TIMEOUT")

    # Development Settings
    debug: bool = Field(default=False, alias="DEBUG")
    enable_human_in_loop: bool = Field(default=True, alias="ENABLE_HUMAN_IN_LOOP")

    @property
    def is_anthropic_configured(self) -> bool:
        """Check if Anthropic API key is configured."""
        return self.anthropic_api_key is not None and len(self.anthropic_api_key) > 0

    @property
    def is_openai_configured(self) -> bool:
        """Check if OpenAI API key is configured."""
        return self.openai_api_key is not None and len(self.openai_api_key) > 0


# Global settings instance
settings = Settings()
