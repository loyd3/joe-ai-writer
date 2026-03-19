<template>
  <div class="long-article">
    <div class="header-section">
      <h2 class="section-title">
        <span class="icon">📚</span>
        长文本写作
      </h2>
      <p class="section-desc">智能大纲规划，章节化管理，轻松创作长文</p>
    </div>

    <!-- 创建计划 -->
    <div v-if="!currentPlan" class="create-plan-section">
      <el-card class="plan-form-card">
        <template #header>
          <div class="card-header">
            <span>创建写作计划</span>
          </div>
        </template>

        <el-form :model="planForm" label-width="100px" class="plan-form">
          <el-form-item label="作品标题" required>
            <el-input
              v-model="planForm.title"
              placeholder="给你的作品起个名字"
              maxlength="200"
              show-word-limit
            />
          </el-form-item>

          <el-form-item label="作品类型">
            <div class="type-grid">
              <div
                v-for="type in articleTypes"
                :key="type.id"
                class="type-card"
                :class="{ active: planForm.articleType === type.id }"
                @click="planForm.articleType = type.id"
              >
                <span class="type-name">{{ type.name }}</span>
                <span class="type-range">{{ type.min_words/1000 }}k-{{ type.max_words/1000 }}k字</span>
              </div>
            </div>
          </el-form-item>

          <el-form-item label="目标字数">
            <div class="word-count-section">
              <el-slider
                v-model="planForm.wordCount"
                :min="currentTypeInfo.min_words"
                :max="currentTypeInfo.max_words"
                :step="1000"
                show-stops
              />
              <div class="word-count-display">
                <span class="count-number">{{ formatWordCount(planForm.wordCount) }}</span>
                <span class="count-unit">字</span>
                <span class="chapter-estimate">预计 {{ estimatedChapters }} 章</span>
              </div>
            </div>
          </el-form-item>

          <el-form-item label="写作风格">
            <div class="style-tags">
              <el-check-tag
                v-for="style in writingStyles"
                :key="style"
                :checked="planForm.style === style"
                @change="planForm.style = style"
                class="style-tag"
              >
                {{ style }}
              </el-check-tag>
            </div>
          </el-form-item>

          <el-form-item label="主题/核心">
            <el-input
              v-model="planForm.theme"
              placeholder="作品想要表达的核心主题"
              type="textarea"
              :rows="2"
            />
          </el-form-item>

          <el-form-item label="目标读者">
            <el-input
              v-model="planForm.targetAudience"
              placeholder="你的目标读者群体"
            />
          </el-form-item>

          <el-form-item label="特殊要求">
            <el-input
              v-model="planForm.requirements"
              placeholder="对作品的特殊要求或期望"
              type="textarea"
              :rows="3"
            />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              size="large"
              :loading="creating"
              @click="createPlan"
              class="create-btn"
            >
              <el-icon><Document /></el-icon>
              创建写作计划
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <!-- 写作计划详情 -->
    <div v-else class="plan-detail">
      <!-- 计划头部 -->
      <div class="plan-header">
        <div class="plan-info">
          <h3 class="plan-title">{{ currentPlan.title }}</h3>
          <p v-if="currentPlan.subtitle" class="plan-subtitle">{{ currentPlan.subtitle }}</p>
          <div class="plan-meta">
            <el-tag>{{ currentPlan.genre }}</el-tag>
            <el-tag type="success">{{ currentPlan.style }}</el-tag>
            <el-tag type="info">{{ formatWordCount(currentPlan.total_word_count) }}字</el-tag>
            <el-tag type="warning">{{ currentPlan.chapter_count }}章</el-tag>
          </div>
        </div>
        <div class="plan-actions">
          <el-button @click="currentPlan = null">新建计划</el-button>
          <el-button type="primary" @click="showExportDialog">
            导出作品
          </el-button>
        </div>
      </div>

      <!-- 进度条 -->
      <div class="progress-section">
        <div class="progress-header">
          <span>创作进度</span>
          <span class="progress-text">{{ planProgress.completed }}/{{ planProgress.total }} 章</span>
        </div>
        <el-progress
          :percentage="planProgressPercentage"
          :status="planProgressStatus"
          :stroke-width="20"
          :text-inside="true"
        />
      </div>

      <!-- 章节列表 -->
      <div class="chapters-section">
        <div class="chapters-header">
          <h4>章节大纲</h4>
          <el-button type="primary" size="small" @click="generateAllChapters" :loading="generatingAll">
            一键生成全部
          </el-button>
        </div>

        <div class="chapters-list">
          <el-collapse v-model="expandedChapters">
            <el-collapse-item
              v-for="(chapter, index) in currentPlan.chapters"
              :key="chapter.id"
              :name="chapter.id"
            >
              <template #title>
                <div class="chapter-title-row">
                  <span class="chapter-number">第{{ index + 1 }}章</span>
                  <span class="chapter-title-text">{{ chapter.title }}</span>
                  <el-tag
                    :type="getChapterStatusType(chapter.status)"
                    size="small"
                    class="chapter-status"
                  >
                    {{ getChapterStatusText(chapter.status) }}
                  </el-tag>
                  <span class="chapter-word-count">{{ chapter.word_count }}字</span>
                </div>
              </template>

              <div class="chapter-detail">
                <div class="chapter-summary">
                  <h5>章节概要</h5>
                  <p>{{ chapter.summary }}</p>
                </div>

                <div class="chapter-key-points" v-if="chapter.key_points?.length">
                  <h5>关键要点</h5>
                  <ul>
                    <li v-for="(point, pIndex) in chapter.key_points" :key="pIndex">
                      {{ point }}
                    </li>
                  </ul>
                </div>

                <div class="chapter-actions">
                  <el-button
                    v-if="chapter.status !== 'completed'"
                    type="primary"
                    size="small"
                    @click="generateChapter(chapter)"
                    :loading="generatingChapterId === chapter.id"
                  >
                    {{ chapter.status === 'pending' ? '生成内容' : '继续生成' }}
                  </el-button>
                  <el-button
                    v-else
                    type="success"
                    size="small"
                    @click="viewChapter(chapter)"
                  >
                    查看内容
                  </el-button>
                  <el-button
                    size="small"
                    @click="editChapter(chapter)"
                  >
                    编辑信息
                  </el-button>
                  <el-button
                    v-if="chapter.status === 'completed'"
                    type="warning"
                    size="small"
                    @click="regenerateChapter(chapter)"
                  >
                    重新生成
                  </el-button>
                </div>

                <!-- 章节内容预览 -->
                <div v-if="chapter.content_preview" class="chapter-preview">
                  <h5>内容预览</h5>
                  <div class="preview-text">{{ chapter.content_preview }}</div>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>

      <!-- 人物设定 -->
      <div v-if="currentPlan.characters?.length" class="characters-section">
        <h4>主要人物</h4>
        <div class="characters-grid">
          <el-card
            v-for="(char, index) in currentPlan.characters"
            :key="index"
            class="character-card"
            shadow="hover"
          >
            <template #header>
              <div class="character-header">
                <span class="character-name">{{ char.name }}</span>
                <el-tag size="small" type="info">{{ char.role }}</el-tag>
              </div>
            </template>
            <p><strong>性格:</strong> {{ char.traits }}</p>
            <p v-if="char.arc"><strong>人物弧线:</strong> {{ char.arc }}</p>
          </el-card>
        </div>
      </div>

      <!-- 世界观 -->
      <div v-if="currentPlan.world_building?.setting" class="world-section">
        <h4>世界观设定</h4>
        <el-card class="world-card">
          <p><strong>背景设定:</strong> {{ currentPlan.world_building.setting }}</p>
          <p v-if="currentPlan.world_building.rules"><strong>世界规则:</strong> {{ currentPlan.world_building.rules }}</p>
          <p v-if="currentPlan.world_building.atmosphere"><strong>氛围基调:</strong> {{ currentPlan.world_building.atmosphere }}</p>
        </el-card>
      </div>
    </div>

    <!-- 编辑章节对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑章节" width="60%">
      <el-form :model="editingChapter" label-width="100px" v-if="editingChapter">
        <el-form-item label="章节标题">
          <el-input v-model="editingChapter.title" />
        </el-form-item>
        <el-form-item label="章节概要">
          <el-input v-model="editingChapter.summary" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="建议字数">
          <el-input-number v-model="editingChapter.word_count" :min="1000" :step="500" />
        </el-form-item>
        <el-form-item label="关键要点">
          <div v-for="(point, index) in editingChapter.key_points" :key="index" class="point-input">
            <el-input v-model="editingChapter.key_points[index]" class="point-field">
              <template #append>
                <el-button @click="removePoint(index)">删除</el-button>
              </template>
            </el-input>
          </div>
          <el-button type="primary" @click="addPoint">添加要点</el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveChapterEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 查看章节内容对话框 -->
    <el-dialog v-model="viewDialogVisible" title="章节内容" width="70%">
      <div v-if="viewingChapter" class="chapter-content-view">
        <h3>{{ viewingChapter.title }}</h3>
        <div class="content-text" v-html="formatChapterContent(viewingChapter.fullContent || viewingChapter.content_preview)"></div>
      </div>
      <template #footer>
        <el-button @click="viewDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="copyChapterContent">复制内容</el-button>
      </template>
    </el-dialog>

    <!-- 导出对话框 -->
    <el-dialog v-model="exportDialogVisible" title="导出作品" width="50%">
      <div class="export-options">
        <p>导出格式: 纯文本 (.txt)</p>
        <el-alert
          title="导出信息"
          type="info"
          :closable="false"
        >
          <p>作品: {{ currentPlan?.title }}</p>
          <p>已完成章节: {{ planProgress.completed }}/{{ planProgress.total }}</p>
        </el-alert>
      </div>
      <template #footer>
        <el-button @click="exportDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="exportArticle" :loading="exporting">
          导出
        </el-button>
      </template>
    </el-dialog>

    <!-- 生成进度对话框 -->
    <el-dialog
      v-model="progressDialogVisible"
      title="生成章节"
      width="50%"
      :close-on-click-modal="false"
      :show-close="false"
    >
      <div class="generation-progress">
        <p class="generating-chapter">正在生成: {{ generatingChapterTitle }}</p>
        <el-progress
          :percentage="generationProgress"
          :status="generationStatus"
          :stroke-width="15"
        />
        <div class="generation-log" ref="generationLog">
          <p v-for="(log, index) in generationLogs" :key="index" :class="log.type">
            {{ log.message }}
          </p>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Document } from '@element-plus/icons-vue'
