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
  border-bottom: 1px solid #e8dcd0;
  
  .header-content {
    h1 {
      font-size: 32px;
      font-weight: 700;
      color: #4a2c17;
      margin-bottom: 8px;
      letter-spacing: 1px;
    }
    
    .subtitle {
      font-size: 15px;
      color: #a67c52;
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
      background: linear-gradient(135deg, #a65e2e 0%, #c97f4a 100%);
      border: none;
    }
    
    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 16px rgba(166, 94, 46, 0.25);
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
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(74, 44, 23, 0.06);
  border: 1px solid #f2e9e0;
  cursor: pointer;
  transition: all 0.3s ease;
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 200px;
  
  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 32px rgba(74, 44, 23, 0.12);
    border-color: #e0d4c4;
  }

  &.create-card {
    background: linear-gradient(135deg, #fdfbf7 0%, #f5ebe0 100%);
    border: 2px dashed #d4c4b0;
    display: flex;
    align-items: center;
    justify-content: center;
    
    &:hover {
      border-color: #c97f4a;
      background: linear-gradient(135deg, #f5ebe0 0%, #f2dec8 100%);
    }
    
    &.template-card-entry {
      background: linear-gradient(135deg, #f8f4ef 0%, #ebe4d8 100%);
      
      &:hover {
        background: linear-gradient(135deg, #f2ebe0 0%, #e5dcc8 100%);
      }
      
      .template-icon {
        color: #a65e2e;
      }
      
      small {
        display: block;
        margin-top: 4px;
        font-size: 12px;
        color: #a67c52;
      }
    }
    
    .create-content {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
      color: #8b7355;
      font-size: 15px;
      font-weight: 500;
      
      .create-icon {
        font-size: 40px;
        color: #c9a86c;
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
      background: linear-gradient(135deg, #f5ebe0 0%, #f2dec8 100%);
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      
      .el-icon {
        font-size: 24px;
        color: #a65e2e;
      }
    }
    
    .more-btn {
      font-size: 18px;
      color: #c9a86c;
      padding: 6px;
      border-radius: 6px;
      transition: all 0.2s;
      opacity: 0;
      
      &:hover {
        background: rgba(166, 94, 46, 0.08);
        color: #a65e2e;
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
      color: #4a2c17;
      margin-bottom: 8px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    
    .project-desc {
      font-size: 14px;
      color: #a67c52;
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
    border-top: 1px solid #f5ebe0;
    
    .meta-item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      color: #c9a86c;
      
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
    background: linear-gradient(135deg, #f5ebe0 0%, #f2dec8 100%);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 24px;
    
    .el-icon {
      font-size: 56px;
      color: #c97f4a;
    }
  }
  
  h2 {
    font-size: 24px;
    font-weight: 600;
    color: #4a2c17;
    margin-bottom: 8px;
  }
  
  p {
    font-size: 15px;
    color: #a67c52;
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
        box-shadow: 0 8px 20px rgba(166, 94, 46, 0.3);
      }
    }
  }
}

/* 对话框样式 */
:deep(.coffee-dialog) {
  .el-dialog__header {
    padding: 20px 24px;
    border-bottom: 1px solid #f2e9e0;
    
    .el-dialog__title {
      font-weight: 600;
      color: #4a2c17;
    }
  }
  
  .el-dialog__body {
    padding: 24px;
  }
  
  .el-dialog__footer {
    padding: 16px 24px;
    border-top: 1px solid #f2e9e0;
  }
}

.coffee-form {
  .el-input__wrapper,
  .el-textarea__inner {
    background: #fdfbf7;
    border-color: #e8dcd0;
    
    &:focus {
      border-color: #c97f4a;
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
