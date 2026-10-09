<script setup lang="ts">
import { ref } from 'vue'
import { useStore } from '@/store'

const store = useStore()
const collapsed = ref(false)
</script>

<template>
  <div class="info panel" :class="{ collapsed }">
    <div class="head panel-title">
      <span>🛰 星座 / 卫星信息</span>
      <button class="ghost mini" @click="collapsed = !collapsed">{{ collapsed ? '▸' : '▾' }}</button>
    </div>

    <div v-if="!collapsed" class="body scroll">
      <div class="row">
        <span class="muted">星座</span>
        <b>{{ store.selectedConstellation?.name }}</b>
      </div>
      <div class="row">
        <span class="muted">卫星数</span>
        <span class="tag ok">{{ store.selectedSatCount }}</span>
      </div>
      <div class="row">
        <span class="muted">壳层</span>
        <span class="tag">{{ store.shells.length }}</span>
      </div>

      <div class="sub">壳层筛选（默认仅稳定壳层，立即生效）</div>
      <label v-for="sh in store.shells" :key="sh.id" class="shell">
        <input
          type="checkbox"
          :checked="store.selectedShellIds.includes(sh.id)"
          @change="store.toggleShell(sh.id)"
        />
        <span class="sh-name">{{ sh.name }}</span>
        <span class="muted">{{ sh.count }}星 · {{ sh.altitude_km }}km · {{ sh.inclination_deg }}°</span>
        <span class="kind" :class="sh.kind">{{ sh.kind === 'stable' ? '稳定' : '临时' }}</span>
      </label>

      <div class="sub">显示选项</div>
      <label class="shell">
        <input type="checkbox" v-model="store.showOrbits" />
        <span class="sh-name">显示高亮卫星轨道</span>
      </label>
    </div>
  </div>
</template>

<style scoped>
.info {
  position: absolute;
  top: 64px;
  right: 14px;
  width: 280px;
  z-index: 25;
  padding: 10px 12px;
}
.head {
  justify-content: space-between;
}
.mini {
  padding: 0 8px;
}
.body {
  margin-top: 8px;
  max-height: 52vh;
}
.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 3px 0;
}
.sub {
  margin: 10px 0 4px;
  color: var(--accent-2);
  font-size: 11px;
  border-top: 1px solid var(--border);
  padding-top: 6px;
}
.shell {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 3px 0;
  font-size: 12px;
}
.sh-name {
  font-weight: 600;
}
.kind {
  margin-left: auto;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 8px;
}
.kind.stable {
  background: rgba(40, 160, 120, 0.25);
  color: var(--ok);
}
.kind.temporary {
  background: rgba(200, 150, 60, 0.25);
  color: var(--warn);
}
</style>
