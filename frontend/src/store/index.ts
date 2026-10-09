import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/services/api'
import type {
  Config,
  Constellation,
  Shell,
  Satellite,
  SimulationTask,
  SimulationDetail,
  SimulationSummary,
  FrameStep,
  CoverageSample,
} from '@/types'
import type { SatElem } from '@/workers/orbital'
import { nowUtcUnix, tzToOffsetMinutes } from '@/utils/time'

const DEG = Math.PI / 180
function toSatElem(s: Satellite): SatElem {
  const mm = s.mean_motion // rev/day
  const n = mm ? (mm * 2 * Math.PI) / 86400 : undefined
  return {
    norad_id: s.norad_id,
    epochUnix: Date.parse(s.epoch) / 1000,
    a_km: s.a_km,
    ecc: s.ecc,
    inc_deg: s.inc_deg,
    raan_deg: s.raan_deg,
    argp_deg: s.argp_deg,
    ma_deg: s.ma_deg,
    n,
  }
}

export const useStore = defineStore('main', () => {
  // ---- 配置与星座 ----
  const config = ref<Config | null>(null)
  const constellations = ref<Constellation[]>([])
  const selectedCid = ref<string>('')
  const shells = ref<Shell[]>([])
  const selectedShellIds = ref<number[]>([])
  const satellites = ref<Satellite[]>([])
  const satElements = ref<SatElem[]>([])

  // ---- 时间轴 ----
  const currentTimeUnix = ref<number>(nowUtcUnix())
  const isRealtime = ref<boolean>(true)
  const playing = ref<boolean>(true)
  const rate = ref<number>(1)
  const timezone = ref<string>('UTC+00:00')

  // ---- 高亮 / 轨道 ----
  const highlighted = ref<number[]>([])
  const showOrbits = ref<boolean>(true)

  // ---- 仿真任务 ----
  const tasks = ref<SimulationTask[]>([])
  const selectedTaskId = ref<number | null>(null)
  const detail = ref<SimulationDetail | null>(null)
  const summary = ref<SimulationSummary | null>(null)
  const frames = ref<FrameStep[]>([])
  const frameIndex = ref<number>(0)
  const frameSamples = ref<CoverageSample[]>([])
  const creating = ref<boolean>(false)
  const taskError = ref<string | null>(null)

  const selectedConstellation = computed(() =>
    constellations.value.find((c) => c.id === selectedCid.value),
  )
  const selectedSatCount = computed(() => satellites.value.length)
  const runningCount = computed(() => tasks.value.filter((t) => t.status === 'running').length)

  // ---- 初始化 ----
  async function init() {
    config.value = await api.config()
    timezone.value = 'UTC+00:00'
    if (config.value.timeline_rates.includes(rate.value)) {
      // keep default
    }
    const list = await api.constellations()
    constellations.value = list
    if (list.length) await selectConstellation(list[0].id)
    await refreshTasks()
  }

  async function selectConstellation(id: string) {
    selectedCid.value = id
    shells.value = await api.shells(id)
    selectedShellIds.value = shells.value.filter((s) => s.is_default).map((s) => s.id)
    await loadSatellites()
    // 切换星座后清除覆盖结果
    selectedTaskId.value = null
    summary.value = null
    frameSamples.value = []
    frames.value = []
  }

  async function loadSatellites() {
    const useDefault = selectedShellIds.value.length === 0
    const sats = await api.satellites(
      selectedCid.value,
      useDefault,
      useDefault ? undefined : selectedShellIds.value,
    )
    satellites.value = sats
    satElements.value = sats.map(toSatElem)
  }

  function setShellSelection(ids: number[]) {
    selectedShellIds.value = ids
    loadSatellites()
  }

  function toggleShell(id: number) {
    const i = selectedShellIds.value.indexOf(id)
    if (i >= 0) selectedShellIds.value = selectedShellIds.value.filter((x) => x !== id)
    else selectedShellIds.value = [...selectedShellIds.value, id]
    loadSatellites()
  }

  // ---- 时间轴控制 ----
  function setRealtime(on: boolean) {
    isRealtime.value = on
    if (on) {
      currentTimeUnix.value = nowUtcUnix()
    }
  }
  function togglePlay() {
    playing.value = !playing.value
  }
  function setRate(r: number) {
    rate.value = r
  }
  function setTimezone(tz: string) {
    timezone.value = tz
  }
  function setTimeUnix(u: number) {
    currentTimeUnix.value = u
    if (isRealtime.value) isRealtime.value = false
  }
  function advanceTime(dtRealSeconds: number) {
    if (isRealtime.value) {
      currentTimeUnix.value = nowUtcUnix()
    } else if (playing.value) {
      currentTimeUnix.value += dtRealSeconds * rate.value
    }
  }

  // ---- 高亮 ----
  function toggleHighlight(norad: number) {
    const i = highlighted.value.indexOf(norad)
    if (i >= 0) highlighted.value = highlighted.value.filter((x) => x !== norad)
    else highlighted.value = [...highlighted.value, norad]
  }
  function clearHighlight() {
    highlighted.value = []
  }

  // ---- 仿真任务 ----
  async function refreshTasks() {
    tasks.value = await api.simulations()
  }

  async function createSimulation(payload: any) {
    creating.value = true
    taskError.value = null
    try {
      const task = await api.createSimulation(payload)
      await refreshTasks()
      pollTask(task.id)
      return task
    } catch (e: any) {
      taskError.value = e.message
      throw e
    } finally {
      creating.value = false
    }
  }

  let pollTimer: ReturnType<typeof setInterval> | null = null
  function pollTask(id: number) {
    const tick = async () => {
      const t = tasks.value.find((x) => x.id === id)
      if (!t) return
      await refreshTasks()
      const upt = tasks.value.find((x) => x.id === id)
      if (upt && (upt.status === 'succeeded' || upt.status === 'failed')) {
        if (pollTimer) {
          clearInterval(pollTimer)
          pollTimer = null
        }
        if (upt.status === 'succeeded') {
          await selectTaskForResults(id)
        }
      }
    }
    if (pollTimer) clearInterval(pollTimer)
    pollTimer = setInterval(tick, 1500)
    tick()
  }

  async function selectTaskForResults(id: number) {
    selectedTaskId.value = id
    detail.value = await api.simulation(id)
    if (detail.value.summary) {
      summary.value = detail.value.summary
    } else {
      summary.value = await api.summary(id)
    }
    frames.value = await api.frames(id)
    frameIndex.value = 0
    if (frames.value.length) await loadFrame(0)
  }

  async function loadFrame(idx: number) {
    if (!selectedTaskId.value || !frames.value[idx]) return
    frameIndex.value = idx
    frameSamples.value = await api.frame(selectedTaskId.value, frames.value[idx].time_step)
  }

  async function deleteTask(id: number) {
    await api.deleteSimulation(id)
    if (selectedTaskId.value === id) {
      selectedTaskId.value = null
      summary.value = null
      frameSamples.value = []
      frames.value = []
    }
    await refreshTasks()
  }

  function nextFrame() {
    if (frames.value.length) loadFrame((frameIndex.value + 1) % frames.value.length)
  }
  function prevFrame() {
    if (frames.value.length)
      loadFrame((frameIndex.value - 1 + frames.value.length) % frames.value.length)
  }

  return {
    config,
    constellations,
    selectedCid,
    shells,
    selectedShellIds,
    satellites,
    satElements,
    currentTimeUnix,
    isRealtime,
    playing,
    rate,
    timezone,
    highlighted,
    showOrbits,
    tasks,
    selectedTaskId,
    detail,
    summary,
    frames,
    frameIndex,
    frameSamples,
    creating,
    taskError,
    selectedConstellation,
    selectedSatCount,
    runningCount,
    init,
    selectConstellation,
    loadSatellites,
    setShellSelection,
    toggleShell,
    setRealtime,
    togglePlay,
    setRate,
    setTimezone,
    setTimeUnix,
    advanceTime,
    toggleHighlight,
    clearHighlight,
    refreshTasks,
    createSimulation,
    pollTask,
    selectTaskForResults,
    loadFrame,
    deleteTask,
    nextFrame,
    prevFrame,
  }
})
