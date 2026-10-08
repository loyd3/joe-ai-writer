<template>
  <div class="story-generator-page">
    <header class="page-header">
      <div class="header-text">
        <h1>
          <el-icon class="header-icon"><MagicStick /></el-icon>
          AI 故事生成器
        </h1>
        <p class="subtitle">从一个主题出发，生成大纲、角色、情节与世界观设定</p>
      </div>
      <div v-if="generatedStory" class="header-actions">
        <el-button @click="regenerate" :loading="generating">
          <el-icon><Refresh /></el-icon>
          重新生成
        </el-button>
        <el-button @click="reset">
          <el-icon><Delete /></el-icon>
          返回编辑
        </el-button>
      </div>
    </header>

    <!-- 输入区 -->
    <div v-if="!generatedStory" class="compose-layout">
      <section class="compose-panel">
        <el-form :model="form" label-position="top" class="compose-form">
          <el-form-item label="故事主题">
            <el-input
              v-model="form.theme"
              type="textarea"
              :rows="4"
              :disabled="generating"
              resize="none"
              placeholder="例如：一个关于时间旅行的爱情故事，主角试图改变过去的遗憾……"
            />
          </el-form-item>

          <el-form-item label="故事类型">
            <div class="genre-chips">
              <button
                v-for="g in genres"
                :key="g"
                type="button"
                class="genre-chip"
                :class="{ active: form.genre === g }"
                :disabled="generating"
                @click="form.genre = form.genre === g ? '' : g"
              >
                {{ g }}
              </button>
            </div>
          </el-form-item>

          <div class="stats-grid">
            <el-form-item label="目标字数">
              <el-slider
                v-model="form.wordCount"
                :min="3000"
                :max="200000"
                :step="1000"
                :disabled="generating"
              />
              <div class="stat-value">{{ formatWordCount(form.wordCount) }}</div>
            </el-form-item>
            <el-form-item label="章节 / 幕数">
              <el-input-number
                v-model="form.chapterCount"
                :min="1"
                :max="100"
                :step="1"
                :disabled="generating"
                controls-position="right"
                style="width: 100%"
              />
              <div class="stat-value muted">
                约 {{ form.chapterCount > 0 ? formatWordCount(Math.round(form.wordCount / form.chapterCount)) : '-' }} / 章
              </div>
            </el-form-item>
          </div>

          <el-form-item label="额外要求（可选）">
            <el-input
              v-model="form.additional"
              type="textarea"
              :rows="2"
              :disabled="generating"
              resize="none"
              placeholder="例如：希望有反转结局，主角要有成长弧线……"
            />
          </el-form-item>

          <el-form-item label="文风智能体">
            <StyleAgentPicker v-model="selectedStyleAgentId" :label="''" />
          </el-form-item>

          <div class="compose-actions">
            <el-button
              class="btn-primary btn-lg generate-btn"
              :loading="generating"
              :disabled="!form.theme.trim()"
              @click="generateStory"
            >
              <el-icon v-if="!generating"><MagicStick /></el-icon>
              {{ generating ? '生成中…' : '生成故事设定' }}
            </el-button>
          </div>
        </el-form>
      </section>

      <aside class="side-panel">
        <div v-if="!generating" class="tips-panel">
          <h3>怎么用更好</h3>
          <ul>
            <li>主题写清冲突与人物关系，生成会更贴题</li>
            <li>类型与章节数会约束大纲结构</li>
            <li>文风智能体可让设定贴近你的写作习惯</li>
            <li>生成后可直接改大纲，再一键创建项目</li>
          </ul>
          <div class="tip-examples">
            <span class="tip-label">示例主题</span>
            <button
              v-for="ex in themeExamples"
              :key="ex"
              type="button"
              class="example-chip"
              @click="form.theme = ex"
            >
              {{ ex }}
            </button>
          </div>
        </div>

        <div v-else class="generating-panel">
          <div class="generating-head">
            <span class="pulse-dot" />
            <div>
              <strong>{{ statusText }}</strong>
              <p>AI 正在流式输出，可随时等待完成</p>
            </div>
          </div>
          <el-progress
            :percentage="Math.min(100, Math.round(progress))"
            :stroke-width="10"
            striped
            striped-flow
          />
          <div class="preview-box">
            <div class="preview-label">
              <el-icon><Document /></el-icon>
              实时预览
            </div>
            <div class="preview-content" v-html="previewContent || '等待模型输出…'" />
          </div>
        </div>
      </aside>
    </div>

    <!-- 结果区 -->
    <div v-else class="result-layout">
      <section class="result-hero">
        <div class="meta-row">
          <span v-if="generatedStory.genre" class="meta-pill">{{ generatedStory.genre }}</span>
          <span v-if="generatedStory.target_word_count" class="meta-pill soft">
            {{ formatWordCount(generatedStory.target_word_count) }}
          </span>
          <span v-if="generatedStory.outline?.length" class="meta-pill soft">
            {{ generatedStory.outline.length }} 幕
          </span>
        </div>
        <p v-if="generatedStory.core_theme" class="core-theme">{{ generatedStory.core_theme }}</p>

        <div class="title-picker">
          <h3>选择标题</h3>
          <el-radio-group v-model="selectedTitle" class="title-options">
            <el-radio
              v-for="(title, idx) in generatedStory.title_options"
              :key="idx"
              :value="title"
              class="title-radio"
              border
            >
              {{ title }}
            </el-radio>
          </el-radio-group>
        </div>
      </section>

      <el-tabs v-model="resultTab" class="result-tabs">
        <el-tab-pane label="大纲" name="outline">
          <div class="outline-editor">
            <div
              v-for="(act, idx) in generatedStory.outline"
              :key="idx"
              class="outline-item"
            >
              <div class="outline-item-header">
                <span class="act-index">{{ idx + 1 }}</span>
                <span class="outline-act">{{ act.act || `第 ${idx + 1} 幕` }}</span>
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
        </el-tab-pane>

        <el-tab-pane label="角色" name="characters">
          <div class="characters-grid">
            <article
              v-for="(char, idx) in generatedStory.characters"
              :key="idx"
              class="character-card"
              :class="getCharacterClass(char.role)"
            >
              <header class="character-header">
                <span class="character-name">{{ char.name }}</span>
                <el-tag size="small" :type="getRoleTagType(char.role)">{{ char.role }}</el-tag>
              </header>
              <div class="character-info">
                <p v-if="char.age"><span>年龄</span>{{ char.age }}</p>
                <p v-if="char.appearance"><span>外貌</span>{{ char.appearance }}</p>
                <p v-if="char.personality"><span>性格</span>{{ formatPersonality(char.personality) }}</p>
                <p v-if="char.background"><span>背景</span>{{ char.background }}</p>
                <p v-if="char.goals"><span>目标</span>{{ char.goals }}</p>
                <p v-if="char.internal_conflict"><span>冲突</span>{{ char.internal_conflict }}</p>
              </div>
            </article>
          </div>
        </el-tab-pane>

        <el-tab-pane
          v-if="generatedStory.plot_points?.length"
          label="情节点"
          name="plot"
        >
          <div class="plot-list">
            <div
              v-for="(point, idx) in generatedStory.plot_points"
              :key="idx"
              class="plot-item"
            >
              <div class="plot-index">{{ idx + 1 }}</div>
              <div class="plot-body">
                <h4>{{ point.point || `情节点 ${idx + 1}` }}</h4>
                <p v-if="point.position"><em>位置</em>{{ point.position }}</p>
                <p v-if="point.significance"><em>意义</em>{{ point.significance }}</p>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane
          v-if="generatedStory.world_building"
          label="世界观"
          name="world"
        >
          <div class="world-grid">
            <div class="world-item">
              <h4>时代背景</h4>
              <p>{{ generatedStory.world_building.time_period || '未设定' }}</p>
            </div>
            <div class="world-item">
              <h4>主要地点</h4>
              <p>{{ generatedStory.world_building.location || '未设定' }}</p>
            </div>
            <div class="world-item span-2">
              <h4>世界规则</h4>
              <p>{{ generatedStory.world_building.rules || '未设定' }}</p>
            </div>
            <div class="world-item span-2">
              <h4>氛围基调</h4>
              <p>{{ generatedStory.world_building.atmosphere || '未设定' }}</p>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane
          v-if="generatedStory.writing_style"
          label="文风建议"
          name="style"
        >
          <div class="style-panel">
            <div class="style-row">
              <span>语气</span>
              <p>{{ generatedStory.writing_style.tone || '—' }}</p>
            </div>
            <div class="style-row">
              <span>视角</span>
              <p>{{ generatedStory.writing_style.pov || '—' }}</p>
            </div>
            <div class="style-row">
              <span>节奏</span>
              <p>{{ generatedStory.writing_style.pacing || '—' }}</p>
            </div>
            <div v-if="generatedStory.writing_style.techniques?.length" class="style-row">
              <span>技巧</span>
              <p>{{ generatedStory.writing_style.techniques.join('、') }}</p>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>

      <section class="apply-bar">
        <div class="apply-copy">
          <h3>应用到项目</h3>
          <p>保存设定后，后续 AI 写作会自动参考这些内容</p>
        </div>
        <el-form :model="applyForm" class="apply-form" @submit.prevent>
          <el-select
            v-model="applyForm.projectId"
            clearable
            placeholder="选择现有项目"
            class="apply-select"
          >
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
          <el-input
            v-model="applyForm.newProjectName"
            placeholder="或输入新项目名称"
            class="apply-input"
          />
        </el-form>
        <div class="apply-actions">
          <el-button type="primary" plain :loading="applying" @click="applyToProject">
            <el-icon><FolderChecked /></el-icon>
            保存到项目
          </el-button>
          <el-button
            class="btn-primary"
            :loading="applying || quickCreating"
            @click="confirmAndCreateProject"
          >
            <el-icon><Check /></el-icon>
            确认并创建
          </el-button>
          <el-button :loading="quickCreating" @click="quickCreateProject">
            <el-icon><Plus /></el-icon>
            一键创建
          </el-button>
        </div>
      </section>
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
import StyleAgentPicker from '@/components/StyleAgentPicker.vue'

