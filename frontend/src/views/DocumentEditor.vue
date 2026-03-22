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
        <el-dropdown trigger="click" @command="handleImageMenuCommand">
          <el-button class="article-image-btn" :loading="generatingImage || uploadingImage">
            <el-icon><Picture /></el-icon>
            <span>图片</span>
            <el-icon class="arrow-icon"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="full-image" :disabled="!content.length">
                <el-icon><Picture /></el-icon>
                AI 插图（全文）
              </el-dropdown-item>
              <el-dropdown-item command="url-image">
                <el-icon><Link /></el-icon>
                插入网络图片…
              </el-dropdown-item>
              <el-dropdown-item command="upload-image">
                <el-icon><Upload /></el-icon>
                上传本地图片…
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
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
              <el-dropdown-item command="extract">
              <el-icon><Aim /></el-icon> AI 智能扩展
              </el-dropdown-item>
              <el-dropdown-item command="image-full" :disabled="!content.length">
                <el-icon><Picture /></el-icon> AI 插图（全文）
              </el-dropdown-item>
              <el-dropdown-item command="image-url">
                <el-icon><Link /></el-icon> 插入网络图片…
              </el-dropdown-item>
              <el-dropdown-item command="image-upload">
                <el-icon><Upload /></el-icon> 上传本地图片…
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
              <el-dropdown-item divided command="publish">
                <el-icon><Promotion /></el-icon> 发布到自媒体
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
          <el-button class="extract-btn" @click="showExtractDrawer = true">
            <el-icon><Aim /></el-icon>
          <span>AI 智能扩展</span>
          </el-button>
          <el-dropdown trigger="click" @command="handleImageMenuCommand">
            <el-button class="extract-btn" :loading="generatingImage || uploadingImage">
              <el-icon><Picture /></el-icon>
              <span>图片</span>
              <el-icon class="arrow-icon"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="full-image" :disabled="!content.length">
                  <el-icon><Picture /></el-icon>
                  AI 插图（全文）
                </el-dropdown-item>
                <el-dropdown-item command="url-image">
                  <el-icon><Link /></el-icon>
                  插入网络图片…
                </el-dropdown-item>
                <el-dropdown-item command="upload-image">
                  <el-icon><Upload /></el-icon>
                  上传本地图片…
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button class="generate-btn" @click="showGenerateDrawer = true">
            <el-icon><MagicStick /></el-icon>
            <span>根据设定生成</span>
          </el-button>
          <el-dropdown
            trigger="click"
            class="export-dropdown"
            @command="(cmd: string) => exportMenuRef?.triggerExport(cmd)"
          >
            <el-button class="extract-btn export-dropdown-btn">
              <el-icon><Download /></el-icon>
              <span>导出</span>
              <el-icon class="arrow-icon"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="markdown">
                  <el-icon><Document /></el-icon> Markdown
                </el-dropdown-item>
                <el-dropdown-item command="pdf">
                  <el-icon><Collection /></el-icon> PDF
                </el-dropdown-item>
                <el-dropdown-item command="docx">
                  <el-icon><Files /></el-icon> Word
                </el-dropdown-item>
                <el-dropdown-item command="txt">
                  <el-icon><Document /></el-icon> 纯文本
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button class="extract-btn" @click="showPublishDialog = true">
            <el-icon><Promotion /></el-icon>
            <span>发布到自媒体</span>
          </el-button>
          <el-button class="extract-btn" @click="handleDocCommand('rename')">
            <el-icon><Edit /></el-icon>
            <span>重命名</span>
          </el-button>
          <el-button class="header-delete-btn" type="danger" @click="handleDocCommand('delete')">
            <el-icon><Delete /></el-icon>
            <span>删除文档</span>
          </el-button>
        </template>
        <ExportMenu
          ref="exportMenuRef"
          mode="document"
          :show-button="false"
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
            ref="blockEditorRef"
            v-model="content" 
            @update:modelValue="onContentChange"
            @polish="onPolish"
            @polish-selected="onPolishSelected"
            @revise-selected="onReviseSelected"
            @expand-selected="onExpandSelected"
            @generate-image-for-selection="onGenerateImageForSelection"
          />
        </div>
      </div>
      
      <AIChatPanel
        v-if="showChatPanel"
        ref="aiChatRef"
        :document-id="Number(documentId)"
        :content="content"
        @insert="insertText"
        @insert-blocks="insertBlocksFromAi"
        @preview="onAiPreview"
        @preview-cancel="onAiPreviewCancel"
        @replace="(oldText, newText, blockIndex, blocks, blockIndices) => replaceText(oldText, newText, blockIndex, blocks, blockIndices)"
      />
    </div>

    <el-drawer
      v-model="showExtractDrawer"
      title="AI 扩展为长篇项目"
      size="520px"
      direction="rtl"
      class="extract-drawer"
      destroy-on-close
    >
      <AIExtract
        v-if="document?.project_id"
        :document-id="Number(documentId)"
        :project-id="document.project_id"
        :document-title="documentTitle"
        :content="content"
        @project-created="onProjectFromArticleCreated"
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

    <PublishDialog
      v-model="showPublishDialog"
      :document-id="Number(documentId)"
    />

    <input
      ref="documentImageUploadRef"
      type="file"
      accept="image/jpeg,image/jpg,image/png,image/gif,image/webp"
      class="doc-hidden-file-input"
      @change="onDocumentImageFileChange"
    />
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
import PublishDialog from '@/components/PublishDialog.vue'
import { parseFormattedTextToBlocks } from '@/utils/formatToBlocks'
import { ElMessageBox } from 'element-plus'
import { aiApi } from '@/api'
import { ArrowLeft, ArrowRight, ArrowDown, ArrowUp, ChatDotRound, Check, Loading, CircleCheck, MoreFilled, Edit, Delete, Aim, MagicStick, Document, Collection, Files, Promotion, Download, Picture, Link, Upload } from '@element-plus/icons-vue'

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
/** AI 预览块：插入到文档末尾，仅用于阅读与 diff 接受/拒绝；未接受前不应自动保存 */
const aiPreviewId = ref<string | null>(null)
const AI_PREVIEW_KEY = '__ai_preview_id'
const lastSaved = ref<Date | null>(null)
const aiChatRef = ref<{
  polishWithText: (text: string, blockIndex?: number) => Promise<void>
  polishWithSelectedText: (text: string, blockIndices: number[]) => Promise<void>
  reviseWithSelectedText: (text: string, blockIndices: number[]) => Promise<void>
  expandWithSelectedText: (text: string, blockIndices: number[]) => Promise<void>
} | null>(null)
const exportMenuRef = ref<{ triggerExport: (command: string) => void } | null>(null)
const blockEditorRef = ref<{ getImageInsertAfterIndex: () => number } | null>(null)
// 默认先折叠：只展示“保存、AI 助手、更多”
const headerExpanded = ref(false)
const showPublishDialog = ref(false)
const generatingImage = ref(false)
const uploadingImage = ref(false)
const documentImageUploadRef = ref<HTMLInputElement | null>(null)

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

