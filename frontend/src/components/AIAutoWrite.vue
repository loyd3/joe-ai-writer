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
      
      <template v-else>
        <div class="select-toolbar">
          <el-button link type="primary" @click="selectAll">全选</el-button>
          <el-button link @click="selectNone">取消全选</el-button>
          <span class="select-count">已选 {{ selectedNodes.length }} / {{ outline.length }}</span>
        </div>
        <el-checkbox-group v-model="selectedNodes" class="outline-list">
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
      </template>

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
        <el-form-item label="每章字数限制（tokens）">
          <div class="slider-with-value">
            <el-slider
              v-model="maxTokens"
              :min="1000"
              :max="30000"
              :step="1000"
            />
            <span class="value-display">≈ {{ estimatedChars.toLocaleString() }} 字</span>
          </div>
          <p class="form-hint">
            建议：短篇 2000-4000，中篇 4000-8000，长篇 8000-20000。
            超过 8192 tokens 时会自动分段续写。
          </p>
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

        <el-form-item label="容错设置">
          <div class="fault-tolerance-config">
            <el-checkbox v-model="autoContinue">
              出错时自动继续下一章
            </el-checkbox>
            <div class="retry-config">
              <span class="retry-label">失败自动重试次数：</span>
              <el-input-number v-model="maxRetries" :min="0" :max="5" :step="1" size="small" />
            </div>
            <div class="timeout-config">
              <span class="retry-label">单章超时时间（秒）：</span>
              <el-input-number v-model="chapterTimeoutSec" :min="30" :max="600" :step="30" size="small" />
            </div>
          </div>
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
      <!-- 控制栏（暂停/继续/停止） -->
      <div class="generation-controls">
        <el-button
          v-if="!isPaused && isGenerating"
          type="warning"
          size="small"
          @click="pauseGeneration"
        >
          <el-icon><VideoPause /></el-icon>
          暂停
        </el-button>
        <el-button
          v-if="isPaused"
          type="success"
          size="small"
          @click="resumeGeneration"
        >
          <el-icon><VideoPlay /></el-icon>
          继续
        </el-button>
        <el-button
          type="danger"
          size="small"
          plain
          @click="confirmStopGeneration"
        >
          <el-icon><Close /></el-icon>
          停止全部
        </el-button>
        <span v-if="currentRetryCount > 0" class="retry-indicator">
          <el-icon class="is-loading"><Loading /></el-icon>
          第 {{ currentRetryCount }} 次重试中...
        </span>
      </div>

      <!-- 自动模式：简洁显示 -->
      <template v-if="autoInsert">
        <h4>{{ isPaused ? '已暂停' : '自动生成中...' }}</h4>
        <div class="auto-mode-info">
          <el-tag type="info" size="large">
            {{ autoInsertMode === 'create' ? '智能匹配：自动更新或创建文档' : '全部追加到当前打开的文档' }}
          </el-tag>
        </div>

        <div class="current-chapter-info" v-if="currentChapterTitle">
          <span>{{ isPaused ? '暂停于：' : '正在生成：' }}</span>
          <el-tag size="large" type="primary">{{ currentChapterTitle }}</el-tag>
          <el-tag v-if="currentRetryCount > 0" type="warning" size="small">重试 {{ currentRetryCount }}/{{ maxRetries }}</el-tag>
        </div>

        <div class="progress-section">
          <el-progress
            :percentage="overallProgress"
            :stroke-width="16"
            :status="progressStatus"
          />
          <div class="progress-text">
            总体进度：{{ completedChapters.length }} / {{ totalChapters }} 章已完成
            <span v-if="failedChapterCount > 0" class="failed-count">（{{ failedChapterCount }} 个失败）</span>
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
            <span>{{ lastCompletedChapter.error ? '✗' : '✓' }} {{ lastCompletedChapter.title }}
              {{ lastCompletedChapter.error ? '生成失败' : `已${lastCompletedChapter.action === 'create' ? '创建' : '保存'}` }}
            </span>
            <span class="char-count">{{ lastCompletedChapter.chars }} 字</span>
          </div>
          <p v-if="lastCompletedChapter.errorMessage" class="error-detail">
            {{ lastCompletedChapter.errorMessage }}
          </p>
        </div>
      </template>

      <!-- 手动模式：详细操作 -->
      <template v-else>
        <h4>{{ isPaused ? '已暂停' : `正在生成第 ${currentChapterIndex + 1} / ${totalChapters} 章` }}</h4>

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
            <span v-if="failedChapterCount > 0" class="failed-count">（{{ failedChapterCount }} 个失败）</span>
          </div>
        </div>

        <!-- 生成中状态 -->
        <div v-if="isGenerating" class="generating-status">
          <div v-if="currentChapterContent" class="auto-preview-content inline-preview" ref="autoPreviewRef">
            {{ currentChapterContent }}<span class="cursor">|</span>
          </div>
          <el-skeleton v-else :rows="6" animated />
          <div class="generating-text">
            <el-icon class="is-loading"><Loading /></el-icon>
            AI 正在创作中... {{ currentChapterChars > 0 ? `(${currentChapterChars} 字)` : '' }}
          </div>
        </div>

        <!-- 生成完成，等待操作 -->
        <div v-else-if="currentChapterContent && !generationError" class="chapter-ready">
          <div class="content-preview-box">
            <div class="preview-header">
              <span>生成内容预览（{{ currentChapterChars }} 字）</span>
              <div>
                <el-button link size="small" type="warning" @click="regenerateChapter">
                  <el-icon><RefreshRight /></el-icon> 重新生成
                </el-button>
                <el-button link size="small" @click="showFullContent = !showFullContent">
                  {{ showFullContent ? '收起' : '展开全文' }}
                </el-button>
              </div>
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
          <p class="error-title">生成失败</p>
          <div class="error-detail-box">
            <p>{{ generationError }}</p>
            <p v-if="currentRetryCount > 0" class="retry-exhausted">已重试 {{ currentRetryCount }} 次仍然失败</p>
          </div>
          <div class="error-actions">
            <el-button type="primary" @click="retryChapter">
              <el-icon><RefreshRight /></el-icon> 重试本章
            </el-button>
            <el-button @click="skipChapter">跳过</el-button>
            <el-button type="danger" plain @click="confirmStopGeneration">停止全部</el-button>
          </div>
        </div>
      </template>
    </div>

    <!-- 第四步：全部完成 -->
    <div v-if="step === 'complete'" class="step-panel">
      <div class="success-state" :class="{ 'has-errors': failedChapterCount > 0 }">
        <el-icon class="success-icon" :size="64">
          <component :is="failedChapterCount > 0 ? WarningFilled : CircleCheck" />
        </el-icon>
        <h4>{{ failedChapterCount > 0 ? '生成完成（部分失败）' : '全部完成！' }}</h4>
        <p>共处理 <strong>{{ completedChapters.length }}</strong> 章</p>
        <p v-if="successChapterCount > 0">成功 <strong>{{ successChapterCount }}</strong> 章</p>
        <p v-if="failedChapterCount > 0" style="color: var(--el-color-danger)">
          失败 <strong>{{ failedChapterCount }}</strong> 章
        </p>
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
              <el-tag
                v-if="!chapter.error"
                :type="chapter.action === 'create' ? 'success' : chapter.action === 'update' ? 'warning' : chapter.action === 'insert' ? 'primary' : 'info'"
                size="small"
              >
                {{ chapter.action === 'create' ? '新建文档' : chapter.action === 'update' ? '更新文档' : chapter.action === 'insert' ? '插入当前' : '已跳过' }}
              </el-tag>
              <template v-if="chapter.error">
                <el-tag type="danger" size="small">失败</el-tag>
                <el-button
                  link
                  type="primary"
                  size="small"
                  @click="retryFailedChapter(index)"
                  :loading="retryingIndex === index"
                >
                  <el-icon><RefreshRight /></el-icon> 重试
                </el-button>
              </template>
            </div>
            <p v-if="chapter.error && chapter.errorMessage" class="timeline-error">
              {{ chapter.errorMessage }}
            </p>
          </el-timeline-item>
        </el-timeline>
      </div>

      <div class="step-actions">
        <el-button v-if="failedChapterCount > 0" type="primary" @click="retryAllFailed" :loading="retryingAll">
          <el-icon><RefreshRight /></el-icon>
          重试所有失败章节
        </el-button>
        <el-button @click="resetAndClose">关闭</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { aiApi, documentApi } from '@/api'
