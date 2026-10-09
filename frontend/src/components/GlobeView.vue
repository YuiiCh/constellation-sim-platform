<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import * as Cesium from 'cesium'
import { useStore } from '@/store'
import type { CoverageSample } from '@/types'

const store = useStore()
const emit = defineEmits<{ (e: 'cell-click', h3: string): void }>()

const container = ref<HTMLDivElement | null>(null)
let viewer: Cesium.Viewer
let scene: Cesium.Scene
let pointPrim: Cesium.PointPrimitiveCollection
let worker: Worker
const satPointMap = new Map<number, Cesium.PointPrimitive>()
const satPositions = new Map<number, { x: number; y: number; z: number; lat: number; lon: number; alt: number }>()
const orbitEntities = new Map<number, Cesium.Entity>()
let coverageEntities: Cesium.Entity[] = []
let connectionEntities: Cesium.Entity[] = []
const cellData = new Map<string, CoverageSample>()
let lastPost = 0

const COLOR_DEFAULT = Cesium.Color.fromCssColorString('#9fd0ff')
const COLOR_HI = Cesium.Color.fromCssColorString('#ffb347')

function initViewer() {
  viewer = new Cesium.Viewer(container.value!, {
    baseLayer: false,
    baseLayerPicker: false,
    geocoder: false,
    homeButton: false,
    sceneModePicker: false,
    navigationHelpButton: false,
    animation: false,
    timeline: false,
    fullscreenButton: false,
    infoBox: false,
    selectionIndicator: false,
    shadows: false,
  })
  scene = viewer.scene
  viewer.imageryLayers.removeAll()
  const globe = scene.globe
  globe.baseColor = Cesium.Color.fromCssColorString('#071428')
  globe.showGroundAtmosphere = true
  globe.atmosphereBrightnessShift = 0.15
  scene.skyAtmosphere.show = true
  scene.backgroundColor = Cesium.Color.fromCssColorString('#03060c')
  scene.fog.enabled = true
  ;(scene as any).skyAtmosphere.hueShift = 0.0
  ;(scene as any).skyAtmosphere.saturationShift = 0.1
  viewer.cesiumWidget.creditContainer.style.display = 'none'

  buildGrid()
  buildRegionBox()
  pointPrim = scene.primitives.add(new Cesium.PointPrimitiveCollection())
  initWorker()

  const handler = new Cesium.ScreenSpaceEventHandler(scene.canvas)
  handler.setInputAction((m: any) => onPick(m.position), Cesium.ScreenSpaceEventType.LEFT_CLICK)

  // 高亮脉冲动画
  scene.postRender.addEventListener(() => {
    const t = performance.now() / 300
    const pulse = 9 + Math.sin(t) * 3.5
    for (const id of store.highlighted) {
      const p = satPointMap.get(id)
      if (p) p.pixelSize = pulse
    }
  })
}

function buildGrid() {
  const gridMat = new Cesium.PolylineColorMaterialProperty(
    Cesium.Color.fromCssColorString('#ffffff').withAlpha(0.12),
  )
  for (let lon = -180; lon <= 180; lon += 20) {
    const pts: Cesium.Cartesian3[] = []
    for (let lat = -85; lat <= 85; lat += 2) pts.push(Cesium.Cartesian3.fromDegrees(lon, lat, 3000))
    viewer.entities.add({ polyline: { positions: pts, width: 1, material: gridMat } })
  }
  for (let lat = -80; lat <= 80; lat += 20) {
    const pts: Cesium.Cartesian3[] = []
    for (let lon = -180; lon <= 180; lon += 2) pts.push(Cesium.Cartesian3.fromDegrees(lon, lat, 3000))
    viewer.entities.add({ polyline: { positions: pts, width: 1, material: gridMat } })
  }
}

