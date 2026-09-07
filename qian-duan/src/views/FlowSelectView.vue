<template>
  <div class="flow-page">
    <!-- 顶部工具条 -->
    <div class="top-bar">
      <span class="top-hint">质量流量窗口选型 · 表单 / 对话输入均可，出结果后右侧展示摘要与排行</span>
      <el-radio-group v-model="mode" size="small">
        <el-radio-button label="form">表单填写</el-radio-button>
        <el-radio-button label="chat">对话输入</el-radio-button>
      </el-radio-group>
    </div>

    <el-alert v-if="error" type="error" :title="error" :closable="false" class="res-error" />

    <!-- 三栏工作区 -->
    <div class="work-area">
      <!-- ========== 左列：输入（表单参数 / 对话框） ========== -->
      <aside class="left-col">
        <!-- 表单填写 -->
        <el-card v-if="mode === 'form'" shadow="never" class="form-card">
          <template #header>表单填写</template>
          <el-form label-position="top" size="small" class="flow-form">
            <el-form-item label="设备类型">
              <el-select v-model="form.device_type" clearable placeholder="全部类型">
                <el-option v-for="t in deviceTypes" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>
            <el-form-item label="制冷剂">
              <el-input v-model="form.refrigerant" placeholder="R410A" />
            </el-form-item>
            <el-form-item label="冷凝温度 ℃">
              <el-input-number v-model="form.cond_temp" :controls="false" style="width: 100%" />
            </el-form-item>
            <el-form-item label="蒸发温度 ℃">
              <el-input-number v-model="form.evap_temp" :controls="false" style="width: 100%" />
            </el-form-item>
            <el-form-item label="过冷度 K">
              <el-input-number v-model="form.subcooling" :controls="false" style="width: 100%" />
            </el-form-item>
            <el-form-item label="过热度 K">
              <el-input-number v-model="form.superheat" :controls="false" style="width: 100%" />
            </el-form-item>
            <el-form-item label="允许压降 MPa（可空）">
              <el-input-number v-model="form.delta_pressure" :controls="false" style="width: 100%" />
            </el-form-item>
            <el-form-item label="需求制冷量 kW">
              <el-input-number v-model="form.required_capacity" :controls="false" style="width: 100%" />
            </el-form-item>
          </el-form>
          <el-button type="primary" :loading="loading" class="run-btn" @click="runForm">开始选型</el-button>
        </el-card>

        <!-- 对话框 -->
        <div v-else class="chat-col">
          <div class="chat-head">
            <span class="tool-title">对话选型</span>
            <el-button size="small" text type="primary" @click="newChat">新对话</el-button>
          </div>
          <div ref="chatListRef" class="chat-list">
            <template v-for="(m, i) in msgs" :key="'m' + i">
              <div v-if="m.role === 'user'" class="msg-row user">
                <div class="msg-bubble user-bubble">{{ m.text }}</div>
              </div>
              <div v-else class="msg-row assistant">
                <div class="msg-bubble ai-bubble">
                  <template v-if="m.kind === 'report'">
                    <div class="markdown-body" v-html="renderMarkdown(m.text)"></div>
                    <div class="ai-export">
                      <el-button size="small" type="primary" plain @click="exportLast">导出报告</el-button>
                    </div>
                  </template>
                  <template v-else-if="m.kind === 'error'">
                    <span class="err-text">{{ m.text }}</span>
                  </template>
                  <template v-else>{{ m.text }}</template>
                </div>
              </div>
            </template>
            <div v-if="chatBusy" class="msg-row assistant">
              <div class="msg-bubble ai-bubble busy">正在解析并选型…</div>
            </div>
          </div>
          <div class="chat-input">
            <el-input
              v-model="draft"
              type="textarea"
              :rows="2"
              resize="none"
              placeholder="描述需求，例如：R410A 冷凝45℃ 蒸发5℃ 过冷度5K 过热度5K 允许压降0.5MPa 制冷量20kW"
              :disabled="chatBusy"
              @keydown.enter.exact.prevent="sendChat"
            />
            <el-button type="primary" :loading="chatBusy" :disabled="!draft.trim()" @click="sendChat">发送</el-button>
          </div>
        </div>
      </aside>

      <!-- ========== 右列：需求摘要 + 筛选排行 ========== -->
      <section class="right-col">
        <template v-if="result">
          <!-- 右上：需求摘要（内部可滑动） -->
          <div class="summary-pane">
            <div class="pane-title">
              需求摘要
              <el-tag size="small" type="info">{{ mode === 'chat' ? '对话输入' : '表单输入' }}</el-tag>
            </div>
            <div class="summary-items">
              <div class="demand-item"><span>制冷剂</span><b>{{ demand.refrigerant || '—' }}</b></div>
              <div class="demand-item"><span>单位焓差</span><b>{{ demand.delta_h || '—' }} kJ/kg</b></div>
              <div class="demand-item"><span>阀前液密度</span><b>{{ demand.rho_liq || '—' }} kg/m³</b></div>
              <div class="demand-item strong"><span>需求质量流量 m_req</span><b>{{ fmtM(demand.m_req) }} kg/h</b></div>
              <div class="demand-item"><span>候选 / 参与 / 达标</span>
                <b>{{ result.candidate_total || count.total }} / {{ count.scored }} / {{ count.passed }}</b></div>
            </div>
          </div>

          <!-- 右下：筛选 + 排行（内部可滑动） -->
          <div class="list-pane">
            <div class="list-head">
              <el-radio-group v-model="filter" size="small">
                <el-radio-button label="all">全部（{{ count.all }}）</el-radio-button>
                <el-radio-button label="passed">达标（{{ count.passed }}）</el-radio-button>
                <el-radio-button label="failed">未达标（{{ count.failed }}）</el-radio-button>
                <el-radio-button label="skipped">跳过（{{ count.skipped }}）</el-radio-button>
              </el-radio-group>
            </div>
            <div v-if="visibleResults.length" class="result-list">
              <div v-for="(r, i) in visibleResults" :key="i" class="flow-card" :class="cardClass(r)">
                <div class="fc-head">
                  <span class="fc-rank">{{ r.skipped ? '—' : rankOf(r) }}</span>
                  <span class="fc-model">{{ r.model }}</span>
                  <el-tag v-if="r.device_type" size="small" effect="plain">{{ r.device_type }}</el-tag>
                  <el-tag v-if="r.series" size="small" effect="plain" type="info">{{ r.series }}</el-tag>
                  <span class="fc-status">
                    <el-tag size="small" :type="r.skipped ? 'info' : r.passed ? 'success' : 'danger'">
                      {{ r.skipped ? '跳过' : r.passed ? '达标' : '不达标' }}
                    </el-tag>
                  </span>
                </div>
                <div v-if="r.skipped" class="fc-reason">{{ r.reason }}</div>
                <div v-else-if="r.kind === 'capacity'" class="cap-body">
                  <div class="fc-body">
                    <div class="fc-metric"><span>{{ r.cap_label || '换向容量' }}</span><b>{{ r.cap_kw }} kW</b></div>
                    <div class="fc-metric"><span>需求制冷量</span><b>{{ fmtM(r.req_kw) }} kW</b></div>
                    <div class="fc-metric"><span>容量比 ratio</span><b>{{ (r.ratio * 100).toFixed(0) }}%</b></div>
                    <div class="fc-metric"><span>{{ r.dp_label || '换向压降' }}</span><b>{{ r.dp_bar }} bar</b></div>
                  </div>
                  <div v-if="r.passed" class="fc-pass-note">✓ 换向容量满足需求（≥60%）</div>
                  <div v-else class="fc-reason">{{ r.reason }}</div>
                </div>
                <template v-else>
                  <div class="fc-body">
                    <div class="fc-metric"><span>Kv</span><b>{{ r.kv }}</b></div>
                    <div class="fc-metric"><span>压降边界</span><b>{{ dpFmt(r) }}</b></div>
                    <div class="fc-metric"><span>允许质量流量</span><b>{{ winFmt(r) }}</b></div>
                    <div class="fc-metric"><span>m_req</span><b>{{ fmtM(r.m_req) }}</b></div>
                  </div>
                  <div v-if="r.passed && r.pos != null" class="fc-bar-wrap">
                    <div class="fc-bar"><div class="fc-bar-fill" :style="{ width: (r.pos * 100).toFixed(1) + '%' }"></div></div>
                    <span class="fc-bar-note">m_req 在窗口 {{ (r.pos * 100).toFixed(0) }}% 处</span>
                  </div>
                  <div v-else-if="r.passed" class="fc-pass-note">✓ 需求在设备压降边界内达标</div>
                  <div v-else class="fc-reason">{{ r.reason }}</div>
                </template>
              </div>
            </div>
            <el-empty v-else description="当前筛选无结果" :image-size="60" />
          </div>
        </template>

        <!-- 尚未选型：引导 -->
        <div v-else class="right-empty">
          <el-empty :description="mode === 'chat' ? '在左侧对话中输入需求开始选型' : '在左侧填写参数后点「开始选型」'" />
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick, watch } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { ElMessage } from 'element-plus'

