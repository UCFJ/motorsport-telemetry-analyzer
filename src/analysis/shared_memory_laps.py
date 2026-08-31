from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import to_hex

from src.ingestion.shared_memory_loader import load_shared_memory_csv
from src.analysis.lap_alignment import (
    align_laps,
    calculate_deltas,
    calculate_line_deviation
)
from src.analysis.section_detection import (
    calculate_reference_geometry,
    detect_corner_sections,
    analyze_section_gaps,
    detect_braking_zones,
    group_corner_regions,
    build_analysis_sections,
    extend_section_exits
)

from src.analysis.observations import (
    calculate_section_observations
)

from src.analysis.conclusions import (
    analyze_section_conclusion
)



from matplotlib.widgets import MultiCursor





PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "shared_memory"
)

CSV_FILE = Path(
    globals().get(
        "CSV_FILE",
        DATA_DIR / "acc_session_20260813_035056.csv",
    )
)
from src.analysis.session_loader import load_session_candidate


def apply_dark_style(fig, ax):
    fig.patch.set_facecolor("black")
    ax.set_facecolor("black")

    ax.tick_params(colors="white")

    ax.xaxis.label.set_color("white")
    ax.yaxis.label.set_color("white")
    ax.title.set_color("white")

    for spine in ax.spines.values():
        spine.set_color("white")

    ax.grid(alpha=0.2)


def style_legend(legend):
    legend.get_frame().set_facecolor("black")
    legend.get_frame().set_edgecolor("white")

    for text in legend.get_texts():
        text.set_color("white")


def format_lap_time(milliseconds):
    total_seconds = milliseconds / 1000

    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60

    return f"{minutes}:{seconds:06.3f}"


REQUIRED_SESSION_COLUMNS = (
    "timestamp_s",
    "lap_number",
    "is_valid_lap",
    "completed_laps",
    "acc_last_lap_ms",
    "normalized_position",
    "speed_kmh",
    "brake",
    "throttle",
    "steering",
    "lap_time_s",
    "world_x",
    "world_z",
)

ALIGNMENT_COLUMNS = (
    "normalized_position",
    "speed_kmh",
    "brake",
    "throttle",
    "steering",
    "lap_time_s",
    "world_x",
    "world_z",
)

COMPLETION_EVENT_WINDOW_S = 1.0


def prepare_session_rows(session_df):
    """Validate required fields and discard rows without a real lap identifier."""
    if "lap_number" not in session_df.columns:
        raise ValueError("missing lap_number")

    if "is_valid_lap" not in session_df.columns:
        raise ValueError("missing is_valid_lap")

    missing_columns = [
        column
        for column in REQUIRED_SESSION_COLUMNS
        if column not in session_df.columns
    ]

    if missing_columns:
        raise ValueError(
            "missing required telemetry columns: "
            + ", ".join(missing_columns)
        )

    lap_numbers = pd.to_numeric(
        session_df["lap_number"],
        errors="coerce",
    )
    usable_identifiers = (
        lap_numbers.notna()
        & np.isfinite(lap_numbers)
        & (lap_numbers == np.floor(lap_numbers))
    )
    skipped_rows = int((~usable_identifiers).sum())

    if skipped_rows:
        print(
            "SESSION LOAD: skipped "
            f"{skipped_rows} row(s) with invalid lap identifiers"
        )

    prepared_df = session_df.loc[usable_identifiers].copy()

    if prepared_df.empty:
        raise ValueError("no usable lap identifiers")

    prepared_df["lap_number"] = (
        lap_numbers.loc[usable_identifiers].astype(int)
    )
    prepared_df["timestamp_s"] = pd.to_numeric(
        prepared_df["timestamp_s"],
        errors="coerce",
    )
    prepared_df["completed_laps"] = pd.to_numeric(
        prepared_df["completed_laps"],
        errors="coerce",
    )
    prepared_df["acc_last_lap_ms"] = pd.to_numeric(
        prepared_df["acc_last_lap_ms"],
        errors="coerce",
    )
    return prepared_df


