<template>
  <div class="hot-topics-page">
    <div class="page-header">
      <h1>🔥 热点写作</h1>
      <p class="subtitle">搜罗网络热点，AI生成提纲，一键创作文章</p>
    </div>

    <!-- 步骤条 -->
    <el-steps :active="currentStep" finish-status="success" class="steps">
      <el-step title="选择热点" description="从各平台热搜中选择" />
      <el-step title="生成大纲" description="AI分析并生成文章结构" />
      <el-step title="生成文章" description="AI根据大纲写作" />
      <el-step title="保存文档" description="保存到项目" />
    </el-steps>

    <!-- 步骤1: 选择热点 -->
    <div v-if="currentStep === 0" class="step-content">
      <div class="toolbar">
        <el-button type="primary" @click="fetchHotTopics" :loading="loading">
          <el-icon><Refresh /></el-icon> 刷新热点
        </el-button>
        <el-input
          v-model="searchQuery"
          placeholder="搜索热点..."
          prefix-icon="Search"
          clearable
          style="width: 300px"
        />
      </div>

      <!-- 热点列表 -->
      <div v-if="loading" class="loading-container">
        <el-skeleton :rows="10" animated />
      </div>

      <div v-else-if="hotTopics.length === 0" class="empty-state">
        <el-empty description="暂无热点数据，点击刷新获取最新热点" />
      </div>

      <div v-else class="topics-grid">
        <div
          v-for="topic in filteredTopics"
          :key="topic.title + topic.source"
          class="topic-card"
          @click="selectTopic(topic)"
        >
          <div class="topic-header">
            <span class="topic-source" :class="getSourceClass(topic.source)">
              {{ topic.source }}
            </span>
            <span v-if="topic.category" class="topic-category">{{ topic.category }}</span>
          </div>
          <h3 class="topic-title">{{ topic.title }}</h3>
          <div class="topic-meta">
            <span v-if="topic.heat" class="topic-heat">
              <el-icon><TrendCharts /></el-icon> {{ formatHeat(topic.heat) }}
            </span>
            <el-button type="primary" size="small" @click.stop="selectTopic(topic)">
              选择这个话题
            </el-button>
          </div>
          <p v-if="topic.excerpt" class="topic-excerpt">{{ topic.excerpt }}</p>
        </div>
      </div>
    </div>

    <!-- 步骤2: 配置大纲参数 -->
    <div v-if="currentStep === 1" class="step-content">
      <el-card class="config-card">
        <template #header>
          <div class="card-header">
            <span>📋 大纲配置</span>
            <el-tag type="info">已选: {{ selectedTopic?.title }}</el-tag>
          </div>
        </template>

        <el-form :model="outlineConfig" label-position="top">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="文章类型">
                <el-select v-model="outlineConfig.articleType" style="width: 100%">
                  <el-option label="深度分析" value="深度分析" />
                  <el-option label="快讯报道" value="快讯" />
                  <el-option label="观点评论" value="评论" />
                  <el-option label="故事叙述" value="故事" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="目标字数">
                <el-slider v-model="outlineConfig.wordCount" :min="500" :max="3000" :step="100" show-stops />
                <span class="slider-value">{{ outlineConfig.wordCount }} 字</span>
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item label="写作风格">
            <el-radio-group v-model="outlineConfig.style">
              <el-radio-button label="专业">专业严谨</el-radio-button>
              <el-radio-button label="轻松">轻松易懂</el-radio-button>
              <el-radio-button label="犀利">观点犀利</el-radio-button>
              <el-radio-button label="温情">温情治愈</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </el-form>

        <div class="action-buttons">
          <el-button @click="currentStep = 0">上一步</el-button>
          <el-button type="primary" @click="generateOutline" :loading="generatingOutline">
            <el-icon><MagicStick /></el-icon> AI生成大纲
          </el-button>
        </div>
      </el-card>

      <!-- 生成中的提示 -->
      <div v-if="generatingOutline" class="generating-hint">
        <el-progress type="circle" :percentage="outlineProgress" />
        <p>AI正在分析热点并生成大纲...</p>
        <pre v-if="outlineStreamPreview" class="streaming-outline">{{ outlineStreamPreview }}</pre>
      </div>
    </div>

    <!-- 步骤3: 查看大纲并生成文章 -->
    <div v-if="currentStep === 2" class="step-content">
      <div v-if="generatedOutline" class="outline-result">
        <el-card class="outline-card">
          <template #header>
            <div class="card-header">
              <span>📑 生成的大纲</span>
              <div>
                <el-button size="small" @click="regenerateOutline" :loading="generatingOutline">
                  <el-icon><Refresh /></el-icon> 重新生成
                </el-button>
              </div>
            </div>
          </template>

          <!-- 标题选项 -->
          <div class="section" v-if="outlineTitles.length > 0">
            <h4>📝 标题选项（请选择一个）</h4>
            <el-radio-group v-model="selectedTitle" class="title-options">
              <el-radio
                v-for="(title, idx) in outlineTitles"
                :key="idx"
                :label="title"
                class="title-radio"
              >
                {{ title }}
              </el-radio>
            </el-radio-group>
          </div>

          <!-- 文章角度 -->
          <div class="section" v-if="generatedOutline?.angle">
            <h4>🎯 切入角度</h4>
            <p>{{ generatedOutline.angle }}</p>
          </div>

          <!-- 目标受众 -->
          <div class="section" v-if="generatedOutline?.target_audience">
            <h4>👥 目标受众</h4>
            <p>{{ generatedOutline.target_audience }}</p>
          </div>

          <!-- 导语 -->
          <div class="section" v-if="generatedOutline?.introduction">
            <h4>📖 导语</h4>
            <p>{{ generatedOutline.introduction }}</p>
          </div>

          <!-- 文章结构 -->
          <div class="section" v-if="outlineSections.length > 0">
            <h4>📊 文章结构</h4>
            <div class="structure-list">
              <div
                v-for="(section, idx) in outlineSections"
                :key="idx"
                class="structure-item"
              >
                <div class="section-header">
                  <span class="section-num">{{ idx + 1 }}</span>
                  <span class="section-name">{{ section.section }}</span>
                  <el-tag v-if="section.word_count" size="small">{{ section.word_count }}字</el-tag>
                </div>
                <ul class="key-points" v-if="section.key_points?.length > 0">
                  <li v-for="(point, pidx) in section.key_points" :key="pidx">{{ point }}</li>
                </ul>
                <p v-if="section.writing_tips" class="writing-tips">
                  💡 {{ section.writing_tips }}
                </p>
              </div>
            </div>
          </div>

          <!-- 结尾建议 -->
          <div class="section" v-if="generatedOutline?.conclusion">
            <h4>🏁 结尾建议</h4>
            <p>{{ generatedOutline.conclusion }}</p>
          </div>

          <!-- 写作风格 -->
          <div class="section" v-if="generatedOutline?.style">
            <h4>🎨 写作风格</h4>
            <p>{{ generatedOutline.style }}</p>
          </div>

          <!-- 关键词 -->
          <div class="section" v-if="outlineKeywords.length > 0">
            <h4>🔑 关键词</h4>
            <el-tag v-for="keyword in outlineKeywords" :key="keyword" class="keyword-tag">
              {{ keyword }}
            </el-tag>
          </div>

          <!-- 万能兜底：如果上面所有结构化字段都为空，直接渲染原始数据 -->
          <div class="section" v-if="outlineTitles.length === 0 && outlineSections.length === 0 && generatedOutline?._raw">
            <h4>📄 大纲详情</h4>
            <pre class="raw-outline">{{ generatedOutline._raw }}</pre>
          </div>

          <div class="action-buttons">
            <el-button @click="currentStep = 1">上一步</el-button>
            <el-button type="primary" @click="generateArticle" :loading="generatingArticle">
              <el-icon><EditPen /></el-icon> AI生成文章
            </el-button>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 步骤4: 生成文章并保存 -->
    <div v-if="currentStep === 3" class="step-content">
      <div class="article-result">
        <!-- 文章预览 -->
        <el-card class="article-preview-card">
          <template #header>
            <div class="card-header">
              <span>✍️ 生成的文章</span>
              <div>
                <el-button size="small" @click="regenerateArticle" :loading="generatingArticle">
                  <el-icon><Refresh /></el-icon> 重新生成
                </el-button>
              </div>
            </div>
          </template>

          <div v-if="generatingArticle" class="article-generating">
            <el-progress :percentage="articleProgress" :stroke-width="20" striped />
            <p>AI正在根据大纲写作...</p>
            <div class="streaming-content" v-html="renderedArticle"></div>
          </div>

          <div v-else class="article-content">
            <div class="article-body" v-html="renderedArticle"></div>
          </div>
        </el-card>

        <!-- 保存选项 -->
        <el-card v-if="!generatingArticle && generatedArticle" class="save-card">
          <template #header>
            <span>💾 保存到项目</span>
          </template>

          <el-form :model="saveConfig" label-position="top">
            <el-form-item label="选择项目">
              <el-select
                v-model="saveConfig.projectId"
                placeholder="选择要保存的项目"
                style="width: 100%"
                filterable
              >
                <el-option :key="'__new__'" :label="'➕ 新建项目'" :value="-1" />
                <el-option
                  v-for="project in projects"
                  :key="project.id"
                  :label="project.title"
                  :value="project.id"
                />
              </el-select>
            </el-form-item>

            <el-form-item v-if="saveConfig.projectId === -1" label="新项目名称">
              <el-input v-model="newProjectName" placeholder="请输入新项目名称" />
            </el-form-item>

            <el-form-item label="文档标题">
              <el-input v-model="saveConfig.title" placeholder="输入文档标题" />
            </el-form-item>
          </el-form>

          <div class="action-buttons">
            <el-button @click="currentStep = 2">上一步</el-button>
            <el-button type="primary" @click="saveDocument" :loading="saving">
              <el-icon><DocumentChecked /></el-icon> 保存文档
            </el-button>
            <el-button type="success" @click="quickWrite" :loading="quickWriting" v-if="!savedDoc">
              <el-icon><MagicStick /></el-icon> 一键写作（快速生成并保存）
            </el-button>
          </div>

          <!-- 发布到自媒体平台 -->
          <el-divider v-if="savedDoc || generatedArticle">或</el-divider>

          <div v-if="savedDoc || generatedArticle" class="publish-section">
            <el-button type="warning" size="large" @click="showPublishDialog = true">
              <el-icon><Promotion /></el-icon> 一键发布到自媒体平台
            </el-button>
          </div>

          <PublishDialog
            v-model="showPublishDialog"
            :document-id="savedDoc?.id"
            :raw-title="selectedTitle || saveConfig.title"
            :raw-content="generatedArticle"
          />

          <!-- 保存成功提示 -->
          <el-alert
            v-if="savedDoc"
            type="success"
            :closable="false"
            class="success-alert"
          >
            <template #title>
              文档保存成功！
              <el-button type="primary" link @click="goToDocument">
                去编辑
              </el-button>
            </template>
          </el-alert>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh, TrendCharts, MagicStick, EditPen, DocumentChecked, Search, Promotion } from '@element-plus/icons-vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import PublishDialog from '@/components/PublishDialog.vue'
