<template>
  <section class="project-agent" aria-label="小墨项目对话">
    <header class="chat-header">
      <div class="toolbar history-toolbar">
        <el-select :model-value="conversationId" placeholder="历史对话" clearable :disabled="!ready || busy" @change="selectConversation" aria-label="历史对话">
          <el-option v-for="conversation in conversations" :key="conversation.id" :value="conversation.id" :label="conversation.label" />
        </el-select>
        <el-button :disabled="!ready || busy" :icon="Plus" @click="newConversation">新对话</el-button>
        <el-button class="refresh-button" :disabled="!ready || busy" :loading="loading" :icon="Refresh" aria-label="刷新历史对话" title="刷新历史对话" @click="refreshHistory" />
      </div>
    </header>
    <el-alert v-if="!ready" title="请登录并选择有效项目后开始对话" type="warning" :closable="false" />
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <div ref="messageList" class="chat-thread" @scroll="onScroll" aria-label="对话消息" aria-live="polite" :aria-busy="conversationActive">
      <div v-if="!conversationRuns.length && !pendingInstruction" class="welcome">
        <div class="welcome-icon" aria-hidden="true"><el-icon><EditPen /></el-icon></div>
        <span class="welcome-eyebrow">让灵感更进一步</span>
        <h3>这次想一起写些什么？</h3>
        <p>从一个想法，到完整章节。<br />聊聊创作，或一起打磨你的项目。</p>
        <div class="suggestions" aria-label="试试这些创作指令">
          <button v-for="suggestion in suggestions" :key="suggestion.label" type="button" class="suggestion" :disabled="!ready || mutating" @click="useSuggestion(suggestion.instruction)">
            <el-icon aria-hidden="true"><component :is="suggestion.icon" /></el-icon>
            <span><strong>{{ suggestion.label }}</strong><small>{{ suggestion.description }}</small></span>
            <el-icon class="suggestion-arrow" aria-hidden="true"><ArrowRight /></el-icon>
          </button>
        </div>
        <p class="welcome-note">先聊想法，修改内容会在你确认后保存。</p>
      </div>
      <article v-for="run in conversationRuns" :key="run.id" class="chat-turn">
        <div class="user-message"><span class="speaker">你</span><p class="plain-text">{{ run.instruction }}</p></div>
        <div class="assistant-message">
          <span class="speaker">小墨</span>
          <p v-for="(text, index) in assistantMessages(run)" :key="index" class="plain-text assistant-text">{{ text }}</p>
          <div v-if="isActive(run)" class="activity"><span class="activity-dot" />{{ run.events[run.events.length - 1]?.message || (run.status === 'queued' ? '正在准备…' : '正在思考…') }}</div>
          <p v-else-if="!assistantMessages(run).length" class="muted">{{ statusLabel(run.status) }}</p>
          <p v-if="run.error" class="run-error plain-text">{{ run.error }}</p>
          <details v-if="run.events.length" class="process"><summary>查看处理过程 · {{ statusLabel(run.status) }}</summary>
            <ol class="events"><li v-for="event in run.events" :key="event.sequence"><p class="plain-text">{{ event.message }}</p></li></ol>
          </details>
          <div v-if="run.changes.length" class="proposal">
            <strong>{{ run.status === 'applied' ? '已保存到项目' : run.status === 'reverted' ? '本次修改已撤销' : '修改预览（尚未保存）' }} · {{ run.changes.length }} 项</strong>
            <details v-for="change in run.changes" :key="change.id" class="change">
              <summary>{{ change.title }}</summary>
              <p class="plain-text muted">{{ change.reason }}</p>
              <div class="previews"><div><h4>修改前</h4><pre>{{ preview(change.before) }}</pre></div><div><h4>修改后</h4><pre>{{ preview(change.after) }}</pre></div></div>
            </details>
          </div>
          <div class="toolbar response-actions">
            <el-button v-if="isActive(run)" size="small" :disabled="busy" @click="performAction('cancel', run)">停止</el-button>
            <el-button v-if="['failed', 'cancelled'].includes(run.status)" size="small" :disabled="busy" @click="performAction('resume', run)">重新尝试</el-button>
            <el-button v-if="run.status === 'proposed' && run.changes.length" size="small" type="primary" :disabled="busy || conversationActive" @click="performAction('apply', run)">确认修改并保存</el-button>
            <el-button v-if="run.status === 'applied'" size="small" :disabled="busy || conversationActive" @click="performAction('revert', run)">撤销这次修改</el-button>
          </div>
        </div>
      </article>
      <div v-if="pendingInstruction" class="chat-turn"><div class="user-message"><span class="speaker">你</span><p class="plain-text">{{ pendingInstruction }}</p></div><p class="muted">正在发送…</p></div>
    </div>
    <div class="composer">
      <el-input ref="composerInput" v-model="instruction" type="textarea" :autosize="{ minRows: 2, maxRows: 6 }" :disabled="!ready || mutating" maxlength="12000" placeholder="和小墨聊聊，或者告诉我想修改什么…" aria-label="消息输入" @keydown="composerKeydown" />
      <div class="composer-footer"><span class="muted">{{ conversationActive ? '小墨正在处理，你可以先写下下一条消息' : 'Enter 发送 · Shift + Enter 换行' }}</span><el-button type="primary" :loading="mutating || preparing" :disabled="!ready || busy || preparing || !instruction.trim() || conversationActive" @click="submit">发送</el-button></div>
      <div class="muted safety-note">修改项目需确认；关闭窗口不会停止后台处理。</div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { assistantMessages, readablePreview } from '@/utils/agentChat'