def prepare_lap_rows(lap):
    """Return finite rows usable by the existing alignment pipeline."""
    if lap.empty:
        return lap, False

    validity = lap["is_valid_lap"]
    is_valid = bool(validity.notna().all() and validity.all())
    numeric_telemetry = lap[list(ALIGNMENT_COLUMNS)].apply(
        pd.to_numeric,
        errors="coerce",
    )
    usable_rows = np.isfinite(numeric_telemetry).all(axis=1)
    prepared_lap = lap.loc[usable_rows].copy()
    prepared_lap.loc[:, list(ALIGNMENT_COLUMNS)] = (
        numeric_telemetry.loc[usable_rows]
    )
    has_usable_samples = (
        len(prepared_lap) >= 2
        and prepared_lap["normalized_position"].nunique() >= 2
    )
    return prepared_lap.reset_index(drop=True), is_valid and has_usable_samples


def detect_acc_completion_events(session_df):
    """Return usable rows where ACC's completed-lap counter increases."""
    events = []
    previous_completed_laps = None

    for timestamp, completed_laps, lap_time_ms in session_df[
        ["timestamp_s", "completed_laps", "acc_last_lap_ms"]
    ].itertuples(index=False, name=None):
        if pd.isna(completed_laps) or not np.isfinite(completed_laps):
            continue

        if (
            previous_completed_laps is not None
            and completed_laps > previous_completed_laps
            and pd.notna(timestamp)
            and np.isfinite(timestamp)
            and pd.notna(lap_time_ms)
            and np.isfinite(lap_time_ms)
            and 0 < lap_time_ms < 2147483647
        ):
            events.append(
                {
                    "timestamp_s": float(timestamp),
                    "completed_laps": int(completed_laps),
                    "lap_time_ms": int(lap_time_ms),
                }
            )

        previous_completed_laps = completed_laps

    return events


def detect_local_lap_boundaries(session_df):
    """Map each recorded local lap ID to its following transition timestamp."""
    boundaries = {}
    previous_lap_number = None

    for timestamp, lap_number in session_df[
        ["timestamp_s", "lap_number"]
    ].itertuples(index=False, name=None):
        if previous_lap_number is None:
            previous_lap_number = lap_number
            continue

        if lap_number == previous_lap_number:
            continue

        if pd.notna(timestamp) and np.isfinite(timestamp):
            boundaries.setdefault(previous_lap_number, float(timestamp))

        previous_lap_number = lap_number

    return boundaries


def match_completion_event(
    boundary_timestamp,
    completion_events,
    used_event_indexes,
):
    """Choose the nearest unused ACC event within the boundary tolerance."""
    candidates = [
        (
            abs(event["timestamp_s"] - boundary_timestamp),
            event_index,
            event,
        )
        for event_index, event in enumerate(completion_events)
        if event_index not in used_event_indexes
        and abs(event["timestamp_s"] - boundary_timestamp)
        <= COMPLETION_EVENT_WINDOW_S
    ]

    if not candidates:
        return None

    _distance, event_index, event = min(
        candidates,
        key=lambda candidate: (candidate[0], candidate[1]),
    )
    used_event_indexes.add(event_index)
    return event


df = load_shared_memory_csv(CSV_FILE)
df = prepare_session_rows(df)

completion_events = detect_acc_completion_events(df)
local_lap_boundaries = detect_local_lap_boundaries(df)
local_lap_numbers = sorted(
    int(lap_number)
    for lap_number in df["lap_number"].unique()
    if lap_number >= 1
)


# -------------------------
# Extract completed laps
# -------------------------

laps = {}

for lap_number in local_lap_numbers:

    lap = df[
        df["lap_number"] == lap_number
    ].copy()

    lap = lap.reset_index(
        drop=True
    )

    laps[lap_number] = lap


# -------------------------
# Build lap information
# -------------------------

lap_info = []
used_completion_event_indexes = set()

for lap_number, lap in laps.items():

    lap, is_valid = prepare_lap_rows(lap)
    laps[lap_number] = lap

    boundary_timestamp = local_lap_boundaries.get(lap_number)
    completion_event = (
        match_completion_event(
            boundary_timestamp,
            completion_events,
            used_completion_event_indexes,
        )
        if boundary_timestamp is not None
        else None
    )

    if completion_event is None:
        lap_time_ms = None
    else:
        lap_time_ms = completion_event["lap_time_ms"]

    lap_info.append(
        {
            "lap_number":
                lap_number,

            "lap_time_ms":
                lap_time_ms,

            "is_valid":
                is_valid
        }
    )
# -------------------------
# Find best valid lap
# -------------------------

valid_lap_info = [
    info
    for info in lap_info
    if info["is_valid"] and info["lap_time_ms"] is not None
]

if not valid_lap_info:

    print()
    print(
        "No usable laps found."
    )

    raise SystemExit

