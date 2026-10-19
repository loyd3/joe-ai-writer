<template>
  <div class="document-editor">
    <el-alert v-if="saveConflict" type="warning" :closable="false" title="服务器版本已变化，自动保存已暂停。本地稿仍在编辑器中，请先复制备份。">
      <el-button size="small" @click="reloadAfterConflict">放弃本地稿并加载最新版本</el-button>
    </el-alert>
    <div class="editor-header">
      <div class="header-left">
        <el-button link class="btn-icon" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <div class="breadcrumb">
          <span class="project-name">{{ project?.title }}</span>
          <el-icon class="separator"><ArrowRight /></el-icon>
          <span
            class="title-input"
          >{{ documentTitle }}</span>
        </div>
      </div>
      <div class="header-right">
        <div class="save-status" v-if="saving">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>保存中...</span>
        </div>
        <div class="save-status saved" v-else-if="lastSaved">
          <el-icon><CircleCheck /></el-icon>
          <span>已保存 {{ formatTime(lastSaved) }}</span>
        </div>
        <el-button class="btn btn-primary" type="primary" @click="saveDocument" :loading="saving">
          <el-icon><Check /></el-icon>
          <span>保存</span>
        </el-button>
        <el-button
          v-if="document?.project_id"
          class="btn"
          @click="goProjectSettings"
        >
          <el-icon><Collection /></el-icon>
          <span>项目设定</span>
        </el-button>
        <el-button
          v-if="document?.project_id"
          class="btn"
          @click="goWritingStyle"
        >
          <el-icon><Brush /></el-icon>
          <span>文风设置</span>
        </el-button>
        <el-dropdown trigger="click" placement="bottom-end" popper-class="coffee-dropdown" @command="setEditorWidth" class="header-dropdown">
          <el-button class="btn" :title="`版面宽度 ${editorWidthLabel}`">
            <el-icon><FullScreen /></el-icon>
            <span>版面</span>
            <el-icon class="arrow-icon"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu class="coffee-dropdown-menu">
              <el-dropdown-item
                v-for="opt in EDITOR_WIDTH_OPTIONS"
                :key="opt.value"
                :command="opt.value"
                :class="{ 'is-active-width': editorMaxWidth === opt.value }"
              >
                <div class="dd-item">
                  <div class="dd-meta">
                    <span class="dd-title">{{ opt.label }}</span>
                    <span class="dd-desc">{{ opt.desc }}</span>
                  </div>
                </div>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button class="btn" @click="xiaoMo.openFloating()">
          <el-icon><ChatDotRound /></el-icon>
          <span>小墨</span>
        </el-button>
        <ExportMenu
          mode="document"
          :document-id="Number(documentId)"
          :document-title="documentTitle"
        />
        <el-dropdown trigger="click" placement="bottom-end" popper-class="coffee-dropdown" @command="handleMoreCommand" class="header-dropdown">
          <el-button class="btn">
            <el-icon><Promotion /></el-icon>
            <span>发布</span>
            <el-icon class="arrow-icon"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu class="coffee-dropdown-menu">
              <el-dropdown-item command="publish">
                <div class="dd-item">
                  <span class="dd-icon"><el-icon><Promotion /></el-icon></span>
                  <div class="dd-meta">
                    <span class="dd-title">发布到自媒体</span>
                    <span class="dd-desc">一键发到内容平台</span>
                  </div>
                </div>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-dropdown trigger="click" placement="bottom-end" popper-class="coffee-dropdown" @command="handleMoreCommand" class="header-dropdown">
          <el-button class="btn">
            <el-icon><MoreFilled /></el-icon>
            <span>更多</span>
            <el-icon class="arrow-icon"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu class="coffee-dropdown-menu">
              <el-dropdown-item command="split-sections" :disabled="!content.length">
                <div class="dd-item">
                  <span class="dd-icon"><el-icon><Files /></el-icon></span>
                  <div class="dd-meta">
                    <span class="dd-title">按章节拆分为多篇</span>
                    <span class="dd-desc">拆成多篇文档，按序加入项目</span>
                  </div>
                </div>
              </el-dropdown-item>
              <el-dropdown-item divided command="rename">
                <div class="dd-item">
                  <span class="dd-icon"><el-icon><Edit /></el-icon></span>
                  <div class="dd-meta">
                    <span class="dd-title">重命名</span>
                    <span class="dd-desc">修改当前文档标题</span>
                  </div>
                </div>
              </el-dropdown-item>
              <el-dropdown-item divided command="delete" class="delete-item">
                <div class="dd-item">
                  <span class="dd-icon"><el-icon><Delete /></el-icon></span>
                  <div class="dd-meta">
                    <span class="dd-title">删除文档</span>
                    <span class="dd-desc">删除后不可恢复</span>
                  </div>
                </div>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <div class="editor-container">
      <div class="editor-main">
        <aside
          v-if="tocItems.length > 0"
          class="doc-outline"
          :class="{ 'is-collapsed': tocCollapsed }"
          @mouseenter="onTocMouseEnter"
          @mouseleave="onTocMouseLeave"
        >
          <div class="outline-header">
            <div v-show="!tocCollapsed" class="outline-title">目录</div>
            <button type="button" class="outline-toggle" @click="toggleToc" :title="tocCollapsed ? '展开目录' : '收起目录'">
              <el-icon v-if="tocCollapsed"><ArrowLeft /></el-icon>
              <el-icon v-else><ArrowRight /></el-icon>
            </button>
          </div>
          <div v-show="!tocCollapsed" class="outline-list">
            <button
              v-for="item in tocItems"
              :key="`toc-${item.index}`"
              type="button"
              class="outline-item"
              :class="{ 'is-sub': item.level === 2 }"
              @click="jumpToTocItem(item.index)"
            >
              {{ item.text }}
            </button>
          </div>
        </aside>
        <div class="editor-content" :style="editorContentStyle">
          <BlockEditor 
            ref="blockEditorRef"
            v-model="content"
            @update:modelValue="onContentChange"
            @content-dirty="onContentChange"
            @polish="onPolish"
            @polish-selected="onPolishSelected"
            @format-style="onFormatStyle"
            @format-style-selected="onFormatStyleSelected"
            @revise-selected="onReviseSelected"
            @expand-selected="onExpandSelected"
            @ask-ai="onAskAi"
          />
        </div>
      </div>
      
    </div>

    <PublishDialog
      v-model="showPublishDialog"
      :document-id="Number(documentId)"
    />

    <SplitDocumentDialog
      v-if="document?.project_id"
      v-model="showSplitDialog"
      :blocks="content"
      :project-id="document.project_id"
      :document-id="Number(documentId)"
      :document-title="documentTitle"
      @done="onSplitDone"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, onUnmounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore, type Block } from '@/stores/project'