import { useProjectStore } from '@/stores/project'
import { API_BASE_URL } from '@/api'

const router = useRouter()
const projectStore = useProjectStore()

marked.setOptions({
  breaks: false,
  gfm: true,
})

// API 基础 URL
const API_BASE = import.meta.env.VITE_API_URL || API_BASE_URL

// 状态
const currentStep = ref(0)
const loading = ref(false)
const hotTopics = ref<any[]>([])
const searchQuery = ref('')
const selectedTopic = ref<any>(null)
const generatingOutline = ref(false)
const outlineProgress = ref(0)
const outlineStreamText = ref('')
const outlineStreamPreview = computed(() => {
  const text = outlineStreamText.value || ''
  const trimmed = text.trim()
  if (!trimmed) return ''

  const prettifyJsonLike = (input: string) => {
    // 把“JSON 原文”尽量变成可读的分段文本（只用于流式中临时展示）
    return input
      .replace(/([{}[\]])/g, '$1\n')
      .replace(/,\s*(?=")/g, ',\n')
      .replace(/\n{3,}/g, '\n\n')
      .trim()
  }

  // 如果流式内容刚好拼成了一个可解析的 JSON，就尝试“更友好”地抽取关键字段展示。
  const tryFormatHotOutline = (): string | null => {
    if (!trimmed.includes('structure') && !trimmed.includes('title_options') && !trimmed.includes('keywords')) return null
    const first = trimmed.indexOf('{')
    const last = trimmed.lastIndexOf('}')
    if (first < 0 || last <= first) return null

    const candidate = trimmed.slice(first, last + 1)
    if (candidate.length > 20000) return null

    try {
      const obj = JSON.parse(candidate) as any
      const titleOptions = Array.isArray(obj?.title_options) ? obj.title_options : []
      const angle = obj?.angle
      const targetAudience = obj?.target_audience
      const introduction = obj?.introduction
      const conclusion = obj?.conclusion
      const style = obj?.style
      const keywords = Array.isArray(obj?.keywords) ? obj.keywords : []
      const structure = Array.isArray(obj?.structure) ? obj.structure : []

      const lines: string[] = []
      if (titleOptions.length) {
        lines.push(`## 标题选项：${titleOptions.slice(0, 3).join(' / ')}${titleOptions.length > 3 ? ' ...' : ''}`)
      }
      if (angle) lines.push(`> 切入角度：${angle}`)
      if (targetAudience) lines.push(`> 目标受众：${targetAudience}`)
      if (introduction) lines.push(`\n## 导语\n${introduction}`)

      if (structure.length) {
        lines.push('\n## 文章结构')
        structure.slice(0, 8).forEach((s: any, idx: number) => {
          const section = s?.section || s?.name || `段落${idx + 1}`
          lines.push(`\n${idx + 1}. ${section}`)
          const points = Array.isArray(s?.key_points) ? s.key_points : []
          for (const p of points) {
            if (p) lines.push(`- ${p}`)
          }
          if (s?.writing_tips) lines.push(`💡 ${s.writing_tips}`)
        })
        if (structure.length > 8) lines.push('\n（预览：仅显示前 8 段结构要点）')
      }

      if (conclusion) lines.push(`\n## 结尾建议\n${conclusion}`)
      if (style) lines.push(`\n## 写作风格\n${style}`)
      if (keywords.length) lines.push(`\n关键词：${keywords.join('、')}`)

      const rendered = lines.join('\n').replace(/\n{3,}/g, '\n\n').trim()
      return rendered || null
    } catch {
      return null
    }
  }

  return tryFormatHotOutline() ?? prettifyJsonLike(trimmed)
})
const generatedOutline = ref<any>(null)
const selectedTitle = ref('')
const generatingArticle = ref(false)
const articleProgress = ref(0)
const generatedArticle = ref('')
const saving = ref(false)
const quickWriting = ref(false)
const savedDoc = ref<any>(null)
const showPublishDialog = ref(false)

// 配置
const outlineConfig = ref({
  articleType: '深度分析',
  wordCount: 1500,
  style: '专业'
})

const saveConfig = ref({
  projectId: null as number | null,
  title: ''
})
const newProjectName = ref('')

// 计算属性
const projects = computed(() => projectStore.projects)

const filteredTopics = computed(() => {
  if (!searchQuery.value) return hotTopics.value
  const query = searchQuery.value.toLowerCase()
  return hotTopics.value.filter(t => 
    t.title.toLowerCase().includes(query) ||
    t.source.toLowerCase().includes(query)
  )
})

const renderedArticle = computed(() => {
  if (!generatedArticle.value) return ''
  let md = generatedArticle.value.trim()
  // 如果文章没有以标题开头，补上选中的标题
  if (selectedTitle.value && !md.startsWith('#')) {
    md = `# ${selectedTitle.value}\n\n${md}`
  }
  const html = marked(md)
  return DOMPurify.sanitize(html as string)
})

const outlineTitles = computed(() => {
  const o = generatedOutline.value
  if (!o) return []
  const arr = o.title_options || o.titles || []
  return Array.isArray(arr) ? arr : []
})

const outlineSections = computed(() => {
  const o = generatedOutline.value
  if (!o) return []
  return Array.isArray(o.structure) ? o.structure : []
})

const outlineKeywords = computed(() => {
  const o = generatedOutline.value
  if (!o) return []
  return Array.isArray(o.keywords) ? o.keywords : []
})

// 方法
const fetchHotTopics = async () => {
  loading.value = true
  try {
    const response = await fetch(`${API_BASE}/api/hot-topics/list`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    })
    if (!response.ok) throw new Error('获取热点失败')
    const data = await response.json()
    hotTopics.value = data.topics || []
    ElMessage.success('热点数据已更新')
  } catch (error) {
    ElMessage.error('获取热点数据失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const getSourceClass = (source: string) => {
  const map: Record<string, string> = {
    '微博热搜': 'weibo',
    '知乎热榜': 'zhihu',
    '百度热搜': 'baidu',
    '头条热榜': 'toutiao'
  }
  return map[source] || 'default'
}

const formatHeat = (heat: any) => {
  if (typeof heat === 'number') {
    if (heat > 10000) return (heat / 10000).toFixed(1) + '万'
    return heat.toString()
  }
  return heat
}

const selectTopic = (topic: any) => {
  selectedTopic.value = topic
  currentStep.value = 1
  ElMessage.success(`已选择：${topic.title}`)
}

const generateOutline = async () => {
  if (!selectedTopic.value) return
  
  generatingOutline.value = true
  outlineProgress.value = 0
  
  outlineStreamText.value = ''
  
  try {
    const response = await fetch(`${API_BASE}/api/hot-topics/generate-outline/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({
        topic_title: selectedTopic.value.title,
        topic_source: selectedTopic.value.source,
        article_type: outlineConfig.value.articleType,
        word_count: outlineConfig.value.wordCount,
        style: outlineConfig.value.style
      })
    })

    if (!response.ok || !response.body) throw new Error('生成大纲失败')

    const reader = response.body.getReader()
    if (!reader) throw new Error('无法读取响应')

    const decoder = new TextDecoder()
    let sseBuffer = ''
    let done = false
    let receivedOutlineMeta = false

    while (!done) {
      const { done: isDone, value } = await reader.read()
      if (isDone) break

      sseBuffer += decoder.decode(value, { stream: true })
      const lines = sseBuffer.split('\n')
      sseBuffer = lines.pop() || ''

      for (const rawLine of lines) {
        const line = rawLine.trim()
        if (!line.startsWith('data: ')) continue

        const data = line.slice(6).trim()
        if (!data) continue

        if (data === '[DONE]') {
          done = true
          break
        }

        if (data.startsWith('[ERROR]')) {
          throw new Error(data.slice('[ERROR]'.length).trim() || '生成大纲失败')
        }

        if (data.startsWith('[OUTLINE_META]')) {
          const metaStr = data.slice('[OUTLINE_META]'.length).trim()
          const meta = JSON.parse(metaStr) as { outline?: any }
          generatedOutline.value = meta.outline || {}
          selectedTitle.value = (meta.outline?.title_options || [])[0] || selectedTopic.value?.title || ''
          receivedOutlineMeta = true
          continue
        }

        if (!receivedOutlineMeta) {
          // 展示生成过程文本（JSON 原文也可帮助用户确认进度）
          outlineStreamText.value += data
          if (outlineStreamText.value.length > 6000) {
            outlineStreamText.value = outlineStreamText.value.slice(-6000)
          }
          outlineProgress.value = Math.min(outlineProgress.value + 2, 95)
        }
      }
    }

    outlineProgress.value = 100
    currentStep.value = 2
    generatingOutline.value = false
  } catch (error) {
    ElMessage.error('生成大纲失败')
    console.error(error)
    generatingOutline.value = false
  }
}

const regenerateOutline = () => {
  generatedOutline.value = null
  generateOutline()
}

const generateArticle = async () => {
  if (!generatedOutline.value) return
  
  generatingArticle.value = true
  articleProgress.value = 0
  generatedArticle.value = ''
  
  try {
    const response = await fetch(`${API_BASE}/api/hot-topics/generate-article/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({
        outline: generatedOutline.value,
        selected_title: selectedTitle.value
      })
    })
    
    if (!response.ok || !response.body) {
      throw new Error('生成文章失败')
    }

    const reader = response.body?.getReader()
    if (!reader) throw new Error('无法读取响应')

    const decoder = new TextDecoder()
    let sseBuffer = ''
    let done = false
    
    while (!done) {
      const { done: isDone, value } = await reader.read()
      if (isDone) break

      sseBuffer += decoder.decode(value, { stream: true })
      const lines = sseBuffer.split('\n')
      sseBuffer = lines.pop() || ''

      for (const rawLine of lines) {
        const line = rawLine.trim()
        if (!line.startsWith('data: ')) continue

        const data = line.slice(6).trim()
        if (!data) continue

        if (data === '[DONE]') {
          articleProgress.value = 100
          done = true
          break
        }

        if (data.startsWith('[ERROR]')) {
          throw new Error(data.slice('[ERROR]'.length).trim() || '生成文章失败')
        }

        generatedArticle.value += data
        articleProgress.value = Math.min(articleProgress.value + 2, 95)
      }
    }
    
    currentStep.value = 3
    saveConfig.value.title = selectedTitle.value
  } catch (error) {
    ElMessage.error('生成文章失败')
    console.error(error)
  } finally {
    generatingArticle.value = false
  }
}

const regenerateArticle = () => {
  generatedArticle.value = ''
  generateArticle()
}

const saveDocument = async () => {
  if (!saveConfig.value.projectId || !saveConfig.value.title) {
    ElMessage.warning('请选择项目并输入文档标题')
    return
  }

  if (saveConfig.value.projectId === -1) {
    if (!newProjectName.value.trim()) {
      ElMessage.warning('请输入新项目名称')
      return
    }
    saving.value = true
    try {
      const project = await projectStore.createProject({ title: newProjectName.value.trim() } as any)
      saveConfig.value.projectId = project.id
      newProjectName.value = ''
    } catch (e) {
      ElMessage.error('创建项目失败')
      saving.value = false
      return
    }
  }

  saving.value = true
  try {
    const response = await fetch(`${API_BASE}/api/hot-topics/create-document`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({
        project_id: saveConfig.value.projectId,
        title: saveConfig.value.title,
        content: generatedArticle.value,
        outline_data: generatedOutline.value
      })
    })
    
    if (!response.ok) throw new Error('保存失败')
    const data = await response.json()
    
    savedDoc.value = data.document
    ElMessage.success('文档保存成功')
  } catch (error) {
    ElMessage.error('保存文档失败')
    console.error(error)
  } finally {
    saving.value = false
  }
}

const quickWrite = async () => {
  if (!saveConfig.value.projectId) {
    ElMessage.warning('请选择要保存的项目')
    return
  }

  if (saveConfig.value.projectId === -1) {
    if (!newProjectName.value.trim()) {
      ElMessage.warning('请输入新项目名称')
      return
    }
    quickWriting.value = true
    try {
      const project = await projectStore.createProject({ title: newProjectName.value.trim() } as any)
      saveConfig.value.projectId = project.id
      newProjectName.value = ''
    } catch (e) {
      ElMessage.error('创建项目失败')
      quickWriting.value = false
      return
    }
  }

  quickWriting.value = true
  try {
    const response = await fetch(`${API_BASE}/api/hot-topics/quick-write`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({
        topic_title: selectedTopic.value.title,
        topic_source: selectedTopic.value.source,
        article_type: outlineConfig.value.articleType,
        word_count: outlineConfig.value.wordCount,
        style: outlineConfig.value.style,
        project_id: saveConfig.value.projectId
      })
    })
    
    if (!response.ok) throw new Error('一键写作失败')
    const data = await response.json()
    
    generatedOutline.value = data.outline || {}
    generatedArticle.value = ((data.article || '').toString().trimEnd() + '\n')
    savedDoc.value = data.document
    selectedTitle.value = (data.outline?.title_options || [])[0] || ''
    saveConfig.value.title = selectedTitle.value
    
    ElMessage.success('文章已生成并保存')
  } catch (error) {
    ElMessage.error('一键写作失败')
    console.error(error)
  } finally {
    quickWriting.value = false
  }
}

