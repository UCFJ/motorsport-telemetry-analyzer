from pathlib import Path

from src.ingestion.motec_loader import load_telemetry

import numpy as np

import matplotlib.pyplot as plt

def find_braking_events(df):
    events = []

    for i in range(1, len(df)):
        previous_brake = df.loc[i - 1, "brake"]
        current_brake = df.loc[i, "brake"]

        if previous_brake < 5 and current_brake >= 5:
            events.append(i)

    return events

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DATA = PROJECT_ROOT / "data" / "raw"


CONTROLLER_FILE = (
    RAW_DATA
    / "monza-mclaren_720s_gt3_evo-5-2026.08.12-02.59.29.ld"
)

WHEEL_FILE = (
    RAW_DATA
    / "monza-mclaren_720s_gt3_evo-0-2026.08.12-05.37.22.ld"
)


controller = load_telemetry(CONTROLLER_FILE)
wheel = load_telemetry(WHEEL_FILE)


print("Controller:")
print(controller.shape)
print(
    "Duration:",
    controller["time_s"].iloc[-1],
    "seconds"
)

print()

print("Wheel / Pedals:")
print(wheel.shape)
print(
    "Duration:",
    wheel["time_s"].iloc[-1],
    "seconds"
)

controller_events = find_braking_events(controller)
wheel_events = find_braking_events(wheel)

print()
print("Brake events:")
print("Controller:", len(controller_events))
print("Wheel:", len(wheel_events))

def time_to_full_brake(df, event_index):
    start_time = df.loc[event_index, "time_s"]

    for i in range(event_index, len(df)):
        if df.loc[i, "brake"] >= 99:
            full_brake_time = df.loc[i, "time_s"]

            return full_brake_time - start_time

    return None


controller_brake_times = []

for event in controller_events:
    ramp_time = time_to_full_brake(controller, event)

    if ramp_time is not None:
        controller_brake_times.append(float(ramp_time))


wheel_brake_times = []

for event in wheel_events:
    ramp_time = time_to_full_brake(wheel, event)

    if ramp_time is not None:
        wheel_brake_times.append(float(ramp_time))


        print()


def print_brake_stats(name, times):
    print()
    print(name)
    print("-" * len(name))

    print("Number of full-brake events:", len(times))
    print("Mean ramp time:", round(np.mean(times), 4), "s")
    print("Median ramp time:", round(np.median(times), 4), "s")
    print("Minimum ramp time:", round(np.min(times), 4), "s")
    print("Maximum ramp time:", round(np.max(times), 4), "s")

print_brake_stats(
    "Controller",
    controller_brake_times
)

print_brake_stats(
    "Wheel / Pedals",
    wheel_brake_times
)


def extract_brake_trace(df, event_index, before=0.1, after=0.5):
    event_time = df.loc[event_index, "time_s"]

    trace = df[
        (df["time_s"] >= event_time - before) &
        (df["time_s"] <= event_time + after)
    ].copy()

    trace["relative_time"] = trace["time_s"] - event_time

    return trace

controller["session_progress"] = (
    controller["time_s"]
    / controller["time_s"].iloc[-1]
    * 100
)

wheel["session_progress"] = (
    wheel["time_s"]
    / wheel["time_s"].iloc[-1]
    * 100
)

plt.figure(figsize=(14, 6))

plt.plot(
    controller["session_progress"],
    controller["steering_deg"],
    label="Controller",
    color="blue",
    linewidth=1
)

plt.plot(
    wheel["session_progress"],
    wheel["steering_deg"],
    label="Wheel",
    color="red",
    linewidth=1
)

plt.xlabel("Session Progress (%)")
plt.ylabel("Steering Angle (deg)")
plt.title("Steering Input - Controller vs Wheel")

plt.legend(
    loc="upper center",
    bbox_to_anchor=(0.5, 1.12),
    ncol=2
)

plt.grid(alpha=0.3)

plt.tight_layout()

plt.show()

plt.legend()
plt.grid()

plt.show()

def print_brake_events(name, df, events):
    print()
    print(name)
    print("-" * len(name))

    for number, event in enumerate(events, start=1):
        print(
            f"Event {number:<2} "
            f"Time: {df.loc[event, 'time_s']:>7.2f}s  "
            f"Speed: {df.loc[event, 'speed_kmh']:>6.1f} km/h"
        )


print_brake_events(
    "Controller brake events",
    controller,
    controller_events
)

print_brake_events(
    "Wheel brake events",
    wheel,
    wheel_events
)