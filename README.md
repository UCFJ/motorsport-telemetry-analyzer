# Motorsport Telemetry Performance Analyzer

A Windows desktop telemetry analysis application for Assetto Corsa Competizione (ACC).

The application records ACC shared-memory telemetry, loads recorded sessions, compares completed valid laps, visualizes driver inputs and racing lines, calculates engineering observations, and presents concise engineer-facing summaries.

The project is designed as an analysis and interpretation tool. It does not prescribe driving advice or make causal claims about driver performance.

## Features

* ACC shared-memory telemetry recording
* Timestamped CSV session files
* Completed-lap and validity handling
* Preservation of original local lap IDs
* Abandoned-lap-safe completion association
* Dynamic valid-lap list
* Dynamic analysis-section list
* Automatic fastest valid completed lap as the initial reference
* Independently selectable Reference and Compare laps
* Pair only visibility mode
* Track-agnostic automatic section detection
* Section-specific telemetry zoom
* Speed, Brake, and Throttle plots shown by default
* Optional Delta, Steering, Racing-Line Deviation, and Racing Line channels
* Lazy analysis cache keyed by ordered Reference and Compare pairs
* Raw engineering observation view
* Concise Summary view
* Scrollable lap list for larger sessions
* Packaged Windows desktop application

V1 analyzes recorded sessions offline. Live telemetry analysis is outside the current scope.

## Windows Release

A packaged Windows build is available from the repository's GitHub Releases page.

Download the Windows x64 release archive:

```text
MotorsportTelemetryAnalyzer-v1.0.0-Windows-x64.zip
```

Extract the entire archive, then run:

```text
MotorsportTelemetryAnalyzer.exe
```

Keep the `_internal` directory next to the executable. It contains the runtime libraries required by the application.

The packaged application does not require a separate Python installation.

Recorded sessions default to:

```text
Documents\Motorsport Telemetry Analyzer\Sessions
```

A different recording folder can be selected from the application.

## Telemetry Pipeline

```text
ACC shared memory
        |
        v
shared_memory_logger.py
        |
        v
acc_session_YYYYMMDD_HHMMSS.csv
        |
        v
Session validation and lap preparation
        |
        v
Spatial lap alignment
        |
        v
Track-agnostic section detection
        |
        v
Function 2 observations
        |
        v
Function 3 conclusions
        |
        v
PySide6 desktop interface
```

Analysis uses 5000 common-position alignment points.

Plotting may downsample aligned arrays for display performance, but engineering calculations use the full aligned resolution.

## Lap Completion and Validity

The telemetry logger maintains local lap IDs, which are preserved during analysis and may be non-contiguous.

ACC's `completed_laps` counter is treated as a completion event source. Local lap boundaries are matched to nearby ACC completion events rather than assuming that the local lap number and ACC completed-lap count are identical.

This allows abandoned or non-counted laps to exist without preventing later completed laps from being recognized correctly.

Invalid or incomplete laps cannot become reference laps.

A valid completed lap is not rejected simply because it is slower than the other laps in the session.

## Section Detection

Analysis sections are inferred automatically from the reference lap.

The detector uses:

* trajectory curvature
* distance between detected regions
* steering activity
* throttle behavior
* brake behavior
* directional continuity

The section detector is track-agnostic. It does not contain Monza-specific corner definitions, track-position rules, or a fixed section count.

Detected boundaries are analytical approximations rather than track-database definitions. V1 does not attempt to name corners or guarantee identical section boundaries for every circuit and recording.

## Observation Model

The analysis architecture separates engineering measurements from presentation wording.

### Function 2: Engineering Observations

Implemented in:

```text
src/analysis/observations.py
```

Function 2 is the source of truth for calculated engineering measurements.

Current observations include:

### Time and Speed

* section delta
* minimum-speed difference
* section-end speed difference

### Braking

* brake application count
* initial brake onset difference
* final brake release difference

### Throttle

* throttle application count
* coasting distance
* final throttle application onset difference
* full or high-throttle commitment difference
* post-full-throttle lift count

### Racing Line

* signed lateral deviation from the reference lap

### Function 3: Engineer-Facing Conclusions

Implemented in:

```text
src/analysis/conclusions.py
```

Function 3 converts existing Function 2 values into concise presentation text.

It may filter insignificant values, apply display thresholds, round values, and organize observations into readable groups.

It does not inspect telemetry arrays or calculate new telemetry metrics.

