"""Main window and layout for the telemetry analyzer UI."""

from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar,
)
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    """Resizable shell for the Motorsport Telemetry Performance Analyzer."""

    def __init__(self) -> None:
        super().__init__()
        self.selected_reference_lap = 5
        self.selected_section = 1

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

        session_label = QLabel("Monza — Practice")
        session_label.setObjectName("sessionValue")
        layout.addWidget(session_label)

        layout.addSpacing(4)
        layout.addWidget(self._create_section_label("Laps"))
        layout.addWidget(self._create_lap_row("5", "1:49.105", is_best=True))
        layout.addWidget(self._create_lap_row("7", "1:49.957"))
        layout.addWidget(self._create_lap_row("8", "1:50.747"))

        layout.addSpacing(4)
        layout.addWidget(self._create_section_label("Reference"))
        self.reference_combo_box = self._create_combo_box(["Lap 5", "Lap 7", "Lap 8"])
        layout.addWidget(self.reference_combo_box)

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
        self.section_combo_box.currentTextChanged.connect(self._on_section_changed)
        self._update_state_readout()

        layout.addStretch(1)
        return panel

    def _on_reference_changed(self, value: str) -> None:
        self.selected_reference_lap = int(value.split()[-1])
        self._update_state_readout()

    def _on_section_changed(self, value: str) -> None:
        self.selected_section = int(value.split()[-1])
        self._update_state_readout()

    def _update_state_readout(self) -> None:
        self.state_readout.setText(
            f"Reference: Lap {self.selected_reference_lap}\n"
            f"Section: S{self.selected_section}"
        )

    @staticmethod
    def _create_section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionLabel")
        return label

    @staticmethod
    def _create_lap_row(
        lap_number: str,
        lap_time: str,
        is_best: bool = False,
    ) -> QWidget:
        row = QWidget()
        row.setObjectName("bestLapRow" if is_best else "lapRow")

        layout = QHBoxLayout(row)
        layout.setContentsMargins(2, 4, 2, 4)
        layout.setSpacing(6)

        lap_label = QLabel(lap_number)
        lap_label.setObjectName("bestLapText" if is_best else "lapText")
        layout.addWidget(lap_label)

        time_label = QLabel(lap_time)
        time_label.setObjectName("bestLapText" if is_best else "lapTime")
        time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        time_label.setMinimumWidth(66)
        layout.addWidget(time_label)
        layout.addStretch(1)

        status_label = QLabel("BEST" if is_best else "")
        status_label.setObjectName("bestText" if is_best else "lapStatus")
        status_label.setMinimumWidth(34)
        if is_best:
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
            get_telemetry_lap_legend_entries,
            set_graph_visibility,
            set_lap_visibility,
        )

        self.telemetry_figure = create_telemetry_figure()
        legend_entries = get_telemetry_lap_legend_entries()
        canvas = self.telemetry_figure.canvas

        if not isinstance(canvas, FigureCanvas):
            raise RuntimeError("The telemetry figure is not using a Qt canvas.")

        self.telemetry_canvas = canvas
        self.telemetry_toolbar = NavigationToolbar(self.telemetry_canvas, panel)
        self.telemetry_toolbar.setObjectName("telemetryToolbar")
        self.telemetry_lap_controls = self._create_lap_visibility_controls(
            legend_entries,
            set_lap_visibility,
        )
        self.telemetry_channel_controls = self._create_channel_visibility_controls(
            set_graph_visibility
        )

        layout.addWidget(self.telemetry_toolbar)
        layout.addWidget(self.telemetry_lap_controls)
        layout.addWidget(self.telemetry_channel_controls)
        layout.addWidget(self.telemetry_canvas, 1)
        return panel

    def _create_lap_visibility_controls(
        self,
        entries: list[tuple[int, str, str, bool]],
        set_visibility,
    ) -> QWidget:
        controls = QWidget()
        controls.setObjectName("telemetryControlRow")

        layout = QHBoxLayout(controls)
        layout.setContentsMargins(1, 0, 1, 2)
        layout.setSpacing(8)

        row_label = QLabel("Laps:")
        row_label.setObjectName("telemetryControlRowLabel")
        layout.addWidget(row_label)

        self.lap_visibility_controls = {}

        for lap_number, label, color, is_reference in entries:
            control = QCheckBox(f"{label}{'  REF' if is_reference else ''}")
            control.setObjectName("telemetryLapControl")
            control.setChecked(True)
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
            control.toggled.connect(
                lambda visible, number=lap_number: set_visibility(number, visible)
            )
            self.lap_visibility_controls[lap_number] = control
            layout.addWidget(control)

        layout.addStretch(1)
        return controls

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
        layout.addWidget(self._create_field_placeholder("Section"))

        mode_placeholder = QLabel("Raw / Summary selection")
        mode_placeholder.setObjectName("inspectionPlaceholder")
        layout.addWidget(mode_placeholder)

        analysis_placeholder = QLabel("Analysis output")
        analysis_placeholder.setObjectName("inspectionPlaceholder")
        analysis_placeholder.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(analysis_placeholder, 1)
        return panel

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
