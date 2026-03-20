<template>
  <div class="brainstorm-writing">
    <div class="page-header">
      <h1>🧠 脑洞写作</h1>
      <p class="subtitle">基于网络流行脑洞和创意话题，生成有趣的文章</p>
    </div>

    <div class="content-grid">
      <!-- 左侧：脑洞选择区 -->
      <div class="left-panel">
        <!-- 分类选择 -->
        <div class="section">
          <h3>📂 脑洞分类</h3>
          <div class="category-tags">
            <button
              v-for="cat in categories"
              :key="cat.key"
              :class="['category-btn', { active: selectedCategory === cat.key }]"
              @click="selectCategory(cat.key)"
            >
              {{ cat.name }}
            </button>
            <button
              :class="['category-btn', { active: selectedCategory === null }]"
              @click="selectCategory(null)"
            >
              🎲 全部
            </button>
          </div>
        </div>

        <!-- 热门脑洞 -->
        <div class="section">
          <div class="section-header">
            <h3>🔥 热门脑洞</h3>
            <button class="refresh-btn" @click="fetchTrendingBrainstorms">
              🔄 刷新
            </button>
          </div>
          <div class="brainstorm-list">
            <div
              v-for="(item, index) in trendingBrainstorms"
              :key="index"
              :class="['brainstorm-card', { selected: selectedBrainstorm?.title === item.title }]"
              @click="selectBrainstorm(item)"
            >
              <div class="card-header">
                <span class="category-tag">{{ item.category }}</span>
                <span class="heat">🔥 {{ formatHeat(item.heat) }}</span>
              </div>
              <h4>{{ item.title }}</h4>
            </div>
          </div>
        </div>

        <!-- 随机生成 -->
        <div class="section">
          <button class="random-btn" @click="generateRandomBrainstorm">
            🎲 随机生成脑洞
          </button>
        </div>

        <!-- 从热点生成 -->
        <div class="section">
          <h3>📰 基于热点生成</h3>
          <button class="secondary-btn" @click="generateFromHotTopics">
            🔥 将当前热点转为脑洞
          </button>
        </div>

        <!-- 自定义脑洞 -->
        <div class="section">
          <div class="section-header">
            <h3>🧩 自定义脑洞</h3>
          </div>

          <div class="custom-form">
            <el-input
              v-model="customTitle"
              placeholder="脑洞标题（可选）"
              clearable
            />
            <el-input
              v-model="customConcept"
              type="textarea"
              :rows="4"
              placeholder="核心概念/设定（必填）"
              show-word-limit
            />
          </div>

          <div class="custom-actions">
            <button
              class="primary-btn"
              :disabled="!customConcept.trim()"
              @click="addCustomBrainstorm"
            >
              ➕ 添加自定义脑洞
            </button>
          </div>

          <div v-if="customBrainstorms.length > 0" class="custom-list">
            <div
              v-for="(item, index) in customBrainstorms"
              :key="item.id || index"
              class="brainstorm-card custom-brain-card"
              :class="{ selected: selectedBrainstorm?.id ? selectedBrainstorm?.id === item.id : selectedBrainstorm?.concept === item.concept }"
              @click="selectBrainstorm(item)"
            >
              <div class="card-header">
                <span class="category-tag">自定义</span>
                <button
                  class="delete-icon-btn"
                  title="删除"
                  @click.stop="deleteCustomBrainstorm(index)"
                >
                  删除
                </button>
              </div>
              <h4>{{ item.title }}</h4>
              <p class="custom-concept">
                {{ item.concept.length > 80 ? item.concept.slice(0, 80) + '...' : item.concept }}
              </p>
            </div>
          </div>

          <div v-else class="custom-empty">
            <p class="hint">还没有自定义脑洞</p>
          </div>
        </div>
      </div>

      <!-- 右侧：写作区 -->
      <div class="right-panel">
        <div v-if="!selectedBrainstorm" class="empty-state">
          <div class="empty-icon">🧠</div>
          <p>选择一个脑洞话题开始创作</p>
          <p class="hint">或者点击"随机生成脑洞"获取灵感</p>
        </div>

        <div v-else class="writing-area">
          <!-- 选中的脑洞 -->
          <div class="selected-brainstorm">
            <div class="brainstorm-header">
              <span class="category-badge">{{ selectedBrainstorm.category }}</span>
              <h2>{{ selectedBrainstorm.title }}</h2>
            </div>
          </div>

          <!-- 写作设置 -->
          <div class="settings-bar">
            <div class="setting-item">
              <label>写作风格：</label>
              <select v-model="writingStyle">
                <option value="幽默风趣">😄 幽默风趣</option>
                <option value="深度思考">🤔 深度思考</option>
                <option value="轻松日常">☕ 轻松日常</option>
                <option value="悬疑反转">🎭 悬疑反转</option>
                <option value="温情治愈">💝 温情治愈</option>
              </select>
            </div>
            <div class="setting-item">
              <label>文章长度：</label>
              <select v-model="wordCount">
                <option value="short">短文 (~1000字)</option>
                <option value="medium">中篇 (~1500字)</option>
                <option value="long">长文 (~2500字)</option>
              </select>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="action-buttons">
            <button
              class="primary-btn"
              :disabled="generatingOutline"
              @click="generateOutline"
            >
              <span v-if="generatingOutline">⏳ 生成中...</span>
              <span v-else>📋 生成大纲</span>
            </button>
            <button
              class="primary-btn"
              :disabled="generatingArticle || !outline"
              @click="generateArticle"
            >
              <span v-if="generatingArticle">✍️ 写作中...</span>
              <span v-else>📝 生成文章</span>
            </button>
            <button class="secondary-btn" @click="quickGenerate">
              ⚡ 一键生成
            </button>
          </div>

          <!-- 大纲展示 -->
          <div v-if="outline" class="outline-section">
            <h3>📋 文章大纲</h3>
            <div class="outline-content">
              <h4>{{ outline.title || selectedBrainstorm?.title }}</h4>
              <div class="angle" v-if="outline.angle">
                <strong>写作角度：</strong>{{ outline.angle }}
              </div>
              <div class="sections" v-if="(outline.sections || []).length > 0">
                <div
                  v-for="(section, idx) in outline.sections"
                  :key="idx"
                  class="outline-section-item"
                >
                  <h5>{{ idx + 1 }}. {{ section.name || section.title || '章节' }}</h5>
                  <ul v-if="(section.points || []).length > 0">
                    <li v-for="(point, pidx) in section.points" :key="pidx">
                      {{ point }}
                    </li>
                  </ul>
                </div>
              </div>
              <!-- fallback: 如果 outline 是字符串 -->
              <pre v-if="typeof outline === 'string'" class="outline-raw">{{ outline }}</pre>
              <div class="keywords" v-if="(outline.keywords || []).length > 0">
                <strong>关键词：</strong>
                <span
                  v-for="(kw, idx) in outline.keywords"
                  :key="idx"
                  class="keyword-tag"
                >
                  {{ kw }}
                </span>
              </div>
            </div>
          </div>

          <!-- 文章展示 -->
          <div v-if="article" class="article-section">
            <div class="article-header">
              <h3>📝 生成的文章</h3>
              <div class="article-actions">
                <button class="icon-btn" @click="copyArticle" title="复制">
                  📋
                </button>
                <button class="icon-btn" @click="openSaveDialog" title="保存">
                  💾
                </button>
                <button class="icon-btn" @click="showPublishDialog = true" title="发布到自媒体">
                  📢
                </button>
              </div>
            </div>
            <div class="article-content">
              <h1>{{ article.title }}</h1>
              <div class="article-meta">
                <span v-if="article.style">风格：{{ article.style }}</span>
                <span v-if="article.word_count">字数：{{ article.word_count }}</span>
              </div>
              <div class="article-body" v-html="renderedArticle"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 保存对话框 -->
  <el-dialog
    v-model="saveDialogVisible"
    title="保存文章"
    width="500px"
    :close-on-click-modal="false"
  >
    <div class="save-dialog-content">
      <p class="dialog-tip">选择要保存到的项目，或创建新项目</p>
      
      <!-- 现有项目列表 -->
      <div v-if="projects.length > 0" class="project-list">
        <div class="section-title">选择项目：</div>
        <el-radio-group v-model="selectedProjectId" class="project-radio-group">
          <el-radio 
            v-for="project in projects" 
            :key="project.id" 
            :value="project.id"
            :label="project.title"
            class="project-radio"
          />
        </el-radio-group>
      </div>
      
      <div v-else class="no-projects">
        <el-empty description="暂无项目" />
      </div>
      
      <!-- 创建新项目 -->
      <div class="new-project-section">
        <el-divider>
          <span class="divider-text">或</span>
        </el-divider>
        <el-input
          v-model="newProjectName"
          placeholder="输入新项目名称"
          clearable
          :disabled="selectedProjectId !== null"
        >
          <template #prefix>
            <span>📁</span>
          </template>
        </el-input>
      </div>
      
      <!-- 文章预览 -->
      <div class="article-preview">
        <div class="section-title">文章预览：</div>
        <div class="preview-content">
          <strong>{{ article?.title }}</strong>
          <p>{{ article?.content?.substring(0, 100) }}...</p>
        </div>
      </div>
    </div>
    
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="saveDialogVisible = false">取消</el-button>
        <el-button 
          type="primary" 
          @click="saveArticle"
          :loading="saving"
          :disabled="!selectedProjectId && !newProjectName.trim()"
        >
          {{ saving ? '保存中...' : '保存' }}
        </el-button>
      </div>
    </template>
  </el-dialog>

  <PublishDialog
    v-model="showPublishDialog"
    :raw-title="article?.title || selectedBrainstorm?.title || ''"
    :raw-content="article?.content || ''"
  />
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import PublishDialog from '@/components/PublishDialog.vue'
import { useAuthStore } from '@/stores/auth'
import api, { projectApi, documentApi } from '@/api'
import type { Block } from '@/api/types'

