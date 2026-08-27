import numpy as np


def find_first_threshold_crossing(
    values,
    start_index,
    end_index,
    threshold
):

    for i in range(
        start_index,
        end_index + 1
    ):

        if values[i] >= threshold:
            return i

    return None



def detect_throttle_applications(
    throttle,
    distance,
    start_index,
    end_index,
    low_threshold=0.10,
    application_threshold=0.20,
    sustain_distance_m=8.0
):

    applications = []

    ready_for_application = (
        throttle[start_index]
        <= low_threshold
    )

    for i in range(
        start_index + 1,
        end_index + 1
    ):

        if throttle[i] <= low_threshold:

            ready_for_application = True
            continue

        if not ready_for_application:
            continue

        if (
            throttle[i]
            < application_threshold
        ):
            continue

        sustain_end_distance = (
            distance[i]
            + sustain_distance_m
        )

        sustain_end = np.searchsorted(
            distance,
            sustain_end_distance
        )

        sustain_end = min(
            sustain_end,
            end_index
        )

        segment = throttle[
            i:sustain_end + 1
        ]

        if len(segment) == 0:
            continue

        active_fraction = np.mean(
            segment
            >= application_threshold
        )

        if active_fraction >= 0.70:

            applications.append(i)

            ready_for_application = False

    return applications



def find_final_throttle_commitment(
    throttle,
    start_index,
    end_index,
    high_threshold=0.90,
    hold_threshold=0.85
):

    section_throttle = throttle[
        start_index:end_index + 1
    ]

    if len(section_throttle) == 0:
        return None

    # Already essentially full throttle
    # through the whole section.
    if np.min(
        section_throttle
    ) >= hold_threshold:

        return None

    # Section does not finish at
    # meaningful full throttle.
    if (
        throttle[end_index]
        < high_threshold
    ):

        return None

    run_start = end_index

    while (
        run_start > start_index
        and
        throttle[run_start - 1]
        >= hold_threshold
    ):

        run_start -= 1

    for i in range(
        run_start,
        end_index + 1
    ):

        if (
            throttle[i]
            >= high_threshold
        ):

            return i

    return None



def find_final_throttle_application_onset(
    throttle,
    throttle_applications,
    end_index,
    high_threshold=0.90,
    exit_hold_threshold=0.85
):

    if len(throttle_applications) == 0:
        return None

    for application_index in reversed(
        throttle_applications
    ):

        remaining_throttle = throttle[
            application_index:
            end_index + 1
        ]

        if len(remaining_throttle) == 0:
            continue

        reaches_high_throttle = (
            np.max(
                remaining_throttle
            )
            >= high_threshold
        )

        finishes_on_throttle = (
            throttle[end_index]
            >= exit_hold_threshold
        )

        if (
            reaches_high_throttle
            and
            finishes_on_throttle
        ):

            return application_index

    return None


def detect_post_full_throttle_lifts(
    throttle,
    start_index,
    end_index,
    full_threshold=0.98,
    lift_threshold=0.90
):

    first_full_index = None

    for i in range(
        start_index,
        end_index + 1
    ):

        if throttle[i] >= full_threshold:

            first_full_index = i
            break


    if first_full_index is None:

        return 0, None


    lift_count = 0
    minimum_throttle = None
    in_lift = False


    for i in range(
        first_full_index + 1,
        end_index + 1
    ):

        if throttle[i] <= lift_threshold:

            if not in_lift:

                lift_count += 1
                in_lift = True


            if (
                minimum_throttle is None
                or
                throttle[i] < minimum_throttle
            ):

                minimum_throttle = float(
                    throttle[i]
                )


        elif throttle[i] >= full_threshold:

            in_lift = False


    return (
        lift_count,
        minimum_throttle
    )


def calculate_coasting_distance(
    throttle,
    brake,
    distance,
    start_index,
    end_index,
    threshold=0.10
):

    section_throttle = throttle[
        start_index:
        end_index + 1
    ]

    section_brake = brake[
        start_index:
        end_index + 1
    ]

    section_distance = distance[
        start_index:
        end_index + 1
    ]

    if len(section_distance) < 2:
        return 0.0

    coasting = (
        (section_throttle <= threshold)
        &
        (section_brake <= threshold)
    )

    distance_steps = np.diff(
        section_distance
    )

    coasting_intervals = (
        coasting[:-1]
        &
        coasting[1:]
    )

    return float(
        np.sum(
            distance_steps[
                coasting_intervals
            ]
        )
    )


