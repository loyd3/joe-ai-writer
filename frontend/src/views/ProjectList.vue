<template>
  <div class="project-list-page">
    <div class="page-header">
      <div class="header-content">
        <h1>我的创作空间</h1>
        <p class="subtitle">在这里记录您的灵感与故事</p>
      </div>
      <div class="header-actions">
        <!-- <el-button type="primary" class="action-btn" @click="showTemplateLibrary = true">
          <el-icon><Collection /></el-icon>
          <span>从模板开始</span>
        </el-button> -->
        <!-- <el-button class="action-btn" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon>
          <span>新建项目</span>
        </el-button> -->
      </div>
    </div>
    
    <div v-if="projects.length > 0" class="projects-grid">
      <el-row :gutter="24">
        <!-- 创建新项目卡片 -->
        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <div class="project-card create-card" @click="showCreateDialog = true">
            <div class="create-content">
              <el-icon class="create-icon"><Plus /></el-icon>
              <span>创建空白项目</span>
            </div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <div class="project-card create-card template-card-entry" @click="showTemplateLibrary = true">
            <div class="create-content">
              <el-icon class="create-icon template-icon"><Collection /></el-icon>
              <span>从模板开始</span>
              <small>18个预设模板</small>
            </div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="8" :lg="6" v-for="project in projects" :key="project.id">
          <div class="project-card" @click="openProject(project.id)">
            <div class="card-header">
              <div class="project-icon">
                <el-icon><Document /></el-icon>
              </div>
              <el-dropdown trigger="click" @command="(cmd) => handleCommand(cmd, project)">
                <el-icon class="more-btn" @click.stop><MoreFilled /></el-icon>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="edit">
                      <el-icon><Edit /></el-icon> 编辑
                    </el-dropdown-item>
                    <el-dropdown-item command="delete" divided class="delete-item">
                      <el-icon><Delete /></el-icon> 删除
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
            <div class="card-body">
              <h3 class="project-title">{{ project.title }}</h3>
              <p class="project-desc">{{ project.description || '暂无描述' }}</p>
            </div>
            <div class="card-footer">
              <div class="meta-item">
                <el-icon><Calendar /></el-icon>
                <span>{{ formatDate(project.updated_at) }}</span>
              </div>
              <div class="meta-item">
                <el-icon><Document /></el-icon>
                <span>{{ project.documents?.length || 0 }} 篇</span>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>
    
    <div v-else class="empty-state">
      <div class="empty-illustration">
        <el-icon><EditPen /></el-icon>
      </div>
      <h2>开启您的创作之旅</h2>
      <p>创建第一个项目，开始记录您的灵感</p>
      <div class="empty-actions">
        <el-button type="primary" size="large" @click="showTemplateLibrary = true">
          <el-icon><Collection /></el-icon> 从模板开始
        </el-button>
        <el-button size="large" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon> 创建空白项目
        </el-button>
      </div>
    </div>

    <!-- 模板库对话框 -->
    <el-dialog
      v-model="showTemplateLibrary"
      title="选择模板"
      width="900px"
      class="template-dialog"
      :destroy-on-close="true"
    >
      <TemplateLibrary @select="onTemplateSelect" />
    </el-dialog>

    <!-- 创建/编辑项目对话框 -->
    <el-dialog 
      v-model="showCreateDialog" 
      :title="editingProject ? '编辑项目' : '新建项目'" 
      width="460px"
      class="coffee-dialog"
    >
      <el-form :model="form" label-width="80px" class="coffee-form">
        <el-form-item label="项目名称">
          <el-input 
            v-model="form.title" 
            placeholder="为您的项目取一个名字"
            maxlength="50"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="项目描述">
          <el-input 
            v-model="form.description" 
            type="textarea" 
            :rows="4"
            placeholder="描述一下这个项目的内容..."
            maxlength="200"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="saveProject" :loading="saving">
          {{ editingProject ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectStore, type Project } from '@/stores/project'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Document, MoreFilled, Edit, Delete, Calendar, EditPen, Collection } from '@element-plus/icons-vue'
import TemplateLibrary from '@/components/TemplateLibrary.vue'

const router = useRouter()
const store = useProjectStore()

const projects = computed(() => store.projectList)
const showCreateDialog = ref(false)
const showTemplateLibrary = ref(false)
const editingProject = ref<Project | null>(null)
const saving = ref(false)
const form = ref({
  title: '',
  description: ''
})

function onTemplateSelect() {
  showTemplateLibrary.value = false
  store.fetchProjects() // 刷新项目列表
}

onMounted(() => {
  store.fetchProjects()
})