marked.setOptions({ breaks: false, gfm: true })

const authStore = useAuthStore()

// 状态
const categories = ref([])
const trendingBrainstorms = ref([])
const selectedCategory = ref(null)
const selectedBrainstorm = ref(null)
const customBrainstorms = ref<Array<{ id: string; title: string; category: string; concept: string }>>([])
const customTitle = ref('')
const customConcept = ref('')
const writingStyle = ref('幽默风趣')
const wordCount = ref('medium')
const outline = ref(null)
const article = ref(null)
const generatingOutline = ref(false)
const generatingArticle = ref(false)

// 保存对话框状态
const saveDialogVisible = ref(false)
const projects = ref([])
const selectedProjectId = ref(null)
const newProjectName = ref('')
const saving = ref(false)
const showPublishDialog = ref(false)

// 获取分类
const fetchCategories = async () => {
  try {
    const res = await api.get('/brainstorm/categories')
    categories.value = res.data
  } catch (error) {
    console.error('获取分类失败:', error)
  }
}

// 获取热门脑洞
const fetchTrendingBrainstorms = async () => {
  try {
    const params: Record<string, any> = { limit: 20 }
    if (selectedCategory.value) {
      params.category = selectedCategory.value
    }
    const res = await api.get('/brainstorm/trending', { params })
    trendingBrainstorms.value = res.data
  } catch (error) {
    console.error('获取热门脑洞失败:', error)
    ElMessage.error('获取热门脑洞失败')
  }
}

