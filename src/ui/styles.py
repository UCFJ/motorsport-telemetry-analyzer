"""Centralized Qt stylesheet for the telemetry analyzer UI."""

APPLICATION_STYLE = """
QWidget {
    background-color: #111310;
    color: #eceee8;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}

QWidget#centralWidget {
    background-color: #111310;
}

QLabel#headerTitle {
    color: #f4f6ef;
    font-size: 20px;
    font-weight: 600;
    padding: 3px 1px 6px 1px;
}

QFrame#leftPanel,
QFrame#workspacePanel,
QFrame#rightPanel {
    background-color: #171917;
    border: none;
    border-radius: 0;
}

QFrame#leftPanel,
QFrame#workspacePanel {
    border-right: 1px solid #30332f;
}

QLabel#panelTitle {
    background-color: transparent;
    border: none;
    color: #8d9289;
    font-size: 11px;
    font-weight: 600;
    padding: 0 0 5px 1px;
}

QLabel#sectionLabel {
    background-color: transparent;
    border: none;
    color: #7f857b;
    font-size: 11px;
    font-weight: 600;
    padding: 0 1px;
}

QLabel#sessionValue {
    background-color: transparent;
    border: none;
    color: #eceee8;
    font-size: 13px;
    padding: 1px;
}

QPushButton#openSessionButton {
    background-color: #1c1f1c;
    border: 1px solid #333732;
    border-radius: 1px;
    color: #c8ccc4;
    font-size: 11px;
    padding: 3px 7px;
}

QPushButton#openSessionButton:hover {
    background-color: #20231f;
    border-color: #4a4e47;
}

QWidget#lapRow,
QWidget#bestLapRow {
    background-color: transparent;
    border: none;
}

QLabel#lapText,
QLabel#lapTime,
QLabel#lapStatus,
QLabel#lapDelta,
QLabel#bestLapText {
    background-color: transparent;
    border: none;
    color: #c5c9c0;
}

QLabel#lapText {
    min-width: 22px;
}

QLabel#lapTime {
    color: #aeb3aa;
}

QLabel#lapDelta {
    color: #8d9289;
    font-size: 11px;
}

QLabel#bestLapText {
    color: #b9dc45;
    font-weight: 600;
}

QLabel#bestText {
    background-color: transparent;
    border: none;
    color: #b9dc45;
    font-size: 10px;
    font-weight: 700;
    padding: 0;
}

QWidget#lapRow:disabled QLabel#lapTime,
QWidget#lapRow:disabled QLabel#lapDelta,
QWidget#bestLapRow:disabled QLabel#bestLapText,
QWidget#bestLapRow:disabled QLabel#bestText {
    color: #5f645c;
}

QComboBox#panelComboBox {
    background-color: #1c1f1c;
    border: 1px solid #333732;
    border-radius: 1px;
    color: #e3e6df;
    min-height: 32px;
    padding: 0 10px;
}

QComboBox#panelComboBox:hover {
    background-color: #20231f;
    border-color: #4a4e47;
}

QComboBox#panelComboBox:focus {
    border-color: #778b3c;
}

QComboBox#panelComboBox QAbstractItemView {
    background-color: #1e211e;
    border: 1px solid #3b3f39;
    color: #e3e6df;
    selection-background-color: #303629;
    selection-color: #f4f6ef;
    outline: none;
}

QToolBar#telemetryToolbar {
    background-color: #171917;
    border: none;
    border-bottom: 1px solid #30332f;
    spacing: 2px;
    padding: 1px;
}

QToolBar#telemetryToolbar QToolButton {
    background-color: transparent;
    border: none;
    border-radius: 1px;
    padding: 3px;
}

QToolBar#telemetryToolbar QToolButton:hover {
    background-color: #242724;
}

QToolBar#telemetryToolbar QToolButton:checked {
    background-color: #303629;
}

QWidget#telemetryControlRow {
    background-color: transparent;
    border: none;
}

QLabel#telemetryControlRowLabel {
    background-color: transparent;
    border: none;
    color: #73786f;
    font-size: 10px;
    font-weight: 600;
    min-width: 52px;
    padding: 0;
}

QCheckBox#telemetryLapControl,
QCheckBox#telemetryChannelControl {
    background-color: transparent;
    border: none;
    font-size: 11px;
    spacing: 4px;
    padding: 0;
}

QCheckBox#telemetryLapControl::indicator,
QCheckBox#telemetryChannelControl::indicator {
    background-color: transparent;
    border: 1px solid #555a52;
    border-radius: 1px;
    height: 9px;
    width: 9px;
}

QCheckBox#telemetryLapControl::indicator:checked,
QCheckBox#telemetryChannelControl::indicator:checked {
    background-color: #92988e;
    border-color: #92988e;
}

QCheckBox#telemetryChannelControl {
    color: #c8ccc4;
}

QCheckBox#telemetryChannelControl:unchecked {
    color: #5f645c;
}

QLabel#inspectionPlaceholder {
    background-color: transparent;
    border: none;
    color: #7f857b;
    padding: 5px 1px;
}

QWidget#analysisModeControls,
QWidget#analysisContent,
QScrollArea#analysisScrollArea,
QScrollArea#analysisScrollArea QWidget#qt_scrollarea_viewport {
    background-color: transparent;
    border: none;
}

QPushButton#analysisModeButton {
    background-color: transparent;
    border: none;
    border-bottom: 1px solid #333732;
    border-radius: 0;
    color: #7f857b;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 1px 4px 1px;
}

QPushButton#analysisModeButton:hover {
    color: #c8ccc4;
    border-bottom-color: #555a52;
}

QPushButton#analysisModeButton:checked {
    color: #b9dc45;
    border-bottom-color: #778b3c;
}

QLabel#analysisEmptyState,
QLabel#analysisRawDetail {
    background-color: transparent;
    color: #7f857b;
}

QLabel#analysisHeadline {
    background-color: transparent;
    color: #eceee8;
    font-size: 13px;
    font-weight: 600;
    padding: 2px 0 7px 0;
}

QLabel#analysisOverallHeadline {
    background-color: transparent;
    color: #b9dc45;
    font-size: 12px;
    font-weight: 600;
    padding: 2px 0 5px 0;
}

QLabel#analysisGroupHeading,
QLabel#analysisRawName {
    background-color: transparent;
    color: #8d9289;
    font-size: 10px;
    font-weight: 600;
    padding: 6px 0 0 0;
}

QLabel#analysisSummaryText,
QLabel#analysisRawValue {
    background-color: transparent;
    color: #d7dad3;
}

QLabel#analysisRawDetail {
    font-size: 11px;
}

QLabel#stateReadout {
    background-color: transparent;
    border: none;
    color: #73786f;
    font-size: 11px;
    padding: 3px 1px 0 1px;
}

QLabel#fieldPlaceholder {
    background-color: transparent;
    border: none;
    border-bottom: 1px solid #333732;
    border-radius: 0;
    color: #a8ada3;
    min-height: 28px;
    padding: 0 2px;
}
"""
