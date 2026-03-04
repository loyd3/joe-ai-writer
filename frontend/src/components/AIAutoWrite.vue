<template>
  <div class="ai-auto-write">
    <div class="auto-write-header">
      <h3>
        <el-icon><EditPen /></el-icon>
        AI 自动写作
      </h3>
      <p class="subtitle">基于大纲设定，逐章生成并插入到对应文档</p>
    </div>

    <!-- 第一步：选择大纲节点 -->
    <div v-if="step === 'select'" class="step-panel">
      <h4>选择要生成的章节</h4>
      <p class="hint">从项目大纲中选择需要 AI 自动写作的章节</p>
      
      <div v-if="outline.length === 0" class="empty-state">
        <el-icon :size="48"><Document /></el-icon>
        <p>暂无大纲数据</p>
        <p class="sub">请先在「项目设定」中创建大纲</p>
      </div>
      
      <el-checkbox-group v-else v-model="selectedNodes" class="outline-list">
        <div
          v-for="(node, index) in outline"
          :key="index"
          class="outline-item"
          :class="{ selected: selectedNodes.includes(index) }"
        >
          <el-checkbox :label="index">
            <div class="node-info">
              <span class="node-title">{{ node.title || `章节 ${index + 1}` }}</span>
              <span v-if="node.description" class="node-desc">{{ node.description }}</span>
            </div>
          </el-checkbox>
        </div>
      </el-checkbox-group>

      <div class="step-actions">
        <el-button @click="emit('close')">取消</el-button>
        <el-button type="primary" :disabled="selectedNodes.length === 0" @click="goToConfig">
          下一步
          <el-icon class="el-icon--right"><ArrowRight /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- 第二步：配置参数 -->
    <div v-if="step === 'config'" class="step-panel">
      <h4>配置生成参数</h4>
      
      <el-form label-position="top">
        <el-form-item label="每章字数限制">
          <div class="slider-with-value">
            <el-slider
              v-model="maxTokens"
              :min="1000"
              :max="8000"
              :step="500"
              show-stops
            />
            <span class="value-display">{{ estimatedChars }} 字</span>
          </div>
          <p class="form-hint">建议：短篇 1500-2500 字，中篇 2000-4000 字</p>
        </el-form-item>

        <el-form-item label="额外要求（可选）">
          <el-input
            v-model="customInstruction"
            type="textarea"
            :rows="3"
            placeholder="例如：注意描写人物心理活动；增加环境描写；保持轻松幽默的语气..."
          />
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="autoInsert">
            自动插入到文档（无需逐章确认）
          </el-checkbox>
          <p class="form-hint" v-if="autoInsert">生成完成后自动保存，无需手动确认每章</p>
        </el-form-item>

        <el-form-item v-if="autoInsert" label="自动插入方式">
          <el-radio-group v-model="autoInsertMode">
            <el-radio label="create">智能匹配：有则更新，无则创建</el-radio>
            <el-radio v-if="props.documentId > 0" label="append">全部追加到当前文档</el-radio>
          </el-radio-group>
          <p class="form-hint" v-if="autoInsertMode === 'create'">
            系统会自动匹配章节标题与现有文档标题，匹配成功则更新原文档，不匹配则创建新文档
          </p>
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="autoContinue">
            出错时自动继续下一章
          </el-checkbox>
        </el-form-item>
      </el-form>

      <div class="summary">
        <h5>生成预览</h5>
        <p>将生成 <strong>{{ selectedNodes.length }}</strong> 个章节</p>
        <p>预计总字数：<strong>{{ (estimatedChars * selectedNodes.length).toLocaleString() }}</strong> 字</p>
        <p v-if="props.documentId === 0" class="form-hint" style="margin-top: 8px;">
          <el-icon><InfoFilled /></el-icon>
          在项目页面使用：将智能匹配或创建新文档
        </p>
      </div>

      <div class="step-actions">
        <el-button @click="step = 'select'">
          <el-icon class="el-icon--left"><ArrowLeft /></el-icon>
          上一步
        </el-button>
        <el-button type="primary" @click="startGeneration">
          <el-icon><VideoPlay /></el-icon>
          开始生成
        </el-button>
      </div>
    </div>

    <!-- 第三步：逐章生成与操作 -->
    <div v-if="step === 'generating'" class="step-panel generating">
      <!-- 自动模式：简洁显示 -->
      <template v-if="autoInsert">
        <h4>自动生成中...</h4>
        <div class="auto-mode-info">
          <el-tag type="info" size="large">
            {{ autoInsertMode === 'create' ? '智能匹配：自动更新或创建文档' : '全部追加到当前打开的文档' }}
          </el-tag>
        </div>

        <div class="current-chapter-info" v-if="currentChapterTitle">
          <span>正在生成：</span>
          <el-tag size="large" type="primary">{{ currentChapterTitle }}</el-tag>
        </div>

        <div class="progress-section">
          <el-progress
            :percentage="overallProgress"
            :stroke-width="16"
            :status="progressStatus"
          />
          <div class="progress-text">
            总体进度：{{ completedChapters.length }} / {{ totalChapters }} 章已完成
          </div>
        </div>

        <!-- 当前章节实时预览（自动滚动） -->
        <div v-if="isGenerating && currentChapterContent" class="auto-preview">
          <div class="auto-preview-header">
            <span>{{ currentChapterTitle }} - 实时预览</span>
            <span class="char-count">{{ currentChapterChars }} 字</span>
          </div>
          <div class="auto-preview-content" ref="autoPreviewRef">
            {{ currentChapterContent }}<span class="cursor">|</span>
          </div>
        </div>

        <!-- 自动处理中的提示 -->
        <div v-else-if="isProcessing" class="processing-status">
          <el-icon class="is-loading" :size="24"><Loading /></el-icon>
          <span>正在保存 {{ processingTitle }}...</span>
        </div>

        <!-- 最后生成的章节预览 -->
        <div v-else-if="lastCompletedChapter" class="last-chapter-preview">
          <div class="preview-header">
            <span>✓ {{ lastCompletedChapter.title }} 已{{ lastCompletedChapter.action === 'create' ? '创建' : '保存' }}</span>
            <span class="char-count">{{ lastCompletedChapter.chars }} 字</span>
          </div>
        </div>
      </template>

      <!-- 手动模式：详细操作 -->
      <template v-else>
        <h4>正在生成第 {{ currentChapterIndex + 1 }} / {{ totalChapters }} 章</h4>

        <div class="current-chapter-info">
          <el-tag size="large" type="primary">{{ currentChapterTitle }}</el-tag>
          <span v-if="currentChapterDesc" class="chapter-desc">{{ currentChapterDesc }}</span>
        </div>

        <div class="progress-section">
          <el-progress
            :percentage="overallProgress"
            :stroke-width="12"
            :status="progressStatus"
          />
          <div class="progress-text">
            总体进度：{{ completedChapters.length }} / {{ totalChapters }} 章已完成
          </div>
        </div>

        <!-- 生成中状态 -->
        <div v-if="isGenerating" class="generating-status">
          <el-skeleton :rows="6" animated />
          <div class="generating-text">
            <el-icon class="is-loading"><Loading /></el-icon>
            AI 正在创作中...
          </div>
        </div>

        <!-- 生成完成，等待操作 -->
        <div v-else-if="currentChapterContent" class="chapter-ready">
          <div class="content-preview-box">
            <div class="preview-header">
              <span>生成内容预览（{{ currentChapterChars }} 字）</span>
              <el-button link size="small" @click="showFullContent = !showFullContent">
                {{ showFullContent ? '收起' : '展开全文' }}
              </el-button>
            </div>
            <div class="preview-content" :class="{ expanded: showFullContent }">
              {{ showFullContent ? currentChapterContent : currentChapterContent.slice(0, 300) + (currentChapterContent.length > 300 ? '...' : '') }}
            </div>
          </div>

          <div class="chapter-actions">
            <p class="action-hint">请选择如何处理本章内容：</p>
            <div class="action-buttons">
              <el-button type="primary" size="large" @click="createNewDocument">
                <el-icon><DocumentAdd /></el-icon>
                创建为新文档
              </el-button>
              <el-button v-if="props.documentId > 0" size="large" @click="insertToCurrentDoc">
                <el-icon><Plus /></el-icon>
                插入当前文档
              </el-button>
              <el-button size="large" @click="skipChapter">
                <el-icon><Right /></el-icon>
                跳过，继续下一章
              </el-button>
            </div>
          </div>
        </div>

        <!-- 错误状态 -->
        <div v-else-if="generationError" class="error-state">
          <el-icon :size="48" color="#f56c6c"><CircleClose /></el-icon>
          <p>生成失败：{{ generationError }}</p>
          <el-button type="primary" @click="retryChapter">重试</el-button>
          <el-button @click="skipChapter">跳过</el-button>
        </div>
      </template>
    </div>

    <!-- 第四步：全部完成 -->
    <div v-if="step === 'complete'" class="step-panel">
      <div class="success-state">
        <el-icon class="success-icon" :size="64"><CircleCheck /></el-icon>
        <h4>全部完成！</h4>
        <p>共生成 <strong>{{ completedChapters.length }}</strong> 章</p>
        <p v-if="updatedChaptersCount > 0">更新 <strong>{{ updatedChaptersCount }}</strong> 个现有文档</p>
        <p v-if="createdDocuments.length > 0">成功创建 <strong>{{ createdDocuments.length }}</strong> 个新文档</p>
        <p>总计 <strong>{{ totalChars.toLocaleString() }}</strong> 字</p>
      </div>

      <div class="chapter-list">
        <h5>处理结果</h5>
        <el-timeline>
          <el-timeline-item
            v-for="(chapter, index) in completedChapters"
            :key="index"
            :type="chapter.error ? 'danger' : 'success'"
          >
            <div class="timeline-content">
              <span class="timeline-title">{{ chapter.title }}</span>
              <span class="timeline-chars">{{ chapter.chars.toLocaleString() }} 字</span>
              <el-tag :type="chapter.action === 'create' ? 'success' : chapter.action === 'update' ? 'warning' : chapter.action === 'insert' ? 'primary' : 'info'" size="small">
                {{ chapter.action === 'create' ? '新建文档' : chapter.action === 'update' ? '更新文档' : chapter.action === 'insert' ? '插入当前' : '已跳过' }}
              </el-tag>
              <el-tag v-if="chapter.error" type="danger" size="small">失败</el-tag>
            </div>
          </el-timeline-item>
        </el-timeline>
      </div>

      <div class="step-actions">
        <el-button @click="resetAndClose">关闭</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { aiApi, documentApi } from '@/api'
