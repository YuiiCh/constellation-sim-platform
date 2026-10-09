"""后端全局配置：从环境变量读取，缺失时使用推荐默认值。"""
from __future__ import annotations

import os
from functools import lru_cache


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _get_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name, None)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    """全局配置对象，全部带默认值/推荐值，避免任何魔法数散落。"""

    # ---- 数据目录与数据库 ----
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR: str = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))
    SQLITE_PATH: str = os.environ.get(
        "SQLITE_PATH", os.path.join(DATA_DIR, "constellation.db")
    )

    # ---- celestrak 拉取 ----
    CELESTRAK_FETCH_INTERVAL: int = _get_int("CELESTRAK_FETCH_INTERVAL", 7200)
    CELESTRAK_TIMEOUT: int = _get_int("CELESTRAK_TIMEOUT", 20)
    CELESTRAK_ENABLED: bool = _get_bool("CELESTRAK_ENABLED", False)
    # 预先登记的 celestrak group（通讯卫星栏目）
    CELESTRAK_GROUPS: list[str] = [
        "oneweb",
        "starlink",
        "iridium-NEXT",
        "globalstar",
        "orbcomm",
        "geo",
    ]

    # ---- 时间轴倍率（前端可用，这里提供默认值集合） ----
    TIMELINE_RATES: list[int] = [1, 10, 60, 600]

    # ---- 仿真默认参数（与 docs/coverage_analysis_design.md 对齐） ----
    DEFAULT_SAMPLE_INTERVAL_S: int = _get_int("DEFAULT_SAMPLE_INTERVAL_S", 15)
    DEFAULT_DURATION_H: int = _get_int("DEFAULT_DURATION_H", 24)
    DEFAULT_EL_MIN_DEG: float = _get_float("DEFAULT_EL_MIN_DEG", 10.0)
    DEFAULT_C_MIN_DBM: float = _get_float("DEFAULT_C_MIN_DBM", -100.0)
    DEFAULT_H3_RES: int = _get_int("DEFAULT_H3_RES", 4)
    DEFAULT_FREQ_HZ: float = _get_float("DEFAULT_FREQ_HZ", 12.0e9)
    DEFAULT_BANDWIDTH_HZ: float = _get_float("DEFAULT_BANDWIDTH_HZ", 30e6)
    DEFAULT_EIRP_DBW: float = _get_float("DEFAULT_EIRP_DBW", 47.0)
    DEFAULT_G_R_DBI: float = _get_float("DEFAULT_G_R_DBI", 3.0)
    DEFAULT_T_S_K: float = _get_float("DEFAULT_T_S_K", 300.0)
    DEFAULT_L_ATM_DB: float = _get_float("DEFAULT_L_ATM_DB", 2.0)
    DEFAULT_L_POL_DB: float = _get_float("DEFAULT_L_POL_DB", 0.5)
    DEFAULT_L_POINT_DB: float = _get_float("DEFAULT_L_POINT_DB", 0.5)
    DEFAULT_REGION: list[float] = [18.0, 73.0, 54.0, 135.0]  # lat_min, lon_min, lat_max, lon_max

    # ---- 渲染/性能 ----
    MAX_FPS: list[int] = [5, 10, 15, 30, 45, 60]
    DEFAULT_MAX_FPS: int = _get_int("DEFAULT_MAX_FPS", 30)

    # ---- 服务器 ----
    HOST: str = os.environ.get("HOST", "0.0.0.0")
    PORT: int = _get_int("PORT", 8080)


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# 确保数据目录存在
os.makedirs(Settings().DATA_DIR, exist_ok=True)
