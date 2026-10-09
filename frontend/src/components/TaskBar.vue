<script setup lang="ts">
import { ref } from 'vue'
import { useStore } from '@/store'

const store = useStore()
const collapsed = ref(false)

function statusTag(s: string) {
  if (s === 'running') return 'run'
  if (s === 'succeeded') return 'ok'
  if (s === 'failed') return 'fail'
  return ''
}
function statusText(s: string) {
  return { pending: '排队中', running: '运行中', succeeded: '已完成', failed: '失败', cancelled: '已取消' }[s] || s
}
</script>

<template>
  <div class="taskbar panel" :class="{ collapsed }">
    <div class="head panel-title">
      <span>📋 任务栏</span>
      <span class="run-badge" v-if="store.runningCount">运行中 {{ store.runningCount }}</span>
      <button class="ghost mini" @click="collapsed = !collapsed">{{ collapsed ? '▸' : '▾' }}</button>
    </div>

    <div v-if="!collapsed" class="body scroll">
      <div v-if="!store.tasks.length" class="empty muted">暂无任务。在左侧仿真助手创建覆盖仿真。</div>
      <div
        v-for="t in store.tasks"
        :key="t.id"
        class="task"
        :class="{ sel: t.id === store.selectedTaskId }"
        @click="t.status === 'succeeded' ? store.selectTaskForResults(t.id) : null"
      >
        <div class="t-top">
          <span class="t-name">#{{ t.id }} {{ t.name }}</span>
          <span class="tag" :class="statusTag(t.status)">{{ statusText(t.status) }}</span>
        </div>
        <div class="t-meta muted">
          {{ t.rule_type === 'complex_power' ? '复杂功率规则' : '简单仰角规则' }} · 进度
          {{ Math.round(t.progress) }}%
        </div>
        <div class="t-progress">
          <div class="bar" :style="{ width: t.progress + '%' }" :class="statusTag(t.status)"></div>
        </div>
        <div class="t-actions">
          <button
            v-if="t.status === 'succeeded'"
            class="mini"
            @click.stop="store.selectTaskForResults(t.id)"
          >
            查看结果
          </button>
          <button class="mini danger" @click.stop="store.deleteTask(t.id)">删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.taskbar {
  position: absolute;
  bottom: 70px;
  right: 14px;
  width: 300px;
  z-index: 25;
  padding: 10px 12px;
}
.head {
  justify-content: space-between;
}
.run-badge {
  margin-left: auto;
  margin-right: 8px;
  font-size: 11px;
  color: var(--accent-2);
}
.mini {
  padding: 1px 8px;
  font-size: 11px;
}
.body {
  margin-top: 8px;
  max-height: 40vh;
}
.empty {
  font-size: 12px;
  padding: 10px 0;
}
.task {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 7px 9px;
  margin-bottom: 7px;
  cursor: pointer;
  transition: border-color 0.15s;
}
.task:hover {
  border-color: var(--border-bright);
}
.task.sel {
  border-color: var(--accent);
  background: rgba(40, 110, 200, 0.18);
}
.t-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.t-name {
  font-weight: 600;
  font-size: 12px;
}
.t-meta {
  font-size: 11px;
  margin: 3px 0;
}
.t-progress {
  height: 4px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  overflow: hidden;
}
.bar {
  height: 100%;
  background: var(--accent);
  transition: width 0.4s;
}
.bar.ok {
  background: var(--ok);
}
.bar.fail {
  background: var(--danger);
}
.bar.run {
  background: var(--accent-2);
}
.t-actions {
  display: flex;
  gap: 6px;
  margin-top: 5px;
  justify-content: flex-end;
}
.danger {
  color: var(--danger);
  border-color: rgba(255, 93, 108, 0.4);
}
</style>
