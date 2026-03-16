<template>
  <div class="document-editor">
    <div class="editor-header">
      <div class="header-left">
        <el-button link class="back-btn" @click="goBack">
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
        <!-- 折叠时只显示 3 个：保存、AI 助手、更多 -->
        <el-button class="save-btn" type="primary" @click="saveDocument" :loading="saving">
          <el-icon><Check /></el-icon>
          <span>保存</span>
        </el-button>
        <el-button 
          class="chat-toggle" 
          :type="showChatPanel ? 'primary' : 'default'"
          @click="showChatPanel = !showChatPanel"
        >
          <el-icon><ChatDotRound /></el-icon>
          <span>AI 助手</span>
        </el-button>
        <el-dropdown v-if="!headerExpanded" trigger="click" @command="handleMoreCommand" class="doc-actions-dropdown">
          <el-button class="more-btn">
            <el-icon><MoreFilled /></el-icon>
            <span>更多</span>
            <el-icon class="arrow-icon"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="format-doc">
                <el-icon><Document /></el-icon> 整理排版
                <span class="shortcut-hint">Ctrl+Shift+F</span>
              </el-dropdown-item>
              <el-dropdown-item divided command="extract">
                <el-icon><Aim /></el-icon> AI 智能提取
              </el-dropdown-item>
              <el-dropdown-item command="generate">
                <el-icon><MagicStick /></el-icon> 根据设定生成
              </el-dropdown-item>
              <el-dropdown-item command="export-markdown">
                <el-icon><Document /></el-icon> 导出 Markdown
              </el-dropdown-item>
              <el-dropdown-item command="export-pdf">
                <el-icon><Collection /></el-icon> 导出 PDF
              </el-dropdown-item>
              <el-dropdown-item command="export-docx">
                <el-icon><Files /></el-icon> 导出 Word
              </el-dropdown-item>
              <el-dropdown-item command="export-txt">
                <el-icon><Document /></el-icon> 导出纯文本
              </el-dropdown-item>
              <el-dropdown-item divided command="rename">
                <el-icon><Edit /></el-icon> 重命名
              </el-dropdown-item>
              <el-dropdown-item command="delete" class="delete-item">
                <el-icon><Delete /></el-icon> 删除文档
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <!-- 展开时显示的其余按钮 -->
        <template v-if="headerExpanded">
          <el-button class="format-doc-btn" @click="doFormatDocument" title="整理排版 (Ctrl+Shift+F)">
            <el-icon><Sort /></el-icon>
            <span>整理排版</span>
          </el-button>
          <el-button class="extract-btn" @click="showExtractDrawer = true">
            <el-icon><Aim /></el-icon>
            <span>AI 智能提取</span>
          </el-button>
          <el-button class="generate-btn" @click="showGenerateDrawer = true">
            <el-icon><MagicStick /></el-icon>
            <span>根据设定生成</span>
          </el-button>
        </template>
        <ExportMenu
          ref="exportMenuRef"
          mode="document"
          :show-button="headerExpanded"
          :document-id="Number(documentId)"
          :document-title="documentTitle"
        />
        <el-button
          v-if="headerExpanded"
          class="collapse-btn"
          link
          @click="headerExpanded = false"
        >
          <el-icon><ArrowUp /></el-icon>
          <span>收起</span>
        </el-button>
        <el-button
          v-else
          class="expand-btn"
          link
          @click="headerExpanded = true"
        >
          <el-icon><ArrowDown /></el-icon>
          <span>展开</span>
        </el-button>
      </div>
    </div>

    <div class="editor-container">
      <div class="editor-main" :class="{ 'with-chat': showChatPanel }">
        <div class="editor-content">
          <BlockEditor 
            v-model="content" 
            @update:modelValue="onContentChange"
            @polish="onPolish"
          />
        </div>
      </div>
      
      <AIChatPanel
        v-if="showChatPanel"
        ref="aiChatRef"
        :document-id="Number(documentId)"
        :content="content"
        @insert="insertText"
        @replace="(oldText, newText, blockIndex) => replaceText(oldText, newText, blockIndex)"
      />
    </div>

    <el-drawer
      v-model="showExtractDrawer"
      title="AI 智能提取"
      size="520px"
      direction="rtl"
      class="extract-drawer"
      destroy-on-close
    >
      <AIExtract
        v-if="document?.project_id"
        :document-id="Number(documentId)"
        :project-id="document.project_id"
        :content="content"
        @applied="onExtractApplied"
      />
    </el-drawer>

    <el-drawer
      v-model="showGenerateDrawer"
      title="根据项目设定生成"
      size="520px"
      direction="rtl"
      class="generate-drawer"
      destroy-on-close
    >
      <AIGenerateFromMemory
        v-if="document?.project_id"
        :project-id="document.project_id"
        :document-id="Number(documentId)"
        :current-content="content"
        @insert="insertText"
      />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, onUnmounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore, type Block } from '@/stores/project'
