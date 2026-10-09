"""space-track 客户端：按需查询历史星历，凭据缺失/限流时给出明确提示，不崩溃。"""
from __future__ import annotations

import csv
import io
import logging

import httpx

from .orbital import a_to_mean_motion

logger = logging.getLogger("spacetrack")

LOGIN_URL = "https://www.space-track.org/ajaxauth/login"
BASE = "https://www.space-track.org/basicspacedata/query"


def query_historical(
    norad_id: int,
    epoch_start: str | None,
    epoch_end: str | None,
    identity: str,
    password: str,
) -> dict:
    """查询历史星历。

    返回 dict: {ok, message, count, rate_limited, needs_credentials, rows}
    rows 为轨道元素列表（与 celestrak 解析结果同结构）。
    """
    if not identity or not password:
        return {
            "ok": False,
            "message": "缺少 space-track 凭据，无法查询历史星历。请在弹窗中填写用户名与密码。",
            "count": 0,
            "rate_limited": False,
            "needs_credentials": True,
            "rows": [],
        }
    try:
        with httpx.Client(timeout=25, follow_redirects=True) as c:
            r = c.post(LOGIN_URL, data={"identity": identity, "password": password})
            if r.status_code != 200 or ("failed" in r.text.lower()) or ("error" in r.text.lower()):
                return {
                    "ok": False,
                    "message": "space-track 认证失败，请检查用户名/密码。",
                    "count": 0,
                    "rate_limited": False,
                    "needs_credentials": False,
                    "rows": [],
                }
            es = epoch_start or "2000-01-01"
            ee = epoch_end or "2025-12-31"
            url = f"{BASE}/class/gp_history/NORAD_CAT_ID/{norad_id}/EPOCH/{es}--{ee}/format/csv"
            r2 = c.get(url)
            if r2.status_code == 429:
                return {
                    "ok": False,
                    "message": "space-track 速率受限（建议 <30 请求/分钟，<300 请求/小时），请稍后再试。",
                    "count": 0,
                    "rate_limited": True,
                    "needs_credentials": False,
                    "rows": [],
                }
            if r2.status_code != 200:
                return {
                    "ok": False,
                    "message": f"space-track 查询失败（HTTP {r2.status_code}）。",
                    "count": 0,
                    "rate_limited": False,
                    "needs_credentials": False,
                    "rows": [],
                }
            rows = _parse_csv(r2.text)
            return {
                "ok": True,
                "message": f"成功查询 {len(rows)} 条历史星历。",
                "count": len(rows),
                "rate_limited": False,
                "needs_credentials": False,
                "rows": rows,
            }
    except Exception as exc:  # 网络不可达等
        logger.warning("space-track 查询异常: %s", exc)
        return {
            "ok": False,
            "message": f"space-track 不可达（{type(exc).__name__}）。请检查网络后重试。",
            "count": 0,
            "rate_limited": False,
            "needs_credentials": False,
            "rows": [],
        }


def _parse_csv(text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    out = []
    for r in reader:
        try:
            mm = float(r.get("MEAN_MOTION", 0) or 0)
            if mm <= 0:
                continue
            out.append(
                {
                    "norad_id": int(r.get("NORAD_CAT_ID", 0)),
                    "name": r.get("OBJECT_NAME", ""),
                    "epoch": r.get("EPOCH", ""),
                    "a_km": a_to_mean_motion(mm),
                    "ecc": float(r.get("ECCENTRICITY", 0) or 0),
                    "inc_deg": float(r.get("INCLINATION", 0) or 0),
                    "raan_deg": float(r.get("RA_OF_ASC_NODE", 0) or 0),
                    "argp_deg": float(r.get("ARG_OF_PERICENTER", 0) or 0),
                    "ma_deg": float(r.get("MEAN_ANOMALY", 0) or 0),
                    "mean_motion": mm,
                }
            )
        except (ValueError, TypeError):
            continue
    return out
