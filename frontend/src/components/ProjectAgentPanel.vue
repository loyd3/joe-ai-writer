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
    <el-alert v-if="!ready" title="请登录后与小墨对话（无项目也可智能建项）" type="warning" :closable="false" />
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <div ref="messageList" class="chat-thread" @scroll="onScroll" aria-label="对话消息" aria-live="polite" :aria-busy="conversationActive">
      <div v-if="!conversationRuns.length && !pendingInstruction" class="welcome">
        <div class="welcome-icon" aria-hidden="true"><el-icon><EditPen /></el-icon></div>
        <span class="welcome-eyebrow">智能编辑搭档</span>
        <h3>这次想一起写些什么？</h3>
        <p>{{ welcomeBlurb }}</p>
        <div class="suggestions" aria-label="快捷功能">
          <button
            v-for="item in shortcuts"
            :key="item.label"
            type="button"
            class="suggestion"
            :disabled="!ready || mutating || conversationActive"
            @click="useSuggestion(item.instruction)"
          >
            <span><strong>{{ item.label }}</strong><small>{{ item.description }}</small></span>
            <el-icon class="suggestion-arrow" aria-hidden="true"><ArrowRight /></el-icon>
          </button>
        </div>
        <p class="welcome-note">生成后会自动替换到正文，不满意可一键撤销。</p>
      </div>
      <article v-for="run in conversationRuns" :key="run.id" class="chat-turn">
        <div class="user-message">
          <span class="speaker">你</span>
          <div class="markdown-body user-body" v-html="formatMarkdown(displayInstruction(run.instruction))" />
        </div>
        <div class="assistant-message">
          <span class="speaker">小墨</span>
          <template v-if="isActive(run)">
            <div
              v-for="(text, index) in liveAssistantTexts(run)"
              :key="index"
              class="markdown-body assistant-body"
              v-html="formatMarkdown(text)"
            />
            <div class="activity"><span class="activity-dot" />{{ run.status === 'queued' ? '正在准备…' : '正在处理…' }}</div>
          </template>
          <template v-else>
            <details v-if="turnOf(run).thinking.length" class="thinking">
              <summary>思考过程 · {{ thinkingSummary(turnOf(run).thinking) }}</summary>
              <div
                v-for="(text, index) in turnOf(run).thinking"
                :key="index"
                class="markdown-body thinking-step"
                v-html="formatMarkdown(text)"
              />
            </details>
            <div
              v-if="turnOf(run).final"
              class="markdown-body assistant-body"
              v-html="formatMarkdown(turnOf(run).final)"
            />
            <p v-else-if="!run.error" class="muted">{{ statusLabel(run.status) }}</p>
          </template>
          <p v-if="run.error" class="run-error plain-text">{{ run.error }}</p>
          <div v-if="run.changes.length" class="proposal" :class="{ applied: run.status === 'applied', reverted: run.status === 'reverted' }">
            <strong>{{ changesHeadline(run) }}</strong>
            <details
              v-for="change in run.changes"
              :key="change.id"
              class="change"
              :open="run.status === 'applied' || run.status === 'proposed'"
            >
              <summary>{{ change.title }}</summary>
              <p v-if="change.reason" class="plain-text muted">{{ change.reason }}</p>
              <div class="previews">
                <div class="after-block">
                  <h4>{{ afterLabel(run.status) }}</h4>
                  <pre>{{ preview(change.after) }}</pre>
                </div>
                <div class="before-block">
                  <h4>{{ run.status === 'reverted' ? '已恢复原文' : '原文' }}</h4>
                  <pre>{{ preview(change.before) }}</pre>
                </div>
              </div>
            </details>
          </div>
          <div class="toolbar response-actions">
            <el-button v-if="isActive(run)" size="small" :disabled="busy" @click="performAction('cancel', run)">停止</el-button>
            <el-button v-if="['failed', 'cancelled'].includes(run.status)" size="small" :disabled="busy" @click="performAction('resume', run)">重新尝试</el-button>
            <el-button v-if="run.status === 'proposed' && run.changes.length" size="small" type="primary" :disabled="busy || conversationActive" @click="performAction('apply', run)">确认写入</el-button>
            <el-button v-if="run.status === 'applied'" size="small" type="warning" plain :disabled="busy || conversationActive" @click="performAction('revert', run)">撤销替换</el-button>
          </div>
        </div>
      </article>
      <div v-if="pendingInstruction" class="chat-turn">
        <div class="user-message">
          <span class="speaker">你</span>
          <div class="markdown-body user-body" v-html="formatMarkdown(displayInstruction(pendingInstruction))" />
        </div>
        <p class="muted">正在发送…</p>
      </div>
    </div>
    <div class="composer">
      <div v-if="attachedContext" class="attached-context">
        <div class="attached-head">
          <span>{{ attachedLabel }}</span>
          <button type="button" class="attached-clear" title="清除引用" @click="attachedContext = null">×</button>
        </div>
        <p class="attached-preview plain-text">{{ attachedPreview }}</p>
      </div>
      <div
        v-if="composerShortcuts.length && (conversationRuns.length || pendingInstruction)"
        class="shortcut-chips"
        aria-label="快捷功能"
      >
        <button
          v-for="item in composerShortcuts"
          :key="item.key"
          type="button"
          class="shortcut-chip"
          :disabled="!ready || mutating || conversationActive || preparing"
          :title="item.description"
          @click="useSuggestion(item.instruction)"
        >
          {{ item.label }}
        </button>
      </div>
      <el-input ref="composerInput" v-model="instruction" type="textarea" :autosize="{ minRows: 2, maxRows: 6 }" :disabled="!ready || mutating" maxlength="12000" :placeholder="composerPlaceholder" aria-label="消息输入" @keydown="composerKeydown" />
      <div class="composer-footer"><span class="muted">{{ footerHint }}</span><el-button type="primary" :loading="mutating || preparing" :disabled="!ready || busy || preparing || !instruction.trim() || conversationActive" @click="submit">发送</el-button></div>
      <div class="muted safety-note">小墨会自动把改稿写入正文并展示替换内容；可用「撤销替换」还原。关闭窗口不会停止后台任务。</div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import {
  assistantMessages,
  assistantTurnDisplay,
  readablePreview,
  extractAgentSystemNotes,
  mergeAgentSystemNotes,
  stripAgentSystemNotes,
  thinkingSummary,
} from '@/utils/agentChat'
import { isAxiosError } from 'axios'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { ElMessage, ElMessageBox, type InputInstance } from 'element-plus'
import { ArrowRight, EditPen, Plus, Refresh } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useXiaoMoStore } from '@/stores/xiaoMo'
import {
  actionToInstruction,
  DOCUMENT_AI_SHORTCUTS,
  documentToolInstruction,
  PROJECT_WRITING_SHORTCUTS,
  writingToolInstruction,
} from '@/utils/xiaoMoIntent'
import { projectAgentApi, type ProjectAgentFocus, type ProjectAgentRun, type ProjectAgentStatus, type ProjectAgentAction } from '@/api/project-agent'

