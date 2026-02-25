<template>
  <div class="template-library">
    <div class="template-header">
      <h2>
        <el-icon><Collection /></el-icon>
        模板库
      </h2>
      <p class="subtitle">选择模板快速开始创作</p>
    </div>

    <div class="template-categories">
      <el-radio-group v-model="selectedCategory" size="large">
        <el-radio-button label="all">全部</el-radio-button>
        <el-radio-button label="novel">小说</el-radio-button>
        <el-radio-button label="blog">博客</el-radio-button>
        <el-radio-button label="work">工作</el-radio-button>
      </el-radio-group>
    </div>

    <div class="template-stats">
      <span class="stat-item">📚 共 {{ templates.length }} 个模板</span>
      <span class="stat-item" v-if="selectedCategory !== 'all'">
        · {{ getCategoryName(selectedCategory) }}类 {{ filteredTemplates.length }} 个
      </span>
    </div>

    <div class="templates-grid">
      <div
        v-for="template in filteredTemplates"
        :key="template.id"
        class="template-card"
        @click="previewTemplate(template)"
      >
        <div class="template-icon">{{ template.icon }}</div>
        <h3 class="template-name">{{ template.name }}</h3>
        <p class="template-desc">{{ template.description }}</p>
        <div class="template-meta">
          <span class="template-category">{{ getCategoryName(template.category) }}</span>
          <el-tag v-if="template.is_system" size="small" type="info">系统</el-tag>
        </div>
      </div>
    </div>

    <!-- 模板预览对话框 -->
    <el-dialog
      v-model="showPreview"
      :title="`预览：${selectedTemplate?.name}`"
      width="600px"
      class="template-dialog"
    >
      <div v-if="selectedTemplate" class="template-preview">
        <div class="preview-section" v-if="selectedTemplate.outline?.length">
          <h4>📋 大纲结构</h4>
          <div class="outline-list">
            <div
              v-for="(item, index) in selectedTemplate.outline"
              :key="index"
              class="outline-item"
            >
              <span class="outline-number">{{ index + 1 }}</span>
              <div class="outline-content">
                <div class="outline-title">{{ item.title }}</div>
                <div class="outline-desc">{{ item.description }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="preview-section" v-if="selectedTemplate.world_building && Object.keys(selectedTemplate.world_building).length">
          <h4>🌍 世界观设定</h4>
          <div class="world-building">
            <div
              v-for="(value, key) in selectedTemplate.world_building"
              :key="key"
              class="world-item"
            >
              <span class="world-key">{{ key }}:</span>
              <span class="world-value">{{ value }}</span>
            </div>
          </div>
        </div>

        <div class="preview-section" v-if="selectedTemplate.writing_style">
          <h4>✍️ 写作风格</h4>
          <p class="writing-style">{{ selectedTemplate.writing_style }}</p>
        </div>
      </div>

      <template #footer>
        <el-button @click="showPreview = false">
          {{ targetProjectId ? '取消' : '关闭' }}
        </el-button>
        <el-button type="primary" @click="applyTemplate" :loading="applying">
          {{ targetProjectId ? '导入到当前项目' : '使用此模板' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 使用模板对话框 - 选择创建新项目或导入到已有项目 -->
    <el-dialog
      v-model="showApplyDialog"
      title="使用模板"
      width="420px"
    >
      <div class="apply-mode-tabs">
        <el-radio-group v-model="applyMode" size="large">
          <el-radio-button label="new">创建新项目</el-radio-button>
          <el-radio-button label="existing">导入已有项目</el-radio-button>
        </el-radio-group>
      </div>

      <!-- 创建新项目 -->
      <div v-if="applyMode === 'new'" class="apply-form">
        <el-form label-width="80px">
          <el-form-item label="项目名称">
            <el-input
              v-model="newProjectName"
              placeholder="输入项目名称"
            />
          </el-form-item>
        </el-form>
      </div>

      <!-- 导入到已有项目 -->
      <div v-else class="apply-form">
        <el-form label-width="80px">
          <el-form-item label="选择项目">
            <el-select
              v-model="selectedProjectId"
              placeholder="选择一个已有项目"
              style="width: 100%"
            >
              <el-option
                v-for="project in myProjects"
                :key="project.id"
                :label="project.title"
                :value="project.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-alert
              title="导入说明"
              type="info"
              :closable="false"
              description="模板的大纲将追加到项目文档，世界观和设定会与现有内容合并"
              show-icon
            />
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <el-button @click="showApplyDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmApply" :loading="applying">
          {{ applyMode === 'new' ? '创建项目' : '导入模板' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { templateApi } from '@/api/template'
import { useProjectStore } from '@/stores/project'
import { Collection } from '@element-plus/icons-vue'

const router = useRouter()
const projectStore = useProjectStore()

// 组件属性
const props = defineProps<{
  targetProjectId?: number  // 如果传入，则直接导入到该项目；否则显示选择对话框
}>()

const emit = defineEmits<{
  (e: 'select'): void
  (e: 'import', projectId: number): void
  (e: 'cancel'): void
}>()

const templates = ref<any[]>([])
const selectedCategory = ref('all')
const showPreview = ref(false)
const showApplyDialog = ref(false)
const selectedTemplate = ref<any>(null)
const newProjectName = ref('')
const applying = ref(false)
const applyMode = ref<'new' | 'existing'>('new')
const selectedProjectId = ref<number | null>(null)

// 用户项目列表
const myProjects = computed(() => projectStore.projectList)

const filteredTemplates = computed(() => {
  if (selectedCategory.value === 'all') {
    return templates.value
  }
  return templates.value.filter(t => t.category === selectedCategory.value)
})

onMounted(() => {
  loadTemplates()
})

async function loadTemplates() {
  try {
    const res = await templateApi.list()
    templates.value = res.data
  } catch (error) {
    ElMessage.error('加载模板失败')
  }
}

function getCategoryName(category: string) {
  const names: Record<string, string> = {
    novel: '小说',
    blog: '博客',
    work: '工作'
  }
  return names[category] || category
}

function previewTemplate(template: any) {
  selectedTemplate.value = template
  showPreview.value = true
}

function applyTemplate() {
  if (!selectedTemplate.value) return
  
  // 如果传入了目标项目ID，直接导入而不显示对话框
  if (props.targetProjectId) {
    confirmApply()
    return
  }
  
  newProjectName.value = `${selectedTemplate.value.name}项目`
  applyMode.value = 'new'
  selectedProjectId.value = null
  showApplyDialog.value = true
}

async function confirmApply() {
  if (!selectedTemplate.value) return
  
  applying.value = true
  
  // 如果传入了目标项目ID，直接导入到该项目
  if (props.targetProjectId) {
    try {
      const res = await templateApi.importToProject(
        selectedTemplate.value.id,
        props.targetProjectId
      )
      ElMessage.success(`模板导入成功，已添加 ${res.data.documents_added} 个文档`)
      showPreview.value = false
      showApplyDialog.value = false
      
      // 通知父组件
      emit('select')
      emit('import', props.targetProjectId)
    } catch (error) {
      ElMessage.error('导入模板失败')
    }
    applying.value = false
    return
  }
  
  if (applyMode.value === 'new') {
    // 创建新项目
    try {
      const res = await templateApi.apply(selectedTemplate.value.id, {
        project_name: newProjectName.value
      })
      ElMessage.success('项目创建成功')
      showPreview.value = false
      showApplyDialog.value = false
      
      // 通知父组件
      emit('select')
      
      // 跳转到新项目
      router.push(`/project/${res.data.project_id}`)
    } catch (error) {
      ElMessage.error('创建项目失败')
    }
  } else {
    // 导入到已有项目
    if (!selectedProjectId.value) {
      ElMessage.warning('请选择一个项目')
      applying.value = false
      return
    }
    
    try {
      const res = await templateApi.importToProject(
        selectedTemplate.value.id,
        selectedProjectId.value
      )
      ElMessage.success(`模板导入成功，已添加 ${res.data.documents_added} 个文档`)
      showPreview.value = false
      showApplyDialog.value = false
      
      // 通知父组件
      emit('select')
      emit('import', selectedProjectId.value)
      
      // 跳转到项目
      router.push(`/project/${selectedProjectId.value}`)
    } catch (error) {
      ElMessage.error('导入模板失败')
    }
  }
  
  applying.value = false
}
</script>

<style scoped lang="scss">
.template-library {
  padding: 24px;
}

.template-header {
  text-align: center;
  margin-bottom: 32px;

  h2 {
    font-size: 24px;
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
    color: var(--coffee-text-muted);
  }
}

.template-categories {
  display: flex;
  justify-content: center;
  margin-bottom: 12px;
}

.template-stats {
  text-align: center;
  margin-bottom: 24px;
  color: var(--coffee-text-muted);
  font-size: 14px;

  .stat-item {
    margin: 0 8px;
  }
}

.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 20px;
}

.template-card {
  background: var(--coffee-bg-card);
  border-radius: 16px;
  padding: 24px;
  border: 1px solid var(--coffee-border);
  cursor: pointer;
  transition: all 0.3s ease;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 32px var(--coffee-shadow-hover);
    border-color: var(--coffee-primary-light);
  }

  .template-icon {
    font-size: 48px;
    margin-bottom: 16px;
  }

  .template-name {
    font-size: 18px;
    font-weight: 600;
    color: var(--coffee-text);
    margin-bottom: 8px;
  }

  .template-desc {
    font-size: 14px;
    color: var(--coffee-text-muted);
    margin-bottom: 16px;
    line-height: 1.5;
  }

  .template-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .template-category {
      font-size: 12px;
      color: var(--coffee-text-light);
      padding: 4px 10px;
      background: var(--coffee-bg-warm);
      border-radius: 12px;
    }
  }
}

.template-preview {
  max-height: 500px;
  overflow-y: auto;
}

.preview-section {
  margin-bottom: 24px;

  h4 {
    font-size: 16px;
    color: var(--coffee-text);
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--coffee-border-light);
  }
}

.outline-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.outline-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  background: var(--coffee-bg-warm);
  border-radius: 8px;

  .outline-number {
    width: 28px;
    height: 28px;
    background: var(--coffee-gradient-primary);
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 600;
    flex-shrink: 0;
  }

  .outline-content {
    flex: 1;

    .outline-title {
      font-weight: 500;
      color: var(--coffee-text);
      margin-bottom: 4px;
    }

    .outline-desc {
      font-size: 13px;
      color: var(--coffee-text-muted);
    }
  }
}

.world-building {
  display: flex;
  flex-direction: column;
  gap: 8px;

  .world-item {
    padding: 8px 12px;
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
}

.writing-style {
  padding: 12px;
  background: var(--coffee-bg-warm);
  border-radius: 8px;
  color: var(--coffee-text-secondary);
  line-height: 1.6;
}

.apply-mode-tabs {
  display: flex;
  justify-content: center;
  margin-bottom: 20px;
}

.apply-form {
  padding: 0 10px;
}
</style>
