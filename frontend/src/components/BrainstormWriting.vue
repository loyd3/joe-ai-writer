<template>
  <div class="brainstorm-writing">
    <div class="header-section">
      <h2 class="section-title">
        <span class="icon">💡</span>
        脑洞写作
      </h2>
      <p class="section-desc">8种创意模式，激发无限灵感</p>
    </div>

    <!-- 创意模式选择 -->
    <div class="mode-section">
      <h3 class="subsection-title">选择创意模式</h3>
      <div class="mode-grid">
        <div
          v-for="mode in creativeModes"
          :key="mode.id"
          class="mode-card"
          :class="{ active: selectedMode === mode.id }"
          :style="{ borderColor: selectedMode === mode.id ? mode.color : '' }"
          @click="selectMode(mode.id)"
        >
          <span class="mode-icon">{{ mode.icon }}</span>
          <span class="mode-name">{{ mode.name }}</span>
          <span class="mode-desc">{{ mode.description }}</span>
        </div>
      </div>
    </div>

    <!-- 创意元素 -->
    <div class="elements-section" v-if="showElements">
      <div class="elements-header">
        <h3 class="subsection-title">创意元素</h3>
        <el-button type="primary" size="small" @click="refreshElements" :loading="refreshing">
          <el-icon><Refresh /></el-icon>
          换一批
        </el-button>
      </div>
      <div class="elements-tags">
        <el-tag
          v-for="(element, index) in creativeElements"
          :key="index"
          :type="getElementType(element)"
          effect="dark"
          class="element-tag"
        >
          {{ formatElement(element) }}
        </el-tag>
      </div>
    </div>

    <!-- 关键词输入 -->
    <div class="keywords-section">
      <h3 class="subsection-title">关键词（可选）</h3>
      <el-input
        v-model="keywordsInput"
        placeholder="输入关键词，用逗号分隔，将用于生成创意"
        clearable
      />
    </div>

    <!-- 生成按钮 -->
    <div class="generate-section">
      <el-button
        type="primary"
        size="large"
        :loading="generating"
        @click="generateIdeas"
        class="btn btn-primary btn-lg"
      >
        <el-icon><MagicStick /></el-icon>
        生成创意
      </el-button>
    </div>

    <!-- 生成的创意列表 -->
    <div class="ideas-section" v-if="generatedIdeas.length > 0">
      <div class="ideas-header">
        <h3 class="subsection-title">生成的创意</h3>
        <div class="ideas-actions">
          <el-button type="success" size="small" @click="expandAllIdeas">
            全部扩展
          </el-button>
          <el-button type="warning" size="small" @click="remixIdeas" :disabled="selectedIdeas.length < 2">
            混合选中({{ selectedIdeas.length }})
          </el-button>
        </div>
      </div>

      <div class="ideas-list">
        <div
          v-for="(idea, index) in generatedIdeas"
          :key="index"
          class="idea-card"
          :class="{ selected: isIdeaSelected(idea), expanded: expandedIdeas[index] }"
          @click="toggleIdeaSelection(idea)"
        >
          <div class="idea-header">
            <div class="idea-select">
              <el-checkbox v-model="idea.selected" @click.stop />
            </div>
            <h4 class="idea-title">{{ idea.title }}</h4>
            <div class="idea-tags">
              <el-tag v-for="tag in idea.tags" :key="tag" size="small" effect="plain">
                {{ tag }}
              </el-tag>
            </div>
          </div>

          <div class="idea-content" v-if="idea.content">
            <p>{{ idea.content }}</p>
          </div>

          <div class="idea-details" v-if="idea.concept || idea.setting || idea.conflict">
            <div class="detail-item" v-if="idea.concept">
              <span class="detail-label">核心概念:</span>
              <span class="detail-value">{{ idea.concept }}</span>
            </div>
            <div class="detail-item" v-if="idea.setting">
              <span class="detail-label">故事设定:</span>
              <span class="detail-value">{{ idea.setting }}</span>
            </div>
            <div class="detail-item" v-if="idea.conflict">
              <span class="detail-label">主要冲突:</span>
              <span class="detail-value">{{ idea.conflict }}</span>
            </div>
          </div>

          <div class="idea-directions" v-if="idea.directions && idea.directions.length">
            <span class="directions-label">发展方向:</span>
            <el-tag
              v-for="(direction, dIndex) in idea.directions"
              :key="dIndex"
              size="small"
              type="info"
              class="direction-tag"
            >
              {{ direction }}
            </el-tag>
          </div>

          <div class="idea-actions">
            <el-button
              type="primary"
              size="small"
              @click.stop="expandIdea(idea, index)"
              :loading="expandingIndex === index"
            >
              扩展方案
            </el-button>
            <el-button
              type="success"
              size="small"
              @click.stop="writeContent(idea)"
            >
              开始写作
            </el-button>
            <el-button
              type="info"
              size="small"
              @click.stop="copyIdea(idea)"
            >
              复制
            </el-button>
          </div>

          <!-- 扩展内容 -->
          <div class="expansion-content" v-if="expandedIdeas[index] && idea.expansion">
            <div class="expansion-section" v-if="idea.expansion.outline">
              <h5>故事大纲</h5>
              <div class="expansion-text">{{ idea.expansion.outline }}</div>
            </div>
            <div class="expansion-section" v-if="idea.expansion.characters?.length">
              <h5>人物设定</h5>
              <div class="character-list">
                <div v-for="(char, cIndex) in idea.expansion.characters" :key="cIndex" class="character-item">
                  <strong>{{ char.name }}</strong> - {{ char.role }}
                  <p>{{ char.traits }}</p>
                </div>
              </div>
            </div>
            <div class="expansion-section" v-if="idea.expansion.scenes?.length">
              <h5>关键场景</h5>
              <ul>
                <li v-for="(scene, sIndex) in idea.expansion.scenes" :key="sIndex">{{ scene }}</li>
              </ul>
            </div>
            <div class="expansion-section" v-if="idea.expansion.suggestions?.length">
              <h5>写作建议</h5>
              <ul>
                <li v-for="(suggestion, sIndex) in idea.expansion.suggestions" :key="sIndex">{{ suggestion }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 写作对话框 -->
    <el-dialog
      v-model="writeDialogVisible"
      title="开始写作"
      width="70%"
      :close-on-click-modal="false"
    >
      <div class="write-dialog-content">
        <div class="write-settings">
          <el-form :model="writeSettings" label-width="100px">
            <el-form-item label="内容类型">
              <el-radio-group v-model="writeSettings.contentType">
                <el-radio-button label="opening">开头</el-radio-button>
                <el-radio-button label="scene">场景</el-radio-button>
                <el-radio-button label="dialogue">对话</el-radio-button>
                <el-radio-button label="ending">结尾</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="目标字数">
              <el-slider v-model="writeSettings.wordCount" :min="500" :max="3000" :step="100" show-stops />
              <span class="word-count-display">{{ writeSettings.wordCount }}字</span>
            </el-form-item>
            <el-form-item label="写作风格">
              <el-select v-model="writeSettings.style" placeholder="选择风格">
                <el-option label="创意独特" value="creative" />
                <el-option label="悬疑紧张" value="suspense" />
                <el-option label="温暖治愈" value="warm" />
                <el-option label="幽默轻松" value="humor" />
                <el-option label="史诗宏大" value="epic" />
              </el-select>
            </el-form-item>
          </el-form>
        </div>
        <div class="generated-content" v-if="generatedContent">
          <h4>生成的内容</h4>
          <div class="content-text" v-html="formatContent(generatedContent)"></div>
        </div>
      </div>
      <template #footer>
        <el-button @click="writeDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="generateWriting" :loading="writing">
          {{ generatedContent ? '重新生成' : '开始生成' }}
        </el-button>
        <el-button type="success" v-if="generatedContent" @click="copyContent">
          复制内容
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { MagicStick, Refresh } from '@element-plus/icons-vue'
import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000/api'

// 状态
const selectedMode = ref('random')
const creativeModes = ref([])
const creativeElements = ref([])
const keywordsInput = ref('')
const generating = ref(false)
const refreshing = ref(false)
const generatedIdeas = ref([])
const expandedIdeas = ref({})
const expandingIndex = ref(-1)
const showElements = ref(true)

// 写作对话框
const writeDialogVisible = ref(false)
const currentIdea = ref(null)
const writeSettings = ref({
  contentType: 'opening',
  wordCount: 1000,
  style: 'creative'
})
const generatedContent = ref('')
const writing = ref(false)

// 计算属性
const selectedIdeas = computed(() => {
  return generatedIdeas.value.filter(idea => idea.selected)
})

// 方法
const selectMode = (modeId) => {
  selectedMode.value = modeId
}

const getElementType = (element) => {
  if (element.includes('人物')) return 'danger'
  if (element.includes('场景')) return 'success'
  if (element.includes('物品')) return 'warning'
  if (element.includes('情境')) return 'primary'
  return 'info'
}

const formatElement = (element) => {
  return element.split(':')[1] || element
}

const fetchCreativeModes = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/brainstorm/modes`)
    creativeModes.value = response.data.modes
  } catch (error) {
    console.error('获取创意模式失败:', error)
  }
}

const fetchRandomElements = async () => {
  refreshing.value = true
  try {
    const response = await axios.get(`${API_BASE_URL}/brainstorm/elements?count=4`)
    creativeElements.value = response.data.elements
  } catch (error) {
    console.error('获取创意元素失败:', error)
  } finally {
    refreshing.value = false
  }
}

const refreshElements = () => {
  fetchRandomElements()
}

const generateIdeas = async () => {
  generating.value = true
  try {
    const keywords = keywordsInput.value
      .split(/[,，]/)
      .map(k => k.trim())
      .filter(k => k)

    const response = await axios.post(`${API_BASE_URL}/brainstorm/generate`, {
      mode: selectedMode.value,
      keywords: keywords.length > 0 ? keywords : undefined,
      count: 3
    })

    if (response.data.success) {
      generatedIdeas.value = response.data.ideas.map(idea => ({
        ...idea,
        selected: false,
        expansion: null
      }))
      expandedIdeas.value = {}
      ElMessage.success('创意生成成功！')
    }
  } catch (error) {
    console.error('生成创意失败:', error)
    ElMessage.error('生成创意失败，请重试')
  } finally {
    generating.value = false
  }
}

const isIdeaSelected = (idea) => {
  return idea.selected
}

const toggleIdeaSelection = (idea) => {
  idea.selected = !idea.selected
}

const expandIdea = async (idea, index) => {
  if (expandedIdeas.value[index]) {
    expandedIdeas.value[index] = false
    return
  }

  expandingIndex.value = index
  try {
    const response = await axios.post(`${API_BASE_URL}/brainstorm/expand`, {
      idea: idea,
      expansion_type: 'outline',
      detail_level: 'detailed'
    })

    if (response.data.success) {
      idea.expansion = response.data.expansion
      expandedIdeas.value[index] = true
    }
  } catch (error) {
    console.error('扩展创意失败:', error)
    ElMessage.error('扩展创意失败')
  } finally {
    expandingIndex.value = -1
  }
}

const expandAllIdeas = async () => {
  for (let i = 0; i < generatedIdeas.value.length; i++) {
    if (!generatedIdeas.value[i].expansion) {
      await expandIdea(generatedIdeas.value[i], i)
    }
  }
}

const remixIdeas = async () => {
  try {
    const response = await axios.post(`${API_BASE_URL}/brainstorm/remix`, {
      ideas: selectedIdeas.value
    })

    if (response.data.success) {
      generatedIdeas.value.push({
        ...response.data.remixed_idea,
        selected: false,
        expansion: null
      })
      ElMessage.success('创意混合成功！')
    }
  } catch (error) {
    console.error('混合创意失败:', error)
    ElMessage.error('混合创意失败')
  }
}

const writeContent = (idea) => {
  currentIdea.value = idea
  generatedContent.value = ''
  writeDialogVisible.value = true
}

const generateWriting = async () => {
  if (!currentIdea.value) return

  writing.value = true
  generatedContent.value = ''

  try {
    const response = await fetch(`${API_BASE_URL}/brainstorm/generate-stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        idea: currentIdea.value,
        content_type: writeSettings.value.contentType,
        word_count: writeSettings.value.wordCount,
        style: writeSettings.value.style
      })
    })

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
            if (data.content) {
              generatedContent.value += data.content
            }
          } catch (e) {
            // 忽略解析错误
          }
        }
      }
    }
  } catch (error) {
    console.error('生成内容失败:', error)
    ElMessage.error('生成内容失败')
  } finally {
    writing.value = false
  }
}

