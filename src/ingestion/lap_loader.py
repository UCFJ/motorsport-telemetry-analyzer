from pathlib import Path
import xml.etree.ElementTree as ET

def load_lap_markers(ldx_file):
    tree = ET.parse(ldx_file)
    root = tree.getroot()

    marker_times = []

    for marker in root.iter("Marker"):
        time_value = float(marker.attrib["Time"])

        time_seconds = time_value / 1_000_000

        marker_times.append(time_seconds)


    return marker_times