import { ElMessage } from 'element-plus'
import BlockEditor from '@/components/BlockEditor.vue'
import { useXiaoMoStore } from '@/stores/xiaoMo'
import { captureEditorSave, matchesEditorSave } from '@/utils/editorSaveSnapshot'
import ExportMenu from '@/components/ExportMenu.vue'
import PublishDialog from '@/components/PublishDialog.vue'
import SplitDocumentDialog from '@/components/SplitDocumentDialog.vue'
import { parseFormattedTextToBlocks } from '@/utils/formatToBlocks'
import { ElMessageBox } from 'element-plus'
import { ArrowLeft, ArrowRight, ArrowDown, ChatDotRound, Check, Loading, CircleCheck, MoreFilled, Edit, Delete, Files, Promotion, Collection, Brush, FullScreen } from '@element-plus/icons-vue'

const EDITOR_WIDTH_KEY = 'joe-editor-content-width'
const EDITOR_WIDTH_OPTIONS = [
  { value: 640, label: '窄栏', desc: '专注阅读，约 640px' },
  { value: 800, label: '标准', desc: '默认版面，约 800px' },
  { value: 960, label: '加宽', desc: '更宽正文，约 960px' },
  { value: 1200, label: '很宽', desc: '大屏写作，约 1200px' },
  { value: 0, label: '铺满', desc: '随编辑区拉满宽度' },
] as const

function loadEditorWidth(): number {
  try {
    const raw = localStorage.getItem(EDITOR_WIDTH_KEY)
    if (raw == null) return 800
    const n = Number(raw)
    if (n === 0) return 0
    if ([640, 800, 960, 1200].includes(n)) return n
  } catch { /* ignore */ }
  return 800
}

const route = useRoute()
const router = useRouter()
const store = useProjectStore()
const xiaoMo = useXiaoMoStore()
const editorMaxWidth = ref(loadEditorWidth())
const editorWidthLabel = computed(
  () => EDITOR_WIDTH_OPTIONS.find(o => o.value === editorMaxWidth.value)?.label || '标准',
)
const editorContentStyle = computed(() => ({
  maxWidth: editorMaxWidth.value === 0 ? '100%' : `${editorMaxWidth.value}px`,
}))