import { isAxiosError } from 'axios'
import { ElMessageBox, type InputInstance } from 'element-plus'
import { ArrowRight, Document, EditPen, List, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { projectAgentApi, type ProjectAgentRun, type ProjectAgentStatus, type ProjectAgentAction } from '@/api/project-agent'

const props = defineProps<{ projectId: number; beforeSubmit?: () => Promise<boolean> }>()
const emit = defineEmits<{ changed: []; activityChanged: [active: boolean] }>()
const auth = useAuthStore()
const runs = ref<ProjectAgentRun[]>([])
const selectedId = ref('')
const conversationId = ref('')
const instruction = ref('')
const error = ref('')
const loading = ref(false)
const mutating = ref(false)
const preparing = ref(false)
const busy = computed(() => loading.value || mutating.value)
const validProject = computed(() => Number.isInteger(props.projectId) && props.projectId > 0)
const ready = computed(() => validProject.value && !!auth.token)
const selected = computed(() => runs.value.find(run => run.id === selectedId.value))
const conversationRuns = computed(() => runs.value.filter(run => run.conversation_id === conversationId.value).sort((a, b) => a.created_at.localeCompare(b.created_at)))
const conversationActive = computed(() => conversationRuns.value.some(isActive))
const conversations = computed(() => {
  const seen = new Set<string>()
  return [...runs.value].sort((a, b) => a.created_at.localeCompare(b.created_at)).flatMap(run => {
    if (seen.has(run.conversation_id)) return []
    seen.add(run.conversation_id)
    return [{ id: run.conversation_id, label: run.instruction.slice(0, 80) }]
  })
})
const labels: Record<ProjectAgentStatus, string> = {
  queued: '排队中', running: '执行中', proposed: '待审批（未保存）', completed: '任务完成',
  failed: '执行失败', cancelled: '已取消', applied: '已保存', reverted: '已撤销'
}
const statusLabel = (status: ProjectAgentStatus) => labels[status] || status
const isActive = (run: ProjectAgentRun) => run.status === 'queued' || run.status === 'running'
watch(() => runs.value.some(isActive), active => emit('activityChanged', active), { immediate: true })
const preview = readablePreview
const composerInput = ref<InputInstance>()
const suggestions = [
  { label: '阅读项目摘要', description: '梳理故事脉络与当前进展', icon: Document, instruction: '请阅读当前项目，梳理故事设定、主要人物和章节进展，给我一份简明摘要。' },
  { label: '检查设定一致性', description: '找出人物、时间线与情节矛盾', icon: Search, instruction: '请检查当前项目的人物设定、时间线和情节是否一致，指出潜在矛盾并给出修改建议。' },
  { label: '拆分与扩写章节', description: '细化章节节奏，展开关键情节', icon: List, instruction: '请阅读当前项目，建议哪些章节适合拆分或扩写，先给我章节规划和扩写思路。' }
]
async function focusComposer() {
  await nextTick()
  composerInput.value?.focus()
}
function useSuggestion(text: string) {
  if (!ready.value || mutating.value) return
  instruction.value = text
  void focusComposer()
}
async function scrollToBottom() {
  followBottom.value = true
  await nextTick()
  const el = messageList.value
  if (el) el.scrollTop = el.scrollHeight
}
defineExpose({ focusComposer, scrollToBottom })
const messageList = ref<HTMLElement>()
const pendingInstruction = ref('')
const followBottom = ref(true)
function onScroll() {
  const el = messageList.value
  if (el) followBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 100
}
watch(() => [JSON.stringify(conversationRuns.value), pendingInstruction.value], async () => {
  if (!followBottom.value) return
  await nextTick()
  const el = messageList.value
  if (el && followBottom.value) el.scrollTop = el.scrollHeight
})
function composerKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault()
    void submit()
  }
}
function message(cause: unknown): string {
  if (isAxiosError(cause)) {
    if (cause.response?.status === 401) return '登录已过期，请重新登录。'
    if (cause.response?.status === 403) return '没有访问当前项目的权限。'
    const detail: unknown = cause.response?.data?.detail
    if (typeof detail === 'string') return detail
  }
  return '请求失败，请检查网络或项目权限。操作可能已被服务器接收，请先刷新历史确认状态，不要重复提交。'
}