marked.setOptions({ gfm: true, breaks: true })

function formatMarkdown(text: string): string {
  if (!text?.trim()) return ''
  try {
    return DOMPurify.sanitize(marked.parse(text.trim()) as string)
  } catch {
    return DOMPurify.sanitize(text.replace(/\n/g, '<br>'))
  }
}

const displayInstruction = stripAgentSystemNotes
/** 快捷功能写入输入框时隐藏；提交时再拼回，功能不受影响 */
const hiddenSystemNotes = ref('')
function turnOf(run: ProjectAgentRun) {
  return assistantTurnDisplay(run)
}
function liveAssistantTexts(run: ProjectAgentRun) {
  return assistantMessages(run)
}

type AttachedContext = {
  text: string
  blockIndex?: number
  blockIndices?: number[]
  blockIds?: string[]
}

export type AgentPageScope = 'system' | 'project' | 'document'

const props = withDefaults(
  defineProps<{
    /** null = 系统级无项目会话，走 /api/agent/runs */
    projectId: number | null
    documentId?: number | null
    /** 随路由自动更新：system / project / document */
    scope?: AgentPageScope
    beforeSubmit?: () => Promise<boolean>
  }>(),
  { scope: undefined },
)
const emit = defineEmits<{
  changed: [projectId: number | null]
  projectCreated: [projectId: number]
  activityChanged: [active: boolean]
}>()
const auth = useAuthStore()
const xiaoMo = useXiaoMoStore()
const runs = ref<ProjectAgentRun[]>([])
const attachedContext = ref<AttachedContext | null>(null)
const selectedId = ref('')
const conversationId = ref('')
const instruction = ref('')
const error = ref('')
const loading = ref(false)
const mutating = ref(false)
const preparing = ref(false)
const busy = computed(() => loading.value || mutating.value)
const attachedPreview = computed(() => {
  const t = attachedContext.value?.text?.trim() || ''
  if (t.length <= 120) return t
  return `${t.slice(0, 120)}…`
})
const attachedLabel = computed(() => {
  const n = attachedContext.value?.blockIds?.length
    || attachedContext.value?.blockIndices?.length
    || 0
  return n > 1 ? `已引用 ${n} 个段落（将只改这些）` : '已引用选中段落（将只改这段）'
})
const composerPlaceholder = computed(() => {
  if (attachedContext.value) {
    return '说说想怎么改选中段落，例如：语气更轻松、缩短一半…'
  }
  if (pageScope.value === 'system') {
    return '例如：帮我建一个科幻短篇项目，先来几个脑洞选题…'
  }
  if (pageScope.value === 'document') {
    return '先在正文选中段落，或点「问小墨」；也可直接说润色/续写…'
  }
  return '和小墨聊聊项目设定、章节，或告诉我想修改什么…'
})
const footerHint = computed(() => {
  if (conversationActive.value) return '小墨正在编辑…'
  if (pageScope.value === 'system') return '系统模式 · Enter 发送'
  if (pageScope.value === 'document') return '文档模式 · Enter 发送'
  return '项目模式 · Enter 发送'
})
const welcomeBlurb = computed(() => {
  if (pageScope.value === 'system') {
    return '当前是系统模式。直接说想法，或点脑洞/热点/文案/故事——小墨会智能创建项目；进入项目页后会自动切到项目协作。'
  }
  if (pageScope.value === 'document') {
    return '当前是文档模式。选中段落或点快捷功能——小墨会直接改这篇正文。'
  }
  return '当前是项目模式。梳理设定、排查矛盾、拆章扩写——直接说需求即可。'
})
const writingShortcuts = computed(() =>
  PROJECT_WRITING_SHORTCUTS.map(item => ({
    key: `w:${item.tool}`,
    tool: item.tool,
    label: item.label,
    description: item.description,
    instruction: writingToolInstruction(item.tool, props.projectId, props.documentId),
  })),
)
/** 对话进行中底部芯片：随页面作用域切换 */
const composerShortcuts = computed(() => {
  const writing = writingShortcuts.value
  if (pageScope.value === 'document' && props.documentId) {
    return [
      ...DOCUMENT_AI_SHORTCUTS.map(item => ({
        key: `d:${item.tool}`,
        tool: item.tool,
        label: item.label,
        description: item.description,
        instruction: documentToolInstruction(item.tool, props.documentId),
      })),
      ...writing,
    ]
  }
  if (pageScope.value === 'system') {
    return [
      {
        key: 'w:create_project',
        tool: 'create_project',
        label: '智能创建项目',
        description: '一句话建项',
        instruction:
          '请根据我的需求智能创建写作项目：先确认主题与类型，再 create_project，' +
          '必要时用专项写作生成开篇或设定，propose 后 finish。\n\n' +
          '（系统：无项目会话；必须先 create_project 再 propose_*。）',
      },
      ...writing,
    ]
  }
  return writing
})
const shortcuts = computed(() => {
  const id = props.documentId
  const writing = writingShortcuts.value
  if (pageScope.value === 'system') {
    return [
      {
        label: '智能创建项目',
        description: '根据一句话主题建项目',
        instruction:
          '请根据我的需求智能创建写作项目：先确认主题与类型，再 create_project，' +
          '必要时用专项写作生成开篇或设定，propose 后 finish。\n\n' +
          '（系统：无项目会话；必须先 create_project 再 propose_*。）',
      },
      ...writing,
    ]
  }
  if (pageScope.value === 'document' && id) {
    return [
      ...DOCUMENT_AI_SHORTCUTS.map(item => ({
        label: item.label,
        description: item.description,
        instruction: documentToolInstruction(item.tool, id),
      })),
      ...writing,
    ]
  }
  // project
  return [
    { label: '阅读项目摘要', description: '梳理故事脉络与当前进展', instruction: '请阅读当前项目，梳理故事设定、主要人物和章节进展，给我一份简明摘要。' },
    {
      label: '更新项目设定',
      description: '按你的要求增量改人设/故事线/情节点等',
      instruction:
        '请根据我的要求更新项目设定。优先用 propose_memory_patch(mode="merge") 分字段增量写入'
        + '（characters / storyline / key_points / outline / world_building / notes），'
        + '每次只改 1 个 field，before 可省略；需要细节时 read_memory(field=...)。改完 finish。\n\n'
        + '（系统：设定已可预读；禁止一次 replace 整包大字段。）',
    },
    {
      label: '丰富人物设定',
      description: '深化角色、补配角与关系网',
      instruction:
        '请丰富 characters：深化主角内心与成长弧，必要时新增配角/关系。'
        + '用 propose_memory_patch(field="characters", mode="merge", after=[...]) 只传新增或改动角色。改完 finish。',
    },
    {
      label: '补全关键情节点',
      description: '按故事线提炼 key_points',
      instruction:
        '请对照 storyline 补全 key_points（title+summary）。'
        + '用 propose_memory_patch(field="key_points", mode="merge", after=[...])；空占位请填实。改完 finish。',
    },
    {
      label: '丰富故事线',
      description: '加入冲突、感情转折与高潮',
      instruction:
        '请丰富 storyline：补充冲突、误会、高潮与收束。'
        + '优先 propose_memory_patch(field="storyline", mode="merge", after={summary, stages})。改完 finish。',
    },
    { label: '检查设定一致性', description: '找出人物、时间线与情节矛盾', instruction: '请检查当前项目的人物设定、时间线和情节是否一致，指出潜在矛盾并给出修改建议；若需直接改设定，用 mode="merge" 分字段提案。' },
    { label: '拆分与扩写章节', description: '细化章节节奏，展开关键情节', instruction: '请阅读当前项目，建议哪些章节适合拆分或扩写，先给我章节规划和扩写思路。' },
    ...writing,
  ]
})
const hasProject = computed(
  () => props.projectId != null && Number.isInteger(props.projectId) && props.projectId > 0,
)
const pageScope = computed<AgentPageScope>(() => {
  if (props.scope) return props.scope
  if (props.documentId && hasProject.value) return 'document'
  if (hasProject.value) return 'project'
  return 'system'
})
const draftStorageKey = computed(
  () =>
    `joe-agent-draft:${auth.currentUser?.id ?? 'anonymous'}:${
      hasProject.value ? props.projectId : 'system'
    }`,
)
function readStoredDraft(): { instruction?: string; conversationId?: string } | null {
  try {
    const raw = sessionStorage.getItem(draftStorageKey.value)
    const saved = raw ? JSON.parse(raw) as { instruction?: unknown; conversationId?: unknown } : null
    if (!saved) return null
    return {
      instruction: typeof saved.instruction === 'string' ? saved.instruction : '',
      conversationId: typeof saved.conversationId === 'string' ? saved.conversationId : ''
    }
  } catch {
    return null
  }
}
let storedDraft = readStoredDraft()
let draftRestored = false
const ready = computed(() => !!auth.token)
const selected = computed(() => runs.value.find(run => run.id === selectedId.value))
const conversationRuns = computed(() => runs.value.filter(run => run.conversation_id === conversationId.value).sort((a, b) => a.created_at.localeCompare(b.created_at)))
const conversationActive = computed(() => conversationRuns.value.some(isActive))
const conversations = computed(() => {
  const seen = new Set<string>()
  return [...runs.value].sort((a, b) => a.created_at.localeCompare(b.created_at)).flatMap(run => {
    if (seen.has(run.conversation_id)) return []
    seen.add(run.conversation_id)
    return [{ id: run.conversation_id, label: displayInstruction(run.instruction).slice(0, 80) || '对话' }]
  })
})
const labels: Record<ProjectAgentStatus, string> = {
  queued: '排队中', running: '执行中', proposed: '写入未完成', completed: '任务完成',
  failed: '执行失败', cancelled: '已取消', applied: '已自动替换', reverted: '已撤销'
}
const statusLabel = (status: ProjectAgentStatus) => labels[status] || status
const isActive = (run: ProjectAgentRun) => run.status === 'queued' || run.status === 'running'
function changesHeadline(run: ProjectAgentRun) {
  const n = run.changes.length
  if (run.status === 'applied') return `已自动替换 · ${n} 项（可撤销）`
  if (run.status === 'reverted') return `本次修改已撤销 · ${n} 项`
  if (run.status === 'proposed') return `替换未完成 · ${n} 项（可点确认写入）`
  return `修改 · ${n} 项`
}
function afterLabel(status: ProjectAgentStatus) {
  if (status === 'reverted') return '曾替换为'
  if (status === 'proposed') return '将替换为'
  return '已替换为'
}
watch(
  () => runs.value.some(isActive),
  active => emit('activityChanged', active),
  { immediate: true },
)
const preview = readablePreview
const composerInput = ref<InputInstance>()
async function focusComposer() {
  await nextTick()
  composerInput.value?.focus()
}
function useSuggestion(text: string) {
  if (!ready.value || mutating.value) return
  const { visible, system } = extractAgentSystemNotes(text)
  hiddenSystemNotes.value = system
  instruction.value = visible
  void focusComposer()
}
async function scrollToBottom() {
  followBottom.value = true
  await nextTick()
  const el = messageList.value
  if (el) el.scrollTop = el.scrollHeight
}
async function submitInstruction(text: string) {
  const value = (text || '').trim()
  if (!value) return false
  const { visible, system } = extractAgentSystemNotes(value)
  hiddenSystemNotes.value = system
  instruction.value = visible
  await focusComposer()
  if (!ready.value || busy.value || conversationActive.value || preparing.value) return false
  await submit()
  return !instruction.value.trim()
}

