<script setup lang="ts">
import { ref, computed } from 'vue'
import { useStore } from '@/store'
import { api } from '@/services/api'
import { startOfDayInTz, toUtcUnix, formatInTz } from '@/utils/time'
import type { SpaceTrackResult } from '@/types'

const store = useStore()

// ---- 创建任务向导（SOP，禁用自然语言输入，仅系统气泡 + 选项/输入） ----
const wizardOpen = ref(false)
const step = ref(1)
const name = ref('覆盖仿真任务')
const ruleType = ref<'simple_elevation' | 'complex_power'>('simple_elevation')
const timeMode = ref<'today' | 'axis' | 'custom'>('today')
const customDate = ref(formatInTz(store.currentTimeUnix, store.timezone).date)
const customTime = ref('00:00:00')
const customDuration = ref(24)
const sampleInterval = ref(15)
const h3Res = ref(4)
const region = ref<number[]>([28, 105, 42, 122])
const elMin = ref(10)
const cMin = ref(-100)
const eirp = ref(47)
const freq = ref(12.0)
const errMsg = ref<string | null>(null)
const busy = ref(false)

const linkParams = computed(() => ({
  el_min_deg: elMin.value,
  c_min_dbm: cMin.value,
  eirp_dBW: eirp.value,
  freq_hz: freq.value * 1e9,
}))

function buildStartUtc(): string {
  if (timeMode.value === 'today') {
    return new Date(Math.floor(Date.now() / 86400000) * 86400000).toISOString().slice(0, 19) + 'Z'
  }
  if (timeMode.value === 'axis') {
    const dayStart = startOfDayInTz(store.currentTimeUnix, store.timezone)
    return new Date(dayStart * 1000).toISOString().slice(0, 19) + 'Z'
  }
  return new Date(toUtcUnix(customDate.value, customTime.value, store.timezone) * 1000).toISOString().slice(0, 19) + 'Z'
}

async function submit() {
  errMsg.value = null
  busy.value = true
  try {
    const payload = {
      name: name.value,
      constellation_id: store.selectedCid,
      rule_type: ruleType.value,
      start_utc: buildStartUtc(),
      duration_h: timeMode.value === 'custom' ? customDuration.value : 24,
      sample_interval_s: sampleInterval.value,
      h3_res: h3Res.value,
      region: region.value,
      selected_shell_ids: store.selectedShellIds,
      params: ruleType.value === 'complex_power' ? linkParams.value : { el_min_deg: elMin.value },
    }
    await store.createSimulation(payload)
    wizardOpen.value = false
    step.value = 1
  } catch (e: any) {
    errMsg.value = e.message || '创建失败'
  } finally {
    busy.value = false
  }
}

// ---- space-track 凭据（历史星历，按需查询） ----
const stOpen = ref(false)
const stIdentity = ref('')
const stPassword = ref('')
const stNorad = ref<number>(store.satellites[0]?.norad_id || 900000)
const stResult = ref<SpaceTrackResult | null>(null)
const stBusy = ref(false)
async function querySpaceTrack() {
  stBusy.value = true
  stResult.value = null
  try {
    stResult.value = await api.spaceTrack({
      norad_id: stNorad.value,
      identity: stIdentity.value,
      password: stPassword.value,
    })
  } catch (e: any) {
    stResult.value = { ok: false, message: e.message, count: 0, rate_limited: false, needs_credentials: false }
  } finally {
    stBusy.value = false
  }
}
</script>