function formatDate(date: string) {
  const d = new Date(date)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function openProject(id: number) {
  router.push(`/project/${id}`)
}

function handleCommand(cmd: string, project: Project) {
  if (cmd === 'edit') {
    editingProject.value = project
    form.value = {
      title: project.title,
      description: project.description || ''
    }
    showCreateDialog.value = true
  } else if (cmd === 'delete') {
    ElMessageBox.confirm(
      `确定要删除项目 "${project.title}" 吗？此操作不可恢复。`,
      '删除项目',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    ).then(async () => {
      await store.deleteProject(project.id)
      ElMessage.success('项目已删除')
    })
  }
}

async function saveProject() {
  if (!form.value.title.trim()) {
    ElMessage.warning('请输入项目名称')
    return
  }
  
  saving.value = true
  try {
    if (editingProject.value) {
      await store.updateProject(editingProject.value.id, form.value)
      ElMessage.success('项目已更新')
    } else {
      await store.createProject(form.value)
      ElMessage.success('项目创建成功')
    }
    showCreateDialog.value = false
    editingProject.value = null
    form.value = { title: '', description: '' }
  } finally {
    saving.value = false
  }
}
</script>

<style scoped lang="scss">
.project-list-page {
  padding: 40px;
  max-width: 1400px;
  margin: 0 auto;
  min-height: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 40px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--coffee-border);
  
  .header-content {
    h1 {
      font-size: 32px;
      font-weight: 700;
      color: var(--coffee-text);
      margin-bottom: 8px;
      letter-spacing: 1px;
    }
    
    .subtitle {
      font-size: 15px;
      color: var(--coffee-text-muted);
      font-style: italic;
    }
  }
  
  .header-actions {
    display: flex;
    gap: 12px;
  }
  
  .action-btn {
    height: 40px;
    padding: 0 20px;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.3s ease;
    
    &.el-button--primary {
      background: var(--coffee-gradient-primary);
      border: none;
    }
    
    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 16px var(--coffee-selection);
    }
    
    .el-icon {
      margin-right: 6px;
    }
  }
}

.projects-grid {
  margin-top: 8px;
  gap: 10px;
}

.project-card {
  background: var(--coffee-bg-card);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 20px var(--coffee-bg-hover);
  border: 1px solid var(--coffee-border-light);
  cursor: pointer;
  transition: all 0.3s ease;
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 200px;
  
  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 32px rgba(var(--coffee-primary-rgb), 0.12);
    border-color: var(--coffee-border);
  }

  &.create-card {
    background: var(--coffee-bg);
    border: 2px dashed var(--coffee-border);
    display: flex;
    align-items: center;
    justify-content: center;
    
    &:hover {

    }
    
    &.template-card-entry {
      background: var(--coffee-bg-warm);
      
      &:hover {

      }
      
      .template-icon {
        color: var(--coffee-primary);
      }
      
      small {
        display: block;
        margin-top: 4px;
        font-size: 12px;
        color: var(--coffee-text-muted);
      }
    }
    
    .create-content {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
      color: var(--coffee-text-muted);
      font-size: 15px;
      font-weight: 500;
      
      .create-icon {
        font-size: 40px;
        color: var(--coffee-text-light);
      }
    }
  }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    
    .project-icon {
      width: 48px;
      height: 48px;
      background: var(--coffee-gradient-light);
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      
      .el-icon {
        font-size: 24px;
        color: var(--coffee-primary);
      }
    }
    
    .more-btn {
      font-size: 18px;
      color: var(--coffee-text-light);
      padding: 6px;
      border-radius: 6px;
      transition: all 0.2s;
      opacity: 0;
      
      &:hover {
        background: var(--coffee-shadow);
        color: var(--coffee-primary);
      }
    }
  }
  
  &:hover .more-btn {
    opacity: 1;
  }
  
  .card-body {
    flex: 1;
    
    .project-title {
      font-size: 18px;
      font-weight: 600;
      color: var(--coffee-text);
      margin-bottom: 8px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    
    .project-desc {
      font-size: 14px;
      color: var(--coffee-text-muted);
      line-height: 1.6;
      overflow: hidden;
      text-overflow: ellipsis;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      min-height: 44px;
    }
  }
  
  .card-footer {
    display: flex;
    gap: 16px;
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid var(--coffee-divider);
    
    .meta-item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      color: var(--coffee-text-light);
      
      .el-icon {
        font-size: 14px;
      }
    }
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
  
  .empty-illustration {
    width: 120px;
    height: 120px;
    background: var(--coffee-gradient-light);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 24px;
    
    .el-icon {
      font-size: 56px;
      color: var(--coffee-primary-light);
    }
  }
  
  h2 {
    font-size: 24px;
    font-weight: 600;
    color: var(--coffee-text);
    margin-bottom: 8px;
  }
  
  p {
    font-size: 15px;
    color: var(--coffee-text-muted);
    margin-bottom: 24px;
  }
  
  .empty-actions {
    display: flex;
    gap: 16px;
    
    .el-button {
      height: 48px;
      padding: 0 32px;
      border-radius: 12px;
      font-size: 15px;
      
      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(var(--coffee-primary-rgb), 0.3);
      }
    }
  }
}

/* 对话框样式 */
:deep(.coffee-dialog) {
  .el-dialog__header {
    padding: 20px 24px;
    border-bottom: 1px solid var(--coffee-border-light);
    
    .el-dialog__title {
      font-weight: 600;
      color: var(--coffee-text);
    }
  }
  
  .el-dialog__body {
    padding: 24px;
  }
  
  .el-dialog__footer {
    padding: 16px 24px;
    border-top: 1px solid var(--coffee-border-light);
  }
}

.coffee-form {
  .el-input__wrapper,
  .el-textarea__inner {
    background: var(--coffee-bg);
    border-color: var(--coffee-border);
    
    &:focus {
      border-color: var(--coffee-primary-light);
    }
  }
}

:deep(.delete-item) {
  color: #f56c6c;
}

@media (max-width: 768px) {
  .project-list-page {
    padding: 24px;
  }
  
  .page-header {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start;
    
    h1 {
      font-size: 24px;
    }
  }
}
</style>
