"""数据库初始化与种子数据：星座、壳层、卫星（合成轨道根数）、默认载荷。"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select

from .config import Settings
from .constellations import build_satellites_for_spec, get_constellation_specs
from .database import Base, SessionLocal
from .models import (
    Constellation,
    ConstellationSatellite,
    CoverageSample,
    Payload,
    Satellite,
    Shell,
    SimulationResult,
)

logger = logging.getLogger("seed")


def _sat_to_model(sat: dict, constellation_id: str) -> Satellite:
    return Satellite(
        norad_id=sat["norad_id"],
        name=sat["name"],
        object_id=sat.get("object_id"),
        epoch=sat["epoch"],
        a_km=sat["a_km"],
        ecc=sat.get("ecc", 0.0),
        inc_deg=sat["inc_deg"],
        raan_deg=sat["raan_deg"],
        argp_deg=sat["argp_deg"],
        ma_deg=sat["ma_deg"],
        mean_motion=sat.get("mean_motion"),
        source="synthetic-fallback",
        constellation_id=constellation_id,
    )


def seed_database(force: bool = False) -> None:
    """若星座表为空（或 force），则写入全部种子数据。"""
    db = SessionLocal()
    try:
        existing = db.scalar(select(func.count()).select_from(Constellation))
        if existing and not force:
            logger.info("数据库已有星座数据，跳过种子。")
            return
        if force:
            logger.info("强制重建种子数据。")
            db.query(CoverageSample).delete()
            db.query(SimulationResult).delete()
            db.query(ConstellationSatellite).delete()
            db.query(Satellite).delete()
            db.query(Shell).delete()
            db.query(Payload).delete()
            db.query(Constellation).delete()
            db.commit()

        s = Settings()
        specs = get_constellation_specs()
        epoch = datetime.now(timezone.utc)
        id_counter = [900000]

        for spec in specs:
            cons = Constellation(
                id=spec["id"],
                name=spec["name"],
                ctype=spec["ctype"],
                description=spec.get("description"),
                celestrak_group=spec.get("celestrak_group"),
                source=spec.get("source", "synthetic-fallback"),
            )
            db.add(cons)
            db.flush()

            if spec.get("walker"):
                w = spec["walker"]
                shell = Shell(
                    constellation_id=spec["id"], name=spec["shells"][0]["name"],
                    kind=spec["shells"][0]["kind"], altitude_km=w["alt_km"],
                    inclination_deg=w["inc_deg"], count=w["total"],
                    is_default=spec["shells"][0]["is_default"],
                )
                db.add(shell)
                db.flush()
                sats = build_satellites_for_spec(spec, epoch, id_counter)
                for sat in sats:
                    db.add(_sat_to_model(sat, spec["id"]))
                    db.add(ConstellationSatellite(constellation_id=spec["id"], norad_id=sat["norad_id"], shell_id=shell.id))
            else:
                for sh in spec["shells"]:
                    shell = Shell(
                        constellation_id=spec["id"], name=sh["name"], kind=sh["kind"],
                        altitude_km=sh["alt_km"], inclination_deg=sh["inc_deg"],
                        count=sh["planes"] * sh["per_plane"], is_default=sh["is_default"],
                    )
                    db.add(shell)
                    db.flush()
                    sub_spec = dict(spec)
                    sub_spec["shells"] = [sh]
                    # 仅生成该壳层：临时构造单壳层 spec
                    sats = build_satellites_for_spec(
                        {**spec, "shells": [sh], "walker": None}, epoch, id_counter
                    )
                    for sat in sats:
                        db.add(_sat_to_model(sat, spec["id"]))
                        db.add(ConstellationSatellite(constellation_id=spec["id"], norad_id=sat["norad_id"], shell_id=shell.id))

            # 默认载荷（复杂规则使用）
            db.add(
                Payload(
                    name=f"{spec['name']}-默认载荷",
                    constellation_id=spec["id"],
                    freq_hz=s.DEFAULT_FREQ_HZ,
                    bandwidth_hz=s.DEFAULT_BANDWIDTH_HZ,
                    eirp_dBW=s.DEFAULT_EIRP_DBW,
                    g_r_dbi=s.DEFAULT_G_R_DBI,
                    t_s_k=s.DEFAULT_T_S_K,
                    l_atm_db=s.DEFAULT_L_ATM_DB,
                    l_pol_db=s.DEFAULT_L_POL_DB,
                    l_point_db=s.DEFAULT_L_POINT_DB,
                )
            )
        db.commit()
        logger.info("种子数据写入完成。")
    finally:
        db.close()