function setEditorWidth(value: number | string) {
  const n = Number(value)
  editorMaxWidth.value = Number.isFinite(n) ? n : 800
  try {
    localStorage.setItem(EDITOR_WIDTH_KEY, String(editorMaxWidth.value))
  } catch { /* ignore */ }
}

const documentId = computed(() => route.params.id as string)
const document = computed(() => store.currentDocument)
const project = computed(() => store.currentProject)

const documentTitle = ref('')
const content = ref<Block[]>([])
const saving = ref(false)
const saveConflict = ref(false)
const editorBaseUpdatedAt = ref('')
const hasChanges = ref(false)
let editorEpoch = 0
/** AI 预览块：插入到文档末尾，仅用于阅读与 diff 接受/拒绝；未接受前不应自动保存 */
const aiPreviewId = ref<string | null>(null)
const AI_PREVIEW_KEY = '__ai_preview_id'
const lastSaved = ref<Date | null>(null)
const blockEditorRef = ref<{
  flushPendingSync: () => void
  focusBlock: (index: number, opts?: { cursor?: 'start' | 'end' | number; align?: 'start' | 'nearest'; behavior?: ScrollBehavior; focus?: boolean; preventScroll?: boolean; force?: boolean }) => void
  getInsertAfterIndex: () => number
  getEditFocus?: () => { text: string; blockIndex?: number; blockIndices?: number[] } | null
} | null>(null)
const showPublishDialog = ref(false)
const showSplitDialog = ref(false)

let autoSaveInterval: number | null = null
const tocCollapsed = ref(true)
const tocPinnedOpen = ref(false)
let tocCollapseTimer: number | null = null
let tocJumpRaf: number | null = null

function stripHtmlToText(html: string): string {
  const div = globalThis.document.createElement('div')
  div.innerHTML = html || ''
  return (div.textContent || '').trim()
}

const tocItems = computed(() => {
  const out: Array<{ index: number; text: string; level: 1 | 2 }> = []
  for (let i = 0; i < content.value.length; i++) {
    const b = content.value[i]
    if (!b) continue
    if (b.type !== 'heading' && b.type !== 'subheading') continue
    const text = stripHtmlToText(b.content) || (b.type === 'heading' ? '未命名标题' : '未命名小标题')
    out.push({ index: i, text, level: b.type === 'heading' ? 1 : 2 })
  }
  return out
})

function jumpToTocItem(index: number) {
  // 目录快速连点时，仅执行最后一次定位，提升“快速定位”手感并减少滚动抖动
  if (tocJumpRaf != null) {
    cancelAnimationFrame(tocJumpRaf)
    tocJumpRaf = null
  }
  tocJumpRaf = requestAnimationFrame(() => {
    tocJumpRaf = null
    blockEditorRef.value?.focusBlock(index, {
      align: 'start',
      behavior: 'auto',
      focus: true,
      cursor: 'start',
      force: true,
    })
  })
}

function clearTocCollapseTimer() {
  if (tocCollapseTimer != null) {
    clearTimeout(tocCollapseTimer)
    tocCollapseTimer = null
  }
}

function onTocMouseEnter() {
  clearTocCollapseTimer()
  if (!tocPinnedOpen.value) {
    tocCollapsed.value = false
  }
}

function onTocMouseLeave() {
  clearTocCollapseTimer()
  if (tocPinnedOpen.value) return
  tocCollapseTimer = window.setTimeout(() => {
    tocCollapsed.value = true
    tocCollapseTimer = null
  }, 320)
}

function toggleToc() {
  const nextCollapsed = !tocCollapsed.value
  tocCollapsed.value = nextCollapsed
  tocPinnedOpen.value = !nextCollapsed
  clearTocCollapseTimer()
}

watch(documentId, () => {
  loadDocument()
})

function applyLoadedDocument() {
  if (!document.value) return
  documentTitle.value = document.value.title
  content.value = JSON.parse(JSON.stringify(document.value.content || [])) as Block[]
  editorBaseUpdatedAt.value = document.value.updated_at
  hasChanges.value = false
  saveConflict.value = false
  aiPreviewId.value = null
}

async function loadDocument(force = false) {
  const id = Number(documentId.value)
  const epoch = editorEpoch
  const switching = document.value?.id !== id
  await store.fetchDocument(id)
  if (Number(documentId.value) !== id) return
  if (!force && !switching && (epoch !== editorEpoch || hasChanges.value || saving.value || aiPreviewId.value)) {
    saveConflict.value = true
    ElMessage.warning('加载期间编辑器有新修改，本地内容已保留。')
    return
  }
  applyLoadedDocument()
  if (document.value?.project_id) await store.fetchProject(document.value.project_id)
}