import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000/api'

// 状态
const articleTypes = ref([])
const writingStyles = ref([])
const currentPlan = ref(null)
const creating = ref(false)
const expandedChapters = ref([])
const generatingChapterId = ref(null)
const generatingAll = ref(false)

// 表单
const planForm = ref({
  title: '',
  articleType: 'novel',
  wordCount: 50000,
  style: '专业严谨',
  theme: '',
  targetAudience: '',
  requirements: ''
})

// 对话框状态
const editDialogVisible = ref(false)
const editingChapter = ref(null)
const viewDialogVisible = ref(false)
const viewingChapter = ref(null)
const exportDialogVisible = ref(false)
const exporting = ref(false)
const progressDialogVisible = ref(false)
const generatingChapterTitle = ref('')
const generationProgress = ref(0)
const generationStatus = ref('')
const generationLogs = ref([])

// 计算属性
const currentTypeInfo = computed(() => {
  return articleTypes.value.find(t => t.id === planForm.value.articleType) || {
    min_words: 10000,
    max_words: 500000,
    default_words: 50000
  }
})

const estimatedChapters = computed(() => {
  return Math.max(3, Math.min(20, Math.ceil(planForm.value.wordCount / 3000)))
})

const planProgress = computed(() => {
  if (!currentPlan.value) return { total: 0, completed: 0 }
  const chapters = currentPlan.value.chapters || []
  return {
    total: chapters.length,
    completed: chapters.filter(c => c.status === 'completed').length
  }
})

