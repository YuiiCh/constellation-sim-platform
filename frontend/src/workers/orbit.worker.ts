/// <reference lib="webworker" />
// 轨道计算 Web Worker：接收卫星元素与时间，返回位置/轨道线，避免阻塞主线程。
import { propagateAll, orbitPolyline, type SatElem } from './orbital'

let elements: SatElem[] = []
let byId = new Map<number, SatElem>()

self.onmessage = (ev: MessageEvent) => {
  const msg = ev.data
  if (msg.type === 'init') {
    elements = (msg.satellites as SatElem[]).map((s) => ({ ...s }))
    byId = new Map(elements.map((e) => [e.norad_id, e]))
    return
  }
  if (msg.type === 'positions') {
    const t = msg.timeUnix as number
    const positions = propagateAll(elements, t)
    ;(self as unknown as Worker).postMessage({ type: 'positions', timeUnix: t, positions })
    return
  }
  if (msg.type === 'orbit') {
    const el = byId.get(msg.norad_id)
    if (!el) return
    const points = orbitPolyline(el, msg.timeUnix as number, msg.points ?? 128)
    ;(self as unknown as Worker).postMessage({ type: 'orbit', norad_id: msg.norad_id, points })
    return
  }
}