best_lap_info = min(
    valid_lap_info,
    key=lambda info: info["lap_time_ms"]
)

best_lap_number = best_lap_info["lap_number"]



# -------------------------
# Align valid laps
# -------------------------

common_position = np.linspace(
    0.0,
    1.0,
    5000
)

aligned_laps = align_laps(
    laps,
    valid_lap_info,
    common_position
)


# -------------------------
# Visualization sampling
# -------------------------

PLOT_STEP = 4

plot_position = (
    common_position[::PLOT_STEP]
    * 100
)

# -------------------------
# Section-detection reference
# -------------------------

reference_line = aligned_laps[
    best_lap_number
]

# -------------------------
# Detect corner sections
# -------------------------

sections, reference_geometry = (
    detect_corner_sections(
        reference_line
    )
)


braking_zones = detect_braking_zones(
    reference_line
)


gap_info = analyze_section_gaps(
    sections,
    reference_line,
    reference_geometry
)

grouped_sections = (
    group_corner_regions(
        sections,
        gap_info
    )
)



analysis_sections = (
    build_analysis_sections(
        grouped_sections,
        braking_zones,
        reference_line,
        reference_geometry
    )
)


analysis_sections = (
    extend_section_exits(
        analysis_sections,
        reference_line,
        reference_geometry
    )
)


# -------------------------
# Telemetry comparison window
# -------------------------

fig = plt.figure(
    figsize=(15, 8.5)
)

grid = fig.add_gridspec(
    6,
    2,
    width_ratios=[3.2, 1.3],
    height_ratios=[
        2.2,
        1.7,
        1.0,
        1.0,
        1.0,
        1.0
    ]
)

ax_speed = fig.add_subplot(
    grid[0, 0]
)

ax_delta = fig.add_subplot(
    grid[1, 0],
    sharex=ax_speed
)

ax_brake = fig.add_subplot(
    grid[2, 0],
    sharex=ax_speed
)

ax_throttle = fig.add_subplot(
    grid[3, 0],
    sharex=ax_speed
)

ax_steering = fig.add_subplot(
    grid[4, 0],
    sharex=ax_speed
)

ax_deviation = fig.add_subplot(
    grid[5, 0],
    sharex=ax_speed
)

ax_line = fig.add_subplot(
    grid[:, 1]
)

apply_dark_style(
    fig,
    ax_line
)

axes = [
    ax_speed,
    ax_delta,
    ax_brake,
    ax_throttle,
    ax_steering,
    ax_deviation
]
fig.patch.set_facecolor("black")

# -------------------------
# Share telemetry X axis
# -------------------------

for ax in axes[1:]:
    ax.sharex(ax_speed)


graph_axes = {
    "Spd": ax_speed,
    "Dlt": ax_delta,
    "Brk": ax_brake,
    "Thr": ax_throttle,
    "Str": ax_steering,
    "Dev": ax_deviation,
    "Line": ax_line
}

graph_weights = {
    "Spd": 2.2,
    "Dlt": 1.7,
    "Brk": 1.0,
    "Thr": 1.0,
    "Str": 1.0,
    "Dev": 1.0
}


# -------------------------
# Consistent lap colors
# -------------------------

color_cycle = [
    "tab:blue",
    "tab:orange",
    "tab:red",
    "tab:purple",
    "tab:brown",
    "tab:pink",
    "tab:gray",
    "tab:cyan"
]

lap_colors = {}
lap_base_colors = {}

color_index = 0

for info in valid_lap_info:

    lap_number = info["lap_number"]

    if lap_number == best_lap_number:
        continue
    else:
        lap_base_colors[lap_number] = (
            color_cycle[
                color_index % len(color_cycle)
            ]
        )
        lap_colors[lap_number] = lap_base_colors[lap_number]

        color_index += 1

lap_base_colors[best_lap_number] = (
    color_cycle[color_index % len(color_cycle)]
)
lap_colors = lap_base_colors.copy()



# -------------------------
# Store plot lines by lap
# -------------------------

lap_lines = {
    info["lap_number"]: []
    for info in valid_lap_info
}
speed_lines = {}


# -------------------------
# Speed comparison
# -------------------------