// 选择分类
const selectCategory = (category: string | null) => {
  selectedCategory.value = category
  fetchTrendingBrainstorms()
}

// 选择脑洞
const selectBrainstorm = (brainstorm) => {
  selectedBrainstorm.value = brainstorm
  outline.value = null
  article.value = null
}

const CUSTOM_BRAINS_KEY = 'brainstorm_custom_brainstorms_v1'

function loadCustomBrainstorms() {
  try {
    const raw = localStorage.getItem(CUSTOM_BRAINS_KEY)
    if (!raw) return
    const arr = JSON.parse(raw)
    if (Array.isArray(arr)) {
      customBrainstorms.value = arr
    }
  } catch {
    // ignore
  }
}

function persistCustomBrainstorms() {
  try {
    localStorage.setItem(CUSTOM_BRAINS_KEY, JSON.stringify(customBrainstorms.value))
  } catch {
    // ignore
  }
}

function addCustomBrainstorm() {
  const concept = customConcept.value.trim()
  if (!concept) return

  const title = customTitle.value.trim() || `自定义脑洞｜${concept.slice(0, 10)}`

  const item = {
    id: crypto.randomUUID(),
    title,
    category: '自定义',
    concept,
  }

  customBrainstorms.value = [item, ...customBrainstorms.value]
  persistCustomBrainstorms()

  customTitle.value = ''
  customConcept.value = ''

  selectBrainstorm(item)
  ElMessage.success('已添加并选中自定义脑洞')
}