function setInstruction(text: string) {
  const { visible, system } = extractAgentSystemNotes(text)
  hiddenSystemNotes.value = system
  instruction.value = visible
  void focusComposer()
}

function attachContext(payload: {
  text: string
  blockIndex?: number
  blockIndices?: number[]
  blockIds?: string[]
}) {
  const text = (payload.text || '').trim()
  if (!text) {
    ElMessage.warning('没有可引用的内容')
    return
  }
  attachedContext.value = {
    text,
    blockIndex: payload.blockIndex,
    blockIndices: payload.blockIndices,
    blockIds: payload.blockIds,
  }
  void focusComposer()
  ElMessage.success('已引用到小墨，说说想怎么改就行')
}

function ensureAttachedFromEditor() {
  if (attachedContext.value?.text?.trim()) return
  const live = xiaoMo.documentBridge?.getEditFocus?.()
  if (!live?.text?.trim()) return
  attachedContext.value = {
    text: live.text,
    blockIndex: live.blockIndex,
    blockIndices: live.blockIndices,
    blockIds: live.blockIds,
  }
}

function buildFocus(selection?: string, blockIds?: string[]): ProjectAgentFocus | null {
  if (!props.documentId) return null
  ensureAttachedFromEditor()
  const ids = (blockIds || attachedContext.value?.blockIds || []).filter(Boolean)
  const sel = (selection ?? attachedContext.value?.text ?? '').trim()
  return {
    document_id: props.documentId,
    ...(sel ? { selection: sel.slice(0, 20000) } : {}),
    ...(ids.length ? { block_ids: ids.slice(0, 40) } : {}),
  }
}

