"""Isolated loading of telemetry-analysis session modules."""

import importlib.util
from pathlib import Path
from types import CodeType, ModuleType


SESSION_MODULE_NAME = "src.analysis.shared_memory_laps"
CANDIDATE_MODULE_NAME = "src.analysis.shared_memory_laps_candidate"


def _create_session_candidate() -> tuple[ModuleType, CodeType]:
    """Create a fresh module from the installed or bundled analysis code."""
    source_spec = importlib.util.find_spec(SESSION_MODULE_NAME)
    loader = source_spec.loader if source_spec is not None else None
    code = loader.get_code(SESSION_MODULE_NAME) if loader is not None else None

    if source_spec is None or loader is None or code is None:
        raise RuntimeError("The telemetry session loader is unavailable.")

    candidate = ModuleType(CANDIDATE_MODULE_NAME)
    candidate.__file__ = source_spec.origin
    candidate.__loader__ = loader
    candidate.__package__ = source_spec.parent
    candidate.__spec__ = source_spec
    return candidate, code


def load_session_candidate(path: Path):
    """Build and validate an isolated analysis session for one CSV."""
    candidate, code = _create_session_candidate()
    candidate.CSV_FILE = Path(path)

    try:
        exec(code, candidate.__dict__)
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
