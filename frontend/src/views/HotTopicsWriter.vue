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
              <el-icon><Fire /></el-icon> {{ formatHeat(topic.heat) }}
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
          <div class="section">
            <h4>📝 标题选项（请选择一个）</h4>
            <el-radio-group v-model="selectedTitle" class="title-options">
              <el-radio
                v-for="(title, idx) in generatedOutline.title_options"
                :key="idx"
                :label="title"
                class="title-radio"
              >
                {{ title }}
              </el-radio>
            </el-radio-group>
          </div>

          <!-- 文章角度 -->
          <div class="section">
            <h4>🎯 切入角度</h4>
            <p>{{ generatedOutline.angle }}</p>
          </div>

          <!-- 目标受众 -->
          <div class="section">
            <h4>👥 目标受众</h4>
            <p>{{ generatedOutline.target_audience }}</p>
          </div>

          <!-- 文章结构 -->
          <div class="section">
            <h4>📊 文章结构</h4>
            <div class="structure-list">
              <div
                v-for="(section, idx) in generatedOutline.structure"
                :key="idx"
                class="structure-item"
              >
                <div class="section-header">
                  <span class="section-num">{{ idx + 1 }}</span>
                  <span class="section-name">{{ section.section }}</span>
                  <el-tag size="small">{{ section.word_count }}字</el-tag>
                </div>
                <ul class="key-points">
                  <li v-for="(point, pidx) in section.key_points" :key="pidx">{{ point }}</li>
                </ul>
                <p v-if="section.writing_tips" class="writing-tips">
                  💡 {{ section.writing_tips }}
                </p>
              </div>
            </div>
          </div>

          <!-- 关键词 -->
          <div class="section">
            <h4>🔑 关键词</h4>
            <el-tag v-for="keyword in generatedOutline.keywords" :key="keyword" class="keyword-tag">
              {{ keyword }}
            </el-tag>
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
            <h1 class="article-title">{{ selectedTitle }}</h1>
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
                <el-option
                  v-for="project in projects"
                  :key="project.id"
                  :label="project.title"
                  :value="project.id"
                />
              </el-select>
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

          <!-- 发布到公众号 -->
          <el-divider v-if="savedDoc">或</el-divider>
          
          <div v-if="savedDoc" class="publish-section">
            <h4>📢 发布到公众号</h4>
            <el-form :model="publishConfig" label-position="top">
              <el-form-item label="作者">
                <el-input v-model="publishConfig.author" placeholder="作者名称" />
              </el-form-item>
              <el-form-item label="摘要">
                <el-input 
                  v-model="publishConfig.digest" 
                  type="textarea" 
                  :rows="2"
                  placeholder="文章摘要（不填则自动提取）" 
                />
              </el-form-item>
              <el-form-item>
                <el-checkbox v-model="publishConfig.needOpenComment">开启评论</el-checkbox>
                <el-checkbox v-model="publishConfig.onlyFansCanComment">仅粉丝可评论</el-checkbox>
                <el-checkbox v-model="publishConfig.publishNow">立即发布（否则保存为草稿）</el-checkbox>
              </el-form-item>
            </el-form>
            
            <div class="publish-buttons">
              <el-button type="warning" @click="publishToWechat" :loading="publishing" size="large">
                <el-icon><Promotion /></el-icon> 发布到公众号
              </el-button>
              <el-button @click="publishToWechatMock" :loading="publishing" size="large">
                🧪 模拟发布（测试）
              </el-button>
            </div>
          </div>

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
import { Refresh, Fire, MagicStick, EditPen, DocumentChecked, Search, Promotion } from '@element-plus/icons-vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { useProjectStore } from '@/stores/project'

const router = useRouter()
const projectStore = useProjectStore()

// 状态
const currentStep = ref(0)
const loading = ref(false)
const hotTopics = ref<any[]>([])
const searchQuery = ref('')
const selectedTopic = ref<any>(null)
const generatingOutline = ref(false)
const outlineProgress = ref(0)
const generatedOutline = ref<any>(null)
const selectedTitle = ref('')
const generatingArticle = ref(false)
const articleProgress = ref(0)
const generatedArticle = ref('')
const saving = ref(false)
const quickWriting = ref(false)
const savedDoc = ref<any>(null)
const publishing = ref(false)

// 发布配置
const publishConfig = ref({
  author: '',
  digest: '',
  needOpenComment: true,
  onlyFansCanComment: false,
  publishNow: false
})

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
  const html = marked(generatedArticle.value)
  return DOMPurify.sanitize(html)
})

