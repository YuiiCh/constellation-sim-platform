// 前端共享类型，与后端 Pydantic 契约对齐

export interface Constellation {
  id: string
  name: string
  ctype: string
  description: string | null
  celestrak_group: string | null
  source: string
  shell_count: number
  satellite_count: number
}

export interface Shell {
  id: number
  constellation_id: string
  name: string
  kind: string
  altitude_km: number
  inclination_deg: number
  count: number
  is_default: boolean
}

export interface Satellite {
  norad_id: number
  name: string
  object_id: string | null
  epoch: string
  a_km: number
  ecc: number
  inc_deg: number
  raan_deg: number
  argp_deg: number
  ma_deg: number
  mean_motion: number | null
  source: string
  constellation_id: string | null
}

export interface Config {
  timeline_rates: number[]
  max_fps_options: number[]
  default_sample_interval_s: number
  default_duration_h: number
  default_el_min_deg: number
  default_c_min_dbm: number
  default_h3_res: number
  default_region: number[]
  default_freq_hz: number
  default_bandwidth_hz: number
  default_eirp_dBW: number
  default_g_r_dbi: number
  default_t_s_k: number
  default_l_atm_db: number
  default_l_pol_db: number
  default_l_point_db: number
  celestrak_enabled: boolean
  celestrak_fetch_interval: number
  timezones: string[]
}

export interface SimulationTask {
  id: number
  name: string
  constellation_id: string
  rule_type: string
  status: string
  progress: number
  error: string | null
  stage_timings: Record<string, number> | null
  created_at: string | null
  started_at: string | null
  finished_at: string | null
}

export interface CoverageSample {
  time_step: number
  timestamp_utc: string
  h3_index: string
  lat: number
  lon: number
  covered_simple: boolean
  covered_complex: boolean
  covering_norad_ids: number[]
  max_elevation_deg: number | null
  max_c_dBm: number | null
  distance_km: number | null
}

export interface CellAggregate {
  h3_index: string
  lat: number
  lon: number
  boundary: [number, number][]
  covered_frac_simple: number
  best_elevation_deg: number | null
  best_c_dBm: number | null
  covering_norad_ids: number[]
}

export interface SimulationSummary {
  rule_type: string
  total_cells: number
  total_satellites: number
  n_steps: number
  sample_interval_s: number
  viz_interval_s: number
  start_utc: string
  end_utc: string
  el_min_deg: number
  c_min_dbm: number
  region: number[]
  h3_res: number
  per_step_coverage_simple: number[]
  per_step_coverage_complex: number[] | null
  overall_coverage_simple: number
  overall_coverage_complex: number | null
  cell_aggregates: CellAggregate[]
  stage_timings: Record<string, number>
  seed: number | null
}

export interface SimulationDetail extends SimulationTask {
  params: any
  summary: SimulationSummary | null
}

export interface FrameStep {
  time_step: number
  timestamp_utc: string
}

export interface SpaceTrackResult {
  ok: boolean
  message: string
  count: number
  rate_limited: boolean
  needs_credentials: boolean
}
