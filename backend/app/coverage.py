"""覆盖仿真引擎：H3 网格 × 卫星 × 时间步，向量化计算覆盖率。

分阶段计时：propagation / elevation / power / aggregation，结果可复现（确定性计算）。
"""
from __future__ import annotations

import json
import math
import time

import numpy as np

from . import orbital
from .config import Settings
from .h3grid import generate_h3_cells

C_LIGHT = 299792458.0  # m/s


def default_coverage_params() -> dict:
    s = Settings()
    return {
        "el_min_deg": s.DEFAULT_EL_MIN_DEG,
        "c_min_dbm": s.DEFAULT_C_MIN_DBM,
        "eirp_dBW": s.DEFAULT_EIRP_DBW,
        "freq_hz": s.DEFAULT_FREQ_HZ,
        "bandwidth_hz": s.DEFAULT_BANDWIDTH_HZ,
        "g_r_dbi": s.DEFAULT_G_R_DBI,
        "t_s_k": s.DEFAULT_T_S_K,
        "l_atm_db": s.DEFAULT_L_ATM_DB,
        "l_pol_db": s.DEFAULT_L_POL_DB,
        "l_point_db": s.DEFAULT_L_POINT_DB,
        "region": s.DEFAULT_REGION,
        "h3_res": s.DEFAULT_H3_RES,
        "sample_interval_s": s.DEFAULT_SAMPLE_INTERVAL_S,
        "viz_interval_s": 1800,  # 覆盖网格动画帧间隔（默认 30 分钟）
    }


