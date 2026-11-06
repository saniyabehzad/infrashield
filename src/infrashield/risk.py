"""Deterministic, explainable ground-motion risk scoring for network sites.

The LLM agent never computes risk itself: it calls functions built on this
module and explains their output. Keep everything here transparent and testable.

Inputs (all coordinates in EPSG:3035, metres; velocities in mm/yr):
    sites:  DataFrame with columns ``site_id``, ``x``, ``y``
    motion: DataFrame with columns ``x``, ``y``, ``v_up``, ``v_east``
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

TIERS = ("HIGH", "MEDIUM", "LOW", "UNKNOWN")


@dataclass(frozen=True)
class RiskConfig:
    """Thresholds for risk tiers. Defaults follow common EGMS study values."""

    radius_m: float = 250.0
    """Search radius around each site."""
    high_mm_yr: float = 10.0
    """90th-percentile motion speed at or above this -> HIGH."""
    medium_mm_yr: float = 5.0
    """90th-percentile motion speed at or above this -> MEDIUM."""
    min_points: int = 3
    """Fewer measurement points than this -> UNKNOWN (insufficient evidence)."""
    percentile: float = 90.0
    """Percentile of point speeds used for the tier decision (robust to outliers)."""


def motion_speed(v_up: np.ndarray, v_east: np.ndarray) -> np.ndarray:
    """Total motion speed in mm/yr, combining vertical and east-west components.

    Alpine landslides move mostly downslope, so horizontal motion matters as
    much as subsidence. Using only ``v_up`` would miss them.
    """
    return np.hypot(np.asarray(v_up, dtype=float), np.asarray(v_east, dtype=float))


def classify(speed_pctl: float, n_points: int, cfg: RiskConfig | None = None) -> str:
    """Map a site's percentile motion speed and evidence count to a tier."""
    cfg = cfg or RiskConfig()
    if n_points < cfg.min_points or np.isnan(speed_pctl):
        return "UNKNOWN"
    if speed_pctl >= cfg.high_mm_yr:
        return "HIGH"
    if speed_pctl >= cfg.medium_mm_yr:
        return "MEDIUM"
    return "LOW"


def score_sites(
    sites: pd.DataFrame, motion: pd.DataFrame, cfg: RiskConfig | None = None
) -> pd.DataFrame:
    """Score every site against the ground-motion points within ``cfg.radius_m``.

    Returns one row per site with the evidence behind its tier:
    ``n_points``, ``speed_median``, ``speed_pctl``, ``speed_max``,
    ``v_up_median`` (negative = subsiding), ``v_east_median`` and ``tier``.
    The result is sorted from highest to lowest risk.
    """
    cfg = cfg or RiskConfig()
    _require(sites, ["site_id", "x", "y"], "sites")
    _require(motion, ["x", "y", "v_up", "v_east"], "motion")

    speed = motion_speed(motion["v_up"].to_numpy(), motion["v_east"].to_numpy())
    v_up = motion["v_up"].to_numpy(dtype=float)
    v_east = motion["v_east"].to_numpy(dtype=float)

    tree = cKDTree(motion[["x", "y"]].to_numpy(dtype=float))
    neighbours = tree.query_ball_point(sites[["x", "y"]].to_numpy(dtype=float), r=cfg.radius_m)

    rows = []
    for site_id, idx in zip(sites["site_id"], neighbours):
        n = len(idx)
        if n:
            s = speed[idx]
            stats = {
                "speed_median": float(np.median(s)),
                "speed_pctl": float(np.percentile(s, cfg.percentile)),
                "speed_max": float(np.max(s)),
                "v_up_median": float(np.median(v_up[idx])),
                "v_east_median": float(np.median(v_east[idx])),
            }
        else:
            stats = dict.fromkeys(
                ["speed_median", "speed_pctl", "speed_max", "v_up_median", "v_east_median"],
                np.nan,
            )
        rows.append(
            {
                "site_id": site_id,
                "n_points": n,
                **stats,
                "tier": classify(stats["speed_pctl"], n, cfg),
            }
        )

    result = pd.DataFrame(rows)
    order = {t: i for i, t in enumerate(TIERS)}
    result["_rank"] = result["tier"].map(order)
    return (
        result.sort_values(["_rank", "speed_pctl"], ascending=[True, False])
        .drop(columns="_rank")
        .reset_index(drop=True)
    )


def _require(df: pd.DataFrame, cols: list[str], name: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{name} is missing required columns: {missing}")
