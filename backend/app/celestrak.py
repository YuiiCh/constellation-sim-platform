"""celestrak 客户端：拉取 OMM/CSV 并解析为轨道元素。网络不可达时优雅降级。"""
from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone

import httpx

from .config import Settings
from .orbital import a_to_mean_motion

logger = logging.getLogger("celestrak")

BASE_URL = "https://celestrak.org/NORAD/elements/gp.php"


def fetch_omm_csv(group: str, timeout: int | None = None) -> tuple[list[dict], str, bool]:
    """拉取指定 celestrak group 的 OMM CSV。返回 (rows, message, ok)。"""
    s = Settings()
    timeout = timeout or s.CELESTRAK_TIMEOUT
    url = f"{BASE_URL}?GROUP={group}&FORMAT=csv"
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url)
        if resp.status_code != 200:
            return [], f"celestrak 返回 HTTP {resp.status_code}", False
        return _parse_omm_csv(resp.text), f"成功拉取 group={group}", True
    except Exception as exc:  # 网络不可达/超时等
        logger.warning("celestrak 拉取失败 group=%s: %s", group, exc)
        return [], f"celestrak 不可达（{type(exc).__name__}），已使用合成数据兜底", False


def _parse_omm_csv(text: str) -> list[dict]:
    """解析 OMM CSV，提取核心轨道字段。"""
    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict] = []
    for r in reader:
        try:
            mm = float(r.get("MEAN_MOTION", 0) or 0)
            if mm <= 0:
                continue
            a_km = a_to_mean_motion(mm)
            norad = int(r.get("NORAD_CAT_ID") or r.get("OBJECT_ID", "").replace(" ", ""))
            rows.append(
                {
                    "norad_id": norad,
                    "name": r.get("OBJECT_NAME", f"SAT-{norad}"),
                    "object_id": r.get("OBJECT_ID"),
                    "epoch": _normalize_epoch(r.get("EPOCH", "")),
                    "a_km": a_km,
                    "ecc": float(r.get("ECCENTRICITY", 0) or 0),
                    "inc_deg": float(r.get("INCLINATION", 0) or 0),
                    "raan_deg": float(r.get("RA_OF_ASC_NODE", 0) or 0),
                    "argp_deg": float(r.get("ARG_OF_PERICENTER", 0) or 0),
                    "ma_deg": float(r.get("MEAN_ANOMALY", 0) or 0),
                    "mean_motion": mm,
                    "source": "celestrak",
                }
            )
        except (ValueError, TypeError):
            continue
    return rows


def _normalize_epoch(epoch: str) -> str:
    """celestrak EPOCH 形如 '2024-01-01 00:00:00' -> ISO8601 UTC。"""
    try:
        dt = datetime.strptime(epoch, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()
