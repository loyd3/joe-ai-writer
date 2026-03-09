<template>
  <div class="project-sidebar">
    <!-- <div class="sidebar-header">
      <el-button 
        type="primary" 
        class="create-btn"
        @click="showCreateDialog = true"
      >
        <el-icon><Plus /></el-icon>
        <span>新建项目</span>
      </el-button>
    </div> -->
    
    <!-- AI工具菜单 -->
    <div class="menu-section">
      <div class="section-title">
        <el-icon><MagicStick /></el-icon>
        <span>AI 工具</span>
      </div>
      
      <div class="tool-list">
        <div
          class="tool-item"
          :class="{ active: route.path === '/hot-topics' }"
          @click="router.push('/hot-topics')"
        >
          <el-icon class="tool-icon"><TrendCharts /></el-icon>
          <span class="tool-title">热点写作</span>
          <el-tag size="small" type="danger" effect="dark" class="hot-tag">HOT</el-tag>
        </div>
      </div>
    </div>
    
    <div class="menu-section">
      <div class="section-title">
        <el-icon><Collection /></el-icon>
        <span>我的项目</span>
      </div>
      
      <div class="project-list" v-if="projects.length > 0">
        <div
          v-for="project in projects"
          :key="project.id"
          class="project-item"
          :class="{ active: currentProjectId === String(project.id) }"
          @click="handleSelect(String(project.id))"
        >
          <el-icon class="project-icon"><FolderOpened /></el-icon>
          <span class="project-title">{{ project.title }}</span>
          <el-dropdown trigger="click" @command="(cmd) => handleCommand(cmd, project)">
            <el-icon class="more-icon" @click.stop><More /></el-icon>
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
      </div>
      
      <div v-else class="empty-state">
        <el-icon class="empty-icon"><Folder /></el-icon>
        <p>还没有项目</p>
        <span>点击上方按钮创建</span>
      </div>
    </div>

    <!-- 创建/编辑项目对话框 -->
    <el-dialog 
      v-model="showCreateDialog" 
      :title="editingProject ? '编辑项目' : '新建项目'" 
      width="420px"
      class="coffee-dialog"
    >
      <el-form :model="newProject" label-width="80px" class="coffee-form">
        <el-form-item label="项目名称">
          <el-input 
            v-model="newProject.title" 
            placeholder="输入项目名称"
            maxlength="50"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="newProject.description"
            type="textarea"
            :rows="3"
            placeholder="项目描述（可选）"
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
import { useRouter, useRoute } from 'vue-router'
import { useProjectStore, type Project } from '@/stores/project'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, FolderOpened, Folder, More, Edit, Delete, Collection, MagicStick, TrendCharts } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const store = useProjectStore()

const projects = computed(() => store.projectList)
const currentProjectId = computed(() => {
  const id = route.params.id || route.params.projectId
  return id ? String(id) : ''
})

const showCreateDialog = ref(false)
const editingProject = ref<Project | null>(null)
const saving = ref(false)
const newProject = ref({
  title: '',
  description: ''
})

onMounted(() => {
  store.fetchProjects()
})

function handleSelect(index: string) {
  router.push(`/project/${index}`)
}

function handleCommand(cmd: string, project: Project) {
  if (cmd === 'edit') {
    editingProject.value = project
    newProject.value = {
      title: project.title,
      description: project.description || ''
    }
    showCreateDialog.value = true
  } else if (cmd === 'delete') {
    ElMessageBox.confirm(
      `确定要删除项目 "${project.title}" 吗？项目下的所有文档将被删除，此操作不可恢复。`,
      '删除项目',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    ).then(async () => {
      try {
        await store.deleteProject(project.id)
        ElMessage.success('项目已删除')
        if (currentProjectId.value === String(project.id)) {
          router.push('/')
        }
      } catch (error: any) {
        ElMessage.error(error?.response?.data?.detail || '删除项目失败，请稍后重试')
      }
    }).catch(() => {})
  }
}

async function saveProject() {
  if (!newProject.value.title.trim()) {
    ElMessage.warning('请输入项目名称')
    return
  }
  
  saving.value = true
  try {
    if (editingProject.value) {
      await store.updateProject(editingProject.value.id, newProject.value)
      ElMessage.success('项目已更新')
    } else {
      const project = await store.createProject(newProject.value)
      ElMessage.success('项目创建成功')
      router.push(`/project/${project.id}`)
    }
    showCreateDialog.value = false
    editingProject.value = null
    newProject.value = { title: '', description: '' }
  } finally {
    saving.value = false
  }
}
</script>

<style scoped lang="scss">
.project-sidebar {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 16px;
  
  .create-btn {
    width: 100%;
    height: 44px;
    border-radius: 10px;
    background: var(--coffee-gradient-primary);
    border: none;
    font-weight: 500;
    transition: all 0.3s ease;
    
    &:hover {
      transform: translateY(-1px);
      box-shadow: 0 6px 16px var(--coffee-shadow-hover);
    }
    
    .el-icon {
      margin-right: 6px;
    }
  }
}

.menu-section {
  flex: 1;
  padding: 0 12px;
  overflow-y: auto;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 12px 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--coffee-text-light);
  text-transform: uppercase;
  letter-spacing: 1px;
  
  .el-icon {
    font-size: 14px;
  }
}

.project-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.project-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  
  &:hover {
    background: var(--coffee-bg-hover);
    
    .more-icon {
      opacity: 1;
    }
  }
  
  &.active {
    background: var(--coffee-selection);
    
    .project-title {
      color: var(--coffee-text);
      font-weight: 600;
    }
    
    .project-icon {
      color: var(--coffee-primary);
    }
  }
  
  .project-icon {
    font-size: 18px;
    color: var(--coffee-text-light);
    flex-shrink: 0;
  }
  
  .project-title {
    flex: 1;
    font-size: 14px;
    color: var(--coffee-text-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  .more-icon {
    font-size: 16px;
    color: var(--coffee-text-light);
    opacity: 0;
    transition: opacity 0.2s;
    padding: 4px;
    border-radius: 4px;
    
    &:hover {
      background: var(--coffee-bg-hover);
      color: var(--coffee-primary);
    }
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: var(--coffee-text-light);
  
  .empty-icon {
    font-size: 48px;
    margin-bottom: 12px;
    opacity: 0.5;
  }
  
  p {
    font-size: 14px;
    margin-bottom: 4px;
  }
  
  span {
    font-size: 12px;
    opacity: 0.7;
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

/* AI工具列表样式 */
.tool-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 16px;
}

.tool-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;

  &:hover {
    background: var(--coffee-bg-hover);
  }

  &.active {
    background: var(--coffee-selection);

    .tool-title {
      color: var(--coffee-text);
      font-weight: 600;
    }

    .tool-icon {
      color: var(--coffee-primary);
    }
  }

  .tool-icon {
    font-size: 18px;
    color: var(--coffee-text-light);
    flex-shrink: 0;
  }

  .tool-title {
    flex: 1;
    font-size: 14px;
    color: var(--coffee-text-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .hot-tag {
    font-size: 10px;
    padding: 0 6px;
    height: 18px;
    line-height: 16px;
    transform: scale(0.85);
    transform-origin: right center;
  }
}
</style>
