"""Copernicus European Ground Motion Service (EGMS) source.

Uses the **Ortho** product (Level 3): vertical and east-west velocities on a
100 m grid in EPSG:3035, delivered as separate CSV files per component.

Data: https://land.copernicus.eu/en/products/european-ground-motion-service
Free and open under the Copernicus data policy (registration required to download).

NOTE: check the column names below against the current EGMS Product
Description Document; they can change between releases.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# Column names in EGMS Ortho CSV files (verify per release).
COL_X = "easting"
COL_Y = "northing"
COL_VELOCITY = "mean_velocity"


def load_ortho(vertical_csv: str | Path, east_west_csv: str | Path) -> pd.DataFrame:
    """Load EGMS Ortho vertical and east-west files and merge them per grid cell.

    Returns the standard InfraShield motion table: ``x``, ``y`` (m, EPSG:3035),
    ``v_up`` and ``v_east`` (mm/yr). Only cells present in both files are kept.
    """
    up = _read_component(vertical_csv, "v_up")
    east = _read_component(east_west_csv, "v_east")
    return up.merge(east, on=["x", "y"], how="inner")


def _read_component(path: str | Path, name: str) -> pd.DataFrame:
    df = pd.read_csv(path, usecols=[COL_X, COL_Y, COL_VELOCITY])
    return df.rename(columns={COL_X: "x", COL_Y: "y", COL_VELOCITY: name})


# TODO(M1): add download_tiles(bbox, out_dir) using the EGMS Explorer API.
