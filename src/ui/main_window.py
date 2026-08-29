"""Main window and layout for the telemetry analyzer UI."""

from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar,
)
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    """Resizable shell for the Motorsport Telemetry Performance Analyzer."""

    LAP_PLACEHOLDER = "Select lap..."

    def __init__(self) -> None:
        super().__init__()

        from src.analysis.shared_memory_laps import (
            clear_pair_analysis_plots,
            get_or_calculate_pair_analysis,
            get_telemetry_lap_entries,
            get_telemetry_lap_legend_entries,
            get_telemetry_session_display_name,
            set_lap_visibility,
            set_reference_style,
            update_pair_analysis,
            zoom_to_analysis_section,
        )

        self.clear_pair_analysis_plots = clear_pair_analysis_plots
        self.get_or_calculate_pair_analysis = get_or_calculate_pair_analysis
        self.get_telemetry_lap_legend_entries = (
            get_telemetry_lap_legend_entries
        )
        self.set_telemetry_reference_style = set_reference_style
        self.set_telemetry_lap_visibility = set_lap_visibility
        self.update_telemetry_pair_analysis = update_pair_analysis
        self.zoom_to_telemetry_section = zoom_to_analysis_section
        self.session_display_name = get_telemetry_session_display_name()
        self.session_lap_entries = get_telemetry_lap_entries()
        self.selected_reference_lap = next(
            lap_number
            for lap_number, _lap_time, _lap_delta, is_best
            in self.session_lap_entries
            if is_best
        )
        self.set_telemetry_reference_style(self.selected_reference_lap)
        reference_entries = self.get_telemetry_lap_legend_entries(
            self.selected_reference_lap
        )
        self.lap_display_colors = {
            lap_number: color
            for lap_number, _label, color, _is_reference in reference_entries
        }
        self.reference_lap_numbers = sorted(
            lap_number
            for lap_number, _label, _color, _is_reference in reference_entries
        )
        self.selected_compare_lap = None
        self.selected_section = 1
        self.analysis_cache = {}
        self.current_pair_analysis = None

        self.setWindowTitle("Motorsport Telemetry Performance Analyzer")
        self.resize(1280, 760)
        self.setMinimumSize(900, 560)

        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(16, 14, 16, 16)
        root_layout.setSpacing(10)

        header = QLabel("Motorsport Telemetry Performance Analyzer")
        header.setObjectName("headerTitle")
        root_layout.addWidget(header)

        panels_layout = QHBoxLayout()
        panels_layout.setSpacing(0)
        root_layout.addLayout(panels_layout, 1)

        panels_layout.addWidget(self._build_left_panel(), 15)
        panels_layout.addWidget(self._build_center_panel(), 65)
        panels_layout.addWidget(self._build_right_panel(), 20)

    def _build_left_panel(self) -> QFrame:
        panel, layout = self._create_panel("LAPS")
        panel.setObjectName("leftPanel")
        layout.setSpacing(6)

        layout.addWidget(self._create_section_label("Session"))

        session_label = QLabel(self.session_display_name)
        session_label.setObjectName("sessionValue")
        layout.addWidget(session_label)

        layout.addSpacing(4)
        layout.addWidget(self._create_section_label("Laps"))
        self.lap_visibility_controls = {}

        for (
            lap_number,
            lap_time,
            lap_delta_to_best,
            is_best,
        ) in self.session_lap_entries:
            layout.addWidget(
                self._create_lap_row(
                    lap_number,
                    lap_time,
                    lap_delta_to_best,
                    self.lap_display_colors[lap_number],
                    is_best=is_best,
                )
            )

        layout.addSpacing(4)
        layout.addWidget(self._create_section_label("Reference"))
        self.reference_combo_box = self._create_combo_box(
            [self.LAP_PLACEHOLDER]
            + [f"Lap {lap_number}" for lap_number in self.reference_lap_numbers]
        )
        self.reference_combo_box.setCurrentText(
            f"Lap {self.selected_reference_lap}"
        )
        layout.addWidget(self.reference_combo_box)

        layout.addSpacing(2)
        layout.addWidget(self._create_section_label("Compare"))
        self.compare_combo_box = self._create_combo_box(
            [self.LAP_PLACEHOLDER]
            + [
                f"Lap {lap_number}"
                for lap_number in self.reference_lap_numbers
                if lap_number != self.selected_reference_lap
            ]
        )
        layout.addWidget(self.compare_combo_box)

        layout.addSpacing(2)
        layout.addWidget(self._create_section_label("Section"))
        self.section_combo_box = self._create_combo_box(
            [f"Section {number}" for number in range(1, 8)]
        )
        layout.addWidget(self.section_combo_box)

        self.state_readout = QLabel()
        self.state_readout.setObjectName("stateReadout")
        layout.addWidget(self.state_readout)

        self.reference_combo_box.currentTextChanged.connect(
            self._on_reference_changed
        )
        self.compare_combo_box.currentTextChanged.connect(
            self._on_compare_changed
        )
        self.section_combo_box.currentTextChanged.connect(self._on_section_changed)
        self._update_state_readout()

        layout.addStretch(1)
        return panel

    def _on_reference_changed(self, value: str) -> None:
        self.selected_reference_lap = self._lap_number_from_text(value)
        self._refresh_compare_options()
        self.set_telemetry_reference_style(self.selected_reference_lap)
        self._update_lap_reference_controls(
            self.get_telemetry_lap_legend_entries(
                self.selected_reference_lap
            )
        )
        self._request_pair_analysis()
        self._update_state_readout()

    def _on_compare_changed(self, value: str) -> None:
        self.selected_compare_lap = self._lap_number_from_text(value)
        self._request_pair_analysis()
        self._update_state_readout()

    def _on_section_changed(self, value: str) -> None:
        self.selected_section = int(value.split()[-1])
        self.zoom_to_telemetry_section(self.selected_section)
        self._update_state_readout()
        self.refresh_analysis_panel()

    def _update_state_readout(self) -> None:
        reference_text = (
            f"Lap {self.selected_reference_lap}"
            if self.selected_reference_lap is not None
            else self.LAP_PLACEHOLDER
        )
        compare_text = (
            f"Lap {self.selected_compare_lap}"
            if self.selected_compare_lap is not None
            else self.LAP_PLACEHOLDER
        )
        self.state_readout.setText(
            f"Reference: {reference_text}\n"
            f"Compare: {compare_text}\n"
            f"Section: S{self.selected_section}"
        )

    def _refresh_compare_options(self) -> None:
        selected_compare_lap = self.selected_compare_lap

        if selected_compare_lap == self.selected_reference_lap:
            selected_compare_lap = None

        compare_laps = [
            lap_number
            for lap_number in self.reference_lap_numbers
            if lap_number != self.selected_reference_lap
        ]
        self.compare_combo_box.blockSignals(True)
        self.compare_combo_box.clear()
        self.compare_combo_box.addItems(
            [self.LAP_PLACEHOLDER]
            + [f"Lap {lap_number}" for lap_number in compare_laps]
        )
        self.compare_combo_box.setCurrentText(
            f"Lap {selected_compare_lap}"
            if selected_compare_lap is not None
            else self.LAP_PLACEHOLDER
        )
        self.compare_combo_box.blockSignals(False)
        self.selected_compare_lap = selected_compare_lap

    def _request_pair_analysis(self) -> None:
        if (
            self.selected_reference_lap is None
            or self.selected_compare_lap is None
            or self.selected_reference_lap == self.selected_compare_lap
        ):
            self.current_pair_analysis = None
            self.clear_pair_analysis_plots()
            self.refresh_analysis_panel()
            return

        self.current_pair_analysis = self.get_or_calculate_pair_analysis(
            self.analysis_cache,
            self.selected_reference_lap,
            self.selected_compare_lap,
        )
        self.update_telemetry_pair_analysis(
            self.selected_reference_lap,
            self.selected_compare_lap,
            self.current_pair_analysis,
        )
        self.refresh_analysis_panel()

    @classmethod
    def _lap_number_from_text(cls, value: str) -> int | None:
        if value == cls.LAP_PLACEHOLDER:
            return None

        return int(value.split()[-1])

    @staticmethod
    def _create_section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionLabel")
        return label

    def _create_lap_row(
        self,
        lap_number: int,
        lap_time: str,
        lap_delta_to_best: str,
        color: str,
        is_best: bool = False,
    ) -> QWidget:
        row = QWidget()
        row.setObjectName("bestLapRow" if is_best else "lapRow")

        layout = QHBoxLayout(row)
        layout.setContentsMargins(2, 4, 2, 4)
        layout.setSpacing(6)

        visibility_control = QCheckBox()
        visibility_control.setObjectName("telemetryLapControl")
        visibility_control.setChecked(True)
        visibility_control.setMinimumWidth(70)
        self._style_lap_visibility_control(
            visibility_control,
            f"Lap {lap_number}",
            color,
            lap_number == self.selected_reference_lap,
        )
        visibility_control.toggled.connect(
            lambda visible, number=lap_number: (
                self.set_telemetry_lap_visibility(number, visible)
            )
        )
        self.lap_visibility_controls[lap_number] = visibility_control
        layout.addWidget(visibility_control)

        time_label = QLabel(lap_time)
        time_label.setObjectName("bestLapText" if is_best else "lapTime")
        time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        time_label.setMinimumWidth(66)
        layout.addWidget(time_label)
        status_label = QLabel(lap_delta_to_best)
        status_label.setObjectName("bestText" if is_best else "lapDelta")
        status_label.setMinimumWidth(46)
        status_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        layout.addWidget(status_label)

        return row

    @staticmethod
    def _create_combo_box(items: list[str]) -> QComboBox:
        combo_box = QComboBox()
        combo_box.setObjectName("panelComboBox")
        combo_box.addItems(items)
        return combo_box

    def _build_center_panel(self) -> QFrame:
        panel, layout = self._create_panel("Telemetry")
        panel.setObjectName("workspacePanel")

        from src.analysis.shared_memory_laps import (
            create_telemetry_figure,
            set_graph_visibility,
        )

        self.telemetry_figure = create_telemetry_figure()
        canvas = self.telemetry_figure.canvas

        if not isinstance(canvas, FigureCanvas):
            raise RuntimeError("The telemetry figure is not using a Qt canvas.")

        self.telemetry_canvas = canvas
        self.telemetry_toolbar = NavigationToolbar(self.telemetry_canvas, panel)
        self.telemetry_toolbar.setObjectName("telemetryToolbar")
        self.telemetry_channel_controls = self._create_channel_visibility_controls(
            set_graph_visibility
        )

        layout.addWidget(self.telemetry_toolbar)
        layout.addWidget(self.telemetry_channel_controls)
        layout.addWidget(self.telemetry_canvas, 1)
        return panel

    def _update_lap_reference_controls(
        self,
        entries: list[tuple[int, str, str, bool]],
    ) -> None:
        for lap_number, label, color, is_reference in entries:
            self._style_lap_visibility_control(
                self.lap_visibility_controls[lap_number],
                label,
                color,
                is_reference,
            )

    @staticmethod
    def _style_lap_visibility_control(
        control: QCheckBox,
        label: str,
        color: str,
        is_reference: bool,
    ) -> None:
        control.setText(f"{label}{'  REF' if is_reference else ''}")
        control.setStyleSheet(
            f"QCheckBox {{ color: {color}; }} "
            "QCheckBox:unchecked { color: #5f645c; } "
            f"QCheckBox::indicator:checked {{ "
            f"background-color: {color}; border-color: {color}; "
            "} "
            "QCheckBox::indicator:unchecked { "
            "background-color: transparent; border-color: #555a52; "
            "}"
        )

    def _create_channel_visibility_controls(self, set_visibility) -> QWidget:
        controls = QWidget()
        controls.setObjectName("telemetryControlRow")

        layout = QHBoxLayout(controls)
        layout.setContentsMargins(1, 0, 1, 2)
        layout.setSpacing(10)

        row_label = QLabel("Channels:")
        row_label.setObjectName("telemetryControlRowLabel")
        layout.addWidget(row_label)

        initial_states = [
            ("Spd", True),
            ("Brk", True),
            ("Thr", True),
            ("Dlt", False),
            ("Str", False),
            ("Dev", False),
            ("Line", False),
        ]

        self.channel_visibility_controls = {}

        for channel, is_visible in initial_states:
            control = QCheckBox(channel)
            control.setObjectName("telemetryChannelControl")
            control.setChecked(is_visible)
            control.toggled.connect(
                lambda visible, name=channel: set_visibility(name, visible)
            )
            self.channel_visibility_controls[channel] = control
            layout.addWidget(control)

        layout.addStretch(1)
        return controls

    def _build_right_panel(self) -> QFrame:
        panel, layout = self._create_panel("Analysis")
        panel.setObjectName("rightPanel")

        mode_controls = QWidget()
        mode_controls.setObjectName("analysisModeControls")
        mode_layout = QHBoxLayout(mode_controls)
        mode_layout.setContentsMargins(0, 0, 0, 2)
        mode_layout.setSpacing(12)

        self.analysis_mode_group = QButtonGroup(self)
        self.analysis_mode_group.setExclusive(True)
        self.raw_mode_button = QPushButton("Raw")
        self.summary_mode_button = QPushButton("Summary")

        for button in (self.raw_mode_button, self.summary_mode_button):
            button.setObjectName("analysisModeButton")
            button.setCheckable(True)
            button.setFlat(True)
            self.analysis_mode_group.addButton(button)
            mode_layout.addWidget(button)

        mode_layout.addStretch(1)
        self.analysis_mode = "summary"
        self.summary_mode_button.setChecked(True)
        self.raw_mode_button.clicked.connect(
            lambda _checked: self._set_analysis_mode("raw")
        )
        self.summary_mode_button.clicked.connect(
            lambda _checked: self._set_analysis_mode("summary")
        )
        layout.addWidget(mode_controls)

        self.analysis_scroll_area = QScrollArea()
        self.analysis_scroll_area.setObjectName("analysisScrollArea")
        self.analysis_scroll_area.setWidgetResizable(True)
        self.analysis_scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.analysis_scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.analysis_content = QWidget()
        self.analysis_content.setObjectName("analysisContent")
        self.analysis_content_layout = QVBoxLayout(self.analysis_content)
        self.analysis_content_layout.setContentsMargins(1, 2, 5, 2)
        self.analysis_content_layout.setSpacing(5)
        self.analysis_scroll_area.setWidget(self.analysis_content)
        layout.addWidget(self.analysis_scroll_area, 1)

        self.refresh_analysis_panel()
        return panel

    def _set_analysis_mode(self, mode: str) -> None:
        self.analysis_mode = mode
        self.refresh_analysis_panel()

    def refresh_analysis_panel(self) -> None:
        while self.analysis_content_layout.count():
            item = self.analysis_content_layout.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        if self.current_pair_analysis is None:
            self._add_analysis_label(
                "Select a reference and comparison lap.",
                "analysisEmptyState",
            )
            self.analysis_content_layout.addStretch(1)
            return

        self._add_analysis_label(
            self._format_overall_lap_difference(
                self.current_pair_analysis[
                    "overall_lap_time_difference_s"
                ]
            ),
            "analysisOverallHeadline",
        )

        result_key = (
            "observations"
            if self.analysis_mode == "raw"
            else "conclusions"
        )
        section_result = next(
            (
                result
                for result in self.current_pair_analysis[result_key]
                if result["section_number"] == self.selected_section
            ),
            None,
        )

        if section_result is None:
            self._add_analysis_label(
                f"Section {self.selected_section} is unavailable.",
                "analysisEmptyState",
            )
        elif self.analysis_mode == "raw":
            self._show_raw_section(section_result)
        else:
            self._show_summary_section(section_result)

        self.analysis_content_layout.addStretch(1)

    def _show_raw_section(self, observation: dict) -> None:
        self._add_analysis_label(
            f"Section {observation['section_number']}",
            "analysisHeadline",
        )
        self._add_raw_field(
            "Section delta",
            self._format_signed_value(observation["section_delta_s"], "s", 3),
        )
        self._add_raw_field(
            "Minimum speed",
            self._format_signed_value(
                observation["min_speed_difference_kmh"],
                "km/h",
                1,
            ),
        )
        self._add_raw_field(
            "Section-end speed",
            self._format_signed_value(
                observation["section_end_speed_difference_kmh"],
                "km/h",
                1,
            ),
        )
        self._add_raw_field(
            "Brake applications",
            f"{observation['lap_brake_application_count']} "
            f"(ref {observation['reference_brake_application_count']})",
        )
        self._add_raw_field(
            "Initial brake onset",
            self._format_signed_value(
                observation["brake_onset_difference_m"],
                "m",
                1,
            ),
        )
        self._add_raw_field(
            "Final brake release",
            self._format_signed_value(
                observation["brake_release_difference_m"],
                "m",
                1,
            ),
        )
        self._add_raw_field(
            "Throttle applications",
            f"{observation['lap_throttle_application_count']} "
            f"(ref {observation['reference_throttle_application_count']})",
        )
        self._add_raw_field(
            "Full lift",
            f"{self._format_boolean(observation['lap_full_lift'])} "
            f"(ref {self._format_boolean(observation['reference_full_lift'])})",
        )
        self._add_raw_field(
            "Coasting distance",
            self._format_signed_value(
                observation["coasting_distance_difference_m"],
                "m",
                1,
            ),
            (
                f"lap {observation['lap_coasting_distance_m']:.1f} m / "
                f"ref {observation['reference_coasting_distance_m']:.1f} m"
            ),
        )
        self._add_raw_field(
            "Final throttle application",
            self._format_signed_value(
                observation["final_throttle_onset_difference_m"],
                "m",
                1,
            ),
        )
        self._add_raw_field(
            "Full throttle reached",
            self._format_signed_value(
                observation["full_throttle_difference_m"],
                "m",
                1,
            ),
        )
        self._add_raw_field(
            "Post-full-throttle lifts",
            f"{observation['lap_post_full_throttle_lift_count']} "
            f"(ref {observation['reference_post_full_throttle_lift_count']})",
        )

        lap_minimum = observation["lap_post_full_throttle_minimum"]
        reference_minimum = observation["reference_post_full_throttle_minimum"]

        if lap_minimum is not None or reference_minimum is not None:
            self._add_raw_field(
                "Post-full-throttle minimum",
                f"lap {self._format_percentage(lap_minimum)} / "
                f"ref {self._format_percentage(reference_minimum)}",
            )

        self._add_raw_field(
            "Peak line deviation",
            self._format_line_deviation(
                observation["peak_line_deviation_m"]
            ),
        )

    def _show_summary_section(self, conclusion: dict) -> None:
        self._add_analysis_label(
            conclusion["headline"],
            "analysisHeadline",
        )

        for group_name, statements in conclusion["groups"].items():
            if not statements:
                continue

            self._add_analysis_label(
                group_name.upper(),
                "analysisGroupHeading",
            )

            for statement in statements:
                self._add_analysis_label(
                    statement,
                    "analysisSummaryText",
                )

    def _add_raw_field(
        self,
        name: str,
        value: str,
        detail: str | None = None,
    ) -> None:
        self._add_analysis_label(name, "analysisRawName")
        self._add_analysis_label(value, "analysisRawValue")

        if detail is not None:
            self._add_analysis_label(detail, "analysisRawDetail")

        self.analysis_content_layout.addSpacing(4)

    def _add_analysis_label(self, text: str, object_name: str) -> None:
        label = QLabel(text)
        label.setObjectName(object_name)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.analysis_content_layout.addWidget(label)

    @staticmethod
    def _format_signed_value(value, unit: str, decimals: int) -> str:
        if value is None:
            return "Not comparable"

        return f"{float(value):+.{decimals}f} {unit}"

    @staticmethod
    def _format_boolean(value) -> str:
        if value is None:
            return "Not available"

        return "Yes" if value else "No"

    @staticmethod
    def _format_percentage(value) -> str:
        if value is None:
            return "not available"

        return f"{float(value) * 100:.0f}%"

    @staticmethod
    def _format_line_deviation(value) -> str:
        if value is None:
            return "Not comparable"

        value = float(value)

        if value < 0:
            direction = "left"
        elif value > 0:
            direction = "right"
        else:
            direction = "center"

        return f"{abs(value):.2f} m {direction}"

    def _format_overall_lap_difference(self, value) -> str:
        rounded_difference = round(abs(float(value)), 3)

        if rounded_difference == 0:
            difference_text = (
                f"No time difference to Lap {self.selected_reference_lap}"
            )
        elif value > 0:
            difference_text = (
                f"Lost {rounded_difference:.3f} s "
                f"to Lap {self.selected_reference_lap}"
            )
        else:
            difference_text = (
                f"Gained {rounded_difference:.3f} s "
                f"on Lap {self.selected_reference_lap}"
            )

        return f"Lap {self.selected_compare_lap} - {difference_text}"

    @staticmethod
    def _create_panel(title: str) -> tuple[QFrame, QVBoxLayout]:
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(9)

        title_label = QLabel(title)
        title_label.setObjectName("panelTitle")
        layout.addWidget(title_label)
        return panel, layout

    @staticmethod
    def _create_field_placeholder(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("fieldPlaceholder")
        label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        return label