const deviceTypes = ['四通换向阀', '电子膨胀阀', '热力膨胀阀', '电磁阀', '干燥过滤器', '压力调节阀', '单向阀', '球阀', '电子截断阀', '电动球阀']

const mode = ref('chat')

// ---------- 表单输入 ----------
const form = reactive({
  device_type: '', refrigerant: 'R410A', cond_temp: 45, evap_temp: 5,
  subcooling: 5, superheat: 5, delta_pressure: 0.5, required_capacity: 20,
})
const loading = ref(false)

// ---------- 共享结果 ----------
const error = ref('')
const result = ref(null)
const filter = ref('passed')

const demand = computed(() => result.value?.demand || {})
const results = computed(() => result.value?.results || [])
const count = computed(() => {
  const rs = results.value
  return {
    total: result.value?.candidate_total ?? rs.length,
    scored: rs.filter((r) => !r.skipped).length,
    passed: rs.filter((r) => r.passed).length,
    failed: rs.filter((r) => !r.passed && !r.skipped).length,
    skipped: rs.filter((r) => r.skipped).length,
    all: rs.length,
  }
})
const visibleResults = computed(() => {
  if (filter.value === 'all') return results.value
  if (filter.value === 'skipped') return results.value.filter((r) => r.skipped)
  return results.value.filter((r) => !r.skipped && (filter.value === 'passed' ? r.passed : !r.passed))
})

