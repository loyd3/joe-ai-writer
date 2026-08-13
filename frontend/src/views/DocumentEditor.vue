<template>
  <div class="document-editor">
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
          class="btn"
          :type="showChatPanel ? 'primary' : 'default'"
          @click="showChatPanel = !showChatPanel"
        >
          <el-icon><ChatDotRound /></el-icon>
          <span>AI 助手</span>
        </el-button>
        <el-button
          class="btn"
          :type="previewMode ? 'primary' : 'default'"
          @click="previewMode = !previewMode"
        >
          <el-icon><View /></el-icon>
          <span>{{ previewMode ? '退出预览' : '预览' }}</span>
        </el-button>
        <el-dropdown trigger="click" placement="bottom-end" popper-class="coffee-dropdown" @command="handleMoreCommand" class="header-dropdown">
          <el-button class="btn">
            <el-icon><MagicStick /></el-icon>
            <span>AI 工具</span>
            <el-icon class="arrow-icon"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu class="coffee-dropdown-menu">
              <el-dropdown-item command="format-style" :disabled="!content.length">
                <div class="dd-item">
                  <span class="dd-icon"><el-icon><SetUp /></el-icon></span>
                  <div class="dd-meta">
                    <span class="dd-title">AI 调整样式</span>
                    <span class="dd-desc">优化结构与排版，不改内容</span>
                  </div>
                </div>
              </el-dropdown-item>
              <el-dropdown-item command="split-sections" :disabled="!content.length">
                <div class="dd-item">
                  <span class="dd-icon"><el-icon><Files /></el-icon></span>
                  <div class="dd-meta">
                    <span class="dd-title">按章节拆分为多篇</span>
                    <span class="dd-desc">拆成多篇文档，按序加入项目</span>
                  </div>
                </div>
              </el-dropdown-item>
              <el-dropdown-item command="extract">
                <div class="dd-item">
                  <span class="dd-icon"><el-icon><Aim /></el-icon></span>
                  <div class="dd-meta">
                    <span class="dd-title">AI 智能扩展</span>
                    <span class="dd-desc">扩展为长篇项目</span>
                  </div>
                </div>
              </el-dropdown-item>
              <el-dropdown-item command="generate">
                <div class="dd-item">
                  <span class="dd-icon"><el-icon><MagicStick /></el-icon></span>
                  <div class="dd-meta">
                    <span class="dd-title">根据设定生成</span>
                    <span class="dd-desc">用项目设定续写或生成</span>
                  </div>
                </div>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-dropdown trigger="click" placement="bottom-end" popper-class="coffee-dropdown" @command="handleMoreCommand" class="header-dropdown">
          <el-button class="btn">
            <el-icon><Picture /></el-icon>
            <span>插图</span>
            <el-icon class="arrow-icon"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu class="coffee-dropdown-menu">
              <el-dropdown-item command="image-full" :disabled="!content.length">
                <div class="dd-item">
                  <span class="dd-icon"><el-icon><Picture /></el-icon></span>
                  <div class="dd-meta">
                    <span class="dd-title">AI 插图（全文）</span>
                    <span class="dd-desc">根据全文生成配图</span>
                  </div>
                </div>
              </el-dropdown-item>
              <el-dropdown-item command="image-url">
                <div class="dd-item">
                  <span class="dd-icon"><el-icon><Link /></el-icon></span>
                  <div class="dd-meta">
                    <span class="dd-title">插入网络图片</span>
                    <span class="dd-desc">粘贴图片链接插入正文</span>
                  </div>
                </div>
              </el-dropdown-item>
              <el-dropdown-item command="image-upload">
                <div class="dd-item">
                  <span class="dd-icon"><el-icon><Upload /></el-icon></span>
                  <div class="dd-meta">
                    <span class="dd-title">上传本地图片</span>
                    <span class="dd-desc">从电脑选择图片插入</span>
                  </div>
                </div>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
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
              <el-dropdown-item command="video-script">
                <div class="dd-item">
                  <span class="dd-icon"><el-icon><VideoCamera /></el-icon></span>
                  <div class="dd-meta">
                    <span class="dd-title">转视频文案</span>
                    <span class="dd-desc">生成口播 / 短视频稿</span>
                  </div>
                </div>
              </el-dropdown-item>
              <el-dropdown-item command="film-script">
                <div class="dd-item">
                  <span class="dd-icon"><el-icon><Film /></el-icon></span>
                  <div class="dd-meta">
                    <span class="dd-title">转影视脚本</span>
                    <span class="dd-desc">转为分镜剧本格式</span>
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
              <el-dropdown-item command="rename">
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
      <div class="editor-main" :class="{ 'with-chat': showChatPanel }">
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
        <div class="editor-content">
          <BlockEditor 
            ref="blockEditorRef"
            v-model="content"
            :preview-mode="previewMode"
            @update:modelValue="onContentChange"
            @content-dirty="onContentChange"
            @polish="onPolish"
            @polish-selected="onPolishSelected"
            @format-style="onFormatStyle"
            @format-style-selected="onFormatStyleSelected"
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

    <VideoScriptDialog
      v-model="showVideoScriptDialog"
      :document-id="Number(documentId)"
      :raw-blocks="blocksSnapshotForImageApi()"
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
import VideoScriptDialog from '@/components/VideoScriptDialog.vue'
import SplitDocumentDialog from '@/components/SplitDocumentDialog.vue'
import { parseFormattedTextToBlocks } from '@/utils/formatToBlocks'
import { ElMessageBox } from 'element-plus'
import { aiApi } from '@/api'
import { ArrowLeft, ArrowRight, ArrowDown, ChatDotRound, Check, Loading, CircleCheck, MoreFilled, Edit, Delete, Aim, MagicStick, Files, Promotion, Picture, Link, Upload, View, VideoCamera, Film, SetUp } from '@element-plus/icons-vue'

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
/** 预览模式：正文不可直接编辑，仍可调整块结构、AI、撤销等 */
const previewMode = ref(false)
const aiChatRef = ref<{
  polishWithText: (text: string, blockIndex?: number) => Promise<void>
  polishWithSelectedText: (text: string, blockIndices: number[]) => Promise<void>
  formatStyleWithText: (text: string, blockIndex?: number) => Promise<void>
  formatStyleWithSelectedText: (text: string, blockIndices: number[]) => Promise<void>
  reviseWithSelectedText: (text: string, blockIndices: number[]) => Promise<void>
  expandWithSelectedText: (text: string, blockIndices: number[]) => Promise<void>
} | null>(null)
const blockEditorRef = ref<{ getImageInsertAfterIndex: () => number; flushPendingSync: () => void; focusBlock: (index: number, opts?: { cursor?: 'start' | 'end' | number; align?: 'start' | 'nearest'; behavior?: ScrollBehavior; focus?: boolean; preventScroll?: boolean; force?: boolean }) => void } | null>(null)
const showPublishDialog = ref(false)
const showVideoScriptDialog = ref(false)
const showSplitDialog = ref(false)
const generatingImage = ref(false)
const uploadingImage = ref(false)
const documentImageUploadRef = ref<HTMLInputElement | null>(null)

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
      focus: !previewMode.value,
      cursor: 'start',
      force: !previewMode.value,
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