function bindPageScope(text: string): string {
  const scope = pageScope.value
  if (scope === 'system') {
    if (text.includes('无项目会话') || text.includes('create_project')) return text
    return (
      `${text}\n\n（系统：当前为系统级无项目会话。可专项写作；要落盘须先 create_project。` +
      `用户若已在其它标签打开项目，仍以本会话为准，勿假设已有 project_id。）`
    )
  }
  if (scope === 'project' && props.projectId) {
    const marker = `project_id=${props.projectId}`
    if (text.includes(marker)) return text
    return (
      `${text}\n\n（系统：当前在项目协作页，${marker}。` +
      `直接读写本项目文档与设定；勿 create_project，除非用户明确要另建项目。）`
    )
  }
  return text
}

function bindCurrentArticle(text: string, focus: ProjectAgentFocus | null): string {
  let out = bindPageScope(text)
  if (!props.documentId) return out
  const marker = `document_id=${props.documentId}`
  const ids = (focus?.block_ids || []).filter(Boolean)
  const hasSelection = !!(focus?.selection || ids.length)
  if (!out.includes(marker)) {
    out += (
      `\n\n（系统：当前打开的文档就是 ${marker}。` +
      `「这篇 / 当前文档」都指这一篇。不要列举或询问项目里还有哪些文档。）`
    )
  }
  if (ids.length && !out.includes('目标已锁定')) {
    const listed = ids.map(id => `block_id=${id}`).join('、')
    out += (
      `\n\n（系统：用户已选中 ${ids.length} 个段落，目标已锁定：${listed}。` +
      `禁止追问是哪几段；禁止通读全文；直接对这些 block_id 调用 propose_block_rewrite 后 finish。）`
    )
  } else if (hasSelection && !out.includes('只改选中') && !out.includes('目标已锁定')) {
    out += (
      `\n\n（系统：用户已选中段落，请只改这些 block，` +
      `禁止追问是哪几段；禁止通读全文，直接 propose_block_rewrite 后 finish。）`
    )
  }
  return out
}

