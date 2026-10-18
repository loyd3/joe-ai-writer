<template>
  <Teleport to="body">
    <div v-if="auth.isLoggedIn" class="floating-agent">
      <Transition name="agent-window">
        <section
          v-show="opened"
          id="floating-project-agent"
          class="agent-window"
          :class="{ maximized, moving, resizing }"
          :style="windowStyle"
          role="dialog"
          aria-label="小墨创作助手"
          @keydown.esc.stop="close"
        >
          <header
            class="window-header"
            :class="{ dragging: moving }"
            @pointerdown="onHeaderPointerDown"
          >
            <div class="agent-identity">
              <span class="agent-avatar"><el-icon><MagicStick /></el-icon></span>
              <div>
                <strong>小墨 <span>创作助手</span></strong>
                <p :title="subtitle">{{ subtitle }}</p>
              </div>
            </div>
            <div class="window-actions" @pointerdown.stop>
              <button type="button" aria-label="重置位置与大小" title="重置位置与大小" @click="resetGeom">
                <el-icon><RefreshRight /></el-icon>
              </button>
              <button type="button" :aria-label="maximized ? '还原窗口' : '放大窗口'" :title="maximized ? '还原窗口' : '放大窗口'" @click="toggleMaximize">
                <el-icon><FullScreen /></el-icon>
              </button>
              <button type="button" aria-label="收起助手" title="收起助手，任务继续运行" @click="close">
                <el-icon><Minus /></el-icon>
              </button>
            </div>
          </header>
          <div class="project-context">
            <span class="context-dot" />
            <span class="scope-badge">{{ scopeLabel }}</span>
            {{ contextLine }}
            <span>{{ contextHint }}</span>
          </div>
          <div class="window-body">
            <ProjectAgentPanel
              v-if="initialized"
              :key="panelKey"
              ref="panel"
              :project-id="projectId"
              :document-id="documentId"
              :scope="resolvedScope"
              :before-submit="prepareSubmission"
              @changed="onPanelChanged"
              @project-created="onProjectCreated"
              @activity-changed="active = $event"
            />
          </div>
          <div
            class="resize-handle"
            title="拖动调整大小"
            aria-label="调整窗口大小"
            @pointerdown="onResizePointerDown"
          />
        </section>
      </Transition>
      <button
        ref="launcher"
        type="button"
        class="agent-launcher"
        :class="{ working: active }"
        aria-controls="floating-project-agent"
        :aria-expanded="opened"
        :aria-label="opened ? '收起小墨助手' : '打开小墨助手'"
        @click="toggle"
      >
        <el-icon><ChatDotRound v-if="!opened" /><ArrowDown v-else /></el-icon>
        <span>{{ active ? '小墨处理中' : '小墨助手' }}</span>
        <span v-if="active" class="launcher-dot" />
      </button>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowDown, ChatDotRound, FullScreen, MagicStick, Minus, RefreshRight } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useXiaoMoStore } from '@/stores/xiaoMo'
import ProjectAgentPanel from '@/components/ProjectAgentPanel.vue'

export type AgentPageScope = 'system' | 'project' | 'document'

type WindowGeom = { x: number; y: number; w: number; h: number }

const GEOM_KEY = 'joe-agent-window-geom'
const MIN_W = 320
const MIN_H = 420

const props = defineProps<{
  projectId: number | null
  projectTitle?: string
  documentId?: number | null
  /** 由路由推导：随页面自动切换 */
  scope?: AgentPageScope
  beforeOpen?: () => Promise<boolean>
}>()
const emit = defineEmits<{ changed: [projectId: number | null] }>()
const auth = useAuthStore()
const router = useRouter()
const xiaoMo = useXiaoMoStore()
const opened = ref(false)
const initialized = ref(false)
const maximized = ref(false)
const active = ref(false)
const opening = ref(false)
const moving = ref(false)
const resizing = ref(false)

