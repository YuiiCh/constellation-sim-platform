// 轨道传播（TS 版）：二体 + J2 一阶长期项开普勒模型，与后端 orbital.py 对齐。
// 用于在 Web Worker 中计算卫星位置与轨道线，避免阻塞主线程。

export const MU = 398600.4418
export const RE = 6378.137
export const OMEGA_E = 7.2921159e-5
export const J2 = 1.08262668e-3
const DEG = Math.PI / 180

export interface SatElem {
  norad_id: number
  epochUnix: number
  a_km: number
  ecc: number
  inc_deg: number
  raan_deg: number
  argp_deg: number
  ma_deg: number
  n?: number
}

export function julianDate(unix: number): number {
  return 2440587.5 + unix / 86400
}

export function gmstRad(unix: number): number {
  const jd = julianDate(unix)
  const T = (jd - 2451545.0) / 36525.0
  let sec = 67310.54841 + (876600.0 * 3600 + 8640184.812866) * T + 0.093104 * T * T - 6.2e-6 * T * T * T
  sec = ((sec % 86400) + 86400) % 86400
  return (sec / 240.0) * DEG
}

export function meanMotionFromA(a_km: number): number {
  return Math.sqrt(MU / (a_km * a_km * a_km))
}

export interface State {
  x: number
  y: number
  z: number
  lat: number
  lon: number
  alt: number
}

export function propagateOne(el: SatElem, timeUnix: number): State {
  const n = el.n ?? meanMotionFromA(el.a_km)
  const inc = el.inc_deg * DEG
  const delta = timeUnix - el.epochUnix
  const p = el.a_km * (1 - el.ecc * el.ecc)
  const raanDot = -1.5 * n * J2 * Math.pow(RE / p, 2) * Math.cos(inc)
  const argpDot = 0.75 * n * J2 * Math.pow(RE / p, 2) * (4 - 5 * Math.sin(inc) * Math.sin(inc))
  const raan = el.raan_deg * DEG + raanDot * delta
  const argp = el.argp_deg * DEG + argpDot * delta
  let M = el.ma_deg * DEG + n * delta

  // 牛顿迭代解开普勒方程
  let E = M + el.ecc * Math.sin(M)
  for (let i = 0; i < 8; i++) {
    const f = E - el.ecc * Math.sin(E) - M
    const fp = 1 - el.ecc * Math.cos(E)
    E = E - f / fp
  }
  const nu = 2 * Math.atan2(Math.sqrt(1 + el.ecc) * Math.sin(E / 2), Math.sqrt(1 - el.ecc) * Math.cos(E / 2))
  const r = el.a_km * (1 - el.ecc * Math.cos(E))
  const xp = r * Math.cos(nu)
  const yp = r * Math.sin(nu)

  const cosO = Math.cos(raan)
  const sinO = Math.sin(raan)
  const cosi = Math.cos(inc)
  const sini = Math.sin(inc)
  const cosw = Math.cos(argp)
  const sinw = Math.sin(argp)

  const xeci = (cosO * cosw - sinO * sinw * cosi) * xp + (-cosO * sinw - sinO * cosw * cosi) * yp
  const yeci = (sinO * cosw + cosO * sinw * cosi) * xp + (-sinO * sinw + cosO * cosw * cosi) * yp
  const zeci = sinw * sini * xp + cosw * sini * yp

  const theta = gmstRad(el.epochUnix) + OMEGA_E * delta
  const cosT = Math.cos(theta)
  const sinT = Math.sin(theta)
  const x = xeci * cosT + yeci * sinT
  const y = -xeci * sinT + yeci * cosT
  const z = zeci

  const rr = Math.sqrt(x * x + y * y + z * z)
  const lat = Math.asin(z / rr) / DEG
  const lon = Math.atan2(y, x) / DEG
  const alt = rr - RE
  return { x, y, z, lat, lon, alt }
}

export function propagateAll(els: SatElem[], timeUnix: number): Array<State & { norad_id: number }> {
  return els.map((el) => {
    const s = propagateOne(el, timeUnix)
    return { norad_id: el.norad_id, ...s }
  })
}

export function orbitPolyline(el: SatElem, timeUnix: number, n = 128): Array<[number, number, number]> {
  const nRate = el.n ?? meanMotionFromA(el.a_km)
  const period = (2 * Math.PI) / nRate
  const out: Array<[number, number, number]> = []
  for (let k = 0; k <= n; k++) {
    const t = timeUnix + (period * k) / n
    const s = propagateOne(el, t)
    out.push([s.x, s.y, s.z])
  }
  return out
}
