<template>
  <div class="project-sidebar">
    <div class="sidebar-header">
      <el-button type="primary" @click="showCreateDialog = true" style="width: 100%">
        <el-icon><Plus /></el-icon> 新建项目
      </el-button>
    </div>
    
    <el-menu
      :default-active="currentProjectId"
      class="project-menu"
      @select="handleSelect"
    >
      <el-menu-item
        v-for="project in projects"
        :key="project.id"
        :index="String(project.id)"
      >
        <el-icon><Folder /></el-icon>
        <span>{{ project.title }}</span>
      </el-menu-item>
    </el-menu>

    <!-- 创建项目对话框 -->
    <el-dialog v-model="showCreateDialog" title="新建项目" width="400px">
      <el-form :model="newProject" label-width="80px">
        <el-form-item label="项目名称">
          <el-input v-model="newProject.title" placeholder="输入项目名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="newProject.description"
            type="textarea"
            placeholder="项目描述（可选）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createProject">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useProjectStore } from '@/stores/project'

const router = useRouter()
const route = useRoute()
const store = useProjectStore()

const projects = computed(() => store.projectList)
const currentProjectId = computed(() => {
  const id = route.params.id || route.params.projectId
  return id ? String(id) : ''
})

const showCreateDialog = ref(false)
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

async function createProject() {
  if (!newProject.value.title.trim()) return
  
  const project = await store.createProject({
    title: newProject.value.title,
    description: newProject.value.description
  })
  
  showCreateDialog.value = false
  newProject.value = { title: '', description: '' }
  router.push(`/project/${project.id}`)
}
</script>

<style scoped>
.project-sidebar {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 15px;
  border-bottom: 1px solid #e4e7ed;
}

.project-menu {
  flex: 1;
  border-right: none;
}
</style>