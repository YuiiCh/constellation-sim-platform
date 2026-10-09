"""仿真任务运行器：后台线程执行覆盖仿真，写库并更新状态/进度/分阶段耗时。"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from .coverage import run_coverage
from .database import SessionLocal
from .models import (
    ConstellationSatellite,
    CoverageSample,
    Satellite,
    Shell,
    SimulationResult,
    SimulationTask,
)

logger = logging.getLogger("taskrunner")

RUNNING: dict[int, Any] = {}


def _sat_to_elem(r: Satellite) -> dict:
    return {
        "norad_id": r.norad_id,
        "name": r.name,
        "epoch": r.epoch,
        "a_km": r.a_km,
        "ecc": r.ecc,
        "inc_deg": r.inc_deg,
        "raan_deg": r.raan_deg,
        "argp_deg": r.argp_deg,
        "ma_deg": r.ma_deg,
        "mean_motion": r.mean_motion,
    }


def build_satellite_elements(db, constellation_id: str, sel: dict) -> list[dict]:
    """根据选择（NORAD ID 列表 / 壳层 / 默认壳层）构造参与仿真的卫星元素。"""
    if sel.get("selected_norad_ids"):
        rows = (
            db.execute(select(Satellite).where(Satellite.norad_id.in_(sel["selected_norad_ids"])))
            .scalars()
            .all()
        )
        return [_sat_to_elem(r) for r in rows]

    shells = db.execute(select(Shell).where(Shell.constellation_id == constellation_id)).scalars().all()
    if sel.get("selected_shell_ids"):
        shell_ids = list(sel["selected_shell_ids"])
    elif sel.get("use_default_shells", True):
        shell_ids = [sh.id for sh in shells if sh.is_default]
    else:
        shell_ids = [sh.id for sh in shells]
    if not shell_ids:
        shell_ids = [sh.id for sh in shells]

    nids = db.execute(
        select(ConstellationSatellite.norad_id).where(
            ConstellationSatellite.constellation_id == constellation_id,
            ConstellationSatellite.shell_id.in_(shell_ids),
        )
    ).scalars().all()
    rows = db.execute(select(Satellite).where(Satellite.norad_id.in_(nids))).scalars().all()
    return [_sat_to_elem(r) for r in rows]


def _default_start_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)


def run_simulation_task(task_id: int) -> None:
    db = SessionLocal()
    try:
        task = db.get(SimulationTask, task_id)
        if task is None:
            return
        task.status = "running"
        task.started_at = datetime.now(timezone.utc)
        db.commit()

        params = json.loads(task.params_json or "{}")
        sel = params.get("selection", {})
        sats = build_satellite_elements(db, task.constellation_id, sel)

        start_utc = params.get("start_utc")
        start_dt = (
            datetime.fromisoformat(start_utc.replace("Z", "+00:00"))
            if start_utc
            else _default_start_utc()
        )
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        duration_h = int(params.get("duration_h", 24))
        interval = int(params.get("sample_interval_s", 15))
        cov_params = dict(params.get("coverage_params", {}))
        if params.get("h3_res"):
            cov_params["h3_res"] = params["h3_res"]
        if params.get("region"):
            cov_params["region"] = params["region"]

        last_commit = 0.0

        def progress(frac: float):
            nonlocal last_commit
            task.progress = round(frac * 100, 1)
            if frac - last_commit >= 0.1:
                db.commit()
                last_commit = frac

        result = run_coverage(
            satellites=sats,
            start_dt=start_dt,
            duration_s=duration_h * 3600,
            sample_interval_s=interval,
            rule_type=task.rule_type,
            params=cov_params,
            seed=params.get("seed"),
            progress_callback=progress,
        )

        # 批量写入覆盖样本
        samples = result["samples"]
        chunk = 4000
        for i in range(0, len(samples), chunk):
            db.bulk_insert_mappings(
                CoverageSample,
                [{**s, "task_id": task.id} for s in samples[i : i + chunk]],
            )
        db.commit()

        db.add(
            SimulationResult(
                task_id=task.id,
                summary_json=json.dumps(result["summary"], ensure_ascii=False),
            )
        )
        task.status = "succeeded"
        task.progress = 100.0
        task.stage_timings_json = json.dumps(result["stage_timings"], ensure_ascii=False)
        task.finished_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("仿真任务 %s 完成：%d 样本。", task_id, len(samples))
    except Exception as exc:  # noqa: BLE001
        logger.exception("仿真任务 %s 失败", task_id)
        try:
            db.rollback()
            task = db.get(SimulationTask, task_id)
            if task:
                task.status = "failed"
                task.error = str(exc)[:500]
                task.finished_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def enqueue_simulation(task_id: int) -> None:
    """启动后台线程执行仿真。"""
    t = __import__("threading").Thread(target=run_simulation_task, args=(task_id,), daemon=True)
    RUNNING[task_id] = t
    t.start()
