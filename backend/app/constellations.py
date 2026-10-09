"""星座定义与合成（Walker-Delta / Walker-Star）。

由于本沙箱无法直连 celestrak，首发数据以"基于真实星座设计参数的合成轨道根数"填充，
保证平台完全可运行；celestrak 可达时会覆盖为真实星历（见 celestrak.py）。
合成星座（千帆一期/国网一期 规划）按 Walker 参数确定性生成，可复现。
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

from .orbital import RE, a_to_mean_motion

# 合成卫星 NORAD ID 起始（高于真实编号段，避免冲突）
SYNTH_NORAD_START = 900000


def generate_walker(
    total: int,
    planes: int,
    per_plane: int,
    alt_km: float,
    inc_deg: float,
    pattern: str = "delta",
    raan0_deg: float = 0.0,
    phase_factor: float = 1.0,
    epoch: datetime | None = None,
    prefix: str = "SAT",
    id_counter: list[int] | None = None,
) -> list[dict]:
    """生成 Walker 星座卫星轨道根数。

    pattern: 'delta'（Walker-Delta，RAAN 跨 360°）或 'star'（Walker-Star，RAAN 跨 180°）。
    返回每颗卫星的轨道元素 dict（含 norad_id）。
    """
    if epoch is None:
        epoch = datetime.now(timezone.utc)
    if id_counter is None:
        id_counter = [SYNTH_NORAD_START]
    sats: list[dict] = []
    a = alt_km + RE
    mm = a_to_mean_motion(a)
    for u in range(planes):
        raan = raan0_deg + (u * 180.0 / planes if pattern == "star" else u * 360.0 / planes)
        for v in range(per_plane):
            ma = (v * 360.0 / per_plane) + phase_factor * u * 360.0 / total
            norad = id_counter[0]
            id_counter[0] += 1
            sats.append(
                {
                    "norad_id": norad,
                    "name": f"{prefix}-{u:02d}-{v:02d}",
                    "epoch": epoch.isoformat(),
                    "a_km": a,
                    "ecc": 0.0,
                    "inc_deg": inc_deg,
                    "raan_deg": raan % 360.0,
                    "argp_deg": 0.0,
                    "ma_deg": ma % 360.0,
                    "mean_motion": mm,
                }
            )
    return sats


# ---- 星座规格（纯数据，供 seed.py 使用） ----
def get_constellation_specs() -> list[dict]:
    """返回全部星座规格。每颗壳层给出 Walker 生成参数与默认筛选（稳定壳层默认选中）。"""
    specs = []

    # 1) 千帆星座（真实在轨，本环境以合成轨道根数填充）
    qianfan_shells = [
        {"name": "QF-1000-50", "kind": "stable", "alt_km": 1000, "inc_deg": 50,
         "planes": 12, "per_plane": 12, "pattern": "delta", "phase_factor": 1, "is_default": True},
        {"name": "QF-1000-55", "kind": "stable", "alt_km": 1000, "inc_deg": 55,
         "planes": 12, "per_plane": 12, "pattern": "delta", "phase_factor": 1, "is_default": True},
        {"name": "QF-1050-60", "kind": "stable", "alt_km": 1050, "inc_deg": 60,
         "planes": 10, "per_plane": 12, "pattern": "delta", "phase_factor": 1, "is_default": True},
        {"name": "QF-800-85-test", "kind": "temporary", "alt_km": 800, "inc_deg": 85,
         "planes": 2, "per_plane": 6, "pattern": "delta", "phase_factor": 1, "is_default": False},
    ]
    specs.append(
        {
            "id": "qianfan",
            "name": "千帆星座",
            "ctype": "real",
            "description": "千帆星座（G60 星链），多壳层低轨宽带星座。",
            "celestrak_group": "qianfan",
            "source": "synthetic-fallback",
            "prefix": "QF",
            "shells": qianfan_shells,
        }
    )

    # 2) 国网星座（真实在轨，本环境以合成轨道根数填充）
    guowang_shells = [
        {"name": "GW-590-30", "kind": "stable", "alt_km": 590, "inc_deg": 30,
         "planes": 8, "per_plane": 10, "pattern": "delta", "phase_factor": 1, "is_default": True},
        {"name": "GW-600-50", "kind": "stable", "alt_km": 600, "inc_deg": 50,
         "planes": 10, "per_plane": 10, "pattern": "delta", "phase_factor": 1, "is_default": True},
        {"name": "GW-610-60", "kind": "stable", "alt_km": 610, "inc_deg": 60,
         "planes": 10, "per_plane": 10, "pattern": "delta", "phase_factor": 1, "is_default": True},
        {"name": "GW-1145-85", "kind": "stable", "alt_km": 1145, "inc_deg": 85,
         "planes": 6, "per_plane": 10, "pattern": "delta", "phase_factor": 1, "is_default": True},
        {"name": "GW-500-85-test", "kind": "temporary", "alt_km": 500, "inc_deg": 85,
         "planes": 2, "per_plane": 4, "pattern": "delta", "phase_factor": 1, "is_default": False},
    ]
    specs.append(
        {
            "id": "guowang",
            "name": "国网星座",
            "ctype": "real",
            "description": "国网星座（中国星网），多层低轨通信星座。",
            "celestrak_group": "guowang",
            "source": "synthetic-fallback",
            "prefix": "GW",
            "shells": guowang_shells,
        }
    )

    # 3) 千帆一期（规划）—— Walker-Delta 合成
    specs.append(
        {
            "id": "qianfan-phase1",
            "name": "千帆一期（规划）",
            "ctype": "composite",
            "description": "千帆一期规划形态（Walker-Delta 合成）。",
            "celestrak_group": None,
            "source": "walker-composite",
            "prefix": "QF1",
            "walker": {
                "total": 300, "planes": 10, "per_plane": 30, "alt_km": 1000,
                "inc_deg": 55, "pattern": "delta", "phase_factor": 1,
            },
            "shells": [
                {"name": "QF1-main", "kind": "stable", "alt_km": 1000, "inc_deg": 55,
                 "count": 300, "is_default": True},
            ],
        }
    )

    # 4) 国网一期（规划）—— Walker-Star 合成
    specs.append(
        {
            "id": "guowang-phase1",
            "name": "国网一期（规划）",
            "ctype": "composite",
            "description": "国网一期规划形态（Walker-Star 合成）。",
            "celestrak_group": None,
            "source": "walker-composite",
            "prefix": "GW1",
            "walker": {
                "total": 360, "planes": 12, "per_plane": 30, "alt_km": 600,
                "inc_deg": 60, "pattern": "star", "phase_factor": 1,
            },
            "shells": [
                {"name": "GW1-main", "kind": "stable", "alt_km": 600, "inc_deg": 60,
                 "count": 360, "is_default": True},
            ],
        }
    )
    return specs


def build_satellites_for_spec(spec: dict, epoch: datetime, id_counter: list[int]) -> list[dict]:
    """根据规格生成卫星元素列表。"""
    sats: list[dict] = []
    if spec.get("walker"):
        w = spec["walker"]
        sats.extend(
            generate_walker(
                total=w["total"], planes=w["planes"], per_plane=w["per_plane"],
                alt_km=w["alt_km"], inc_deg=w["inc_deg"], pattern=w["pattern"],
                raan0_deg=0.0, phase_factor=w.get("phase_factor", 1), epoch=epoch,
                prefix=spec["prefix"], id_counter=id_counter,
            )
        )
    else:
        for sh in spec["shells"]:
            sats.extend(
                generate_walker(
                    total=sh["planes"] * sh["per_plane"], planes=sh["planes"],
                    per_plane=sh["per_plane"], alt_km=sh["alt_km"], inc_deg=sh["inc_deg"],
                    pattern=sh.get("pattern", "delta"), phase_factor=sh.get("phase_factor", 1),
                    epoch=epoch, prefix=spec["prefix"], id_counter=id_counter,
                )
            )
    return sats