import type { OutlineNode, AIGenerateChunk } from '@/api/types'
import {
  ArrowRight, ArrowLeft, VideoPlay, EditPen,
  CircleCheck, DocumentAdd, Document, Plus, Right,
  Loading, CircleClose, InfoFilled
} from '@element-plus/icons-vue'

const props = defineProps<{
  projectId: number
  documentId: number
  outline: OutlineNode[]
  existingDocuments?: Array<{ id: number; title: string; content?: any[] }>
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'document-created', docId: number): void
  (e: 'refresh-documents'): void
}>()

// 步骤控制
const step = ref<'select' | 'config' | 'generating' | 'complete'>('select')

// 第一步：选择
const selectedNodes = ref<number[]>([])

// 第二步：配置
const maxTokens = ref(2000)
const customInstruction = ref('')
const autoContinue = ref(true)
const autoInsert = ref(false)
const autoInsertMode = ref<'create' | 'append'>('create')

// 第三步：逐章生成
const isGenerating = ref(false)
const isProcessing = ref(false)
const processingTitle = ref('')
const currentChapterIndex = ref(0)
const currentChapterTitle = ref('')
const currentChapterDesc = ref('')
const currentChapterContent = ref('')
const currentChapterChars = ref(0)
const showFullContent = ref(false)
const generationError = ref('')
const lastCompletedChapter = ref<CompletedChapter | null>(null)
const autoPreviewRef = ref<HTMLElement>()