<template>
  <div class="assistant panel">
    <div class="head panel-title">
      <span>🤖 仿真助手</span>
    </div>
    <div class="body">
      <div class="bubble sys">
        欢迎使用星座仿真平台。我可协助你创建<strong>地面区域覆盖仿真</strong>。点击下方按钮开始（按推荐默认值即可）。
      </div>
      <button class="primary wide" @click="wizardOpen = true">＋ 创建新任务</button>
      <button class="wide" @click="stOpen = true">🔑 配置 space-track 历史星历</button>
    </div>

    <!-- 创建任务向导 -->
    <div v-if="wizardOpen" class="modal-mask" @click.self="wizardOpen = false">
      <div class="modal panel">
        <div class="modal-head">
          <span class="panel-title">创建覆盖仿真任务</span>
          <button class="ghost mini" @click="wizardOpen = false">✕</button>
        </div>

        <div v-if="step === 1" class="step">
          <div class="bubble sys">步骤 1 / 3：选择覆盖规则（默认简单仰角规则，开箱即用）。</div>
          <div class="opts">
            <button :class="['opt', ruleType === 'simple_elevation' ? 'active' : '']" @click="ruleType = 'simple_elevation'">
              <b>简单仰角规则</b><span class="muted">仅需仰角约束，快速</span>
            </button>
            <button :class="['opt', ruleType === 'complex_power' ? 'active' : '']" @click="ruleType = 'complex_power'">
              <b>复杂 C/dBm 功率规则</b><span class="muted">链路预算，需载荷参数</span>
            </button>
          </div>
          <div class="actions">
            <button class="primary" @click="step = 2">下一步</button>
          </div>
        </div>

        <div v-else-if="step === 2" class="step">
          <div class="bubble sys">步骤 2 / 3：仿真时间区间（默认今天 24 小时）。</div>
          <label class="opt-line" :class="{ on: timeMode === 'today' }" @click="timeMode = 'today'">
            今天（今日 0–24 时 UTC）
          </label>
          <label class="opt-line" :class="{ on: timeMode === 'axis' }" @click="timeMode = 'axis'">
            时间轴所选日期的 24 小时
          </label>
          <label class="opt-line" :class="{ on: timeMode === 'custom' }" @click="timeMode = 'custom'">
            自定义起止
          </label>
          <div v-if="timeMode === 'custom'" class="custom">
            <input type="date" v-model="customDate" />
            <input type="time" step="1" v-model="customTime" />
            <label>时长(小时) <input type="number" min="1" max="72" v-model="customDuration" style="width:70px" /></label>
          </div>
          <div class="actions">
            <button @click="step = 1">上一步</button>
            <button class="primary" @click="step = 3">下一步</button>
          </div>
        </div>

        <div v-else class="step">
          <div class="bubble sys">步骤 3 / 3：采样与区域参数（已填推荐值，可直接提交）。</div>
          <div class="grid">
            <label>任务名 <input v-model="name" /></label>
            <label>采样间隔(秒) <input type="number" min="1" v-model="sampleInterval" /></label>
            <label>H3 分辨率 <input type="number" min="3" max="6" v-model="h3Res" /></label>
            <label>仰角门槛(°) <input type="number" step="0.5" v-model="elMin" /></label>
            <label v-if="ruleType === 'complex_power'">C/dBm 门槛 <input type="number" v-model="cMin" /></label>
            <label v-if="ruleType === 'complex_power'">EIRP(dBW) <input type="number" v-model="eirp" /></label>
            <label v-if="ruleType === 'complex_power'">频率(GHz) <input type="number" step="0.1" v-model="freq" /></label>
          </div>
          <div class="region">
            <span class="muted">区域包围盒 [lat_min,lon_min,lat_max,lon_max]</span>
            <div class="region-inputs">
              <input type="number" v-model="region[0]" />
              <input type="number" v-model="region[1]" />
              <input type="number" v-model="region[2]" />
              <input type="number" v-model="region[3]" />
            </div>
          </div>
          <div v-if="errMsg" class="err">⚠ {{ errMsg }}</div>
          <div class="actions">
            <button @click="step = 2">上一步</button>
            <button class="primary" :disabled="busy" @click="submit">{{ busy ? '提交中…' : '提交仿真' }}</button>
          </div>
        </div>
      </div>
    </div>

    <!-- space-track -->
    <div v-if="stOpen" class="modal-mask" @click.self="stOpen = false">
      <div class="modal panel">
        <div class="modal-head">
          <span class="panel-title">space-track 历史星历</span>
          <button class="ghost mini" @click="stOpen = false">✕</button>
        </div>
        <div class="bubble sys">
          用于查询历史星历。仅在仿真/展示时间早于实时数据覆盖范围时按需使用。凭据仅保存在本地内存，不会持久化。
        </div>
        <label class="st">NORAD ID <input type="number" v-model="stNorad" /></label>
        <label class="st">用户名 <input v-model="stIdentity" placeholder="space-track 账号" /></label>
        <label class="st">密码 <input type="password" v-model="stPassword" placeholder="space-track 密码" /></label>
        <button class="primary" :disabled="stBusy" @click="querySpaceTrack">{{ stBusy ? '查询中…' : '查询历史星历' }}</button>
        <div v-if="stResult" class="st-result" :class="{ ok: stResult.ok, warn: !stResult.ok }">
          {{ stResult.message }}（记录数：{{ stResult.count }}）
          <span v-if="stResult.needs_credentials" class="badge">缺少凭据</span>
          <span v-if="stResult.rate_limited" class="badge">速率受限</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.assistant {
  position: absolute;
  top: 64px;
  left: 14px;
  width: 270px;
  z-index: 25;
  padding: 10px 12px;
}
.head {
  margin-bottom: 8px;
}
.body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.bubble {
  background: rgba(30, 60, 110, 0.35);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 8px 10px;
  font-size: 12px;
  line-height: 1.5;
}
.wide {
  width: 100%;
}
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 14, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.modal {
  width: 560px;
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
.step {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.opts {
  display: flex;
  gap: 10px;
}
.opt {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-align: left;
  padding: 10px;
}
.opt span {
  font-size: 11px;
}
.opt-line {
  display: block;
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
}
.opt-line.on {
  border-color: var(--accent);
  background: rgba(40, 110, 200, 0.25);
}
.custom {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.grid label,
.region,
.st {
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 11px;
  color: var(--text-dim);
}
.region-inputs {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 1fr;
  gap: 5px;
}
.err {
  color: var(--danger);
  font-size: 12px;
}
.st-result {
  font-size: 12px;
  padding: 8px;
  border-radius: 8px;
  border: 1px solid var(--border);
}
.st-result.ok {
  background: rgba(40, 160, 120, 0.2);
  color: var(--ok);
}
.st-result.warn {
  background: rgba(200, 80, 90, 0.18);
  color: var(--danger);
}
.badge {
  margin-left: 6px;
  padding: 1px 6px;
  border-radius: 8px;
  background: rgba(255, 179, 71, 0.25);
  color: var(--warn);
}
</style>
