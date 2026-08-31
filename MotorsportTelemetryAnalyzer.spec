from pathlib import Path


project_root = Path(SPECPATH)


a = Analysis(
    ["telemetry_analyzer.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (
            str(project_root / "assets" / "telemetry_analtzer.png"),
            "assets",
        ),
    ],
    hiddenimports=[
        "src.analysis.shared_memory_laps",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MotorsportTelemetryAnalyzer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(project_root / "assets" / "telemetry_analtzer.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MotorsportTelemetryAnalyzer",
)