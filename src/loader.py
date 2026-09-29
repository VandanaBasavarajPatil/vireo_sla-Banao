"""Read the CSV files, either uploaded in the app or from the data/ folder."""
import os
import pandas as pd

EXPECTED = ["tickets", "agents", "orders", "customers", "products"]
REQUIRED = ["tickets", "agents"]  # only these two are needed for the SLA report


def _match(filename):
    """Work out which dataset a file is, from its name (e.g. 'abc-tickets.csv')."""
    name = filename.lower()
    for key in EXPECTED:
        if key in name:
            return key
    return None


def load_uploaded(files):
    """files: list of Streamlit UploadedFile objects. Returns dict name -> DataFrame."""
    data = {}
    for f in files:
        key = _match(f.name)
        if key:
            data[key] = pd.read_csv(f)
    return data


def load_from_folder(folder="data"):
    """Fallback: read any matching CSVs from a local folder."""
    data = {}
    if not os.path.isdir(folder):
        return data
    for fname in os.listdir(folder):
        if fname.lower().endswith(".csv"):
            key = _match(fname)
            if key:
                data[key] = pd.read_csv(os.path.join(folder, fname))
    return data


def missing_required(data):
    return [k for k in REQUIRED if k not in data]