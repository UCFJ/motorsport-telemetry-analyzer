"""Repository-relative paths shared by ingestion and UI code."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def get_default_shared_memory_output_dir() -> Path:
    """Return the movable project default for ACC telemetry recordings."""
    if getattr(sys, "frozen", False):
        return (
            Path.home()
            / "Documents"
            / "Motorsport Telemetry Analyzer"
            / "Sessions"
        )

    return PROJECT_ROOT / "data" / "raw" / "shared_memory"