for info in valid_lap_info:

    lap_number = info["lap_number"]
    aligned = aligned_laps[lap_number]

    label = (
        f"Lap {lap_number} - "
        f"{format_lap_time(info['lap_time_ms'])}"
    )

    if lap_number == best_lap_number:
        line, = ax_speed.plot(
            plot_position,
            aligned["speed_kmh"][::PLOT_STEP],
            label=label + " - BEST",
            color=lap_colors[lap_number],
            linewidth=1.2
        )
        
        lap_lines[lap_number].append(line)
        speed_lines[lap_number] = line
    else:
        line, = ax_speed.plot(
            plot_position,
            aligned["speed_kmh"][::PLOT_STEP],
            label=label,
            linewidth=1.2,
            color=lap_colors[lap_number],
        )
        
        lap_lines[lap_number].append(line)
        speed_lines[lap_number] = line

ax_speed.set_ylabel("Speed (km/h)")
ax_speed.set_title("Speed Comparison")

apply_dark_style(
    fig,
    ax_speed
)

# -------------------------
# Lazy ordered-pair analysis
# -------------------------

def get_or_calculate_pair_analysis(
    analysis_cache,
    reference_lap_number,
    comparison_lap_number
):
    reference_lap_number = int(reference_lap_number)
    comparison_lap_number = int(comparison_lap_number)
    cache_key = (
        reference_lap_number,
        comparison_lap_number
    )

    if cache_key in analysis_cache:
        return analysis_cache[cache_key]

    if (
        reference_lap_number not in aligned_laps
        or comparison_lap_number not in aligned_laps
        or reference_lap_number == comparison_lap_number
    ):
        raise ValueError("Reference and comparison must be different valid laps.")

    pair_laps = {
        reference_lap_number: aligned_laps[reference_lap_number].copy(),
        comparison_lap_number: aligned_laps[comparison_lap_number].copy(),
    }
    pair_deltas = calculate_deltas(
        pair_laps,
        reference_lap_number
    )
    pair_laps = calculate_line_deviation(
        pair_laps,
        reference_lap_number
    )
    pair_reference = pair_laps[reference_lap_number]
    pair_comparison = pair_laps[comparison_lap_number]
    pair_reference_geometry = calculate_reference_geometry(
        pair_reference
    )
    reference_info = next(
        info
        for info in valid_lap_info
        if info["lap_number"] == reference_lap_number
    )
    comparison_info = next(
        info
        for info in valid_lap_info
        if info["lap_number"] == comparison_lap_number
    )
    overall_lap_time_difference_s = (
        comparison_info["lap_time_ms"]
        - reference_info["lap_time_ms"]
    ) / 1000
    observations = [
        calculate_section_observations(
            pair_comparison,
            pair_reference,
            section,
            pair_reference_geometry,
            pair_deltas[comparison_lap_number]
        )
        for section in analysis_sections
    ]
    conclusions = [
        analyze_section_conclusion(observation)
        for observation in observations
    ]

    pair_result = {
        "overall_lap_time_difference_s": overall_lap_time_difference_s,
        "delta": pair_deltas[comparison_lap_number],
        "line_deviation": pair_comparison["line_deviation_m"],
        "observations": observations,
        "conclusions": conclusions,
    }
    analysis_cache[cache_key] = pair_result
    return pair_result


# -------------------------
# Delta comparison
# -------------------------

delta_lines = {}

for info in valid_lap_info:

    lap_number = info["lap_number"]

    line, = ax_delta.plot(
        plot_position,
        np.zeros_like(plot_position),
        label="_nolegend_",
        color=lap_colors[lap_number],
        linewidth=1.5
    )
    line.set_visible(False)
    line._pair_active = False
    
    lap_lines[lap_number].append(line)
    delta_lines[lap_number] = line

ax_delta.axhline(
    0,
    color="white",
    linestyle="--",
    linewidth=1
)

ax_delta.set_ylabel("Delta (s)")
ax_delta.set_ylim(-1.0, 1.0)

ax_delta.set_title(
    "Delta"
)

apply_dark_style(
    fig,
    ax_delta
)

ax_delta.set_visible(False)


# -------------------------
# Brake comparison
# -------------------------

for info in valid_lap_info:

    lap_number = info["lap_number"]
    aligned = aligned_laps[lap_number]

    line, = ax_brake.plot(
        plot_position,
        aligned["brake"][::PLOT_STEP],
        color=lap_colors[lap_number],
        linewidth=1
    )
    
    lap_lines[lap_number].append(line)

ax_brake.set_ylabel("Brake")
ax_brake.set_ylim(-0.05, 1.05)
ax_brake.set_title("Brake Input")