// 完成的章节记录
interface CompletedChapter {
  title: string
  chars: number
  content?: string
  action?: 'create' | 'insert' | 'skip' | 'update'
  documentId?: number
  error?: boolean
}
const completedChapters = ref<CompletedChapter[]>([])
const createdDocuments = ref<{ id: number; title: string }[]>([])
const totalChars = ref(0)

// 待生成的章节队列
const pendingChapters = ref<OutlineNode[]>([])

// document_id 为 0 时（项目页）先创建文档，后续请求用此 id
const effectiveDocumentId = ref(0)
// 本次会话在项目页创建的文档标题，用于智能匹配时优先更新该文档而非新建
const sessionCreatedDocTitle = ref('')

// 计算属性
const estimatedChars = computed(() => {
  return Math.floor(maxTokens.value / 1.5)
})

const totalChapters = computed(() => pendingChapters.value.length)

const overallProgress = computed(() => {
  if (totalChapters.value === 0) return 0
  return Math.round((completedChapters.value.length / totalChapters.value) * 100)
})

const progressStatus = computed(() => {
  if (step.value === 'complete') return 'success'
  return ''
})

const updatedChaptersCount = computed(() => {
  return completedChapters.value.filter(c => c.action === 'update').length
})

// 方法
function goToConfig() {
  if (selectedNodes.value.length === 0) {
    ElMessage.warning('请至少选择一个章节')
    return
  }
  step.value = 'config'
}

// 自动滚动预览区域
function scrollAutoPreview() {
  nextTick(() => {
    if (autoPreviewRef.value) {
      autoPreviewRef.value.scrollTop = autoPreviewRef.value.scrollHeight
    }
  })
}

async function startGeneration() {
  // 准备待生成队列
  pendingChapters.value = selectedNodes.value.map(i => props.outline[i])
  completedChapters.value = []
  createdDocuments.value = []
  totalChars.value = 0
  currentChapterIndex.value = 0

  // document_id 为 0 时（从项目页进入）：若第一章已有对应文档则直接用，否则新建一篇
  if (props.documentId === 0) {
    const firstTitle = pendingChapters.value[0]?.title || 'AI 自动生成'
    const existingFirst = findExistingDocumentByTitle(firstTitle)
    if (existingFirst) {
      effectiveDocumentId.value = existingFirst.id
      sessionCreatedDocTitle.value = ''
    } else {
      try {
        sessionCreatedDocTitle.value = firstTitle
        const doc = await documentApi.create(props.projectId, {
          title: firstTitle,
          content: []
        })
        effectiveDocumentId.value = doc.data.id
        emit('document-created', doc.data.id)
        emit('refresh-documents')
      } catch (e: any) {
        ElMessage.error(e?.response?.data?.detail || e?.message || '创建文档失败')
        return
      }
    }
  } else {
    effectiveDocumentId.value = props.documentId
    sessionCreatedDocTitle.value = ''
  }

  step.value = 'generating'

  // 开始生成第一章
  await generateCurrentChapter()
}

