<template>
  <div class="main-layout">
    <el-container class="layout-container">
      <el-aside :width="`${sidebarWidth}px`" class="sidebar" :class="{ resizing: sidebarResizing }">
        <div class="logo" @click="goToHome" @keydown.enter="goToHome" role="button" tabindex="0" title="回到我的创作空间">
          <el-icon class="logo-icon"><EditPen /></el-icon>
          <div class="logo-text-wrap">
            <span class="logo-text">墨心</span>
            <span class="logo-sub">AI 辅助写作</span>
          </div>
        </div>

        <div class="search-section">
          <GlobalSearch />
        </div>

        <div class="nav-menu">
          <div
            class="nav-item"
            :class="{ active: $route.path === '/' }"
            @click="$router.push('/')"
          >
            <el-icon><HomeFilled /></el-icon>
            <span>我的项目</span>
          </div>
          <div
            class="nav-item"
            :class="{ active: $route.path === '/dashboard' }"
            @click="$router.push('/dashboard')"
          >
            <el-icon><DataLine /></el-icon>
            <span>数据看板</span>
          </div>
          <div
            class="nav-item"
            :class="{ active: $route.path === '/hot-topics' }"
            @click="$router.push('/hot-topics')"
          >
            <el-icon><TrendCharts /></el-icon>
            <span>热点写作</span>
          </div>
          <div
            class="nav-item"
            :class="{ active: $route.path === '/brainstorm-writing' }"
            @click="$router.push('/brainstorm-writing')"
          >
            <el-icon><Lightning /></el-icon>
            <span>脑洞写作</span>
          </div>
          <div
            class="nav-item"
            :class="{ active: $route.path === '/copywriting-writing' }"
            @click="$router.push('/copywriting-writing')"
          >
            <el-icon><Promotion /></el-icon>
            <span>文案写作</span>
          </div>
          <div
            class="nav-item"
            :class="{ active: $route.path === '/ai-story-generator' }"
            @click="$router.push('/ai-story-generator')"
          >
            <el-icon><MagicStick /></el-icon>
            <span>AI故事生成</span>
          </div>
        </div>

        <div class="sidebar-content">
          <ProjectSidebar />
        </div>

        <div class="user-section">
          <el-divider class="coffee-divider" />
          <div
            class="ai-mode-switch"
            :class="{ 'is-busy': aiModeStore.loading || aiModeStore.switching }"
          >
            <div class="ai-mode-top">
              <span class="ai-mode-title">AI 通道</span>
              <button
                type="button"
                class="ai-mode-gear"
                title="大模型设置"
                @click="settingsDrawer.show('ai-config')"
              >
                <el-icon :size="14"><Setting /></el-icon>
              </button>
            </div>
            <div class="ai-mode-seg" role="group" aria-label="切换 AI 通道">
              <button
                type="button"
                class="ai-mode-opt"
                :class="{ active: aiModeStore.preferredMode === 'local' }"
                :disabled="aiModeStore.switching || aiModeStore.loading"
                @click="onAiModeChange('local')"
              >
                本地
              </button>
              <button
                type="button"
                class="ai-mode-opt"
                :class="{ active: aiModeStore.preferredMode === 'online' }"
                :disabled="aiModeStore.switching || aiModeStore.loading"
                @click="onAiModeChange('online')"
              >
                线上
              </button>
            </div>
            <div class="ai-mode-meta" :title="aiChannelLabel">
              <span class="ai-mode-meta-text">{{ aiChannelLabel }}</span>
              <span v-if="aiModeStore.switching" class="ai-mode-busy">切换中…</span>
            </div>
          </div>
          <el-dropdown trigger="click" @command="handleUserCommand">
            <div class="user-info">
              <div class="user-avatar">
                <el-avatar v-if="authStore.currentUser?.avatar_url" :size="36" :src="sidebarAvatarUrl" />
                <el-icon v-else><UserFilled /></el-icon>
              </div>
              <div class="user-meta">
                <span class="username">{{ authStore.currentUser?.username }}</span>
                <span class="user-role">创作者</span>
              </div>
              <el-icon class="arrow-icon"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu class="user-dropdown">
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon> 个人中心
                </el-dropdown-item>
                <el-dropdown-item command="writing-style">
                  <el-icon><Brush /></el-icon> 文风库
                </el-dropdown-item>
                <el-dropdown-item command="ai-config">
                  <el-icon><Cpu /></el-icon> 大模型设置
                </el-dropdown-item>
                <el-dropdown-item command="theme">
                  <el-icon><Setting /></el-icon> 主题设置
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon> 退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <div
          class="sidebar-resize-handle"
          title="拖动调整侧栏宽度"
          aria-label="调整侧栏宽度"
          @pointerdown="onSidebarResizeStart"
        />
      </el-aside>

      <el-container>
        <el-main class="main-content">
          <router-view v-slot="{ Component }">
            <component :is="Component" ref="pageView" />
          </router-view>
        </el-main>
      </el-container>
    </el-container>

    <FloatingProjectAgent
      :project-id="agentProjectId"
      :project-title="agentProjectTitle"
      :document-id="agentDocumentId"
      :scope="agentScope"
      :before-open="prepareAgent"
      @changed="onAgentChanged"
    />
    <SettingsDrawer />
    <ProjectSettingsDrawer />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/project'
