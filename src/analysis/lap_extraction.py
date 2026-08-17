from pathlib import Path


import matplotlib.pyplot as plt
import numpy as np

from src.ingestion.motec_loader import load_telemetry
from src.ingestion.lap_loader import load_lap_markers


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

RAW_DATA = PROJECT_ROOT / "data" / "raw"

LD_FILE = (
    RAW_DATA
    / "monza-mclaren_720s_gt3_evo-5-2026.08.12-02.59.29.ld"
)

LDX_FILE = (
    RAW_DATA
    / "monza-mclaren_720s_gt3_evo-5-2026.08.12-02.59.29.ldx"
)


df = load_telemetry(LD_FILE)
markers = load_lap_markers(LDX_FILE)

laps = []

for i in range(len(markers) - 1):
    lap_start = markers[i]
    lap_end = markers[i + 1]

    lap = df[
        (df["time_s"] >= lap_start) &
        (df["time_s"] < lap_end)
    ].copy()

    lap["lap_time_s"] = (
        lap["time_s"] - lap_start
    )

    lap = lap.reset_index(drop=True)

    dt = np.diff(lap["time_s"])

    average_speed = (
        lap["speed_mps"].iloc[:-1].to_numpy()
        + lap["speed_mps"].iloc[1:].to_numpy()
    ) / 2

    distance_steps = average_speed * dt

    lap["distance_m"] = np.concatenate(
        ([0], np.cumsum(distance_steps))
    )

    laps.append(lap)


def has_position_teleport(
    lap,
    teleport_threshold_m=100.0
):

    x = lap["world_x"].to_numpy()
    z = lap["world_z"].to_numpy()

    step_distance = np.hypot(
        np.diff(x),
        np.diff(z)
    )

    return np.any(
        step_distance
        > teleport_threshold_m
    )


def is_complete_analysis_lap(
    lap,
    lap_time_ms,
    minimum_position_coverage=0.95
):

    if lap_time_ms is None:
        return False

    if not lap["is_valid_lap"].all():
        return False

    position_coverage = (
        lap["normalized_position"].max()
        - lap["normalized_position"].min()
    )

    if position_coverage < minimum_position_coverage:
        return False

    if has_position_teleport(lap):
        return False

    return True



print()
print("Extracted laps:")
print("---------------")

for i, lap in enumerate(laps, start=1):
    duration = lap["lap_time_s"].iloc[-1]

    distance = lap["distance_m"].iloc[-1]

    print(
        f"Lap {i}: "
        f"{duration:.3f} s, "
        f"{len(lap)} samples, "
        f"{distance:.1f} m"
    )



lap_distances = [
    lap["distance_m"].iloc[-1]
    for lap in laps
]

reference_distance = np.median(lap_distances)

print()
print(
    "Reference lap distance:",
    round(reference_distance, 1),
    "m"
)


for lap in laps:
    actual_distance = lap["distance_m"].iloc[-1]

    lap["aligned_distance_m"] = (
        lap["distance_m"]
        / actual_distance
        * reference_distance
    )


common_distance = np.arange(
    0,
    reference_distance,
    1
)


aligned_laps = []

for lap in laps:
    aligned = {
        "distance_m": common_distance,

        "speed_kmh": np.interp(
            common_distance,
            lap["aligned_distance_m"],
            lap["speed_kmh"]
        ),

        "brake": np.interp(
            common_distance,
            lap["aligned_distance_m"],
            lap["brake"]
        ),

        "throttle": np.interp(
            common_distance,
            lap["aligned_distance_m"],
            lap["throttle"]
        ),

        "steering_deg": np.interp(
            common_distance,
            lap["aligned_distance_m"],
            lap["steering_deg"]
        ),

        "lap_time_s": np.interp(
            common_distance,
            lap["aligned_distance_m"],
            lap["lap_time_s"]
        )
    }

    aligned_laps.append(aligned)



    

def format_lap_time(seconds):
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60

    return f"{minutes}:{remaining_seconds:06.3f}"


def diagnose_analysis_lap(
    lap,
    lap_time_ms,
    minimum_position_coverage=0.95,
    teleport_threshold_m=100.0
):

    x = lap["world_x"].to_numpy()
    z = lap["world_z"].to_numpy()

    step_distance = np.hypot(
        np.diff(x),
        np.diff(z)
    )

    if len(step_distance) > 0:
        max_jump_m = np.max(
            step_distance
        )
    else:
        max_jump_m = 0.0

    position_coverage = (
        lap["normalized_position"].max()
        - lap["normalized_position"].min()
    )

    valid_fraction = (
        lap["is_valid_lap"].mean()
    )

    return {
        "lap_time_ms": lap_time_ms,
        "position_coverage": position_coverage,
        "valid_fraction": valid_fraction,
        "max_jump_m": max_jump_m,
        "completed_laps_min": (
            lap["completed_laps"].min()
        ),
        "completed_laps_max": (
            lap["completed_laps"].max()
        )
    }



