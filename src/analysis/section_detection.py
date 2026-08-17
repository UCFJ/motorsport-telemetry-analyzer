import numpy as np


def smooth_signal(values, window=21):

    if window <= 1:
        return values.copy()

    kernel = np.ones(window) / window

    return np.convolve(
        values,
        kernel,
        mode="same"
    )


def calculate_reference_geometry(
    aligned_lap
):

    x = aligned_lap["world_x"]
    z = aligned_lap["world_z"]

    # -------------------------
    # Distance along trajectory
    # -------------------------

    dx = np.diff(x)
    dz = np.diff(z)

    step_distance = np.hypot(
        dx,
        dz
    )

    distance_m = np.concatenate(
        (
            [0.0],
            np.cumsum(step_distance)
        )
    )

    # -------------------------
    # Heading
    # -------------------------

    dx_ds = np.gradient(x)
    dz_ds = np.gradient(z)

    heading = np.arctan2(
        dz_ds,
        dx_ds
    )

    heading = np.unwrap(
        heading
    )

    # -------------------------
    # Prevent duplicate distance
    # -------------------------

    safe_distance = (
        distance_m.copy()
    )

    for i in range(
        1,
        len(safe_distance)
    ):

        if (
            safe_distance[i]
            <= safe_distance[i - 1]
        ):
            safe_distance[i] = (
                safe_distance[i - 1]
                + 0.001
            )

    # -------------------------
    # Curvature
    # -------------------------

    curvature = np.gradient(
        heading,
        safe_distance
    )

    curvature = smooth_signal(
        curvature,
        window=21
    )

    return {
        "distance_m": distance_m,
        "heading_rad": heading,
        "curvature": curvature
    }


def detect_corner_sections(
    aligned_lap,
    curvature_threshold=0.0025,
    minimum_length_m=20.0,
    merge_gap_m=30.0
):

    geometry = (
        calculate_reference_geometry(
            aligned_lap
        )
    )

    distance = geometry[
        "distance_m"
    ]

    curvature = geometry[
        "curvature"
    ]

    cornering = (
        np.abs(curvature)
        >= curvature_threshold
    )

    # -------------------------
    # Find raw cornering regions
    # -------------------------

    raw_sections = []

    start_index = None

    for i, is_cornering in enumerate(
        cornering
    ):

        if (
            is_cornering
            and start_index is None
        ):
            start_index = i

        elif (
            not is_cornering
            and start_index is not None
        ):

            raw_sections.append(
                [
                    start_index,
                    i - 1
                ]
            )

            start_index = None

    if start_index is not None:

        raw_sections.append(
            [
                start_index,
                len(cornering) - 1
            ]
        )

    # -------------------------
    # Merge nearby regions
    # -------------------------

    merged_sections = []

    for section in raw_sections:

        if not merged_sections:

            merged_sections.append(
                section
            )

            continue

        previous = (
            merged_sections[-1]
        )

        gap_m = (
            distance[section[0]]
            - distance[previous[1]]
        )

        if gap_m <= merge_gap_m:

            previous[1] = (
                section[1]
            )

        else:

            merged_sections.append(
                section
            )

    # -------------------------
    # Remove tiny regions
    # -------------------------

    final_sections = []

    for start, end in merged_sections:

        length_m = (
            distance[end]
            - distance[start]
        )

        section_curvature = curvature[
            start:end + 1
        ]
        
        peak_index_local = np.argmax(
            np.abs(section_curvature)
        )
        
        peak_index = (
            start
            + peak_index_local
        )
        
        peak_curvature = curvature[
            peak_index
        ]
        
        if peak_curvature > 0:
            direction = "positive"
        else:
            direction = "negative"

        if (
            length_m
            < minimum_length_m
        ):
            continue

        final_sections.append(
            {
                "start_index": start,
                "end_index": end,
        
                "start_position": (
                    aligned_lap[
                        "normalized_position"
                    ][start]
                ),
        
                "end_position": (
                    aligned_lap[
                        "normalized_position"
                    ][end]
                ),
        
                "start_distance_m": (
                    distance[start]
                ),
        
                "end_distance_m": (
                    distance[end]
                ),
        
                "length_m": length_m,
        
                "peak_index": peak_index,
        
                "peak_position": (
                    aligned_lap[
                        "normalized_position"
                    ][peak_index]
                ),
        
                "peak_curvature": (
                    peak_curvature
                ),
        
                "direction": direction
            }
        )

    return (
        final_sections,
        geometry
    )



