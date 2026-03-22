<template>
  <div class="ai-extract">
    <div class="extract-header">
      <h3>
        <el-icon><MagicStick /></el-icon>
        AI 智能扩展
      </h3>
      <p class="subtitle">分析当前文章并扩展成长篇项目（生成大纲/项目设定）</p>
    </div>

    <div class="extend-mode">
      <el-radio-group v-model="extendMode" size="large">
        <el-radio-button label="new">新建项目</el-radio-button>
        <el-radio-button label="overwrite">覆盖当前项目设定</el-radio-button>
      </el-radio-group>
    </div>

    <div class="extract-actions">
      <el-button
        type="primary"
        size="large"
        @click="expandToProject"
        :loading="expanding"
        :disabled="contentLength < 100"
      >
        <el-icon><Aim /></el-icon>
        {{ expanding ? '生成项目中...' : '开始扩展' }}
      </el-button>
    </div>

    <el-alert
      v-if="contentLength < 100"
      type="info"
      :closable="false"
      show-icon
    >
      文档内容需要至少 100 字才能扩展生成长篇项目
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
        <el-button
          type="primary"
          size="large"
          @click="goToProject"
          :loading="createdProjectLoading"
          v-if="createdProject?.project_id && createdDocumentId"
        >
          <el-icon><Check /></el-icon>
          {{ extendMode === 'new' ? '进入新项目文档' : '进入文档' }}
        </el-button>
        <el-button size="large" @click="resetAll" v-else>
          重新生成
        </el-button>
      </div>
    </div>

    <!-- 故事主线（可选） -->
    <div v-if="extractedData?.storyline" class="storyline-result">
      <h4>故事主线</h4>
      <div class="storyline-content">{{ extractedData.storyline }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { aiApi, documentApi } from '@/api'
import { MagicStick, Aim, User, List, Star, MapLocation, EditPen, Check } from '@element-plus/icons-vue'

const props = defineProps<{
  documentId: number
  projectId: number
  documentTitle?: string
  content: any[]
}>()

const extractedData = ref<any>(null)
const createdProject = ref<any>(null)
const createdDocumentId = ref<number | null>(null)
const extendMode = ref<'new' | 'overwrite'>('new')
const expanding = ref(false)
const createdProjectLoading = ref(false)

const contentLength = computed(() => {
  return props.content.reduce((acc, block) => acc + (block.content?.length || 0), 0)
})

const hasExtractedContent = computed(() => {
  if (!extractedData.value) return false
  return true
})

async function expandToProject() {
  expanding.value = true
  createdProject.value = null
  createdDocumentId.value = null
  try {
    const contentText = (props.content || [])
      .map(b => b?.content)
      .filter(Boolean)
      .join('\n')

    const analysisRes = await aiApi.analyzeLiterature({
      content: contentText,
      title: props.documentTitle || undefined,
      category: 'novel',
    })

    extractedData.value = analysisRes.data
    const baseTitle = (props.documentTitle || '').trim() || '未命名文章'
    const markerHeading = `【原文】${baseTitle}`
    const newDocTitle = extendMode.value === 'overwrite'
      ? `【原文】${baseTitle}（覆盖设定）`
      : `【原文】${baseTitle}`

    let targetProjectId = props.projectId

    if (extendMode.value === 'new') {
      const createRes = await aiApi.createProjectFromLiterature({
        analysis: extractedData.value
      })

      createdProject.value = createRes.data
      extractedData.value = createdProject.value?.analysis || extractedData.value
      targetProjectId = createdProject.value.project_id
    } else {
      const applyRes = await aiApi.applyProjectFromLiterature({
        project_id: props.projectId,
        analysis: extractedData.value
      })

      createdProject.value = { project_id: props.projectId }
      // 后端会兜底生成长篇 outline，这里尽量用返回的 analysis 刷新展示
      extractedData.value = applyRes?.data?.analysis || extractedData.value
      targetProjectId = props.projectId
    }

    const normalizeBlock = (b: any) => {
      const id = b?.id ? String(b.id) : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`
      return {
        id: crypto.randomUUID ? crypto.randomUUID() : id,
        type: b?.type || 'paragraph',
        content: typeof b?.content === 'string' ? b.content : '',
        props: b?.props && typeof b.props === 'object' ? { ...b.props } : {},
      }
    }

    const originalBlocks = (props.content || []).map(normalizeBlock)

    // 只在开头标识“原文”，避免影响后续“续写当前文档”的上下文（上下文取末尾 2000 字）。
    const markerBlocks = [
      {
        id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now().toString(36)}-marker-start`,
        type: 'heading',
        content: markerHeading,
        props: {},
      },
      {
        id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now().toString(36)}-marker-desc`,
        type: 'paragraph',
        content: '以下为从当前文章导入的原文内容，可基于此继续扩写成长篇项目。',
        props: {},
      },
      {
        id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now().toString(36)}-marker-divider`,
        type: 'divider',
        content: '',
        props: {},
      },
    ]

    const createdDoc = await documentApi.create(targetProjectId, {
      title: newDocTitle,
      content: [...markerBlocks, ...originalBlocks],
    })

    createdDocumentId.value = createdDoc.data?.id ?? createdDoc.id ?? null
    ElMessage.success(
      extendMode.value === 'new'
        ? '长篇项目已创建，并已导入原文到新文档'
        : '已覆盖项目设定，并已导入原文到新文档'
    )
  } catch (error) {
    ElMessage.error('扩展生成失败')
  } finally {
    expanding.value = false
  }
}

function goToProject() {
  if (!createdProject.value?.project_id || !createdDocumentId.value) return
  createdProjectLoading.value = true
  emit('project-created', createdProject.value.project_id, createdDocumentId.value)
  // 让父组件路由跳转时销毁该抽屉；这里不阻塞
  setTimeout(() => {
    createdProjectLoading.value = false
  }, 300)
}

function resetAll() {
  extractedData.value = null
  createdProject.value = null
  createdDocumentId.value = null
}

const emit = defineEmits<{
  (e: 'project-created', projectId: number, documentId: number): void
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

.extend-mode {
  display: flex;
  justify-content: center;
  margin-bottom: 18px;

  :deep(.el-radio-button__inner) {
    padding: 10px 16px;
  }
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