const router = useRouter()
const projectStore = useProjectStore()
const authStore = useAuthStore()

const API_BASE = import.meta.env.VITE_API_URL || API_BASE_URL
const getAuthToken = () => authStore.token || localStorage.getItem('token')

const genres = [
  '科幻', '悬疑推理', '爱情', '奇幻', '历史',
  '武侠', '恐怖惊悚', '现实主义', '冒险', '其他',
]

const themeExamples = [
  '失忆侦探在雨夜里追查自己的案件',
  '星际邮差投递一封无法送达的情书',
  '小镇茶馆里，每个人都在隐瞒同一件事',
]

const generating = ref(false)
const progress = ref(0)
const statusText = ref('正在生成...')
const generatedStory = ref<any>(null)
const selectedTitle = ref('')
const applying = ref(false)
const quickCreating = ref(false)
const previewContent = ref('')
const resultTab = ref('outline')

const form = ref({
  theme: '',
  genre: '',
  wordCount: 10000,
  chapterCount: 5,
  additional: '',
})
const selectedStyleAgentId = ref<number | undefined>(undefined)

const applyForm = ref({
  projectId: null as number | null,
  newProjectName: '',
})

const projects = computed(() => projectStore.projects)

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
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        theme: form.value.theme,
        genre: form.value.genre || undefined,
        word_count: form.value.wordCount,
        chapter_count: form.value.chapterCount,
        additional_requirements: form.value.additional || undefined,
        style_agent_id: selectedStyleAgentId.value,
      }),
    })

    if (!response.ok) {
      if (response.status === 401) {
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
      if (data.startsWith('[ERROR]')) {
        throw new Error(data.slice('[ERROR]'.length).trim() || '生成失败')
      }
      let parsed: any
      try {
        parsed = JSON.parse(data)
      } catch {
        chunksReceived++
        const safe = (data || '')
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/\n/g, '<br>')
        previewContent.value += safe
        progress.value = Math.min(95, 10 + chunksReceived * 5)
        return
      }

      if (parsed.success !== undefined) {
        if (parsed.success) {
          generatedStory.value = parsed.data
          selectedTitle.value = parsed.data?.title_options?.[0] || ''
          resultTab.value = 'outline'
          progress.value = 100
          statusText.value = '生成完成！'
          ElMessage.success('故事设定生成成功！')
          isDone = true
        } else {
          throw new Error(parsed.error || '生成失败')
        }
        return
      }
      if (parsed.chunk != null) {
        const content = String(parsed.chunk)
        chunksReceived++
        previewContent.value += content
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/\n/g, '<br>')
        progress.value = Math.min(95, 10 + chunksReceived * 5)
        if (chunksReceived < 3) statusText.value = '正在构思故事框架...'
        else if (chunksReceived < 6) statusText.value = '正在设计角色...'
        else if (chunksReceived < 9) statusText.value = '正在构建情节...'
        else statusText.value = '正在完善世界观...'
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
  } catch (error: unknown) {
    clearInterval(progressInterval)
    const raw = String(error instanceof Error ? error.message : error || '')
    let msg = raw || '生成失败，请重试'
    if (/network error|failed to fetch|incomplete_chunked|ERR_INCOMPLETE/i.test(raw)) {
      msg = '与 AI 的连接中断。请确认本地 Ollama 已启动，或稍后重试；若刚切换本地/在线模式，可刷新页面后再试。'
    }
    ElMessage.error(msg)
    console.error(error)
  } finally {
    generating.value = false
  }
}

