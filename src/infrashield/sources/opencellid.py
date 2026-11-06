"""OpenCellID cell-location source.

Data: https://opencellid.org (Unwired Labs), licensed CC BY-SA 4.0.
Country files are named by Mobile Country Code, e.g. ``232.csv.gz`` for Austria.
They come without a header row; the columns are listed in ``COLUMNS``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from infrashield.sites import to_laea

COLUMNS = [
    "radio",
    "mcc",
    "net",
    "area",
    "cell",
    "unit",
    "lon",
    "lat",
    "range",
    "samples",
    "changeable",
    "created",
    "updated",
    "average_signal",
]

DOWNLOAD_URL = "https://opencellid.org/downloads.php?token={token}&type=mcc&file={mcc}.csv.gz"


def load_cells(
    path: str | Path, bbox: tuple[float, float, float, float] | None = None
) -> pd.DataFrame:
    """Load an OpenCellID CSV (optionally gzipped) and reproject it to EPSG:3035.

    Args:
        path: local file path.
        bbox: optional (min_lon, min_lat, max_lon, max_lat) filter in WGS84.

    Returns:
        DataFrame with the original columns plus ``x``, ``y`` in metres.
    """
    df = pd.read_csv(path, header=None, names=COLUMNS)
    if bbox is not None:
        min_lon, min_lat, max_lon, max_lat = bbox
        df = df[df["lon"].between(min_lon, max_lon) & df["lat"].between(min_lat, max_lat)]
    x, y = to_laea(df["lon"].to_numpy(), df["lat"].to_numpy())
    return df.assign(x=x, y=y).reset_index(drop=True)


def download_url(mcc: int, token: str | None = None) -> str:
    """Build the download URL for a country file. Reads ``OPENCELLID_API_KEY`` if no token is given."""
    token = token or os.environ.get("OPENCELLID_API_KEY")
    if not token:
        raise RuntimeError("Set OPENCELLID_API_KEY in your .env file (see .env.example).")
    return DOWNLOAD_URL.format(token=token, mcc=mcc)


# TODO(M1): add download_cells(mcc, out_dir) that streams the file to data/raw/.
