<template>
  <div class="story-generator-page">
    <div class="page-header">
      <h1>✨ AI 故事生成器</h1>
      <p class="subtitle">输入一个主题，AI 自动生成大纲、角色、情节等完整设定</p>
    </div>

    <!-- 输入区域 -->
    <el-card class="input-card" v-if="!generatedStory">
      <template #header>
        <span>📝 输入主题</span>
      </template>

      <el-form :model="form" label-position="top">
        <el-form-item label="故事主题/核心概念">
          <el-input
            v-model="form.theme"
            type="textarea"
            :rows="3"
            placeholder="例如：一个关于时间旅行的爱情故事，主角试图改变过去的遗憾..."
          />
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="故事类型">
              <el-select v-model="form.genre" style="width: 100%" placeholder="选择类型">
                <el-option label="科幻" value="科幻" />
                <el-option label="悬疑推理" value="悬疑推理" />
                <el-option label="爱情" value="爱情" />
                <el-option label="奇幻" value="奇幻" />
                <el-option label="历史" value="历史" />
                <el-option label="武侠" value="武侠" />
                <el-option label="恐怖惊悚" value="恐怖惊悚" />
                <el-option label="现实主义" value="现实主义" />
                <el-option label="冒险" value="冒险" />
                <el-option label="其他" value="其他" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="目标字数（设定参考）">
              <el-slider v-model="form.wordCount" :min="3000" :max="200000" :step="1000" show-stops />
              <span class="word-count-display">{{ formatWordCount(form.wordCount) }}</span>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="章节数量（幕数）">
              <el-input-number
                v-model="form.chapterCount"
                :min="1"
                :max="100"
                :step="1"
                controls-position="right"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item>
              <template #label>
                <span>预估每章字数</span>
              </template>
              <span class="word-count-display" style="line-height: 32px">
                {{ form.chapterCount > 0 ? formatWordCount(Math.round(form.wordCount / form.chapterCount)) : '-' }}
              </span>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="额外要求（可选）">
          <el-input
            v-model="form.additional"
            type="textarea"
            :rows="2"
            placeholder="例如：希望有反转结局，主角要有成长弧线，包含悬疑元素..."
          />
        </el-form-item>

        <div class="action-buttons">
          <el-button class="btn-primary btn-lg" @click="generateStory" :loading="generating">
            <el-icon><MagicStick /></el-icon>
            生成故事设定
          </el-button>
        </div>
      </el-form>

      <!-- 生成进度 -->
      <div v-if="generating" class="generating-status">
        <el-progress :percentage="progress" :stroke-width="20" striped />
        <p>{{ statusText }}</p>
      </div>

      <!-- 实时生成预览 -->
      <div class="preview-container" :class="{ 'hidden': !generating }">
        <div class="preview-header">
          <el-icon><Document /></el-icon>
          <span>实时生成预览</span>
        </div>
        <div class="preview-content" v-html="previewContent"></div>
      </div>
    </el-card>

    <!-- 生成结果 -->
    <div v-else class="result-container">
      <!-- 标题选项 -->
      <el-card class="result-card">
        <template #header>
          <div class="card-header">
            <span>📚 生成的故事设定</span>
            <div>
              <el-button @click="regenerate" :loading="generating">
                <el-icon><Refresh /></el-icon> 重新生成
              </el-button>
              <el-button type="danger" @click="reset">
                <el-icon><Delete /></el-icon> 清空
              </el-button>
            </div>
          </div>
        </template>

        <!-- 标题选择 -->
        <div class="section">
          <h3>🎯 选择标题</h3>
          <el-radio-group v-model="selectedTitle" class="title-options">
            <el-radio
              v-for="(title, idx) in generatedStory.title_options"
              :key="idx"
              :label="title"
              class="title-radio"
            >
              {{ title }}
            </el-radio>
          </el-radio-group>
        </div>

        <!-- 故事信息 -->
        <div class="section story-info">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="类型">{{ generatedStory.genre }}</el-descriptions-item>
            <el-descriptions-item label="核心主题">{{ generatedStory.core_theme }}</el-descriptions-item>
            <el-descriptions-item label="目标字数" :span="2">{{ formatWordCount(generatedStory.target_word_count) }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 大纲 -->
        <div class="section">
          <h3>📖 故事大纲</h3>
          <div class="outline-editor">
            <div 
              v-for="(act, idx) in generatedStory.outline" 
              :key="idx" 
              class="outline-item"
            >
              <div class="outline-item-header">
                <el-icon><Document /></el-icon>
                <span class="outline-act">{{ act.act }}</span>
              </div>
              <el-input
                v-model="act.title"
                type="textarea"
                :rows="2"
                placeholder="大纲标题"
                class="outline-title-input"
              />
              <el-input
                v-model="act.content"
                type="textarea"
                :rows="4"
                placeholder="大纲内容"
                class="outline-content-input"
              />
              <div class="outline-footer">
                <el-input
                  v-model="act.word_count_estimate"
                  placeholder="预估字数"
                  class="outline-word-count"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- 角色设定 -->
        <div class="section">
          <h3>👥 角色设定</h3>
          <div class="characters-grid">
            <el-card
              v-for="(char, idx) in generatedStory.characters"
              :key="idx"
              class="character-card"
              :class="getCharacterClass(char.role)"
            >
              <template #header>
                <div class="character-header">
                  <span class="character-name">{{ char.name }}</span>
                  <el-tag size="small" :type="getRoleTagType(char.role)">{{ char.role }}</el-tag>
                </div>
              </template>
              <div class="character-info">
                <p v-if="char.age"><strong>年龄：</strong>{{ char.age }}</p>
                <p v-if="char.appearance"><strong>外貌：</strong>{{ char.appearance }}</p>
                <p v-if="char.personality"><strong>性格：</strong>{{ formatPersonality(char.personality) }}</p>
                <p v-if="char.background"><strong>背景：</strong>{{ char.background }}</p>
                <p v-if="char.goals"><strong>目标：</strong>{{ char.goals }}</p>
                <p v-if="char.internal_conflict"><strong>内心冲突：</strong>{{ char.internal_conflict }}</p>
              </div>
            </el-card>
          </div>
        </div>

        <!-- 关键情节点 -->
        <div class="section" v-if="generatedStory.plot_points?.length">
          <h3>🔥 关键情节点</h3>
          <el-collapse>
            <el-collapse-item
              v-for="(point, idx) in generatedStory.plot_points"
              :key="idx"
              :title="point.point || `情节点 ${idx + 1}`"
            >
              <p><strong>位置：</strong>{{ point.position }}</p>
              <p><strong>意义：</strong>{{ point.significance }}</p>
            </el-collapse-item>
          </el-collapse>
        </div>

        <!-- 世界观 -->
        <div class="section" v-if="generatedStory.world_building">
          <h3>🌍 世界观设定</h3>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="时代背景">
              {{ generatedStory.world_building.time_period || '未设定' }}
            </el-descriptions-item>
            <el-descriptions-item label="主要地点">
              {{ generatedStory.world_building.location || '未设定' }}
            </el-descriptions-item>
            <el-descriptions-item label="世界规则">
              {{ generatedStory.world_building.rules || '未设定' }}
            </el-descriptions-item>
            <el-descriptions-item label="氛围基调">
              {{ generatedStory.world_building.atmosphere || '未设定' }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 写作风格 -->
        <div class="section" v-if="generatedStory.writing_style">
          <h3>✍️ 写作风格建议</h3>
          <el-alert type="info" :closable="false">
            <p><strong>语气：</strong>{{ generatedStory.writing_style.tone }}</p>
            <p><strong>视角：</strong>{{ generatedStory.writing_style.pov }}</p>
            <p><strong>节奏：</strong>{{ generatedStory.writing_style.pacing }}</p>
            <p v-if="generatedStory.writing_style.techniques?.length">
              <strong>推荐技巧：</strong>{{ generatedStory.writing_style.techniques.join('、') }}
            </p>
          </el-alert>
        </div>

        <!-- 应用到项目 -->
        <el-divider />
        
        <div class="apply-section">
          <h3>💾 应用到项目</h3>
          <p class="hint">将生成的设定保存到项目中，AI 写作时会自动参考这些设定</p>
          
          <el-form :model="applyForm" label-position="top">
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="选择现有项目">
                  <el-select v-model="applyForm.projectId" style="width: 100%" clearable>
                    <el-option
                      v-for="project in projects"
                      :key="project.id"
                      :label="project.name"
                      :value="project.id"
                    />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="或创建新项目">
                  <el-input v-model="applyForm.newProjectName" placeholder="输入新项目名称" />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>

          <div class="action-buttons">
            <el-button class="btn-primary" @click="confirmAndCreateProject" :loading="applying || quickCreating">
              <el-icon><Check /></el-icon>
              确认并创建项目
            </el-button>
            <el-button type="primary" @click="applyToProject" :loading="applying">
              <el-icon><FolderChecked /></el-icon>
              保存到项目
            </el-button>
            <el-button type="success" @click="quickCreateProject" :loading="quickCreating">
              <el-icon><Plus /></el-icon>
              一键创建项目
            </el-button>
          </div>

        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { MagicStick, Refresh, Delete, FolderChecked, Plus, Check, Document } from '@element-plus/icons-vue'
import { useProjectStore } from '@/stores/project'
import { useAuthStore } from '@/stores/auth'
import { API_BASE_URL } from '@/api'

const router = useRouter()
const projectStore = useProjectStore()
const authStore = useAuthStore()

// API 基础 URL
const API_BASE = import.meta.env.VITE_API_URL || API_BASE_URL

// 获取当前 token（优先 store，避免 store 未同步时漏带）
const getAuthToken = () => authStore.token || localStorage.getItem('token')

// 状态
const generating = ref(false)
const progress = ref(0)
const statusText = ref('正在生成...')
const generatedStory = ref<any>(null)
const selectedTitle = ref('')
const applying = ref(false)
const quickCreating = ref(false)
const previewContent = ref('')

// 表单
const form = ref({
  theme: '',
  genre: '',
  wordCount: 10000,
  chapterCount: 5,
  additional: ''
})

const applyForm = ref({
  projectId: null as number | null,
  newProjectName: ''
})


// 计算属性
const projects = computed(() => projectStore.projects)

// 方法
const formatWordCount = (count: number) => {
  if (count >= 10000) return (count / 10000).toFixed(1) + '万字'
  return count + '字'
}

const generateStory = async () => {
  if (!form.value.theme.trim()) {
    ElMessage.warning('请输入故事主题')
    return
  }
  const token = getAuthToken()
  if (!token) {
    ElMessage.warning('请先登录后再使用故事生成')
    router.push('/login')
    return
  }

  generating.value = true
  progress.value = 0
  statusText.value = '正在构思故事框架...'
  previewContent.value = ''

  // 模拟进度
  const progressInterval = setInterval(() => {
    if (progress.value < 90) {
      progress.value += Math.random() * 15
      if (progress.value > 30 && progress.value < 50) {
        statusText.value = '正在设计角色...'
      } else if (progress.value > 50 && progress.value < 70) {
        statusText.value = '正在构建情节...'
      } else if (progress.value > 70) {
        statusText.value = '正在完善世界观...'
      }
    }
  }, 800)

  try {
    const response = await fetch(`${API_BASE}/api/ai-story-generator/generate/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        theme: form.value.theme,
        genre: form.value.genre || undefined,
        word_count: form.value.wordCount,
        chapter_count: form.value.chapterCount,
        additional_requirements: form.value.additional || undefined
      })
    })

    if (!response.ok) {
      if (response.status === 401) {
        // 仅提示并跳转，不主动清除 token，避免因代理未转发 header 等原因误登出
        ElMessage.warning('登录已过期或未生效，请重新登录')
        router.push('/login')
        throw new Error('请重新登录')
      }
      let detail = '生成失败'
      try {
        const error = await response.json()
        detail = error.detail ?? detail
      } catch {
        detail = response.statusText || detail
      }
      throw new Error(detail)
    }

    // 处理流式响应 (SSE 格式)：按事件缓冲解析，避免多行/分包导致解析失败
    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    let sseBuffer = ''
    let chunksReceived = 0
    let isDone = false

    const processEventData = (data: string) => {
      if (data === '[DONE]') {
        isDone = true
        return
      }
      try {
        const parsed = JSON.parse(data)
        // 最终结果：生成完成
        if (parsed.success !== undefined) {
          if (parsed.success) {
            generatedStory.value = parsed.data
            selectedTitle.value = parsed.data?.title_options?.[0] || ''
            progress.value = 100
            statusText.value = '生成完成！'
            ElMessage.success('故事设定生成成功！')
            isDone = true
          } else {
            throw new Error(parsed.error || '生成失败')
          }
          return
        }
        // 流式内容块：更新实时预览
        if (parsed.chunk != null) {
          const content = String(parsed.chunk)
          chunksReceived++
          previewContent.value += content.replace(/\n/g, '<br>').replace(/</g, '&lt;').replace(/>/g, '&gt;')
          const estimatedProgress = Math.min(95, 10 + chunksReceived * 5)
          progress.value = estimatedProgress
          if (chunksReceived < 3) statusText.value = '正在构思故事框架...'
          else if (chunksReceived < 6) statusText.value = '正在设计角色...'
          else if (chunksReceived < 9) statusText.value = '正在构建情节...'
          else statusText.value = '正在完善世界观...'
        }
      } catch (e) {
        // 非 JSON 时当作纯文本追加到预览
        chunksReceived++
        const safe = (data || '').replace(/\n/g, '<br>').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        previewContent.value += safe
        progress.value = Math.min(95, 10 + chunksReceived * 5)
      }
    }

    if (reader) {
      while (true) {
        const { done, value } = await reader.read()
        if (done || isDone) break

        sseBuffer += decoder.decode(value, { stream: true })
        const events = sseBuffer.split('\n\n')
        sseBuffer = events.pop() ?? ''

        for (const event of events) {
          const line = event.trim()
          if (line.startsWith('data: ')) {
            const payload = line.slice(6).trim()
            processEventData(payload)
            if (isDone) break
          }
        }
        if (isDone) break
      }
    }

    clearInterval(progressInterval)
  } catch (error: any) {
    clearInterval(progressInterval)
    ElMessage.error(error.message || '生成失败，请重试')
    console.error(error)
  } finally {
    generating.value = false
  }
}

const regenerate = () => {
  generateStory()
}

const reset = () => {
  generatedStory.value = null
  selectedTitle.value = ''
  previewContent.value = ''
  form.value.theme = ''
  form.value.additional = ''
}

const getTimelineType = (idx: number) => {
  const types = ['primary', 'success', 'warning', 'danger']
  return types[idx % types.length]
}

const getTimelineIcon = (idx: number) => {
  if (idx === 0) return 'Flag'
  if (idx === (generatedStory.value?.outline?.length - 1)) return 'Finished'
  return 'CircleCheck'
}

const getCharacterClass = (role: string) => {
  if (role?.includes('主角')) return 'protagonist'
  if (role?.includes('反派')) return 'antagonist'
  return 'supporting'
}

const getRoleTagType = (role: string) => {
  if (role?.includes('主角')) return 'success'
  if (role?.includes('反派')) return 'danger'
  return 'info'
}

const formatPersonality = (personality: any) => {
  if (typeof personality === 'string') return personality
  if (personality?.strengths && personality?.weaknesses) {
    return `优点：${personality.strengths.join('、')}；缺点：${personality.weaknesses.join('、')}`
  }
  return JSON.stringify(personality)
}

const confirmAndCreateProject = async () => {
  try {
    // 先确认修改
    await ElMessageBox.confirm(
      '确认要使用当前修改的大纲创建新项目吗？',
      '确认创建',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    // 创建新项目
    quickCreating.value = true
    const payload: Record<string, any> = {
      theme: form.value.theme,
      project_name: applyForm.value.newProjectName || selectedTitle.value,
      genre: form.value.genre,
      word_count: form.value.wordCount
    }
    if (generatedStory.value) payload.story_data = generatedStory.value

    const response = await fetch(`${API_BASE}/api/ai-story-generator/quick-create-project`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getAuthToken()}`
      },
      body: JSON.stringify(payload)
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || '创建失败')
    }

    const data = await response.json()
    
    if (data.success) {
      ElMessage.success('项目创建成功！')
      router.push(`/project/${data.project.id}`)
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '创建失败')
      console.error(error)
    }
  } finally {
    quickCreating.value = false
  }
}

