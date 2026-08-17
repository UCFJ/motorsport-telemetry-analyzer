import numpy as np


def align_laps(
    laps,
    valid_lap_info,
    common_position
):

    aligned_laps = {}

    for info in valid_lap_info:

        lap_number = info["lap_number"]
        lap = laps[lap_number].copy()

        lap = (
            lap
            .sort_values("normalized_position")
            .drop_duplicates(
                "normalized_position",
                keep="last"
            )
        )

        position = lap[
            "normalized_position"
        ].to_numpy()

        aligned = {
            "normalized_position": common_position,

            "speed_kmh": np.interp(
                common_position,
                position,
                lap["speed_kmh"]
            ),

            "brake": np.interp(
                common_position,
                position,
                lap["brake"]
            ),

            "throttle": np.interp(
                common_position,
                position,
                lap["throttle"]
            ),

            "steering": np.interp(
                common_position,
                position,
                lap["steering"]
            ),

            "lap_time_s": np.interp(
                common_position,
                position,
                lap["lap_time_s"]
            ),

            "world_x": np.interp(
                common_position,
                position,
                lap["world_x"]
            ),

            "world_z": np.interp(
                common_position,
                position,
                lap["world_z"]
            )
        }

        aligned_laps[
            lap_number
        ] = aligned

    return aligned_laps


def calculate_deltas(
    aligned_laps,
    reference_lap_number
):

    reference_lap = aligned_laps[
        reference_lap_number
    ]

    delta_times = {}

    for lap_number, aligned in (
        aligned_laps.items()
    ):

        if (
            lap_number
            == reference_lap_number
        ):
            continue

        delta_times[lap_number] = (
            aligned["lap_time_s"]
            - reference_lap["lap_time_s"]
        )

    return delta_times


def calculate_line_deviation(
    aligned_laps,
    reference_lap_number
):

    reference_lap = aligned_laps[
        reference_lap_number
    ]

    reference_x = reference_lap[
        "world_x"
    ]

    reference_z = reference_lap[
        "world_z"
    ]

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

    normal_x = (
        -reference_dz
        / direction_length
    )

    normal_z = (
        reference_dx
        / direction_length
    )

    for lap_number, aligned in (
        aligned_laps.items()
    ):

        difference_x = (
            aligned["world_x"]
            - reference_x
        )

        difference_z = (
            aligned["world_z"]
            - reference_z
        )

        aligned[
            "line_deviation_m"
        ] = (
            difference_x * normal_x
            + difference_z * normal_z
        )

        aligned[
            "line_distance_m"
        ] = np.hypot(
            difference_x,
            difference_z
        )

    return aligned_laps