import { ElMessage } from 'element-plus'
import BlockEditor from '@/components/BlockEditor.vue'
import AIChatPanel from '@/components/AIChatPanel.vue'
import AIExtract from '@/components/AIExtract.vue'
import AIGenerateFromMemory from '@/components/AIGenerateFromMemory.vue'
import ExportMenu from '@/components/ExportMenu.vue'
import { parseFormattedTextToBlocks } from '@/utils/formatToBlocks'
import { ElMessageBox } from 'element-plus'
import { ArrowLeft, ArrowRight, ArrowDown, ArrowUp, ChatDotRound, Check, Loading, CircleCheck, MoreFilled, Edit, Delete, Aim, MagicStick, Document, Collection, Files, Sort } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const store = useProjectStore()

const documentId = computed(() => route.params.id as string)
const document = computed(() => store.currentDocument)
const project = computed(() => store.currentProject)

const documentTitle = ref('')
const content = ref<Block[]>([])
const saving = ref(false)
const showChatPanel = ref(true)
const showExtractDrawer = ref(false)
const showGenerateDrawer = ref(false)
const hasChanges = ref(false)
const lastSaved = ref<Date | null>(null)
const aiChatRef = ref<{ polishWithText: (text: string, blockIndex?: number) => Promise<void> } | null>(null)
const exportMenuRef = ref<{ triggerExport: (command: string) => void } | null>(null)
const headerExpanded = ref(true)

let autoSaveInterval: number | null = null

watch(documentId, () => {
  loadDocument()
})

async function loadDocument() {
  await store.fetchDocument(Number(documentId.value))
  if (document.value) {
    documentTitle.value = document.value.title
    content.value = document.value.content || []
    if (document.value.project_id) {
      await store.fetchProject(document.value.project_id)
    }
  }
}

function onContentChange() {
  hasChanges.value = true
}

function onPolish(payload: { index: number; text: string }) {
  showChatPanel.value = true
  nextTick(() => {
    aiChatRef.value?.polishWithText(payload.text, payload.index)
  })
}

async function saveTitle() {
  if (documentTitle.value !== document.value?.title) {
    await store.updateDocument(Number(documentId.value), {
      title: documentTitle.value
    })
    ElMessage.success('标题已保存')
  }
}

async function saveDocument() {
  if (!hasChanges.value && !saving.value) return
  
  saving.value = true
  try {
    await store.updateDocument(Number(documentId.value), {
      title: documentTitle.value,
      content: content.value
    })
    hasChanges.value = false
    lastSaved.value = new Date()
  } finally {
    saving.value = false
  }
}

async function onExtractApplied() {
  showExtractDrawer.value = false
  if (document.value?.project_id) {
    await store.fetchMemory(document.value.project_id)
  }
}

function goBack() {
  if (project.value) {
    router.push(`/project/${project.value.id}`)
  } else {
    router.push('/')
  }
}

function handleMoreCommand(command: string) {
  if (command === 'format-doc') {
    doFormatDocument()
    return
  }
  if (command === 'extract') {
    showExtractDrawer.value = true
  } else if (command === 'generate') {
    showGenerateDrawer.value = true
  } else if (command === 'export-markdown') {
    exportMenuRef.value?.triggerExport('markdown')
  } else if (command === 'export-pdf') {
    exportMenuRef.value?.triggerExport('pdf')
  } else if (command === 'export-docx') {
    exportMenuRef.value?.triggerExport('docx')
  } else if (command === 'export-txt') {
    exportMenuRef.value?.triggerExport('txt')
  } else if (command === 'rename' || command === 'delete') {
    handleDocCommand(command)
  }
}