def calculate_section_observations(
    aligned_lap,
    reference_lap,
    section,
    reference_geometry,
    delta,
    brake_threshold=0.10,
    search_margin_m=150.0
):

    distance = reference_geometry[
        "distance_m"
    ]

    core_start = section[
        "core_start_index"
    ]

    section_start = section[
        "start_index"
    ]

    section_end = section[
        "end_index"
    ]

    # -------------------------
    # Search window before entry
    # -------------------------

    search_start_distance = max(
        0.0,
        distance[core_start]
        - search_margin_m
    )

    search_start = np.searchsorted(
        distance,
        search_start_distance
    )

    # -------------------------
    # Section time difference
    # -------------------------

    section_delta_s = (
        delta[section_end]
        - delta[section_start]
    )

    # -------------------------
    # Minimum speed
    # -------------------------

    reference_min_speed = np.min(
        reference_lap[
            "speed_kmh"
        ][section_start:section_end + 1]
    )

    lap_min_speed = np.min(
        aligned_lap[
            "speed_kmh"
        ][section_start:section_end + 1]
    )

    min_speed_difference = (
        lap_min_speed
        - reference_min_speed
    )



    # -------------------------
    # Section end speed
    # -------------------------
    
    section_end_speed_difference = (
        aligned_lap[
            "speed_kmh"
        ][section_end]
        -
        reference_lap[
            "speed_kmh"
        ][section_end]
    )


    
    # -------------------------
    # Brake behavior
    # -------------------------
    
    reference_brake_events = (
        detect_brake_events(
            reference_lap["brake"],
            distance,
            search_start,
            section_end
        )
    )
    
    lap_brake_events = (
        detect_brake_events(
            aligned_lap["brake"],
            distance,
            search_start,
            section_end
        )
    )
    
    
    # -------------------------
    # Initial brake onset
    # -------------------------
    
    if (
        len(reference_brake_events) > 0
        and
        len(lap_brake_events) > 0
    ):
    
        reference_initial_brake = (
            reference_brake_events[0][
                "start_index"
            ]
        )
    
        lap_initial_brake = (
            lap_brake_events[0][
                "start_index"
            ]
        )
    
        brake_onset_difference_m = (
            distance[
                lap_initial_brake
            ]
            -
            distance[
                reference_initial_brake
            ]
        )
    
    else:
    
        brake_onset_difference_m = None
    
    
    # -------------------------
    # Final brake release
    # -------------------------
    
    if (
        len(reference_brake_events) > 0
        and
        len(lap_brake_events) > 0
    ):
    
        reference_final_release = (
            reference_brake_events[-1][
                "end_index"
            ]
        )
    
        lap_final_release = (
            lap_brake_events[-1][
                "end_index"
            ]
        )
    
        brake_release_difference_m = (
            distance[
                lap_final_release
            ]
            -
            distance[
                reference_final_release
            ]
        )
    
    else:
    
        brake_release_difference_m = None

    # -------------------------
    # Throttle behavior
    # -------------------------
    
    reference_throttle = (
        reference_lap["throttle"]
    )
    
    lap_throttle = (
        aligned_lap["throttle"]
    )
    
    
    reference_throttle_applications = (
        detect_throttle_applications(
            reference_throttle,
            distance,
            section_start,
            section_end
        )
    )


    # -------------------------
    # Coasting
    # -------------------------
    
    reference_coasting_distance = (
        calculate_coasting_distance(
            reference_lap["throttle"],
            reference_lap["brake"],
            distance,
            section_start,
            section_end
        )
    )
    
    lap_coasting_distance = (
        calculate_coasting_distance(
            aligned_lap["throttle"],
            aligned_lap["brake"],
            distance,
            section_start,
            section_end
        )
    )
    
    coasting_distance_difference_m = (
        lap_coasting_distance
        -
        reference_coasting_distance
    )

    
    
    lap_throttle_applications = (
        detect_throttle_applications(
            lap_throttle,
            distance,
            section_start,
            section_end
        )
    )

    # -------------------------
    # Post-full-throttle lifts
    # -------------------------
    
    if lap_throttle_applications:
    
        lap_post_full_throttle_start = (
            lap_throttle_applications[-1]
        )
    
    else:
    
        lap_post_full_throttle_start = (
            section_start
        )
    
    
    if reference_throttle_applications:
    
        reference_post_full_throttle_start = (
            reference_throttle_applications[-1]
        )
    
    else:
    
        reference_post_full_throttle_start = (
            section_start
        )
    
    
    (
        lap_post_full_throttle_lift_count,
        lap_post_full_throttle_minimum
    ) = detect_post_full_throttle_lifts(
        lap_throttle,
        lap_post_full_throttle_start,
        section_end
    )
    
    
    (
        reference_post_full_throttle_lift_count,
        reference_post_full_throttle_minimum
    ) = detect_post_full_throttle_lifts(
        reference_throttle,
        reference_post_full_throttle_start,
        section_end
    )

    post_full_throttle_lift_count_difference = (
        lap_post_full_throttle_lift_count
        - reference_post_full_throttle_lift_count
    )
    
    
    reference_full_lift = (
        np.min(
            reference_throttle[
                section_start:
                section_end + 1
            ]
        )
        <= 0.10
    )
    
    lap_full_lift = (
        np.min(
            lap_throttle[
                section_start:
                section_end + 1
            ]
        )
        <= 0.10
    )
    
    
    reference_throttle_interrupted = (
        np.min(
            reference_throttle[
                section_start:
                section_end + 1
            ]
        )
        < 0.85
    )
    
    lap_throttle_interrupted = (
        np.min(
            lap_throttle[
                section_start:
                section_end + 1
            ]
        )
        < 0.85
    )
    
    
    reference_final_throttle = (
        find_final_throttle_commitment(
            reference_throttle,
            section_start,
            section_end
        )
    )
    
    lap_final_throttle = (
        find_final_throttle_commitment(
            lap_throttle,
            section_start,
            section_end
        )
    )
    
    
    if (
        reference_final_throttle is not None
        and
        lap_final_throttle is not None
    ):
    
        full_throttle_difference_m = (
            distance[
                lap_final_throttle
            ]
            -
            distance[
                reference_final_throttle
            ]
        )
    
    else:
    
        full_throttle_difference_m = None
   



    reference_final_throttle_onset = (
        find_final_throttle_application_onset(
            reference_throttle,
            reference_throttle_applications,
            section_end
        )
    )
    
    lap_final_throttle_onset = (
        find_final_throttle_application_onset(
            lap_throttle,
            lap_throttle_applications,
            section_end
        )
    )
    
    
    if (
        reference_final_throttle_onset
        is not None
        and
        lap_final_throttle_onset
        is not None
    ):
    
        final_throttle_onset_difference_m = (
            distance[
                lap_final_throttle_onset
            ]
            -
            distance[
                reference_final_throttle_onset
            ]
        )
    
    else:
    
        final_throttle_onset_difference_m = None



    # -------------------------
    # Racing-line deviation
    # -------------------------

    line_deviation = aligned_lap[
        "line_deviation_m"
    ][section_start:section_end + 1]

    if len(line_deviation) > 0:

        peak_local_index = np.argmax(
            np.abs(
                line_deviation
            )
        )

        peak_line_deviation_m = (
            line_deviation[
                peak_local_index
            ]
        )

    else:

        peak_line_deviation_m = 0.0

    return {
        "section_number":
            section["section_number"],
    
        "section_delta_s":
            section_delta_s,
    
        "min_speed_difference_kmh":
            min_speed_difference,

        "section_end_speed_difference_kmh":
            section_end_speed_difference,
            
        "brake_onset_difference_m":
            brake_onset_difference_m,
    
        "reference_brake_application_count":
            len(reference_brake_events),
        
        "lap_brake_application_count":
            len(lap_brake_events),
        
        "brake_onset_difference_m":
            brake_onset_difference_m,
        
        "brake_release_difference_m":
            brake_release_difference_m,
    
        "reference_throttle_application_count":
            len(
                reference_throttle_applications
            ),
    
        "lap_throttle_application_count":
            len(
                lap_throttle_applications
            ),

        "lap_post_full_throttle_lift_count":
            lap_post_full_throttle_lift_count,
        
        "reference_post_full_throttle_lift_count":
            reference_post_full_throttle_lift_count,

        "post_full_throttle_lift_count_difference":
            post_full_throttle_lift_count_difference,
        
        "lap_post_full_throttle_minimum":
            lap_post_full_throttle_minimum,
        
        "reference_post_full_throttle_minimum":
            reference_post_full_throttle_minimum,
    
        "reference_full_lift":
            reference_full_lift,
    
        "lap_full_lift":
            lap_full_lift,

        "reference_coasting_distance_m":
            reference_coasting_distance,
        
        "lap_coasting_distance_m":
            lap_coasting_distance,
        
        "coasting_distance_difference_m":
            coasting_distance_difference_m,
    
        "reference_throttle_interrupted":
            reference_throttle_interrupted,
    
        "lap_throttle_interrupted":
            lap_throttle_interrupted,
    
        "final_throttle_onset_difference_m":
            final_throttle_onset_difference_m,
        
        "full_throttle_difference_m":
            full_throttle_difference_m,
    
        "peak_line_deviation_m":
            peak_line_deviation_m
    }



def detect_brake_events(
    brake,
    distance,
    start_index,
    end_index,
    threshold=0.10,
    release_distance_m=5.0
):

    events = []

    in_event = False
    event_start = None

    i = start_index

    while i <= end_index:

        if not in_event:

            if brake[i] >= threshold:

                in_event = True
                event_start = i

            i += 1
            continue


        # Currently inside a braking event
        if brake[i] > threshold:

            i += 1
            continue


        release_end_distance = (
            distance[i]
            + release_distance_m
        )

        release_end = np.searchsorted(
            distance,
            release_end_distance
        )

        release_end = min(
            release_end,
            end_index
        )

        release_segment = brake[
            i:release_end + 1
        ]

        released_fraction = np.mean(
            release_segment <= threshold
        )

        if released_fraction >= 0.80:

            events.append({
                "start_index":
                    event_start,

                "end_index":
                    i
            })

            in_event = False
            event_start = None

        i += 1


    # Brake still active at section end
    if (
        in_event
        and
        event_start is not None
    ):

        events.append({
            "start_index":
                event_start,

            "end_index":
                end_index
        })


    return events
