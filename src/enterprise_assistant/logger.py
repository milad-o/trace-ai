"""Logging configuration for the Enterprise Assistant."""

import logging
from pathlib import Path
from rich.logging import RichHandler

# Create logs directory if it doesn't exist
logs_dir = Path("./logs")
logs_dir.mkdir(exist_ok=True)

# Configure logging with Rich for clean terminal output
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(
            rich_tracebacks=True,
            show_time=True,
            show_path=False,
            markup=True
        ),
        logging.FileHandler(logs_dir / "enterprise_assistant.log"),
    ],
)

logger = logging.getLogger("enterprise_assistant")

# Silence noisy HTTP logs from OpenAI/Anthropic
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)