function deleteCustomBrainstorm(index: number) {
  const removed = customBrainstorms.value[index]
  if (!removed) return

  customBrainstorms.value = customBrainstorms.value.filter((_, i) => i !== index)
  persistCustomBrainstorms()

  if (selectedBrainstorm.value?.id && selectedBrainstorm.value?.id === removed.id) {
    selectedBrainstorm.value = null
    outline.value = null
    article.value = null
  }

  ElMessage.success('已删除自定义脑洞')
}

// 随机生成脑洞
const generateRandomBrainstorm = async () => {
  try {
    const res = await api.get('/brainstorm/random', {
      params: { category: selectedCategory.value }
    })
    selectBrainstorm(res.data)
    ElMessage.success('已生成随机脑洞')
  } catch (error) {
    console.error('生成随机脑洞失败:', error)
    ElMessage.error('生成随机脑洞失败')
  }
}

// 从热点生成
const generateFromHotTopics = async () => {
  try {
    ElMessage.info('正在从热点生成脑洞...')
    const res = await api.get('/brainstorm/from-hot-topics', { params: { limit: 5 } })
    if (res.data.brainstorms?.length > 0) {
      trendingBrainstorms.value = res.data.brainstorms
      ElMessage.success(`已生成 ${res.data.brainstorms.length} 个脑洞`)
    }
  } catch (error) {
    console.error('从热点生成失败:', error)
    ElMessage.error('从热点生成脑洞失败')
  }
}

// 生成大纲
const generateOutline = async () => {
  if (!selectedBrainstorm.value) return

  generatingOutline.value = true
  try {
    const res = await api.post('/brainstorm/generate-outline', {
      title: selectedBrainstorm.value.title,
      category: selectedBrainstorm.value.category,
      concept: selectedBrainstorm.value.concept,
      style: writingStyle.value,
      word_count: wordCount.value
    }, { timeout: 180000 })
    outline.value = res.data.outline
    ElMessage.success('大纲生成成功')
  } catch (error) {
    console.error('生成大纲失败:', error)
    ElMessage.error('生成大纲失败')
  } finally {
    generatingOutline.value = false
  }
}

// 生成文章
const generateArticle = async () => {
  if (!selectedBrainstorm.value) return

  generatingArticle.value = true
  try {
    const res = await api.post('/brainstorm/generate-article', {
      title: selectedBrainstorm.value.title,
      category: selectedBrainstorm.value.category,
      concept: selectedBrainstorm.value.concept,
      style: writingStyle.value,
      word_count: wordCount.value,
      outline: outline.value
    }, { timeout: 180000 })
    article.value = res.data.article
    ElMessage.success('文章生成成功')
  } catch (error) {
    console.error('生成文章失败:', error)
    ElMessage.error('生成文章失败')
  } finally {
    generatingArticle.value = false
  }
}

// 一键生成
const quickGenerate = async () => {
  if (!selectedBrainstorm.value) {
    ElMessage.warning('请先选择一个脑洞')
    return
  }

  await generateOutline()
  if (outline.value) {
    await generateArticle()
  }
}

// 渲染文章 Markdown
const renderedArticle = computed(() => {
  if (!article.value?.content) return ''
  return DOMPurify.sanitize(marked(article.value.content) as string)
})

// 格式化热度
const formatHeat = (heat) => {
  if (heat >= 10000) {
    return (heat / 10000).toFixed(1) + 'w'
  }
  return heat.toString()
}

// 复制文章
const copyArticle = () => {
  if (!article.value) return
  navigator.clipboard.writeText(article.value.content)
  ElMessage.success('已复制到剪贴板')
}

// 获取项目列表
const fetchProjects = async () => {
  try {
    const res = await projectApi.list()
    projects.value = res.data
  } catch (error) {
    console.error('获取项目列表失败:', error)
  }
}

// 打开保存对话框
const openSaveDialog = async () => {
  if (!article.value) return
  
  // 检查用户是否登录
  if (!authStore.isLoggedIn) {
    ElMessage.warning('请先登录后再保存文章')
    return
  }
  
  await fetchProjects()
  selectedProjectId.value = projects.value.length > 0 ? projects.value[0].id : null
  newProjectName.value = ''
  saveDialogVisible.value = true
}