async function generateCurrentChapter() {
  if (currentChapterIndex.value >= pendingChapters.value.length) {
    // 全部完成
    step.value = 'complete'
    return
  }

  const node = pendingChapters.value[currentChapterIndex.value]
  currentChapterTitle.value = node.title || `章节 ${currentChapterIndex.value + 1}`
  currentChapterDesc.value = node.description || ''
  currentChapterContent.value = ''
  currentChapterChars.value = 0
  generationError.value = ''
  isGenerating.value = true
  showFullContent.value = false

  try {
    const res = await aiApi.batchGenerateStream({
      project_id: props.projectId,
      document_id: effectiveDocumentId.value,
      outline_nodes: [node],  // 只生成当前这一章
      max_tokens_per_chapter: maxTokens.value,
      continue_on_complete: autoContinue.value,
      custom_instruction: customInstruction.value || undefined
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || '生成失败')
    }

    const reader = res.body?.getReader()
    const decoder = new TextDecoder()

    if (!reader) throw new Error('无法读取响应')

    let fullContent = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value, { stream: true })
      const lines = chunk.split('\n')

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue

        const data = line.slice(6)
        if (data === '[DONE]') continue

        try {
          const parsed: AIGenerateChunk = JSON.parse(data)
          if (parsed.type === 'content' && parsed.content) {
            // 实时累积内容用于预览
            currentChapterContent.value += parsed.content
            currentChapterChars.value = currentChapterContent.value.length
            // 自动滚动预览区域
            scrollAutoPreview()
          }
          if (parsed.type === 'chapter_complete' && parsed.chapter_content) {
            fullContent = parsed.chapter_content
            currentChapterChars.value = parsed.chapter_chars || fullContent.length
          }
        } catch (e) {
          // 忽略解析错误
        }
      }
    }

    currentChapterContent.value = fullContent
    isGenerating.value = false

    // 自动模式下，自动执行插入
    if (autoInsert.value && fullContent.trim()) {
      await autoProcessChapter()
    }

  } catch (e: any) {
    isGenerating.value = false
    if (autoInsert.value && autoContinue.value) {
      // 自动模式下且设置了出错继续，则记录错误并继续
      completedChapters.value.push({
        title: currentChapterTitle.value,
        chars: 0,
        error: true
      })
      await nextChapter()
    } else {
      generationError.value = e?.message || '生成失败'
      completedChapters.value.push({
        title: currentChapterTitle.value,
        chars: 0,
        error: true
      })
    }
  }
}

// 自动处理当前章节
async function autoProcessChapter() {
  isProcessing.value = true
  processingTitle.value = currentChapterTitle.value

  try {
    if (autoInsertMode.value === 'create') {
      // 智能模式：检查现有文档，存在则更新，否则创建
      await autoCreateOrUpdateDocument()
    } else {
      await autoAppendToCurrent()
    }
  } finally {
    isProcessing.value = false
  }
}

// 仅在项目已有文档中按标题查找（用于开始时判断“第一章”是否已存在，避免重复创建）
function findExistingDocumentByTitle(title: string): { id: number; title: string; content?: any[] } | undefined {
  if (!props.existingDocuments || props.existingDocuments.length === 0) return undefined
  return props.existingDocuments.find(doc =>
    doc.title === title ||
    doc.title.includes(title) ||
    title.includes(doc.title)
  )
}

// 查找是否已有对应标题的文档（先查项目已有文档，再 fallback 到本次会话创建的那篇）
function findExistingDocument(title: string): { id: number; title: string; content?: any[] } | undefined {
  // 优先在项目已有文档中查找：若第三章/第四章等已存在，应更新该文档而不是新建
  if (props.existingDocuments && props.existingDocuments.length > 0) {
    const found = props.existingDocuments.find(doc =>
      doc.title === title ||
      doc.title.includes(title) ||
      title.includes(doc.title)
    )
    if (found) return found
  }

  // 没有匹配的已有文档时，再看是否是本次会话先创建的那篇（避免从第一章开始时重复新建）
  if (sessionCreatedDocTitle.value && effectiveDocumentId.value > 0) {
    const sessionTitle = sessionCreatedDocTitle.value
    if (title === sessionTitle || title.includes(sessionTitle) || sessionTitle.includes(title)) {
      return {
        id: effectiveDocumentId.value,
        title: sessionCreatedDocTitle.value,
        content: []
      }
    }
  }

  return undefined
}

// 智能处理：检查是否存在现有文档，存在则更新，否则创建
async function autoCreateOrUpdateDocument() {
  try {
    const title = currentChapterTitle.value
    const content = currentChapterContent.value

    // 查找是否已有对应文档
    const existingDoc = findExistingDocument(title)

    if (existingDoc) {
      // 更新现有文档
      const existingContent = existingDoc.content || []

      // 添加章节标题和内容
      const newBlocks = [
        {
          id: Date.now().toString() + '-h',
          type: 'heading',
          content: title,
          props: { level: 2 }
        },
        {
          id: Date.now().toString(),
          type: 'paragraph',
          content: content,
          props: {}
        }
      ]

      await documentApi.update(existingDoc.id, {
        content: [...existingContent, ...newBlocks]
      })

      // 若本次更新的是会话内先创建的那篇文档，用过后即清空，避免后续章节误匹配
      if (existingDoc.id === effectiveDocumentId.value) {
        sessionCreatedDocTitle.value = ''
      }

      const completed: CompletedChapter = {
        title: currentChapterTitle.value,
        chars: currentChapterChars.value,
        content: content,
        action: 'update',
        documentId: existingDoc.id
      }
      completedChapters.value.push(completed)
      lastCompletedChapter.value = completed
      totalChars.value += currentChapterChars.value

      ElMessage.success(`已更新文档：${existingDoc.title}`)
    } else {
      // 创建新文档
      const doc = await documentApi.create(props.projectId, {
        title: title,
        content: [{
          id: Date.now().toString(),
          type: 'paragraph',
          content: content,
          props: {}
        }]
      })

      const completed: CompletedChapter = {
        title: currentChapterTitle.value,
        chars: currentChapterChars.value,
        content: content,
        action: 'create',
        documentId: doc.data.id
      }
      completedChapters.value.push(completed)
      lastCompletedChapter.value = completed
      createdDocuments.value.push({ id: doc.data.id, title })
      totalChars.value += currentChapterChars.value

      emit('document-created', doc.data.id)
      ElMessage.success(`已创建文档：${title}`)
    }

    emit('refresh-documents')

    // 继续下一章
    await nextChapter()

  } catch (e: any) {
    ElMessage.error(e?.message || '保存文档失败')
    if (autoContinue.value) {
      await nextChapter()
    }
  }
}

