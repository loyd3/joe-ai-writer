<template>
  <div class="long-article-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>📚 长篇文章生成器</h1>
      <p class="subtitle">支持生成10万至100万字的超长文章，智能分章节生成，断点续写</p>
    </div>

    <!-- 步骤一：创建任务 -->
    <el-card class="step-card" v-if="step === 'create'">
      <template #header>
        <span>📝 第一步：设置文章参数</span>
      </template>

      <el-form :model="form" label-position="top" :rules="rules" ref="formRef">
        <el-form-item label="文章主题 / 核心内容" prop="topic">
          <el-input
            v-model="form.topic"
            type="textarea"
            :rows="3"
            placeholder="例如：人工智能对现代社会的深远影响与未来展望..."
          />
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="写作风格" prop="style">
              <el-select v-model="form.style" style="width: 100%">
                <el-option label="专业学术" value="专业学术" />
                <el-option label="通俗易懂" value="通俗易懂" />
                <el-option label="新闻报道" value="新闻报道" />
                <el-option label="文学叙事" value="文学叙事" />
                <el-option label="商业分析" value="商业分析" />
                <el-option label="科普教育" value="科普教育" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="目标字数" prop="targetWords">
              <el-select v-model="form.targetWords" style="width: 100%">
                <el-option label="10万字" :value="100000" />
                <el-option label="20万字" :value="200000" />
                <el-option label="50万字" :value="500000" />
                <el-option label="100万字" :value="1000000" />
                <el-option label="自定义" value="custom" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item v-if="form.targetWords === 'custom'" label="自定义字数">
          <el-input-number
            v-model="form.customWords"
            :min="10000"
            :max="2000000"
            :step="10000"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="额外要求（可选）">
          <el-input
            v-model="form.requirements"
            type="textarea"
            :rows="2"
            placeholder="例如：需要包含大量数据支撑，每章结尾有小结，语言要严谨..."
          />
        </el-form-item>

        <div class="action-buttons">
          <el-button type="primary" size="large" @click="handleCreate" :loading="creating">
            <el-icon><DocumentAdd /></el-icon>
            创建任务并生成大纲
          </el-button>
        </div>
      </el-form>
    </el-card>

    <!-- 步骤二：确认大纲 -->
    <div v-if="step === 'outline'">
      <el-card class="step-card">
        <template #header>
          <div class="card-header-row">
            <span>📋 第二步：确认文章大纲</span>
            <el-button size="small" @click="regenerateOutline" :loading="generatingOutline">
              重新生成大纲
            </el-button>
          </div>
        </template>

        <div v-if="generatingOutline" class="loading-state">
          <el-icon class="spinning"><Loading /></el-icon>
          <span>正在生成大纲，请稍候...</span>
        </div>

        <div v-else-if="outline" class="outline-view">
          <div class="outline-meta">
            <h2>{{ outline.title }}</h2>
            <p class="outline-intro">{{ outline.introduction }}</p>
            <el-tag>{{ outline.style }}</el-tag>
            <el-tag type="info" style="margin-left: 8px">
              共 {{ outline.chapters?.length }} 章
            </el-tag>
            <el-tag type="success" style="margin-left: 8px">
              预计 {{ formatWordCount(totalTargetWords) }}
            </el-tag>
          </div>

          <el-collapse class="chapter-list">
            <el-collapse-item
              v-for="(chapter, idx) in outline.chapters"
              :key="idx"
              :title="`第 ${idx + 1} 章：${chapter.title}`"
              :name="idx"
            >
              <div class="chapter-detail">
                <p class="chapter-words">预计字数：{{ chapter.target_words?.toLocaleString() }} 字</p>
                <ul>
                  <li v-for="(point, pi) in chapter.key_points" :key="pi">{{ point }}</li>
                </ul>
              </div>
            </el-collapse-item>
          </el-collapse>

          <div class="action-buttons" style="margin-top: 24px">
            <el-button @click="step = 'create'">← 返回修改</el-button>
            <el-button type="primary" size="large" @click="startGeneration">
              <el-icon><VideoPlay /></el-icon>
              确认大纲，开始生成
            </el-button>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 步骤三：生成中 -->
    <div v-if="step === 'generating'">
      <!-- 总体进度 -->
      <el-card class="step-card progress-card">
        <template #header>
          <div class="card-header-row">
            <span>⚡ 正在生成文章</span>
            <div>
              <el-tag :type="statusTagType">{{ statusText }}</el-tag>
            </div>
          </div>
        </template>

        <div class="progress-overview">
          <div class="progress-stats">
            <div class="stat-item">
              <span class="stat-value">{{ completedChapters }}</span>
              <span class="stat-label">已完成章节</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ outline?.chapters?.length || 0 }}</span>
              <span class="stat-label">总章节数</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ formatWordCount(totalGeneratedWords) }}</span>
              <span class="stat-label">已生成字数</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ estimatedTimeLeft }}</span>
              <span class="stat-label">预计剩余时间</span>
            </div>
          </div>

          <el-progress
            :percentage="overallProgress"
            :stroke-width="16"
            status="active"
            style="margin-top: 16px"
          />
          <p class="progress-message">{{ currentMessage }}</p>
        </div>
      </el-card>

      <!-- 章节进度列表 -->
      <el-card class="step-card chapters-card">
        <template #header>
          <span>📖 章节生成状态</span>
        </template>

        <div class="chapter-progress-list">
          <div
            v-for="(chapter, idx) in outline?.chapters || []"
            :key="idx"
            class="chapter-progress-item"
            :class="{
              completed: idx < completedChapters,
              active: idx === currentChapterIndex,
              pending: idx > currentChapterIndex
            }"
          >
            <div class="chapter-status-icon">
              <el-icon v-if="idx < completedChapters" color="#67c23a"><CircleCheck /></el-icon>
              <el-icon v-else-if="idx === currentChapterIndex" class="spinning" color="#409eff"><Loading /></el-icon>
              <el-icon v-else color="#c0c4cc"><Clock /></el-icon>
            </div>
            <div class="chapter-info">
              <span class="chapter-title">第 {{ idx + 1 }} 章：{{ chapter.title }}</span>
              <span class="chapter-words" v-if="idx < completedChapters">
                {{ chapterWordCounts[idx]?.toLocaleString() }} 字
              </span>
              <span class="chapter-words generating" v-else-if="idx === currentChapterIndex">
                生成中...
              </span>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 实时内容预览 -->
      <el-card class="step-card preview-card" v-if="currentChapterContent">
        <template #header>
          <span>👁️ 实时预览 - 第 {{ currentChapterIndex + 1 }} 章</span>
        </template>
        <div class="content-preview">{{ currentChapterContent }}</div>
      </el-card>
    </div>

    <!-- 步骤四：完成 -->
    <div v-if="step === 'completed'">
      <el-card class="step-card complete-card">
        <div class="complete-content">
          <el-icon class="complete-icon" color="#67c23a"><CircleCheck /></el-icon>
          <h2>文章生成完成！</h2>
          <div class="complete-stats">
            <el-statistic title="总章节数" :value="completedChapters" />
            <el-statistic title="总字数" :value="totalGeneratedWords" />
            <el-statistic title="生成耗时" :value="elapsedTime" suffix="分钟" />
          </div>
          <div class="export-buttons">
            <el-button type="primary" size="large" @click="exportArticle('txt')">
              <el-icon><Download /></el-icon>
              导出 TXT
            </el-button>
            <el-button type="success" size="large" @click="exportArticle('md')">
              <el-icon><Download /></el-icon>
              导出 Markdown
            </el-button>
            <el-button size="large" @click="viewChapters">
              <el-icon><View /></el-icon>
              查看全文
            </el-button>
          </div>
        </div>
      </el-card>

      <!-- 章节列表 -->
      <el-card class="step-card" v-if="showChapters">
        <template #header>
          <span>📖 全文章节</span>
        </template>
        <el-collapse>
          <el-collapse-item
            v-for="(chapter, idx) in generatedChapters"
            :key="idx"
            :title="`第 ${idx + 1} 章：${chapter.title}（${chapter.word_count?.toLocaleString()} 字）`"
            :name="idx"
          >
            <div class="chapter-content">{{ chapter.content }}</div>
          </el-collapse-item>
        </el-collapse>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  DocumentAdd, VideoPlay, Loading, CircleCheck, Clock,
  Download, View
} from '@element-plus/icons-vue'
import { longArticleApi } from '@/api/longArticle'