// 保存文章
const saveArticle = async () => {
  if (!article.value) return
  
  // 检查用户是否登录
  if (!authStore.isLoggedIn) {
    ElMessage.warning('请先登录后再保存文章')
    return
  }
  
  // 如果没有项目，需要先创建项目
  if (projects.value.length === 0 && !newProjectName.value.trim()) {
    ElMessage.warning('请先输入项目名称创建新项目')
    return
  }
  
  saving.value = true
  try {
    let projectId = selectedProjectId.value
    
    // 如果选择了创建新项目
    if (!projectId && newProjectName.value.trim()) {
      const createRes = await projectApi.create({
        title: newProjectName.value.trim()
      })
      projectId = createRes.data.id
    }
    
    // 创建文档 - 将字符串内容转换为 Block 格式
    const blocks: Block[] = [
      {
        id: crypto.randomUUID(),
        type: 'paragraph',
        content: article.value.content,
        props: {}
      }
    ]
    
    await documentApi.create(projectId, {
      title: article.value.title,
      content: blocks,
    })
    
    ElMessage.success('文章保存成功')
    saveDialogVisible.value = false
  } catch (error) {
    console.error('保存文章失败:', error)
    ElMessage.error('保存文章失败')
  } finally {
    saving.value = false
  }
}

// 初始化
onMounted(() => {
  fetchCategories()
  fetchTrendingBrainstorms()
  loadCustomBrainstorms()
})
</script>

<style scoped lang="scss">
.brainstorm-writing {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;

  h1 {
    font-size: 28px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .subtitle {
    color: #666;
    font-size: 14px;
  }
}

.content-grid {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 24px;
}

.left-panel {
  .section {
    background: #fff;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 16px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

    h3 {
      font-size: 16px;
      margin-bottom: 12px;
      color: #333;
    }
  }
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;

  h3 {
    margin: 0;
  }
}

.refresh-btn {
  font-size: 12px;
  padding: 4px 10px;
  background: #f0f0f0;
  border: none;
  border-radius: 4px;
  cursor: pointer;

  &:hover {
    background: #e0e0e0;
  }
}

.category-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.category-btn {
  padding: 6px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 16px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;

  &:hover {
    border-color: #409eff;
    color: #409eff;
  }

  &.active {
    background: #409eff;
    color: #fff;
    border-color: #409eff;
  }
}

.brainstorm-list {
  max-height: 400px;
  overflow-y: auto;
}

.brainstorm-card {
  padding: 12px;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: #409eff;
    box-shadow: 0 2px 8px rgba(64, 158, 255, 0.15);
  }

  &.selected {
    border-color: #409eff;
    background: #f0f9ff;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }

  .category-tag {
    font-size: 11px;
    padding: 2px 8px;
    background: #f0f0f0;
    border-radius: 4px;
    color: #666;
  }

  .heat {
    font-size: 12px;
    color: #ff6b6b;
  }

  h4 {
    font-size: 14px;
    line-height: 1.5;
    color: #333;
    margin: 0;
  }
}

.random-btn {
  width: 100%;
  padding: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  cursor: pointer;
  transition: transform 0.2s;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  }
}

.secondary-btn {
  width: 100%;
  padding: 10px;
  background: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;

  &:hover {
    background: #e8e8e8;
  }
}

.right-panel {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  min-height: 600px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 400px;
  color: #999;

  .empty-icon {
    font-size: 64px;
    margin-bottom: 16px;
  }

  p {
    font-size: 16px;
    margin-bottom: 8px;
  }

  .hint {
    font-size: 14px;
    color: #bbb;
  }
}

.writing-area {
  .selected-brainstorm {
    margin-bottom: 20px;
    padding-bottom: 20px;
    border-bottom: 1px solid #e8e8e8;

    .brainstorm-header {
      .category-badge {
        display: inline-block;
        padding: 4px 12px;
        background: #409eff;
        color: #fff;
        border-radius: 4px;
        font-size: 12px;
        margin-bottom: 12px;
      }

      h2 {
        font-size: 20px;
        line-height: 1.5;
        color: #333;
        margin: 0;
      }
    }
  }
}

.settings-bar {
  display: flex;
  gap: 24px;
  margin-bottom: 20px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;

  .setting-item {
    display: flex;
    align-items: center;
    gap: 8px;

    label {
      font-size: 14px;
      color: #666;
    }

    select {
      padding: 6px 12px;
      border: 1px solid #d9d9d9;
      border-radius: 4px;
      background: #fff;
      font-size: 14px;
      cursor: pointer;

      &:focus {
        outline: none;
        border-color: #409eff;
      }
    }
  }
}

