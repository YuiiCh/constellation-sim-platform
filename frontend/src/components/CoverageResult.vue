<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, computed, nextTick } from 'vue'
import * as echarts from 'echarts'
import { useStore } from '@/store'

const props = defineProps<{ selectedCellH3?: string | null }>()
const store = useStore()
const chartEl = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

const currentFrame = computed(() => store.frames[store.frameIndex] || null)
const selCell = computed(() =>
  props.selectedCellH3 && store.summary
    ? store.summary.cell_aggregates.find((c) => c.h3_index === props.selectedCellH3)
    : null,
)

function renderChart() {
  if (!chart || !store.summary) return
  const s = store.summary
  const x = s.per_step_coverage_simple.map((_, i) => i)
  const series: any[] = [
    {
      name: '简单仰角覆盖率',
      type: 'line',
      showSymbol: false,
      smooth: true,
      data: s.per_step_coverage_simple.map((v, i) => [i, v]),
      lineStyle: { color: '#4ea3ff' },
      itemStyle: { color: '#4ea3ff' },
    },
  ]
  if (s.per_step_coverage_complex) {
    series.push({
      name: '复杂功率覆盖率',
      type: 'line',
      showSymbol: false,
      smooth: true,
      data: s.per_step_coverage_complex.map((v, i) => [i, v]),
      lineStyle: { color: '#ffb347' },
      itemStyle: { color: '#ffb347' },
    })
  }
  const markLine = currentFrame.value
    ? {
        silent: true,
        symbol: 'none',
        lineStyle: { color: '#ffffff', type: 'dashed' },
        data: [{ xAxis: currentFrame.value.time_step }],
      }
    : undefined
  series[0].markLine = markLine
  if (series[1]) series[1].markLine = markLine
  chart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 42, right: 16, top: 28, bottom: 28 },
    legend: { textStyle: { color: '#cfe0ff' }, top: 0, fontSize: 11 },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'value',
      name: '步',
      min: 0,
      max: s.n_steps - 1,
      axisLabel: { color: '#8aa0c4' },
      axisLine: { lineStyle: { color: '#34507a' } },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 1,
      axisLabel: { color: '#8aa0c4' },
      splitLine: { lineStyle: { color: 'rgba(90,150,220,0.12)' } },
    },
    series,
  })
}

function initChart() {
  if (chart || !chartEl.value) return
  chart = echarts.init(chartEl.value)
}

async function ensureChart() {
  await nextTick()
  initChart()
  renderChart()
}

onMounted(ensureChart)
onBeforeUnmount(() => chart?.dispose())
watch(
  () => store.summary,
  async (s) => {
    if (!s) {
      chart?.dispose()
      chart = null
      return
    }
    await ensureChart()
  },
  { deep: false },
)
watch(() => store.frameIndex, renderChart)

function closeDetail() {
  // 由父组件通过 prop 控制，这里仅提示
}
</script>

<template>
  <div class="coverage panel" v-if="store.summary">
    <div class="head panel-title">
      <span>📊 覆盖仿真结果</span>
      <button class="ghost mini" @click="store.selectTaskForResults(store.selectedTaskId!)">↻ 刷新</button>
    </div>

    <div class="stats">
      <div class="stat"><span class="muted">任务</span><b>#{{ store.selectedTaskId }} {{ store.detail?.name }}</b></div>
      <div class="stat"><span class="muted">网格数</span><b>{{ store.summary.total_cells }}</b></div>
      <div class="stat"><span class="muted">规则</span><b>{{ store.summary.rule_type === 'complex_power' ? '复杂功率' : '简单仰角' }}</b></div>
      <div class="stat"><span class="muted">简单覆盖</span><b class="ok">{{ (store.summary.overall_coverage_simple * 100).toFixed(1) }}%</b></div>
      <div class="stat" v-if="store.summary.overall_coverage_complex !== null">
        <span class="muted">复杂覆盖</span><b class="warn">{{ (store.summary.overall_coverage_complex! * 100).toFixed(1) }}%</b>
      </div>
    </div>

    <div class="frame-nav">
      <button class="mini" @click="store.prevFrame()">◀</button>
      <span class="muted">帧 {{ store.frameIndex + 1 }}/{{ store.frames.length }} · {{ currentFrame?.timestamp_utc }}</span>
      <button class="mini" @click="store.nextFrame()">▶</button>
    </div>

    <div ref="chartEl" class="chart"></div>

    <div class="phases" v-if="store.detail?.stage_timings">
      <span class="muted">分阶段耗时(s)：</span>
      <span>传播 {{ store.detail.stage_timings.propagation_s }}</span>
      <span>仰角 {{ store.detail.stage_timings.elevation_s }}</span>
      <span>功率 {{ store.detail.stage_timings.power_s }}</span>
      <span>聚合 {{ store.detail.stage_timings.aggregation_s }}</span>
    </div>

    <div class="cell-detail" v-if="selCell">
      <div class="cd-head">📍 网格详情 <span class="muted">{{ selCell.h3_index }}</span>
        <button class="mini" @click="closeDetail()">×</button>
      </div>
      <div class="cd-body">
        <div>中心：{{ selCell.lat.toFixed(2) }}°, {{ selCell.lon.toFixed(2) }}°</div>
        <div>覆盖占比：<b class="ok">{{ (selCell.covered_frac_simple * 100).toFixed(1) }}%</b></div>
        <div>最佳仰角：{{ selCell.best_elevation_deg ?? '—' }}<span v-if="selCell.best_elevation_deg">°</span></div>
        <div v-if="selCell.best_c_dBm !== null">最佳 C/dBm：{{ selCell.best_c_dBm }} dBm</div>
        <div>覆盖卫星：<span v-if="!selCell.covering_norad_ids.length" class="muted">无</span>
          <span v-for="n in selCell.covering_norad_ids" :key="n" class="tag" style="margin-right:4px">{{ n }}</span>
        </div>
      </div>
    </div>
    <div v-else class="hint muted">在地球上点击任意覆盖网格查看详情。</div>
  </div>
</template>

<style scoped>
.coverage {
  position: absolute;
  bottom: 70px;
  left: 14px;
  width: 380px;
  z-index: 26;
  padding: 10px 12px;
  max-height: 70vh;
  overflow: auto;
}
.head {
  justify-content: space-between;
  margin-bottom: 8px;
}
.mini {
  padding: 1px 8px;
  font-size: 11px;
}
.stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}
.stat {
  display: flex;
  flex-direction: column;
  gap: 1px;
  font-size: 11px;
}
.stat b {
  font-size: 14px;
}
.ok {
  color: var(--ok);
}
.warn {
  color: var(--warn);
}
.frame-nav {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 10px 0 4px;
  font-size: 11px;
}
.chart {
  width: 100%;
  height: 180px;
}
.phases {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 11px;
  color: var(--text-dim);
  border-top: 1px solid var(--border);
  padding-top: 6px;
}
.cell-detail {
  margin-top: 8px;
  border: 1px solid var(--border-bright);
  border-radius: 8px;
  padding: 8px;
  background: rgba(30, 60, 110, 0.25);
}
.cd-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  margin-bottom: 5px;
}
.cd-head .mini {
  margin-left: auto;
}
.cd-body {
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 12px;
}
.hint {
  font-size: 11px;
  margin-top: 6px;
}
</style>
