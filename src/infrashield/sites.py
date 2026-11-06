"""Group individual cells into approximate physical sites (masts).

One mast typically hosts many cells (several operators, technologies and
sectors). OpenCellID positions are crowd-sourced estimates, so cells of the
same mast appear scattered. Cells closer than ``eps_m`` are linked and each
connected group becomes one site.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

_WGS84_TO_LAEA = Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True)


def to_laea(lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Reproject WGS84 lon/lat (degrees) to ETRS89-LAEA (EPSG:3035, metres)."""
    x, y = _WGS84_TO_LAEA.transform(np.asarray(lon, float), np.asarray(lat, float))
    return np.asarray(x), np.asarray(y)


def cluster_cells(cells: pd.DataFrame, eps_m: float = 75.0) -> pd.DataFrame:
    """Cluster cells (columns ``x``, ``y``, optional ``radio``) into sites.

    Returns one row per site: ``site_id``, ``x``, ``y`` (cluster centroid),
    ``n_cells`` and ``radios`` (sorted, comma-separated technologies).
    """
    if cells.empty:
        return pd.DataFrame(columns=["site_id", "x", "y", "n_cells", "radios"])

    xy = cells[["x", "y"]].to_numpy(dtype=float)
    pairs = cKDTree(xy).query_pairs(r=eps_m, output_type="ndarray")
    n = len(xy)
    graph = coo_matrix(
        (np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])) if len(pairs) else ([], ([], [])),
        shape=(n, n),
    )
    _, labels = connected_components(graph, directed=False)

    df = cells.assign(_site=labels)
    radio = df["radio"] if "radio" in df else pd.Series("unknown", index=df.index)
    df = df.assign(radio=radio.astype(str))

    sites = (
        df.groupby("_site")
        .agg(
            x=("x", "mean"),
            y=("y", "mean"),
            n_cells=("x", "size"),
            radios=("radio", lambda r: ",".join(sorted(set(r)))),
        )
        .reset_index(drop=True)
    )
    sites.insert(0, "site_id", [f"S{i:05d}" for i in range(len(sites))])
    return sites