.action-buttons {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;

  .primary-btn {
    padding: 10px 20px;
    background: #409eff;
    color: #fff;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s;

    &:hover:not(:disabled) {
      background: #66b1ff;
    }

    &:disabled {
      background: #a0cfff;
      cursor: not-allowed;
    }
  }
}

.outline-section {
  margin-bottom: 24px;

  h3 {
    font-size: 16px;
    margin-bottom: 12px;
    color: #333;
  }
}

.outline-content {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 16px;

  h4 {
    font-size: 16px;
    color: #409eff;
    margin-bottom: 12px;
  }

  .angle {
    font-size: 14px;
    color: #666;
    margin-bottom: 16px;
    padding: 8px 12px;
    background: #fff;
    border-radius: 4px;
    border-left: 3px solid #409eff;
  }

  .outline-section-item {
    margin-bottom: 12px;

    h5 {
      font-size: 14px;
      color: #333;
      margin-bottom: 6px;
    }

    ul {
      margin: 0;
      padding-left: 20px;

      li {
        font-size: 13px;
        color: #666;
        margin-bottom: 4px;
      }
    }
  }

  .keywords {
    margin-top: 16px;
    padding-top: 12px;
    border-top: 1px solid #e8e8e8;

    .keyword-tag {
      display: inline-block;
      padding: 2px 8px;
      background: #e6f7ff;
      color: #1890ff;
      border-radius: 4px;
      font-size: 12px;
      margin-right: 8px;
    }
  }
}

.article-section {
  .article-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    h3 {
      font-size: 16px;
      color: #333;
      margin: 0;
    }

    .article-actions {
      display: flex;
      gap: 8px;

      .icon-btn {
        padding: 6px 10px;
        background: #f5f5f5;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 16px;

        &:hover {
          background: #e8e8e8;
        }
      }
    }
  }
}

.article-content {
  background: #fafafa;
  border-radius: 8px;
  padding: 24px;

  h1 {
    font-size: 22px;
    color: #333;
    margin-bottom: 12px;
  }

  .article-meta {
    display: flex;
    gap: 16px;
    font-size: 13px;
    color: #999;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid #e8e8e8;
  }

  .article-body {
    line-height: 1.9;
    color: #333;
    font-size: 15px;

    :deep(h1), :deep(h2), :deep(h3) {
      margin: 24px 0 12px;
      color: #303133;
    }

    :deep(h2) { font-size: 19px; }
    :deep(h3) { font-size: 17px; }

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

    :deep(li) { margin-bottom: 6px; }

    :deep(hr) {
      border: none;
      border-top: 1px solid #ebeef5;
      margin: 20px 0;
    }
  }
}

.outline-raw {
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 400px;
  overflow-y: auto;
}

@media (max-width: 1024px) {
  .content-grid {
    grid-template-columns: 1fr;
  }

  .left-panel {
    .brainstorm-list {
      max-height: 300px;
    }
  }
}

// 保存对话框样式
.save-dialog-content {
  .dialog-tip {
    color: #666;
    margin-bottom: 20px;
  }

  .section-title {
    font-weight: 500;
    margin-bottom: 12px;
    color: #333;
  }

  .project-list {
    margin-bottom: 16px;

    .project-radio-group {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .project-radio {
      padding: 8px 12px;
      border-radius: 8px;
      transition: background-color 0.2s;

      &:hover {
        background-color: #f5f5f5;
      }
    }
  }

  .no-projects {
    margin-bottom: 16px;
  }

  .new-project-section {
    margin-bottom: 20px;

    .divider-text {
      color: #999;
      font-size: 13px;
    }
  }

  .article-preview {
    background-color: #f8f9fa;
    padding: 16px;
    border-radius: 8px;

    .preview-content {
      p {
        color: #666;
        font-size: 13px;
        margin-top: 8px;
      }
    }
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.custom-actions {
  margin: 12px 0 6px;
}

.custom-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.custom-list {
  margin-top: 12px;
}

.custom-empty {
  margin-top: 12px;
}

.custom-brain-card {
  position: relative;
}

.delete-icon-btn {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 4px 8px;
  cursor: pointer;
  font-size: 12px;

  &:hover {
    border-color: #f56c6c;
    color: #f56c6c;
  }
}

.custom-concept {
  margin: 8px 0 0;
  color: #606266;
  font-size: 13px;
  line-height: 1.6;
}
</style>
