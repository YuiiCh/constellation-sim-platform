<script setup lang="ts">
import { computed } from 'vue'
import { useStore } from '@/store'

const store = useStore()
const items = computed(() =>
  store.highlighted
    .map((id) => store.satellites.find((s) => s.norad_id === id))
    .filter(Boolean) as any[],
)
</script>

<template>
  <div v-if="items.length" class="satpanel panel">
    <div class="head panel-title">
      <span>🛰 已选卫星 ({{ items.length }})</span>
      <button class="ghost mini" @click="store.clearHighlight()">清除全部</button>
    </div>
    <div class="body scroll">
      <div v-for="s in items" :key="s.norad_id" class="sat">
        <div class="sat-top">
          <b>{{ s.name }}</b>
          <button class="mini" @click="store.toggleHighlight(s.norad_id)">✕</button>
        </div>
        <div class="sat-meta muted">
          NORAD {{ s.norad_id }} · {{ s.inc_deg }}° · {{ Math.round(s.a_km - 6378) }}km
        </div>
      </div>
      <div class="hint muted">点击卫星可多选高亮；高亮卫星显示脉冲点与轨道线（在信息面板开启）。</div>
    </div>
  </div>
</template>

<style scoped>
.satpanel {
  position: absolute;
  top: 64px;
  right: 310px;
  width: 230px;
  z-index: 24;
  padding: 10px 12px;
}
.head {
  justify-content: space-between;
  margin-bottom: 6px;
}
.mini {
  padding: 1px 7px;
  font-size: 11px;
}
.body {
  max-height: 40vh;
}
.sat {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 6px 8px;
  margin-bottom: 6px;
  background: rgba(30, 60, 110, 0.2);
}
.sat-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.sat-meta {
  font-size: 11px;
  margin-top: 2px;
}
.hint {
  font-size: 11px;
  margin-top: 4px;
  line-height: 1.5;
}
</style>