const messageList = ref<HTMLElement>()
const pendingInstruction = ref('')
const followBottom = ref(true)
function onScroll() {
  const el = messageList.value
  if (el) followBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 100
}
watch(
  () => [JSON.stringify(conversationRuns.value), pendingInstruction.value],
  async () => {
    if (!followBottom.value) return
    await nextTick()
    const el = messageList.value
    if (el && followBottom.value) el.scrollTop = el.scrollHeight
  },
)
function composerKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault()
    void submit()
  }
}

/** 快捷动作 / 引用段落 → 走智能体（带 focus），不再走死板 assist API */
async function runDocumentAssist(
  action: string,
  text: string,
  blockIndex?: number,
  blockIndices?: number[],
  blockIds?: string[],
) {
  if (!props.documentId) {
    ElMessage.warning('当前不在文档页，无法编辑正文')
    return
  }
  const selected = (text || '').trim()
  if (selected) {
    attachedContext.value = {
      text: selected,
      blockIndex,
      blockIndices,
      blockIds,
    }
  }
  const ok = await submitInstruction(actionToInstruction(action))
  if (!ok && !instruction.value.trim()) {
    instruction.value = actionToInstruction(action)
  }
}

defineExpose({
  focusComposer,
  scrollToBottom,
  submitInstruction,
  setInstruction,
  attachContext,
  runDocumentAssist,
  buildFocus,
})
function message(cause: unknown): string {
  if (isAxiosError(cause)) {
    if (cause.response?.status === 401) return '登录已过期，请重新登录。'
    if (cause.response?.status === 403) return '没有访问当前项目的权限。'
    const detail: unknown = cause.response?.data?.detail
    if (typeof detail === 'string') {
      if (detail === 'Conversation not found') {
        return '上一会话已失效（可能切换了项目/无项目模式），已为你新开对话，请再发一次。'
      }
      return detail
    }
  }
  return '请求失败，请检查网络或项目权限。操作可能已被服务器接收，请先刷新历史确认状态，不要重复提交。'
}

