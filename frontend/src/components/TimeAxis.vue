<script setup lang="ts">
import { computed } from 'vue'
import { useStore } from '@/store'
import {
  formatInTz,
  secondsIntoDay,
  startOfDayInTz,
  fromDayOffset,
  toUtcUnix,
} from '@/utils/time'

const store = useStore()

const fmt = computed(() => formatInTz(store.currentTimeUnix, store.timezone))
const dayOffset = computed(() => secondsIntoDay(store.currentTimeUnix, store.timezone))

function onDateInput(e: Event) {
  const date = (e.target as HTMLInputElement).value
  const { time } = formatInTz(store.currentTimeUnix, store.timezone)
  store.setTimeUnix(toUtcUnix(date, time, store.timezone))
}
function onTimeInput(e: Event) {
  const time = (e.target as HTMLInputElement).value
  const { date } = formatInTz(store.currentTimeUnix, store.timezone)
  store.setTimeUnix(toUtcUnix(date, time, store.timezone))
}
function onSlider(e: Event) {
  const v = Number((e.target as HTMLInputElement).value)
  const dayStart = startOfDayInTz(store.currentTimeUnix, store.timezone)
  store.setTimeUnix(fromDayOffset(dayStart, v))
}
function onRate(e: Event) {
  store.setRate(Number((e.target as HTMLSelectElement).value))
}
function onTz(e: Event) {
  store.setTimezone((e.target as HTMLSelectElement).value)
}
function toggleRealtime() {
  store.setRealtime(!store.isRealtime)
}
function fmtSeconds(s: number) {
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}
</script>

<template>
  <div class="timeaxis panel">
    <button :class="['play', store.playing ? 'active' : '']" @click="store.togglePlay()" :title="store.playing ? '暂停' : '播放'">
      {{ store.playing ? '⏸' : '▶' }}
    </button>

    <div class="field">
      <label>日期</label>
      <input type="date" :value="fmt.date" @change="onDateInput" />
    </div>

    <div class="field">
      <label>时间</label>
      <input type="time" step="1" :value="fmt.time" @change="onTimeInput" />
    </div>

    <div class="slider-wrap">
      <input
        class="slider"
        type="range"
        min="0"
        max="86399"
        :value="dayOffset"
        @input="onSlider"
      />
      <div class="ticks">
        <span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>24:00</span>
      </div>
    </div>

    <button :class="['realtime', store.isRealtime ? 'active' : '']" @click="toggleRealtime">
      {{ store.isRealtime ? '● 实时' : '实时' }}
    </button>

    <div class="field">
      <label>倍率</label>
      <select :value="store.rate" @change="onRate">
        <option v-for="r in store.config?.timeline_rates" :key="r" :value="r">x{{ r }}</option>
      </select>
    </div>

    <div class="field">
      <label>时区</label>
      <select :value="store.timezone" @change="onTz">
        <option v-for="tz in store.config?.timezones" :key="tz" :value="tz">{{ tz }}</option>
      </select>
    </div>
  </div>
</template>

<style scoped>
.timeaxis {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 8px 16px;
  position: absolute;
  bottom: 14px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 20;
  width: min(1080px, 94vw);
}
.field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.field label {
  font-size: 10px;
  color: var(--text-dim);
}
.slider-wrap {
  flex: 1;
  min-width: 220px;
}
.slider {
  width: 100%;
  accent-color: var(--accent);
}
.ticks {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: var(--text-dim);
}
.play,
.realtime {
  font-size: 14px;
  min-width: 56px;
}
.realtime.active {
  background: linear-gradient(180deg, #ff9a3c, #f07a1c);
  border-color: #ffb347;
  color: #1a1206;
  font-weight: 700;
}
</style>
