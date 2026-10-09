<script setup lang="ts">
import { ref, computed } from 'vue'
import { useStore } from '@/store'
import { api } from '@/services/api'

const store = useStore()
const emit = defineEmits<{ (e: 'close'): void }>()

const tab = ref<'composite' | 'payload'>('composite')
const cons = computed(() => store.selectedConstellation)
const isComposite = computed(() => cons.value?.ctype === 'composite')

// Walker 参数（合成星座）
const w = ref({
  total: 300,
  planes: 10,
  per_plane: 30,
  alt_km: 1000,
  inc_deg: 55,
  pattern: 'delta',
  phase_factor: 1,
})
const msg = ref<string | null>(null)
const busy = ref(false)

// 链路预算默认参数（复杂功率规则使用）
const lb = ref({
  eirp_dBW: store.config?.default_eirp_dBW ?? 47,
  freq_ghz: (store.config?.default_freq_hz ?? 12e9) / 1e9,
  c_min_dbm: store.config?.default_c_min_dbm ?? -100,
  el_min_deg: store.config?.default_el_min_deg ?? 10,
})

async function regenerate() {
  if (!cons.value) return
  busy.value = true
  msg.value = null
  try {
    const r = await api.regenerate(cons.value.id, { walker: w.value })
    msg.value = r.message
    await store.selectConstellation(cons.value.id)
  } catch (e: any) {
    msg.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="mask" @click.self="emit('close')">
    <div class="modal panel">
      <div class="modal-head">
        <span class="panel-title">⚙ 星座高级设置 · {{ cons?.name }}</span>
        <button class="ghost mini" @click="emit('close')">✕</button>
      </div>

      <div class="tabs">
        <button :class="['tab', tab === 'composite' ? 'active' : '']" @click="tab = 'composite'">合成星座参数</button>
        <button :class="['tab', tab === 'payload' ? 'active' : '']" @click="tab = 'payload'">载荷 / 链路预算</button>
      </div>

      <div v-if="tab === 'composite'" class="content">
        <div v-if="isComposite" class="form">
          <div class="note">Walker 星座参数（Walker-Delta / Walker-Star），修改后点击“重新生成”即时生效。</div>
          <div class="grid">
            <label>总卫星数 <input type="number" min="1" v-model="w.total" /></label>
            <label>轨道面数 <input type="number" min="1" v-model="w.planes" /></label>
            <label>面内卫星数 <input type="number" min="1" v-model="w.per_plane" /></label>
            <label>高度(km) <input type="number" v-model="w.alt_km" /></label>
            <label>倾角(°) <input type="number" step="0.5" v-model="w.inc_deg" /></label>
            <label>相位因子 <input type="number" step="0.1" v-model="w.phase_factor" /></label>
            <label>构型
              <select v-model="w.pattern">
                <option value="delta">Walker-Delta</option>
                <option value="star">Walker-Star</option>
              </select>
            </label>
          </div>
          <button class="primary" :disabled="busy" @click="regenerate">{{ busy ? '生成中…' : '重新生成星座' }}</button>
          <div v-if="msg" class="msg">{{ msg }}</div>
        </div>
        <div v-else class="note">
          当前为实时/真实星座（{{ cons?.name }}），其星历由 celestrak 拉取或合成轨道根数填充，不支持 Walker 参数重生成。可切换至“合成星座（规划）”进行调整。
        </div>
      </div>

      <div v-else class="content">
        <div class="note">复杂 C/dBm 功率规则默认链路预算参数（可在创建仿真任务时按任务覆盖）。</div>
        <div class="grid">
          <label>EIRP(dBW) <input type="number" step="0.5" v-model="lb.eirp_dBW" /></label>
          <label>频率(GHz) <input type="number" step="0.1" v-model="lb.freq_ghz" /></label>
          <label>C/dBm 门槛 <input type="number" v-model="lb.c_min_dbm" /></label>
          <label>仰角门槛(°) <input type="number" step="0.5" v-model="lb.el_min_deg" /></label>
        </div>
        <div class="note muted">
          载荷管理（每颗星独立载荷）为 P1 能力，当前以星座级默认载荷参数驱动链路预算。
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 14, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 120;
}
.modal {
  width: 640px;
  max-width: 94vw;
  max-height: 88vh;
  overflow: auto;
  padding: 16px;
}
.modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.mini {
  padding: 0 8px;
}
.tabs {
  display: flex;
  gap: 8px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 12px;
}
.tab {
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  border-radius: 0;
  padding: 8px 6px;
}
.tab.active {
  border-bottom-color: var(--accent);
  color: #fff;
  font-weight: 600;
}
.content {
  min-height: 200px;
}
.note {
  font-size: 12px;
  color: var(--text-dim);
  background: rgba(30, 60, 110, 0.25);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 10px;
  margin-bottom: 10px;
  line-height: 1.5;
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.grid label {
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 11px;
  color: var(--text-dim);
}
.msg {
  margin-top: 10px;
  color: var(--ok);
  font-size: 12px;
}
</style>