const planProgressPercentage = computed(() => {
  if (planProgress.value.total === 0) return 0
  return Math.round((planProgress.value.completed / planProgress.value.total) * 100)
})

const planProgressStatus = computed(() => {
  if (planProgressPercentage.value === 100) return 'success'
  if (planProgressPercentage.value > 0) return ''
  return ''
})

// 方法
const formatWordCount = (count) => {
  if (count >= 10000) {
    return (count / 10000).toFixed(1) + '万'
  }
  return count.toLocaleString()
}

const fetchArticleTypes = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/long-article/types`)
    articleTypes.value = response.data.types
  } catch (error) {
    console.error('获取文章类型失败:', error)
  }
}

const fetchWritingStyles = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/long-article/styles`)
    writingStyles.value = response.data.styles
  } catch (error) {
    console.error('获取写作风格失败:', error)
  }
}

const createPlan = async () => {
  if (!planForm.value.title.trim()) {
    ElMessage.warning('请输入作品标题')
    return
  }

  creating.value = true
  try {
    const response = await axios.post(`${API_BASE_URL}/long-article/plan`, {
      title: planForm.value.title,
      article_type: planForm.value.articleType,
      total_word_count: planForm.value.wordCount,
      style: planForm.value.style,
      theme: planForm.value.theme,
      target_audience: planForm.value.targetAudience,
      requirements: planForm.value.requirements
    })

    if (response.data.success) {
      currentPlan.value = response.data.plan
      expandedChapters.value = []
      ElMessage.success('写作计划创建成功！')
    }
  } catch (error) {
    console.error('创建计划失败:', error)
    ElMessage.error('创建计划失败，请重试')
  } finally {
    creating.value = false
  }
}

