from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from src.ingestion.shared_memory_loader import load_shared_memory_csv
from src.analysis.lap_alignment import (
    align_laps,
    calculate_deltas,
    calculate_line_deviation
)
from src.analysis.section_detection import (
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



from matplotlib.widgets import CheckButtons, MultiCursor

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "shared_memory"
)

CSV_FILE = (
    DATA_DIR
    / "acc_session_20260813_035056.csv"
)

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


df = load_shared_memory_csv(CSV_FILE)

max_lap_number = int(
    df["lap_number"].max()
)


# -------------------------
# Extract completed laps
# -------------------------

laps = {}

for lap_number in range(
    1,
    max_lap_number
):

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

for lap_number, lap in laps.items():

    is_valid = (
        lap["is_valid_lap"].all()
    )

    next_lap = df[
        df["lap_number"]
        == lap_number + 1
    ]

    completed_rows = next_lap[
        next_lap["completed_laps"]
        >= lap_number
    ]

    if completed_rows.empty:

        lap_time_ms = None

    else:

        lap_time_ms = int(
            completed_rows[
                "acc_last_lap_ms"
            ].iloc[0]
        )

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
# Print lap summary
# -------------------------

print()
print("Complete laps:")
print("--------------")

for info in lap_info:

    if info["lap_time_ms"] is None:

        lap_time = "NO TIME"

    else:

        lap_time = format_lap_time(
            info["lap_time_ms"]
        )

    validity = (
        "VALID"
        if info["is_valid"]
        else "INVALID"
    )

    print(
        f"Lap {info['lap_number']}: "
        f"{lap_time}  "
        f"{validity}"
    )

# -------------------------
# Find best valid lap
# -------------------------

