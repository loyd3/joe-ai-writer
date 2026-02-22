<template>
  <div class="project-list">
    <div class="header">
      <h1>我的项目</h1>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon> 新建项目
      </el-button>
    </div>
    
    <el-row :gutter="20" class="project-grid">
      <el-col :xs="24" :sm="12" :md="8" :lg="6" v-for="project in projects" :key="project.id">
        <el-card class="project-card" shadow="hover" @click="openProject(project.id)">
          <div class="card-header">
            <el-icon class="project-icon"><Document /></el-icon>
            <el-dropdown trigger="click" @command="(cmd) => handleCommand(cmd, project)">
              <el-icon class="more-icon"><More /></el-icon>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="edit">编辑</el-dropdown-item>
                  <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          <h3 class="project-title">{{ project.title }}</h3>
          <p class="project-desc">{{ project.description || '暂无描述' }}</p>
          <div class="project-meta">
            <span>{{ formatDate(project.updated_at) }}</span>
            <span>{{ project.documents?.length || 0 }} 篇文档</span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 创建/编辑项目对话框 -->
    <el-dialog v-model="showCreateDialog" :title="editingProject ? '编辑项目' : '新建项目'" width="400px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="项目名称">
          <el-input v-model="form.title" placeholder="输入项目名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" placeholder="项目描述（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="saveProject">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectStore, type Project } from '@/stores/project'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const store = useProjectStore()

const projects = computed(() => store.projectList)
const showCreateDialog = ref(false)
const editingProject = ref<Project | null>(null)
const form = ref({
  title: '',
  description: ''
})

onMounted(() => {
  store.fetchProjects()
})

function formatDate(date: string) {
  return new Date(date).toLocaleDateString('zh-CN')
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
      `确定要删除项目 "${project.title}" 吗？`,
      '警告',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    ).then(() => {
      store.deleteProject(project.id)
      ElMessage.success('已删除')
    })
  }
}

async function saveProject() {
  if (!form.value.title.trim()) {
    ElMessage.warning('请输入项目名称')
    return
  }
  
  if (editingProject.value) {
    await store.updateProject(editingProject.value.id, form.value)
    ElMessage.success('已更新')
  } else {
    await store.createProject(form.value)
    ElMessage.success('创建成功')
  }
  
  showCreateDialog.value = false
  editingProject.value = null
  form.value = { title: '', description: '' }
}
</script>

<style scoped>
.project-list {
  padding: 30px;
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.header h1 {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
}

.project-grid {
  margin-top: 20px;
}

.project-card {
  cursor: pointer;
  margin-bottom: 20px;
  transition: transform 0.2s;
}

.project-card:hover {
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.project-icon {
  font-size: 32px;
  color: #409eff;
}

.more-icon {
  padding: 5px;
  cursor: pointer;
  color: #909399;
}

.more-icon:hover {
  color: #409eff;
}

.project-title {
  font-size: 18px;
  font-weight: 500;
  margin-bottom: 8px;
  color: #303133;
}

.project-desc {
  font-size: 14px;
  color: #909399;
  margin-bottom: 15px;
  height: 40px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.project-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #c0c4cc;
}
</style>