## Application Workflow

1. Launch the application.
2. Optionally choose a telemetry recording folder.
3. Start logging while ACC is running.
4. Complete the desired driving session.
5. Stop logging.
6. Open the recorded CSV session.
7. The fastest valid completed lap becomes the initial Reference.
8. Choose another valid lap as Compare.
9. Select an analysis section when section-specific detail is required.
10. Switch between Raw and Summary views.
11. Toggle telemetry channels and lap visibility as needed.

### Pair Only

Pair only is enabled by default.

When enabled, visibility is restricted to the selected Reference and Compare laps.

Reference and Compare selection remains independent from individual plot visibility, so either lap can still be hidden manually.

Turning Pair only off restores the previous normal lap-visibility state.

## Running From Source

The application is Windows-focused because ACC and its shared-memory interface run on Windows.

### Requirements

* Windows
* Python 3
* Assetto Corsa Competizione for recording new telemetry

ACC is not required when opening and analyzing an existing compatible CSV recording.

### Setup

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

### Launch the Application

```powershell
python -m src.ui.app
```

Or use the virtual-environment interpreter directly:

```powershell
.venv\Scripts\python.exe -m src.ui.app
```

### Run the Logger Independently

```powershell
python -m src.ingestion.shared_memory_logger
```

Press `Ctrl+C` to stop the standalone logger.

The desktop application starts and stops the logger automatically through its Logging controls.

## Building the Windows Application

The Windows application is packaged with PyInstaller.

From the project root:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm MotorsportTelemetryAnalyzer.spec
```

The resulting application is created at:

```text
dist\MotorsportTelemetryAnalyzer\MotorsportTelemetryAnalyzer.exe
```

The build uses PyInstaller's onedir format.

Repository documentation, sample telemetry sessions, Git metadata, development files, and legacy experiment data are not included as application runtime data.

The Windows executable uses an embedded `.ico` resource, while the PySide6 application uses a bundled PNG version of the same icon for the title bar and taskbar.

## Project Structure

```text
telemetry_analyzer.py
MotorsportTelemetryAnalyzer.spec

assets/
  telemetry_analyzer.svg
  telemetry_analyzer.ico
  telemetry_analyzer.png

src/
  analysis/
    shared_memory_laps.py
    lap_alignment.py
    section_detection.py
    observations.py
    conclusions.py
    session_loader.py

  ingestion/
    shared_memory_logger.py
    shared_memory_loader.py
    paths.py

  ui/
    app.py
    main_window.py
    styles.py
```

### Key Modules

`shared_memory_laps.py`
Prepares sessions, aligns valid laps, constructs the telemetry viewer, and performs lazy ordered-pair analysis.

`lap_alignment.py`
Aligns laps to a common normalized track-position axis and calculates lap deltas and racing-line deviation.

`section_detection.py`
Detects and groups track-agnostic analysis sections from reference-lap geometry and driver inputs.

`observations.py`
Implements Function 2 engineering measurements.

`conclusions.py`
Implements Function 3 presentation wording.

`session_loader.py`
Creates isolated session-analysis instances and supports transactional session replacement.

`shared_memory_logger.py`
Records ACC shared-memory telemetry to CSV.

`main_window.py`
Implements the PySide6 desktop interface, session lifecycle, logging controls, lap visibility, comparison selection, and analysis display.

## V1 Limitations

* Analysis is recorded-session based.
* Live telemetry analysis is not included.
* The runtime accepts telemetry recorded from ACC shared memory.
* Section boundaries are inferred rather than supplied by a circuit database.
* Detected sections are analytical approximations.
* There is no automated driving recommendation system.
* There is no causal diagnosis engine.
* Turn-in detection is not included in v1.
* MoTeC `.ld` and `.ldx` files are not required or used by the v1 application runtime.
* Legacy and experimental MoTeC-related code may remain in the repository outside the v1 application path.

## V1 Status

V1 is complete.

The current release includes:

* telemetry acquisition
* completed-lap handling
* lap alignment
* automatic section detection
* telemetry visualization
* racing-line comparison
* engineering observations
* engineer-facing summaries
* session management
* integrated logging controls
* packaged Windows distribution

The project has been regression-tested against recorded ACC sessions, including sessions containing abandoned laps and non-contiguous valid lap IDs.

Further development, including live analysis and additional driver-performance analysis features, is reserved for future versions.
