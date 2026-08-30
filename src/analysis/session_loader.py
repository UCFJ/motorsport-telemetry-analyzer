"""Isolated loading of telemetry-analysis session modules."""

import importlib.util
from pathlib import Path


SESSION_MODULE_PATH = Path(__file__).with_name("shared_memory_laps.py")


def load_session_candidate(path: Path):
    """Build and validate an isolated analysis session for one CSV."""
    spec = importlib.util.spec_from_file_location(
        "src.analysis.shared_memory_laps_candidate",
        SESSION_MODULE_PATH,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError("The telemetry session loader is unavailable.")

    candidate = importlib.util.module_from_spec(spec)
    candidate.CSV_FILE = Path(path)

    try:
        spec.loader.exec_module(candidate)
        entries = candidate.get_telemetry_lap_entries()

        if not entries or not any(entry[3] for entry in entries):
            raise ValueError("No usable reference-eligible laps were found.")
    except SystemExit as error:
        detail = str(error) or "no usable laps"
        print(f"SESSION LOAD FAILED: {detail}")
        _close_candidate_figure(candidate)
        raise ValueError("candidate session validation failed") from error
    except Exception as error:
        print(f"SESSION LOAD FAILED: {error}")
        _close_candidate_figure(candidate)
        raise

    return candidate


def _close_candidate_figure(candidate) -> None:
    candidate_figure = getattr(candidate, "fig", None)

    if candidate_figure is not None:
        candidate.plt.close(candidate_figure)