const route = useRoute()

// 表单
const formRef = ref(null)
const form = ref({
  topic: '',
  style: '专业学术',
  targetWords: 100000,
  customWords: 100000,
  requirements: ''
})

const rules = {
  topic: [{ required: true, message: '请输入文章主题', trigger: 'blur' }],
  style: [{ required: true, message: '请选择写作风格', trigger: 'change' }]
}

// 状态
const step = ref('create')
const creating = ref(false)
const generatingOutline = ref(false)
const articleId = ref(null)
const outline = ref(null)
const eventSource = ref(null)

// 生成进度
const overallProgress = ref(0)
const currentChapterIndex = ref(-1)
const completedChapters = ref(0)
const currentMessage = ref('')
const currentChapterContent = ref('')
const chapterWordCounts = ref({})
const totalGeneratedWords = ref(0)
const generatedChapters = ref([])
const showChapters = ref(false)
const startTime = ref(null)

// 计算属性
const actualTargetWords = computed(() => {
  return form.value.targetWords === 'custom'
    ? form.value.customWords
    : form.value.targetWords
})

const totalTargetWords = computed(() => {
  if (!outline.value?.chapters) return 0
  return outline.value.chapters.reduce((sum, ch) => sum + (ch.target_words || 0), 0)
})

const statusText = computed(() => {
  if (overallProgress.value >= 100) return '已完成'
  if (currentChapterIndex.value >= 0) return '生成中'
  return '准备中'
})

