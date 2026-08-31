"""Main window and layout for the telemetry analyzer UI."""

from pathlib import Path
import sys
import tempfile
import uuid

from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar,
)
from matplotlib.figure import Figure
from PySide6.QtCore import QProcess, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.analysis.session_loader import load_session_candidate
from src.ingestion.paths import (
    PROJECT_ROOT,
    get_default_shared_memory_output_dir,
)


class MainWindow(QMainWindow):
    """Resizable shell for the Motorsport Telemetry Performance Analyzer."""

    LAP_PLACEHOLDER = "Select lap..."
    SECTION_PLACEHOLDER = "Select section..."
    SESSION_BINDING_NAMES = (
        "clear_pair_analysis_plots",
        "get_or_calculate_pair_analysis",
        "get_telemetry_lap_legend_entries",
        "get_telemetry_section_numbers",
        "set_telemetry_reference_style",
        "set_telemetry_lap_visibility",
        "restore_telemetry_full_lap_view",
        "update_telemetry_pair_analysis",
        "zoom_to_telemetry_section",
    )

    def __init__(self) -> None:
        super().__init__()

        self.telemetry_session = None
        self.current_session_path = None
        self.session_display_name = "No session loaded"
        self.session_lap_entries = []
        self.selected_reference_lap = None
        self.selected_compare_lap = None
        self.selected_section = None
        self.analysis_cache = {}
        self.current_pair_analysis = None
        self.pair_only_enabled = True
        self.normal_lap_visibility = {}
        self.lap_display_colors = {}
        self.reference_lap_numbers = []
        self.section_numbers = []
        self.logging_output_dir = get_default_shared_memory_output_dir()
        self.logger_stop_requested = False
        self.logger_error_reported = False
        self.logger_stop_file = None
        self.logger_process = QProcess(self)
        self.logger_process.setProcessChannelMode(
            QProcess.ProcessChannelMode.ForwardedChannels
        )
        self.logger_process.started.connect(self._on_logger_started)
        self.logger_process.errorOccurred.connect(self._on_logger_error)
        self.logger_process.finished.connect(self._on_logger_finished)

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
        self._set_session_controls_enabled(False)

    def _bind_telemetry_session(self, telemetry_session) -> None:
        self.telemetry_session = telemetry_session
        self.clear_pair_analysis_plots = (
            telemetry_session.clear_pair_analysis_plots
        )
        self.get_or_calculate_pair_analysis = (
            telemetry_session.get_or_calculate_pair_analysis
        )
        self.get_telemetry_lap_legend_entries = (
            telemetry_session.get_telemetry_lap_legend_entries
        )
        self.get_telemetry_section_numbers = (
            telemetry_session.get_telemetry_section_numbers
        )
        self.set_telemetry_reference_style = (
            telemetry_session.set_reference_style
        )
        self.set_telemetry_lap_visibility = telemetry_session.set_lap_visibility
        self.restore_telemetry_full_lap_view = (
            telemetry_session.restore_full_lap_view
        )
        self.update_telemetry_pair_analysis = telemetry_session.update_pair_analysis
        self.zoom_to_telemetry_section = (
            telemetry_session.zoom_to_analysis_section
        )

    def _build_left_panel(self) -> QFrame:
        panel, layout = self._create_panel("LAPS")
        panel.setObjectName("leftPanel")
        layout.setSpacing(6)

        layout.addWidget(self._create_section_label("Session"))

        self.session_label = QLabel(self.session_display_name)
        self.session_label.setObjectName("sessionValue")
        layout.addWidget(self.session_label)

        self.open_session_button = QPushButton("Open session")
        self.open_session_button.setObjectName("openSessionButton")
        self.open_session_button.setSizePolicy(
            QSizePolicy.Policy.Maximum,
            QSizePolicy.Policy.Fixed,
        )
        self.open_session_button.clicked.connect(self._open_session)
        layout.addWidget(self.open_session_button)

        layout.addSpacing(4)
        layout.addWidget(self._create_section_label("Logging"))
        layout.addWidget(self._create_section_label("Save to:"))

        self.logging_directory_label = QLabel(str(self.logging_output_dir))
        self.logging_directory_label.setObjectName("loggingDirectoryValue")
        self.logging_directory_label.setToolTip(str(self.logging_output_dir))
        self.logging_directory_label.setWordWrap(True)
        layout.addWidget(self.logging_directory_label)

        logging_buttons = QWidget()
        logging_buttons_layout = QHBoxLayout(logging_buttons)
        logging_buttons_layout.setContentsMargins(0, 0, 0, 0)
        logging_buttons_layout.setSpacing(6)
        self.choose_logging_folder_button = QPushButton("Choose folder")
        self.choose_logging_folder_button.setObjectName("loggingControlButton")
        self.choose_logging_folder_button.clicked.connect(
            self._choose_logging_directory
        )
        logging_buttons_layout.addWidget(self.choose_logging_folder_button)
        self.logging_toggle_button = QPushButton("Start logging")
        self.logging_toggle_button.setObjectName("loggingControlButton")
        self.logging_toggle_button.clicked.connect(self._toggle_logging)
        logging_buttons_layout.addWidget(self.logging_toggle_button)
        layout.addWidget(logging_buttons)

        self.logging_status_label = QLabel("Status: Not logging")
        self.logging_status_label.setObjectName("loggingStatusValue")
        layout.addWidget(self.logging_status_label)

        layout.addSpacing(4)

        laps_header = QWidget()
        laps_header_layout = QHBoxLayout(laps_header)
        laps_header_layout.setContentsMargins(0, 0, 0, 0)
        laps_header_layout.setSpacing(6)
        laps_header_layout.addWidget(self._create_section_label("Laps"))
        laps_header_layout.addStretch(1)
        self.pair_only_control = QCheckBox("Pair only")
        self.pair_only_control.setObjectName("pairOnlyControl")
        self.pair_only_control.setChecked(self.pair_only_enabled)
        laps_header_layout.addWidget(self.pair_only_control)
        layout.addWidget(laps_header)

        self.lap_visibility_controls = {}
        self.lap_rows = {}
        self.laps_container = QWidget()
        self.laps_container.setObjectName("lapsContainer")
        self.laps_layout = QVBoxLayout(self.laps_container)
        self.laps_layout.setContentsMargins(0, 0, 0, 0)
        self.laps_layout.setSpacing(6)
        self.laps_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.laps_scroll_area = QScrollArea()
        self.laps_scroll_area.setObjectName("lapsScrollArea")
        self.laps_scroll_area.setWidgetResizable(True)
        self.laps_scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.laps_scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.laps_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.laps_scroll_area.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.laps_scroll_area.setWidget(self.laps_container)
        layout.addWidget(self.laps_scroll_area, 1)
        self._rebuild_lap_rows()

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
            [self.SECTION_PLACEHOLDER]
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
        self.pair_only_control.toggled.connect(self._set_pair_only_enabled)
        self._apply_pair_only_visibility(
            laps_to_show=self._selected_pair_laps()
        )
        self._update_state_readout()

        return panel

    def _set_session_controls_enabled(self, enabled: bool) -> None:
        self.reference_combo_box.setEnabled(enabled)
        self.compare_combo_box.setEnabled(enabled)
        self.section_combo_box.setEnabled(enabled)
        self.pair_only_control.setEnabled(enabled)

    def _choose_logging_directory(self) -> None:
        selected_directory = QFileDialog.getExistingDirectory(
            self,
            "Choose telemetry logging folder",
            str(self.logging_output_dir),
        )

        if not selected_directory:
            return

        self.logging_output_dir = Path(selected_directory)
        directory_text = str(self.logging_output_dir)
        self.logging_directory_label.setText(directory_text)
        self.logging_directory_label.setToolTip(directory_text)

    def _toggle_logging(self) -> None:
        if self.logger_process.state() == QProcess.ProcessState.NotRunning:
            self._start_logging()
        else:
            self._stop_logging()

    def _start_logging(self) -> None:
        self._clear_logger_stop_file()

        try:
            self.logging_output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            print(f"LOGGER START FAILED: {error}")
            self._show_logger_error("Could not start telemetry logging.")
            return

        self.logger_stop_requested = False
        self.logger_error_reported = False
        self._update_logging_ui("starting")
        self.logger_process.setWorkingDirectory(str(PROJECT_ROOT))
        self.logger_process.setProgram(sys.executable)
        if getattr(sys, "frozen", False):
            self.logger_stop_file = (
                Path(tempfile.gettempdir())
                / f"motorsport-telemetry-{uuid.uuid4().hex}.stop"
            )
            logger_arguments = [
                "--logger",
                "--output-dir",
                str(self.logging_output_dir),
                "--stop-file",
                str(self.logger_stop_file),
            ]
        else:
            logger_arguments = [
                "-m",
                "src.ingestion.shared_memory_logger",
                "--output-dir",
                str(self.logging_output_dir),
            ]
        self.logger_process.setArguments(logger_arguments)
        self.logger_process.start()

    def _stop_logging(self) -> None:
        if self.logger_process.state() == QProcess.ProcessState.NotRunning:
            self._clear_logger_stop_file()
            self._update_logging_ui("stopped")
            return

        self.logger_stop_requested = True
        if self.logger_stop_file is None:
            self.logger_process.write(b"stop\n")
            self.logger_process.waitForBytesWritten(500)
        else:
            try:
                self.logger_stop_file.touch(exist_ok=True)
            except OSError as error:
                print(f"LOGGER STOP FILE FAILED: {error}")

        if not self.logger_process.waitForFinished(3000):
            print("LOGGER STOP: stop command timed out; terminating process")
            self.logger_process.terminate()

            if not self.logger_process.waitForFinished(1500):
                print("LOGGER STOP: termination timed out; killing process")
                self.logger_process.kill()
                self.logger_process.waitForFinished(1000)

        self._clear_logger_stop_file()
        self._update_logging_ui("stopped")

    def _on_logger_started(self) -> None:
        print(f"LOGGER STARTED: output directory {self.logging_output_dir}")
        self._update_logging_ui("recording")

    def _on_logger_error(self, error) -> None:
        print(f"LOGGER PROCESS ERROR: {self.logger_process.errorString()}")

        if (
            error == QProcess.ProcessError.FailedToStart
            and not self.logger_stop_requested
        ):
            self.logger_error_reported = True
            self._clear_logger_stop_file()
            self._update_logging_ui("stopped")
            self._show_logger_error("Could not start telemetry logging.")

    def _on_logger_finished(self, exit_code: int, exit_status) -> None:
        stopped_intentionally = self.logger_stop_requested
        self._clear_logger_stop_file()
        self._update_logging_ui("stopped")

        if not stopped_intentionally and not self.logger_error_reported:
            print(
                "LOGGER EXITED UNEXPECTEDLY: "
                f"code={exit_code}, status={exit_status}"
            )
            self._show_logger_error("Telemetry logging stopped unexpectedly.")

        self.logger_stop_requested = False
        self.logger_error_reported = False

    def _clear_logger_stop_file(self) -> None:
        stop_file = self.logger_stop_file
        self.logger_stop_file = None

        if stop_file is None:
            return

        try:
            stop_file.unlink()
        except FileNotFoundError:
            pass

    def _update_logging_ui(self, state: str) -> None:
        if state == "recording":
            self.logging_toggle_button.setText("Stop logging")
            self.logging_toggle_button.setEnabled(True)
            self.choose_logging_folder_button.setEnabled(False)
            self.logging_status_label.setText("Status: Recording...")
        elif state == "starting":
            self.logging_toggle_button.setText("Starting...")
            self.logging_toggle_button.setEnabled(False)
            self.choose_logging_folder_button.setEnabled(False)
            self.logging_status_label.setText("Status: Starting...")
        else:
            self.logging_toggle_button.setText("Start logging")
            self.logging_toggle_button.setEnabled(True)
            self.choose_logging_folder_button.setEnabled(True)
            self.logging_status_label.setText("Status: Not logging")

    def _show_logger_error(self, message: str) -> None:
        QMessageBox.critical(self, "Telemetry logging", message)

    def _open_session(self) -> None:
        initial_directory = (
            self.current_session_path.parent
            if self.current_session_path is not None
            else self.logging_output_dir
        )
        selected_path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Open telemetry session",
            str(initial_directory),
            "CSV files (*.csv);;All files (*)",
        )

        if not selected_path:
            return

        try:
            candidate = self._load_session_candidate(Path(selected_path))
        except Exception:
            self._show_session_load_error()
            return

        try:
            self._commit_session(candidate)
        except Exception as error:
            print(f"SESSION COMMIT FAILED: {error}")
            self._show_session_load_error()

    def _show_session_load_error(self) -> None:
        QMessageBox.critical(
            self,
            "Unable to open session",
            "The selected telemetry session could not be loaded.\n\n"
            "This recording does not contain enough usable "
            "completed-lap telemetry.",
        )

    def _load_session_candidate(self, path: Path):
        return load_session_candidate(path)

    def _commit_session(self, candidate) -> None:
        previous_state = self._capture_session_commit_state()
        prepared_viewer = None
        state_mutated = False

        try:
            session_lap_entries = candidate.get_telemetry_lap_entries()
            selected_reference_lap = next(
                lap_number
                for lap_number, _lap_time, _lap_delta, is_best
                in session_lap_entries
                if is_best
            )
            candidate.set_reference_style(selected_reference_lap)
            reference_entries = candidate.get_telemetry_lap_legend_entries(
                selected_reference_lap
            )
            section_numbers = candidate.get_telemetry_section_numbers()
            channel_states = {
                channel: control.isChecked()
                for channel, control in self.channel_visibility_controls.items()
            }
            prepared_viewer = self._prepare_telemetry_viewer(
                candidate,
                channel_states,
            )

            state_mutated = True
            self._bind_telemetry_session(candidate)
            self.current_session_path = Path(candidate.CSV_FILE)
            self.session_display_name = (
                candidate.get_telemetry_session_display_name()
            )
            self.session_lap_entries = session_lap_entries
            self.selected_reference_lap = selected_reference_lap
            self.selected_compare_lap = None
            self.selected_section = None
            self.current_pair_analysis = None
            self.analysis_cache = {}
            self.pair_only_enabled = True
            self.normal_lap_visibility = {
                lap_number: True
                for lap_number, *_rest in self.session_lap_entries
            }
            self.lap_display_colors = {
                lap_number: color
                for lap_number, _label, color, _is_reference in reference_entries
            }
            self.reference_lap_numbers = sorted(
                lap_number
                for lap_number, _label, _color, _is_reference in reference_entries
            )
            self.section_numbers = section_numbers

            self._activate_prepared_viewer(prepared_viewer)
            self._rebuild_lap_rows()
            self._reset_session_selectors()
            self._apply_pair_only_visibility(
                laps_to_show=self._selected_pair_laps()
            )
            self.restore_telemetry_full_lap_view()
            self.session_label.setText(self.session_display_name)
            self._update_state_readout()
            self.refresh_analysis_panel()
        except Exception:
            self._rollback_session_commit(
                candidate,
                previous_state,
                prepared_viewer,
                state_mutated,
            )
            raise

        self._retire_viewer(previous_state["viewer"], candidate.plt)

    def _capture_session_commit_state(self) -> dict:
        state_names = (
            "telemetry_session",
            "current_session_path",
            "session_display_name",
            "session_lap_entries",
            "selected_reference_lap",
            "selected_compare_lap",
            "selected_section",
            "analysis_cache",
            "current_pair_analysis",
            "pair_only_enabled",
            "normal_lap_visibility",
            "lap_display_colors",
            "reference_lap_numbers",
            "section_numbers",
        )
        return {
            "state": {
                name: getattr(self, name)
                for name in state_names
            },
            "bindings": {
                name: (hasattr(self, name), getattr(self, name, None))
                for name in self.SESSION_BINDING_NAMES
            },
            "viewer": (
                self.telemetry_figure,
                self.telemetry_canvas,
                self.telemetry_toolbar,
                self.telemetry_channel_controls,
                self.channel_visibility_controls,
            ),
            "lap_controls": {
                lap_number: (control.isChecked(), self.lap_rows[lap_number].isEnabled())
                for lap_number, control in self.lap_visibility_controls.items()
            },
            "selectors": {
                "reference": self._capture_combo_box(self.reference_combo_box),
                "compare": self._capture_combo_box(self.compare_combo_box),
                "section": self._capture_combo_box(self.section_combo_box),
            },
            "pair_only": (
                self.pair_only_control.isChecked(),
                self.pair_only_control.isEnabled(),
            ),
            "session_label": self.session_label.text(),
            "state_readout": self.state_readout.text(),
        }

    @staticmethod
    def _capture_combo_box(combo_box: QComboBox) -> tuple[list[str], str, bool]:
        return (
            [combo_box.itemText(index) for index in range(combo_box.count())],
            combo_box.currentText(),
            combo_box.isEnabled(),
        )

    @staticmethod
    def _restore_combo_box(
        combo_box: QComboBox,
        state: tuple[list[str], str, bool],
    ) -> None:
        items, current_text, enabled = state
        combo_box.blockSignals(True)
        combo_box.clear()
        combo_box.addItems(items)
        combo_box.setCurrentText(current_text)
        combo_box.setEnabled(enabled)
        combo_box.blockSignals(False)

    def _rollback_session_commit(
        self,
        candidate,
        previous_state: dict,
        prepared_viewer,
        state_mutated: bool,
    ) -> None:
        if prepared_viewer is not None:
            self._discard_viewer(prepared_viewer, candidate.plt)
        else:
            candidate_figure = getattr(candidate, "fig", None)
            if candidate_figure is not None:
                candidate.plt.close(candidate_figure)

        if not state_mutated:
            return

        for name, value in previous_state["state"].items():
            setattr(self, name, value)

        for name, (was_present, value) in previous_state["bindings"].items():
            if was_present:
                setattr(self, name, value)
            elif hasattr(self, name):
                delattr(self, name)

        (
            self.telemetry_figure,
            self.telemetry_canvas,
            self.telemetry_toolbar,
            self.telemetry_channel_controls,
            self.channel_visibility_controls,
        ) = previous_state["viewer"]

        self._rebuild_lap_rows()
        for lap_number, (checked, enabled) in previous_state["lap_controls"].items():
            control = self.lap_visibility_controls[lap_number]
            control.blockSignals(True)
            control.setChecked(checked)
            control.blockSignals(False)
            self.lap_rows[lap_number].setEnabled(enabled)

        for name, combo_box in (
            ("reference", self.reference_combo_box),
            ("compare", self.compare_combo_box),
            ("section", self.section_combo_box),
        ):
            self._restore_combo_box(combo_box, previous_state["selectors"][name])

        pair_checked, pair_enabled = previous_state["pair_only"]
        self.pair_only_control.blockSignals(True)
        self.pair_only_control.setChecked(pair_checked)
        self.pair_only_control.setEnabled(pair_enabled)
        self.pair_only_control.blockSignals(False)
        self.session_label.setText(previous_state["session_label"])
        self.state_readout.setText(previous_state["state_readout"])
        self.refresh_analysis_panel()

    def _reset_session_selectors(self) -> None:
        self.reference_combo_box.blockSignals(True)
        self.reference_combo_box.clear()
        self.reference_combo_box.addItems(
            [self.LAP_PLACEHOLDER]
            + [f"Lap {lap_number}" for lap_number in self.reference_lap_numbers]
        )
        self.reference_combo_box.setCurrentText(
            f"Lap {self.selected_reference_lap}"
        )
        self.reference_combo_box.blockSignals(False)

        self.compare_combo_box.blockSignals(True)
        self.compare_combo_box.clear()
        self.compare_combo_box.addItems(
            [self.LAP_PLACEHOLDER]
            + [
                f"Lap {lap_number}"
                for lap_number in self.reference_lap_numbers
                if lap_number != self.selected_reference_lap
            ]
        )
        self.compare_combo_box.setCurrentText(self.LAP_PLACEHOLDER)
        self.compare_combo_box.blockSignals(False)

        self.section_combo_box.blockSignals(True)
        self.section_combo_box.clear()
        self.section_combo_box.addItems(
            [self.SECTION_PLACEHOLDER]
            + [
                f"Section {section_number}"
                for section_number in self.section_numbers
            ]
        )
        self.section_combo_box.setCurrentText(self.SECTION_PLACEHOLDER)
        self.section_combo_box.blockSignals(False)

        self.pair_only_control.blockSignals(True)
        self.pair_only_control.setChecked(True)
        self.pair_only_control.blockSignals(False)
        self._set_session_controls_enabled(True)

    def _rebuild_lap_rows(self) -> None:
        while self.laps_layout.count():
            item = self.laps_layout.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        self.lap_visibility_controls = {}
        self.lap_rows = {}

        for (
            lap_number,
            lap_time,
            lap_delta_to_best,
            is_best,
        ) in self.session_lap_entries:
            self.laps_layout.addWidget(
                self._create_lap_row(
                    lap_number,
                    lap_time,
                    lap_delta_to_best,
                    self.lap_display_colors[lap_number],
                    is_best=is_best,
                )
            )

    def _on_reference_changed(self, value: str) -> None:
        if self.telemetry_session is None:
            return

        previous_pair_laps = self._selected_pair_laps()
        self.selected_reference_lap = self._lap_number_from_text(value)
        self._refresh_compare_options()
        self.set_telemetry_reference_style(self.selected_reference_lap)
        self._update_lap_reference_controls(
            self.get_telemetry_lap_legend_entries(
                self.selected_reference_lap
            )
        )
        self._apply_pair_only_visibility(
            laps_to_show=self._selected_pair_laps() - previous_pair_laps
        )
        self._request_pair_analysis()
        self._update_state_readout()

    def _on_compare_changed(self, value: str) -> None:
        if self.telemetry_session is None:
            return

        previous_pair_laps = self._selected_pair_laps()
        self.selected_compare_lap = self._lap_number_from_text(value)
        self._apply_pair_only_visibility(
            laps_to_show=self._selected_pair_laps() - previous_pair_laps
        )
        self._request_pair_analysis()
        self._update_state_readout()

    def _selected_pair_laps(self) -> set[int]:
        return {
            lap_number
            for lap_number in (
                self.selected_reference_lap,
                self.selected_compare_lap,
            )
            if lap_number is not None
        }

    def _set_pair_only_enabled(self, enabled: bool) -> None:
        if self.telemetry_session is None:
            return

        if enabled:
            self.normal_lap_visibility = {
                lap_number: control.isChecked()
                for lap_number, control
                in self.lap_visibility_controls.items()
            }

        self.pair_only_enabled = enabled

        if enabled:
            self._apply_pair_only_visibility(
                laps_to_show=self._selected_pair_laps()
            )
            return

        for lap_number, control in self.lap_visibility_controls.items():
            self.lap_rows[lap_number].setEnabled(True)
            self._set_lap_control_visibility(
                lap_number,
                self.normal_lap_visibility[lap_number],
            )

    def _apply_pair_only_visibility(
        self,
        laps_to_show: set[int] | None = None,
    ) -> None:
        if not self.pair_only_enabled:
            return

        allowed_laps = self._selected_pair_laps()
        laps_to_show = laps_to_show or set()

        for lap_number in self.lap_visibility_controls:
            is_allowed = lap_number in allowed_laps
            self.lap_rows[lap_number].setEnabled(is_allowed)

            if not is_allowed:
                self._set_lap_control_visibility(lap_number, False)
            elif lap_number in laps_to_show:
                self._set_lap_control_visibility(lap_number, True)

    def _set_lap_control_visibility(
        self,
        lap_number: int,
        visible: bool,
    ) -> None:
        control = self.lap_visibility_controls[lap_number]
        control.blockSignals(True)
        control.setChecked(visible)
        control.blockSignals(False)
        self.set_telemetry_lap_visibility(lap_number, visible)

    def _on_lap_visibility_toggled(
        self,
        lap_number: int,
        visible: bool,
    ) -> None:
        if not self.pair_only_enabled:
            self.normal_lap_visibility[lap_number] = visible

        self.set_telemetry_lap_visibility(lap_number, visible)

    def _on_section_changed(self, value: str) -> None:
        if self.telemetry_session is None:
            return

        if value == self.SECTION_PLACEHOLDER:
            self.selected_section = None
            self.restore_telemetry_full_lap_view()
        else:
            try:
                section_number = int(value.split()[-1])
            except (IndexError, ValueError):
                section_number = None

            if section_number not in self.section_numbers:
                self.selected_section = None
                self.section_combo_box.blockSignals(True)
                self.section_combo_box.setCurrentText(self.SECTION_PLACEHOLDER)
                self.section_combo_box.blockSignals(False)
                self.restore_telemetry_full_lap_view()
            else:
                self.selected_section = section_number
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
        section_text = (
            f"S{self.selected_section}"
            if self.selected_section is not None
            else self.SECTION_PLACEHOLDER
        )
        self.state_readout.setText(
            f"Reference: {reference_text}\n"
            f"Compare: {compare_text}\n"
            f"Section: {section_text}"
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
        if self.telemetry_session is None:
            return

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
                self._on_lap_visibility_toggled(number, visible)
            )
        )
        self.lap_visibility_controls[lap_number] = visibility_control
        self.lap_rows[lap_number] = row
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
        self.telemetry_panel = panel
        self.telemetry_layout = layout
        self._install_empty_telemetry_viewer()
        return panel

    def _install_empty_telemetry_viewer(self) -> None:
        self.telemetry_figure = Figure(facecolor="black")
        self.telemetry_canvas = FigureCanvas(self.telemetry_figure)
        self.telemetry_toolbar = NavigationToolbar(
            self.telemetry_canvas,
            self.telemetry_panel,
        )
        self.telemetry_toolbar.setObjectName("telemetryToolbar")
        (
            self.telemetry_channel_controls,
            self.channel_visibility_controls,
        ) = self._create_channel_visibility_controls(
            lambda _channel, _visible: None
        )
        self.telemetry_layout.addWidget(self.telemetry_toolbar)
        self.telemetry_layout.addWidget(self.telemetry_channel_controls)
        self.telemetry_layout.addWidget(self.telemetry_canvas, 1)

    def _prepare_telemetry_viewer(
        self,
        telemetry_session,
        channel_states: dict[str, bool] | None = None,
    ) -> tuple:
        figure = telemetry_session.create_telemetry_figure()
        canvas = figure.canvas

        if not isinstance(canvas, FigureCanvas):
            telemetry_session.plt.close(figure)
            raise RuntimeError("The telemetry figure is not using a Qt canvas.")

        toolbar = None
        controls = None
        try:
            toolbar = NavigationToolbar(
                canvas,
                self.telemetry_panel,
            )
            toolbar.setObjectName("telemetryToolbar")
            controls, control_map = self._create_channel_visibility_controls(
                telemetry_session.set_graph_visibility,
                channel_states,
            )
        except Exception:
            for widget in (toolbar, controls, canvas):
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()
            telemetry_session.plt.close(figure)
            raise

        return figure, canvas, toolbar, controls, control_map

    def _activate_prepared_viewer(self, prepared_viewer: tuple) -> None:
        (
            self.telemetry_figure,
            self.telemetry_canvas,
            self.telemetry_toolbar,
            self.telemetry_channel_controls,
            self.channel_visibility_controls,
        ) = prepared_viewer

        self.telemetry_layout.addWidget(self.telemetry_toolbar)
        self.telemetry_layout.addWidget(self.telemetry_channel_controls)
        self.telemetry_layout.addWidget(self.telemetry_canvas, 1)

    def _discard_viewer(
        self,
        viewer: tuple,
        pyplot,
    ) -> None:
        figure, canvas, toolbar, controls, _control_map = viewer

        for widget in (toolbar, controls, canvas):
            self.telemetry_layout.removeWidget(widget)
            widget.setParent(None)
            widget.deleteLater()

        pyplot.close(figure)

    def _retire_viewer(self, viewer: tuple, pyplot) -> None:
        self._discard_viewer(viewer, pyplot)

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
            "QCheckBox:disabled { color: #50554d; } "
            f"QCheckBox::indicator:checked {{ "
            f"background-color: {color}; border-color: {color}; "
            "} "
            "QCheckBox::indicator:unchecked { "
            "background-color: transparent; border-color: #555a52; "
            "} "
            "QCheckBox::indicator:disabled { "
            "background-color: transparent; border-color: #454941; "
            "}"
        )

    def _create_channel_visibility_controls(
        self,
        set_visibility,
        channel_states: dict[str, bool] | None = None,
    ) -> tuple[QWidget, dict[str, QCheckBox]]:
        controls = QWidget()
        controls.setObjectName("telemetryControlRow")

        layout = QHBoxLayout(controls)
        layout.setContentsMargins(1, 0, 1, 2)
        layout.setSpacing(10)

        row_label = QLabel("Channels:")
        row_label.setObjectName("telemetryControlRowLabel")
        layout.addWidget(row_label)

        default_states = [
            ("Spd", True),
            ("Brk", True),
            ("Thr", True),
            ("Dlt", False),
            ("Str", False),
            ("Dev", False),
            ("Line", False),
        ]

        channel_visibility_controls = {}

        for channel, default_visible in default_states:
            is_visible = (
                channel_states.get(channel, default_visible)
                if channel_states is not None
                else default_visible
            )
            control = QCheckBox(channel)
            control.setObjectName("telemetryChannelControl")
            control.setChecked(is_visible)
            control.toggled.connect(
                lambda visible, name=channel: set_visibility(name, visible)
            )
            channel_visibility_controls[channel] = control
            layout.addWidget(control)

            if channel_states is not None:
                set_visibility(channel, is_visible)

        layout.addStretch(1)
        return controls, channel_visibility_controls

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

        if self.telemetry_session is None:
            self._add_analysis_label(
                "Open a session to begin.",
                "analysisEmptyState",
            )
            self.analysis_content_layout.addStretch(1)
            return

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

        if self.selected_section is None:
            self._add_analysis_label(
                "Select a section to view analysis.",
                "analysisEmptyState",
            )
            self.analysis_content_layout.addStretch(1)
            return

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

    def closeEvent(self, event) -> None:
        if self.logger_process.state() != QProcess.ProcessState.NotRunning:
            self._stop_logging()

        super().closeEvent(event)

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