let generation = 0
let historyLoaded = false
let pollGeneration = 0
let disposed = false
let timer: ReturnType<typeof setTimeout> | undefined
let request: AbortController | undefined
let polling: AbortController | undefined
function stopPolling() {
  pollGeneration++
  if (timer) clearTimeout(timer)
  timer = undefined
  polling?.abort()
  polling = undefined
}
function upsert(run: ProjectAgentRun) {
  runs.value = [run, ...runs.value.filter(item => item.id !== run.id)]
}
function reconcileHistory(history: ProjectAgentRun[]) {
  const projectChanged = history.some(run => {
    const previous = runs.value.find(item => item.id === run.id)
    return previous && (run.status === 'applied' || run.status === 'reverted') && previous.status !== run.status
  })
  runs.value = history
  if (projectChanged) emit('changed')
}
function schedulePolling() {
  stopPolling()
  const active = selected.value && isActive(selected.value) ? selected.value : runs.value.find(isActive)
  if (disposed || document.hidden || !ready.value || busy.value || !active) return
  const context = generation
  const epoch = pollGeneration
  const id = active.id
  const project = props.projectId
  timer = setTimeout(async () => {
    const controller = new AbortController()
    polling = controller
    try {
      const history = await projectAgentApi.list(project, controller.signal)
      const run = await projectAgentApi.get(project, id, controller.signal)
      if (context !== generation || epoch !== pollGeneration || disposed) return
      reconcileHistory([run, ...history.filter(item => item.id !== run.id)])
      error.value = ''
      schedulePolling()
    } catch (cause) {
      if (context === generation && epoch === pollGeneration && !controller.signal.aborted) {
        error.value = `${message(cause)} 自动刷新已暂停，请手动刷新。`
      }
    }
  }, 2000)
}
async function refreshHistory() {
  if (!ready.value || busy.value || disposed) return
  stopPolling()
  const context = generation
  const controller = new AbortController()
  request = controller
  loading.value = true
  error.value = ''
  let succeeded = false
  try {
    const history = await projectAgentApi.list(props.projectId, controller.signal)
    if (context !== generation || disposed) return
    reconcileHistory(history)
    if (!historyLoaded && !selectedId.value && !conversationId.value && history.length) {
      const latest = [...history].sort((a, b) => b.created_at.localeCompare(a.created_at))[0]
      selectedId.value = latest.id
      conversationId.value = latest.conversation_id
    }
    historyLoaded = true
    succeeded = true
  } catch (cause) {
    if (context === generation && !controller.signal.aborted) error.value = message(cause)
  } finally {
    if (context === generation && !disposed) {
      loading.value = false
      if (succeeded) schedulePolling()
    }
  }
}
function selectRun(id: string) {
  if (busy.value) return
  stopPolling()
  selectedId.value = id
  error.value = ''
  schedulePolling()
}
function selectConversation(value: string | undefined) {
  if (busy.value) return
  followBottom.value = true
  conversationId.value = value || ''
  instruction.value = ''
  selectRun(conversationRuns.value[conversationRuns.value.length - 1]?.id || '')
}
function newConversation() {
  selectConversation('')
}
async function submit() {
  if (disposed || preparing.value || !ready.value || busy.value || !instruction.value.trim() || conversationActive.value) return
  const context = generation
  const draft = instruction.value
  const conversation = conversationId.value || undefined
  const text = draft.trim()
  preparing.value = true
  try {
    const prepared = await props.beforeSubmit?.()
    if (prepared === false || context !== generation || disposed || !ready.value || busy.value || conversationActive.value) return
    // Do not send a different conversation or edits made while saving.
    if ((conversationId.value || undefined) !== conversation || instruction.value !== draft) return
    pendingInstruction.value = text
    followBottom.value = true
    await mutate((project, signal) => projectAgentApi.create(project, text, conversation, signal), true)
  } catch {
    if (context === generation && !disposed) error.value = '发送前保存未完成，请检查当前文档后重试。'
  } finally {
    preparing.value = false
    if (context === generation && !disposed) pendingInstruction.value = ''
  }
}
async function performAction(action: ProjectAgentAction, target?: ProjectAgentRun) {
  const run = target || selected.value
  if (!ready.value || busy.value || !run) return
  await mutate(async (project, signal) => {
    if (action === 'apply' || action === 'revert') {
      try {
        await ElMessageBox.confirm(
          action === 'apply' ? `批准全部 ${run.changes.length} 项变更并写入当前项目？请先检查每项预览。` : '撤销本次已保存的全部变更？这将修改实际项目内容。',
          action === 'apply' ? '确认保存到项目' : '确认撤销变更',
          { type: 'warning', confirmButtonText: action === 'apply' ? '批准全部并保存' : '确认撤销', cancelButtonText: '返回预览', closeOnClickModal: false }
        )
      } catch { return undefined }
    }
    if (signal.aborted || disposed) return undefined
    return projectAgentApi.action(project, run.id, action, signal)
  }, false, action)
}
async function mutate(operation: (project: number, signal: AbortSignal) => Promise<ProjectAgentRun | undefined>, creating: boolean, action?: ProjectAgentAction) {
  stopPolling()
  const context = generation
  const controller = new AbortController()
  request = controller
  mutating.value = true
  error.value = ''
  let succeeded = false
  try {
    const run = await operation(props.projectId, controller.signal)
    if (context !== generation || disposed) return
    // Dismissing a confirmation is not a network failure: restore polling.
    succeeded = true
    if (!run) return
    upsert(run)
    selectedId.value = run.id
    conversationId.value = run.conversation_id
    if (creating) instruction.value = ''
    if ((action === 'apply' && run.status === 'applied') || (action === 'revert' && run.status === 'reverted')) emit('changed')
    succeeded = true
  } catch (cause) {
    if (context === generation && !controller.signal.aborted) error.value = message(cause)
  } finally {
    if (context === generation && !disposed) {
      mutating.value = false
      if (succeeded) schedulePolling()
    }
  }
}
function visibilityChanged() {
  if (document.hidden) stopPolling()
  else if (!busy.value) void refreshHistory()
}
watch(() => [props.projectId, auth.token] as const, () => {
  generation++
  historyLoaded = false
  stopPolling()
  request?.abort()
  runs.value = []
  selectedId.value = ''
  conversationId.value = ''
  instruction.value = ''
  pendingInstruction.value = ''
  followBottom.value = true
  error.value = ''
  loading.value = false
  mutating.value = false
  if (ready.value) void refreshHistory()
}, { immediate: true })
document.addEventListener('visibilitychange', visibilityChanged)
onBeforeUnmount(() => {
  disposed = true
  generation++
  stopPolling()
  request?.abort()
  document.removeEventListener('visibilitychange', visibilityChanged)
})
</script>

