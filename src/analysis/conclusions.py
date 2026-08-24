def format_timing_sentence(
    value,
    earlier_text,
    later_text,
    same_text
):

    if value is None:
        return None

    difference = round(
        abs(float(value)),
        1
    )

    if difference == 0.0:
        return same_text

    if value < 0:
        return (
            f"{earlier_text} "
            f"{difference:.1f} m earlier."
        )

    return (
        f"{later_text} "
        f"{difference:.1f} m later."
    )


def format_speed_sentence(
    value,
    label
):

    difference = round(
        abs(float(value)),
        1
    )

    if difference == 0.0:
        return (
            f"{label} was the same "
            f"as the reference."
        )

    if value > 0:
        return (
            f"{label} was "
            f"{difference:.1f} km/h higher."
        )

    return (
        f"{label} was "
        f"{difference:.1f} km/h lower."
    )


def format_application_count(
    lap_count,
    reference_count,
    input_name
):

    if (
        lap_count == 0
        and reference_count == 0
    ):

        return (
            f"Neither lap had a "
            f"{input_name} application."
        )

    if lap_count == reference_count:

        if lap_count == 1:
            return (
                f"Both laps had 1 "
                f"{input_name} application."
            )

        return (
            f"Both laps had "
            f"{lap_count} "
            f"{input_name} applications."
        )

    return (
        f"You had {lap_count} "
        f"{input_name} applications "
        f"vs {reference_count} "
        f"on the reference."
    )


def format_full_lift(
    lap_full_lift,
    reference_full_lift
):

    if (
        lap_full_lift
        and reference_full_lift
    ):

        return (
            "You and the reference "
            "both fully lifted."
        )

    if (
        lap_full_lift
        and not reference_full_lift
    ):

        return (
            "You fully lifted; "
            "the reference did not."
        )

    if (
        not lap_full_lift
        and reference_full_lift
    ):

        return (
            "The reference fully lifted; "
            "you did not."
        )

    return (
        "Neither lap fully lifted."
    )


def format_racing_line(
    value
):

    deviation = round(
        abs(float(value)),
        1
    )

    if deviation == 0.0:

        return (
            "Peak racing-line deviation "
            "was 0.0 m."
        )

    if value < 0:
        direction = "left"
    else:
        direction = "right"

    return (
        f"Peak racing-line deviation "
        f"was {deviation:.1f} m "
        f"{direction} of the reference."
    )


def analyze_section_conclusion(
    observation
):

    section_number = (
        observation[
            "section_number"
        ]
    )

    section_delta = float(
        observation[
            "section_delta_s"
        ]
    )


    # -------------------------
    # Section time
    # -------------------------

    if section_delta > 0:

        headline = (
            f"Section {section_number} — "
            f"Lost {abs(section_delta):.3f} s"
        )

    elif section_delta < 0:

        headline = (
            f"Section {section_number} — "
            f"Gained {abs(section_delta):.3f} s"
        )

    else:

        headline = (
            f"Section {section_number} — "
            f"No time difference"
        )


    statements = []


    # -------------------------
    # Speed
    # -------------------------

    statements.append(
        format_speed_sentence(
            observation[
                "min_speed_difference_kmh"
            ],
            "Minimum speed"
        )
    )

    statements.append(
        format_speed_sentence(
            observation[
                "section_end_speed_difference_kmh"
            ],
            "Section-end speed"
        )
    )


    # -------------------------
    # Braking
    # -------------------------

    statements.append(
        format_application_count(
            observation[
                "lap_brake_application_count"
            ],
            observation[
                "reference_brake_application_count"
            ],
            "brake"
        )
    )


    brake_onset_sentence = (
        format_timing_sentence(
            observation[
                "brake_onset_difference_m"
            ],
            "You braked",
            "You braked",
            (
                "You braked at the same "
                "point as the reference."
            )
        )
    )

    if brake_onset_sentence is not None:
        statements.append(
            brake_onset_sentence
        )


    brake_release_sentence = (
        format_timing_sentence(
            observation[
                "brake_release_difference_m"
            ],
            "You released the brakes",
            "You released the brakes",
            (
                "You released the brakes "
                "at the same point as "
                "the reference."
            )
        )
    )

    if brake_release_sentence is not None:
        statements.append(
            brake_release_sentence
        )


    # -------------------------
    # Throttle
    # -------------------------

    statements.append(
        format_application_count(
            observation[
                "lap_throttle_application_count"
            ],
            observation[
                "reference_throttle_application_count"
            ],
            "throttle"
        )
    )


    statements.append(
        format_full_lift(
            observation[
                "lap_full_lift"
            ],
            observation[
                "reference_full_lift"
            ]
        )
    )


    lap_throttle_interrupted = (
        observation[
            "lap_throttle_interrupted"
        ]
    )

    reference_throttle_interrupted = (
        observation[
            "reference_throttle_interrupted"
        ]
    )


    if (
        not lap_throttle_interrupted
        and
        not reference_throttle_interrupted
    ):

        statements.append(
            "Neither lap had a "
            "throttle interruption."
        )

    else:

        throttle_onset_sentence = (
            format_timing_sentence(
                observation[
                    "final_throttle_onset_difference_m"
                ],
                (
                    "Your final throttle "
                    "application began"
                ),
                (
                    "Your final throttle "
                    "application began"
                ),
                (
                    "Your final throttle "
                    "application began at "
                    "the same point as "
                    "the reference."
                )
            )
        )

        if (
            throttle_onset_sentence
            is not None
        ):

            statements.append(
                throttle_onset_sentence
            )

        

        lap_post_lift_count = (
            observation[
                "lap_post_full_throttle_lift_count"
            ]
        )
        
        reference_post_lift_count = (
            observation[
                "reference_post_full_throttle_lift_count"
            ]
        )
        
        
        if (
            lap_post_lift_count
            > reference_post_lift_count
        ):
        
            additional_lifts = (
                lap_post_lift_count
                - reference_post_lift_count
            )
        
            minimum_throttle = (
                observation[
                    "lap_post_full_throttle_minimum"
                ]
            )
        
        
            if additional_lifts == 1:
        
                sentence = (
                    "You had 1 additional "
                    "throttle lift after first "
                    "reaching full throttle"
                )
        
            else:
        
                sentence = (
                    f"You had {additional_lifts} "
                    f"additional throttle lifts "
                    f"after first reaching "
                    f"full throttle"
                )
        
        
            if minimum_throttle is not None:
        
                sentence += (
                    f", dropping to "
                    f"{minimum_throttle * 100:.0f}%."
                )
        
            else:
        
                sentence += "."
        
        
            statements.append(
                sentence
            )
        full_throttle_sentence = (
            format_timing_sentence(
                observation[
                    "full_throttle_difference_m"
                ],
                (
                    "Your final full-throttle "
                    "commitment occurred"
                ),
                (
                    "Your final full-throttle "
                    "commitment occurred"
                ),
                (
                    "Your final full-throttle "
                    "commitment occurred at "
                    "the same point as "
                    "the reference."
                )
            )
        )

        if (
            full_throttle_sentence
            is not None
        ):

            statements.append(
                full_throttle_sentence
            )


    # -------------------------
    # Racing line
    # -------------------------

    statements.append(
        format_racing_line(
            observation[
                "peak_line_deviation_m"
            ]
        )
    )


    return {
        "section_number":
            section_number,

        "headline":
            headline,

        "statements":
            statements
    }