const formatContent = (content) => {
  return content.replace(/\n/g, '<br>')
}

const copyIdea = (idea) => {
  const text = `${idea.title}\n\n${idea.content}\n\n${idea.concept || ''}\n${idea.setting || ''}\n${idea.conflict || ''}`
  navigator.clipboard.writeText(text)
  ElMessage.success('已复制到剪贴板')
}

const copyContent = () => {
  navigator.clipboard.writeText(generatedContent.value)
  ElMessage.success('内容已复制')
}

// 初始化
onMounted(() => {
  fetchCreativeModes()
  fetchRandomElements()
})
</script>

<style scoped>
.brainstorm-writing {
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

.subsection-title {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 15px;
}

.mode-section {
  margin-bottom: 25px;
}

.mode-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.mode-card {
  padding: 15px;
  border: 2px solid #e4e7ed;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: center;
}

.mode-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.mode-card.active {
  background: #f5f7fa;
  border-width: 2px;
}

.mode-icon {
  font-size: 24px;
  display: block;
  margin-bottom: 8px;
}

.mode-name {
  font-weight: 500;
  color: #303133;
  display: block;
  margin-bottom: 4px;
}

.mode-desc {
  font-size: 12px;
  color: #909399;
}

.elements-section {
  margin-bottom: 25px;
}

.elements-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.elements-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.element-tag {
  font-size: 14px;
  padding: 8px 15px;
}

.keywords-section {
  margin-bottom: 25px;
}

.generate-section {
  text-align: center;
  margin-bottom: 30px;
}

.ideas-section {
  margin-top: 30px;
}

.ideas-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.ideas-actions {
  display: flex;
  gap: 10px;
}

.ideas-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.idea-card {
  border: 2px solid #e4e7ed;
  border-radius: 10px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.idea-card:hover {
  border-color: #409eff;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.1);
}

.idea-card.selected {
  border-color: #67c23a;
  background: #f0f9ff;
}

.idea-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.idea-select {
  flex-shrink: 0;
}

.idea-title {
  flex: 1;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.idea-tags {
  display: flex;
  gap: 5px;
}

.idea-content {
  color: #606266;
  margin-bottom: 12px;
  line-height: 1.6;
}

.idea-details {
  background: #f5f7fa;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 12px;
}

.detail-item {
  margin-bottom: 6px;
}

.detail-item:last-child {
  margin-bottom: 0;
}

.detail-label {
  font-weight: 500;
  color: #303133;
}

.detail-value {
  color: #606266;
}

.idea-directions {
  margin-bottom: 12px;
}

.directions-label {
  font-weight: 500;
  color: #303133;
  margin-right: 10px;
}

.direction-tag {
  margin-right: 5px;
  margin-bottom: 5px;
}

.idea-actions {
  display: flex;
  gap: 10px;
}

.expansion-content {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #e4e7ed;
}

.expansion-section {
  margin-bottom: 15px;
}

.expansion-section h5 {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.expansion-text {
  color: #606266;
  line-height: 1.6;
}

.character-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.character-item {
  background: white;
  padding: 10px;
  border-radius: 6px;
}

.character-item p {
  margin: 5px 0 0 0;
  color: #909399;
  font-size: 13px;
}

.write-dialog-content {
  max-height: 60vh;
  overflow-y: auto;
}

.write-settings {
  margin-bottom: 20px;
}

.word-count-display {
  margin-left: 15px;
  color: #606266;
}

.generated-content {
  border-top: 1px solid #e4e7ed;
  padding-top: 20px;
}

.generated-content h4 {
  margin-bottom: 15px;
}

.content-text {
  background: #f5f7fa;
  padding: 20px;
  border-radius: 8px;
  line-height: 1.8;
  color: #303133;
  max-height: 300px;
  overflow-y: auto;
}

@media (max-width: 768px) {
  .mode-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .ideas-header {
    flex-direction: column;
    gap: 10px;
    align-items: flex-start;
  }
}
</style>
