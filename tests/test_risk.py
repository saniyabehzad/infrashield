"""Tests for risk scoring and site clustering, using synthetic data only."""

import numpy as np
import pandas as pd
import pytest

from infrashield.risk import RiskConfig, classify, motion_speed, score_sites
from infrashield.sites import cluster_cells, to_laea


def _grid(cx: float, cy: float, v_up: float, v_east: float, n: int = 5, step: float = 100.0):
    """An n x n grid of motion points centred on (cx, cy), all with the same velocity."""
    offs = (np.arange(n) - n // 2) * step
    xx, yy = np.meshgrid(cx + offs, cy + offs)
    return pd.DataFrame({"x": xx.ravel(), "y": yy.ravel(), "v_up": v_up, "v_east": v_east})


def test_motion_speed_combines_components():
    assert motion_speed(np.array([3.0]), np.array([4.0]))[0] == pytest.approx(5.0)


@pytest.mark.parametrize(
    "speed,n,expected",
    [
        (12.0, 10, "HIGH"),
        (10.0, 3, "HIGH"),
        (6.0, 10, "MEDIUM"),
        (1.0, 10, "LOW"),
        (50.0, 2, "UNKNOWN"),
        (float("nan"), 0, "UNKNOWN"),
    ],
)
def test_classify(speed, n, expected):
    assert classify(speed, n) == expected


def test_score_sites_assigns_expected_tiers_and_order():
    motion = pd.concat(
        [
            _grid(0, 0, v_up=-2, v_east=-11),  # landslide: mostly horizontal
            _grid(5_000, 0, v_up=-6, v_east=0),  # moderate subsidence
            _grid(10_000, 0, v_up=0.5, v_east=0.5),  # stable
        ],
        ignore_index=True,
    )
    sites = pd.DataFrame(
        {
            "site_id": ["stable", "slide", "subside", "forest"],
            "x": [10_000, 0, 5_000, 20_000],
            "y": [0, 0, 0, 0],
        }
    )
    out = score_sites(sites, motion).set_index("site_id")

    assert out.loc["slide", "tier"] == "HIGH"  # caught via the east-west component
    assert out.loc["subside", "tier"] == "MEDIUM"
    assert out.loc["stable", "tier"] == "LOW"
    assert out.loc["forest", "tier"] == "UNKNOWN"  # no radar points nearby
    assert out.loc["forest", "n_points"] == 0
    assert out.loc["subside", "v_up_median"] == pytest.approx(-6)
    assert list(score_sites(sites, motion)["site_id"]) == ["slide", "subside", "stable", "forest"]


def test_radius_controls_evidence():
    motion = _grid(0, 0, v_up=-20, v_east=0)
    sites = pd.DataFrame({"site_id": ["a"], "x": [0.0], "y": [0.0]})
    small = score_sites(sites, motion, RiskConfig(radius_m=50))
    large = score_sites(sites, motion, RiskConfig(radius_m=250))
    assert small.loc[0, "n_points"] == 1 and small.loc[0, "tier"] == "UNKNOWN"
    assert large.loc[0, "n_points"] > 3 and large.loc[0, "tier"] == "HIGH"


def test_missing_columns_raise():
    with pytest.raises(ValueError, match="missing required columns"):
        score_sites(pd.DataFrame({"site_id": [1]}), _grid(0, 0, 0, 0))


def test_cluster_cells_merges_nearby_cells():
    cells = pd.DataFrame(
        {
            "x": [0, 30, 60, 1_000, 1_020],
            "y": [0, 0, 0, 0, 10],
            "radio": ["LTE", "NR", "LTE", "GSM", "LTE"],
        }
    )
    sites = cluster_cells(cells, eps_m=75)
    assert len(sites) == 2
    assert sorted(sites["n_cells"]) == [2, 3]
    assert "LTE,NR" in set(sites["radios"])


def test_to_laea_innsbruck_is_metric():
    # Innsbruck lies roughly at E 4.4e6 m, N 2.7e6 m in EPSG:3035.
    x, y = to_laea(np.array([11.39]), np.array([47.27]))
    assert 4.3e6 < x[0] < 4.5e6 and 2.6e6 < y[0] < 2.8e6