const goToDocument = () => {
  if (savedDoc.value) {
    router.push(`/editor/${savedDoc.value.id}`)
  }
}

// 监听
watch(() => generatedOutline.value, (outline) => {
  if (outline?.title_options?.length > 0) {
    selectedTitle.value = outline.title_options[0]
  }
})

// 初始化
onMounted(() => {
  fetchHotTopics()
  projectStore.fetchProjects()
})
</script>

<style scoped lang="scss">
.hot-topics-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.page-header {
  text-align: center;
  margin-bottom: 30px;

  h1 {
    font-size: 28px;
    margin-bottom: 8px;
  }

  .subtitle {
    color: #666;
    font-size: 16px;
  }
}

.steps {
  margin-bottom: 40px;
}

.step-content {
  min-height: 400px;
}

.empty-hint {
  margin-top: 8px;
  color: #888;
  font-size: 13px;
}

.outline-fallback {
  margin-top: 12px;
  padding: 12px;
  border: 1px dashed #ddd;
  border-radius: 8px;
  background: #fafafa;
}

.fallback-block {
  margin-bottom: 10px;
}

.fallback-block h5 {
  margin: 0 0 6px 0;
  font-size: 14px;
}

.raw-outline {
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 500px;
  overflow-y: auto;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.loading-container {
  padding: 40px;
}

.empty-state {
  padding: 60px 0;
}

.topics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.topic-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.3s;

  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    transform: translateY(-2px);
    border-color: #409eff;
  }
}