function onContentChange() {
  editorEpoch += 1
  hasChanges.value = true
}

function resolveBlockIds(index?: number, indices?: number[]): string[] | undefined {
  const idxs = indices?.length ? indices : (index != null ? [index] : [])
  const ids = idxs.map(i => content.value[i]?.id).filter((id): id is string => !!id)
  return ids.length ? ids : undefined
}

function askXiaoMo(
  kind: 'action' | 'attach' | 'ask',
  payload: { text: string; index?: number; indices?: number[]; instruction?: string; action?: string },
) {
  xiaoMo.requestAssist({
    kind,
    action: payload.action,
    text: payload.text,
    blockIndex: payload.index,
    blockIndices: payload.indices,
    blockIds: resolveBlockIds(payload.index, payload.indices),
    instruction: payload.instruction,
  })
}

function onPolish(payload: { index: number; text: string }) {
  askXiaoMo('ask', {
    action: 'polish',
    text: payload.text,
    index: payload.index,
    instruction:
      '请只润色我选中的这些段落（不要通读或重读全文），让表达更流畅自然，保留原意与语气，直接改稿后 finish。',
  })
}

function onPolishSelected(payload: { indices: number[]; text: string }) {
  askXiaoMo('ask', {
    action: 'polish',
    text: payload.text,
    indices: payload.indices,
    instruction:
      '请只润色我选中的这些段落（不要通读或重读全文），让表达更流畅自然，保留原意与语气，直接改稿后 finish。',
  })
}

function onFormatStyle(payload: { index: number; text: string }) {
  askXiaoMo('ask', {
    action: 'format_style',
    text: payload.text,
    index: payload.index,
    instruction: '请只调整这段的结构与排版层次，不要改写措辞内容本身。',
  })
}

function onFormatStyleSelected(payload: { indices: number[]; text: string }) {
  askXiaoMo('ask', {
    action: 'format_style',
    text: payload.text,
    indices: payload.indices,
    instruction: '请只调整这些段落的结构与排版层次，不要改写措辞内容本身。',
  })
}


function onReviseSelected(payload: { indices: number[]; text: string }) {
  askXiaoMo('ask', {
    action: 'revise',
    text: payload.text,
    indices: payload.indices,
    instruction: '请改写这些段落，修正生硬或不通顺处，提升可读性，保留核心信息。',
  })
}

function onExpandSelected(payload: { indices: number[]; text: string }) {
  askXiaoMo('ask', {
    action: 'expand',
    text: payload.text,
    indices: payload.indices,
    instruction: '请在这些段落基础上扩写，补充细节与画面感，风格与上下文一致。',
  })
}

/** 把段落贴到小墨浮窗，便于自由提修改要求 */
function onAskAi(payload: { text: string; index?: number; indices?: number[] }) {
  askXiaoMo('attach', {
    text: payload.text,
    index: payload.index,
    indices: payload.indices,
  })
}

async function saveDocument(): Promise<boolean> {
  if (saving.value || saveConflict.value) return false
  blockEditorRef.value?.flushPendingSync?.()
  await nextTick()
  if (saving.value || saveConflict.value) return false
  if (!hasChanges.value) return true
  if (!editorBaseUpdatedAt.value) return false

  const snapshot = captureEditorSave(
    Number(documentId.value), documentTitle.value,
    content.value.filter(block => !block.props?.[AI_PREVIEW_KEY]), editorBaseUpdatedAt.value,
  )
  saving.value = true
  try {
    const saved = await store.updateDocument(snapshot.documentId, snapshot.payload)
    if (snapshot.documentId === Number(documentId.value)) {
      editorBaseUpdatedAt.value = saved.updated_at
      hasChanges.value = !matchesEditorSave(snapshot, Number(documentId.value), documentTitle.value,
        content.value.filter(block => !block.props?.[AI_PREVIEW_KEY]))
      lastSaved.value = new Date()
    }
    return true
  } catch (error: unknown) {
    const status = (error as { response?: { status?: number } }).response?.status
    if (status === 409) {
      saveConflict.value = true
      ElMessage.error('文档已在其他位置更新，已停止自动保存；本地修改仍保留，请先复制备份再重新加载。')
    } else {
      ElMessage.error('保存失败，本地修改仍保留，请稍后重试')
    }
    return false
  } finally {
    saving.value = false
  }
}