const getChapterStatusType = (status) => {
  const types = {
    pending: 'info',
    writing: 'warning',
    completed: 'success'
  }
  return types[status] || 'info'
}

const getChapterStatusText = (status) => {
  const texts = {
    pending: '待生成',
    writing: '生成中',
    completed: '已完成'
  }
  return texts[status] || status
}

const generateChapter = async (chapter) => {
  generatingChapterId.value = chapter.id
  progressDialogVisible.value = true
  generatingChapterTitle.value = chapter.title
  generationProgress.value = 0
  generationStatus.value = ''
  generationLogs.value = [{ type: 'info', message: '开始生成章节...' }]

  try {
    const response = await fetch(
      `${API_BASE_URL}/long-article/plan/${currentPlan.value.id}/chapter/${chapter.id}/generate`,
      { method: 'POST' }
    )

    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const text = decoder.decode(value)
      const lines = text.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            if (data.progress) {
              generationProgress.value = Math.min(100, Math.round(data.progress * 100))
            }
            if (data.type === 'complete') {
              generationLogs.value.push({ type: 'success', message: '章节生成完成！' })
              generationProgress.value = 100
              generationStatus.value = 'success'
              // 刷新计划数据
              await refreshPlan()
            }
          } catch (e) {
            // 忽略解析错误
          }
        }
      }
    }
  } catch (error) {
    console.error('生成章节失败:', error)
    generationLogs.value.push({ type: 'error', message: '生成失败: ' + error.message })
    generationStatus.value = 'exception'
    ElMessage.error('生成章节失败')
  } finally {
    generatingChapterId.value = null
    setTimeout(() => {
      progressDialogVisible.value = false
    }, 1000)
  }
}

const generateAllChapters = async () => {
  generatingAll.value = true
  const pendingChapters = currentPlan.value.chapters.filter(c => c.status === 'pending')

  for (const chapter of pendingChapters) {
    await generateChapter(chapter)
  }

  generatingAll.value = false
  ElMessage.success('全部章节生成完成！')
}

const refreshPlan = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/long-article/plan/${currentPlan.value.id}`)
    if (response.data.success) {
      currentPlan.value = response.data.plan
    }
  } catch (error) {
    console.error('刷新计划失败:', error)
  }
}

const editChapter = (chapter) => {
  editingChapter.value = JSON.parse(JSON.stringify(chapter))
  editDialogVisible.value = true
}

const saveChapterEdit = async () => {
  try {
    await axios.put(
      `${API_BASE_URL}/long-article/plan/${currentPlan.value.id}/chapter/${editingChapter.value.id}`,
      editingChapter.value
    )
    await refreshPlan()
    editDialogVisible.value = false
    ElMessage.success('保存成功')
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error('保存失败')
  }
}

const addPoint = () => {
  if (!editingChapter.value.key_points) {
    editingChapter.value.key_points = []
  }
  editingChapter.value.key_points.push('')
}

const removePoint = (index) => {
  editingChapter.value.key_points.splice(index, 1)
}

const viewChapter = async (chapter) => {
  viewingChapter.value = chapter
  viewDialogVisible.value = true
}

const formatChapterContent = (content) => {
  if (!content) return ''
  return content.replace(/\n/g, '<br>')
}

const copyChapterContent = () => {
  const content = viewingChapter.value?.fullContent || viewingChapter.value?.content_preview || ''
  navigator.clipboard.writeText(content)
  ElMessage.success('内容已复制')
}

const regenerateChapter = async (chapter) => {
  try {
    await axios.post(
      `${API_BASE_URL}/long-article/plan/${currentPlan.value.id}/chapter/${chapter.id}/regenerate`,
      {}
    )
    chapter.status = 'pending'
    chapter.content_preview = ''
    ElMessage.success('章节已重置，可以重新生成')
  } catch (error) {
    console.error('重置章节失败:', error)
    ElMessage.error('重置失败')
  }
}

const showExportDialog = () => {
  exportDialogVisible.value = true
}

const exportArticle = async () => {
  exporting.value = true
  try {
    const response = await axios.get(
      `${API_BASE_URL}/long-article/plan/${currentPlan.value.id}/export?format=txt`
    )

    if (response.data.content) {
      // 创建下载
      const blob = new Blob([response.data.content], { type: 'text/plain;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${response.data.title || '作品'}.txt`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      ElMessage.success('导出成功！')
      exportDialogVisible.value = false
    }
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

// 初始化
onMounted(() => {
  fetchArticleTypes()
  fetchWritingStyles()
})
</script>