def run_coverage(
    satellites: list[dict],
    start_dt,
    duration_s: int,
    sample_interval_s: int,
    rule_type: str = "simple_elevation",
    params: dict | None = None,
    seed: int | None = None,
    progress_callback=None,
) -> dict:
    """执行覆盖仿真。

    参数
    ----
    satellites: 轨道元素列表（含 norad_id, name, epoch, a_km, ecc, inc_deg, raan_deg, argp_deg, ma_deg）
    start_dt: 仿真起始 UTC datetime
    duration_s: 仿真时长（秒）
    sample_interval_s: 采样间隔（秒）
    rule_type: 'simple_elevation' | 'complex_power'
    params: 覆盖规则与区域参数（缺省用 default_coverage_params 合并）

    返回
    ----
    {
      'samples': [ {task_id占位由调用方填充} ... ],   # 降采样网格帧，用于持久化
      'summary': { ... },                              # 汇总指标 + 分阶段耗时 + 单元聚合
      'stage_timings': { ... },
    }
    """
    p = default_coverage_params()
    if params:
        p.update(params)

    el_min = float(p["el_min_deg"])
    rule = rule_type if rule_type in ("simple_elevation", "complex_power") else "simple_elevation"
    complex_rule = rule == "complex_power"

    eirp = float(p["eirp_dBW"])
    freq = float(p["freq_hz"])
    l_atm = float(p["l_atm_db"])
    l_pol = float(p["l_pol_db"])
    l_point = float(p["l_point_db"])
    c_min = float(p["c_min_dbm"])
    batch_size = int(p.get("viz_interval_s", 1800) // max(1, sample_interval_s))
    if batch_size < 1:
        batch_size = 1

    # ---- 时间步 ----
    n_steps = max(1, int(round(duration_s / sample_interval_s)) + 1)
    times = [start_dt.fromtimestamp(start_dt.timestamp() + i * sample_interval_s) for i in range(n_steps)]
    times_unix = np.array([t.timestamp() for t in times])

    # ---- H3 网格 ----
    t0 = time.perf_counter()
    cells = generate_h3_cells(p["region"], int(p["h3_res"]))
    C = len(cells)
    g_ecef = np.array([[c["ecef"][0], c["ecef"][1], c["ecef"][2]] for c in cells], dtype=float)
    g_unit = g_ecef / orbital.RE  # 地面点高度 0，单位向量

    # ---- 传播（一次性） ----
    sat_arr = orbital.build_sat_arrays(satellites)
    S = sat_arr["a"].shape[0]
    X, Y, Z = orbital.propagate_ecef(sat_arr, times_unix)  # (S, T, 3)
    pos = np.stack([X, Y, Z], axis=-1)  # (S, T, 3)
    stage_prop = time.perf_counter() - t0

    # ---- 逐时间步计算 ----
    t1 = time.perf_counter()
    per_step_simple = np.zeros(n_steps, dtype=float)
    per_step_complex = np.zeros(n_steps, dtype=float) if complex_rule else None

    # 单元级聚合
    cell_best_el = np.full(C, -90.0)
    cell_best_cdbm = np.full(C, -200.0) if complex_rule else None
    cell_covered_frames = np.zeros(C, dtype=int)
    cell_covering = [set() for _ in range(C)]

    samples: list[dict] = []
    norad_by_idx = [s["norad_id"] for s in satellites]

    t2 = time.perf_counter()
    for ti in range(n_steps):
        s_pos = pos[:, ti, :]  # (S,3)
        rho = s_pos[:, None, :] - g_ecef[None, :, :]  # (S,C,3)
        dist = np.sqrt(np.sum(rho * rho, axis=-1))  # (S,C)
        dot = np.sum(rho * g_unit[None, :, :], axis=-1)  # (S,C)
        with np.errstate(invalid="ignore", divide="ignore"):
            el = np.arcsin(np.clip(dot / dist, -1.0, 1.0))  # (S,C) rad
        el_deg = np.degrees(el)
        max_el = el_deg.max(axis=0)  # (C,)
        arg = el_deg.argmax(axis=0)  # (C,)
        covered_simple = max_el >= el_min
        per_step_simple[ti] = float(covered_simple.mean())

        if complex_rule:
            d_m = dist * 1000.0
            l_fs = 20.0 * np.log10(4.0 * math.pi * d_m * freq / C_LIGHT)
            cdbm = eirp - l_fs - l_atm - l_pol - l_point + 30.0  # (S,C)
            max_cdbm = cdbm.max(axis=0)  # (C,)
            covered_complex = (max_el >= el_min) & (max_cdbm >= c_min)
            per_step_complex[ti] = float(covered_complex.mean())

        # 聚合（仅覆盖单元更新，减少开销）
        cov_idx = np.where(covered_simple)[0]
        cell_covered_frames[cov_idx] += 1
        np.maximum.at(cell_best_el, cov_idx, max_el[cov_idx])
        if complex_rule:
            np.maximum.at(cell_best_cdbm, cov_idx, max_cdbm[cov_idx])
        # 仅对覆盖单元记录覆盖卫星（用于点击详情/连线）
        if cov_idx.size > 0:
            for ci in cov_idx.tolist():
                cell_covering[ci].add(int(norad_by_idx[int(arg[ci])]))

        # 降采样帧：写入覆盖样本（全单元，供热力图）
        if ti % batch_size == 0:
            if progress_callback is not None:
                progress_callback((ti + 1) / n_steps)
            ts_iso = times[ti].isoformat()
            for ci in range(C):
                ce = float(max_el[ci])
                csim = bool(ce >= el_min)
                ccom = bool(csim and (not complex_rule or float(max_cdbm[ci]) >= c_min))
                covering = [int(norad_by_idx[int(arg[ci])])] if csim else []
                samples.append(
                    {
                        "time_step": ti,
                        "timestamp_utc": ts_iso,
                        "h3_index": cells[ci]["h3_index"],
                        "lat": float(cells[ci]["lat"]),
                        "lon": float(cells[ci]["lon"]),
                        "covered_simple": csim,
                        "covered_complex": ccom,
                        "covering_norad_ids": json.dumps(covering),
                        "max_elevation_deg": round(ce, 3),
                        "max_c_dBm": (None if not complex_rule else round(float(max_cdbm[ci]), 3)),
                        "distance_km": (None if not csim else round(float(dist[int(arg[ci]), ci]), 1)),
                    }
                )
    stage_elev = time.perf_counter() - t2
    stage_power = 0.0  # 已并入 elevation 循环内（复杂规则）

    # ---- 汇总 ----
    t3 = time.perf_counter()
    n_frames = (n_steps + batch_size - 1) // batch_size
    cell_agg = []
    for ci in range(C):
        cell_agg.append(
            {
                "h3_index": cells[ci]["h3_index"],
                "lat": float(cells[ci]["lat"]),
                "lon": float(cells[ci]["lon"]),
                "boundary": cells[ci]["boundary"],
                "covered_frac_simple": round(float(cell_covered_frames[ci]) / n_frames, 4),
                "best_elevation_deg": (None if cell_best_el[ci] <= -90 else round(float(cell_best_el[ci]), 3)),
                "best_c_dBm": (None if not complex_rule else round(float(cell_best_cdbm[ci]), 3)),
                "covering_norad_ids": sorted(cell_covering[ci]),
            }
        )

    summary = {
        "rule_type": rule,
        "total_cells": C,
        "total_satellites": S,
        "n_steps": n_steps,
        "sample_interval_s": sample_interval_s,
        "viz_interval_s": int(batch_size * sample_interval_s),
        "start_utc": times[0].isoformat(),
        "end_utc": times[-1].isoformat(),
        "el_min_deg": el_min,
        "c_min_dbm": c_min,
        "region": p["region"],
        "h3_res": int(p["h3_res"]),
        "per_step_coverage_simple": np.round(per_step_simple, 4).tolist(),
        "per_step_coverage_complex": (None if not complex_rule else np.round(per_step_complex, 4).tolist()),
        "overall_coverage_simple": round(float(per_step_simple.mean()), 4),
        "overall_coverage_complex": (None if not complex_rule else round(float(per_step_complex.mean()), 4)),
        "cell_aggregates": cell_agg,
        "seed": seed,
    }
    stage_agg = time.perf_counter() - t3

    stage_timings = {
        "propagation_s": round(stage_prop, 3),
        "elevation_s": round(stage_elev, 3),
        "power_s": round(stage_power, 3),
        "aggregation_s": round(stage_agg, 3),
        "total_s": round(stage_prop + stage_elev + stage_agg, 3),
    }
    summary["stage_timings"] = stage_timings

    return {"samples": samples, "summary": summary, "stage_timings": stage_timings}
