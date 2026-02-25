<template>
  <div class="ai-extract">
    <div class="extract-header">
      <h3>
        <el-icon><Magic /></el-icon>
        AI 智能提取
      </h3>
      <p class="subtitle">自动分析文档，提取角色、大纲等信息</p>
    </div>

    <div class="extract-actions">
      <el-button
        type="primary"
        size="large"
        @click="extractInfo"
        :loading="extracting"
        :disabled="contentLength < 100"
      >
        <el-icon><Aim /></el-icon>
        {{ extracting ? '分析中...' : '开始提取' }}
      </el-button>

      <el-button
        size="large"
        @click="analyzeStoryline"
        :loading="analyzingStory"
        :disabled="contentLength < 200"
      >
        <el-icon><TrendCharts /></el-icon>
        分析故事线
      </el-button>
    </div>

    <el-alert
      v-if="contentLength < 100"
      type="info"
      :closable="false"
      show-icon
    >
      文档内容需要至少 100 字才能进行 AI 提取
    </el-alert>

    <!-- 提取结果 -->
    <div v-if="extractedData" class="extract-results">
      <div class="result-section" v-if="extractedData.characters?.length">
        <h4>
          <el-icon><User /></el-icon>
          角色设定 ({{ extractedData.characters.length }})
        </h4>
        <div class="characters-list">
          <div
            v-for="(char, index) in extractedData.characters"
            :key="index"
            class="character-card"
          >
            <div class="char-name">{{ char.name }}</div>
            <div class="char-desc">{{ char.description }}</div>
            <div v-if="char.personality" class="char-attr">
              <span class="attr-label">性格:</span> {{ char.personality }}
            </div>
            <div v-if="char.goals" class="char-attr">
              <span class="attr-label">目标:</span> {{ char.goals }}
            </div>
          </div>
        </div>
      </div>

      <div class="result-section" v-if="extractedData.outline?.length">
        <h4>
          <el-icon><List /></el-icon>
          大纲结构 ({{ extractedData.outline.length }})
        </h4>
        <div class="outline-list">
          <div
            v-for="(item, index) in extractedData.outline"
            :key="index"
            class="outline-item"
          >
            <span class="outline-num">{{ index + 1 }}</span>
            <div class="outline-content">
              <div class="outline-title">{{ item.title }}</div>
              <div class="outline-desc">{{ item.description }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="result-section" v-if="extractedData.key_points?.length">
        <h4>
          <el-icon><Star /></el-icon>
          关键情节 ({{ extractedData.key_points.length }})
        </h4>
        <ul class="key-points">
          <li v-for="(point, index) in extractedData.key_points" :key="index">
            {{ point }}
          </li>
        </ul>
      </div>

      <div class="result-section" v-if="extractedData.world_building && Object.keys(extractedData.world_building).length">
        <h4>
          <el-icon><MapLocation /></el-icon>
          世界观元素
        </h4>
        <div class="world-building">
          <div
            v-for="(value, key) in extractedData.world_building"
            :key="key"
            class="world-item"
          >
            <span class="world-key">{{ key }}:</span>
            <span class="world-value">{{ value }}</span>
          </div>
        </div>
      </div>

      <div class="result-section" v-if="extractedData.writing_style">
        <h4>
          <el-icon><EditPen /></el-icon>
          写作风格
        </h4>
        <p class="writing-style">{{ extractedData.writing_style }}</p>
      </div>

      <div class="apply-actions" v-if="hasExtractedContent">
        <el-button type="primary" size="large" @click="applyToMemory" :loading="applying">
          <el-icon><Check /></el-icon>
          应用到项目设定
        </el-button>
        <el-button size="large" @click="extractedData = null">
          重新提取
        </el-button>
      </div>
    </div>

    <!-- 故事线分析结果 -->
    <div v-if="storyline" class="storyline-result">
      <h4>故事线分析</h4>
      <div class="storyline-content">{{ storyline }}</div>
      <div class="apply-actions">
        <el-button type="primary" @click="applyStoryline">
          应用到故事线
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { extractApi } from '@/api/extract'
import { Magic, Aim, TrendCharts, User, List, Star, MapLocation, EditPen, Check } from '@element-plus/icons-vue'

const props = defineProps<{
  documentId: number
  projectId: number
  content: any[]
}>()

const extracting = ref(false)
const analyzingStory = ref(false)
const applying = ref(false)
const extractedData = ref<any>(null)
const storyline = ref('')

const contentLength = computed(() => {
  return props.content.reduce((acc, block) => acc + (block.content?.length || 0), 0)
})

const hasExtractedContent = computed(() => {
  if (!extractedData.value) return false
  const d = extractedData.value
  return d.characters?.length || d.outline?.length || d.key_points?.length ||
         (d.world_building && Object.keys(d.world_building).length) || d.writing_style
})

async function extractInfo() {
  extracting.value = true
  try {
    const res = await extractApi.extract(props.documentId)
    extractedData.value = res.data.extracted
    ElMessage.success('提取完成')
  } catch (error) {
    ElMessage.error('提取失败')
  } finally {
    extracting.value = false
  }
}

async function analyzeStoryline() {
  analyzingStory.value = true
  try {
    const res = await extractApi.analyzeStoryline(props.documentId)
    storyline.value = res.data.storyline
    ElMessage.success('分析完成')
  } catch (error) {
    ElMessage.error('分析失败')
  } finally {
    analyzingStory.value = false
  }
}

async function applyToMemory() {
  applying.value = true
  try {
    await extractApi.apply(props.documentId, {
      extracted: extractedData.value
    })
    ElMessage.success('已应用到项目设定')
    emit('applied')
  } catch (error) {
    ElMessage.error('应用失败')
  } finally {
    applying.value = false
  }
}

async function applyStoryline() {
  try {
    await extractApi.analyzeStoryline(props.documentId)
    ElMessage.success('故事线已保存')
    emit('applied')
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const emit = defineEmits<{
  (e: 'applied'): void
}>()
</script>

<style scoped lang="scss">
.ai-extract {
  padding: 20px;
}

.extract-header {
  text-align: center;
  margin-bottom: 24px;

  h3 {
    font-size: 18px;
    color: var(--coffee-text);
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;

    .el-icon {
      color: var(--coffee-primary);
    }
  }

  .subtitle {
    font-size: 14px;
    color: var(--coffee-text-muted);
  }
}

.extract-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-bottom: 20px;
}

.extract-results {
  margin-top: 24px;
}

.result-section {
  margin-bottom: 24px;

  h4 {
    font-size: 15px;
    color: var(--coffee-text);
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 6px;

    .el-icon {
      color: var(--coffee-primary);
    }
  }
}

.characters-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.character-card {
  background: var(--coffee-bg-warm);
  border-radius: 10px;
  padding: 12px 16px;

  .char-name {
    font-weight: 600;
    color: var(--coffee-primary);
    margin-bottom: 6px;
  }

  .char-desc {
    font-size: 13px;
    color: var(--coffee-text-secondary);
    margin-bottom: 8px;
  }

  .char-attr {
    font-size: 12px;
    color: var(--coffee-text-muted);

    .attr-label {
      font-weight: 500;
      color: var(--coffee-text);
    }
  }
}

.outline-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.outline-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 10px 12px;
  background: var(--coffee-bg-warm);
  border-radius: 8px;

  .outline-num {
    width: 24px;
    height: 24px;
    background: var(--coffee-primary);
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 600;
    flex-shrink: 0;
  }

  .outline-content {
    flex: 1;

    .outline-title {
      font-weight: 500;
      color: var(--coffee-text);
      margin-bottom: 2px;
    }

    .outline-desc {
      font-size: 12px;
      color: var(--coffee-text-muted);
    }
  }
}

.key-points {
  margin: 0;
  padding-left: 20px;

  li {
    margin-bottom: 8px;
    color: var(--coffee-text-secondary);
    line-height: 1.6;
  }
}

.world-building {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.world-item {
  padding: 10px 12px;
  background: var(--coffee-bg-warm);
  border-radius: 6px;

  .world-key {
    font-weight: 500;
    color: var(--coffee-primary);
    margin-right: 8px;
  }

  .world-value {
    color: var(--coffee-text-secondary);
  }
}

.writing-style {
  padding: 12px;
  background: var(--coffee-bg-warm);
  border-radius: 8px;
  color: var(--coffee-text-secondary);
  line-height: 1.6;
  font-style: italic;
}

.apply-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--coffee-border);
}

.storyline-result {
  margin-top: 24px;
  padding: 20px;
  background: var(--coffee-bg-warm);
  border-radius: 12px;

  h4 {
    font-size: 15px;
    color: var(--coffee-text);
    margin-bottom: 12px;
  }

  .storyline-content {
    color: var(--coffee-text-secondary);
    line-height: 1.8;
    white-space: pre-wrap;
    margin-bottom: 16px;
  }
}
</style>
