from pathlib import Path

import pandas as pd

from src.ingestion.ldparser import ldData


def load_telemetry(ld_file):
    telemetry = ldData.fromfile(str(ld_file))

    speed = telemetry["SPEED"].data
    brake = telemetry["BRAKE"].data
    throttle = telemetry["THROTTLE"].data
    steering = telemetry["STEERANGLE"].data
    rpm = telemetry["RPMS"].data

    sample_rate = telemetry["SPEED"].freq

    df = pd.DataFrame({
        "speed_mps": speed,
        "brake": brake,
        "throttle": throttle,
        "steering_deg": steering,
        "rpm": rpm
    })

    df["time_s"] = df.index / sample_rate
    df["speed_kmh"] = df["speed_mps"] * 3.6

    df = df[
        [
            "time_s",
            "speed_mps",
            "speed_kmh",
            "brake",
            "throttle",
            "steering_deg",
            "rpm"
        ]
    ]

    return df