function cardClass(r) {
  if (r.skipped) return 'card-skip'
  return r.passed ? 'card-pass' : 'card-fail'
}
function rankOf(r) {
  const idx = results.value.filter((x) => !x.skipped).findIndex((x) => x === r)
  return idx >= 0 ? idx + 1 : '—'
}
function fmtM(v) {
  return v == null ? '—' : Number(v).toFixed(1)
}
function dpFmt(r) {
  const d = r.dp_eff
  if (!d || (d[0] == null && d[1] == null)) return '—'
  if (d[0] == null) return `≤ ${d[1]} MPa`
  if (d[1] == null) return `≥ ${d[0]} MPa`
  return `${d[0]} ~ ${d[1]} MPa`
}
function winFmt(r) {
  if (r.m_min == null && r.m_max == null) return '—'
  if (r.m_min == null) return `≤ ${fmtM(r.m_max)} kg/h`
  if (r.m_max == null) return `≥ ${fmtM(r.m_min)} kg/h`
  return `${fmtM(r.m_min)} ~ ${fmtM(r.m_max)} kg/h`
}
function renderMarkdown(md) {
  return DOMPurify.sanitize(marked.parse(md || ''))
}

// ---------- 表单：选型 ----------
async function runForm() {
  if (loading.value) return
  error.value = ''
  result.value = null
  if (!form.refrigerant?.trim() || form.cond_temp == null || form.evap_temp == null || form.required_capacity == null) {
    ElMessage.warning('请填写 制冷剂 / 冷凝 / 蒸发温度 / 需求制冷量')
    return
  }
  loading.value = true
  try {
    const res = await fetch('/select/flow', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...form }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || `请求失败（HTTP ${res.status}）`)
    }
    result.value = await res.json()
    filter.value = 'passed'
  } catch (e) {
    error.value = e.message || '选型失败'
  } finally {
    loading.value = false
  }
}

// ---------- 对话 ----------
const msgs = ref([])
const draft = ref('')
const chatBusy = ref(false)
const chatListRef = ref(null)
const chatParams = ref({})
const chatHistory = ref([])
const lastReport = ref('')

async function sendChat() {
  const text = draft.value.trim()
  if (!text || chatBusy.value) return
  draft.value = ''
  msgs.value.push({ role: 'user', text })
  chatBusy.value = true
  await scrollBottom()
  try {
    const res = await fetch('/flow/chat', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, history: chatHistory.value, params: chatParams.value }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || `请求失败（HTTP ${res.status}）`)
    }
    const data = await res.json()
    if (data.type === 'clarify') {
      chatParams.value = data.params || chatParams.value
      chatHistory.value = [...chatHistory.value, text]
      msgs.value.push({ role: 'assistant', text: data.question })
    } else if (data.type === 'done') {
      chatParams.value = data.params || chatParams.value
      chatHistory.value = [...chatHistory.value, text]
      result.value = {
        demand: data.demand || {},
        results: data.results || [],
        candidate_total: data.candidate_total,
        passed_count: data.passed_count,
        skipped: data.skipped,
      }
      filter.value = 'passed'
      lastReport.value = data.report || ''
      msgs.value.push({ role: 'assistant', kind: 'report', text: data.report || '', canExport: !!data.report })
    } else if (data.type === 'error') {
      msgs.value.push({ role: 'assistant', kind: 'error', text: data.detail || '处理失败' })
    }
  } catch (e) {
    msgs.value.push({ role: 'assistant', kind: 'error', text: e.message || '网络错误' })
  } finally {
    chatBusy.value = false
    await scrollBottom()
  }
}