async function handleDocCommand(command: string) {
  if (command === 'rename') {
    try {
      const { value } = await ElMessageBox.prompt('输入新标题', '重命名文档', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputValue: documentTitle.value,
        inputPattern: /.{1,100}/,
        inputErrorMessage: '标题长度 1～100 个字符'
      })
      await store.updateDocument(Number(documentId.value), { title: value })
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

function insertText(text: string) {
  const blocks = parseFormattedTextToBlocks(text, 'doc')
  if (blocks.length) {
    content.value.push(...blocks)
  } else {
    content.value.push({
      id: Date.now().toString(),
      type: 'paragraph',
      content: text,
      props: {}
    })
  }
  hasChanges.value = true
}

function replaceText(oldText: string, newText: string, blockIndex?: number) {
  if (blockIndex != null && blockIndex >= 0 && content.value[blockIndex]?.content.includes(oldText)) {
    content.value[blockIndex].content = content.value[blockIndex].content.replace(oldText, newText)
    hasChanges.value = true
    return
  }
  for (let i = 0; i < content.value.length; i++) {
    if (content.value[i].content.includes(oldText)) {
      content.value[i].content = content.value[i].content.replace(oldText, newText)
      hasChanges.value = true
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

/** 一键整理排版：去除每块首尾空白、删除空块、段落内多余换行合并 */
function formatDocumentContent(blocks: Block[]): Block[] {
  if (!blocks?.length) return blocks
  const result: Block[] = []
  for (const b of blocks) {
    const trimmed = typeof b.content === 'string' ? b.content.trim() : ''
    if (b.type === 'divider') {
      result.push({ ...b, content: '' })
      continue
    }
    if (!trimmed) continue
    const normalized = trimmed.replace(/\n{3,}/g, '\n\n')
    result.push({ ...b, content: normalized })
  }
  if (result.length === 0) {
    return [{ id: String(Date.now()), type: 'paragraph', content: '', props: {} }]
  }
  return result
}

function doFormatDocument() {
  const next = formatDocumentContent(content.value)
  if (JSON.stringify(next) === JSON.stringify(content.value)) {
    ElMessage.info('当前文档已整洁，无需整理')
    return
  }
  content.value = next
  hasChanges.value = true
  ElMessage.success('已整理排版')
}

// 阻止页面级别的 Ctrl+A 选择，让编辑器自己处理；Ctrl+Shift+F 一键整理排版
function handleDocumentKeydown(event: KeyboardEvent) {
  const isMod = event.ctrlKey || event.metaKey
  const key = event.key.toLowerCase()

  if (isMod && event.shiftKey && key === 'f') {
    event.preventDefault()
    doFormatDocument()
    return
  }

  if (isMod && key === 'a') {
    const activeElement = document.activeElement
    const isInEditor = activeElement?.closest('.block-editor') !== null
    if (!isInEditor) {
      event.preventDefault()
    }
  }
}

onMounted(() => {
  loadDocument()
  // 启动自动保存
  autoSaveInterval = window.setInterval(() => {
    if (hasChanges.value && documentId.value) {
      saveDocument()
    }
  }, 30000)
  // 添加键盘事件监听
  window.document.addEventListener('keydown', handleDocumentKeydown)
})

onUnmounted(() => {
  if (autoSaveInterval) {
    clearInterval(autoSaveInterval)
  }
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
  
  .back-btn {
    width: 36px;
    height: 36px;
    border-radius: 8px;
    color: var(--coffee-text-muted);
    
    &:hover {
      background: var(--coffee-bg-warm);
      color: var(--coffee-primary);
    }
  }
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

  .doc-actions-dropdown .more-btn {
    height: 40px;
    padding: 0 12px;
    color: var(--coffee-text-muted);
    .arrow-icon {
      margin-left: 4px;
      font-size: 12px;
      transition: transform 0.2s;
      &.expanded { transform: rotate(180deg); }
    }
    &:hover {
      color: var(--coffee-primary);
    }
  }

  .collapse-btn,
  .expand-btn {
    height: 40px;
    padding: 0 8px;
    color: var(--coffee-text-muted);
    font-size: 13px;
    &:hover { color: var(--coffee-primary); }
    .el-icon { margin-right: 2px; font-size: 14px; }
  }

  :deep(.delete-item) {
    color: var(--el-color-danger);
  }

  :deep(.shortcut-hint) {
    margin-left: auto;
    font-size: 12px;
    color: var(--coffee-text-light);
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
    color: #67c23a;
  }
}

.chat-toggle,
.extract-btn,
.generate-btn {
  height: 40px;
  padding: 0 16px;
  border-radius: 8px;
  border-color: var(--coffee-border);
  color: var(--coffee-text-secondary);
  
  &:hover, &.el-button--primary {
    border-color: var(--coffee-primary);
    color: var(--coffee-primary);
    background: var(--coffee-bg-hover);
  }
  
  &.el-button--primary {
    background: var(--coffee-primary);
    color: #fff;
  }
  
  .el-icon {
    margin-right: 6px;
  }
}

.save-btn {
  height: 40px;
  padding: 0 20px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--coffee-primary) 0%, var(--coffee-primary-light) 100%);
  border: none;
  font-weight: 500;
  
  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px var(--coffee-selection);
  }
  
  .el-icon {
    margin-right: 6px;
  }
}

.editor-container {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.editor-main {
  flex: 1;
  overflow-y: auto;
  padding: 40px;
  position: relative;
  z-index: 2; /* 高于右侧 AI 面板，避免快捷栏被遮挡 */
  &.with-chat {
    flex: 0 0 60%;
  }
}

.editor-content {
  max-width: 800px;
  margin: 0 auto;
  background: var(--coffee-bg-card);
  border-radius: 16px;
  padding: 48px;
  box-shadow: 0 4px 20px var(--coffee-shadow);
  min-height: calc(100vh - 180px);
}

@media (max-width: 1024px) {
  .header-right {
    .chat-toggle span,
    .extract-btn span,
    .generate-btn span,
    .save-btn span {
      display: none;
    }
    .chat-toggle,
    .extract-btn,
    .generate-btn,
    .save-btn {
      padding: 0 12px;
      .el-icon {
        margin-right: 0;
      }
    }
  }
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

  .editor-content {
    padding: 24px;
  }

  .save-status span {
    display: none;
  }
}

</style>