// 自动创建文档（保留旧方法用于手动模式）
async function autoCreateDocument() {
  try {
    const title = currentChapterTitle.value
    const content = currentChapterContent.value

    const doc = await documentApi.create(props.projectId, {
      title: title,
      content: [{
        id: Date.now().toString(),
        type: 'paragraph',
        content: content,
        props: {}
      }]
    })

    const completed: CompletedChapter = {
      title: currentChapterTitle.value,
      chars: currentChapterChars.value,
      content: content,
      action: 'create',
      documentId: doc.data.id
    }
    completedChapters.value.push(completed)
    lastCompletedChapter.value = completed
    createdDocuments.value.push({ id: doc.data.id, title })
    totalChars.value += currentChapterChars.value

    emit('document-created', doc.data.id)
    emit('refresh-documents')

    // 继续下一章
    await nextChapter()

  } catch (e: any) {
    ElMessage.error(e?.message || '创建文档失败')
    if (autoContinue.value) {
      await nextChapter()
    }
  }
}

// 自动追加到当前文档
async function autoAppendToCurrent() {
  try {
    const content = currentChapterContent.value

    const currentDoc = await documentApi.get(props.documentId)
    const existingContent = currentDoc.data.content || []

    const newBlocks = [
      {
        id: Date.now().toString() + '-h',
        type: 'heading',
        content: currentChapterTitle.value,
        props: { level: 2 }
      },
      {
        id: Date.now().toString(),
        type: 'paragraph',
        content: content,
        props: {}
      }
    ]

    await documentApi.update(props.documentId, {
      content: [...existingContent, ...newBlocks]
    })

    const completed: CompletedChapter = {
      title: currentChapterTitle.value,
      chars: currentChapterChars.value,
      content: content,
      action: 'insert'
    }
    completedChapters.value.push(completed)
    lastCompletedChapter.value = completed
    totalChars.value += currentChapterChars.value

    emit('refresh-documents')

    // 继续下一章
    await nextChapter()

  } catch (e: any) {
    ElMessage.error(e?.message || '插入文档失败')
    if (autoContinue.value) {
      await nextChapter()
    }
  }
}

async function createNewDocument() {
  if (!currentChapterContent.value.trim()) {
    ElMessage.warning('没有可插入的内容')
    return
  }

  try {
    const title = currentChapterTitle.value
    const content = currentChapterContent.value

    // 创建新文档
    const doc = await documentApi.create(props.projectId, {
      title: title,
      content: [{
        id: Date.now().toString(),
        type: 'paragraph',
        content: content,
        props: {}
      }]
    })

    // 记录
    completedChapters.value.push({
      title: currentChapterTitle.value,
      chars: currentChapterChars.value,
      content: content,
      action: 'create',
      documentId: doc.data.id
    })
    createdDocuments.value.push({ id: doc.data.id, title })
    totalChars.value += currentChapterChars.value

    ElMessage.success(`已创建文档：${title}`)
    emit('document-created', doc.data.id)
    emit('refresh-documents')

    // 继续下一章
    await nextChapter()

  } catch (e: any) {
    ElMessage.error(e?.message || '创建文档失败')
  }
}

async function insertToCurrentDoc() {
  if (!currentChapterContent.value.trim()) {
    ElMessage.warning('没有可插入的内容')
    return
  }

  try {
    const content = currentChapterContent.value

    // 更新当前文档
    const currentDoc = await documentApi.get(props.documentId)
    const existingContent = currentDoc.data.content || []

    // 添加章节标题和内容
    const newBlocks = [
      {
        id: Date.now().toString() + '-h',
        type: 'heading',
        content: currentChapterTitle.value,
        props: { level: 2 }
      },
      {
        id: Date.now().toString(),
        type: 'paragraph',
        content: content,
        props: {}
      }
    ]

    await documentApi.update(props.documentId, {
      content: [...existingContent, ...newBlocks]
    })

    // 记录
    completedChapters.value.push({
      title: currentChapterTitle.value,
      chars: currentChapterChars.value,
      content: content,
      action: 'insert'
    })
    totalChars.value += currentChapterChars.value

    ElMessage.success(`已插入到当前文档：${currentChapterTitle.value}`)
    emit('refresh-documents')

    // 继续下一章
    await nextChapter()

  } catch (e: any) {
    ElMessage.error(e?.message || '插入文档失败')
  }
}

async function skipChapter() {
  completedChapters.value.push({
    title: currentChapterTitle.value,
    chars: 0,
    action: 'skip'
  })

  ElMessage.info(`已跳过：${currentChapterTitle.value}`)
  await nextChapter()
}

async function nextChapter() {
  currentChapterIndex.value++
  if (currentChapterIndex.value < pendingChapters.value.length) {
    await generateCurrentChapter()
  } else {
    step.value = 'complete'
  }
}

async function retryChapter() {
  // 移除之前的错误记录
  if (completedChapters.value.length > 0 &&
      completedChapters.value[completedChapters.value.length - 1].error) {
    completedChapters.value.pop()
  }
  await generateCurrentChapter()
}

function resetAndClose() {
  step.value = 'select'
  selectedNodes.value = []
  completedChapters.value = []
  createdDocuments.value = []
  pendingChapters.value = []
  currentChapterContent.value = ''
  currentChapterIndex.value = 0
  emit('close')
}
</script>

<style scoped lang="scss">
// 动画关键帧
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-5px); }
}