function buildRegionBox() {
  const r = store.config?.default_region || [18, 73, 54, 135]
  const [lat0, lon0, lat1, lon1] = r
  const pts = [
    Cesium.Cartesian3.fromDegrees(lon0, lat0, 3000),
    Cesium.Cartesian3.fromDegrees(lon1, lat0, 3000),
    Cesium.Cartesian3.fromDegrees(lon1, lat1, 3000),
    Cesium.Cartesian3.fromDegrees(lon0, lat1, 3000),
    Cesium.Cartesian3.fromDegrees(lon0, lat0, 3000),
  ]
  viewer.entities.add({
    polyline: {
      positions: pts,
      width: 2,
      material: Cesium.Color.fromCssColorString('#bfe3ff').withAlpha(0.6),
    },
  })
}

function initWorker() {
  try {
    worker = new Worker(new URL('../workers/orbit.worker.ts', import.meta.url), { type: 'module' })
    worker.onmessage = (ev: MessageEvent) => {
      const msg = ev.data
      if (msg.type === 'positions') updateSatellitePositions(msg.positions)
      else if (msg.type === 'orbit') updateOrbit(msg.norad_id, msg.points)
    }
    worker.onerror = (e) => console.warn('轨道 Worker 错误（已降级）', e.message)
  } catch (e) {
    console.warn('Web Worker 初始化失败，卫星位置更新降级', e)
    worker = undefined as any
  }
}

function buildSatellitePoints() {
  pointPrim.removeAll()
  satPointMap.clear()
  satPositions.clear()
  for (const s of store.satElements) {
    const p = pointPrim.add({
      position: Cesium.Cartesian3.fromDegrees(0, 0, 700000),
      pixelSize: 5,
      color: COLOR_DEFAULT,
      outlineColor: Cesium.Color.fromCssColorString('#0a1830'),
      outlineWidth: 1,
    })
    p.id = s.norad_id
    satPointMap.set(s.norad_id, p)
  }
  postPositions()
  requestOrbits()
}

function postPositions() {
  if (!worker) return
  worker.postMessage({ type: 'positions', timeUnix: store.currentTimeUnix })
  lastPost = performance.now()
}

function updateSatellitePositions(positions: any[]) {
  for (const pos of positions) {
    const p = satPointMap.get(pos.norad_id)
    if (!p) continue
    p.position = new Cesium.Cartesian3(pos.x * 1000, pos.y * 1000, pos.z * 1000)
    p.color = store.highlighted.includes(pos.norad_id) ? COLOR_HI : COLOR_DEFAULT
    satPositions.set(pos.norad_id, pos)
  }
}

function onPick(pos: Cesium.Cartesian2) {
  const picked = scene.pick(pos)
  if (!picked) return
  const norad = (picked as any).primitive?.id ?? (picked as any).id
  if (typeof norad === 'number') {
    store.toggleHighlight(norad)
    return
  }
  if (typeof norad === 'string' && norad.startsWith('cell:')) {
    emit('cell-click', norad.slice(5))
  }
}

// ---- 轨道线 ----
function requestOrbits() {
  if (!store.showOrbits || !worker) return
  for (const id of store.highlighted) {
    worker.postMessage({ type: 'orbit', norad_id: id, timeUnix: store.currentTimeUnix })
  }
}
function updateOrbit(norad: number, points: [number, number, number][]) {
  const cart = points.map((p) => new Cesium.Cartesian3(p[0] * 1000, p[1] * 1000, p[2] * 1000))
  let ent = orbitEntities.get(norad)
  if (!ent) {
    ent = viewer.entities.add({
      polyline: {
        positions: cart,
        width: 2,
        material: Cesium.Color.fromCssColorString('#ffb347').withAlpha(0.85),
      },
    })
    orbitEntities.set(norad, ent)
  } else {
    ;(ent.polyline as any).positions = cart
  }
}
function clearOrbit(norad: number) {
  const ent = orbitEntities.get(norad)
  if (ent) {
    viewer.entities.remove(ent)
    orbitEntities.delete(norad)
  }
}