watch(showChatPanel, (open) => {
  if (open) {
    tocCollapsed.value = true
    tocPinnedOpen.value = false
    clearTocCollapseTimer()
  }
})

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

function onFormatStyle(payload: { index: number; text: string }) {
  showChatPanel.value = true
  nextTick(() => {
    aiChatRef.value?.formatStyleWithText(payload.text, payload.index)
  })
}

function onFormatStyleSelected(payload: { indices: number[]; text: string }) {
  showChatPanel.value = true
  nextTick(() => {
    aiChatRef.value?.formatStyleWithSelectedText(payload.text, payload.indices)
  })
}

/** 对整篇文档做仅排版优化 */
function onFormatStyleDocument() {
  const targets = content.value
    .map((b, i) => ({ b, i }))
    .filter(({ b }) => b && b.type !== 'image' && stripHtmlToText(b.content || '').trim())
  const parts = targets.map(({ b }) => stripHtmlToText(b.content))
  const text = parts.join('\n\n')
  if (!text.trim()) {
    ElMessage.warning('文档暂无内容可调整')
    return
  }
  const indices = targets.map(({ i }) => i)
  showChatPanel.value = true
  nextTick(() => {
    aiChatRef.value?.formatStyleWithSelectedText(text, indices)
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

  blockEditorRef.value?.flushPendingSync?.()
  await nextTick()

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
  if (command === 'format-style') {
    onFormatStyleDocument()
  } else if (command === 'split-sections') {
    openSplitDialog()
  } else if (command === 'extract') {
    showExtractDrawer.value = true
  } else if (command === 'image-full') {
    void generateAndInsertArticleImage()
  } else if (command === 'image-url') {
    void promptInsertImageUrl()
  } else if (command === 'image-upload') {
    triggerDocumentImageUpload()
  } else if (command === 'generate') {
    showGenerateDrawer.value = true
  } else if (command === 'publish') {
    showPublishDialog.value = true
  } else if (command === 'video-script') {
    showVideoScriptDialog.value = true
  } else if (command === 'film-script') {
    void convertToFilmScript()
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
    await loadDocument()
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
  const startIndex = content.value.length
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
  nextTick(() => {
    blockEditorRef.value?.focusBlock?.(startIndex, { cursor: 'end', align: 'nearest' })
  })
}

function getImageInsertAfterIndexFromEditor(): number {
  const fn = blockEditorRef.value?.getImageInsertAfterIndex
  if (typeof fn === 'function') return fn()
  const n = content.value.length
  if (n === 0) return -1
  return n - 1
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

const convertingFilmScript = ref(false)

async function convertToFilmScript() {
  if (convertingFilmScript.value) return
  if (!content.value.length) {
    ElMessage.warning('文档内容为空，无法转换')
    return
  }
  convertingFilmScript.value = true
  const loading = ElMessage({ message: '正在转换为影视脚本，请稍候...', type: 'info', duration: 0 })
  try {
    if (hasChanges.value) await saveDocument()
    const res = await aiApi.convertToFilmScript({
      document_id: Number(documentId.value),
      blocks: blocksSnapshotForImageApi(),
    })
    const data = res.data?.data
    if (!data?.script_text) throw new Error('empty script')
    const projectId = document.value?.project_id
    if (!projectId) throw new Error('no project')
    const title = (data.script_title || `${documentTitle.value}·影视脚本`).slice(0, 100)
    const blocks = parseFormattedTextToBlocks(data.script_text, 'doc')
    const newDoc = await store.createDocument(projectId, { title, content: blocks })
    ElMessage.success('已生成影视脚本文档')
    router.push(`/document/${newDoc.id}`)
  } catch (e) {
    console.error(e)
    ElMessage.error(messageFromAxiosError(e, '转换影视脚本失败，请稍后重试'))
  } finally {
    loading.close()
    convertingFilmScript.value = false
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
  const startIndex = content.value.length
  const normalize = (b: Block): Block => ({
    id: b.id && String(b.id).length ? String(b.id) : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`,
    type: b.type || 'paragraph',
    content: typeof b.content === 'string' ? b.content : '',
    props: b.props && typeof b.props === 'object' ? { ...b.props } : {},
  })
  content.value.push(...blocks.map(normalize))
  hasChanges.value = true
  nextTick(() => {
    blockEditorRef.value?.focusBlock?.(startIndex, { cursor: 'end', align: 'nearest' })
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
    nextTick(() => {
      blockEditorRef.value?.focusBlock?.(indices[0], { cursor: 'end', align: 'nearest' })
    })
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
    color: #67c23a;
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
  max-width: 800px;
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

.doc-hidden-file-input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
  overflow: hidden;
}

</style>