import FloatingProjectAgent from '@/components/FloatingProjectAgent.vue'
import { useAuthStore } from '@/stores/auth'
import { useAiModeStore, type AiPreferredMode } from '@/stores/aiMode'
import { useSettingsDrawerStore } from '@/stores/settingsDrawer'
import { useProjectSettingsDrawerStore } from '@/stores/projectSettingsDrawer'
import ProjectSidebar from '@/components/ProjectSidebar.vue'
import GlobalSearch from '@/components/GlobalSearch.vue'
import SettingsDrawer from '@/components/SettingsDrawer.vue'
import ProjectSettingsDrawer from '@/components/ProjectSettingsDrawer.vue'
import { API_BASE_URL } from '@/api'
import {
  EditPen, UserFilled, ArrowDown, User, Setting, SwitchButton, Cpu,
  HomeFilled, DataLine, TrendCharts, MagicStick, Lightning, Promotion, Brush,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const SIDEBAR_WIDTH_KEY = 'joe-sidebar-width'
const SIDEBAR_MIN = 200
const SIDEBAR_MAX = 480
const SIDEBAR_DEFAULT = 280

function loadSidebarWidth(): number {
  try {
    const n = Number(localStorage.getItem(SIDEBAR_WIDTH_KEY))
    if (Number.isFinite(n) && n >= SIDEBAR_MIN && n <= SIDEBAR_MAX) return Math.round(n)
  } catch { /* ignore */ }
  return SIDEBAR_DEFAULT
}

const router = useRouter()
const authStore = useAuthStore()
const aiModeStore = useAiModeStore()
const settingsDrawer = useSettingsDrawerStore()
const projectSettingsDrawer = useProjectSettingsDrawerStore()
const route = useRoute()
const projectStore = useProjectStore()
const pageView = ref<{ prepareProjectAgent?: () => Promise<boolean>; onAgentProjectChanged?: () => Promise<void> }>()
const sidebarWidth = ref(loadSidebarWidth())
const sidebarResizing = ref(false)
let sidebarResizeStartX = 0
let sidebarResizeStartW = 0

function clampSidebarWidth(w: number) {
  const maxByViewport = typeof window !== 'undefined'
    ? Math.min(SIDEBAR_MAX, Math.floor(window.innerWidth * 0.45))
    : SIDEBAR_MAX
  return Math.max(SIDEBAR_MIN, Math.min(maxByViewport, Math.round(w)))
}

function persistSidebarWidth() {
  try {
    localStorage.setItem(SIDEBAR_WIDTH_KEY, String(sidebarWidth.value))
  } catch { /* ignore */ }
}

function onSidebarResizeMove(e: PointerEvent) {
  if (!sidebarResizing.value) return
  sidebarWidth.value = clampSidebarWidth(sidebarResizeStartW + (e.clientX - sidebarResizeStartX))
}

function onSidebarResizeEnd() {
  if (!sidebarResizing.value) return
  sidebarResizing.value = false
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  window.removeEventListener('pointermove', onSidebarResizeMove)
  window.removeEventListener('pointerup', onSidebarResizeEnd)
  window.removeEventListener('pointercancel', onSidebarResizeEnd)
  persistSidebarWidth()
}

function onSidebarResizeStart(e: PointerEvent) {
  if (e.button !== 0) return
  e.preventDefault()
  sidebarResizing.value = true
  sidebarResizeStartX = e.clientX
  sidebarResizeStartW = sidebarWidth.value
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  window.addEventListener('pointermove', onSidebarResizeMove)
  window.addEventListener('pointerup', onSidebarResizeEnd)
  window.addEventListener('pointercancel', onSidebarResizeEnd)
}
/** 仅在项目/文档路由绑定 projectId；首页与写作工具页为系统级（无项目） */
const agentProjectId = computed(() => {
  if (route.name === 'project' || route.name === 'project-settings') {
    const id = Number(route.params.id)
    if (!Number.isInteger(id) || id <= 0) return null
    // 用路由上的项目编号，避免新项目尚未写入 store 时闪成无项目会话并带上旧 conversation
    return id
  }
  if (route.name === 'document') {
    const routeDocId = Number(route.params.id)
    const doc = projectStore.currentDocument
    if (doc?.id === routeDocId && doc.project_id) return doc.project_id
    // 新文档尚未载入时沿用当前项目，避免智能体闪成无项目会话并取消请求
    const projectId = projectStore.currentProject?.id
    if (projectId && projectId > 0) return projectId
    return null
  }
  return null
})
const agentDocumentId = computed(() => {
  if (route.name !== 'document') return null
  const id = Number(route.params.id)
  return Number.isInteger(id) && id > 0 ? id : null
})
/** 页面作用域：系统（无项目）/ 项目 / 文档编辑 */
const agentScope = computed<'system' | 'project' | 'document'>(() => {
  if (agentDocumentId.value && agentProjectId.value) return 'document'
  if (agentProjectId.value) return 'project'
  return 'system'
})
const agentProjectTitle = computed(() =>
  projectStore.currentProject?.id === agentProjectId.value
    ? (projectStore.currentProject.title || '')
    : '',
)
async function prepareAgent() {
  const settingsOk = await projectSettingsDrawer.prepareProjectAgent()
  if (!settingsOk) return false
  if (route.name === 'document') {
    if (!agentProjectId.value || !pageView.value?.prepareProjectAgent) return false
    const path = route.fullPath
    const prepared = await pageView.value.prepareProjectAgent()
    return prepared && path === route.fullPath
  }
  return true
}
async function onAgentChanged(changedProjectId: number | null) {
  if (!changedProjectId) return
  // 系统会话智能建项：刷新列表并进入新项目
  if (changedProjectId !== agentProjectId.value) {
    try {
      await projectStore.fetchProjects()
      await projectStore.fetchProject(changedProjectId)
      if (route.name !== 'project' && route.name !== 'document' && route.name !== 'project-settings') {
        await router.push(`/project/${changedProjectId}`)
      }
    } catch { /* 导航失败不阻断 */ }
    return
  }
  try {
    await projectSettingsDrawer.onAgentProjectChanged()
    if (pageView.value?.onAgentProjectChanged) {
      await pageView.value.onAgentProjectChanged()
    } else {
      await projectStore.fetchProject(changedProjectId)
    }
  } catch {
    ElMessage.warning('项目变更已保存，但页面刷新失败，请手动刷新确认。')
  }
}

function onViewportResizeSidebar() {
  sidebarWidth.value = clampSidebarWidth(sidebarWidth.value)
}

onMounted(() => {
  if (authStore.isLoggedIn) aiModeStore.load()
  sidebarWidth.value = clampSidebarWidth(sidebarWidth.value)
  window.addEventListener('resize', onViewportResizeSidebar)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onViewportResizeSidebar)
  onSidebarResizeEnd()
})