@keyframes scaleIn {
  from {
    opacity: 0;
    transform: scale(0.9);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.ai-auto-write {
  padding: 24px;
  max-width: 600px;
  margin: 0 auto;
  animation: fadeInUp 0.4s ease-out;
}

.auto-write-header {
  text-align: center;
  margin-bottom: 32px;
  padding: 24px;
  background: linear-gradient(135deg, var(--el-color-primary-light-9) 0%, var(--el-fill-color-light) 100%);
  border-radius: 16px;
  border: 1px solid var(--el-color-primary-light-7);
  box-shadow: 0 4px 16px rgba(var(--el-color-primary-rgb), 0.1);

  h3 {
    margin: 0 0 10px;
    font-size: 22px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    color: var(--el-color-primary);
    font-weight: 600;

    .el-icon {
      font-size: 26px;
      animation: float 3s ease-in-out infinite;
    }
  }

  .subtitle {
    margin: 0;
    color: var(--el-text-color-secondary);
    font-size: 14px;
    font-weight: 400;
  }
}

.step-panel {
  animation: fadeInUp 0.3s ease-out;

  h4 {
    margin: 0 0 12px;
    font-size: 18px;
    color: var(--el-text-color-primary);
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 8px;

    &::before {
      content: '';
      width: 4px;
      height: 20px;
      background: var(--el-color-primary);
      border-radius: 2px;
    }
  }

  .hint {
    margin: 0 0 20px;
    color: var(--el-text-color-secondary);
    font-size: 14px;
    padding: 12px 16px;
    background: var(--el-fill-color-light);
    border-radius: 8px;
    border-left: 3px solid var(--el-color-info);
  }
}

.empty-state {
  text-align: center;
  padding: 60px 24px;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-light);
  border-radius: 16px;
  border: 2px dashed var(--el-border-color);

  .el-icon {
    margin-bottom: 16px;
    color: var(--el-text-color-placeholder);
    transition: transform 0.3s ease;

    &:hover {
      transform: scale(1.1);
    }
  }

  p {
    margin: 8px 0 0;
    font-size: 15px;
    color: var(--el-text-color-regular);

    &.sub {
      font-size: 13px;
      opacity: 0.7;
      margin-top: 6px;
    }
  }
}

.outline-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 320px;
  overflow-y: auto;
  padding: 8px;
  background: var(--el-fill-color-light);
  border-radius: 12px;

  // 自定义滚动条
  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
    border-radius: 3px;
  }

  &::-webkit-scrollbar-thumb {
    background: var(--el-border-color);
    border-radius: 3px;

    &:hover {
      background: var(--el-color-primary-light-5);
    }
  }
}

.outline-item {
  padding: 14px 18px;
  border: 2px solid transparent;
  border-radius: 10px;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  background: var(--el-bg-color);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);

  &:hover {
    border-color: var(--el-color-primary-light-5);
    box-shadow: 0 4px 12px rgba(var(--el-color-primary-rgb), 0.1);
    transform: translateY(-2px);
  }

  &.selected {
    border-color: var(--el-color-primary);
    background: var(--el-color-primary-light-9);
    box-shadow: 0 4px 16px rgba(var(--el-color-primary-rgb), 0.15);
    animation: scaleIn 0.2s ease-out;

    .node-title {
      color: var(--el-color-primary);
      font-weight: 600;
    }
  }

  :deep(.el-checkbox) {
    width: 100%;
    align-items: flex-start;

    .el-checkbox__label {
      padding-left: 12px;
      flex: 1;
    }

    .el-checkbox__input.is-checked + .el-checkbox__label {
      color: var(--el-color-primary);
    }
  }
}

.node-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.node-title {
  font-weight: 500;
  color: var(--el-text-color-primary);
  font-size: 15px;
  transition: color 0.2s;
}

.node-desc {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.5;
}

.slider-with-value {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 12px 16px;
  background: var(--el-fill-color-light);
  border-radius: 10px;

  .el-slider {
    flex: 1;
  }

  .value-display {
    min-width: 90px;
    text-align: center;
    font-weight: 600;
    color: var(--el-color-primary);
    font-size: 16px;
    padding: 8px 12px;
    background: var(--el-color-primary-light-9);
    border-radius: 8px;
    border: 2px solid var(--el-color-primary-light-7);
  }
}

.form-hint {
  margin: 8px 0 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  display: flex;
  align-items: center;
  gap: 6px;

  .el-icon {
    font-size: 14px;
    color: var(--el-color-info);
  }
}

.summary {
  margin-top: 28px;
  padding: 20px;
  background: linear-gradient(135deg, var(--el-color-success-light-9) 0%, var(--el-fill-color-light) 100%);
  border-radius: 12px;
  border: 1px solid var(--el-color-success-light-7);

  h5 {
    margin: 0 0 16px;
    font-size: 15px;
    color: var(--el-text-color-primary);
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 8px;

    &::before {
      content: '';
      width: 4px;
      height: 16px;
      background: var(--el-color-success);
      border-radius: 2px;
    }
  }

  p {
    margin: 8px 0;
    font-size: 14px;
    color: var(--el-text-color-secondary);

    strong {
      color: var(--el-color-primary);
      font-size: 18px;
      font-weight: 700;
    }
  }
}