apply_dark_style(
    fig,
    ax_brake
)


# -------------------------
# Throttle comparison
# -------------------------

for info in valid_lap_info:

    lap_number = info["lap_number"]
    aligned = aligned_laps[lap_number]

    line, = ax_throttle.plot(
        plot_position,
        aligned["throttle"][::PLOT_STEP],
        color=lap_colors[lap_number],
        linewidth=1
    )
    
    lap_lines[lap_number].append(line)

ax_throttle.set_xlabel("Track Position (%)")
ax_throttle.set_ylabel("Throttle")
ax_throttle.set_ylim(-0.05, 1.05)
ax_throttle.set_title("Throttle Input")

apply_dark_style(
    fig,
    ax_throttle
)



# -------------------------
# Steering comparison
# -------------------------

for info in valid_lap_info:

    lap_number = info["lap_number"]
    aligned = aligned_laps[lap_number]

    line, = ax_steering.plot(
        plot_position,
        aligned["steering"][::PLOT_STEP],
        color=lap_colors[lap_number],
        linewidth=1
    )

    lap_lines[lap_number].append(line)


ax_steering.axhline(
    0,
    color="white",
    linestyle="--",
    linewidth=0.7,
    alpha=0.5
)

ax_steering.set_ylabel("Steer")
ax_steering.set_title("Steering Input")

apply_dark_style(
    fig,
    ax_steering
)

ax_steering.set_visible(False)


# -------------------------
# Analysis section markers
# -------------------------

for section in analysis_sections:

    start_pct = (
        section["start_position"]
        * 100
    )

    end_pct = (
        section["end_position"]
        * 100
    )

    for ax in axes:

        ax.axvspan(
            start_pct,
            end_pct,
            color="white",
            alpha=0.035,
            zorder=0
        )

    
# -------------------------
# Racing-line deviation
# -------------------------

deviation_lines = {}

for info in valid_lap_info:

    lap_number = info["lap_number"]

    aligned = aligned_laps[
        lap_number
    ]

    line, = ax_deviation.plot(
        plot_position,
        np.zeros_like(plot_position),
        color=lap_colors[lap_number],
        linewidth=1.2,
        label=f"L{lap_number}"
    )
    line.set_visible(False)
    line._pair_active = False

    lap_lines[
        lap_number
    ].append(line)
    deviation_lines[lap_number] = line


ax_deviation.axhline(
    0,
    color="white",
    linestyle="--",
    linewidth=0.8,
    alpha=0.6
)

ax_deviation.set_ylabel(
    "Dev (m)"
)

ax_deviation.set_title(
    "Racing-Line Deviation vs Reference"
)

apply_dark_style(
    fig,
    ax_deviation
)

# Start hidden
ax_deviation.set_visible(False)




# -------------------------
# Racing-line comparison
# -------------------------

for info in valid_lap_info:

    lap_number = info["lap_number"]
    aligned = aligned_laps[lap_number]
    linewidth = 1.2

    line, = ax_line.plot(
        aligned["world_x"],
        aligned["world_z"],
        color=lap_colors[lap_number],
        linewidth=1.2,
        label=f"L{lap_number}"
    )

    lap_lines[lap_number].append(line)


ax_line.set_visible(False)

ax_line.set_title(
    "Racing Line"
)

ax_line.set_xlabel(
    "World X"
)

ax_line.set_ylabel(
    "World Z"
)

ax_line.set_aspect(
    "equal",
    adjustable="datalim"
)

ax_line.invert_yaxis()

apply_dark_style(
    fig,
    ax_line
)


# -------------------------
# Section labels on track map
# -------------------------

track_center_x = (
    np.min(reference_line["world_x"])
    + np.max(reference_line["world_x"])
) / 2


for section in analysis_sections:

    middle_position = (
        section["core_start_position"]
        + section["core_end_position"]
    ) / 2

    middle_index = np.argmin(
        np.abs(
            reference_line["normalized_position"]
            - middle_position
        )
    )

    section_x = reference_line[
        "world_x"
    ][middle_index]

    section_z = reference_line[
        "world_z"
    ][middle_index]


    # -------------------------
    # Put label outside track
    # -------------------------

    if section_x >= track_center_x:

        label_offset = (
            12,
            0
        )

        horizontal_alignment = "left"

    else:

        label_offset = (
            -12,
            0
        )

        horizontal_alignment = "right"


    ax_line.annotate(
        f"S{section['section_number']}",

        xy=(
            section_x,
            section_z
        ),

        xytext=label_offset,

        textcoords="offset points",

        color="white",
        fontsize=9,
        fontweight="bold",

        ha=horizontal_alignment,
        va="center",

        bbox={
            "facecolor": "black",
            "edgecolor": "white",
            "boxstyle": "round,pad=0.2",
            "alpha": 0.8
        },

        annotation_clip=True,
        clip_on=True,
        zorder=10
    )

    