watch(
  () => authStore.isLoggedIn,
  (loggedIn) => {
    if (loggedIn) aiModeStore.load()
  },
)

async function onAiModeChange(mode: string | number | boolean | undefined) {
  if (mode !== 'local' && mode !== 'online') return
  await aiModeStore.setMode(mode as AiPreferredMode)
}

const BASE_URL = import.meta.env.VITE_API_URL || API_BASE_URL

const aiChannelLabel = computed(() =>
  aiModeStore.preferredMode === 'local'
    ? `Ollama · ${aiModeStore.localModel}`
    : aiModeStore.onlineLabel,
)

const sidebarAvatarUrl = computed(() => {
  const url = authStore.currentUser?.avatar_url
  if (!url) return ''
  const base = BASE_URL.replace(/\/api\/?$/, '')
  return base + url
})

function goToHome() {
  router.push('/')
}

async function handleUserCommand(command: string) {
  if (command === 'profile' || command === 'writing-style' || command === 'ai-config' || command === 'theme') {
    settingsDrawer.show(command)
    return
  }
  if (command !== 'logout') return
  try {
    await ElMessageBox.confirm(
      '确定要退出登录吗？',
      '退出确认',
      {
        confirmButtonText: '退出',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
    await authStore.logout()
    router.push('/login')
  } catch {
    // 用户取消
  }
}
</script>

<style scoped lang="scss">
.main-layout {
  height: 100vh;
  background: var(--coffee-bg);
}

.layout-container {
  height: 100%;
}

.sidebar {
  position: relative;
  background: linear-gradient(180deg, var(--coffee-bg) 0%, var(--coffee-bg-warm) 100%);
  border-right: 1px solid var(--coffee-border);
  display: flex;
  flex-direction: column;
  box-shadow: 4px 0 20px var(--coffee-sidebar-shadow);
  transition: none;

  &.resizing {
    user-select: none;
  }
}

.sidebar-resize-handle {
  position: absolute;
  top: 0;
  right: -3px;
  width: 6px;
  height: 100%;
  cursor: col-resize;
  z-index: 20;
  touch-action: none;

  &::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 2px;
    height: 48px;
    border-radius: 2px;
    background: transparent;
    transition: background 0.15s ease;
  }

  &:hover::after,
  .sidebar.resizing &::after {
    background: var(--coffee-primary);
    opacity: 0.55;
  }
}

.logo {
  height: 70px;
  display: flex;
  align-items: center;
  padding: 0 24px;
  gap: 12px;
  border-bottom: 1px solid var(--coffee-border-light);
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: var(--coffee-bg-hover);
  }

  .logo-icon {
    width: 40px;
    height: 40px;
    background: var(--coffee-gradient-primary);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    color: #fff;
  }

  .logo-text-wrap {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .logo-text {
    font-size: 18px;
    font-weight: 700;
    color: var(--coffee-text);
    letter-spacing: 1px;
  }
  .logo-sub {
    font-size: 11px;
    color: var(--coffee-text-muted);
    letter-spacing: 0.5px;
  }
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
}

.search-section {
  padding: 12px 16px;
  border-bottom: 1px solid var(--coffee-border-light);
}

.nav-menu {
  padding: 8px 16px;
  border-bottom: 1px solid var(--coffee-border-light);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: 4px;
  color: var(--coffee-text-secondary);
  font-size: 14px;

  .el-icon {
    font-size: 18px;
  }

  &:hover {
    background: var(--coffee-bg-hover);
    color: var(--coffee-text);
  }

  &.active {
    background: var(--coffee-selection);
    color: var(--coffee-primary);
    font-weight: 400;
  }
}

.user-section {
  padding: 0 16px 16px;

  .coffee-divider {
    margin: 8px 0 16px;
    border-color: var(--coffee-border);
  }
}

.ai-mode-switch {
  margin-bottom: 10px;
  padding: 4px 0 2px;
  background: transparent;

  &.is-busy {
    opacity: 0.85;
  }
}

.ai-mode-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.ai-mode-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--coffee-text-secondary);
}