<style scoped>
.long-article {
  padding: 20px;
}

.header-section {
  text-align: center;
  margin-bottom: 30px;
}

.section-title {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.section-title .icon {
  font-size: 28px;
}

.section-desc {
  color: #909399;
  font-size: 14px;
}

.plan-form-card {
  max-width: 800px;
  margin: 0 auto;
}

.card-header {
  font-weight: 600;
}

.plan-form {
  padding: 20px 0;
}

.type-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

.type-card {
  padding: 12px;
  border: 2px solid #e4e7ed;
  border-radius: 8px;
  cursor: pointer;
  text-align: center;
  transition: all 0.3s ease;
}

.type-card:hover {
  border-color: #409eff;
}

.type-card.active {
  border-color: #409eff;
  background: #ecf5ff;
}

.type-name {
  display: block;
  font-weight: 500;
  margin-bottom: 4px;
}

.type-range {
  font-size: 12px;
  color: #909399;
}

.word-count-section {
  padding: 10px 0;
}

.word-count-display {
  margin-top: 10px;
  text-align: center;
}

.count-number {
  font-size: 24px;
  font-weight: 600;
  color: #409eff;
}

.count-unit {
  margin-left: 5px;
  color: #606266;
}

.chapter-estimate {
  margin-left: 20px;
  color: #909399;
}

.style-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.style-tag {
  cursor: pointer;
}

.create-btn {
  padding: 15px 40px;
  font-size: 16px;
}

.plan-detail {
  max-width: 1000px;
  margin: 0 auto;
}

.plan-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 25px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 10px;
}

.plan-title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.plan-subtitle {
  color: #606266;
  margin-bottom: 12px;
}

.plan-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.plan-actions {
  display: flex;
  gap: 10px;
}

.progress-section {
  margin-bottom: 25px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
  font-weight: 500;
}

.progress-text {
  color: #409eff;
}

.chapters-section {
  margin-bottom: 25px;
}

.chapters-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.chapters-header h4 {
  margin: 0;
}

.chapter-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
}

.chapter-number {
  font-weight: 500;
  color: #909399;
}

.chapter-title-text {
  flex: 1;
  font-weight: 500;
}

.chapter-status {
  margin-left: auto;
}

.chapter-word-count {
  color: #909399;
  font-size: 13px;
}

.chapter-detail {
  padding: 15px;
}

.chapter-summary h5,
.chapter-key-points h5,
.chapter-preview h5 {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.chapter-summary p {
  color: #606266;
  line-height: 1.6;
}

.chapter-key-points ul {
  margin: 0;
  padding-left: 20px;
  color: #606266;
}

.chapter-key-points li {
  margin-bottom: 4px;
}

.chapter-actions {
  margin-top: 15px;
  display: flex;
  gap: 10px;
}

.chapter-preview {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #e4e7ed;
}

.preview-text {
  background: #f5f7fa;
  padding: 15px;
  border-radius: 6px;
  color: #606266;
  font-size: 14px;
  line-height: 1.6;
  max-height: 150px;
  overflow-y: auto;
}

.characters-section,
.world-section {
  margin-bottom: 25px;
}

.characters-section h4,
.world-section h4 {
  margin-bottom: 15px;
}

.characters-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 15px;
}

.character-card {
  transition: all 0.3s ease;
}

.character-card:hover {
  transform: translateY(-2px);
}

.character-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.character-name {
  font-weight: 600;
}

.world-card {
  line-height: 1.8;
}

.world-card p {
  margin-bottom: 10px;
}

.point-input {
  margin-bottom: 10px;
}

.point-field {
  width: 100%;
}

.chapter-content-view {
  max-height: 60vh;
  overflow-y: auto;
}

.chapter-content-view h3 {
  margin-bottom: 20px;
  text-align: center;
}

.content-text {
  line-height: 1.8;
  color: #303133;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.generation-progress {
  padding: 20px;
}

.generating-chapter {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 15px;
}

.generation-log {
  margin-top: 20px;
  max-height: 200px;
  overflow-y: auto;
  background: #f5f7fa;
  padding: 15px;
  border-radius: 6px;
}

.generation-log p {
  margin: 5px 0;
  font-size: 13px;
}

.generation-log .info {
  color: #409eff;
}

.generation-log .success {
  color: #67c23a;
}

.generation-log .error {
  color: #f56c6c;
}

@media (max-width: 768px) {
  .type-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .plan-header {
    flex-direction: column;
    gap: 15px;
  }

  .characters-grid {
    grid-template-columns: 1fr;
  }
}
</style>