section_label_artists = []


def update_section_labels():

    global section_label_artists

    # Remove old labels
    for label in section_label_artists:
        label.remove()

    section_label_artists = []


    # Find top visible telemetry graph
    visible_axes = [
        ax
        for ax in axes
        if ax.get_visible()
    ]

    if not visible_axes:
        return


    top_ax = visible_axes[0]


    # Add labels to top visible graph
    for section in analysis_sections:

        middle_pct = (
            (
                section["start_position"]
                + section["end_position"]
            )
            / 2
            * 100
        )

        label = top_ax.text(
            middle_pct,
            0.97,
            f"S{section['section_number']}",
            transform=top_ax.get_xaxis_transform(),
            color="white",
            fontsize=8,
            fontweight="bold",
            ha="center",
            va="top",
            clip_on=True,
            zorder=20
        )

        section_label_artists.append(
            label
        )


# -------------------------
# Dynamic graph layout
# -------------------------

TELEMETRY_GAP_MIN = 0.035
TELEMETRY_GAP_MAX = 0.050
TELEMETRY_LABEL_PADDING_PX = 5.0


def calculate_telemetry_gap(visible_axes):
    gap = 0.035

    if len(visible_axes) < 2:
        return gap

    try:
        renderer = fig.canvas.get_renderer()
        canvas_height_px = float(renderer.height)

        if not np.isfinite(canvas_height_px) or canvas_height_px <= 0:
            return gap

        required_gap_px = TELEMETRY_LABEL_PADDING_PX

        for upper_ax, lower_ax in zip(visible_axes, visible_axes[1:]):
            upper_axis_bounds = upper_ax.get_window_extent(renderer)
            lower_axis_bounds = lower_ax.get_window_extent(renderer)
            upper_label_bounds = upper_ax.yaxis.label.get_window_extent(renderer)
            lower_label_bounds = lower_ax.yaxis.label.get_window_extent(renderer)

            bounds = (
                upper_axis_bounds.y0,
                lower_axis_bounds.y1,
                upper_label_bounds.y0,
                lower_label_bounds.y1,
            )

            if not np.all(np.isfinite(bounds)):
                return gap

            upper_bottom_overhang = max(
                0.0,
                upper_axis_bounds.y0 - upper_label_bounds.y0,
            )
            lower_top_overhang = max(
                0.0,
                lower_label_bounds.y1 - lower_axis_bounds.y1,
            )

            required_gap_px = max(
                required_gap_px,
                upper_bottom_overhang
                + lower_top_overhang
                + TELEMETRY_LABEL_PADDING_PX,
            )

        measured_gap = required_gap_px / canvas_height_px
        return float(
            np.clip(
                measured_gap,
                TELEMETRY_GAP_MIN,
                TELEMETRY_GAP_MAX,
            )
        )
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return gap