const applyToProject = async () => {
  if (!applyForm.value.projectId) {
    ElMessage.warning('请选择要应用的项目')
    return
  }

  applying.value = true
  try {
    const response = await fetch(`${API_BASE}/api/ai-story-generator/apply-to-project`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getAuthToken()}`
      },
      body: JSON.stringify({
        project_id: applyForm.value.projectId,
        story_data: generatedStory.value
      })
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || '应用失败')
    }

    const data = await response.json()
    
    if (data.success) {
      ElMessage.success('故事设定已应用到项目！')
      router.push(`/project/${applyForm.value.projectId}`)
    }
  } catch (error: any) {
    ElMessage.error(error.message || '应用失败')
    console.error(error)
  } finally {
    applying.value = false
  }
}

const quickCreateProject = async () => {
  quickCreating.value = true
  try {
    const payload: Record<string, any> = {
      theme: form.value.theme,
      project_name: applyForm.value.newProjectName || selectedTitle.value,
      genre: form.value.genre,
      word_count: form.value.wordCount
    }
    // 若已有生成结果则带上，后端不再调 AI，避免长时间等待
    if (generatedStory.value) {
      payload.story_data = generatedStory.value
    }
    const response = await fetch(`${API_BASE}/api/ai-story-generator/quick-create-project`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getAuthToken()}`
      },
      body: JSON.stringify(payload)
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || '创建失败')
    }

    const data = await response.json()
    
    if (data.success) {
      ElMessage.success('项目创建成功！')
      router.push(`/project/${data.project.id}`)
    }
  } catch (error: any) {
    ElMessage.error(error.message || '创建失败')
    console.error(error)
  } finally {
    quickCreating.value = false
  }
}