// 方法
const fetchHotTopics = async () => {
  loading.value = true
  try {
    const response = await fetch('/api/hot-topics/list', {
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
  
  // 模拟进度
  const progressInterval = setInterval(() => {
    if (outlineProgress.value < 90) {
      outlineProgress.value += 10
    }
  }, 500)
  
  try {
    const response = await fetch('/api/hot-topics/generate-outline', {
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
    
    clearInterval(progressInterval)
    outlineProgress.value = 100
    
    if (!response.ok) throw new Error('生成大纲失败')
    const data = await response.json()
    
    generatedOutline.value = data.outline
    selectedTitle.value = data.outline.title_options?.[0] || ''
    
    setTimeout(() => {
      currentStep.value = 2
      generatingOutline.value = false
    }, 500)
  } catch (error) {
    clearInterval(progressInterval)
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
    const response = await fetch('/api/hot-topics/generate-article/stream', {
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
    
    const reader = response.body?.getReader()
    if (!reader) throw new Error('无法读取响应')
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      const text = new TextDecoder().decode(value)
      const lines = text.split('\n')
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') {
            articleProgress.value = 100
          } else {
            generatedArticle.value += data
            articleProgress.value = Math.min(articleProgress.value + 2, 95)
          }
        }
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
  
  saving.value = true
  try {
    const response = await fetch('/api/hot-topics/create-document', {
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
  
  quickWriting.value = true
  try {
    const response = await fetch('/api/hot-topics/quick-write', {
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
    
    generatedOutline.value = data.outline
    generatedArticle.value = data.article
    savedDoc.value = data.document
    selectedTitle.value = data.outline.title_options?.[0] || ''
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

// 发布到公众号
const publishToWechat = async () => {
  if (!savedDoc.value) {
    ElMessage.warning('请先保存文档')
    return
  }
  
  publishing.value = true
  try {
    const response = await fetch('/api/publish/wechat/draft', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({
        document_id: savedDoc.value.id,
        title: saveConfig.value.title,
        author: publishConfig.value.author,
        digest: publishConfig.value.digest,
        need_open_comment: publishConfig.value.needOpenComment,
        only_fans_can_comment: publishConfig.value.onlyFansCanComment,
        publish_now: publishConfig.value.publishNow,
        mock_mode: false
      })
    })
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || '发布失败')
    }
    
    const data = await response.json()
    
    if (data.success) {
      if (publishConfig.value.publishNow) {
        ElMessage.success('文章已提交发布！')
      } else {
        ElMessage.success('草稿已创建！请在公众号后台查看')
      }
    } else {
      ElMessage.error(data.draft?.error || '发布失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '发布失败')
    console.error(error)
  } finally {
    publishing.value = false
  }
}

// 模拟发布到公众号（测试用）
const publishToWechatMock = async () => {
  if (!savedDoc.value) {
    ElMessage.warning('请先保存文档')
    return
  }
  
  publishing.value = true
  try {
    const response = await fetch('/api/publish/wechat/draft', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({
        document_id: savedDoc.value.id,
        title: saveConfig.value.title,
        author: publishConfig.value.author || '测试作者',
        digest: publishConfig.value.digest,
        need_open_comment: publishConfig.value.needOpenComment,
        only_fans_can_comment: publishConfig.value.onlyFansCanComment,
        publish_now: publishConfig.value.publishNow,
        mock_mode: true
      })
    })
    
    if (!response.ok) throw new Error('模拟发布失败')
    const data = await response.json()
    
    if (data.success) {
      ElMessage.success(`✅ 模拟发布成功！\nMedia ID: ${data.draft.media_id}`)
      console.log('发布结果:', data)
    } else {
      ElMessage.error(data.draft?.error || '模拟发布失败')
    }
  } catch (error) {
    ElMessage.error('模拟发布失败')
    console.error(error)
  } finally {
    publishing.value = false
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

.streaming-content {
  text-align: left;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
  min-height: 200px;
  max-height: 400px;
  overflow-y: auto;
  margin-top: 16px;
  line-height: 1.8;
}

.article-content {
  .article-title {
    font-size: 24px;
    font-weight: 700;
    text-align: center;
    margin-bottom: 30px;
    color: #303133;
  }

  .article-body {
    line-height: 2;
    color: #303133;

    :deep(h1), :deep(h2), :deep(h3) {
      margin: 24px 0 16px;
      color: #303133;
    }

    :deep(p) {
      margin-bottom: 16px;
      text-indent: 2em;
    }

    :deep(blockquote) {
      border-left: 4px solid #409eff;
      padding-left: 16px;
      margin: 16px 0;
      color: #606266;
    }
  }
}

.success-alert {
  margin-top: 20px;
}

// 发布区域样式
.publish-section {
  margin-top: 24px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;

  h4 {
    margin: 0 0 16px 0;
    color: #303133;
    font-size: 16px;
  }

  .publish-buttons {
    display: flex;
    gap: 12px;
    margin-top: 16px;
  }
}
</style>