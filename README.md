# Motorsport Telemetry Performance Analyzer

## Overview

This project is a Windows desktop telemetry analyzer for Assetto Corsa Competizione (ACC). It records ACC shared-memory telemetry to CSV, loads recorded sessions, compares completed valid laps, and presents both raw engineering observations and concise engineer-facing summaries.

The application is an analyzer and interpreter. It does not prescribe driving advice or make causal claims about driver performance.

## V1 Features

- ACC shared-memory telemetry logger and timestamped CSV recording
- Recorded-session loading with schema and telemetry validation
- Completed-lap and validity handling that preserves local lap IDs
- Completion association that does not let abandoned laps block later completed laps
- Dynamic valid-lap and section lists
- Automatic fastest valid completed lap as the initial reference
- Independently selectable Reference and Compare laps
- Pair only visibility mode
- Track-agnostic automatic section detection and section zoom
- Speed, Brake, and Throttle plots shown by default
- Optional Delta, Steering, Racing-Line Deviation, and Racing Line channels
- Lazy cache keyed by ordered Reference and Compare pairs
- Raw observation and Summary views
- Independently scrollable lap rows for large sessions

V1 analyzes recorded sessions offline. It does not perform live telemetry analysis.

## Telemetry Pipeline

```text
ACC shared memory
  -> src/ingestion/shared_memory_logger.py
  -> acc_session_YYYYMMDD_HHMMSS.csv
  -> session validation and lap preparation
  -> spatial alignment
  -> track-agnostic section detection
  -> Function 2 observations
  -> Function 3 conclusions
  -> PySide6 interface
```

Analysis uses 5000 common-position alignment points. Plotting may downsample those arrays for display, but engineering calculations use the full aligned resolution.

## Lap Completion and Validity

The logger's local lap IDs are preserved and may be non-contiguous. Increases in ACC's `completed_laps` counter are treated as completion events and matched to recorded local lap boundaries. An abandoned or non-counted lap therefore does not prevent a later completed lap from being recognized.

Invalid or incomplete laps cannot become reference laps. A valid completed lap is not rejected merely because it is slower than other laps.

## Section Detection

Sections are inferred from the reference lap using trajectory curvature, gap continuity, steering, throttle, and brake behavior. The detector is track-agnostic and contains no Monza-specific corner definitions or fixed section count.

Detected boundaries are analytical approximations. V1 does not name corners or promise perfect boundaries on every circuit and recording.

## Observation Model

Function 2, implemented in `src/analysis/observations.py`, is the source of truth for engineering measurements. Function 3, implemented in `src/analysis/conclusions.py`, converts existing Function 2 values into concise presentation text and does not calculate new telemetry metrics.

Current observations include:

- Time and speed: section delta, minimum-speed difference, and section-end speed difference
- Braking: application count, initial onset difference, and final release difference
- Throttle: application count, coasting distance, final application onset, full/high-throttle commitment, and post-full-throttle lifts
- Racing line: signed lateral deviation from the reference lap

## UI Workflow

1. Launch the application.
2. Optionally choose the logger output folder.
3. Start logging while ACC is running.
4. Stop logging after the driving session.
5. Open the recorded CSV session.
6. The fastest valid completed lap becomes the initial reference.
7. Choose a comparison lap.
8. Choose an analysis section when section-specific detail is wanted.
9. Switch between Raw measurements and Summary wording.
10. Toggle plot channels and lap visibility as needed.

Pair only is enabled by default and limits visible laps to the selected Reference and Compare pair. Turning it off restores normal per-lap visibility controls.

## Installation

The v1 application is Windows-focused because ACC and its shared-memory interface run on Windows.

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

ACC must be running to record new telemetry. ACC is not required to inspect an existing compatible CSV recording.

## Running

Launch the desktop application:

```powershell
python -m src.ui.app
```

On Windows, the virtual-environment interpreter can be used directly:

```powershell
.venv\Scripts\python.exe -m src.ui.app
```

The logger can also run independently:

```powershell
python -m src.ingestion.shared_memory_logger
```

Press `Ctrl+C` to stop the standalone logger. The desktop application starts and stops the same logger through its UI controls.

## Project Structure

```text
src/
  analysis/
    shared_memory_laps.py   Session preparation, plots, and pair analysis
    section_detection.py    Geometry-based analysis sections
    observations.py         Function 2 engineering measurements
    conclusions.py          Function 3 presentation wording
  ingestion/
    shared_memory_logger.py ACC shared-memory CSV recorder
    shared_memory_loader.py CSV reader
  ui/
    app.py                  Application entry point
    main_window.py          PySide6 interface and session lifecycle
```

## V1 Limitations

- Analysis is offline and recorded-session based.
- The v1 runtime accepts ACC shared-memory CSV data.
- Section boundaries are inferred rather than supplied by a track database.
- There is no automated driving recommendation or causal diagnosis engine.
- There is no turn-in detector in v1.
- MoTeC `.ld` and `.ldx` files are not required or used by the v1 application runtime. Legacy and experimental MoTeC code remains in the repository outside the v1 path.

## Status

V1 is feature-complete and stable against the repository's current regression sessions and automated checks. Manual application smoke testing is recommended before creating the final v1 commit.
