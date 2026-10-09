"""后端单元测试：轨道传播与覆盖仿真引擎（无需网络）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone, timedelta

from app.coverage import run_coverage
from app.orbital import propagate_subpoints, geodetic_to_ecef, a_to_mean_motion


def _qianfan_elements():
    from app.database import SessionLocal
    from app.models import Satellite
    from sqlalchemy import select

    db = SessionLocal()
    sats = db.execute(select(Satellite).where(Satellite.constellation_id == "qianfan")).scalars().all()
    out = [
        {
            "norad_id": s.norad_id,
            "name": s.name,
            "epoch": s.epoch,
            "a_km": s.a_km,
            "ecc": s.ecc,
            "inc_deg": s.inc_deg,
            "raan_deg": s.raan_deg,
            "argp_deg": s.argp_deg,
            "ma_deg": s.ma_deg,
            "mean_motion": s.mean_motion,
        }
        for s in sats
    ]
    db.close()
    return out


def test_propagate_shapes():
    els = _qianfan_elements()
    assert len(els) > 0
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    res = propagate_subpoints(els, [start, start + timedelta(hours=1)])
    assert res["lat"].shape == (len(els), 2)
    # 子点纬度应在合理范围
    assert res["lat"].min() >= -90 and res["lat"].max() <= 90


def test_coverage_simple_runs():
    els = _qianfan_elements()
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    params = {
        "region": [30.0, 110.0, 38.0, 120.0],
        "h3_res": 4,
        "el_min_deg": 10,
        "eirp_dBW": 47,
        "freq_hz": 12e9,
        "c_min_dbm": -100,
    }
    r = run_coverage(els, start, 3 * 3600, 300, "simple_elevation", params)
    assert r["summary"]["total_cells"] > 0
    assert "propagation_s" in r["stage_timings"]
    assert len(r["samples"]) > 0
    assert 0.0 <= r["summary"]["overall_coverage_simple"] <= 1.0


def test_geodetic_roundtrip():
    x, y, z = geodetic_to_ecef(0.0, 0.0, 0.0)
    assert abs((x**2 + y**2 + z**2) ** 0.5 - 6378.137) < 1e-3


def test_a_to_mean_motion():
    # 约 550km 近圆轨道，周期约 95 分钟 → 每日约 15 圈
    a = 6378.137 + 550
    rev_per_day = a_to_mean_motion(a)  # 返回 rev/day
    period_min = 1440.0 / rev_per_day
    assert 90 < period_min < 100