function onPolishSelected(payload: { indices: number[]; text: string }) {
  showChatPanel.value = true
  nextTick(() => {
    aiChatRef.value?.polishWithSelectedText(payload.text, payload.indices)
  })
}

function onReviseSelected(payload: { indices: number[]; text: string }) {
  showChatPanel.value = true
  nextTick(() => {
    aiChatRef.value?.reviseWithSelectedText(payload.text, payload.indices)
  })
}

function onExpandSelected(payload: { indices: number[]; text: string }) {
  showChatPanel.value = true
  nextTick(() => {
    aiChatRef.value?.expandWithSelectedText(payload.text, payload.indices)
  })
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

async function onProjectFromArticleCreated(projectId: number, documentId: number) {
  showExtractDrawer.value = false
  ElMessage.success('项目创建成功，正在导入原文并进入新文档...')
  router.push(`/document/${documentId}`)
}

function goBack() {
  if (project.value) {
    router.push(`/project/${project.value.id}`)
  } else {
    router.push('/')
  }
}

function handleMoreCommand(command: string) {
  if (command === 'extract') {
    showExtractDrawer.value = true
  } else if (command === 'image-full') {
    void generateAndInsertArticleImage()
  } else if (command === 'image-url') {
    void promptInsertImageUrl()
  } else if (command === 'image-upload') {
    triggerDocumentImageUpload()
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
  } else if (command === 'publish') {
    showPublishDialog.value = true
  } else if (command === 'rename' || command === 'delete') {
    handleDocCommand(command)
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

function getImageInsertAfterIndexFromEditor(): number {
  const fn = blockEditorRef.value?.getImageInsertAfterIndex
  if (typeof fn === 'function') return fn()
  const n = content.value.length
  if (n === 0) return -1
  return n - 1
}

function handleImageMenuCommand(cmd: string) {
  if (cmd === 'full-image') void generateAndInsertArticleImage()
  else if (cmd === 'url-image') void promptInsertImageUrl()
  else if (cmd === 'upload-image') triggerDocumentImageUpload()
}

function triggerDocumentImageUpload() {
  documentImageUploadRef.value?.click()
}

async function onDocumentImageFileChange(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  if (!file.type.startsWith('image/')) {
    ElMessage.warning('请选择图片文件')
    return
  }
  uploadingImage.value = true
  try {
    const res = await aiApi.uploadDocumentImage(Number(documentId.value), file)
    const data = res.data as { url?: string }
    if (!data?.url) {
      ElMessage.warning('上传失败')
      return
    }
    const after = getImageInsertAfterIndexFromEditor()
    insertBlocksAfterIndex(after, [{ id: '', type: 'image', content: '', props: { src: data.url, alt: '' } }])
    ElMessage.success('图片已插入到当前位置之后，记得保存')
  } catch (e) {
    console.error(e)
  } finally {
    uploadingImage.value = false
  }
}

async function promptInsertImageUrl() {
  try {
    const res = await ElMessageBox.prompt('请输入图片地址（http/https）', '插入网络图片', {
      confirmButtonText: '插入',
      cancelButtonText: '取消',
      inputPlaceholder: 'https://example.com/image.png',
      inputPattern: /^https?:\/\/.+/i,
      inputErrorMessage: '请输入以 http:// 或 https:// 开头的地址',
    })
    const url = String((res as { value?: string }).value ?? '').trim()
    if (!url) return
    const after = getImageInsertAfterIndexFromEditor()
    insertBlocksAfterIndex(after, [{ id: '', type: 'image', content: '', props: { src: url, alt: '' } }])
    ElMessage.success('图片已插入到当前位置之后，记得保存')
  } catch {
    // 取消
  }
}

function blocksSnapshotForImageApi(): Block[] {
  try {
    return JSON.parse(JSON.stringify(content.value)) as Block[]
  } catch {
    return [...content.value]
  }
}

function messageFromAxiosError(e: unknown, fallback: string): string {
  const ax = e as { response?: { data?: { detail?: unknown } } }
  const d = ax.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d) && d.length && typeof (d[0] as { msg?: string }).msg === 'string') {
    return (d[0] as { msg: string }).msg
  }
  return fallback
}

async function onGenerateImageForSelection(payload: { indices: number[]; text: string }) {
  const { indices, text } = payload
  if (!indices.length || !text.trim()) return
  generatingImage.value = true
  try {
    const res = await aiApi.generateArticleImage({
      document_id: Number(documentId.value),
      context_text: text,
      style: '',
      extra_hint: '',
      blocks: blocksSnapshotForImageApi(),
    })
    const data = res.data as {
      success?: boolean
      block?: Block
    }
    if (data?.block) {
      const after = Math.max(...indices)
      insertBlocksAfterIndex(after, [data.block])
      ElMessage.success('插图已插入到选中段落之后，记得保存')
    } else {
      ElMessage.warning('未返回插图数据')
    }
  } catch (e) {
    console.error(e)
    ElMessage.error(messageFromAxiosError(e, '生成插图失败'))
  } finally {
    generatingImage.value = false
  }
}

function insertBlocksAfterIndex(afterIndex: number, blocks: Block[]) {
  if (!blocks?.length) return
  const normalize = (b: Block): Block => ({
    id: b.id && String(b.id).length ? String(b.id) : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`,
    type: b.type || 'paragraph',
    content: typeof b.content === 'string' ? b.content : '',
    props: b.props && typeof b.props === 'object' ? { ...b.props } : {},
  })
  const normalized = blocks.map(normalize)
  const next = [...content.value]
  const at = Math.max(0, Math.min(afterIndex + 1, next.length))
  next.splice(at, 0, ...normalized)
  content.value = next
  hasChanges.value = true
}

/** 根据当前文档正文调用后端文生图，插入 image 块到文末 */
async function generateAndInsertArticleImage() {
  if (!content.value.length) {
    ElMessage.warning('请先撰写一些正文，再生成插图')
    return
  }
  generatingImage.value = true
  try {
    const res = await aiApi.generateArticleImage({
      document_id: Number(documentId.value),
      style: '',
      extra_hint: '',
      blocks: blocksSnapshotForImageApi(),
    })
    const data = res.data as {
      success?: boolean
      block?: Block
      prompt?: string
      image_url?: string
    }
    if (data?.block) {
      insertBlocksFromAi([data.block])
      ElMessage.success('插图已插入到文档末尾，记得保存')
    } else {
      ElMessage.warning('未返回插图数据')
    }
  } catch (e: unknown) {
    console.error(e)
    ElMessage.error(messageFromAxiosError(e, '生成插图失败'))
  } finally {
    generatingImage.value = false
  }
}

/** AI 助手返回的 blocks（与后端 / 脑洞写作解析一致）直接插入文档末尾 */
function insertBlocksFromAi(blocks: Block[]) {
  if (!blocks?.length) return
  const normalize = (b: Block): Block => ({
    id: b.id && String(b.id).length ? String(b.id) : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`,
    type: b.type || 'paragraph',
    content: typeof b.content === 'string' ? b.content : '',
    props: b.props && typeof b.props === 'object' ? { ...b.props } : {},
  })
  content.value.push(...blocks.map(normalize))
  hasChanges.value = true
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
  // 多选块：把 AI 输出的 blocks 替换到选中的块集合上
  if (blockIndices?.length) {
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
    return
  }

  // AI 改写类操作通常会返回「编辑器块格式」文本。
  // 这里优先把改写结果解析为 Block，并用新块替换当前块，以确保块类型/样式匹配编辑器。
  if (blockIndex != null && blockIndex >= 0 && blockIndex < content.value.length) {
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

  .export-dropdown {
    display: inline-flex;
    .export-dropdown-btn {
      .el-icon.arrow-icon {
        margin-left: 6px;
        margin-right: 0;
        font-size: 12px;
      }
    }
  }

  .header-delete-btn {
    height: 40px;
    padding: 0 16px;
    border-radius: 8px;
    .el-icon {
      margin-right: 6px;
    }
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

.doc-hidden-file-input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
  overflow: hidden;
}

</style>