import type { OutlineNode, AIGenerateChunk } from '@/api/types'
import { parseFormattedTextToBlocks } from '@/utils/formatToBlocks'
import {
  ArrowRight, ArrowLeft, VideoPlay, VideoPause, EditPen,
  CircleCheck, DocumentAdd, Document, Plus, Right, Close,
  Loading, CircleClose, InfoFilled, RefreshRight, WarningFilled
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
const maxTokens = ref(8000)
const customInstruction = ref('')
const autoContinue = ref(true)
const autoInsert = ref(false)
const autoInsertMode = ref<'create' | 'append'>('create')
const maxRetries = ref(2)
const chapterTimeoutSec = ref(180)

// 第三步：逐章生成
const isGenerating = ref(false)
const isProcessing = ref(false)
const isPaused = ref(false)
const isStopped = ref(false)
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
const currentRetryCount = ref(0)
const retryingIndex = ref(-1)
const retryingAll = ref(false)

let activeReader: ReadableStreamDefaultReader<Uint8Array> | null = null
let pauseResolve: (() => void) | null = null
let timeoutTimer: ReturnType<typeof setTimeout> | null = null

interface CompletedChapter {
  title: string
  chars: number
  content?: string
  action?: 'create' | 'insert' | 'skip' | 'update'
  documentId?: number
  error?: boolean
  errorMessage?: string
  nodeIndex?: number
}
const completedChapters = ref<CompletedChapter[]>([])
const createdDocuments = ref<{ id: number; title: string }[]>([])
const totalChars = ref(0)

const pendingChapters = ref<OutlineNode[]>([])

const effectiveDocumentId = ref(0)
const sessionCreatedDocTitle = ref('')

// 计算属性
const estimatedChars = computed(() => Math.floor(maxTokens.value / 1.5))
const totalChapters = computed(() => pendingChapters.value.length)

const overallProgress = computed(() => {
  if (totalChapters.value === 0) return 0
  return Math.round((completedChapters.value.length / totalChapters.value) * 100)
})

const progressStatus = computed(() => {
  if (step.value === 'complete') {
    return failedChapterCount.value > 0 ? 'warning' : 'success'
  }
  return ''
})

const updatedChaptersCount = computed(() =>
  completedChapters.value.filter(c => c.action === 'update').length
)

const failedChapterCount = computed(() =>
  completedChapters.value.filter(c => c.error).length
)

const successChapterCount = computed(() =>
  completedChapters.value.filter(c => !c.error && c.action !== 'skip').length
)

// 自动滚动 preview
watch(() => currentChapterContent.value, () => {
  nextTick(() => {
    if (autoPreviewRef.value) {
      autoPreviewRef.value.scrollTop = autoPreviewRef.value.scrollHeight
    }
  })
})

// 方法
function selectAll() {
  selectedNodes.value = props.outline.map((_, i) => i)
}
function selectNone() {
  selectedNodes.value = []
}

function goToConfig() {
  if (selectedNodes.value.length === 0) {
    ElMessage.warning('请至少选择一个章节')
    return
  }
  step.value = 'config'
}

function clearTimeoutTimer() {
  if (timeoutTimer) {
    clearTimeout(timeoutTimer)
    timeoutTimer = null
  }
}

async function startGeneration() {
  pendingChapters.value = selectedNodes.value.map(i => props.outline[i])
  completedChapters.value = []
  createdDocuments.value = []
  totalChars.value = 0
  currentChapterIndex.value = 0
  isPaused.value = false
  isStopped.value = false

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
  await generateCurrentChapter()
}

async function generateCurrentChapter() {
  if (isStopped.value) {
    step.value = 'complete'
    return
  }
  if (currentChapterIndex.value >= pendingChapters.value.length) {
    step.value = 'complete'
    return
  }

  // Check pause before starting
  if (isPaused.value) {
    await waitForResume()
    if (isStopped.value) { step.value = 'complete'; return }
  }

  const node = pendingChapters.value[currentChapterIndex.value]
  currentChapterTitle.value = node.title || `章节 ${currentChapterIndex.value + 1}`
  currentChapterDesc.value = node.description || ''
  currentChapterContent.value = ''
  currentChapterChars.value = 0
  generationError.value = ''
  isGenerating.value = true
  showFullContent.value = false
  currentRetryCount.value = 0

  await attemptGenerate(node)
}

async function attemptGenerate(node: OutlineNode) {
  try {
    const res = await fetchWithTimeout(
      () => aiApi.batchGenerateStream({
        project_id: props.projectId,
        document_id: effectiveDocumentId.value,
        outline_nodes: [node],
        max_tokens_per_chapter: maxTokens.value,
        continue_on_complete: autoContinue.value,
        custom_instruction: customInstruction.value || undefined
      }),
      chapterTimeoutSec.value * 1000
    )

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      const detail = err.detail
      const errMsg = typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ')
          : '生成失败'
      throw new Error(errMsg)
    }

    const reader = res.body?.getReader()
    if (!reader) throw new Error('无法读取响应流')
    activeReader = reader

    const decoder = new TextDecoder()
    let fullContent = ''
    let lastChunkTime = Date.now()

    // Start inactivity watchdog
    const inactivityLimit = Math.max(60000, chapterTimeoutSec.value * 500)
    const watchdog = setInterval(() => {
      if (Date.now() - lastChunkTime > inactivityLimit && isGenerating.value) {
        clearInterval(watchdog)
        reader.cancel().catch(() => {})
      }
    }, 5000)

    let sseBuffer = ''

    try {
      while (true) {
        if (isStopped.value) {
          await reader.cancel()
          break
        }
        if (isPaused.value) {
          await waitForResume()
          if (isStopped.value) { await reader.cancel(); break }
        }

        const { done, value } = await reader.read()
        if (done) break
        lastChunkTime = Date.now()

        sseBuffer += decoder.decode(value, { stream: true })
        const lines = sseBuffer.split('\n')
        sseBuffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = line.slice(6).trim()
          if (data === '[DONE]') continue

          try {
            const parsed: AIGenerateChunk = JSON.parse(data)
            if (parsed.type === 'content' && parsed.content) {
              currentChapterContent.value += parsed.content
              currentChapterChars.value = currentChapterContent.value.length
            }
            if (parsed.type === 'chapter_complete' && parsed.chapter_content) {
              fullContent = parsed.chapter_content
              currentChapterChars.value = parsed.chapter_chars || fullContent.length
            }
            if (parsed.type === 'error') {
              throw new Error(parsed.error_message || '服务端返回错误')
            }
          } catch (parseErr: any) {
            if (parseErr.message && !parseErr.message.includes('JSON')) throw parseErr
          }
        }
      }
    } finally {
      clearInterval(watchdog)
      activeReader = null
    }

    // Use accumulated content if no chapter_complete event
    if (!fullContent && currentChapterContent.value.trim()) {
      fullContent = currentChapterContent.value
    }

    if (!fullContent.trim()) {
      throw new Error('生成结果为空，可能是 AI 服务异常')
    }

    currentChapterContent.value = fullContent
    currentChapterChars.value = fullContent.length
    isGenerating.value = false

    if (autoInsert.value) {
      await autoProcessChapter()
    }

  } catch (e: any) {
    isGenerating.value = false
    activeReader = null

    if (isStopped.value) {
      step.value = 'complete'
      return
    }

    const errorMsg = parseErrorMessage(e)

    // Auto-retry logic
    if (currentRetryCount.value < maxRetries.value) {
      currentRetryCount.value++
      const delayMs = Math.min(2000 * currentRetryCount.value, 10000)
      ElMessage.warning(`生成失败，${delayMs / 1000}秒后自动重试 (${currentRetryCount.value}/${maxRetries.value})`)

      currentChapterContent.value = ''
      currentChapterChars.value = 0
      isGenerating.value = true
      await sleep(delayMs)

      if (isStopped.value) { step.value = 'complete'; return }
      await attemptGenerate(node)
      return
    }

    if (autoInsert.value && autoContinue.value) {
      completedChapters.value.push({
        title: currentChapterTitle.value,
        chars: 0,
        error: true,
        errorMessage: errorMsg,
        nodeIndex: currentChapterIndex.value
      })
      lastCompletedChapter.value = completedChapters.value[completedChapters.value.length - 1]
      await nextChapter()
    } else {
      generationError.value = errorMsg
    }
  }
}

