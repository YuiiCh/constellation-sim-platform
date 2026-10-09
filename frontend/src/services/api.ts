// 后端 API 封装。所有响应类型位于 types.ts。
import type {
  Config,
  Constellation,
  Shell,
  Satellite,
  SimulationTask,
  SimulationDetail,
  CoverageSample,
  CellAggregate,
  FrameStep,
  SpaceTrackResult,
} from '@/types'

const BASE = '/api'

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!resp.ok) {
    const text = await resp.text().catch(() => '')
    throw new Error(`API ${path} 失败 ${resp.status}: ${text.slice(0, 200)}`)
  }
  return resp.json() as Promise<T>
}

export const api = {
  config: () => http<Config>('/config'),

  constellations: () => http<Constellation[]>('/constellations'),

  shells: (cid: string) => http<Shell[]>(`/constellations/${cid}/shells`),

  satellites: (cid: string, onlyDefault = true, shellIds?: number[]) => {
    const params = new URLSearchParams()
    params.set('only_default', String(onlyDefault))
    if (shellIds && shellIds.length) params.set('shell_ids', shellIds.join(','))
    return http<Satellite[]>(`/constellations/${cid}/satellites?${params.toString()}`)
  },

  satelliteDetail: (noradId: number) =>
    http<any>(`/satellites/${noradId}`),

  propagate: (cid: string, t: string, onlyDefault = true) =>
    http<{ time: string; satellites: any[] }>(
      `/constellations/${cid}/propagate?t=${encodeURIComponent(t)}&only_default=${onlyDefault}`,
    ),

  createSimulation: (body: any) =>
    http<SimulationTask>('/simulations', { method: 'POST', body: JSON.stringify(body) }),

  simulations: () => http<SimulationTask[]>('/simulations'),

  simulation: (id: number) => http<SimulationDetail>(`/simulations/${id}`),

  deleteSimulation: (id: number) =>
    http<SimulationTask>(`/simulations/${id}`, { method: 'DELETE' }),

  summary: (id: number) => http<SimulationSummary>(`/simulations/${id}/summary`),

  frames: (id: number) => http<FrameStep[]>(`/simulations/${id}/frames`),

  frame: (id: number, timeStep: number) =>
    http<CoverageSample[]>(`/simulations/${id}/frame/${timeStep}`),

  spaceTrack: (body: any) =>
    http<SpaceTrackResult>('/spacetrack/query', { method: 'POST', body: JSON.stringify(body) }),

  regenerate: (cid: string, body: any) =>
    http<{ ok: boolean; message: string; satellites: number }>(
      `/constellations/${cid}/regenerate`,
      { method: 'POST', body: JSON.stringify(body) },
    ),
}

export type { CellAggregate }