async function prepareProjectAgent(): Promise<boolean> {
  if (aiPreviewId.value) {
    ElMessage.warning('请先接受或拒绝当前 AI 预览，再打开项目智能体')
    return false
  }
  if (!(await saveDocument())) return false
  if (hasChanges.value) {
    ElMessage.warning('保存期间又有新修改，请再次保存后打开智能体')
    return false
  }
  return true
}

defineExpose({ prepareProjectAgent, onAgentProjectChanged })

async function reloadAfterConflict() {
  try {
    await ElMessageBox.confirm('将放弃当前编辑器里的未保存内容。请确认已复制需要保留的内容。', '加载最新版本', { type: 'warning' })
    await loadDocument(true)
  } catch {
    // Cancellation keeps the local manuscript untouched.
  }
}

async function onAgentProjectChanged() {
  // 小墨已自动写入服务器：以服务器结果为准，直接替换编辑器内容，不走「冲突备份」流程
  blockEditorRef.value?.flushPendingSync?.()
  await nextTick()
  if (saving.value) {
    // 等在途保存结束，避免本地 PUT 覆盖刚写入的智能体结果
    for (let i = 0; i < 40 && saving.value; i++) {
      await new Promise(r => setTimeout(r, 50))
    }
  }
  aiPreviewId.value = null
  hasChanges.value = false
  saveConflict.value = false
  await loadDocument(true)
}

function goBack() {
  if (project.value) {
    router.push(`/project/${project.value.id}`)
  } else {
    router.push('/')
  }
}

function goProjectSettings() {
  const pid = document.value?.project_id || project.value?.id
  if (!pid) return
  import('@/stores/projectSettingsDrawer').then(({ useProjectSettingsDrawerStore }) => {
    useProjectSettingsDrawerStore().show(Number(pid))
  })
}

function goWritingStyle() {
  import('@/stores/settingsDrawer').then(({ useSettingsDrawerStore }) => {
    useSettingsDrawerStore().show('writing-style')
  })
}

function handleMoreCommand(command: string) {
  if (command === 'split-sections') {
    openSplitDialog()
  } else if (command === 'publish') {
    showPublishDialog.value = true
  } else if (command === 'rename' || command === 'delete') {
    handleDocCommand(command)
  }
}

function openSplitDialog() {
  blockEditorRef.value?.flushPendingSync?.()
  if (!document.value?.project_id) {
    ElMessage.warning('无法获取项目信息')
    return
  }
  if (!content.value.length) {
    ElMessage.warning('文档暂无内容')
    return
  }
  showSplitDialog.value = true
}

async function onSplitDone(payload: { created: import('@/api/types').Document[]; deletedOriginal: boolean }) {
  if (payload.deletedOriginal) {
    const projectId = document.value?.project_id || project.value?.id
    if (payload.created[0]) {
      router.replace(`/document/${payload.created[0].id}`)
    } else if (projectId) {
      router.replace(`/project/${projectId}`)
    } else {
      router.replace('/')
    }
    return
  }
  // 原文档改为目录时，重新加载当前文档内容
  if (documentId.value) {
    await loadDocument(true)
    hasChanges.value = false
  }
}

async function handleDocCommand(command: string) {
  if (command === 'rename') {
    try {
      const res = await ElMessageBox.prompt('输入新标题', '重命名文档', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputValue: documentTitle.value,
        inputPattern: /.{1,100}/,
        inputErrorMessage: '标题长度 1～100 个字符'
      })
      const value = (res as any)?.value as string
      const saved = await store.updateDocument(Number(documentId.value), {
        title: value, expected_updated_at: editorBaseUpdatedAt.value,
      })
      editorBaseUpdatedAt.value = saved.updated_at
      editorEpoch += 1
      documentTitle.value = value
      ElMessage.success('已重命名')
    } catch {
      // 用户取消
    }
  } else if (command === 'delete') {
    try {
      await ElMessageBox.confirm(
        `确定要删除文档「${documentTitle.value || document.value?.title}」吗？此操作不可恢复。`,
        '删除文档',
        {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning',
          confirmButtonClass: 'el-button--danger'
        }
      )
      if (hasChanges.value) await saveDocument()
      const projectId = document.value?.project_id
      await store.deleteDocument(Number(documentId.value))
      ElMessage.success('文档已删除')
      if (projectId) {
        router.push(`/project/${projectId}`)
      } else {
        router.push('/')
      }
    } catch {
      // 用户取消
    }
  }
}

type InsertPos = 'cursor' | 'end'

