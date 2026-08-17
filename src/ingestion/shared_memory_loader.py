from pathlib import Path

import pandas as pd


def load_shared_memory_csv(csv_file):
    df = pd.read_csv(csv_file)

    return df