const regenerate = () => {
  generatedStory.value = null
  generateStory()
}

const reset = () => {
  generatedStory.value = null
  selectedTitle.value = ''
  previewContent.value = ''
  resultTab.value = 'outline'
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
    await ElMessageBox.confirm(
      '确认要使用当前修改的大纲创建新项目吗？',
      '确认创建',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )

    quickCreating.value = true
    const payload: Record<string, any> = {
      theme: form.value.theme,
      project_name: applyForm.value.newProjectName || selectedTitle.value,
      genre: form.value.genre,
      word_count: form.value.wordCount,
    }
    if (generatedStory.value) payload.story_data = generatedStory.value

    const response = await fetch(`${API_BASE}/api/ai-story-generator/quick-create-project`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getAuthToken()}`,
      },
      body: JSON.stringify(payload),
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
        Authorization: `Bearer ${getAuthToken()}`,
      },
      body: JSON.stringify({
        project_id: applyForm.value.projectId,
        story_data: generatedStory.value,
      }),
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
      word_count: form.value.wordCount,
    }
    if (generatedStory.value) {
      payload.story_data = generatedStory.value
    }
    const response = await fetch(`${API_BASE}/api/ai-story-generator/quick-create-project`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getAuthToken()}`,
      },
      body: JSON.stringify(payload),
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