function resolveInsertAt(position: InsertPos = 'cursor'): number {
  if (position === 'end') return content.value.length
  const after = blockEditorRef.value?.getInsertAfterIndex?.()
  if (typeof after === 'number') return Math.max(0, after + 1)
  return content.value.length
}

function normalizeIncomingBlocks(blocks: Block[]): Block[] {
  return blocks.map(b => ({
    id: b.id && String(b.id).length ? String(b.id) : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`,
    type: b.type || 'paragraph',
    content: typeof b.content === 'string' ? b.content : '',
    props: b.props && typeof b.props === 'object' ? { ...b.props } : {},
  }))
}

function insertText(text: string, position: InsertPos = 'cursor') {
  const blocks = parseFormattedTextToBlocks(text, 'doc')
  if (blocks.length) {
    insertBlocksFromAi(blocks, position)
    return
  }
  insertBlocksFromAi([{
    id: Date.now().toString(),
    type: 'paragraph',
    content: text,
    props: {}
  }], position)
}

/** AI 助手返回的 blocks 插入到光标处或文末 */
function insertBlocksFromAi(blocks: Block[], position: InsertPos = 'cursor') {
  if (!blocks?.length) return
  const normalized = normalizeIncomingBlocks(blocks)
  const at = resolveInsertAt(position)
  content.value.splice(at, 0, ...normalized)
  hasChanges.value = true
  nextTick(() => {
    blockEditorRef.value?.focusBlock?.(at, { cursor: 'end', align: 'nearest' })
  })
}

function removeAiPreviewBlocks() {
  if (!aiPreviewId.value) return
  const pid = aiPreviewId.value
  // 预览块只用于阅读，不应落盘，因此通过私有 props 标记移除。
  content.value = content.value.filter(b => !(b.props && (b.props as any)[AI_PREVIEW_KEY] === pid))
  aiPreviewId.value = null
}

function onAiPreview(payload: { blockIndex?: number; blockIndices?: number[]; text: string; blocks?: Block[] }) {
  removeAiPreviewBlocks()
  if (!payload?.text?.trim() && (!payload.blocks || payload.blocks.length === 0)) return

  const previewId = `ai-preview-${Date.now().toString(36)}`
  aiPreviewId.value = previewId

  const sourceBlocks = payload.blocks?.length ? payload.blocks : parseFormattedTextToBlocks(payload.text, 'doc')
  if (!sourceBlocks?.length) return

  const normalized: Block[] = sourceBlocks.map(b => ({
    id: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`,
    type: b.type || 'paragraph',
    content: typeof b.content === 'string' ? b.content : '',
    props: {
      ...(b.props || {}),
      [AI_PREVIEW_KEY]: previewId,
    },
  }))

  // 预览只插入到文档末尾供阅读，未接受前不设置 hasChanges，避免自动保存落盘。
  content.value.push(...normalized)
}

function onAiPreviewCancel() {
  removeAiPreviewBlocks()
}