.topic-header {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.topic-source {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;

  &.weibo {
    background: #ff8200;
    color: white;
  }

  &.zhihu {
    background: #0066ff;
    color: white;
  }

  &.baidu {
    background: #2932e1;
    color: white;
  }

  &.toutiao {
    background: #ed4040;
    color: white;
  }

  &.default {
    background: #909399;
    color: white;
  }
}

.topic-category {
  font-size: 12px;
  padding: 2px 8px;
  background: #f4f4f5;
  color: #606266;
  border-radius: 4px;
}

.topic-title {
  font-size: 16px;
  font-weight: 600;
  line-height: 1.5;
  margin-bottom: 12px;
  color: #303133;
}

.topic-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.topic-heat {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #f56c6c;
  font-size: 14px;
}

.topic-excerpt {
  margin-top: 12px;
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.config-card, .outline-card, .article-preview-card, .save-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.slider-value {
  color: #409eff;
  font-weight: 600;
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #e4e7ed;
}

.generating-hint {
  text-align: center;
  padding: 60px;

  p {
    margin-top: 20px;
    color: #666;
  }
}

.streaming-outline {
  margin-top: 18px;
  text-align: left;
  width: 100%;
  max-width: 720px;
  margin-left: auto;
  margin-right: auto;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  max-height: 260px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
}

.section {
  margin-bottom: 24px;

  h4 {
    font-size: 15px;
    color: #303133;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #e4e7ed;
  }

  p {
    color: #606266;
    line-height: 1.8;
  }
}

.title-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.title-radio {
  padding: 8px;
  background: #f5f7fa;
  border-radius: 4px;

  &:hover {
    background: #ecf5ff;
  }
}

.structure-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.structure-item {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 8px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.section-num {
  width: 24px;
  height: 24px;
  background: #409eff;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
}

.section-name {
  font-weight: 600;
  color: #303133;
  flex: 1;
}

.key-points {
  margin: 0;
  padding-left: 20px;
  color: #606266;

  li {
    margin-bottom: 6px;
    line-height: 1.6;
  }
}

.writing-tips {
  margin-top: 12px;
  padding: 8px 12px;
  background: #fdf6ec;
  border-radius: 4px;
  font-size: 13px;
  color: #e6a23c;
}

.keyword-tag {
  margin-right: 8px;
  margin-bottom: 8px;
}

.article-generating {
  text-align: center;
  padding: 20px;

  p {
    margin: 16px 0;
    color: #666;
  }
}

.streaming-content,
.article-body {
  text-align: left;
  padding: 20px;
  background: #fafafa;
  border-radius: 8px;
  min-height: 200px;
  max-height: 600px;
  overflow-y: auto;
  margin-top: 16px;
  line-height: 1.9;
  font-size: 15px;
  color: #303133;

  :deep(h1) {
    font-size: 24px;
    font-weight: 700;
    text-align: center;
    margin: 0 0 24px;
    padding-bottom: 12px;
    border-bottom: 2px solid #409eff;
  }

  :deep(h1 ~ h1) {
    font-size: 20px;
    text-align: left;
    margin: 28px 0 14px;
    padding-bottom: 8px;
    border-bottom: 1px solid #ebeef5;
  }

  :deep(h2) {
    font-size: 19px;
    font-weight: 600;
    margin: 24px 0 12px;
  }

  :deep(h3) {
    font-size: 17px;
    font-weight: 600;
    margin: 20px 0 10px;
  }

  :deep(p) {
    margin-bottom: 14px;
    text-indent: 2em;
  }

  :deep(blockquote) {
    border-left: 4px solid #409eff;
    padding: 10px 16px;
    margin: 16px 0;
    color: #606266;
    background: #f0f5ff;
    border-radius: 0 6px 6px 0;
  }

  :deep(ul), :deep(ol) {
    padding-left: 2em;
    margin-bottom: 14px;
  }

  :deep(li) {
    margin-bottom: 6px;
  }

  :deep(strong) {
    color: #303133;
  }

  :deep(hr) {
    border: none;
    border-top: 1px solid #ebeef5;
    margin: 20px 0;
  }

  :deep(code) {
    background: #f0f2f5;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.9em;
  }
}

.article-content {
  .article-title {
    font-size: 24px;
    font-weight: 700;
    text-align: center;
    margin-bottom: 30px;
    color: #303133;
  }
}

.success-alert {
  margin-top: 20px;
}

.publish-section {
  margin-top: 16px;
  text-align: center;
}
</style>