<style scoped lang="scss">
.project-agent {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  color: var(--coffee-text);
  background: var(--coffee-bg-card);
  font-size: 14px;
  container-type: inline-size;
}
.chat-header {
  flex-shrink: 0;
  padding: 12px 16px;
  border-bottom: 1px solid var(--coffee-border);
  background: var(--coffee-bg-warm);
}
.toolbar { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
.toolbar :deep(.el-button + .el-button) { margin-left: 0; }
.history-toolbar { flex-wrap: nowrap; }
.history-toolbar .el-select { flex: 1; min-width: 0; width: 0; }
.history-toolbar .el-button { flex-shrink: 0; border-radius: 8px; }
.refresh-button { width: 32px; padding: 0; }
.project-agent > .el-alert { flex-shrink: 0; width: auto; margin: 10px 16px 0; border-radius: 8px; }
.chat-thread {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 20px 18px;
  overscroll-behavior: contain;
  scrollbar-width: thin;
  scrollbar-color: var(--coffee-border) transparent;
}
.welcome { max-width: 360px; margin: 0 auto; padding: 12px 0 8px; text-align: center; line-height: 1.7; }
.welcome-icon {
  display: grid;
  place-items: center;
  width: 56px;
  height: 56px;
  margin: 0 auto 14px;
  border: 1px solid color-mix(in srgb, var(--coffee-primary) 20%, var(--coffee-border));
  border-radius: 18px;
  background: linear-gradient(145deg, var(--coffee-bg-warm), var(--coffee-bg-card));
  color: var(--coffee-primary);
  box-shadow: 0 6px 18px color-mix(in srgb, var(--coffee-primary) 8%, transparent);
  font-size: 27px;
}
.welcome-eyebrow { color: var(--coffee-primary); font-size: 11px; font-weight: 600; letter-spacing: 2px; }
.welcome h3 { margin: 7px 0 8px; font-size: 19px; font-weight: 650; letter-spacing: -.3px; }
.welcome > p { margin: 0; color: var(--coffee-text-muted); font-size: 13px; }
.suggestions { display: grid; gap: 8px; margin-top: 22px; }
.suggestion {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--coffee-border);
  border-radius: 12px;
  background: var(--coffee-bg-card);
  color: var(--coffee-text);
  text-align: left;
  font: inherit;
  cursor: pointer;
  transition: border-color .18s ease, background .18s ease;
}
.suggestion > .el-icon:first-child { flex-shrink: 0; color: var(--coffee-primary); font-size: 19px; }
.suggestion > span { flex: 1; min-width: 0; }
.suggestion strong { display: block; font-size: 13px; font-weight: 600; line-height: 1.6; }
.suggestion small { display: block; margin-top: 2px; font-size: 11px; line-height: 1.6; }
.suggestion-arrow { color: var(--coffee-text-muted); font-size: 12px; }
.suggestion:hover:not(:disabled) { border-color: var(--coffee-primary); background: var(--coffee-bg-warm); }
.suggestion:focus-visible, summary:focus-visible { outline: 2px solid var(--coffee-primary); outline-offset: 3px; }
.suggestion:disabled { opacity: .55; cursor: not-allowed; }
.welcome > .welcome-note { margin-top: 16px; font-size: 11px; }
.chat-turn { min-width: 0; margin-bottom: 26px; }
.chat-turn:last-child { margin-bottom: 0; }
.user-message {
  width: fit-content;
  max-width: 88%;
  margin-left: auto;
  padding: 11px 14px;
  border: 1px solid color-mix(in srgb, var(--coffee-primary) 12%, var(--coffee-border));
  border-radius: 14px 14px 4px 14px;
  background: var(--coffee-bg-warm);
}
.user-message p { margin: 5px 0 0; }
.speaker { font-size: 11px; font-weight: 600; color: var(--coffee-text-muted); }
.assistant-message { min-width: 0; padding-top: 18px; }
.assistant-message > .speaker { display: flex; align-items: center; gap: 7px; color: var(--coffee-primary); }
.assistant-message > .speaker::before { content: ''; width: 5px; height: 14px; border-radius: 3px; background: var(--coffee-primary); }
.assistant-text { margin: 10px 0; }
.activity { display: flex; align-items: baseline; gap: 8px; margin: 12px 0; color: var(--coffee-text-muted); font-size: 12px; overflow-wrap: anywhere; line-height: 1.7; }
.activity-dot { flex-shrink: 0; height: 6px; width: 6px; border-radius: 50%; background: var(--coffee-primary); box-shadow: 0 0 0 3px color-mix(in srgb, var(--coffee-primary) 12%, transparent); }
.process { margin: 12px 0; padding: 10px 12px; border-radius: 8px; background: var(--coffee-bg-warm); font-size: 12px; color: var(--coffee-text-muted); }
.proposal { margin-top: 14px; padding: 12px; border: 1px solid var(--coffee-border); border-radius: 12px; }
.proposal > strong { display: block; color: var(--coffee-primary); font-size: 13px; line-height: 1.7; }
.response-actions { margin-top: 12px; }
.response-actions:empty { display: none; }
.response-actions .el-button { max-width: 100%; height: auto; min-height: 28px; white-space: normal; }
.run-error { color: var(--el-color-danger); font-size: 13px; }
.composer { flex-shrink: 0; padding: 14px 16px 12px; border-top: 1px solid var(--coffee-border); background: var(--coffee-bg-card); }
.composer :deep(.el-textarea__inner) { padding: 11px 12px; border-radius: 12px; background: var(--coffee-bg-warm); color: var(--coffee-text); box-shadow: 0 0 0 1px var(--coffee-border) inset; font-family: inherit; font-size: 13px; line-height: 1.7; resize: none; }
.composer :deep(.el-textarea__inner:focus) { box-shadow: 0 0 0 1px var(--coffee-primary) inset; }
.composer-footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 10px; }
.composer-footer > .muted { font-size: 11px; line-height: 1.6; }
.composer-footer > .el-button { flex-shrink: 0; min-width: 66px; border-radius: 9px; }
.safety-note { margin-top: 9px; text-align: center; font-size: 10px; line-height: 1.6; }
h4 { font-size: 12px; margin: 8px 0; color: var(--coffee-text-muted); }
.muted, small { color: var(--coffee-text-muted); font-size: 13px; }
.plain-text { white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.8; }
.events { max-height: 240px; overflow: auto; padding-left: 20px; }
.events p { margin: 4px 0 12px; }
.change { padding-top: 12px; margin-top: 12px; border-top: 1px solid var(--coffee-border); font-size: 13px; }
summary { cursor: pointer; font-weight: 500; overflow-wrap: anywhere; line-height: 1.7; }
.previews { display: grid; grid-template-columns: minmax(0, 1fr); gap: 4px; }
.previews > div { min-width: 0; }
pre { max-height: 240px; overflow: auto; margin: 6px 0; padding: 10px; border-radius: 8px; background: var(--coffee-bg-warm); white-space: pre-wrap; overflow-wrap: anywhere; font-size: 12px; line-height: 1.7; }
@container (max-width: 360px) {
  .chat-header { padding: 10px 12px; }
  .chat-thread { padding: 16px 12px; }
  .composer { padding: 12px; }
  .history-toolbar { gap: 6px; }
  .history-toolbar > .el-button:not(.refresh-button) { padding: 8px; }
  .welcome h3 { font-size: 17px; }
  .suggestion { padding: 10px; gap: 9px; }
}
@media (prefers-reduced-motion: reduce) { .suggestion { transition: none; } }
</style>
