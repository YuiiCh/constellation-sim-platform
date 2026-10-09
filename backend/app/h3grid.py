"""H3 地面区域网格生成。给定经纬度包围盒与分辨率，返回 H3 单元及其边界。"""
from __future__ import annotations

import h3

from .orbital import geodetic_to_ecef


def build_region_polygon(box: list[float]):
    """box = [lat_min, lon_min, lat_max, lon_max] -> h3.LatLngPoly。"""
    lat0, lon0, lat1, lon1 = box
    return h3.LatLngPoly([(lat0, lon0), (lat1, lon0), (lat1, lon1), (lat0, lon1), (lat0, lon0)])


def generate_h3_cells(box: list[float], res: int) -> list[dict]:
    """返回地面区域 H3 单元列表，每项含 h3_index / 中心经纬度 / 边界(经纬度环) / ECEF 向量。"""
    poly = build_region_polygon(box)
    cells = list(h3.polygon_to_cells(poly, res))
    out: list[dict] = []
    for c in cells:
        lat, lon = h3.cell_to_latlng(c)
        bnd = h3.cell_to_boundary(c)  # 顶点 (lat, lon)
        gx, gy, gz = geodetic_to_ecef(lat, lon, 0.0)
        out.append(
            {
                "h3_index": c,
                "lat": lat,
                "lon": lon,
                "boundary": [[float(la), float(lo)] for la, lo in bnd],
                "ecef": (gx, gy, gz),
                "ecef_unit": (gx, gy, gz),  # 地面点高度为 0，单位向量即 ECEF 方向
            }
        )
    return out
