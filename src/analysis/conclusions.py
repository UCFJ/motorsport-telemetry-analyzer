SPEED_DISPLAY_THRESHOLD = 1.0
POSITION_DISPLAY_THRESHOLD = 1.0
COASTING_DISPLAY_THRESHOLD = 1.0
LINE_DISPLAY_THRESHOLD = 0.5
TIME_DISPLAY_THRESHOLD = 0.020


def format_timing_sentence(
    value,
    label
):

    if value is None:
        return None

    if abs(float(value)) < POSITION_DISPLAY_THRESHOLD:
        return None

    difference = round(
        abs(float(value)),
        1
    )

    if value < 0:
        direction = "earlier"
    else:
        direction = "later"

    return (
        f"{label}: "
        f"{difference:.1f} m {direction}."
    )


def format_speed_sentence(
    value,
    label
):

    if abs(float(value)) < SPEED_DISPLAY_THRESHOLD:
        return None

    difference = round(
        abs(float(value)),
        1
    )

    if value > 0:
        direction = "higher"
    else:
        direction = "lower"

    return (
        f"{label}: "
        f"{difference:.1f} km/h {direction}."
    )


def format_application_count(
    lap_count,
    reference_count,
    input_name
):

    if lap_count == reference_count:
        return None

    return (
        f"{input_name} applications: "
        f"{lap_count} vs {reference_count} reference."
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


def format_coasting_distance(
    value
):

    if abs(float(value)) < COASTING_DISPLAY_THRESHOLD:
        return None

    difference = round(
        abs(float(value)),
        1
    )

    if value > 0:
        direction = "more"
    else:
        direction = "less"

    return (
        f"Coasting: "
        f"{difference:.1f} m {direction}."
    )


def format_racing_line(
    value
):

    if abs(float(value)) < LINE_DISPLAY_THRESHOLD:
        return None

    deviation = round(
        abs(float(value)),
        1
    )

    if value < 0:
        direction = "left"
    else:
        direction = "right"

    return (
        f"Peak line deviation: "
        f"{deviation:.1f} m {direction}."
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
    # Headline
    # -------------------------

    if abs(section_delta) < TIME_DISPLAY_THRESHOLD:

        headline = (
            f"Section {section_number} — "
            f"No time difference"
        )

    elif section_delta > 0:

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


    # -------------------------
    # Output groups
    # -------------------------

    speed = []
    braking = []
    throttle = []
    racing_line = []


    # -------------------------
    # Speed
    # -------------------------

    minimum_speed_sentence = (
        format_speed_sentence(
            observation[
                "min_speed_difference_kmh"
            ],
            "Minimum speed"
        )
    )

    if minimum_speed_sentence is not None:

        speed.append(
            minimum_speed_sentence
        )


    section_end_speed_sentence = (
        format_speed_sentence(
            observation[
                "section_end_speed_difference_kmh"
            ],
            "Section-end speed"
        )
    )

    if section_end_speed_sentence is not None:

        speed.append(
            section_end_speed_sentence
        )


    # -------------------------
    # Braking
    # -------------------------

    brake_count_sentence = (
        format_application_count(
            observation[
                "lap_brake_application_count"
            ],
            observation[
                "reference_brake_application_count"
            ],
            "Brake"
        )
    )

    if brake_count_sentence is not None:

        braking.append(
            brake_count_sentence
        )


    brake_onset_sentence = (
        format_timing_sentence(
            observation[
                "brake_onset_difference_m"
            ],
            "Brake onset"
        )
    )

    if brake_onset_sentence is not None:

        braking.append(
            brake_onset_sentence
        )


    brake_release_sentence = (
        format_timing_sentence(
            observation[
                "brake_release_difference_m"
            ],
            "Brake release"
        )
    )

    if brake_release_sentence is not None:

        braking.append(
            brake_release_sentence
        )


    # -------------------------
    # Throttle
    # -------------------------

    throttle_count_sentence = (
        format_application_count(
            observation[
                "lap_throttle_application_count"
            ],
            observation[
                "reference_throttle_application_count"
            ],
            "Throttle"
        )
    )

    if throttle_count_sentence is not None:

        throttle.append(
            throttle_count_sentence
        )


    coasting_sentence = (
        format_coasting_distance(
            observation[
                "coasting_distance_difference_m"
            ]
        )
    )

    if coasting_sentence is not None:

        throttle.append(
            coasting_sentence
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
        lap_throttle_interrupted
        or
        reference_throttle_interrupted
    ):

        throttle_onset_sentence = (
            format_timing_sentence(
                observation[
                    "final_throttle_onset_difference_m"
                ],
                "Final throttle application"
            )
        )

        if throttle_onset_sentence is not None:

            throttle.append(
                throttle_onset_sentence
            )


        full_throttle_sentence = (
            format_timing_sentence(
                observation[
                    "full_throttle_difference_m"
                ],
                "Full throttle reached"
            )
        )

        if full_throttle_sentence is not None:

            throttle.append(
                full_throttle_sentence
            )


    # -------------------------
    # Extra lifts after reaching
    # full throttle
    # -------------------------

    additional_lifts = (
        observation[
            "post_full_throttle_lift_count_difference"
        ]
    )

    if additional_lifts > 0:

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

        throttle.append(
            sentence
        )


    # -------------------------
    # Racing line
    # -------------------------

    racing_line_sentence = (
        format_racing_line(
            observation[
                "peak_line_deviation_m"
            ]
        )
    )

    if racing_line_sentence is not None:

        racing_line.append(
            racing_line_sentence
        )


    # -------------------------
    # Structured wording layer
    # -------------------------

    groups = {
        group_name: group_statements
        for group_name, group_statements in (
            ("Speed", speed),
            ("Braking", braking),
            ("Throttle", throttle),
            ("Racing line", racing_line)
        )
        if group_statements
    }


    # Keep flat statements as well
    # so existing code does not break.
    statements = (
        speed
        + braking
        + throttle
        + racing_line
    )


    return {
        "section_number":
            section_number,

        "headline":
            headline,

        "groups":
            groups,

        "statements":
            statements
    }