function isStaleConversationError(cause: unknown): boolean {
  if (!isAxiosError(cause) || cause.response?.status !== 404) return false
  const detail = cause.response?.data?.detail
  return detail === 'Conversation not found'
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
  const newlyAppliedRuns = history.filter(run => {
    const previous = runs.value.find(item => item.id === run.id)
    return previous && run.status === 'applied' && previous.status !== 'applied' && run.changes.length > 0
  })
  runs.value = history
  if (projectChanged) emit('changed', props.projectId)
  if (newlyAppliedRuns.length) {
    ElMessage.success(
      hasProject.value ? '已自动替换到正文，可在对话里撤销' : '已写入，可在对话里撤销',
    )
    for (const run of newlyAppliedRuns) {
      notifyProjectCreated(run)
    }
  }
  void autoApplyPending(history)
}

/** 仅当本轮确实 create_project 时通知；勿用 run.project_id 兜底（已有项目每次发消息都会误弹）。 */
const notifiedProjectCreates = new Set<string>()
function notifyProjectCreated(run: ProjectAgentRun) {
  if (notifiedProjectCreates.has(run.id)) return
  const fromChange = run.changes?.find(c => c.kind === 'created_project')
  if (!fromChange) return
  const pid =
    (fromChange.project_id as number | undefined)
    || (fromChange.target_id as number | undefined)
    || run.project_id
    || null
  if (pid && Number.isInteger(pid) && pid > 0) {
    notifiedProjectCreates.add(run.id)
    emit('projectCreated', pid)
  }
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
  hiddenSystemNotes.value = ''
  selectConversation('')
}

watch(instruction, (value) => {
  // 用户清空输入框时丢弃隐藏系统说明，避免误带到下一条手写消息
  if (!value.trim()) hiddenSystemNotes.value = ''
})
async function submit() {
  if (disposed || preparing.value || !ready.value || busy.value || !instruction.value.trim() || conversationActive.value) return
  const context = generation
  const draft = instruction.value
  const stashedSystem = hiddenSystemNotes.value
  const conversation = conversationId.value || undefined
  const focus = buildFocus()
  // 输入框只有用户可见短句；把快捷功能藏起的（系统：…）拼回再发给后端
  const text = bindCurrentArticle(
    mergeAgentSystemNotes(draft.trim(), stashedSystem),
    focus,
  )

  preparing.value = true
  try {
    const prepared = await props.beforeSubmit?.()
    if (prepared === false || context !== generation || disposed || !ready.value || busy.value || conversationActive.value) return
    if ((conversationId.value || undefined) !== conversation || instruction.value !== draft) return
    pendingInstruction.value = text
    followBottom.value = true
    attachedContext.value = null
    hiddenSystemNotes.value = ''
    await mutate(
      async (project, signal) => {
        try {
          return await projectAgentApi.create(project, text, conversation, signal, focus)
        } catch (cause) {
          // 无项目↔有项目切换后，sessionStorage 里的旧 conversation_id 会 404
          if (!conversation || !isStaleConversationError(cause)) throw cause
          conversationId.value = ''
          selectedId.value = ''
          return projectAgentApi.create(project, text, undefined, signal, focus)
        }
      },
      true,
    )
  } catch {
    if (context === generation && !disposed) {
      error.value = '发送前保存未完成，请检查当前文档后重试。'
      // 发送失败时恢复隐藏说明，便于用户重试
      if (!hiddenSystemNotes.value && stashedSystem) hiddenSystemNotes.value = stashedSystem
    }
  } finally {
    preparing.value = false
    if (context === generation && !disposed) pendingInstruction.value = ''
  }
}
const autoApplying = new Set<string>()

/** 兜底：后端自动写入失败时仍为 proposed，前端静默再试一次 */
async function autoApplyPending(history: ProjectAgentRun[]) {
  if (!ready.value || busy.value || preparing.value || disposed) return
  const pending = history.find(run => run.status === 'proposed' && run.changes.length > 0)
  if (!pending || autoApplying.has(pending.id)) return
  autoApplying.add(pending.id)
  const context = generation
  preparing.value = true
  mutating.value = true
  try {
    const prepared = await props.beforeSubmit?.()
    if (prepared === false || disposed || context !== generation || !ready.value) return
    const run = await projectAgentApi.action(props.projectId, pending.id, 'apply')
    if (disposed || context !== generation) return
    upsert(run)
    if (run.status === 'applied') {
      emit('changed', run.project_id ?? props.projectId)
      notifyProjectCreated(run)
      ElMessage.success(
        hasProject.value ? '已自动替换到正文，可在对话里撤销' : '已写入，可在对话里撤销',
      )
    }
  } catch {
    /* 冲突等留给用户点「确认写入」 */
  } finally {
    autoApplying.delete(pending.id)
    if (context === generation && !disposed) {
      preparing.value = false
      mutating.value = false
      schedulePolling()
    }
  }
}