def reflow_graphs():

    telemetry_axes = {
        name: ax
        for name, ax in graph_axes.items()
        if name != "Line"
    }

    visible_telemetry = [
        (name, ax)
        for name, ax in telemetry_axes.items()
        if ax.get_visible()
    ]

    line_visible = ax_line.get_visible()

    # -------------------------
    # Overall usable area
    # -------------------------

    left = 0.07
    right = 0.97

    bottom = 0.08
    top = 0.96

    # -------------------------
    # Decide horizontal layout
    # -------------------------

    if line_visible and visible_telemetry:

        # Telemetry on left,
        # racing line on right

        telemetry_left = left
        telemetry_right = 0.63

        line_left = 0.67
        line_right = right

    elif line_visible and not visible_telemetry:

        # Racing line gets everything

        line_left = left
        line_right = right

    elif visible_telemetry:

        # No racing line:
        # telemetry gets everything

        telemetry_left = left
        telemetry_right = right

    # -------------------------
    # Layout telemetry graphs
    # -------------------------

    if visible_telemetry:

        gap = calculate_telemetry_gap(
            [ax for name, ax in visible_telemetry]
        )

        total_weight = sum(
            graph_weights[name]
            for name, ax in visible_telemetry
        )

        usable_height = (
            top
            - bottom
            - gap * (
                len(visible_telemetry) - 1
            )
        )

        current_top = top

        for name, ax in visible_telemetry:

            height = (
                usable_height
                * graph_weights[name]
                / total_weight
            )

            current_top -= height

            ax.set_position(
                [
                    telemetry_left,
                    current_top,
                    telemetry_right
                    - telemetry_left,
                    height
                ]
            )

            ax.set_xlabel("")

            ax.tick_params(
                labelbottom=False
            )

            current_top -= gap

        bottom_ax = visible_telemetry[-1][1]

        bottom_ax.set_xlabel(
            "Track Position (%)"
        )

        bottom_ax.tick_params(
            labelbottom=True
        )

    # -------------------------
    # Layout racing-line graph
    # -------------------------

    if line_visible:

        ax_line.set_position(
            [
                line_left,
                bottom,
                line_right - line_left,
                top - bottom
            ]
        )

        ax_line.set_facecolor("black")

    fig.canvas.draw_idle()
    update_section_labels()


cursor = None


def rebuild_cursor():

    global cursor

    # Remove old cursor
    if cursor is not None:

        cursor.disconnect()

        for line in cursor.vlines:
            line.remove()

        for line in cursor.hlines:
            line.remove()

    # Only attach cursor to visible
    # telemetry graphs
    cursor_axes = [
        ax
        for ax in axes
        if ax.get_visible()
    ]

    # All telemetry graphs may be hidden
    if not cursor_axes:

        cursor = None
        fig.canvas.draw_idle()
        return

    cursor = MultiCursor(
        cursor_axes,
        useblit=True,
        horizOn=False,
        vertOn=True,
        color="white",
        linestyle=":",
        linewidth=1
    )

    fig.canvas.draw_idle()

def set_graph_visibility(label, visible):
    ax = graph_axes[label]
    ax.set_visible(visible)

    reflow_graphs()

    if fig.canvas.toolbar is not None:
        fig.canvas.toolbar.update()

    rebuild_cursor()


def set_lap_visibility(lap_number, visible):
    lines = lap_lines[lap_number]

    for line in lines:
        line.set_visible(
            visible
            and (
                line.axes not in (
                    ax_delta,
                    ax_deviation
                )
                or getattr(
                    line,
                    "_pair_active",
                    False
                )
            )
        )

    fig.canvas.draw_idle()


reflow_graphs()


def reflow_graphs_after_resize(_event):
    reflow_graphs()


fig.canvas.mpl_connect(
    "resize_event",
    reflow_graphs_after_resize
)


# -------------------------
# Synchronized cursor
# -------------------------

rebuild_cursor()



def refresh_cursor_after_navigation(event):

    if event.inaxes in axes:
        rebuild_cursor()


fig.canvas.mpl_connect(
    "button_release_event",
    refresh_cursor_after_navigation
)

# -------------------------
# Pause cursor while navigating
# -------------------------

navigation_active = False


def pause_cursor_during_navigation(event):

    global navigation_active

    toolbar = fig.canvas.toolbar

    if (
        toolbar is not None
        and toolbar.mode
        and cursor is not None
    ):

        cursor.disconnect()
        navigation_active = True


def resume_cursor_after_navigation(event):

    global navigation_active

    if not navigation_active:
        return

    navigation_active = False

    rebuild_cursor()



fig.canvas.mpl_connect(
    "button_press_event",
    pause_cursor_during_navigation
)

fig.canvas.mpl_connect(
    "button_release_event",
    resume_cursor_after_navigation
)



def create_telemetry_figure():
    """Return the initialized telemetry viewer figure."""
    return fig


def set_reference_style(reference_lap_number):
    """Apply reference color only; no pair analysis is performed here."""
    for info in valid_lap_info:
        lap_number = info["lap_number"]
        is_reference = lap_number == reference_lap_number
        color = (
            "lime"
            if is_reference
            else lap_base_colors[lap_number]
        )
        lap_colors[lap_number] = color

        for line in lap_lines[lap_number]:
            line.set_color(color)

    fig.canvas.draw_idle()