.generating {
  .current-chapter-info {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
    padding: 14px 18px;
    background: var(--el-color-primary-light-9);
    border-radius: 10px;
    border: 1px solid var(--el-color-primary-light-7);
    animation: slideIn 0.3s ease-out;

    .chapter-desc {
      color: var(--el-text-color-secondary);
      font-size: 13px;
    }
  }

  .progress-section {
    margin-bottom: 24px;
    padding: 16px;
    background: var(--el-fill-color-light);
    border-radius: 12px;

    :deep(.el-progress-bar__outer) {
      background-color: var(--el-border-color-lighter);
      border-radius: 10px;
    }

    :deep(.el-progress-bar__inner) {
      border-radius: 10px;
      transition: width 0.4s ease;
    }

    .progress-text {
      margin-top: 12px;
      font-size: 14px;
      color: var(--el-text-color-secondary);
      text-align: center;
      font-weight: 500;
    }
  }

  .generating-status {
    padding: 32px 24px;
    background: linear-gradient(135deg, var(--el-fill-color-light) 0%, var(--el-color-primary-light-9) 100%);
    border-radius: 16px;
    border: 1px solid var(--el-color-primary-light-7);

    .generating-text {
      text-align: center;
      margin-top: 20px;
      color: var(--el-color-primary);
      font-size: 15px;
      font-weight: 500;

      .el-icon {
        margin-right: 10px;
        font-size: 18px;
      }
    }
  }

  .chapter-ready {
    animation: fadeInUp 0.4s ease-out;

    .content-preview-box {
      border: 2px solid var(--el-border-color-light);
      border-radius: 12px;
      margin-bottom: 24px;
      overflow: hidden;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
      transition: box-shadow 0.3s ease;

      &:hover {
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
      }

      .preview-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 14px 18px;
        background: linear-gradient(135deg, var(--el-fill-color-light) 0%, var(--el-fill-color) 100%);
        border-bottom: 1px solid var(--el-border-color-light);
        font-size: 14px;
        color: var(--el-text-color-secondary);
        font-weight: 500;

        span:first-child {
          display: flex;
          align-items: center;
          gap: 8px;

          &::before {
            content: '';
            width: 8px;
            height: 8px;
            background: var(--el-color-success);
            border-radius: 50%;
            animation: pulse 2s infinite;
          }
        }
      }

      .preview-content {
        padding: 20px;
        font-size: 15px;
        line-height: 1.9;
        color: var(--el-text-color-primary);
        max-height: 180px;
        overflow-y: auto;
        white-space: pre-wrap;
        word-break: break-word;
        background: var(--el-bg-color);

        &.expanded {
          max-height: 450px;
        }

        &::-webkit-scrollbar {
          width: 6px;
        }

        &::-webkit-scrollbar-thumb {
          background: var(--el-border-color);
          border-radius: 3px;
        }
      }
    }

    .chapter-actions {
      animation: fadeInUp 0.3s ease-out 0.1s both;

      .action-hint {
        margin: 0 0 18px;
        color: var(--el-text-color-secondary);
        font-size: 14px;
        text-align: center;
        padding: 12px;
        background: var(--el-fill-color-light);
        border-radius: 8px;
      }

      .action-buttons {
        display: flex;
        flex-direction: column;
        gap: 12px;

        .el-button {
          justify-content: center;
          padding: 18px 24px;
          font-size: 15px;
          border-radius: 10px;
          transition: all 0.25s ease;

          .el-icon {
            margin-right: 10px;
            font-size: 18px;
          }

          &:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(var(--el-color-primary-rgb), 0.25);
          }

          &:active {
            transform: translateY(0);
          }

          &.el-button--primary {
            background: linear-gradient(135deg, var(--el-color-primary) 0%, var(--el-color-primary-light-3) 100%);
            border: none;

            &:hover {
              box-shadow: 0 8px 24px rgba(var(--el-color-primary-rgb), 0.35);
            }
          }
        }
      }
    }
  }

  .error-state {
    text-align: center;
    padding: 40px 32px;
    background: var(--el-color-danger-light-9);
    border-radius: 16px;
    border: 1px solid var(--el-color-danger-light-5);
    animation: shake 0.5s ease-in-out;

    p {
      margin: 16px 0;
      color: var(--el-color-danger);
      font-size: 15px;
    }

    .el-button {
      margin: 0 8px;
    }
  }
}

.success-state {
  text-align: center;
  padding: 40px 32px;
  background: linear-gradient(135deg, var(--el-color-success-light-9) 0%, var(--el-fill-color-light) 100%);
  border-radius: 16px;
  border: 2px solid var(--el-color-success-light-5);
  animation: scaleIn 0.4s ease-out;

  .success-icon {
    color: var(--el-color-success);
    margin-bottom: 20px;
    font-size: 72px;
    animation: float 3s ease-in-out infinite;
  }

  h4 {
    margin: 0 0 16px;
    font-size: 22px;
    color: var(--el-text-color-primary);
  }

  p {
    margin: 8px 0;
    color: var(--el-text-color-secondary);
    font-size: 15px;

    strong {
      color: var(--el-color-primary);
      font-size: 20px;
    }
  }
}

.chapter-list {
  margin-top: 28px;
  max-height: 320px;
  overflow-y: auto;
  padding: 20px;
  background: var(--el-fill-color-light);
  border-radius: 12px;

  h5 {
    margin: 0 0 16px;
    font-size: 15px;
    color: var(--el-text-color-primary);
    font-weight: 600;
  }

  :deep(.el-timeline-item__node) {
    background-color: var(--el-color-primary);
  }

  :deep(.el-timeline-item__tail) {
    border-left-color: var(--el-border-color-lighter);
  }
}