valid_lap_info = [
    info
    for info in lap_info
    if info["is_valid"]
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

print()
print("Best valid lap:")
print(
    f"Lap {best_lap_number} - "
    f"{format_lap_time(best_lap_info['lap_time_ms'])}"
)



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

aligned_laps = (
    calculate_line_deviation(
        aligned_laps,
        best_lap_number
    )
)

# -------------------------
# Racing-line deviation
# -------------------------

reference_line = aligned_laps[
    best_lap_number
]

reference_x = reference_line[
    "world_x"
]

reference_z = reference_line[
    "world_z"
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


print()
print("Detected cornering sections:")
print("----------------------------")

previous_section = None

for index, section in enumerate(
    sections,
    start=1
):

    if previous_section is None:
        gap_text = ""
    else:
        gap_m = (
            section["start_distance_m"]
            - previous_section["end_distance_m"]
        )

        gap_text = (
            f"| gap {gap_m:.1f} m "
        )

    print(
        f"Section {index}: "
        f"{section['start_position'] * 100:.2f}% "
        f"to "
        f"{section['end_position'] * 100:.2f}% "
        f"| peak "
        f"{section['peak_position'] * 100:.2f}% "
        f"| "
        f"{section['direction']} "
        f"| "
        f"{section['length_m']:.1f} m "
        f"{gap_text}"
    )

    previous_section = section




print()
print("Gap analysis:")
print("-------------")

for gap in gap_info:

    print(
        f"Sections "
        f"{gap['first_section']} -> "
        f"{gap['second_section']} "
        f"| {gap['gap_m']:.1f} m "
        f"| curvature "
        f"{gap['max_curvature']:.5f} "
        f"| steer avg "
        f"{gap['mean_abs_steering']:.3f} "
        f"| steer max "
        f"{gap['max_abs_steering']:.3f} "
        f"| throttle avg "
        f"{gap['mean_throttle']:.2f} "
        f"| throttle min "
        f"{gap['min_throttle']:.2f} "
        f"| brake max "
        f"{gap['max_brake']:.2f}"
    )



print()
print("Reference geometry diagnostic:")
print("------------------------------")

for start_pct in range(
    0,
    40,
    5
):

    end_pct = (
        start_pct + 5
    )

    mask = (
        (
            common_position
            >= start_pct / 100
        )
        &
        (
            common_position
            < end_pct / 100
        )
    )

    curvature_slice = (
        reference_geometry[
            "curvature"
        ][mask]
    )

    speed_slice = (
        reference_line[
            "speed_kmh"
        ][mask]
    )

    brake_slice = (
        reference_line[
            "brake"
        ][mask]
    )

    steering_slice = (
        reference_line[
            "steering"
        ][mask]
    )

    print(
        f"{start_pct:02d}-{end_pct:02d}% "
        f"| curvature max "
        f"{np.max(np.abs(curvature_slice)):.5f} "
        f"| speed min "
        f"{np.min(speed_slice):.1f} "
        f"| brake max "
        f"{np.max(brake_slice):.2f} "
        f"| steer max "
        f"{np.max(np.abs(steering_slice)):.3f}"
    )


print()
print("Detected braking zones:")
print("-----------------------")

for index, zone in enumerate(
    braking_zones,
    start=1
):

    print(
        f"Brake {index}: "
        f"{zone['start_position'] * 100:.2f}% "
        f"to "
        f"{zone['end_position'] * 100:.2f}% "
        f"| "
        f"{zone['length_m']:.1f} m"
    )



print()
print("Grouped cornering regions:")
print("--------------------------")

for group_number, group in enumerate(
    grouped_sections,
    start=1
):

    region_numbers = []

    for region in group:

        region_number = (
            sections.index(region) + 1
        )

        region_numbers.append(
            str(region_number)
        )

    print(
        f"Group {group_number}: "
        f"regions "
        f"{', '.join(region_numbers)} "
        f"| "
        f"{group[0]['start_position'] * 100:.2f}% "
        f"to "
        f"{group[-1]['end_position'] * 100:.2f}%"
    )



print()
print("Analysis sections:")
print("------------------")

for section in analysis_sections:

    if section["has_braking"]:

        brake_position = (
            section["brake_zone"][
                "start_position"
            ]
            * 100
        )

        brake_text = (
            f"brake from "
            f"{brake_position:.2f}%"
        )

    else:

        brake_text = (
            "no braking zone"
        )

    if section[
        "exit_recovery_found"
    ]:

        exit_text = (
            f"exit recovery "
            f"{section['end_position'] * 100:.2f}%"
        )

    else:

        exit_text = (
            "no exit recovery found"
        )

    print(
        f"Section "
        f"{section['section_number']}: "
        f"{section['start_position'] * 100:.2f}% "
        f"to "
        f"{section['end_position'] * 100:.2f}% "
        f"| core "
        f"{section['core_start_position'] * 100:.2f}% "
        f"to "
        f"{section['core_end_position'] * 100:.2f}% "
        f"| {brake_text} "
        f"| {exit_text}"
    )


print()
print("Exit recovery diagnostic:")
print("-------------------------")

for section in analysis_sections:

    core_end = section[
        "core_end_index"
    ]

    print(
        f"Section "
        f"{section['section_number']} "
        f"| core end "
        f"{section['core_end_position'] * 100:.2f}% "
        f"| throttle at core end "
        f"{reference_line['throttle'][core_end]:.3f} "
        f"| brake at core end "
        f"{reference_line['brake'][core_end]:.3f} "
        f"| detected exit "
        f"{section['end_position'] * 100:.2f}% "
        f"| found "
        f"{section['exit_recovery_found']}"
    )
# Direction of reference trajectory
reference_dx = np.gradient(
    reference_x
)

reference_dz = np.gradient(
    reference_z
)

direction_length = np.hypot(
    reference_dx,
    reference_dz
)

direction_length[
    direction_length < 1e-9
] = 1.0


# Perpendicular direction
normal_x = (
    -reference_dz
    / direction_length
)

normal_z = (
    reference_dx
    / direction_length
)


for lap_number, aligned in aligned_laps.items():

    difference_x = (
        aligned["world_x"]
        - reference_x
    )

    difference_z = (
        aligned["world_z"]
        - reference_z
    )

    signed_deviation = (
        difference_x * normal_x
        + difference_z * normal_z
    )

    absolute_deviation = np.hypot(
        difference_x,
        difference_z
    )

    aligned["line_deviation_m"] = (
        signed_deviation
    )

    aligned["line_distance_m"] = (
        absolute_deviation
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

color_index = 0

for info in valid_lap_info:

    lap_number = info["lap_number"]

    if lap_number == best_lap_number:
        lap_colors[lap_number] = "lime"
    else:
        lap_colors[lap_number] = (
            color_cycle[
                color_index % len(color_cycle)
            ]
        )

        color_index += 1



# -------------------------
# Store plot lines by lap
# -------------------------

lap_lines = {
    info["lap_number"]: []
    for info in valid_lap_info
}


# -------------------------
# Speed comparison
# -------------------------

for info in valid_lap_info:

    lap_number = info["lap_number"]
    aligned = aligned_laps[lap_number]

    track_position = (
        aligned["normalized_position"] * 100
    )

    label = (
        f"Lap {lap_number} - "
        f"{format_lap_time(info['lap_time_ms'])}"
    )

    if lap_number == best_lap_number:
        line, = ax_speed.plot(
            track_position,
            aligned["speed_kmh"],
            label=label + " - BEST",
            color=lap_colors[lap_number],
            linewidth=2.5
        )
        
        lap_lines[lap_number].append(line)
    else:
        line, = ax_speed.plot(
            track_position,
            aligned["speed_kmh"],
            label=label,
            linewidth=1.2,
            color=lap_colors[lap_number],
        )
        
        lap_lines[lap_number].append(line)

ax_speed.set_ylabel("Speed (km/h)")
ax_speed.set_title("Speed Comparison")

apply_dark_style(
    fig,
    ax_speed
)

speed_legend = ax_speed.legend()
style_legend(speed_legend)




# -------------------------
# Calculate time delta
# -------------------------

delta_times = calculate_deltas(
    aligned_laps,
    best_lap_number
)



# -------------------------
# Section observations
# -------------------------

all_observations = {}

for info in valid_lap_info:

    lap_number = info[
        "lap_number"
    ]

    if (
        lap_number
        == best_lap_number
    ):
        continue

    aligned = aligned_laps[
        lap_number
    ]

    lap_observations = []

    for section in analysis_sections:

        observation = (
            calculate_section_observations(
                aligned,
                reference_line,
                section,
                reference_geometry,
                delta_times[
                    lap_number
                ]
            )
        )

        lap_observations.append(
            observation
        )

    all_observations[
        lap_number
    ] = lap_observations



print()
print("Section observations:")
print("=====================")

for (
    lap_number,
    observations
) in all_observations.items():

    print()
    print(
        f"Lap {lap_number} "
        f"vs reference "
        f"Lap {best_lap_number}"
    )

    print(
        "-----------------------------"
    )

    for observation in observations:

        print()
        print(
            f"Section "
            f"{observation['section_number']}"
        )

        print(
            f"  Section delta: "
            f"{observation['section_delta_s']:+.3f} s"
        )

        print(
            f"  Minimum speed: "
            f"{observation['min_speed_difference_kmh']:+.1f} km/h"
        )


        # -------------------------
        # Brake behavior
        # -------------------------

        print(
            f"  Brake applications: "
            f"{observation['lap_brake_application_count']} "
            f"(ref "
            f"{observation['reference_brake_application_count']})"
        )

        if (
            observation[
                "brake_onset_difference_m"
            ]
            is None
        ):

            print(
                "  Initial brake onset: "
                "no comparable braking event"
            )

        else:

            print(
                f"  Initial brake onset: "
                f"{observation['brake_onset_difference_m']:+.1f} m"
            )


        if (
            observation[
                "brake_release_difference_m"
            ]
            is None
        ):

            print(
                "  Final brake release: "
                "no comparable braking event"
            )

        else:

            print(
                f"  Final brake release: "
                f"{observation['brake_release_difference_m']:+.1f} m"
            )


        # -------------------------
        # Throttle behavior
        # -------------------------

        print(
            f"  Throttle applications: "
            f"{observation['lap_throttle_application_count']} "
            f"(ref "
            f"{observation['reference_throttle_application_count']})"
        )

        lap_full_lift_text = (
            "Yes"
            if observation["lap_full_lift"]
            else "No"
        )

        reference_full_lift_text = (
            "Yes"
            if observation["reference_full_lift"]
            else "No"
        )

        print(
            f"  Full lift: "
            f"{lap_full_lift_text} "
            f"(ref "
            f"{reference_full_lift_text})"
        )


        if (
            not observation[
                "lap_throttle_interrupted"
            ]
            and
            not observation[
                "reference_throttle_interrupted"
            ]
        ):

            print(
                "  Final throttle commitment: "
                "no throttle interruption"
            )

        elif (
            observation[
                "final_throttle_difference_m"
            ]
            is None
        ):

            print(
                "  Final throttle commitment: "
                "no comparable event"
            )

        else:

            print(
                f"  Final throttle commitment: "
                f"{observation['final_throttle_difference_m']:+.1f} m"
            )


        # -------------------------
        # Racing line
        # -------------------------

        line_deviation = (
            observation[
                "peak_line_deviation_m"
            ]
        )
        
        if line_deviation < 0:
        
            line_direction = "left"
        
        elif line_deviation > 0:
        
            line_direction = "right"
        
        else:
        
            line_direction = "center"
        
        
        print(
            f"  Peak line deviation: "
            f"{abs(line_deviation):.2f} m "
            f"{line_direction}"
        )
# -------------------------
# Delta comparison
# -------------------------

for info in valid_lap_info:

    lap_number = info["lap_number"]

    if lap_number == best_lap_number:
        continue

    official_delta = (
        info["lap_time_ms"]
        - best_lap_info["lap_time_ms"]
    ) / 1000

    line, = ax_delta.plot(
        common_position * 100,
        delta_times[lap_number],
        label=(
            f"Lap {lap_number} "
            f"({official_delta:+.3f}s)"
        ),
        color=lap_colors[lap_number],
        linewidth=1.5
    )
    
    lap_lines[lap_number].append(line)

ax_delta.axhline(
    0,
    color="white",
    linestyle="--",
    linewidth=1
)

ax_delta.set_ylabel("Delta (s)")

ax_delta.set_title(
    f"Delta vs Lap {best_lap_number} - "
    f"{format_lap_time(best_lap_info['lap_time_ms'])}"
)

apply_dark_style(
    fig,
    ax_delta
)

delta_legend = ax_delta.legend()
style_legend(delta_legend)


# -------------------------
# Brake comparison
# -------------------------

for info in valid_lap_info:

    lap_number = info["lap_number"]
    aligned = aligned_laps[lap_number]

    if lap_number == best_lap_number:
        linewidth = 2
    else:
        linewidth = 1
    
    line, = ax_brake.plot(
        common_position * 100,
        aligned["brake"],
        color=lap_colors[lap_number],
        linewidth=linewidth
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

    if lap_number == best_lap_number:
        linewidth = 2
    else:
        linewidth = 1
    
    line, = ax_throttle.plot(
        common_position * 100,
        aligned["throttle"],
        color=lap_colors[lap_number],
        linewidth=linewidth
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

    if lap_number == best_lap_number:
        linewidth = 2
    else:
        linewidth = 1

    line, = ax_steering.plot(
        common_position * 100,
        aligned["steering"],
        color=lap_colors[lap_number],
        linewidth=linewidth
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

for info in valid_lap_info:

    lap_number = info["lap_number"]

    if lap_number == best_lap_number:
        continue

    aligned = aligned_laps[
        lap_number
    ]

    line, = ax_deviation.plot(
        common_position * 100,
        aligned["line_deviation_m"],
        color=lap_colors[lap_number],
        linewidth=1.2,
        label=f"L{lap_number}"
    )

    lap_lines[
        lap_number
    ].append(line)


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

deviation_legend = (
    ax_deviation.legend()
)

style_legend(
    deviation_legend
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

        annotation_clip=False,
        zorder=10
    )

    



line_legend = ax_line.legend()

style_legend(
    line_legend
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
            zorder=20
        )

        section_label_artists.append(
            label
        )


# -------------------------
# Dynamic graph layout
# -------------------------

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
    right = 0.86

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

        gap = 0.025

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


# -------------------------
# Graph selector
# -------------------------

selector_ax = fig.add_axes(
    [0.88, 0.82, 0.09, 0.12]
)

selector_ax.set_facecolor("black")

selector_ax.tick_params(
    left=False,
    bottom=False,
    labelleft=False,
    labelbottom=False
)

for spine in selector_ax.spines.values():
    spine.set_visible(False)

graph_selector = CheckButtons(
    selector_ax,
    labels=list(graph_axes.keys()),
    actives=[True, True, True, True, True, False, False],

    label_props={
        "color": ["white"],
        "fontsize": [8]
    },

    frame_props={
        "edgecolor": ["white"],
        "facecolor": ["black"],
        "linewidth": [1]
    },

    check_props={
        "color": ["lime"],
        "linewidth": [2]
    }
)

for label in graph_selector.labels:
    label.set_color("white")
    label.set_fontsize(8)

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

def toggle_graph(label):
    ax = graph_axes[label]
    ax.set_visible(not ax.get_visible())

    reflow_graphs()

    if fig.canvas.toolbar is not None:
        fig.canvas.toolbar.update()

    rebuild_cursor()


graph_selector.on_clicked(
    toggle_graph
)


# -------------------------
# Lap selector
# -------------------------

lap_labels = [
    f"L{info['lap_number']}"
    for info in valid_lap_info
]

lap_label_to_number = {
    f"L{info['lap_number']}": info["lap_number"]
    for info in valid_lap_info
}

lap_selector_height = (
    0.032 * len(lap_labels) + 0.02
)

lap_selector_ax = fig.add_axes(
    [
        0.88,
        0.78 - lap_selector_height,
        0.09,
        lap_selector_height
    ]
)

lap_selector_ax.set_facecolor("black")

lap_selector_ax.tick_params(
    left=False,
    bottom=False,
    labelleft=False,
    labelbottom=False
)

for spine in lap_selector_ax.spines.values():
    spine.set_visible(False)

lap_selector = CheckButtons(
    lap_selector_ax,
    labels=lap_labels,
    actives=[True] * len(lap_labels),

    label_props={
        "color": ["white"],
        "fontsize": [8]
    },

    frame_props={
        "edgecolor": ["white"],
        "facecolor": ["black"],
        "linewidth": [1]
    },

    check_props={
        "color": ["lime"],
        "linewidth": [2]
    }
)


def update_lap_legends():

    # Speed legend
    speed_handles = [
        line
        for line in ax_speed.get_lines()
        if (
            line.get_visible()
            and not line.get_label().startswith("_")
        )
    ]

    if speed_handles:
        speed_legend = ax_speed.legend(
            handles=speed_handles
        )

        style_legend(speed_legend)

    # Delta legend
    delta_handles = [
        line
        for line in ax_delta.get_lines()
        if (
            line.get_visible()
            and not line.get_label().startswith("_")
        )
    ]

    if delta_handles:
        delta_legend = ax_delta.legend(
            handles=delta_handles
        )

        style_legend(delta_legend)

    # Racing-line legend
    line_handles = [
        line
        for line in ax_line.get_lines()
        if (
            line.get_visible()
            and not line.get_label().startswith("_")
        )
    ]
    
    if line_handles:
        line_legend = ax_line.legend(
            handles=line_handles
        )
    
        style_legend(line_legend)

    # Deviation legend
    deviation_handles = [
        line
        for line in ax_deviation.get_lines()
        if (
            line.get_visible()
            and not line.get_label().startswith("_")
        )
    ]
    
    if deviation_handles:
    
        deviation_legend = (
            ax_deviation.legend(
                handles=deviation_handles
            )
        )
    
        style_legend(
            deviation_legend
        )


def toggle_lap(label):

    lap_number = lap_label_to_number[label]

    lines = lap_lines[lap_number]

    new_visibility = not lines[0].get_visible()

    for line in lines:
        line.set_visible(
            new_visibility
        )

    update_lap_legends()

    fig.canvas.draw_idle()


lap_selector.on_clicked(
    toggle_lap
)

reflow_graphs()


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



plt.show()