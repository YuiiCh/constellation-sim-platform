<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { useStore } from '@/store'
import GlobeView from '@/components/GlobeView.vue'
import HeaderBar from '@/components/HeaderBar.vue'
import TimeAxis from '@/components/TimeAxis.vue'
import ConstellationInfo from '@/components/ConstellationInfo.vue'
import SimulationAssistant from '@/components/SimulationAssistant.vue'
import TaskBar from '@/components/TaskBar.vue'
import SatelliteInfoPanel from '@/components/SatelliteInfoPanel.vue'
import CoverageResult from '@/components/CoverageResult.vue'
import AdvancedSettingsModal from '@/components/AdvancedSettingsModal.vue'

const store = useStore()
const showSettings = ref(false)
const selectedCellH3 = ref<string | null>(null)

let timer: ReturnType<typeof setInterval> | null = null
let taskTimer: ReturnType<typeof setInterval> | null = null
let last = performance.now()

function tick() {
  const now = performance.now()
  const dt = (now - last) / 1000
  last = now
  store.advanceTime(dt)
}

onMounted(async () => {
  await store.init()
  last = performance.now()
  timer = setInterval(tick, 50)
  // 周期性刷新任务列表（含通过 API 创建/历史任务），保证任务栏实时同步
  taskTimer = setInterval(() => store.refreshTasks(), 3000)
})
onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
  if (taskTimer) clearInterval(taskTimer)
})

function onCellClick(h3: string) {
  selectedCellH3.value = h3
}
</script>

<template>
  <div class="root">
    <GlobeView @cell-click="onCellClick" />

    <HeaderBar @open-settings="showSettings = true" />
    <ConstellationInfo />
    <SatelliteInfoPanel />
    <SimulationAssistant />
    <TaskBar />
    <CoverageResult :selected-cell-h3="selectedCellH3" />
    <TimeAxis />

    <AdvancedSettingsModal v-if="showSettings" @close="showSettings = false" />

    <div v-if="store.taskError" class="global-err">⚠ {{ store.taskError }}</div>
  </div>
</template>

<style scoped>
.root {
  position: absolute;
  inset: 0;
  overflow: hidden;
}
.global-err {
  position: absolute;
  top: 60px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(200, 60, 80, 0.9);
  color: #fff;
  padding: 6px 14px;
  border-radius: 8px;
  z-index: 200;
  font-size: 12px;
}
</style>