onMounted(() => {
  projectStore.fetchProjects()
})
</script>

<style scoped lang="scss">
.story-generator-page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 20px 20px 48px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;

  h1 {
    margin: 0 0 6px;
    font-size: 26px;
    font-weight: 700;
    color: var(--coffee-text);
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .header-icon {
    color: var(--coffee-primary);
  }

  .subtitle {
    margin: 0;
    color: var(--coffee-text-secondary);
    font-size: 14px;
  }

  .header-actions {
    display: flex;
    gap: 8px;
    flex-shrink: 0;
  }
}

.compose-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(280px, 0.9fr);
  gap: 20px;
  align-items: start;
}

.compose-panel,
.side-panel,
.result-hero,
.apply-bar {
  background: var(--coffee-bg-card);
  border: 1px solid var(--coffee-border);
  border-radius: 14px;
  box-shadow: 0 2px 12px var(--coffee-shadow);
}

.compose-panel {
  padding: 22px 22px 18px;
}

.compose-form {
  :deep(.el-form-item__label) {
    color: var(--coffee-text-secondary);
    font-weight: 600;
  }
}

.genre-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.genre-chip,
.example-chip {
  border: 1px solid var(--coffee-border);
  background: var(--coffee-bg-warm, var(--coffee-bg));
  color: var(--coffee-text-secondary);
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.18s ease;

  &:hover:not(:disabled) {
    border-color: var(--coffee-primary);
    color: var(--coffee-primary);
  }

  &.active {
    background: color-mix(in srgb, var(--coffee-primary) 14%, transparent);
    border-color: var(--coffee-primary);
    color: var(--coffee-primary);
    font-weight: 600;
  }

  &:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
}