function defaultGeom(): WindowGeom {
  const w = Math.min(460, Math.max(MIN_W, window.innerWidth - 40))
  const h = Math.min(700, Math.max(MIN_H, window.innerHeight - 112))
  return {
    w,
    h,
    x: Math.max(12, window.innerWidth - w - 24),
    y: Math.max(12, window.innerHeight - h - 88),
  }
}

function loadGeom(): WindowGeom {
  try {
    const raw = localStorage.getItem(GEOM_KEY)
    if (!raw) return defaultGeom()
    const parsed = JSON.parse(raw) as Partial<WindowGeom>
    const base = defaultGeom()
    return clampGeom({
      x: Number(parsed.x) || base.x,
      y: Number(parsed.y) || base.y,
      w: Number(parsed.w) || base.w,
      h: Number(parsed.h) || base.h,
    })
  } catch {
    return defaultGeom()
  }
}

function clampGeom(g: WindowGeom): WindowGeom {
  const maxW = Math.max(MIN_W, window.innerWidth - 16)
  const maxH = Math.max(MIN_H, window.innerHeight - 16)
  const w = Math.min(maxW, Math.max(MIN_W, g.w))
  const h = Math.min(maxH, Math.max(MIN_H, g.h))
  const x = Math.min(window.innerWidth - w - 8, Math.max(8, g.x))
  const y = Math.min(window.innerHeight - h - 8, Math.max(8, g.y))
  return { x, y, w, h }
}

const geom = ref<WindowGeom>(typeof window !== 'undefined' ? loadGeom() : { x: 24, y: 24, w: 460, h: 640 })
let geomBeforeMaximize: WindowGeom | null = null

function persistGeom() {
  try {
    localStorage.setItem(GEOM_KEY, JSON.stringify(geom.value))
  } catch { /* private mode */ }
}

const windowStyle = computed(() => {
  if (maximized.value) {
    return {
      left: '12px',
      top: '12px',
      width: 'calc(100vw - 24px)',
      height: 'calc(100dvh - 24px)',
    }
  }
  const g = geom.value
  return {
    left: `${g.x}px`,
    top: `${g.y}px`,
    width: `${g.w}px`,
    height: `${g.h}px`,
  }
})

let dragOffsetX = 0
let dragOffsetY = 0
let resizeStartX = 0
let resizeStartY = 0
let resizeStartW = 0
let resizeStartH = 0

function setBodyDragStyle(active: boolean) {
  if (typeof document === 'undefined') return
  document.body.style.cursor = active ? (resizing.value ? 'nwse-resize' : 'grabbing') : ''
  document.body.style.userSelect = active ? 'none' : ''
}

function onHeaderPointerDown(e: PointerEvent) {
  if (maximized.value || e.button !== 0) return
  const target = e.target as HTMLElement
  if (target.closest('button, a, input, textarea')) return
  moving.value = true
  dragOffsetX = e.clientX - geom.value.x
  dragOffsetY = e.clientY - geom.value.y
  setBodyDragStyle(true)
  ;(e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId)
  window.addEventListener('pointermove', onDragMove)
  window.addEventListener('pointerup', onDragEnd)
  window.addEventListener('pointercancel', onDragEnd)
}

function onDragMove(e: PointerEvent) {
  if (!moving.value) return
  geom.value = clampGeom({
    ...geom.value,
    x: e.clientX - dragOffsetX,
    y: e.clientY - dragOffsetY,
  })
}

function onDragEnd() {
  if (!moving.value) return
  moving.value = false
  setBodyDragStyle(false)
  window.removeEventListener('pointermove', onDragMove)
  window.removeEventListener('pointerup', onDragEnd)
  window.removeEventListener('pointercancel', onDragEnd)
  persistGeom()
}

function onResizePointerDown(e: PointerEvent) {
  if (maximized.value || e.button !== 0) return
  e.preventDefault()
  e.stopPropagation()
  resizing.value = true
  resizeStartX = e.clientX
  resizeStartY = e.clientY
  resizeStartW = geom.value.w
  resizeStartH = geom.value.h
  setBodyDragStyle(true)
  ;(e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId)
  window.addEventListener('pointermove', onResizeMove)
  window.addEventListener('pointerup', onResizeEnd)
  window.addEventListener('pointercancel', onResizeEnd)
}