.ai-mode-gear {
  width: 26px;
  height: 26px;
  border: none;
  border-radius: 7px;
  background: transparent;
  color: var(--coffee-text-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;

  &:hover {
    background: var(--coffee-bg-hover);
    color: var(--coffee-primary);
  }
}

.ai-mode-seg {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  padding: 3px;
  border-radius: 9px;
  border: 1px solid var(--coffee-border);
  background: transparent;
}

.ai-mode-opt {
  height: 30px;
  border: none;
  border-radius: 7px;
  background: transparent;
  color: var(--coffee-text-secondary);
  font-size: 13px;
  font-weight: 400;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;

  &:hover:not(:disabled):not(.active) {
    color: var(--coffee-text);
    background: var(--coffee-bg-hover);
  }

  &.active {
    background: var(--coffee-selection);
    color: var(--coffee-primary);
    font-weight: 600;
  }

  &:disabled {
    cursor: not-allowed;
    opacity: 0.65;
  }
}

.ai-mode-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 8px;
  min-width: 0;
}

.ai-mode-meta-text {
  flex: 1;
  min-width: 0;
  font-size: 11px;
  line-height: 1.3;
  color: var(--coffee-text-light);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ai-mode-busy {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--coffee-primary);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;

  &:hover {
    background: var(--coffee-bg-hover);
  }

  .user-avatar {
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, var(--coffee-border) 0%, var(--coffee-text-light) 100%);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--coffee-text);
    font-size: 18px;
  }

  .user-meta {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;

    .username {
      font-size: 14px;
      font-weight: 600;
      color: var(--coffee-text);
    }

    .user-role {
      font-size: 12px;
      color: var(--coffee-text-light);
    }
  }

  .arrow-icon {
    font-size: 12px;
    color: var(--coffee-text-light);
  }
}

.main-content {
  padding: 0 !important;
  background: var(--coffee-gradient-light);
  height: 100%;
  min-height: 0;
  overflow-y: auto;
  box-sizing: border-box;
  position: relative;
}

:deep(.user-dropdown) {
  .el-dropdown-menu__item {
    padding: 10px 16px;

    .el-icon {
      margin-right: 8px;
      color: var(--coffee-text-muted);
    }

    &:hover {
      background: var(--coffee-bg-warm);
      color: var(--coffee-primary);

      .el-icon {
        color: var(--coffee-primary);
      }
    }
  }
}
</style>
