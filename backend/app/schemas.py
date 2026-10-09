"""Pydantic 数据模型：API 请求/响应契约。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ShellOut(BaseModel):
    id: int
    constellation_id: str
    name: str
    kind: str
    altitude_km: float
    inclination_deg: float
    count: int
    is_default: bool


class ConstellationOut(BaseModel):
    id: str
    name: str
    ctype: str
    description: Optional[str]
    celestrak_group: Optional[str]
    source: str
    shell_count: int = 0
    satellite_count: int = 0


class SatelliteOut(BaseModel):
    norad_id: int
    name: str
    object_id: Optional[str] = None
    epoch: str
    a_km: float
    ecc: float
    inc_deg: float
    raan_deg: float
    argp_deg: float
    ma_deg: float
    mean_motion: Optional[float] = None
    source: str
    constellation_id: Optional[str] = None


class SatelliteDetailOut(SatelliteOut):
    shells: list[str] = []


class ConfigOut(BaseModel):
    timeline_rates: list[int]
    max_fps_options: list[int]
    default_sample_interval_s: int
    default_duration_h: int
    default_el_min_deg: float
    default_c_min_dbm: float
    default_h3_res: int
    default_region: list[float]
    default_freq_hz: float
    default_bandwidth_hz: float
    default_eirp_dBW: float
    default_g_r_dbi: float
    default_t_s_k: float
    default_l_atm_db: float
    default_l_pol_db: float
    default_l_point_db: float
    celestrak_enabled: bool
    celestrak_fetch_interval: int
    timezones: list[str]


class SimulationCreate(BaseModel):
    name: str
    constellation_id: str
    rule_type: str = "simple_elevation"  # simple_elevation | complex_power
    start_utc: Optional[str] = None  # ISO8601；缺省为"今天 00:00 UTC"
    duration_h: int = Field(default=24, ge=1, le=72)
    sample_interval_s: int = Field(default=15, ge=1)
    h3_res: Optional[int] = None
    region: Optional[list[float]] = None  # [lat_min,lon_min,lat_max,lon_max]
    selected_norad_ids: Optional[list[int]] = None
    selected_shell_ids: Optional[list[int]] = None  # 缺省=稳态壳层
    use_default_shells: bool = True
    params: dict[str, Any] = Field(default_factory=dict)


class SimulationOut(BaseModel):
    id: int
    name: str
    constellation_id: str
    rule_type: str
    status: str
    progress: float
    error: Optional[str] = None
    stage_timings: Optional[dict] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class CoverageSampleOut(BaseModel):
    time_step: int
    timestamp_utc: str
    h3_index: str
    lat: float
    lon: float
    covered_simple: bool
    covered_complex: bool
    covering_norad_ids: list[int]
    max_elevation_deg: Optional[float]
    max_c_dBm: Optional[float]
    distance_km: Optional[float]


class SimulationDetailOut(SimulationOut):
    params: Optional[dict] = None
    summary: Optional[dict] = None


class FetchResult(BaseModel):
    ok: bool
    message: str
    fetched: int = 0


class SpaceTrackQuery(BaseModel):
    norad_id: int
    epoch_start: Optional[str] = None
    epoch_end: Optional[str] = None
    identity: str = ""  # space-track 用户名
    password: str = ""  # space-track 密码


class SpaceTrackResult(BaseModel):
    ok: bool
    message: str
    count: int = 0
    rate_limited: bool = False
    needs_credentials: bool = False