def analyze_section_gaps(
    sections,
    aligned_lap,
    geometry
):

    gap_info = []

    curvature = geometry[
        "curvature"
    ]

    distance = geometry[
        "distance_m"
    ]

    steering = aligned_lap[
        "steering"
    ]

    throttle = aligned_lap[
        "throttle"
    ]

    brake = aligned_lap[
        "brake"
    ]

    speed = aligned_lap[
        "speed_kmh"
    ]

    for i in range(
        len(sections) - 1
    ):

        first = sections[i]
        second = sections[i + 1]

        start = (
            first["end_index"] + 1
        )
        
        end = (
            second["start_index"] - 1
        )

        if end < start:
            continue

        gap_curvature = curvature[
            start:end + 1
        ]

        gap_steering = steering[
            start:end + 1
        ]

        gap_throttle = throttle[
            start:end + 1
        ]

        gap_brake = brake[
            start:end + 1
        ]

        gap_speed = speed[
            start:end + 1
        ]

        gap_distance = (
            distance[end]
            - distance[start]
        )

        gap_info.append(
            {
                "first_section": i + 1,
                "second_section": i + 2,

                "gap_m": gap_distance,

                "max_curvature": np.max(
                    np.abs(
                        gap_curvature
                    )
                ),

                "mean_abs_steering": np.mean(
                    np.abs(
                        gap_steering
                    )
                ),

                "max_abs_steering": np.max(
                    np.abs(
                        gap_steering
                    )
                ),

                "mean_throttle": np.mean(
                    gap_throttle
                ),

                "min_throttle": np.min(
                    gap_throttle
                ),

                "max_brake": np.max(
                    gap_brake
                ),

                "mean_speed_kmh": np.mean(
                    gap_speed
                ),

                "min_speed_kmh": np.min(
                    gap_speed
                )
            }
        )

    return gap_info

def detect_braking_zones(
    aligned_lap,
    brake_threshold=0.10,
    minimum_length_m=10.0
):

    brake = aligned_lap["brake"]

    x = aligned_lap["world_x"]
    z = aligned_lap["world_z"]

    dx = np.diff(x)
    dz = np.diff(z)

    step_distance = np.hypot(
        dx,
        dz
    )

    distance = np.concatenate(
        (
            [0.0],
            np.cumsum(step_distance)
        )
    )

    braking = (
        brake >= brake_threshold
    )

    zones = []

    start_index = None

    for i, is_braking in enumerate(
        braking
    ):

        if (
            is_braking
            and start_index is None
        ):
            start_index = i

        elif (
            not is_braking
            and start_index is not None
        ):

            end_index = i - 1

            length_m = (
                distance[end_index]
                - distance[start_index]
            )

            if (
                length_m
                >= minimum_length_m
            ):

                zones.append(
                    {
                        "start_index": start_index,
                        "end_index": end_index,

                        "start_position": (
                            aligned_lap[
                                "normalized_position"
                            ][start_index]
                        ),

                        "end_position": (
                            aligned_lap[
                                "normalized_position"
                            ][end_index]
                        ),

                        "start_distance_m": (
                            distance[start_index]
                        ),

                        "end_distance_m": (
                            distance[end_index]
                        ),

                        "length_m": length_m
                    }
                )

            start_index = None

    return zones


def group_corner_regions(
    sections,
    gap_info,
    max_link_gap_m=80.0,
    steering_link_threshold=0.05
):

    if not sections:
        return []

    grouped = []

    current_group = [
        sections[0]
    ]

    for i in range(
        len(sections) - 1
    ):

        current = sections[i]
        next_section = sections[i + 1]

        gap = gap_info[i]

        short_gap = (
            gap["gap_m"]
            <= max_link_gap_m
        )

        direction_change = (
            current["direction"]
            != next_section["direction"]
        )

        steering_active = (
            gap["mean_abs_steering"]
            >= steering_link_threshold
        )

        should_link = (
            short_gap
            and (
                direction_change
                or steering_active
            )
        )

        if should_link:

            current_group.append(
                next_section
            )

        else:

            grouped.append(
                current_group
            )

            current_group = [
                next_section
            ]

    grouped.append(
        current_group
    )

    return grouped