function replaceText(
  oldText: string,
  newText: string,
  blockIndex?: number,
  rewrittenBlocks?: Block[],
  blockIndices?: number[]
) {
  // 单块「划词」改写：走单块路径（支持只替换选中片段）
  if (blockIndices?.length === 1) {
    blockIndex = blockIndices[0]
    blockIndices = undefined
  }

  // 多选块：把 AI 输出的 blocks 替换到选中的块集合上
  if (blockIndices && blockIndices.length > 1) {
    const indices = Array.from(new Set(blockIndices))
      .filter(i => i >= 0 && i < content.value.length)
      .sort((a, b) => a - b)
    if (indices.length === 0) return

    const blocks = rewrittenBlocks?.length ? rewrittenBlocks : parseFormattedTextToBlocks(newText, 'doc')
    if (!blocks.length) return

    const normalized: Block[] = blocks.map(b => ({
      id: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`,
      type: b.type || 'paragraph',
      content: typeof b.content === 'string' ? b.content : '',
      props: b.props && typeof b.props === 'object' ? { ...b.props } : {},
    }))

    // 从大到小删除，避免删除导致下标错乱；再在最小下标处插入 AI 结果
    const desc = [...indices].sort((a, b) => b - a)
    for (const idx of desc) {
      content.value.splice(idx, 1)
    }
    content.value.splice(indices[0], 0, ...normalized)

    hasChanges.value = true
    removeAiPreviewBlocks()
    nextTick(() => {
      blockEditorRef.value?.focusBlock?.(indices[0], { cursor: 'end', align: 'nearest' })
    })
    return
  }

  // AI 改写类操作通常会返回「编辑器块格式」文本。
  // 这里优先把改写结果解析为 Block，并用新块替换当前块，以确保块类型/样式匹配编辑器。
  if (blockIndex != null && blockIndex >= 0 && blockIndex < content.value.length) {
    const block = content.value[blockIndex]
    const old = oldText || ''
    const plain = stripHtmlToText(block.content || '')
    const isPartial =
      !!old.trim() &&
      plain.includes(old.trim()) &&
      plain.trim() !== old.trim()

    // 划词改写：只替换段落内选中片段，避免整块被拆掉
    if (isPartial) {
      let replacement = newText
      const sourceBlocks = rewrittenBlocks?.length ? rewrittenBlocks : parseFormattedTextToBlocks(newText, 'doc')
      if (sourceBlocks.length === 1) {
        replacement = sourceBlocks[0].content || newText
      } else if (sourceBlocks.length > 1) {
        replacement = sourceBlocks.map(b => stripHtmlToText(b.content || '')).filter(Boolean).join('\n')
      }
      let nextContent = block.content || ''
      if (old && nextContent.includes(old)) {
        nextContent = nextContent.replace(old, replacement)
      } else {
        const oldTrim = old.trim()
        const idx = plain.indexOf(oldTrim)
        if (idx >= 0) {
          const nextPlain =
            plain.slice(0, idx) +
            stripHtmlToText(replacement) +
            plain.slice(idx + oldTrim.length)
          nextContent = nextPlain
        } else {
          nextContent = replacement
        }
      }
      content.value[blockIndex] = { ...block, content: nextContent }
      hasChanges.value = true
      removeAiPreviewBlocks()
      nextTick(() => {
        blockEditorRef.value?.focusBlock?.(blockIndex, { cursor: 'end', align: 'nearest' })
      })
      return
    }

    const blocks = rewrittenBlocks?.length ? rewrittenBlocks : parseFormattedTextToBlocks(newText, 'doc')
    if (blocks.length) {
      // 接受后：用 AI 结果替换选中块，并移除末尾预览内容。
      const normalized: Block[] = blocks.map(b => ({
        id: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`,
        type: b.type || 'paragraph',
        content: typeof b.content === 'string' ? b.content : '',
        props: b.props && typeof b.props === 'object' ? { ...b.props } : {},
      }))
      content.value.splice(blockIndex, 1, ...normalized)
      hasChanges.value = true
      removeAiPreviewBlocks()
      nextTick(() => {
        blockEditorRef.value?.focusBlock?.(blockIndex, { cursor: 'end', align: 'nearest' })
      })
      return
    }
  }
  for (let i = 0; i < content.value.length; i++) {
    if (content.value[i].content.includes(oldText)) {
      content.value[i].content = content.value[i].content.replace(oldText, newText)
      hasChanges.value = true
      removeAiPreviewBlocks()
      return
    }
  }
}

function formatTime(date: Date) {
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

// 监听页面关闭，提示未保存
onBeforeUnmount(() => {
  if (hasChanges.value) {
    saveDocument()
  }
})

// 阻止页面级别的 Ctrl+A 选择，让编辑器自己处理
function handleDocumentKeydown(event: KeyboardEvent) {
  const isMod = event.ctrlKey || event.metaKey
  const key = event.key.toLowerCase()

  if (isMod && key === 'a') {
    const activeElement = globalThis.document.activeElement as HTMLElement | null
    const isInEditor = activeElement?.closest('.block-editor') !== null
    if (!isInEditor) {
      event.preventDefault()
    }
  }
}

onMounted(() => {
  loadDocument()
  xiaoMo.registerDocumentBridge({
    insert: (text, position) => insertText(text, position),
    insertBlocks: (blocks, position) => insertBlocksFromAi(blocks, position),
    replace: (oldText, newText, blockIndex, blocks, blockIndices) =>
      replaceText(oldText, newText, blockIndex, blocks, blockIndices),
    preview: (payload) => onAiPreview(payload),
    previewCancel: () => onAiPreviewCancel(),
    getEditFocus: () => {
      const focus = blockEditorRef.value?.getEditFocus?.()
      if (!focus?.text?.trim()) return null
      return {
        text: focus.text,
        blockIndex: focus.blockIndex,
        blockIndices: focus.blockIndices,
        blockIds: resolveBlockIds(focus.blockIndex, focus.blockIndices),
      }
    },
  })
  // 启动自动保存
  autoSaveInterval = window.setInterval(() => {
    if (hasChanges.value && documentId.value) {
      saveDocument()
    }
  }, 60000)
  // 添加键盘事件监听
  window.document.addEventListener('keydown', handleDocumentKeydown)
})

onUnmounted(() => {
  xiaoMo.registerDocumentBridge(null)
  if (autoSaveInterval) {
    clearInterval(autoSaveInterval)
  }
  if (tocJumpRaf != null) {
    cancelAnimationFrame(tocJumpRaf)
    tocJumpRaf = null
  }
  clearTocCollapseTimer()
  window.document.removeEventListener('keydown', handleDocumentKeydown)
})
</script>

<style scoped lang="scss">
.document-editor {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--coffee-bg);
}