function newChat() {
  msgs.value = []
  chatParams.value = {}
  chatHistory.value = []
  lastReport.value = ''
  result.value = null
}

function exportLast() {
  const text = (lastReport.value || '').trim()
  if (!text) return
  const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
  const blob = new Blob(['\uFEFF' + text], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `流量选型报告-${ts}.md`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

async function scrollBottom() {
  await nextTick()
  if (chatListRef.value) chatListRef.value.scrollTop = chatListRef.value.scrollHeight
}
watch(() => msgs.value.length, scrollBottom)
</script>

<style scoped>
/* 页面占满可视区（header≈60 + app-main 上下 padding≈28），内部各自滚动 */
.flow-page {
  height: calc(100vh - 100px);
  min-height: 560px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.top-bar {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.top-hint {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.res-error { flex: none; }

/* 三栏工作区 */
.work-area {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 12px;
}
.left-col {
  flex: 1 1 50%;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.right-col {
  flex: 1 1 50%;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 左：表单卡（内部滚动） */
.form-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.form-card :deep(.el-card__body) {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
.flow-form { display: grid; grid-template-columns: repeat(2, 1fr); gap: 2px 12px; }
.run-btn { width: 100%; margin-top: 12px; }

/* 左：对话 */
.chat-col {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-bg-color);
  padding: 10px;
}
.chat-head { flex: none; display: flex; align-items: center; justify-content: space-between; }
.tool-title { font-size: 14px; font-weight: 600; }
.chat-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 2px;
}
.msg-row { display: flex; }
.msg-row.user { justify-content: flex-end; }
.msg-row.assistant { justify-content: flex-start; }
.msg-bubble {
  max-width: 96%;
  padding: 8px 10px;
  border-radius: 8px;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.6;
}
.user-bubble { background: var(--el-color-primary); color: #fff; }
.ai-bubble { background: var(--el-fill-color-light); color: var(--el-text-color-primary); border: 1px solid var(--el-border-color-lighter); }
.ai-bubble.busy { color: var(--el-text-color-secondary); }
.err-text { color: var(--el-color-danger); }
.ai-export { margin-top: 6px; }
.chat-input { flex: none; display: flex; gap: 8px; align-items: flex-end; }
.chat-input .el-textarea { flex: 1; }

/* 右上：需求摘要（可滑动） */
.summary-pane {
  flex: none;
  max-height: 178px;
  overflow-y: auto;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-bg-color);
  padding: 10px 12px;
}
.pane-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.summary-items { display: flex; flex-wrap: wrap; gap: 10px 26px; }
.demand-item span { font-size: 12px; color: var(--el-text-color-secondary); display: block; }
.demand-item b { font-size: 16px; }
.demand-item.strong b { color: var(--el-color-primary); font-size: 19px; }

/* 右下：筛选 + 排行（列表可滑动） */
.list-pane {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-bg-color);
  padding: 10px 12px;
}
.list-head { flex: none; }
.result-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-right: 2px;
}
.flow-card {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 8px 10px;
  background: var(--el-bg-color-page);
}
.card-pass { border-left: 4px solid var(--el-color-success); }
.card-fail { border-left: 4px solid var(--el-color-danger); }
.card-skip { border-left: 4px solid var(--el-color-info); opacity: .85; }
.fc-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.fc-rank { font-weight: 700; color: var(--el-color-primary); width: 22px; text-align: center; }
.fc-model { font-weight: 700; font-size: 14px; }
.fc-status { margin-left: auto; }
.fc-body { display: flex; flex-wrap: wrap; gap: 6px 24px; margin-top: 6px; }
.fc-metric span { font-size: 11px; color: var(--el-text-color-secondary); display: block; }
.fc-metric b { font-size: 13px; }
.fc-reason { margin-top: 4px; font-size: 12px; color: var(--el-text-color-secondary); }
.fc-pass-note { margin-top: 4px; font-size: 12px; color: var(--el-color-success); }
.fc-bar-wrap { margin-top: 6px; display: flex; align-items: center; gap: 8px; }
.fc-bar { flex: 1; height: 6px; border-radius: 3px; background: var(--el-border-color-lighter); overflow: hidden; }
.fc-bar-fill { height: 100%; background: var(--el-color-success); }
.fc-bar-note { font-size: 11px; color: var(--el-text-color-secondary); white-space: nowrap; }

/* 右列空态 */
.right-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-bg-color);
}
</style>