def build_analysis_sections(
    grouped_sections,
    braking_zones,
    aligned_lap,
    geometry,
    brake_link_distance_m=150.0
):

    distance = geometry[
        "distance_m"
    ]

    analysis_sections = []

    used_braking_zones = set()

    for section_number, group in enumerate(
        grouped_sections,
        start=1
    ):

        core_start_index = (
            group[0]["start_index"]
        )

        core_end_index = (
            group[-1]["end_index"]
        )

        core_start_distance = (
            distance[core_start_index]
        )

        core_end_distance = (
            distance[core_end_index]
        )

        linked_brake = None
        linked_brake_index = None

        # -------------------------
        # Find braking zone that
        # leads into this core
        # -------------------------

        for brake_index, brake in enumerate(
            braking_zones
        ):

            if brake_index in used_braking_zones:
                continue

            brake_start = (
                brake["start_distance_m"]
            )

            brake_end = (
                brake["end_distance_m"]
            )

            # Brake overlaps the
            # geometric core
            overlaps_core = (
                brake_end >= core_start_distance
                and
                brake_start <= core_end_distance
            )

            # Or braking ends shortly
            # before the core begins
            ends_before_core = (
                brake_end < core_start_distance
                and
                (
                    core_start_distance
                    - brake_end
                )
                <= brake_link_distance_m
            )

            if (
                overlaps_core
                or ends_before_core
            ):

                linked_brake = brake
                linked_brake_index = (
                    brake_index
                )

                break

        # -------------------------
        # Analysis section start
        # -------------------------

        if linked_brake is not None:

            start_index = linked_brake[
                "start_index"
            ]

            used_braking_zones.add(
                linked_brake_index
            )

        else:

            start_index = (
                core_start_index
            )

        # For now, section ends at
        # the end of geometric core.
        # We will extend the exit later.
        end_index = core_end_index

        analysis_sections.append(
            {
                "section_number": (
                    section_number
                ),

                "start_index": (
                    start_index
                ),

                "end_index": (
                    end_index
                ),

                "core_start_index": (
                    core_start_index
                ),

                "core_end_index": (
                    core_end_index
                ),

                "start_position": (
                    aligned_lap[
                        "normalized_position"
                    ][start_index]
                ),

                "end_position": (
                    aligned_lap[
                        "normalized_position"
                    ][end_index]
                ),

                "core_start_position": (
                    aligned_lap[
                        "normalized_position"
                    ][core_start_index]
                ),

                "core_end_position": (
                    aligned_lap[
                        "normalized_position"
                    ][core_end_index]
                ),

                "start_distance_m": (
                    distance[start_index]
                ),

                "end_distance_m": (
                    distance[end_index]
                ),

                "has_braking": (
                    linked_brake is not None
                ),

                "brake_zone": (
                    linked_brake
                )
            }
        )

    return analysis_sections



def extend_section_exits(
    analysis_sections,
    aligned_lap,
    geometry,
    throttle_threshold=0.95,
    brake_threshold=0.05,
    curvature_threshold=0.0015,
    stable_distance_m=20.0
):

    distance = geometry[
        "distance_m"
    ]

    curvature = geometry[
        "curvature"
    ]

    throttle = aligned_lap[
        "throttle"
    ]

    brake = aligned_lap[
        "brake"
    ]

    total_samples = len(
        aligned_lap[
            "normalized_position"
        ]
    )

    for i, section in enumerate(
        analysis_sections
    ):

        core_end = section[
            "core_end_index"
        ]

        if (
            i
            < len(analysis_sections) - 1
        ):

            search_end = (
                analysis_sections[
                    i + 1
                ]["start_index"]
                - 1
            )

        else:

            search_end = (
                total_samples - 1
            )

        search_end = max(
            core_end,
            search_end
        )

        exit_index = (
            core_end
        )

        found_recovery = False

        for start in range(
            core_end + 1,
            search_end + 1
        ):

            recovered = (
                throttle[start]
                >= throttle_threshold
                and
                brake[start]
                <= brake_threshold
                and
                abs(curvature[start])
                <= curvature_threshold
            )

            if not recovered:
                continue

            start_distance = (
                distance[start]
            )

            end = start

            while (
                end <= search_end
            ):

                still_recovered = (
                    throttle[end]
                    >= throttle_threshold
                    and
                    brake[end]
                    <= brake_threshold
                    and
                    abs(curvature[end])
                    <= curvature_threshold
                )

                if not still_recovered:
                    break

                if (
                    distance[end]
                    - start_distance
                    >= stable_distance_m
                ):

                    exit_index = start
                    found_recovery = True
                    break

                end += 1

            if found_recovery:
                break

        section[
            "end_index"
        ] = exit_index

        section[
            "end_position"
        ] = (
            aligned_lap[
                "normalized_position"
            ][exit_index]
        )

        section[
            "end_distance_m"
        ] = (
            distance[exit_index]
        )

        section[
            "exit_recovery_found"
        ] = (
            found_recovery
        )

    return analysis_sections