.editor-header {
  min-height: 64px;
  height: auto;
  padding: 12px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  background: var(--coffee-bg-card);
  border-bottom: 1px solid var(--coffee-border);
  box-shadow: 0 2px 8px var(--coffee-shadow);
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 10px;
  
  .project-name {
    font-size: 14px;
    color: var(--coffee-text-muted);
    max-width: 150px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  .separator {
    font-size: 12px;
    color: var(--coffee-text-light);
  }
  
  .title-input {
    
    :deep(.el-input__wrapper) {
      box-shadow: none;
      padding: 0;
    }
    
    :deep(.el-input__inner) {
      font-size: 16px;
      font-weight: 600;
      color: var(--coffee-text);
      border: none;
      padding: 0;
      
      &::placeholder {
        color: var(--coffee-text-light);
      }
    }
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
  min-width: 0;

  .header-dropdown .btn .arrow-icon {
    font-size: 12px;
  }

  :deep(.export-menu .btn .arrow-icon) {
    font-size: 12px;
  }
}

.save-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--coffee-text-light);
  padding: 6px 12px;
  border-radius: 6px;
  background: var(--coffee-bg-warm);
  white-space: nowrap;
  
  .el-icon {
    font-size: 14px;
  }
  
  &.saved {
    color: var(--coffee-success);
  }
}

@media (max-width: 1024px) {
  .header-right {
    :deep(.btn span) {
      display: none;
    }
    :deep(.btn) {
      padding: 0 12px;
      .el-icon {
        margin-right: 0;
      }
    }
  }
}

.editor-container {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-height: 0;
}

.editor-main {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 40px;
  position: relative;
  z-index: 2; /* 高于右侧 AI 面板，避免快捷栏被遮挡 */
  &.with-chat {
    flex: 0 0 60%;
  }
}

.doc-outline {
  position: absolute;
  right: 16px;
  top: 40px;
  width: 220px;
  max-height: calc(100% - 80px);
  overflow: auto;
  background: var(--coffee-bg-card);
  border: 1px solid var(--coffee-border);
  border-radius: 12px;
  box-shadow: 0 4px 14px var(--coffee-shadow);
  padding: 8px;
  z-index: 3;
  transition: width 0.2s ease;

  &.is-collapsed {
    width: 44px;
    overflow: hidden;
    padding: 8px 6px;
  }
}

.outline-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.outline-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--coffee-text-muted);
  margin: 2px 8px;
}

.outline-toggle {
  border: none;
  background: transparent;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  color: var(--coffee-text-muted);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;

  &:hover {
    background: var(--coffee-shadow);
    color: var(--coffee-primary);
  }
}

.outline-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.outline-item {
  width: 100%;
  border: none;
  background: transparent;
  color: var(--coffee-text-secondary);
  text-align: left;
  font-size: 13px;
  line-height: 1.35;
  border-radius: 8px;
  padding: 7px 8px;
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;

  &:hover {
    background: var(--coffee-shadow);
    color: var(--coffee-primary);
  }

  &.is-sub {
    padding-left: 20px;
    font-size: 12px;
  }
}

.editor-content {
  width: 100%;
  margin: 0 auto;
  background: var(--coffee-bg-card);
  border-radius: 16px;
  padding: 48px;
  box-shadow: 0 4px 20px var(--coffee-shadow);
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: max-width 0.2s ease;
}

@media (max-width: 768px) {
  .editor-header {
    padding: 8px 16px;
  }

  .header-left {
    min-width: 0;
  }

  .breadcrumb {
    .project-name {
      max-width: 80px;
    }
    .title-input {
      width: 120px;
      min-width: 0;
    }
  }

  .header-right {
    gap: 6px;
  }

  .editor-main {
    padding: 20px;

    &.with-chat {
      flex: 0 0 100%;
    }
  }

  .doc-outline {
    display: none;
  }

  .editor-content {
    padding: 24px;
  }

  .save-status span {
    display: none;
  }
}

</style>
