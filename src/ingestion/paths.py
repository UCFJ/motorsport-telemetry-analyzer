"""Repository-relative paths shared by ingestion and UI code."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def get_default_shared_memory_output_dir() -> Path:
    """Return the movable project default for ACC telemetry recordings."""
    return PROJECT_ROOT / "data" / "raw" / "shared_memory"
