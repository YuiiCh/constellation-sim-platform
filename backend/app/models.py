"""ORM 数据模型：星座、卫星、壳层、历史星历、仿真任务/结果、覆盖样本、载荷。"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Constellation(Base):
    __tablename__ = "constellations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    ctype: Mapped[str] = mapped_column(String, default="real")  # real | synthetic | composite
    description: Mapped[str | None] = mapped_column(Text)
    celestrak_group: Mapped[str | None] = mapped_column(String)
    source: Mapped[str] = mapped_column(String, default="celestrak")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    satellites: Mapped[list["Satellite"]] = relationship(back_populates="constellation")
    shells: Mapped[list["Shell"]] = relationship(back_populates="constellation")


class Satellite(Base):
    __tablename__ = "satellites"

    norad_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    object_id: Mapped[str | None] = mapped_column(String)
    epoch: Mapped[str] = mapped_column(String, nullable=False)  # ISO8601 UTC
    a_km: Mapped[float] = mapped_column(Float, nullable=False)
    ecc: Mapped[float] = mapped_column(Float, default=0.0)
    inc_deg: Mapped[float] = mapped_column(Float, nullable=False)
    raan_deg: Mapped[float] = mapped_column(Float, nullable=False)
    argp_deg: Mapped[float] = mapped_column(Float, nullable=False)
    ma_deg: Mapped[float] = mapped_column(Float, nullable=False)
    mean_motion: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String, default="synthetic")
    constellation_id: Mapped[str | None] = mapped_column(
        ForeignKey("constellations.id")
    )

    constellation: Mapped["Constellation | None"] = relationship(back_populates="satellites")


class Shell(Base):
    __tablename__ = "shells"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    constellation_id: Mapped[str] = mapped_column(ForeignKey("constellations.id"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, default="stable")  # stable | temporary
    altitude_km: Mapped[float] = mapped_column(Float)
    inclination_deg: Mapped[float] = mapped_column(Float)
    count: Mapped[int] = mapped_column(Integer, default=0)
    is_default: Mapped[bool] = mapped_column(Boolean, default=True)

    constellation: Mapped["Constellation"] = relationship(back_populates="shells")


class ConstellationSatellite(Base):
    __tablename__ = "constellation_satellites"
    __table_args__ = (UniqueConstraint("constellation_id", "norad_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    constellation_id: Mapped[str] = mapped_column(ForeignKey("constellations.id"))
    norad_id: Mapped[int] = mapped_column(ForeignKey("satellites.norad_id"))
    shell_id: Mapped[int | None] = mapped_column(ForeignKey("shells.id"))


class HistoricalEphemeris(Base):
    __tablename__ = "historical_ephemeris"
    __table_args__ = (UniqueConstraint("norad_id", "epoch"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    norad_id: Mapped[int] = mapped_column(Integer, nullable=False)
    epoch: Mapped[str] = mapped_column(String, nullable=False)
    a_km: Mapped[float] = mapped_column(Float)
    ecc: Mapped[float] = mapped_column(Float)
    inc_deg: Mapped[float] = mapped_column(Float)
    raan_deg: Mapped[float] = mapped_column(Float)
    argp_deg: Mapped[float] = mapped_column(Float)
    ma_deg: Mapped[float] = mapped_column(Float)
    mean_motion: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class SimulationTask(Base):
    __tablename__ = "simulation_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    constellation_id: Mapped[str] = mapped_column(String, nullable=False)
    rule_type: Mapped[str] = mapped_column(String, default="simple_elevation")
    status: Mapped[str] = mapped_column(String, default="pending")
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    params_json: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    stage_timings_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


class SimulationResult(Base):
    __tablename__ = "simulation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("simulation_tasks.id"), unique=True)
    summary_json: Mapped[str | None] = mapped_column(Text)


class CoverageSample(Base):
    __tablename__ = "coverage_samples"
    __table_args__ = (
        UniqueConstraint("task_id", "time_step", "h3_index"),
        {
            "sqlite_autoincrement": True,
        },
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("simulation_tasks.id"), index=True)
    time_step: Mapped[int] = mapped_column(Integer, index=True)
    timestamp_utc: Mapped[str] = mapped_column(String)
    h3_index: Mapped[str] = mapped_column(String, index=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    covered_simple: Mapped[bool] = mapped_column(Boolean, default=False)
    covered_complex: Mapped[bool] = mapped_column(Boolean, default=False)
    covering_norad_ids: Mapped[str | None] = mapped_column(Text)
    max_elevation_deg: Mapped[float | None] = mapped_column(Float)
    max_c_dBm: Mapped[float | None] = mapped_column(Float)
    distance_km: Mapped[float | None] = mapped_column(Float)


class Payload(Base):
    __tablename__ = "payloads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    satellite_norad_id: Mapped[int | None] = mapped_column(ForeignKey("satellites.norad_id"))
    constellation_id: Mapped[str | None] = mapped_column(ForeignKey("constellations.id"))
    freq_hz: Mapped[float] = mapped_column(Float, default=19.7e9)
    bandwidth_hz: Mapped[float] = mapped_column(Float, default=30e6)
    eirp_dBW: Mapped[float] = mapped_column(Float, default=25.0)
    g_r_dbi: Mapped[float] = mapped_column(Float, default=3.0)
    t_s_k: Mapped[float] = mapped_column(Float, default=300.0)
    l_atm_db: Mapped[float] = mapped_column(Float, default=2.0)
    l_pol_db: Mapped[float] = mapped_column(Float, default=0.5)
    l_point_db: Mapped[float] = mapped_column(Float, default=0.5)
