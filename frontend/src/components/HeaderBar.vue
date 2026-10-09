<script setup lang="ts">
import { useStore } from '@/store'
const store = useStore()
const emit = defineEmits<{ (e: 'open-settings'): void }>()

function onChange(e: Event) {
  store.selectConstellation((e.target as HTMLSelectElement).value)
}
</script>

<template>
  <header class="header">
    <div class="brand">
      <span class="logo">✦</span>
      <span class="title">星座仿真平台</span>
    </div>

    <div class="center">
      <label class="muted">当前星座</label>
      <select class="cons-select" :value="store.selectedCid" @change="onChange">
        <option v-for="c in store.constellations" :key="c.id" :value="c.id">
          {{ c.name }}（{{ c.satellite_count }} 星）
        </option>
      </select>
    </div>

    <button class="settings-btn" @click="emit('open-settings')">⚙ 星座高级设置</button>
  </header>
</template>

<style scoped>
.header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 52px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  z-index: 30;
  background: linear-gradient(180deg, rgba(6, 14, 28, 0.92), rgba(6, 14, 28, 0.4));
  border-bottom: 1px solid var(--border);
}
.brand {
  display: flex;
  align-items: center;
  gap: 8px;
}
.logo {
  color: var(--accent-2);
  font-size: 18px;
}
.title {
  font-weight: 700;
  letter-spacing: 1px;
  color: #eaf3ff;
}
.center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 10px;
}
.cons-select {
  min-width: 200px;
  font-size: 14px;
  font-weight: 600;
  background: rgba(20, 40, 70, 0.9);
}
.settings-btn {
  margin-left: auto;
  background: rgba(40, 70, 120, 0.4);
}
</style>
