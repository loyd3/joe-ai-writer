<template>
  <div class="project-sidebar">
    <div class="sidebar-header">
      <el-button 
        type="primary" 
        class="create-btn"
        @click="showCreateDialog = true"
      >
        <el-icon><Plus /></el-icon>
        <span>新建项目</span>
      </el-button>
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
import { Plus, FolderOpened, Folder, More, Edit, Delete, Collection } from '@element-plus/icons-vue'

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
      if (currentProjectId.value === String(project.id)) {
        router.push('/')
      }
    })
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
    background: linear-gradient(135deg, #a65e2e 0%, #c97f4a 100%);
    border: none;
    font-weight: 500;
    transition: all 0.3s ease;
    
    &:hover {
      transform: translateY(-1px);
      box-shadow: 0 6px 16px rgba(166, 94, 46, 0.25);
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
  color: #c9a86c;
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
    background: rgba(166, 94, 46, 0.06);
    
    .more-icon {
      opacity: 1;
    }
  }
  
  &.active {
    background: rgba(166, 94, 46, 0.12);
    
    .project-title {
      color: #4a2c17;
      font-weight: 600;
    }
    
    .project-icon {
      color: #a65e2e;
    }
  }
  
  .project-icon {
    font-size: 18px;
    color: #c9a86c;
    flex-shrink: 0;
  }
  
  .project-title {
    flex: 1;
    font-size: 14px;
    color: #6b5a4a;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  .more-icon {
    font-size: 16px;
    color: #c9a86c;
    opacity: 0;
    transition: opacity 0.2s;
    padding: 4px;
    border-radius: 4px;
    
    &:hover {
      background: rgba(166, 94, 46, 0.1);
      color: #a65e2e;
    }
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #c9a86c;
  
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
</style>