.stats-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 16px;
}

.stat-value {
  margin-top: 4px;
  font-size: 13px;
  font-weight: 600;
  color: var(--coffee-primary);

  &.muted {
    font-weight: 500;
    color: var(--coffee-text-muted);
  }
}

.compose-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}

.generate-btn {
  min-width: 180px;
}

.side-panel {
  padding: 20px;
  position: sticky;
  top: 16px;
}

.tips-panel {
  h3 {
    margin: 0 0 12px;
    font-size: 16px;
    color: var(--coffee-text);
  }

  ul {
    margin: 0 0 18px;
    padding-left: 18px;
    color: var(--coffee-text-secondary);
    font-size: 13px;
    line-height: 1.7;
  }
}

.tip-examples {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tip-label {
  font-size: 12px;
  color: var(--coffee-text-muted);
  margin-bottom: 2px;
}

.example-chip {
  text-align: left;
  border-radius: 10px;
  line-height: 1.45;
}

.generating-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.generating-head {
  display: flex;
  gap: 12px;
  align-items: flex-start;

  strong {
    display: block;
    color: var(--coffee-text);
    margin-bottom: 2px;
  }

  p {
    margin: 0;
    font-size: 12px;
    color: var(--coffee-text-muted);
  }
}

.pulse-dot {
  width: 10px;
  height: 10px;
  margin-top: 5px;
  border-radius: 50%;
  background: var(--coffee-primary);
  box-shadow: 0 0 0 0 rgba(var(--coffee-primary-rgb), 0.45);
  animation: pulse 1.4s ease-out infinite;
}

@keyframes pulse {
  70% {
    box-shadow: 0 0 0 10px rgba(var(--coffee-primary-rgb), 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(var(--coffee-primary-rgb), 0);
  }
}

.preview-box {
  border: 1px solid var(--coffee-border);
  border-radius: 10px;
  overflow: hidden;
  background: var(--coffee-bg-warm, var(--coffee-bg));
}

.preview-label {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--coffee-text-secondary);
  border-bottom: 1px solid var(--coffee-border);
}

.preview-content {
  padding: 12px;
  max-height: 360px;
  overflow-y: auto;
  font-size: 13px;
  line-height: 1.7;
  color: var(--coffee-text);
  word-break: break-word;
}

.result-layout {
  display: flex;
  flex-direction: column;
  gap: 18px;
  animation: fadeIn 0.35s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.result-hero {
  padding: 20px 22px;
}

.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.meta-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  color: var(--coffee-primary);
  background: color-mix(in srgb, var(--coffee-primary) 12%, transparent);

  &.soft {
    color: var(--coffee-text-secondary);
    background: var(--coffee-bg-warm, var(--coffee-bg));
  }
}

.core-theme {
  margin: 0 0 16px;
  color: var(--coffee-text-secondary);
  font-size: 14px;
  line-height: 1.6;
}

.title-picker {
  h3 {
    margin: 0 0 10px;
    font-size: 15px;
    color: var(--coffee-text);
  }
}

.title-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
  width: 100%;
}

.title-radio {
  margin: 0 !important;
  height: auto !important;
  padding: 12px 14px !important;
  border-radius: 10px !important;
  white-space: normal;
  align-items: flex-start;

  :deep(.el-radio__label) {
    font-size: 14px;
    font-weight: 500;
    line-height: 1.45;
    color: var(--coffee-text);
  }
}

.result-tabs {
  background: var(--coffee-bg-card);
  border: 1px solid var(--coffee-border);
  border-radius: 14px;
  padding: 8px 18px 18px;
  box-shadow: 0 2px 12px var(--coffee-shadow);

  :deep(.el-tabs__header) {
    margin-bottom: 16px;
  }

  :deep(.el-tabs__item) {
    font-weight: 600;
  }
}