// 初始化
onMounted(() => {
  projectStore.fetchProjects()
})
</script>

<style scoped lang="scss">
.story-generator-page {
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
}

.page-header {
  text-align: center;
  margin-bottom: 30px;

  h1 {
    font-size: 28px;
    margin-bottom: 8px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .subtitle {
    color: #666;
    font-size: 16px;
  }
}

.input-card {
  margin-bottom: 20px;
}

.word-count-display {
  color: #409eff;
  font-weight: 600;
  font-size: 14px;
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 24px;
}

.generating-status {
  margin-top: 30px;
  text-align: center;

  p {
    margin-top: 16px;
    color: #666;
    font-size: 14px;
  }
}

.preview-container.hidden {
  display: none;
}

.preview-container {
  margin-top: 24px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
  background: #f5f7fa;

  .preview-header {
    padding: 12px 16px;
    background: #fafafa;
    border-bottom: 1px solid #e4e7ed;
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 500;
    color: #606266;
  }

  .preview-content {
    padding: 16px;
    max-height: 400px;
    overflow-y: auto;
    font-size: 14px;
    line-height: 1.8;
    color: #303133;

    h4 {
      margin: 16px 0 8px;
      color: #303133;
      font-size: 16px;
      font-weight: 600;
    }

    p {
      margin: 8px 0;
      color: #606266;
    }

    ul, ol {
      margin: 8px 0;
      padding-left: 24px;

      li {
        margin: 4px 0;
        color: #606266;
      }
    }
  }
}

.result-container {
  animation: fadeIn 0.5s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.result-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section {
  margin-bottom: 30px;

  h3 {
    font-size: 18px;
    color: #303133;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 2px solid #e4e7ed;
  }
}

.title-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.title-radio {
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;
  transition: all 0.3s;

  &:hover {
    background: #ecf5ff;
  }

  :deep(.el-radio__label) {
    font-size: 16px;
    font-weight: 500;
  }
}

.story-info {
  margin-top: 20px;
}

.outline-timeline {
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;

  h4 {
    margin: 0 0 8px 0;
    color: #303133;
  }

  p {
    color: #606266;
    margin-bottom: 8px;
  }
}

.outline-editor {
  .outline-item {
    background: var(--coffee-bg-card);
    border: 1px solid #e4e7ed;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 16px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);

    .outline-item-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
      color: #606266;
      font-weight: 500;

      .outline-act {
        color: #303133;
        font-weight: 600;
      }
    }

    .outline-title-input,
    .outline-content-input {
      margin-bottom: 12px;

      :deep(.el-textarea__inner) {
        font-size: 14px;
        line-height: 1.6;
      }
    }

    .outline-footer {
      display: flex;
      gap: 12px;
      align-items: center;

      .outline-word-count {
        flex: 1;
      }
    }
  }
}

.characters-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.character-card {
  &.protagonist {
    border-left: 4px solid #67c23a;
  }

  &.antagonist {
    border-left: 4px solid #f56c6c;
  }

  &.supporting {
    border-left: 4px solid #909399;
  }
}

.character-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.character-name {
  font-size: 16px;
  font-weight: 600;
}

.character-info {
  p {
    margin-bottom: 8px;
    line-height: 1.6;

    &:last-child {
      margin-bottom: 0;
    }
  }
}

.apply-section {
  .hint {
    color: #909399;
    margin-bottom: 16px;
  }
}

</style>
