# Motorsport Telemetry Performance Analyzer: Project State

## V1 Status

V1 is complete after final automated validation. The application is a recorded-session ACC telemetry analyzer, not a live analysis system or automated driving coach.

Launch command:

```powershell
python -m src.ui.app
```

Windows virtual-environment command:

```powershell
.venv\Scripts\python.exe -m src.ui.app
```

## Current Workflow

1. `src/ingestion/shared_memory_logger.py` records ACC shared-memory data.
2. Recordings are saved as `acc_session_YYYYMMDD_HHMMSS.csv` files.
3. The UI loads and validates a selected session without replacing the current session until commit succeeds.
4. Completed valid laps are spatially aligned to 5000 common-position points.
5. Reference-lap geometry produces track-agnostic analysis sections.
6. The user selects Reference, Compare, and optionally Section.
7. Ordered-pair analysis is calculated lazily and cached.
8. Function 2 measurements appear in Raw mode; Function 3 wording appears in Summary mode.

Analysis is offline. Logging and analysis are independent, so a recording can continue while an existing session is inspected.

## Lap Completion and Eligibility

- Logger-generated local lap IDs are preserved and may be non-contiguous.
- Increases in ACC's `completed_laps` counter provide completion events.
- Local lap boundaries are matched to nearby ACC completion events.
- An abandoned or non-counted lap does not consume the later lap's completion event.
- A final lap without a following boundary is not fabricated as complete.
- Invalid or incomplete laps cannot become reference laps.
- Slow valid completed laps remain eligible; no performance-delta filter rejects them.
- The fastest valid completed lap becomes the initial reference after loading.

## Section Detection

Sections are inferred from reference-lap geometry and driving-control continuity. The pipeline uses curvature, distance gaps, steering, throttle, brake behavior, braking zones, and exit recovery.

The detector is track-agnostic. It contains no track names, corner names, fixed normalized-position ranges, or fixed section count.

## Application Architecture

### Function 1: Viewer

- PySide6 three-panel desktop interface
- Embedded Matplotlib telemetry viewer
- Speed, Brake, and Throttle visible by default
- Optional Delta, Steering, Racing-Line Deviation, and Racing Line channels
- Dynamic valid-lap and section controls
- Independently scrollable lap-row area
- Reference, Compare, and Section controls remain fixed outside that area
- Pair only enabled by default after session load
- Section zoom, full-lap restore, pan, and zoom

Reference and Compare selection controls analysis identity. Plot checkboxes control visibility independently. Pair only temporarily restricts visibility to the selected pair and restores normal per-lap visibility when disabled.

### Function 2: Observations

File: `src/analysis/observations.py`

Function 2 is the numerical source of truth. It calculates section time and speed differences, brake and throttle events, coasting, throttle commitment and lift behavior, and signed racing-line deviation.

### Function 3: Conclusions

File: `src/analysis/conclusions.py`

Function 3 is a presentation layer. It reads Function 2 values, applies display thresholds, rounds values, converts signs into wording, and groups statements. It does not inspect raw telemetry, calculate new engineering metrics, give driving advice, or make causal claims.

### Pair Analysis

Analysis is keyed by the ordered pair `(reference_lap, comparison_lap)`. Selecting a valid pair calculates deltas, line deviation, observations, and conclusions only when that ordered pair is absent from the session cache.

Raw and Summary are two views of the same pair result:

- Raw shows Function 2 measurements.
- Summary shows Function 3 wording.

## Data and Runtime Boundaries

- V1 input is ACC shared-memory CSV telemetry.
- V1 calculations use the full 5000-point spatial alignment.
- `PLOT_STEP` affects display sampling only.
- MoTeC `.ld` and `.ldx` support is not required or used by the v1 runtime.
- Legacy MoTeC and experiment files remain in the repository but are outside the application path.
- The application does not generate driving recommendations or causal diagnoses.

## V2 Candidates

These are possible future directions, not unfinished v1 requirements:

- Live section and session analysis
- Live racing-line analysis
- A validated turn-in detector
- Separate reference, analysis, and display eligibility concepts if needed
- Additional pit and partial-lap handling refinements
- Plot spacing and interaction improvements
- Possible migration from Matplotlib to a more interactive plotting backend