async function performAction(action: ProjectAgentAction, target?: ProjectAgentRun) {
  const run = target || selected.value
  if (!ready.value || busy.value || preparing.value || !run) return
  if (action === 'apply' || action === 'revert') {
    const context = generation
    preparing.value = true
    try {
      const prepared = await props.beforeSubmit?.()
      if (prepared === false || context !== generation || disposed || !ready.value || busy.value) return
    } catch {
      if (context === generation && !disposed) error.value = '保存当前编辑未完成，请处理后再操作。'
      return
    } finally {
      if (context === generation && !disposed) preparing.value = false
    }
  }
  await mutate(async (project, signal) => {
    if (action === 'revert') {
      try {
        await ElMessageBox.confirm(
          `撤销本次已写入的 ${run.changes.length} 项替换，恢复原文？`,
          '撤销替换',
          { type: 'warning', confirmButtonText: '撤销替换', cancelButtonText: '保留', closeOnClickModal: false },
        )
      } catch { return undefined }
    }
    if (signal.aborted || disposed) return undefined
    return projectAgentApi.action(project, run.id, action, signal)
  }, false, action)
}
async function mutate(
  operation: (project: number | null, signal: AbortSignal) => Promise<ProjectAgentRun | undefined>,
  creating: boolean,
  action?: ProjectAgentAction,
) {
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
    // 仅在 changes 含 created_project 时通知；创建 run 时带 project_id 是常态，不能当「新建项目」
    notifyProjectCreated(run)
    if (action === 'apply' && run.status === 'applied') {
      emit('changed', run.project_id ?? props.projectId)
      ElMessage.success('已写入正文')
    } else if (action === 'revert' && run.status === 'reverted') {
      emit('changed', run.project_id ?? props.projectId)
      ElMessage.success('已撤销替换，原文已恢复')
    }
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
watch(() => [props.projectId, pageScope.value, auth.token] as const, () => {
  generation++
  historyLoaded = false
  notifiedProjectCreates.clear()
  stopPolling()
  request?.abort()
  runs.value = []
  selectedId.value = ''
  // 作用域切换时重读对应 draft；勿跨系统/项目复用 conversation_id
  storedDraft = readStoredDraft()
  const restoreDraft = !draftRestored && storedDraft
  conversationId.value = restoreDraft?.conversationId || ''
  if (restoreDraft?.instruction) {
    const { visible, system } = extractAgentSystemNotes(restoreDraft.instruction)
    instruction.value = visible
    hiddenSystemNotes.value = system
  } else {
    instruction.value = ''
    hiddenSystemNotes.value = ''
  }
  draftRestored = true
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
  try {
    if (instruction.value.trim() || conversationId.value || hiddenSystemNotes.value) {
      sessionStorage.setItem(draftStorageKey.value, JSON.stringify({
        instruction: mergeAgentSystemNotes(instruction.value, hiddenSystemNotes.value),
        conversationId: conversationId.value,
      }))
    } else sessionStorage.removeItem(draftStorageKey.value)
  } catch { /* private mode may reject storage; the live draft remains until navigation */ }
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
.speaker { font-size: 11px; font-weight: 600; color: var(--coffee-text-muted); }
.assistant-message { min-width: 0; padding-top: 18px; }
.assistant-message > .speaker { display: flex; align-items: center; gap: 7px; color: var(--coffee-primary); }
.assistant-message > .speaker::before { content: ''; width: 5px; height: 14px; border-radius: 3px; background: var(--coffee-primary); }
.markdown-body {
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.75;
  overflow-wrap: anywhere;
  color: var(--coffee-text);
}
.markdown-body :deep(p) { margin: 0 0 0.65em; }
.markdown-body :deep(p:last-child) { margin-bottom: 0; }
.markdown-body :deep(strong) { font-weight: 650; }
.markdown-body :deep(em) { font-style: italic; }
.markdown-body :deep(ul),
.markdown-body :deep(ol) { margin: 0.4em 0; padding-left: 1.35em; }
.markdown-body :deep(li) { margin: 0.2em 0; }
.markdown-body :deep(code) {
  padding: 0.12em 0.35em;
  border-radius: 4px;
  background: color-mix(in srgb, var(--coffee-shadow) 55%, transparent);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.9em;
}
.markdown-body :deep(pre) {
  margin: 0.55em 0;
  padding: 10px 12px;
  overflow-x: auto;
  border-radius: 8px;
  background: var(--coffee-bg-warm);
  font-size: 12px;
}
.markdown-body :deep(pre code) { padding: 0; background: none; }
.markdown-body :deep(blockquote) {
  margin: 0.55em 0;
  padding-left: 0.85em;
  border-left: 3px solid color-mix(in srgb, var(--coffee-primary) 45%, var(--coffee-border));
  color: var(--coffee-text-muted);
}
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin: 0.85em 0 0.4em;
  font-weight: 650;
  line-height: 1.35;
}
.markdown-body :deep(h1) { font-size: 1.15em; }
.markdown-body :deep(h2) { font-size: 1.05em; }
.markdown-body :deep(h3) { font-size: 1em; }
.markdown-body :deep(a) { color: var(--coffee-primary); text-decoration: none; }
.markdown-body :deep(a:hover) { text-decoration: underline; }
.markdown-body :deep(hr) { border: none; border-top: 1px solid var(--coffee-border); margin: 0.85em 0; }
.user-body { margin-top: 5px; }
.assistant-body { margin: 10px 0 4px; }
.thinking {
  margin: 10px 0 8px;
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--coffee-bg-warm);
  color: var(--coffee-text-muted);
  font-size: 12px;
}
.thinking > summary {
  cursor: pointer;
  font-weight: 500;
  line-height: 1.6;
  list-style: none;
  display: flex;
  align-items: baseline;
  gap: 6px;
  overflow: hidden;
}
.thinking > summary::-webkit-details-marker { display: none; }
.thinking > summary::before {
  content: '▸';
  flex-shrink: 0;
  font-size: 10px;
  opacity: .7;
}
.thinking[open] > summary::before { content: '▾'; }
.thinking > summary {
  white-space: nowrap;
  text-overflow: ellipsis;
}
.thinking-step {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--coffee-border);
  font-size: 12px;
  color: var(--coffee-text-muted);
  max-height: 160px;
  overflow: auto;
}
.activity { display: flex; align-items: baseline; gap: 8px; margin: 12px 0; color: var(--coffee-text-muted); font-size: 12px; overflow-wrap: anywhere; line-height: 1.7; }
.activity-dot { flex-shrink: 0; height: 6px; width: 6px; border-radius: 50%; background: var(--coffee-primary); box-shadow: 0 0 0 3px color-mix(in srgb, var(--coffee-primary) 12%, transparent); }
.proposal { margin-top: 14px; padding: 12px; border: 1px solid var(--coffee-border); border-radius: 12px; background: var(--coffee-bg-card); }
.proposal.applied { border-color: color-mix(in srgb, var(--coffee-primary) 35%, var(--coffee-border)); background: color-mix(in srgb, var(--coffee-bg-warm) 70%, var(--coffee-bg-card)); }
.proposal.reverted { opacity: .85; }
.proposal > strong { display: block; color: var(--coffee-primary); font-size: 13px; line-height: 1.7; }
.response-actions { margin-top: 12px; }
.response-actions:empty { display: none; }
.response-actions .el-button { max-width: 100%; height: auto; min-height: 28px; white-space: normal; }
.run-error { color: var(--el-color-danger); font-size: 13px; }
.attached-context {
  margin-bottom: 10px;
  padding: 10px 12px;
  border: 1px solid var(--coffee-border);
  border-radius: 10px;
  background: var(--coffee-bg-warm);
}
.attached-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--coffee-primary);
}
.attached-clear {
  border: 0;
  background: transparent;
  color: var(--coffee-text-muted);
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
}
.attached-preview {
  margin: 0;
  max-height: 72px;
  overflow: auto;
  font-size: 12px;
  color: var(--coffee-text-muted);
}
.shortcut-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}
.shortcut-chip {
  padding: 5px 10px;
  border: 1px solid var(--coffee-border);
  border-radius: 999px;
  background: var(--coffee-bg-warm);
  color: var(--coffee-text);
  font: inherit;
  font-size: 11px;
  line-height: 1.4;
  cursor: pointer;
  transition: border-color .15s ease, background .15s ease, color .15s ease;
}
.shortcut-chip:hover:not(:disabled) {
  border-color: var(--coffee-primary);
  color: var(--coffee-primary);
  background: color-mix(in srgb, var(--coffee-bg-warm) 70%, var(--coffee-bg-card));
}
.shortcut-chip:disabled { opacity: .5; cursor: not-allowed; }
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
.change { padding-top: 12px; margin-top: 12px; border-top: 1px solid var(--coffee-border); font-size: 13px; }
summary { cursor: pointer; font-weight: 500; overflow-wrap: anywhere; line-height: 1.7; }
.previews { display: grid; grid-template-columns: minmax(0, 1fr); gap: 10px; }
.previews > div { min-width: 0; }
.after-block h4 { color: var(--coffee-primary); }
.after-block pre {
  max-height: 320px;
  border: 1px solid color-mix(in srgb, var(--coffee-primary) 22%, var(--coffee-border));
  background: color-mix(in srgb, var(--coffee-bg-warm) 70%, var(--coffee-bg-card));
}
.before-block pre { max-height: 160px; opacity: .92; }
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