function parseErrorMessage(e: any): string {
  if (!e) return '未知错误'
  const msg = e?.message || String(e)
  if (msg.includes('timeout') || msg.includes('Timeout')) return '生成超时，请检查网络或减少字数后重试'
  if (msg.includes('Failed to fetch') || msg.includes('NetworkError')) return '网络连接失败，请检查网络后重试'
  if (msg.includes('max_tokens')) return 'Token 数量超出限制，请减少每章字数'
  if (msg.includes('rate_limit') || msg.includes('429')) return 'API 调用频率超限，请稍后再试'
  return msg
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function fetchWithTimeout(fetchFn: () => Promise<Response>, timeoutMs: number): Promise<Response> {
  const controller = new AbortController()
  clearTimeoutTimer()
  timeoutTimer = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const res = await fetchFn()
    clearTimeoutTimer()
    return res
  } catch (e: any) {
    clearTimeoutTimer()
    if (e.name === 'AbortError' || controller.signal.aborted) {
      throw new Error(`请求超时（${Math.round(timeoutMs / 1000)}秒）`)
    }
    throw e
  }
}

// 暂停/恢复/停止
function pauseGeneration() {
  isPaused.value = true
  ElMessage.info('已暂停，点击"继续"恢复生成')
}

function resumeGeneration() {
  isPaused.value = false
  if (pauseResolve) {
    pauseResolve()
    pauseResolve = null
  }
}

