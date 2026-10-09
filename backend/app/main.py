"""FastAPI 主应用：星座/卫星/壳层 API、仿真任务 CRUD、覆盖结果、celestrak/space-track、静态托管。"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select

from .celestrak import fetch_omm_csv
from .config import Settings
from .constellations import generate_walker
from .database import SessionLocal, init_db
from .models import (
    Constellation,
    ConstellationSatellite,
    CoverageSample,
    Satellite,
    Shell,
    SimulationResult,
    SimulationTask,
)
from .schemas import (
    ConfigOut,
    ConstellationOut,
    CoverageSampleOut,
    FetchResult,
    SatelliteDetailOut,
    SatelliteOut,
    ShellOut,
    SimulationCreate,
    SimulationDetailOut,
    SimulationOut,
    SpaceTrackQuery,
    SpaceTrackResult,
)
from .seed import seed_database
from .spacetrack import query_historical
from .taskrunner import enqueue_simulation

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("main")

settings = Settings()
app = FastAPI(title="星座仿真平台", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIST = os.path.join(settings.BASE_DIR, "..", "frontend", "dist")


# ---------------- 启动钩子 ----------------
@app.on_event("startup")
def on_startup():
    init_db()
    seed_database()
    if settings.CELESTRAK_ENABLED:
        threading.Thread(target=_celestrak_fetcher, daemon=True).start()
    logger.info("后端启动完成。前端构建目录: %s (存在=%s)", FRONTEND_DIST, os.path.isdir(FRONTEND_DIST))


def _celestrak_fetcher():
    """持续拉取 celestrak（可达时）并持久化；不可达则静默跳过。"""
    while True:
        try:
            for group in settings.CELESTRAK_GROUPS:
                try:
                    rows, msg, ok = fetch_omm_csv(group)
                    if ok:
                        # 此处仅记录，真实 upsert 由数据管线决定；默认合成数据已覆盖展示
                        logger.info("celestrak %s: %s (%d 条)", group, msg, len(rows))
                except Exception as e:  # noqa: BLE001
                    logger.warning("celestrak 拉取跳过 %s: %s", group, e)
        except Exception:  # noqa: BLE001
            pass
        time.sleep(settings.CELESTRAK_FETCH_INTERVAL)


# ---------------- 配置 ----------------
@app.get("/api/config", response_model=ConfigOut)
def get_config():
    tzs = [f"UTC{sign}{abs(h):02d}:00" for h in range(-12, 15) for sign in ("+" if h >= 0 else "-")]
    tzs = sorted(set(tzs))
    return ConfigOut(
        timeline_rates=settings.TIMELINE_RATES,
        max_fps_options=settings.MAX_FPS,
        default_sample_interval_s=settings.DEFAULT_SAMPLE_INTERVAL_S,
        default_duration_h=settings.DEFAULT_DURATION_H,
        default_el_min_deg=settings.DEFAULT_EL_MIN_DEG,
        default_c_min_dbm=settings.DEFAULT_C_MIN_DBM,
        default_h3_res=settings.DEFAULT_H3_RES,
        default_region=settings.DEFAULT_REGION,
        default_freq_hz=settings.DEFAULT_FREQ_HZ,
        default_bandwidth_hz=settings.DEFAULT_BANDWIDTH_HZ,
        default_eirp_dBW=settings.DEFAULT_EIRP_DBW,
        default_g_r_dbi=settings.DEFAULT_G_R_DBI,
        default_t_s_k=settings.DEFAULT_T_S_K,
        default_l_atm_db=settings.DEFAULT_L_ATM_DB,
        default_l_pol_db=settings.DEFAULT_L_POL_DB,
        default_l_point_db=settings.DEFAULT_L_POINT_DB,
        celestrak_enabled=settings.CELESTRAK_ENABLED,
        celestrak_fetch_interval=settings.CELESTRAK_FETCH_INTERVAL,
        timezones=tzs,
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


# ---------------- 星座 / 卫星 / 壳层 ----------------
@app.get("/api/constellations", response_model=list[ConstellationOut])
def list_constellations():
    db = SessionLocal()
    try:
        out = []
        for c in db.execute(select(Constellation)).scalars().all():
            sc = db.scalar(
                select(func.count()).select_from(Shell).where(Shell.constellation_id == c.id)
            )
            satc = db.scalar(
                select(func.count()).select_from(ConstellationSatellite).where(
                    ConstellationSatellite.constellation_id == c.id
                )
            )
            out.append(
                ConstellationOut(
                    id=c.id, name=c.name, ctype=c.ctype, description=c.description,
                    celestrak_group=c.celestrak_group, source=c.source,
                    shell_count=int(sc or 0), satellite_count=int(satc or 0),
                )
            )
        return out
    finally:
        db.close()


@app.get("/api/constellations/{cid}/shells", response_model=list[ShellOut])
def list_shells(cid: str):
    db = SessionLocal()
    try:
        rows = db.execute(select(Shell).where(Shell.constellation_id == cid)).scalars().all()
        return [ShellOut(**_row_to_dict(s)) for s in rows]
    finally:
        db.close()


@app.get("/api/constellations/{cid}/satellites", response_model=list[SatelliteOut])
def list_satellites(
    cid: str,
    only_default: bool = Query(True),
    shell_ids: str | None = Query(None),
):
    db = SessionLocal()
    try:
        q = select(Satellite).where(Satellite.constellation_id == cid)
        if shell_ids:
            sids = [int(x) for x in shell_ids.split(",") if x.strip()]
            nids = db.execute(
                select(ConstellationSatellite.norad_id).where(
                    ConstellationSatellite.constellation_id == cid,
                    ConstellationSatellite.shell_id.in_(sids),
                )
            ).scalars().all()
            q = q.where(Satellite.norad_id.in_(nids))
        elif only_default:
            shells = db.execute(select(Shell).where(Shell.constellation_id == cid)).scalars().all()
            sids = [s.id for s in shells if s.is_default]
            nids = db.execute(
                select(ConstellationSatellite.norad_id).where(
                    ConstellationSatellite.constellation_id == cid,
                    ConstellationSatellite.shell_id.in_(sids),
                )
            ).scalars().all()
            q = q.where(Satellite.norad_id.in_(nids))
        rows = db.execute(q).scalars().all()
        return [SatelliteOut(**_row_to_dict(s)) for s in rows]
    finally:
        db.close()


@app.get("/api/satellites/{norad_id}", response_model=SatelliteDetailOut)
def get_satellite(norad_id: int):
    db = SessionLocal()
    try:
        s = db.get(Satellite, norad_id)
        if not s:
            raise HTTPException(404, "卫星不存在")
        shells = db.execute(
            select(Shell.name).join(ConstellationSatellite, Shell.id == ConstellationSatellite.shell_id).where(
                ConstellationSatellite.norad_id == norad_id
            )
        ).scalars().all()
        d = _row_to_dict(s)
        d["shells"] = list(shells)
        return SatelliteDetailOut(**d)
    finally:
        db.close()


@app.get("/api/constellations/{cid}/propagate")
def propagate_constellation(cid: str, t: str, only_default: bool = True):
    """返回指定时刻星座内卫星的 ECI/ECEF 与子点位置（前端 Web Worker 亦可本地复算）。"""
    from .orbital import propagate_subpoints

    db = SessionLocal()
    try:
        rows = list_satellites(cid, only_default=only_default, shell_ids=None)
        sats = [_sat_from_out(s) for s in rows]
        dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        res = propagate_subpoints([_sat_to_elem(s) for s in sats], [dt])
        out = []
        for i, s in enumerate(sats):
            out.append(
                {
                    "norad_id": s["norad_id"],
                    "lat": float(res["lat"][i, 0]),
                    "lon": float(res["lon"][i, 0]),
                    "alt": float(res["alt"][i, 0]),
                    "x": float(res["x"][i, 0]),
                    "y": float(res["y"][i, 0]),
                    "z": float(res["z"][i, 0]),
                }
            )
        return {"time": dt.isoformat(), "satellites": out}
    finally:
        db.close()


# ---------------- 仿真任务 CRUD ----------------
@app.post("/api/simulations", response_model=SimulationOut)
def create_simulation(req: SimulationCreate):
    db = SessionLocal()
    try:
        cons = db.get(Constellation, req.constellation_id)
        if not cons:
            raise HTTPException(404, "星座不存在")
        params = {
            "selection": {
                "selected_norad_ids": req.selected_norad_ids,
                "selected_shell_ids": req.selected_shell_ids,
                "use_default_shells": req.use_default_shells,
            },
            "start_utc": req.start_utc,
            "duration_h": req.duration_h,
            "sample_interval_s": req.sample_interval_s,
            "h3_res": req.h3_res,
            "region": req.region,
            "coverage_params": req.params,
            "seed": 42,
        }
        task = SimulationTask(
            name=req.name,
            constellation_id=req.constellation_id,
            rule_type=req.rule_type,
            status="pending",
            progress=0.0,
            params_json=json.dumps(params, ensure_ascii=False),
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        out = _task_to_out(task)
        enqueue_simulation(task.id)
        return out
    finally:
        db.close()


@app.get("/api/simulations", response_model=list[SimulationOut])
def list_simulations():
    db = SessionLocal()
    try:
        rows = db.execute(select(SimulationTask).order_by(SimulationTask.id.desc())).scalars().all()
        return [_task_to_out(t) for t in rows]
    finally:
        db.close()


@app.get("/api/simulations/{tid}", response_model=SimulationDetailOut)
def get_simulation(tid: int):
    db = SessionLocal()
    try:
        t = db.get(SimulationTask, tid)
        if not t:
            raise HTTPException(404, "任务不存在")
        summary = None
        res = db.execute(select(SimulationResult).where(SimulationResult.task_id == tid)).scalar_one_or_none()
        if res:
            summary = json.loads(res.summary_json)
        out = _task_to_out(t)
        return SimulationDetailOut(**out.model_dump(), params=json.loads(t.params_json or "{}"), summary=summary)
    finally:
        db.close()


@app.delete("/api/simulations/{tid}", response_model=SimulationOut)
def delete_simulation(tid: int):
    db = SessionLocal()
    try:
        t = db.get(SimulationTask, tid)
        if not t:
            raise HTTPException(404, "任务不存在")
        db.execute(CoverageSample.__table__.delete().where(CoverageSample.task_id == tid))
        db.execute(SimulationResult.__table__.delete().where(SimulationResult.task_id == tid))
        db.delete(t)
        db.commit()
        return _task_to_out(t)
    finally:
        db.close()


@app.get("/api/simulations/{tid}/summary")
def get_summary(tid: int):
    db = SessionLocal()
    try:
        res = db.execute(select(SimulationResult).where(SimulationResult.task_id == tid)).scalar_one_or_none()
        if not res:
            raise HTTPException(404, "结果未生成")
        return json.loads(res.summary_json)
    finally:
        db.close()


@app.get("/api/simulations/{tid}/frame/{time_step}", response_model=list[CoverageSampleOut])
def get_frame(tid: int, time_step: int):
    db = SessionLocal()
    try:
        rows = db.execute(
            select(CoverageSample).where(CoverageSample.task_id == tid, CoverageSample.time_step == time_step)
        ).scalars().all()
        return [
            CoverageSampleOut(
                time_step=r.time_step, timestamp_utc=r.timestamp_utc, h3_index=r.h3_index,
                lat=r.lat, lon=r.lon, covered_simple=r.covered_simple, covered_complex=r.covered_complex,
                covering_norad_ids=json.loads(r.covering_norad_ids or "[]"),
                max_elevation_deg=r.max_elevation_deg, max_c_dBm=r.max_c_dBm, distance_km=r.distance_km,
            )
            for r in rows
        ]
    finally:
        db.close()


@app.get("/api/simulations/{tid}/frames")
def get_frame_steps(tid: int):
    """返回该任务所有已存帧的 time_step 列表与对应 UTC 时间。"""
    db = SessionLocal()
    try:
        rows = db.execute(
            select(CoverageSample.time_step, CoverageSample.timestamp_utc)
            .where(CoverageSample.task_id == tid)
            .distinct()
            .order_by(CoverageSample.time_step)
        ).all()
        steps = []
        for ts, iso in rows:
            if ts not in [x["time_step"] for x in steps]:
                steps.append({"time_step": ts, "timestamp_utc": iso})
        return steps
    finally:
        db.close()


# ---------------- 管理 / 外部数据源 ----------------
@app.post("/api/admin/fetch/celestrak", response_model=FetchResult)
def admin_fetch_celestrak():
    total = 0
    last_msg = "未拉取"
    ok = False
    for group in settings.CELESTRAK_GROUPS:
        try:
            rows, msg, gok = fetch_omm_csv(group)
            last_msg = msg
            if gok:
                ok = True
                total += len(rows)
        except Exception as e:  # noqa: BLE001
            last_msg = str(e)
    return FetchResult(ok=ok, message=last_msg, fetched=total)


@app.post("/api/spacetrack/query", response_model=SpaceTrackResult)
def spacetrack_query(q: SpaceTrackQuery):
    r = query_historical(q.norad_id, q.epoch_start, q.epoch_end, q.identity, q.password)
    return SpaceTrackResult(
        ok=r["ok"], message=r["message"], count=r["count"],
        rate_limited=r["rate_limited"], needs_credentials=r["needs_credentials"],
    )


@app.post("/api/constellations/{cid}/regenerate")
def regenerate_constellation(cid: str, body: dict):
    """仅合成星座：依据 Walker 参数重新生成卫星（高级设置弹窗调用）。"""
    db = SessionLocal()
    try:
        cons = db.get(Constellation, cid)
        if not cons:
            raise HTTPException(404, "星座不存在")
        if cons.ctype != "composite":
            return {"ok": False, "message": "仅合成星座支持参数重生成", "satellites": 0}
        w = body.get("walker", {})
        nids = db.execute(
            select(ConstellationSatellite.norad_id).where(ConstellationSatellite.constellation_id == cid)
        ).scalars().all()
        if nids:
            db.execute(Satellite.__table__.delete().where(Satellite.norad_id.in_(nids)))
        db.execute(ConstellationSatellite.__table__.delete().where(ConstellationSatellite.constellation_id == cid))
        db.execute(Shell.__table__.delete().where(Shell.constellation_id == cid))

        epoch = datetime.now(timezone.utc)
        max_id = db.execute(select(func.max(Satellite.norad_id))).scalar()
        id_counter = [max(max_id or 900000, 900000) + 1]
        total = int(w.get("total", 300))
        planes = int(w.get("planes", 10))
        per_plane = int(w.get("per_plane", 30))
        alt = float(w.get("alt_km", 1000))
        inc = float(w.get("inc_deg", 55))
        pattern = w.get("pattern", "delta")
        pf = float(w.get("phase_factor", 1))

        shell = Shell(
            constellation_id=cid, name=f"{cid}-main", kind="stable",
            altitude_km=alt, inclination_deg=inc, count=total, is_default=True,
        )
        db.add(shell)
        db.flush()
        sats = generate_walker(
            total, planes, per_plane, alt, inc, pattern=pattern, phase_factor=pf,
            epoch=epoch, prefix=cid[:3].upper(), id_counter=id_counter,
        )
        for sat in sats:
            db.add(
                Satellite(
                    norad_id=sat["norad_id"], name=sat["name"], epoch=sat["epoch"],
                    a_km=sat["a_km"], ecc=sat.get("ecc", 0.0), inc_deg=sat["inc_deg"],
                    raan_deg=sat["raan_deg"], argp_deg=sat["argp_deg"], ma_deg=sat["ma_deg"],
                    mean_motion=sat.get("mean_motion"), source="walker-composite",
                    constellation_id=cid,
                )
            )
            db.add(ConstellationSatellite(constellation_id=cid, norad_id=sat["norad_id"], shell_id=shell.id))
        db.commit()
        return {"ok": True, "message": f"已重生成 {len(sats)} 颗卫星", "satellites": len(sats)}
    finally:
        db.close()


# ---------------- 静态托管（生产构建） ----------------
if os.path.isdir(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="static")


# ---------------- 工具 ----------------
def _row_to_dict(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def _task_to_out(t: SimulationTask) -> SimulationOut:
    timings = json.loads(t.stage_timings_json) if t.stage_timings_json else None
    return SimulationOut(
        id=t.id, name=t.name, constellation_id=t.constellation_id, rule_type=t.rule_type,
        status=t.status, progress=t.progress, error=t.error, stage_timings=timings,
        created_at=t.created_at, started_at=t.started_at, finished_at=t.finished_at,
    )


def _sat_to_elem(s: Satellite) -> dict:
    return {
        "norad_id": s.norad_id, "name": s.name, "epoch": s.epoch, "a_km": s.a_km,
        "ecc": s.ecc, "inc_deg": s.inc_deg, "raan_deg": s.raan_deg,
        "argp_deg": s.argp_deg, "ma_deg": s.ma_deg, "mean_motion": s.mean_motion,
    }


def _sat_from_out(s: SatelliteOut) -> dict:
    d = s.model_dump()
    return {
        "norad_id": d["norad_id"], "name": d["name"], "epoch": d["epoch"], "a_km": d["a_km"],
        "ecc": d["ecc"], "inc_deg": d["inc_deg"], "raan_deg": d["raan_deg"],
        "argp_deg": d["argp_deg"], "ma_deg": d["ma_deg"], "mean_motion": d["mean_motion"],
    }