function onResizeMove(e: PointerEvent) {
  if (!resizing.value) return
  geom.value = clampGeom({
    ...geom.value,
    w: resizeStartW + (e.clientX - resizeStartX),
    h: resizeStartH + (e.clientY - resizeStartY),
  })
}

function onResizeEnd() {
  if (!resizing.value) return
  resizing.value = false
  setBodyDragStyle(false)
  window.removeEventListener('pointermove', onResizeMove)
  window.removeEventListener('pointerup', onResizeEnd)
  window.removeEventListener('pointercancel', onResizeEnd)
  persistGeom()
}

function toggleMaximize() {
  if (maximized.value) {
    maximized.value = false
    if (geomBeforeMaximize) {
      geom.value = clampGeom(geomBeforeMaximize)
      geomBeforeMaximize = null
    }
  } else {
    geomBeforeMaximize = { ...geom.value }
    maximized.value = true
  }
}

function resetGeom() {
  maximized.value = false
  geomBeforeMaximize = null
  geom.value = defaultGeom()
  persistGeom()
}

function onViewportResize() {
  // 仅临时钳制到可视区域，不写入 localStorage，避免缩小窗口后丢失偏好尺寸
  if (!maximized.value) {
    geom.value = clampGeom(geom.value)
  }
}

if (typeof window !== 'undefined') {
  window.addEventListener('resize', onViewportResize)
}
onBeforeUnmount(() => {
  window.removeEventListener('resize', onViewportResize)
  onDragEnd()
  onResizeEnd()
})
/** 并发 open() 共享同一 promise，避免 pendingAssist 撞上 opening 早退丢请求 */
let openInFlight: Promise<void> | null = null
const launcher = ref<HTMLButtonElement>()
const panel = ref<{
  focusComposer: () => void
  attachContext: (payload: {
    text: string
    blockIndex?: number
    blockIndices?: number[]
    blockIds?: string[]
  }) => void
  runDocumentAssist: (
    action: string,
    text: string,
    blockIndex?: number,
    blockIndices?: number[],
    blockIds?: string[],
  ) => Promise<void>
  submitInstruction: (text: string) => Promise<boolean>
  setInstruction: (text: string) => void
}>()

/** 严格跟随当前页面：有文档 → document；有项目 → project；否则 system */
const resolvedScope = computed<AgentPageScope>(() => {
  if (props.scope) return props.scope
  if (props.documentId && props.projectId) return 'document'
  if (props.projectId) return 'project'
  return 'system'
})

/** 同项目内文档↔项目页保持同一面板；离开项目或进系统级则换会话 */
const panelKey = computed(() => {
  if (resolvedScope.value === 'system' || !props.projectId) return 'system'
  return `p:${props.projectId}`
})

const scopeLabel = computed(() => {
  if (resolvedScope.value === 'document') return '文档'
  if (resolvedScope.value === 'project') return '项目'
  return '系统'
})

const subtitle = computed(() => {
  if (props.projectTitle) return props.projectTitle
  if (resolvedScope.value === 'system') return '系统助手 · 可智能建项'
  return '你的随身写作伙伴'
})

const contextLine = computed(() => {
  if (active.value) return '正在处理…'
  if (resolvedScope.value === 'document') {
    return props.documentId
      ? `正在编辑文档 #${props.documentId}，可直接改稿`
      : '文档协作模式'
  }
  if (resolvedScope.value === 'project') {
    return props.projectTitle
      ? `项目「${props.projectTitle}」协作中`
      : `项目 #${props.projectId} 协作中`
  }
  return '无项目模式 · 对话 / 写作 / 智能建项'
})

const contextHint = computed(() => {
  if (resolvedScope.value === 'document') return '选区优先 · 改稿可撤销'
  if (resolvedScope.value === 'project') return '设定与章节 · 确认后写入'
  return '建项后自动进入项目'
})