def clear_pair_analysis_plots():
    """Hide pair-only plot artists without changing lap visibility state."""
    for lap_number in delta_lines:
        delta_lines[lap_number]._pair_active = False
        delta_lines[lap_number].set_visible(False)
        deviation_lines[lap_number]._pair_active = False
        deviation_lines[lap_number].set_visible(False)

    ax_delta.set_title("Delta")
    fig.canvas.draw_idle()


def update_pair_analysis(
    reference_lap_number,
    comparison_lap_number,
    pair_result
):
    """Display cached/calculated data for one ordered comparison pair."""
    reference_info = next(
        info
        for info in valid_lap_info
        if info["lap_number"] == reference_lap_number
    )
    comparison_info = next(
        info
        for info in valid_lap_info
        if info["lap_number"] == comparison_lap_number
    )

    for lap_number in delta_lines:
        is_comparison = lap_number == comparison_lap_number
        lap_is_visible = speed_lines[lap_number].get_visible()
        delta_lines[lap_number]._pair_active = is_comparison
        delta_lines[lap_number].set_visible(
            is_comparison and lap_is_visible
        )
        deviation_lines[lap_number]._pair_active = is_comparison
        deviation_lines[lap_number].set_visible(
            is_comparison and lap_is_visible
        )

    official_delta = (
        comparison_info["lap_time_ms"]
        - reference_info["lap_time_ms"]
    ) / 1000
    delta_lines[comparison_lap_number].set_ydata(
        pair_result["delta"][::PLOT_STEP]
    )
    delta_lines[comparison_lap_number].set_label(
        f"Lap {comparison_lap_number} "
        f"({official_delta:+.3f}s)"
    )
    deviation_lines[comparison_lap_number].set_ydata(
        pair_result["line_deviation"][::PLOT_STEP]
    )

    ax_delta.set_title(
        f"Delta vs Lap {reference_lap_number} - "
        f"{format_lap_time(reference_info['lap_time_ms'])}"
    )
    fig.canvas.draw_idle()


def get_telemetry_lap_legend_entries(reference_lap_number=None):
    """Return lap labels, display colors, and reference status for the Qt UI."""
    return [
        (
            info["lap_number"],
            f"Lap {info['lap_number']}",
            to_hex(lap_colors[info["lap_number"]]),
            info["lap_number"] == reference_lap_number,
        )
        for info in valid_lap_info
    ]


def get_telemetry_lap_entries():
    """Return valid completed lap details for the Qt session lap list."""
    return [
        (
            info["lap_number"],
            (
                format_lap_time(info["lap_time_ms"])
                if info["lap_time_ms"] is not None
                else "NO TIME"
            ),
            (
                "BEST"
                if info["lap_number"] == best_lap_number
                else (
                    f"{(info['lap_time_ms'] - best_lap_info['lap_time_ms']) / 1000:+.3f}"
                    if info["lap_time_ms"] is not None
                    else "NO DELTA"
                )
            ),
            info["lap_number"] == best_lap_number,
        )
        for info in sorted(
            valid_lap_info,
            key=lambda lap: lap["lap_number"]
        )
    ]


def get_telemetry_section_numbers():
    """Return section identifiers in the detector's output order."""
    return [
        section["section_number"]
        for section in analysis_sections
    ]


def get_telemetry_session_display_name():
    """Return a timestamp label derived from the loaded session filename."""
    try:
        session_time = datetime.strptime(
            CSV_FILE.name,
            "acc_session_%Y%m%d_%H%M%S.csv"
        )
    except ValueError:
        return CSV_FILE.stem

    return session_time.strftime("%d %b %Y %H:%M")


default_telemetry_xlim = ax_speed.get_xlim()


def restore_full_lap_view():
    """Restore the initial horizontal range on every telemetry axis."""
    for ax in axes:
        ax.set_xlim(*default_telemetry_xlim)

    fig.canvas.draw_idle()


def zoom_to_analysis_section(section_number, clearance=0.15):
    """Zoom every telemetry axis to a detected section with proportional padding."""
    section = next(
        (
            section
            for section in analysis_sections
            if section["section_number"] == int(section_number)
        ),
        None,
    )

    if section is None:
        return

    section_start = section["start_position"]
    section_end = section["end_position"]
    padding = (section_end - section_start) * clearance
    visible_start = max(common_position[0], section_start - padding) * 100
    visible_end = min(common_position[-1], section_end + padding) * 100

    for ax in axes:
        ax.set_xlim(visible_start, visible_end)

    fig.canvas.draw_idle()


if __name__ == "__main__":
    plt.show()
