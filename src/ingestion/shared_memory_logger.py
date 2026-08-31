import argparse
import csv
import sys
import threading
import time
from pathlib import Path

from pyaccsharedmemory import accSharedMemory

from src.ingestion.paths import get_default_shared_memory_output_dir


FLUSH_EVERY_ROWS = 25


def remove_stop_file(stop_file):
    if stop_file is None:
        return

    try:
        stop_file.unlink()
    except FileNotFoundError:
        pass


def listen_for_stop_command(stop_event):
    """Watch stdin for the UI's simple graceful-stop command."""
    for line in sys.stdin:
        if line.strip().lower() == "stop":
            stop_event.set()
            return


def get_player_coordinates(data):
    player_id = data.Graphics.player_car_id

    for i in range(data.Graphics.active_cars):
        if data.Graphics.car_id[i] == player_id:
            coords = data.Graphics.car_coordinates[i]

            return (
                coords.x,
                coords.y,
                coords.z
            )

    return None, None, None


FIELDNAMES = [
    "timestamp_s",
    "lap_number",
    "lap_time_s",
    "acc_current_lap_ms",
    "acc_last_lap_ms",
    "acc_best_lap_ms",
    "completed_laps",
    "sector_index",
    "last_sector_ms",
    "is_valid_lap",
    "speed_kmh",
    "throttle",
    "brake",
    "steering",
    "rpm",
    "gear",
    "normalized_position",
    "world_x",
    "world_y",
    "world_z"
]


def record_session(output_file, sample_interval=0.01, stop_file=None):
    asm = accSharedMemory()
    stop_event = threading.Event()

    if stop_file is None:
        stop_listener = threading.Thread(
            target=listen_for_stop_command,
            args=(stop_event,),
            daemon=True,
        )
        stop_listener.start()

    start_time = time.perf_counter()
    lap_number = 0
    lap_start_time = None
    previous_position = None

    with open(
        output_file,
        "w",
        newline="",
        buffering=1
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=FIELDNAMES
        )

        writer.writeheader()
        file.flush()
        rows_since_flush = 0

        print("Recording ACC telemetry...")
        print("Press Ctrl+C to stop.")
        print()

        try:
            while not stop_event.is_set():
                if stop_file is not None and stop_file.exists():
                    stop_event.set()
                    continue

                data = asm.read_shared_memory()

                if data is None:
                    time.sleep(sample_interval)
                    continue

                world_x, world_y, world_z = (
                    get_player_coordinates(data)
                )

                timestamp = (
                    time.perf_counter()
                    - start_time
                )

                normalized_position = (
                    data.Graphics.normalized_car_position
                )
                
                if previous_position is not None:
                    crossed_start_finish = (
                        previous_position > 0.9
                        and normalized_position < 0.1
                    )
                
                    if crossed_start_finish:
                        lap_number += 1
                        lap_start_time = timestamp
                
                previous_position = normalized_position

                if lap_start_time is None:
                    lap_time = None
                else:
                    lap_time = timestamp - lap_start_time
                
                row = {
                    "timestamp_s": timestamp,
                    "lap_number": lap_number,
                    "lap_time_s": lap_time,
                    "acc_current_lap_ms": data.Graphics.current_time,
                    "acc_last_lap_ms": data.Graphics.last_time,
                    "acc_best_lap_ms": data.Graphics.best_time,
                    "completed_laps": data.Graphics.completed_lap,
                    "sector_index": data.Graphics.current_sector_index,
                    "last_sector_ms": data.Graphics.last_sector_time,
                    "is_valid_lap": data.Graphics.is_valid_lap,
                    "speed_kmh": data.Physics.speed_kmh,
                    "throttle": data.Physics.gas,
                    "brake": data.Physics.brake,
                    "steering": data.Physics.steer_angle,
                    "rpm": data.Physics.rpm,
                    "gear": data.Physics.gear,
                    "normalized_position": normalized_position,
                    "world_x": world_x,
                    "world_y": world_y,
                    "world_z": world_z
                }

                writer.writerow(row)
                rows_since_flush += 1

                if rows_since_flush >= FLUSH_EVERY_ROWS:
                    file.flush()
                    rows_since_flush = 0

                time.sleep(sample_interval)

            print()
            print("Recording stopped.")

        except KeyboardInterrupt:
            print()
            print("Recording stopped.")

        finally:
            file.flush()
            asm.close()
            remove_stop_file(stop_file)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Record ACC shared-memory data.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=get_default_shared_memory_output_dir(),
        help="Directory in which to create the telemetry session CSV.",
    )
    parser.add_argument(
        "--stop-file",
        type=Path,
        help="Optional file whose appearance requests a graceful stop.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    output_dir = args.output_dir.expanduser().resolve()
    stop_file = (
        args.stop_file.expanduser().resolve()
        if args.stop_file is not None
        else None
    )
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = (
            "acc_session_"
            + time.strftime("%Y%m%d_%H%M%S")
            + ".csv"
        )

        output_file = output_dir / filename

        print("Saving to:")
        print(output_file)
        print()

        record_session(output_file, stop_file=stop_file)
    finally:
        remove_stop_file(stop_file)


if __name__ == "__main__":
    main()