.timeline-content {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding: 8px 0;
}

.timeline-title {
  font-weight: 600;
  color: var(--el-text-color-primary);
  font-size: 14px;
}

.timeline-chars {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color);
  padding: 2px 8px;
  border-radius: 4px;
}

.step-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 28px;
  padding-top: 20px;
  border-top: 1px solid var(--el-border-color-lighter);

  .el-button {
    padding: 12px 24px;
    border-radius: 8px;
    transition: all 0.25s ease;

    &:hover {
      transform: translateY(-1px);
    }

    &.el-button--primary {
      box-shadow: 0 4px 12px rgba(var(--el-color-primary-rgb), 0.2);

      &:hover {
        box-shadow: 0 6px 20px rgba(var(--el-color-primary-rgb), 0.3);
      }
    }
  }
}

// 自动模式样式
.auto-mode-info {
  text-align: center;
  margin-bottom: 20px;
  animation: fadeInUp 0.3s ease-out;
}

.auto-preview {
  border: 2px solid var(--el-color-primary-light-7);
  border-radius: 12px;
  overflow: hidden;
  margin-top: 20px;
  box-shadow: 0 4px 16px rgba(var(--el-color-primary-rgb), 0.1);
  animation: fadeInUp 0.3s ease-out;

  .auto-preview-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 18px;
    background: linear-gradient(135deg, var(--el-color-primary-light-9) 0%, var(--el-fill-color-light) 100%);
    border-bottom: 1px solid var(--el-color-primary-light-7);
    font-size: 14px;
    color: var(--el-text-color-secondary);
    font-weight: 500;

    .char-count {
      color: var(--el-color-primary);
      font-weight: 600;
      font-size: 15px;
    }
  }

  .auto-preview-content {
    padding: 18px;
    font-size: 14px;
    line-height: 1.8;
    color: var(--el-text-color-primary);
    max-height: 220px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-word;
    background: var(--el-bg-color);

    .cursor {
      animation: blink 1s step-end infinite;
      color: var(--el-color-primary);
      font-weight: bold;
    }

    &::-webkit-scrollbar {
      width: 6px;
    }

    &::-webkit-scrollbar-thumb {
      background: var(--el-border-color);
      border-radius: 3px;
    }
  }
}

.processing-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 32px 24px;
  color: var(--el-color-primary);
  font-size: 15px;
  font-weight: 500;
  background: var(--el-color-primary-light-9);
  border-radius: 12px;
  margin-top: 20px;
  animation: pulse 2s infinite;

  .el-icon {
    font-size: 24px;
  }
}

.last-chapter-preview {
  padding: 16px 20px;
  background: linear-gradient(135deg, var(--el-color-success-light-9) 0%, var(--el-fill-color-light) 100%);
  border: 2px solid var(--el-color-success-light-5);
  border-radius: 12px;
  margin-top: 20px;
  animation: slideIn 0.4s ease-out;

  .preview-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 14px;
    font-weight: 500;
    color: var(--el-color-success);

    .char-count {
      color: var(--el-color-success);
      font-weight: 600;
      background: var(--el-color-success-light-8);
      padding: 4px 12px;
      border-radius: 6px;
    }
  }
}

@keyframes blink {
  50% { opacity: 0; }
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-5px); }
  75% { transform: translateX(5px); }
}

// 响应式适配
@media (max-width: 600px) {
  .ai-auto-write {
    padding: 16px;
  }

  .auto-write-header {
    padding: 18px;
    margin-bottom: 24px;

    h3 {
      font-size: 18px;

      .el-icon {
        font-size: 22px;
      }
    }
  }

  .outline-list {
    max-height: 280px;
  }

  .outline-item {
    padding: 12px 14px;
  }

  .slider-with-value {
    flex-direction: column;
    gap: 12px;

    .value-display {
      width: 100%;
      min-width: unset;
    }
  }

  .summary {
    padding: 16px;

    p strong {
      font-size: 16px;
    }
  }

  .generating {
    .current-chapter-info {
      flex-direction: column;
      align-items: flex-start;
      gap: 8px;
    }

    .chapter-ready {
      .content-preview-box {
        .preview-content {
          max-height: 150px;
          padding: 16px;
          font-size: 14px;

          &.expanded {
            max-height: 350px;
          }
        }
      }

      .action-buttons {
        .el-button {
          padding: 14px 20px;
          font-size: 14px;
        }
      }
    }
  }

  .success-state {
    padding: 32px 24px;

    .success-icon {
      font-size: 56px;
    }

    h4 {
      font-size: 20px;
    }

    p strong {
      font-size: 18px;
    }
  }

  .chapter-list {
    padding: 16px;
  }

  .step-actions {
    flex-direction: column;

    .el-button {
      width: 100%;
      padding: 14px;
    }
  }
}

// 深色模式适配
@media (prefers-color-scheme: dark) {
  .auto-write-header {
    background: linear-gradient(135deg, rgba(var(--el-color-primary-rgb), 0.15) 0%, var(--el-fill-color-light) 100%);
  }

  .summary {
    background: linear-gradient(135deg, rgba(var(--el-color-success-rgb), 0.15) 0%, var(--el-fill-color-light) 100%);
  }

  .generating-status {
    background: linear-gradient(135deg, var(--el-fill-color-light) 0%, rgba(var(--el-color-primary-rgb), 0.15) 100%);
  }
}
</style>