function waitForResume(): Promise<void> {
  return new Promise(resolve => { pauseResolve = resolve })
}

async function confirmStopGeneration() {
  try {
    await ElMessageBox.confirm(
      '确定要停止所有生成任务吗？已完成的章节不会丢失。',
      '确认停止',
      { confirmButtonText: '确定停止', cancelButtonText: '取消', type: 'warning' }
    )
    stopGeneration()
  } catch { /* cancelled */ }
}

function stopGeneration() {
  isStopped.value = true
  isPaused.value = false
  isGenerating.value = false
  clearTimeoutTimer()
  if (pauseResolve) { pauseResolve(); pauseResolve = null }
  if (activeReader) {
    activeReader.cancel().catch(() => {})
    activeReader = null
  }
  step.value = 'complete'
}

// 重新生成当前章节（手动模式）
async function regenerateChapter() {
  if (completedChapters.value.length > 0 &&
      completedChapters.value[completedChapters.value.length - 1].title === currentChapterTitle.value) {
    completedChapters.value.pop()
  }
  currentRetryCount.value = 0
  currentChapterContent.value = ''
  currentChapterChars.value = 0
  generationError.value = ''
  isGenerating.value = true
  const node = pendingChapters.value[currentChapterIndex.value]
  await attemptGenerate(node)
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

      // 添加章节标题和内容（自动解析 ##、>、- 等格式为块）
      const contentBlocks = parseFormattedTextToBlocks(content, 'upd')
      const newBlocks = [
        { id: Date.now().toString() + '-h', type: 'heading', content: title, props: { level: 2 } },
        ...contentBlocks
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
      // 创建新文档（自动解析格式为块）
      const contentBlocks = parseFormattedTextToBlocks(content, 'new')
      const doc = await documentApi.create(props.projectId, {
        title: title,
        content: contentBlocks.length ? contentBlocks : [{ id: Date.now().toString(), type: 'paragraph', content: content, props: {} }]
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
    const contentBlocks = parseFormattedTextToBlocks(content, 'auto')
    const doc = await documentApi.create(props.projectId, {
      title: title,
      content: contentBlocks.length ? contentBlocks : [{ id: Date.now().toString(), type: 'paragraph', content: content, props: {} }]
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
    const contentBlocks = parseFormattedTextToBlocks(content, 'cur')
    const newBlocks = [
      { id: Date.now().toString() + '-h', type: 'heading', content: currentChapterTitle.value, props: { level: 2 } },
      ...contentBlocks
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
    const contentBlocks = parseFormattedTextToBlocks(content, 'doc')
    const doc = await documentApi.create(props.projectId, {
      title: title,
      content: contentBlocks.length ? contentBlocks : [{ id: Date.now().toString(), type: 'paragraph', content: content, props: {} }]
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

    // 添加章节标题和内容（自动解析格式）
    const contentBlocks = parseFormattedTextToBlocks(content, 'ins')
    const newBlocks = [
      { id: Date.now().toString() + '-h', type: 'heading', content: currentChapterTitle.value, props: { level: 2 } },
      ...contentBlocks
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
    action: 'skip',
    nodeIndex: currentChapterIndex.value
  })

  ElMessage.info(`已跳过：${currentChapterTitle.value}`)
  await nextChapter()
}

async function nextChapter() {
  currentChapterIndex.value++
  if (isStopped.value) {
    step.value = 'complete'
    return
  }
  if (currentChapterIndex.value < pendingChapters.value.length) {
    await generateCurrentChapter()
  } else {
    step.value = 'complete'
  }
}

async function retryChapter() {
  if (completedChapters.value.length > 0 &&
      completedChapters.value[completedChapters.value.length - 1].error) {
    completedChapters.value.pop()
  }
  currentRetryCount.value = 0
  await generateCurrentChapter()
}

async function retryFailedChapter(completedIndex: number) {
  const chapter = completedChapters.value[completedIndex]
  if (!chapter || !chapter.error) return

  const nodeIdx = chapter.nodeIndex
  if (nodeIdx === undefined || nodeIdx < 0 || nodeIdx >= pendingChapters.value.length) {
    ElMessage.error('无法定位原始章节数据')
    return
  }

  retryingIndex.value = completedIndex
  const node = pendingChapters.value[nodeIdx]
  currentChapterTitle.value = node.title || `章节 ${nodeIdx + 1}`
  currentChapterDesc.value = node.description || ''
  currentChapterContent.value = ''
  currentChapterChars.value = 0
  generationError.value = ''
  currentRetryCount.value = 0

  try {
    isGenerating.value = true
    const res = await aiApi.batchGenerateStream({
      project_id: props.projectId,
      document_id: effectiveDocumentId.value,
      outline_nodes: [node],
      max_tokens_per_chapter: maxTokens.value,
      continue_on_complete: true,
      custom_instruction: customInstruction.value || undefined
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || '生成失败')
    }

    const reader = res.body?.getReader()
    if (!reader) throw new Error('无法读取响应流')

    const decoder = new TextDecoder()
    let fullContent = ''
    let sseBuffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      sseBuffer += decoder.decode(value, { stream: true })
      const lines = sseBuffer.split('\n')
      sseBuffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const data = line.slice(6).trim()
        if (data === '[DONE]') continue
        try {
          const parsed: AIGenerateChunk = JSON.parse(data)
          if (parsed.type === 'content' && parsed.content) {
            currentChapterContent.value += parsed.content
            currentChapterChars.value = currentChapterContent.value.length
          }
          if (parsed.type === 'chapter_complete' && parsed.chapter_content) {
            fullContent = parsed.chapter_content
            currentChapterChars.value = parsed.chapter_chars || fullContent.length
          }
          if (parsed.type === 'error') throw new Error(parsed.error_message || '服务端返回错误')
        } catch (pe: any) {
          if (pe.message && !pe.message.includes('JSON')) throw pe
        }
      }
    }

    if (!fullContent && currentChapterContent.value.trim()) fullContent = currentChapterContent.value
    if (!fullContent.trim()) throw new Error('生成结果为空')

    isGenerating.value = false

    // Auto-save the regenerated content
    if (autoInsert.value) {
      const content = fullContent
      const contentBlocks = parseFormattedTextToBlocks(content, 'retry')
      const doc = await documentApi.create(props.projectId, {
        title: currentChapterTitle.value,
        content: contentBlocks.length
          ? contentBlocks
          : [{ id: Date.now().toString(), type: 'paragraph', content, props: {} }]
      })
      emit('document-created', doc.data.id)
      emit('refresh-documents')

      completedChapters.value[completedIndex] = {
        title: currentChapterTitle.value,
        chars: fullContent.length,
        content: fullContent,
        action: 'create',
        documentId: doc.data.id,
        nodeIndex: nodeIdx
      }
      totalChars.value += fullContent.length
      ElMessage.success(`重新生成成功：${currentChapterTitle.value}`)
    } else {
      completedChapters.value[completedIndex] = {
        title: currentChapterTitle.value,
        chars: fullContent.length,
        content: fullContent,
        action: 'create',
        nodeIndex: nodeIdx
      }
      totalChars.value += fullContent.length
      ElMessage.success(`重新生成成功：${currentChapterTitle.value}`)
    }
  } catch (e: any) {
    isGenerating.value = false
    completedChapters.value[completedIndex] = {
      ...chapter,
      errorMessage: parseErrorMessage(e)
    }
    ElMessage.error(`重试失败：${parseErrorMessage(e)}`)
  } finally {
    retryingIndex.value = -1
    currentChapterContent.value = ''
  }
}

async function retryAllFailed() {
  const failedIndices = completedChapters.value
    .map((c, i) => c.error ? i : -1)
    .filter(i => i >= 0)

  if (failedIndices.length === 0) return

  retryingAll.value = true
  for (const idx of failedIndices) {
    if (isStopped.value) break
    await retryFailedChapter(idx)
  }
  retryingAll.value = false

  if (failedChapterCount.value === 0) {
    ElMessage.success('所有失败章节已重新生成成功！')
  }
}

function resetAndClose() {
  clearTimeoutTimer()
  isStopped.value = false
  isPaused.value = false
  step.value = 'select'
  selectedNodes.value = []
  completedChapters.value = []
  createdDocuments.value = []
  pendingChapters.value = []
  currentChapterContent.value = ''
  currentChapterIndex.value = 0
  currentRetryCount.value = 0
  retryingIndex.value = -1
  activeReader = null
  emit('close')
}
</script>

<style scoped lang="scss">
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes slideIn {
  from { opacity: 0; transform: translateX(-20px); }
  to { opacity: 1; transform: translateX(0); }
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
  from { opacity: 0; transform: scale(0.9); }
  to { opacity: 1; transform: scale(1); }
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

    .error-title {
      margin: 16px 0 8px;
      color: var(--el-color-danger);
      font-size: 17px;
      font-weight: 600;
    }

    .error-detail-box {
      margin: 0 auto 20px;
      max-width: 400px;
      padding: 12px 16px;
      background: var(--el-bg-color);
      border-radius: 8px;
      border: 1px solid var(--el-color-danger-light-5);
      text-align: left;

      p {
        margin: 4px 0;
        color: var(--el-text-color-secondary);
        font-size: 13px;
        word-break: break-word;
      }

      .retry-exhausted {
        color: var(--el-color-warning);
        font-weight: 500;
        margin-top: 8px;
      }
    }

    .error-actions {
      display: flex;
      justify-content: center;
      gap: 10px;
      flex-wrap: wrap;
    }
  }

  .inline-preview {
    max-height: 160px;
    margin-bottom: 12px;
    border: 1px solid var(--el-border-color-light);
    border-radius: 8px;
    padding: 12px;
    font-size: 13px;
    line-height: 1.7;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-word;
  }
}

.select-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
  padding: 8px 12px;
  background: var(--el-fill-color-light);
  border-radius: 8px;

  .select-count {
    margin-left: auto;
    font-size: 13px;
    color: var(--el-text-color-secondary);
  }
}

.generation-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  padding: 10px 14px;
  background: var(--el-fill-color-light);
  border-radius: 10px;
  border: 1px solid var(--el-border-color-lighter);

  .retry-indicator {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    color: var(--el-color-warning);
    font-weight: 500;
  }
}

.fault-tolerance-config {
  display: flex;
  flex-direction: column;
  gap: 12px;

  .retry-config,
  .timeout-config {
    display: flex;
    align-items: center;
    gap: 10px;
    padding-left: 4px;
  }

  .retry-label {
    font-size: 14px;
    color: var(--el-text-color-regular);
    white-space: nowrap;
  }
}

.failed-count {
  color: var(--el-color-danger);
  font-weight: 500;
}

.error-detail {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--el-color-danger-light-3);
  word-break: break-word;
}

.timeline-error {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--el-color-danger);
  word-break: break-word;
}

.success-state {
  text-align: center;
  padding: 40px 32px;
  background: linear-gradient(135deg, var(--el-color-success-light-9) 0%, var(--el-fill-color-light) 100%);
  border-radius: 16px;
  border: 2px solid var(--el-color-success-light-5);
  animation: scaleIn 0.4s ease-out;

  &.has-errors {
    background: linear-gradient(135deg, var(--el-color-warning-light-9) 0%, var(--el-fill-color-light) 100%);
    border-color: var(--el-color-warning-light-5);
  }

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