watch(
  () => [props.projectId, props.documentId, resolvedScope.value] as const,
  (next, prev) => {
    if (!prev) return
    const [pid, docId, scope] = next
    const [prevPid, prevDoc, prevScope] = prev
    // 作用域或项目变化：停掉「处理中」态，面板 key 会重挂
    if (pid !== prevPid || scope !== prevScope) {
      active.value = false
    } else if (docId !== prevDoc && opened.value) {
      // 同项目换文档：轻提示，能力已随 documentId 更新
      // no-op；快捷与焦点由 Panel 响应 props
    }
  },
)

function onPanelChanged(projectId: number | null) {
  emit('changed', projectId ?? props.projectId)
}

function onProjectCreated(projectId: number) {
  if (!projectId || projectId <= 0) return
  emit('changed', projectId)
  const name = router.currentRoute.value.name
  if (name !== 'project' && name !== 'document' && name !== 'project-settings') {
    void router.push(`/project/${projectId}`).then(() => {
      ElMessage.success('已创建项目，已切换到项目协作模式')
    })
  } else {
    ElMessage.success('已创建项目并写入内容')
  }
}

watch(
  () => xiaoMo.openNonce,
  () => {
    void open()
  },
)

watch(
  () => xiaoMo.pendingAssist,
  async (req) => {
    if (!req) return
    await open()
    await nextTick()
    if (!panel.value) await nextTick()
    try {
      if (!panel.value) {
        ElMessage.warning('助手尚未就绪，请再试一次')
        return
      }
      if (req.kind === 'attach') {
        panel.value.attachContext({
          text: req.text,
          blockIndex: req.blockIndex,
          blockIndices: req.blockIndices,
          blockIds: req.blockIds,
        })
        if (req.instruction?.trim()) {
          panel.value.setInstruction(req.instruction.trim())
        }
      } else if (req.kind === 'ask' && req.instruction?.trim()) {
        panel.value.attachContext({
          text: req.text,
          blockIndex: req.blockIndex,
          blockIndices: req.blockIndices,
          blockIds: req.blockIds,
        })
        await panel.value.submitInstruction(req.instruction.trim())
      } else if (req.kind === 'action' && req.action) {
        await panel.value.runDocumentAssist(
          req.action,
          req.text,
          req.blockIndex,
          req.blockIndices,
          req.blockIds,
        )
      }
    } finally {
      xiaoMo.consumeAssist(req.nonce)
    }
  },
)

async function prepareSubmission() {
  if (resolvedScope.value === 'system' || !props.projectId) return true
  const snapshot = props.projectId
  const prepared = await props.beforeOpen?.()
  return prepared !== false && props.projectId === snapshot
}

async function open() {
  if (openInFlight) return openInFlight
  if (opened.value) {
    await nextTick()
    panel.value?.focusComposer()
    return
  }
  opening.value = true
  const project = props.projectId
  const scope = resolvedScope.value
  openInFlight = (async () => {
    try {
      if (props.beforeOpen && !(await props.beforeOpen())) return
      if (project !== props.projectId || scope !== resolvedScope.value) return
      initialized.value = true
      opened.value = true
      await nextTick()
      panel.value?.focusComposer()
    } catch {
      ElMessage.warning('打开助手前保存未完成，请检查文档后重试。')
    } finally {
      opening.value = false
      openInFlight = null
    }
  })()
  return openInFlight
}

function close() {
  opened.value = false
  launcher.value?.focus()
}

function toggle() {
  if (opened.value) close()
  else void open()
}

defineExpose({ open })
</script>

