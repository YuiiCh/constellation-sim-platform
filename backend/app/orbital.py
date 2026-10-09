"""轨道传播：二体 + J2 一阶长期项的开普勒模型（NumPy 向量化）。

用于：
- 覆盖仿真（后端，求卫星 ECEF 位置）
- 提供卫星位置 API（前端 Web Worker 也可本地复算，用于地球渲染/轨道线）

所有角单位为弧度，长度单位 km，时间单位秒（UNIX 秒）。
"""
from __future__ import annotations

import numpy as np
from datetime import datetime, timezone

MU = 398600.4418  # 地球引力常数 km^3/s^2
RE = 6378.137  # 地球赤道半径 km
OMEGA_E = 7.2921159e-5  # 地球自转角速度 rad/s
J2 = 1.08262668e-3
DEG = np.pi / 180.0


def julian_date(dt: datetime) -> float:
    """UTC datetime -> 儒略日。"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return 2440587.5 + dt.timestamp() / 86400.0


def gmst_rad(dt: datetime) -> float:
    """IAU-1982 近似：给定 UTC 时刻的格林尼治平恒星时（弧度）。"""
    jd = julian_date(dt)
    T = (jd - 2451545.0) / 36525.0
    sec = (
        67310.54841
        + (876600.0 * 3600 + 8640184.812866) * T
        + 0.093104 * T * T
        - 6.2e-6 * T * T * T
    )
    sec %= 86400.0
    return (sec / 240.0) * DEG  # 86400s ≡ 360° → 1s ≡ 1/240°


def mean_motion_to_a(mean_motion_rev_per_day: float) -> float:
    """rev/day -> 半长轴 km。"""
    n = mean_motion_rev_per_day * 2 * np.pi / 86400.0
    return (MU / n**2) ** (1.0 / 3.0)


def a_to_mean_motion(a_km: float) -> float:
    n = np.sqrt(MU / a_km**3)
    return n * 86400.0 / (2 * np.pi)


def build_sat_arrays(sats: list[dict]) -> dict:
    """将卫星元素列表转为 NumPy 数组，便于向量化传播。

    每个 sat 含：epoch(datetime)、a、ecc、inc_deg、raan_deg、argp_deg、ma_deg。
    """
    S = len(sats)
    epoch_unix = np.empty(S)
    a = np.empty(S)
    ecc = np.empty(S)
    inc = np.empty(S)
    raan = np.empty(S)
    argp = np.empty(S)
    ma0 = np.empty(S)
    gmst0 = np.empty(S)
    for i, s in enumerate(sats):
        ep = s["epoch"]
        if isinstance(ep, str):
            ep = datetime.fromisoformat(ep.replace("Z", "+00:00"))
        if ep.tzinfo is None:
            ep = ep.replace(tzinfo=timezone.utc)
        epoch_unix[i] = ep.timestamp()
        a[i] = float(s["a_km"])
        ecc[i] = float(s.get("ecc", 0.0))
        inc[i] = float(s["inc_deg"]) * DEG
        raan[i] = float(s["raan_deg"]) * DEG
        argp[i] = float(s["argp_deg"]) * DEG
        ma0[i] = float(s["ma_deg"]) * DEG
        gmst0[i] = gmst_rad(ep)
    # 平均运动 n (rad/s) = sqrt(mu/a^3)
    n = np.sqrt(MU / a**3)
    return {
        "epoch_unix": epoch_unix,
        "a": a,
        "ecc": ecc,
        "inc": inc,
        "raan": raan,
        "argp": argp,
        "ma0": ma0,
        "gmst0": gmst0,
        "n": n,
    }


def propagate_ecef(sat_arr: dict, times_unix: np.ndarray) -> tuple:
    """向量化传播：返回 (x,y,z) ECEF 数组，形状均为 (S, T)。"""
    a = sat_arr["a"]
    ecc = sat_arr["ecc"]
    inc = sat_arr["inc"]
    raan0 = sat_arr["raan"]
    argp0 = sat_arr["argp"]
    ma0 = sat_arr["ma0"]
    gmst0 = sat_arr["gmst0"]
    n = sat_arr["n"]
    epoch_unix = sat_arr["epoch_unix"]

    T = times_unix.shape[0]
    delta = times_unix[None, :] - epoch_unix[:, None]  # (S, T)

    # J2 一阶长期项（RAAN 进动 + 近地点幅角变化）
    p = a * (1 - ecc**2)
    raan_dot = -1.5 * n * J2 * (RE / p) ** 2 * np.cos(inc)
    argp_dot = 0.75 * n * J2 * (RE / p) ** 2 * (4 - 5 * np.sin(inc) ** 2)

    raan = raan0[:, None] + raan_dot[:, None] * delta
    argp = argp0[:, None] + argp_dot[:, None] * delta
    M = ma0[:, None] + n[:, None] * delta

    # 牛顿迭代解开普勒方程 E - e sinE = M
    E = M + ecc[:, None] * np.sin(M)
    for _ in range(8):
        f = E - ecc[:, None] * np.sin(E) - M
        fp = 1 - ecc[:, None] * np.cos(E)
        E = E - f / fp

    nu = 2 * np.arctan2(
        np.sqrt(1 + ecc[:, None]) * np.sin(E / 2),
        np.sqrt(1 - ecc[:, None]) * np.cos(E / 2),
    )
    r = a[:, None] * (1 - ecc[:, None] * np.cos(E))

    xp = r * np.cos(nu)
    yp = r * np.sin(nu)

    cosO = np.cos(raan)
    sinO = np.sin(raan)
    cosi = np.cos(inc)[:, None]
    sini = np.sin(inc)[:, None]
    cosw = np.cos(argp)
    sinw = np.sin(argp)

    x_eci = (cosO * cosw - sinO * sinw * cosi) * xp + (
        -cosO * sinw - sinO * cosw * cosi
    ) * yp
    y_eci = (sinO * cosw + cosO * sinw * cosi) * xp + (
        -sinO * sinw + cosO * cosw * cosi
    ) * yp
    z_eci = (sinw * sini) * xp + (cosw * sini) * yp

    theta = gmst0[:, None] + OMEGA_E * delta
    cosT = np.cos(theta)
    sinT = np.sin(theta)

    x_ecef = x_eci * cosT + y_eci * sinT
    y_ecef = -x_eci * sinT + y_eci * cosT
    z_ecef = z_eci

    return x_ecef, y_ecef, z_ecef


def geodetic_to_ecef(lat_deg, lon_deg, alt_km: float = 0.0) -> tuple:
    """经纬度(deg)+高度(km) -> ECEF(km)。支持标量。"""
    lat = np.radians(lat_deg)
    lon = np.radians(lon_deg)
    r = RE + alt_km
    x = r * np.cos(lat) * np.cos(lon)
    y = r * np.cos(lat) * np.sin(lon)
    z = r * np.sin(lat)
    return float(x), float(y), float(z)


def ecef_to_geodetic(x, y, z):
    """ECEF(km) -> (lat_deg, lon_deg, alt_km)。广播支持数组。"""
    r = np.sqrt(x**2 + y**2 + z**2)
    lat = np.arcsin(np.divide(z, r, out=np.zeros_like(r), where=r != 0))
    lon = np.arctan2(y, x)
    alt = r - RE
    return lat / DEG, lon / DEG, alt


def propagate_subpoints(sats: list[dict], datetimes: list[datetime]) -> dict:
    """便捷接口：返回每颗卫星在给定时刻的 (lat, lon, alt) 子点。

    返回 dict: { 'lat': (S,T) deg, 'lon': (S,T) deg, 'alt': (S,T) km,
                 'x':(S,T), 'y':(S,T), 'z':(S,T) ecef km }
    """
    sat_arr = build_sat_arrays(sats)
    times_unix = np.array([d.timestamp() for d in datetimes])
    x, y, z = propagate_ecef(sat_arr, times_unix)
    lat, lon, alt = ecef_to_geodetic(x, y, z)
    return {"lat": lat, "lon": lon, "alt": alt, "x": x, "y": y, "z": z}
