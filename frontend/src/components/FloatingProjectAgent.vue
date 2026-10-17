<template>
  <Teleport to="body">
    <div v-if="auth.isLoggedIn" class="floating-agent">
      <Transition name="agent-window">
        <section v-show="opened" id="floating-project-agent" class="agent-window" :class="{ expanded }" role="dialog" aria-label="小墨创作助手" @keydown.esc.stop="close">
          <header class="window-header">
            <div class="agent-identity"><span class="agent-avatar"><el-icon><MagicStick /></el-icon></span><div><strong>小墨 <span>创作助手</span></strong><p :title="projectTitle">{{ projectTitle || '你的随身写作伙伴' }}</p></div></div>
            <div class="window-actions">
              <button type="button" :aria-label="expanded ? '还原窗口' : '放大窗口'" :title="expanded ? '还原窗口' : '放大窗口'" @click="expanded = !expanded"><el-icon><FullScreen /></el-icon></button>
              <button type="button" aria-label="收起助手" title="收起助手，任务继续运行" @click="close"><el-icon><Minus /></el-icon></button>
            </div>
          </header>
          <div class="project-context"><span class="context-dot" />{{ !projectId ? '等待选择项目' : active ? '正在处理项目任务' : '基于当前项目协作' }}<span>修改前由你确认</span></div>
          <div class="window-body">
            <ProjectAgentPanel v-if="retainedProjectId && initialized" v-show="!!projectId" :key="retainedProjectId" ref="panel" :project-id="retainedProjectId" :before-submit="prepareSubmission" @changed="emit('changed', retainedProjectId)" @activity-changed="active = $event" />
            <div v-if="!projectId" class="no-project"><el-icon><Collection /></el-icon><h3>从一个项目开始创作</h3><p>打开项目或文档后，小墨就能阅读设定、梳理故事、协助修改。</p><el-button type="primary" @click="router.push('/')">前往我的项目</el-button></div>
          </div>
        </section>
      </Transition>
      <button ref="launcher" type="button" class="agent-launcher" :class="{ working: active }" aria-controls="floating-project-agent" :aria-expanded="opened" :aria-label="opened ? '收起小墨助手' : '打开小墨助手'" @click="toggle">
        <el-icon><ChatDotRound v-if="!opened" /><ArrowDown v-else /></el-icon><span>{{ active ? '小墨处理中' : '小墨助手' }}</span><span v-if="active" class="launcher-dot" />
      </button>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowDown, ChatDotRound, Collection, FullScreen, MagicStick, Minus } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import ProjectAgentPanel from '@/components/ProjectAgentPanel.vue'