def extract_acc_completed_laps(
    df,
    teleport_threshold_m=100.0,
    minimum_position_coverage=0.95
):

    df = df.reset_index(drop=True)

    laps = {}
    lap_info = []

    if df.empty:
        return laps, lap_info

    x = df["world_x"].to_numpy()
    z = df["world_z"].to_numpy()

    step_distance = np.zeros(
        len(df)
    )

    step_distance[1:] = np.hypot(
        np.diff(x),
        np.diff(z)
    )

    candidate_start = 0

    previous_completed = int(
        df["completed_laps"].iloc[0]
    )

    extracted_lap_number = 0

    for i in range(
        1,
        len(df)
    ):

        current_completed = int(
            df["completed_laps"].iloc[i]
        )

        # -------------------------
        # Return-to-garage / teleport
        # -------------------------

        if (
            step_distance[i]
            > teleport_threshold_m
        ):

            candidate_start = i + 1

            previous_completed = (
                current_completed
            )

            continue

        # -------------------------
        # Session/reset protection
        # -------------------------

        if (
            current_completed
            < previous_completed
        ):

            candidate_start = i

            previous_completed = (
                current_completed
            )

            continue

        # -------------------------
        # ACC completed a lap
        # -------------------------

        if (
            current_completed
            > previous_completed
        ):

            lap = df.iloc[
                candidate_start:i + 1
            ].copy()

            lap = lap.reset_index(
                drop=True
            )

            extracted_lap_number += 1

            lap_time_ms = int(
                df["acc_last_lap_ms"].iloc[i]
            )

            if (
                lap_time_ms <= 0
                or
                lap_time_ms >= 2147483647
            ):
                lap_time_ms = None

            # -------------------------
            # Position coverage
            # -------------------------

            if lap.empty:

                position_coverage = 0.0

            else:

                position_coverage = (
                    lap[
                        "normalized_position"
                    ].max()
                    -
                    lap[
                        "normalized_position"
                    ].min()
                )

            # -------------------------
            # ACC validity
            # -------------------------

            if lap.empty:

                acc_valid = False

            else:

                valid_fraction = (
                    lap[
                        "is_valid_lap"
                    ].mean()
                )
                
                acc_valid = (
                    lap[
                        "is_valid_lap"
                    ].all()
                )

            # -------------------------
            # Teleport sanity check
            # -------------------------

            if len(lap) > 1:

                lap_dx = np.diff(
                    lap[
                        "world_x"
                    ].to_numpy()
                )

                lap_dz = np.diff(
                    lap[
                        "world_z"
                    ].to_numpy()
                )

                max_jump_m = np.max(
                    np.hypot(
                        lap_dx,
                        lap_dz
                    )
                )

            else:

                max_jump_m = 0.0

            is_usable = (
                lap_time_ms is not None
                and
                position_coverage
                >= minimum_position_coverage
                and
                max_jump_m
                <= teleport_threshold_m
            )

            laps[
                extracted_lap_number
            ] = lap

            lap_info.append(
                {
                    "lap_number":
                        extracted_lap_number,

                    "acc_completed_lap":
                        current_completed,

                    "lap_time_ms":
                        lap_time_ms,

                    "is_valid":
                        is_usable,

                    "acc_valid":
                        acc_valid,

                    "position_coverage":
                        position_coverage,

                    "max_jump_m":
                        max_jump_m,

                    "valid_fraction":
                        valid_fraction,
                }
            )

            # The completion row is the
            # beginning of the next lap.
            candidate_start = i

        previous_completed = (
            current_completed
        )

    return laps, lap_info



lap_times = [
    markers[i + 1] - markers[i]
    for i in range(len(laps))
]

best_lap_index = np.argmin(lap_times)

print()
print("Best lap:", best_lap_index + 1)
print(
    "Best lap time:",
    format_lap_time(lap_times[best_lap_index])
)


reference_lap = aligned_laps[best_lap_index]

delta_times = []

for aligned in aligned_laps:
    delta = (
        aligned["lap_time_s"]
        - reference_lap["lap_time_s"]
    )

    delta_times.append(delta)




plt.figure(figsize=(14, 6))

for i, aligned in enumerate(aligned_laps, start=1):
    lap_time = markers[i] - markers[i - 1]

    plt.plot(
        aligned["distance_m"],
        aligned["speed_kmh"],
        label=f"Lap {i} - {format_lap_time(lap_time)}"
    )

plt.xlabel("Lap Time (s)")
plt.ylabel("Speed (km/h)")
plt.title("Monza - Lap Speed Comparison")

plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()

plt.show()




plt.figure(figsize=(14, 6))

for i, delta in enumerate(delta_times, start=1):

    if i - 1 == best_lap_index:
        continue

    plt.plot(
        common_distance,
        delta,
        label=f"Lap {i} vs Lap {best_lap_index + 1}"
    )

plt.axhline(
    0,
    color="black",
    linestyle="--",
    linewidth=1
)

plt.xlabel("Distance (m)")
plt.ylabel("Time Delta (s)")
plt.title(
    f"Time Delta vs Best Lap "
    f"(Lap {best_lap_index + 1} - "
    f"{format_lap_time(lap_times[best_lap_index])})"
)

plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()

plt.show()