const statusTagType = computed(() => {
  if (overallProgress.value >= 100) return 'success'
  if (currentChapterIndex.value >= 0) return 'primary'
  return 'info'
})

const estimatedTimeLeft = computed(() => {
  if (!startTime.value || completedChapters.value === 0) return '计算中...'
  const elapsed = (Date.now() - startTime.value) / 1000 / 60
  const total = outline.value?.chapters?.length || 1
  const perChapter = elapsed / completedChapters.value
  const remaining = (total - completedChapters.value) * perChapter
  if (remaining < 1) return '< 1 分钟'
  return `约 ${Math.ceil(remaining)} 分钟`
})

const elapsedTime = computed(() => {
  if (!startTime.value) return 0
  return Math.ceil((Date.now() - startTime.value) / 1000 / 60)
})

// 方法
const formatWordCount = (n) => {
  if (!n) return '0'
  if (n >= 10000) return `${(n / 10000).toFixed(1)}万字`
  return `${n.toLocaleString()}字`
}

const handleCreate = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  creating.value = true
  try {
    const result = await longArticleApi.createArticle({
      project_id: 1, // TODO: 从路由或store获取
      topic: form.value.topic,
      target_words: actualTargetWords.value,
      style: form.value.style,
      requirements: form.value.requirements || undefined
    })

    articleId.value = result.article_id
    step.value = 'outline'
    await fetchOutline()
  } catch (e) {
    ElMessage.error('创建失败：' + (e.response?.data?.detail || e.message))
  } finally {
    creating.value = false
  }
}

const fetchOutline = async () => {
  if (!articleId.value) return
  generatingOutline.value = true
  try {
    const result = await longArticleApi.generateOutline(articleId.value)
    outline.value = result.outline
  } catch (e) {
    ElMessage.error('大纲加载失败：' + (e.response?.data?.detail || e.message))
  } finally {
    generatingOutline.value = false
  }
}

onMounted(async () => {
  const id = route.query.articleId
  if (id) {
    articleId.value = Number(id)
    step.value = 'outline'
    await fetchOutline()
  }
})

const regenerateOutline = async () => {
  generatingOutline.value = true
  try {
    const result = await longArticleApi.generateOutline(articleId.value, true)
    outline.value = result.outline
    ElMessage.success('大纲已重新生成')
  } catch (e) {
    ElMessage.error('重新生成失败：' + (e.response?.data?.detail || e.message))
  } finally {
    generatingOutline.value = false
  }
}

const startGeneration = () => {
  step.value = 'generating'
  startTime.value = Date.now()
  connectSSE()
}

const connectSSE = () => {
  if (eventSource.value) {
    eventSource.value.close()
  }

  const es = new EventSource(
    `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/long-article/generate/${articleId.value}`
  )

  es.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      handleSSEEvent(data)
    } catch (e) {
      console.error('SSE parse error:', e)
    }
  }

  es.onerror = (err) => {
    console.error('SSE error:', err)
    es.close()
    ElMessage.error('连接中断，请尝试恢复生成')
  }

  eventSource.value = es
}