// ---- 覆盖渲染 ----
let boundaryMap = new Map<string, [number, number][]>()
function clearCoverage() {
  for (const e of coverageEntities) viewer.entities.remove(e)
  coverageEntities = []
  for (const e of connectionEntities) viewer.entities.remove(e)
  connectionEntities = []
  cellData.clear()
}

function renderCoverage() {
  clearCoverage()
  const samples = store.frameSamples
  let lines = 0
  for (const s of samples) {
    const covered =
      store.summary?.rule_type === 'complex_power' ? s.covered_complex : s.covered_simple
    const color = covered
      ? Cesium.Color.fromCssColorString('#46e0a8').withAlpha(0.34)
      : Cesium.Color.fromCssColorString('#34507a').withAlpha(0.12)
    const b = boundaryMap.get(s.h3_index)
    let ent: Cesium.Entity
    if (b && b.length >= 3) {
      const flat: number[] = []
      for (const [la, lo] of b) flat.push(lo, la)
      ent = viewer.entities.add({
        polygon: {
          hierarchy: Cesium.Cartesian3.fromDegreesArray(flat),
          material: color,
          height: 0,
        },
      })
    } else {
      ent = viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(s.lon, s.lat, 0),
        ellipse: { semiMajorAxis: 26000, semiMinorAxis: 26000, material: color, height: 0 },
      })
    }
    ent.id = 'cell:' + s.h3_index
    cellData.set(s.h3_index, s)
    coverageEntities.push(ent)

    if (covered && lines < 70 && s.covering_norad_ids.length) {
      const sp = satPositions.get(s.covering_norad_ids[0])
      if (sp) {
        const line = viewer.entities.add({
          polyline: {
            positions: [
              Cesium.Cartesian3.fromDegrees(s.lon, s.lat, 0),
              Cesium.Cartesian3.fromDegrees(sp.lon, sp.lat, sp.alt * 1000),
            ],
            width: 1,
            material: Cesium.Color.fromCssColorString('#7fe0c0').withAlpha(0.35),
          },
        })
        connectionEntities.push(line)
        lines++
      }
    }
  }
}

function flyToChina() {
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(105, 35, 12000000),
    duration: 1.5,
  })
}

onMounted(() => {
  initViewer()
  buildSatellitePoints()
  flyToChina()
})

onBeforeUnmount(() => {
  worker?.terminate()
  viewer?.destroy()
})

watch(
  () => store.satElements,
  () => buildSatellitePoints(),
)
watch(
  () => store.currentTimeUnix,
  () => {
    if (performance.now() - lastPost > 40) postPositions()
  },
)
watch(
  () => store.highlighted.slice(),
  (now, before) => {
    for (const id of before || []) if (!now.includes(id)) clearOrbit(id)
    for (const id of now) {
      const p = satPointMap.get(id)
      if (p) p.color = COLOR_HI
    }
    for (const id of before || []) {
      if (!now.includes(id)) {
        const p = satPointMap.get(id)
        if (p) p.color = COLOR_DEFAULT
      }
    }
    requestOrbits()
  },
)
watch(
  () => store.showOrbits,
  (v) => {
    if (!v) for (const id of [...orbitEntities.keys()]) clearOrbit(id)
    else requestOrbits()
  },
)
watch(
  () => store.frameSamples,
  () => {
    if (store.summary) renderCoverage()
  },
  { deep: false },
)
watch(
  () => store.summary,
  (s) => {
    boundaryMap = new Map()
    if (s?.cell_aggregates) {
      for (const c of s.cell_aggregates) boundaryMap.set(c.h3_index, c.boundary)
    }
    if (store.frameSamples.length) renderCoverage()
  },
  { deep: false },
)

defineExpose({ requestOrbits, postPositions })
</script>

<template>
  <div ref="container" class="globe"></div>
</template>

<style scoped>
.globe {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

/* 隐藏 Cesium 错误面板，避免在无 GPU 环境下拦截交互 */
:deep(.cesium-widget-errorPanel) {
  display: none !important;
}
</style>