<style scoped lang="scss">
.floating-agent { position: fixed; right: max(24px, env(safe-area-inset-right)); bottom: max(22px, env(safe-area-inset-bottom)); z-index: 1900; color: var(--coffee-text); pointer-events: none; }
.floating-agent > * { pointer-events: auto; }
.agent-launcher { display: flex; align-items: center; gap: 9px; height: 50px; margin-left: auto; padding: 0 20px; border: 1px solid rgba(255,255,255,.18); border-radius: 25px; background: var(--coffee-gradient-primary); color: #fff; font: inherit; font-size: 14px; font-weight: 600; cursor: pointer; box-shadow: 0 6px 24px rgba(var(--coffee-primary-rgb), .28); transition: transform .2s, box-shadow .2s; }
.agent-launcher:hover { transform: translateY(-2px); box-shadow: 0 8px 30px rgba(var(--coffee-primary-rgb), .36); }
.agent-launcher .el-icon { font-size: 21px; }
.launcher-dot, .context-dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; flex-shrink: 0; }
.launcher-dot { animation: agent-pulse 1.6s ease-in-out infinite; }
.agent-window {
  position: fixed;
  z-index: 1901;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--coffee-border-light);
  border-radius: 20px;
  background: var(--coffee-bg-card);
  box-shadow: var(--app-shadow-lg), 0 12px 60px rgba(var(--coffee-primary-rgb), .1);
  overflow: hidden;
  min-width: 320px;
  min-height: 420px;
}
.agent-window.moving,
.agent-window.resizing { user-select: none; }
.agent-window.maximized { border-radius: 16px; }
.window-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 20px 14px;
  background: var(--coffee-gradient-light);
  cursor: grab;
  touch-action: none;
}
.window-header.dragging,
.window-header:active { cursor: grabbing; }
.agent-identity { display: flex; align-items: center; gap: 11px; min-width: 0; }
.agent-identity > div { min-width: 0; }
.agent-avatar { display: grid; place-items: center; width: 40px; height: 40px; flex-shrink: 0; border-radius: 13px; background: var(--coffee-gradient-primary); color: white; font-size: 22px; }
.agent-identity strong { font-size: 17px; }
.agent-identity strong span { margin-left: 6px; font-size: 12px; font-weight: 400; color: var(--coffee-text-muted); }
.agent-identity p { font-size: 12px; color: var(--coffee-text-muted); max-width: 260px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.window-actions { display: flex; gap: 4px; cursor: default; }
.window-actions button { display: grid; place-items: center; width: 30px; height: 30px; border: 0; border-radius: 8px; color: var(--coffee-text-muted); background: transparent; font-size: 16px; cursor: pointer; }
.window-actions button:hover { background: var(--coffee-bg-hover); color: var(--coffee-primary); }
button:focus-visible { outline: 2px solid var(--coffee-primary); outline-offset: 3px; }
.project-context { display: flex; align-items: center; gap: 7px; padding: 9px 20px; border-bottom: 1px solid var(--coffee-border-light); font-size: 11px; color: var(--coffee-primary); min-width: 0; }
.scope-badge {
  flex-shrink: 0;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(var(--coffee-primary-rgb), .12);
  font-weight: 600;
  font-size: 10px;
  letter-spacing: .02em;
}
.project-context > span:last-child { margin-left: auto; flex-shrink: 0; color: var(--coffee-text-muted); }
.window-body { flex: 1; min-height: 0; overflow: hidden; }
.resize-handle {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 18px;
  height: 18px;
  cursor: nwse-resize;
  touch-action: none;
  z-index: 2;
}
.resize-handle::after {
  content: '';
  position: absolute;
  right: 5px;
  bottom: 5px;
  width: 9px;
  height: 9px;
  border-right: 2px solid var(--coffee-text-muted);
  border-bottom: 2px solid var(--coffee-text-muted);
  opacity: .55;
}
.agent-window.maximized .resize-handle { display: none; }
.agent-window-enter-active, .agent-window-leave-active { transition: opacity .18s ease, transform .18s ease; }
.agent-window-enter-from, .agent-window-leave-to { opacity: 0; transform: translateY(12px) scale(.98); }
@keyframes agent-pulse { 50% { opacity: .35; } }
@media (max-width: 600px) {
  .floating-agent { right: 12px; bottom: max(12px, env(safe-area-inset-bottom)); }
  .window-header { padding: 14px; cursor: default; }
  .agent-identity p { max-width: 180px; }
  .agent-launcher { height: 46px; padding: 0 16px; }
}
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
</style>