const handleSSEEvent = (event) => {
  switch (event.type) {
    case 'progress':
      overallProgress.value = event.data.progress || 0
      currentMessage.value = event.data.message || ''
      if (event.data.chapter_index !== undefined) {
        currentChapterIndex.value = event.data.chapter_index
        currentChapterContent.value = ''
      }
      break

    case 'outline':
      outline.value = event.data
      break

    case 'chapter_chunk':
      currentChapterContent.value += event.data.chunk
      break

    case 'chapter_complete':
      completedChapters.value++
      chapterWordCounts.value[event.data.chapter_index] = event.data.word_count
      totalGeneratedWords.value += event.data.word_count
      currentChapterContent.value = ''
      break

    case 'complete':
      overallProgress.value = 100
      currentMessage.value = '文章生成完成！'
      eventSource.value?.close()
      step.value = 'completed'
      loadGeneratedChapters()
      break

    case 'error':
      ElMessage.error('生成出错：' + event.data.message)
      eventSource.value?.close()
      break
  }
}

const loadGeneratedChapters = async () => {
  try {
    const result = await longArticleApi.getChapters(articleId.value)
    generatedChapters.value = result.chapters
  } catch (e) {
    console.error('加载章节失败', e)
  }
}

const viewChapters = async () => {
  if (generatedChapters.value.length === 0) {
    await loadGeneratedChapters()
  }
  showChapters.value = !showChapters.value
}

const exportArticle = async (format) => {
  try {
    const blob = await longArticleApi.exportArticle(articleId.value, format)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `article_${articleId.value}.${format}`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败：' + e.message)
  }
}

onUnmounted(() => {
  eventSource.value?.close()
})
</script>

<style scoped>
.long-article-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 28px;
  margin: 0 0 8px;
}

.subtitle {
  color: #666;
  margin: 0;
}

.step-card {
  margin-bottom: 20px;
}

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.action-buttons {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 16px;
}

.loading-state {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 40px;
  justify-content: center;
  color: #666;
  font-size: 16px;
}

.outline-meta {
  margin-bottom: 20px;
}

.outline-meta h2 {
  margin: 0 0 8px;
}

.outline-intro {
  color: #666;
  margin-bottom: 12px;
}

.chapter-detail {
  padding: 8px 0;
}

.chapter-words {
  color: #409eff;
  font-size: 13px;
  margin-bottom: 8px;
}

.chapter-detail ul {
  margin: 0;
  padding-left: 20px;
  color: #555;
}

.chapter-detail li {
  margin-bottom: 4px;
}

/* 进度卡片 */
.progress-overview {
  padding: 8px 0;
}

.progress-stats {
  display: flex;
  gap: 32px;
  margin-bottom: 16px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #409eff;
}

.stat-label {
  font-size: 13px;
  color: #888;
  margin-top: 4px;
}

.progress-message {
  text-align: center;
  color: #666;
  margin-top: 12px;
}

/* 章节进度列表 */
.chapter-progress-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.chapter-progress-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 6px;
  background: #f5f7fa;
  transition: all 0.3s;
}

.chapter-progress-item.completed {
  background: #f0f9eb;
}

.chapter-progress-item.active {
  background: #ecf5ff;
  border: 1px solid #b3d8ff;
}

.chapter-progress-item.pending {
  opacity: 0.6;
}

.chapter-status-icon {
  flex-shrink: 0;
  font-size: 18px;
}

.chapter-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex: 1;
}

.chapter-title {
  font-size: 14px;
}

.chapter-words {
  font-size: 13px;
  color: #67c23a;
}

.chapter-words.generating {
  color: #409eff;
}

/* 内容预览 */
.content-preview {
  max-height: 300px;
  overflow-y: auto;
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.8;
  color: #333;
  padding: 8px;
}

/* 完成页 */
.complete-content {
  text-align: center;
  padding: 32px;
}

.complete-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.complete-stats {
  display: flex;
  justify-content: center;
  gap: 48px;
  margin: 24px 0;
}

.export-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.chapter-content {
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.8;
  color: #333;
  max-height: 500px;
  overflow-y: auto;
  padding: 8px;
}

/* 旋转动画 */
.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