const props = defineProps<{ projectId: number | null; projectTitle?: string; beforeOpen?: () => Promise<boolean> }>()
const emit = defineEmits<{ changed: [projectId: number | null] }>()
const auth = useAuthStore()
const router = useRouter()
const opened = ref(false)
const initialized = ref(false)
const expanded = ref(false)
const active = ref(false)
const opening = ref(false)
const launcher = ref<HTMLButtonElement>()
const panel = ref<{ focusComposer: () => void }>()
// Route loading can briefly clear the project context. Keep the same panel alive
// so navigating between a project and its documents does not discard a draft.
const retainedProjectId = ref<number | null>(props.projectId)
watch(() => props.projectId, (id) => {
  if (id && id !== retainedProjectId.value) {
    active.value = false
    retainedProjectId.value = id
  }
})
async function prepareSubmission() {
  const project = props.projectId
  if (!project || project !== retainedProjectId.value) return false
  const prepared = await props.beforeOpen?.()
  return prepared !== false && project === props.projectId
}
async function open() {
  if (opening.value) return
  opening.value = true
  const project = props.projectId
  try {
    if (props.beforeOpen && !(await props.beforeOpen())) return
    if (project !== props.projectId) return
    initialized.value = true
    opened.value = true
    await nextTick()
    panel.value?.focusComposer()
  } catch {
    ElMessage.warning('打开助手前保存未完成，请检查文档后重试。')
  } finally {
    opening.value = false
  }
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
.floating-agent { position: fixed; right: max(24px, env(safe-area-inset-right)); bottom: max(22px, env(safe-area-inset-bottom)); z-index: 1900; color: var(--coffee-text); }
.agent-launcher { display: flex; align-items: center; gap: 9px; height: 50px; margin-left: auto; padding: 0 20px; border: 1px solid rgba(255,255,255,.18); border-radius: 25px; background: var(--coffee-gradient-primary); color: #fff; font: inherit; font-size: 14px; font-weight: 600; cursor: pointer; box-shadow: 0 6px 24px rgba(var(--coffee-primary-rgb), .28); transition: transform .2s, box-shadow .2s; }
.agent-launcher:hover { transform: translateY(-2px); box-shadow: 0 8px 30px rgba(var(--coffee-primary-rgb), .36); }
.agent-launcher .el-icon { font-size: 21px; }
.launcher-dot, .context-dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; flex-shrink: 0; }
.launcher-dot { animation: agent-pulse 1.6s ease-in-out infinite; }
.agent-window { position: absolute; right: 0; bottom: 64px; display: flex; flex-direction: column; width: min(460px, calc(100vw - 40px)); height: min(700px, calc(100dvh - 112px)); border: 1px solid var(--coffee-border-light); border-radius: 20px; background: var(--coffee-bg-card); box-shadow: var(--app-shadow-lg), 0 12px 60px rgba(var(--coffee-primary-rgb), .1); overflow: hidden; }
.agent-window.expanded { width: min(800px, calc(100vw - 40px)); height: calc(100dvh - 112px); }
.window-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 18px 20px 14px; background: var(--coffee-gradient-light); }
.agent-identity { display: flex; align-items: center; gap: 11px; min-width: 0; }
.agent-identity > div { min-width: 0; }
.agent-avatar { display: grid; place-items: center; width: 40px; height: 40px; flex-shrink: 0; border-radius: 13px; background: var(--coffee-gradient-primary); color: white; font-size: 22px; }
.agent-identity strong { font-size: 17px; }
.agent-identity strong span { margin-left: 6px; font-size: 12px; font-weight: 400; color: var(--coffee-text-muted); }
.agent-identity p { font-size: 12px; color: var(--coffee-text-muted); max-width: 260px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.window-actions { display: flex; gap: 4px; }
.window-actions button { display: grid; place-items: center; width: 30px; height: 30px; border: 0; border-radius: 8px; color: var(--coffee-text-muted); background: transparent; font-size: 16px; cursor: pointer; }
.window-actions button:hover { background: var(--coffee-bg-hover); color: var(--coffee-primary); }
button:focus-visible { outline: 2px solid var(--coffee-primary); outline-offset: 3px; }
.project-context { display: flex; align-items: center; gap: 7px; padding: 9px 20px; border-bottom: 1px solid var(--coffee-border-light); font-size: 11px; color: var(--coffee-primary); }
.project-context > span:last-child { margin-left: auto; color: var(--coffee-text-muted); }
.window-body { flex: 1; min-height: 0; overflow: hidden; }
.no-project { display: flex; height: 100%; flex-direction: column; justify-content: center; align-items: center; gap: 16px; padding: 32px; text-align: center; }
.no-project > .el-icon { font-size: 38px; color: var(--coffee-primary); }
.no-project h3 { font-size: 17px; }
.no-project p { color: var(--coffee-text-muted); font-size: 13px; line-height: 1.8; }
.agent-window-enter-active, .agent-window-leave-active { transition: opacity .18s ease, transform .18s ease; }
.agent-window-enter-from, .agent-window-leave-to { opacity: 0; transform: translateY(12px) scale(.98); }
@keyframes agent-pulse { 50% { opacity: .35; } }
@media (max-width: 600px) { .floating-agent { right: 12px; bottom: max(12px, env(safe-area-inset-bottom)); } .agent-window, .agent-window.expanded { width: calc(100vw - 24px); height: calc(100dvh - 100px); bottom: 62px; border-radius: 16px; } .window-header { padding: 14px; } .agent-identity p { max-width: 180px; } .agent-launcher { height: 46px; padding: 0 16px; } }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
</style>