.outline-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.outline-item {
  background: var(--coffee-bg-warm, var(--coffee-bg));
  border: 1px solid var(--coffee-border);
  border-radius: 12px;
  padding: 14px;
}

.outline-item-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.act-index {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
  background: var(--coffee-gradient-primary, var(--coffee-primary));
}

.outline-act {
  font-weight: 600;
  color: var(--coffee-text);
}

.outline-title-input,
.outline-content-input {
  margin-bottom: 10px;
}

.outline-footer {
  display: flex;
}

.outline-word-count {
  max-width: 220px;
}

.characters-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
}

.character-card {
  border: 1px solid var(--coffee-border);
  border-radius: 12px;
  padding: 14px;
  background: var(--coffee-bg-warm, var(--coffee-bg));
  border-left-width: 4px;

  &.protagonist {
    border-left-color: #67c23a;
  }
  &.antagonist {
    border-left-color: #f56c6c;
  }
  &.supporting {
    border-left-color: var(--coffee-text-muted);
  }
}

.character-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.character-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--coffee-text);
}

.character-info {
  p {
    margin: 0 0 8px;
    font-size: 13px;
    line-height: 1.55;
    color: var(--coffee-text-secondary);

    span {
      display: inline-block;
      min-width: 36px;
      margin-right: 8px;
      color: var(--coffee-text-muted);
      font-weight: 600;
    }

    &:last-child {
      margin-bottom: 0;
    }
  }
}

.plot-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.plot-item {
  display: grid;
  grid-template-columns: 32px 1fr;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--coffee-border);
  border-radius: 12px;
  background: var(--coffee-bg-warm, var(--coffee-bg));
}

.plot-index {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: var(--coffee-primary);
  background: color-mix(in srgb, var(--coffee-primary) 12%, transparent);
}

.plot-body {
  h4 {
    margin: 0 0 6px;
    font-size: 14px;
    color: var(--coffee-text);
  }

  p {
    margin: 0 0 4px;
    font-size: 13px;
    color: var(--coffee-text-secondary);
    line-height: 1.55;

    em {
      font-style: normal;
      font-weight: 600;
      color: var(--coffee-text-muted);
      margin-right: 8px;
    }
  }
}

.world-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.world-item {
  padding: 14px;
  border: 1px solid var(--coffee-border);
  border-radius: 12px;
  background: var(--coffee-bg-warm, var(--coffee-bg));

  &.span-2 {
    grid-column: span 2;
  }

  h4 {
    margin: 0 0 8px;
    font-size: 13px;
    color: var(--coffee-text-muted);
  }

  p {
    margin: 0;
    font-size: 14px;
    line-height: 1.6;
    color: var(--coffee-text);
  }
}

.style-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.style-row {
  display: grid;
  grid-template-columns: 64px 1fr;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid var(--coffee-border);
  background: var(--coffee-bg-warm, var(--coffee-bg));

  span {
    font-size: 13px;
    font-weight: 600;
    color: var(--coffee-text-muted);
  }

  p {
    margin: 0;
    font-size: 14px;
    color: var(--coffee-text);
    line-height: 1.55;
  }
}

.apply-bar {
  padding: 18px 20px;
  display: grid;
  grid-template-columns: minmax(160px, 0.8fr) minmax(0, 1.4fr) auto;
  gap: 16px;
  align-items: center;
  position: sticky;
  bottom: 12px;
  z-index: 5;
}

.apply-copy {
  h3 {
    margin: 0 0 4px;
    font-size: 15px;
    color: var(--coffee-text);
  }

  p {
    margin: 0;
    font-size: 12px;
    color: var(--coffee-text-muted);
  }
}

.apply-form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.apply-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

@media (max-width: 960px) {
  .compose-layout {
    grid-template-columns: 1fr;
  }

  .side-panel {
    position: static;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .apply-bar {
    grid-template-columns: 1fr;
  }

  .apply-form {
    grid-template-columns: 1fr;
  }

  .world-item.span-2 {
    grid-column: span 1;
  }

  .world-grid {
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
  }
}
</style>
