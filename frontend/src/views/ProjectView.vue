<template>
  <div class="project-view">
    <div class="project-header">
      <div class="title-section">
        <h1>{{ project?.title }}</h1>
        <p class="desc">{{ project?.description }}</p>
      </div>
      <div class="actions">
        <el-button @click="showMemoryDrawer = true">
          <el-icon><Collection /></el-icon> AI 记忆
        </el-button>
        <el-button type="primary" @click="showCreateDocDialog = true">
          <el-icon><Plus /></el-icon> 新建文档
        </el-button>
      </div>
    </div>

    <div class="documents-section">
      <h2>文档列表</h2>
      <el-empty v-if="!documents?.length" description="暂无文档，点击上方按钮创建" />
      <el-row :gutter="16" v-else>
        <el-col :xs="24" :sm="12" :md="8" v-for="doc in documents" :key="doc.id">
          <el-card class="doc-card" shadow="hover" @click="openDocument(doc.id)">
            <div class="doc-header">
              <el-icon class="doc-icon"><Document /></el-icon>
              <el-dropdown trigger="click" @command="(cmd) => handleDocCommand(cmd, doc)">
                <el-icon class="more-icon"><More /></el-icon>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="rename">重命名</el-dropdown-item>
                    <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
            <h4 class="doc-title">{{ doc.title }}</h4>
            <p class="doc-preview">{{ getDocPreview(doc) }}</p>
            <div class="doc-meta">
              {{ formatDate(doc.updated_at) }}
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- AI 记忆抽屉 -->
    <el-drawer
      v-model="showMemoryDrawer"
      title="AI 记忆管理"
      size="500px"
      :destroy-on-close="false"
    >
      <AIMemoryManager :project-id="Number(projectId)" />
    </el-drawer>

    <!-- 新建文档对话框 -->
    <el-dialog v-model="showCreateDocDialog" title="新建文档" width="400px">
      <el-form :model="newDoc" label-width="80px">
        <el-form-item label="文档标题">
          <el-input v-model="newDoc.title" placeholder="输入文档标题" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDocDialog = false">取消</el-button>
        <el-button type="primary" @click="createDocument">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore, type Document } from '@/stores/project'
import { ElMessage, ElMessageBox } from 'element-plus'
import AIMemoryManager from '@/components/AIMemoryManager.vue'

const route = useRoute()
const router = useRouter()
const store = useProjectStore()

const projectId = computed(() => route.params.id as string)
const project = computed(() => store.currentProject)
const documents = computed(() => store.currentProject?.documents || [])

const showMemoryDrawer = ref(false)
const showCreateDocDialog = ref(false)
const newDoc = ref({ title: '' })

onMounted(() => {
  loadProject()
})

watch(projectId, () => {
  loadProject()
})

async function loadProject() {
  if (projectId.value) {
    await store.fetchProject(Number(projectId.value))
  }
}

function formatDate(date: string) {
  return new Date(date).toLocaleDateString('zh-CN')
}

function getDocPreview(doc: Document) {
  if (!doc.content?.length) return '空白文档'
  const text = doc.content.map(b => b.content).join(' ')
  return text.slice(0, 60) + (text.length > 60 ? '...' : '')
}

function openDocument(id: number) {
  router.push(`/document/${id}`)
}

async function createDocument() {
  if (!newDoc.value.title.trim()) {
    ElMessage.warning('请输入文档标题')
    return
  }
  
  const doc = await store.createDocument(Number(projectId.value), {
    title: newDoc.value.title,
    content: []
  })
  
  showCreateDocDialog.value = false
  newDoc.value = { title: '' }
  router.push(`/document/${doc.id}`)
}

function handleDocCommand(cmd: string, doc: Document) {
  if (cmd === 'rename') {
    ElMessageBox.prompt('新标题', '重命名文档', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputValue: doc.title
    }).then(({ value }) => {
      store.updateDocument(doc.id, { title: value })
      ElMessage.success('已重命名')
    })
  } else if (cmd === 'delete') {
    ElMessageBox.confirm(
      `确定要删除文档 "${doc.title}" 吗？`,
      '警告',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    ).then(() => {
      store.deleteDocument(doc.id)
      ElMessage.success('已删除')
    })
  }
}
</script>

<style scoped>
.project-view {
  padding: 30px;
  max-width: 1200px;
  margin: 0 auto;
}

.project-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e4e7ed;
}

.title-section h1 {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.title-section .desc {
  color: #909399;
  font-size: 14px;
}

.actions {
  display: flex;
  gap: 10px;
}

.documents-section h2 {
  font-size: 18px;
  font-weight: 500;
  margin-bottom: 20px;
  color: #606266;
}

.doc-card {
  cursor: pointer;
  margin-bottom: 16px;
}

.doc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.doc-icon {
  font-size: 24px;
  color: #67c23a;
}

.more-icon {
  padding: 4px;
  cursor: pointer;
  color: #909399;
}

.doc-title {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 8px;
  color: #303133;
}

.doc-preview {
  font-size: 13px;
  color: #909399;
  height: 36px;
  overflow: hidden;
  margin-bottom: 12px;
}

.doc-meta {
  font-size: 12px;
  color: #c0c4cc;
}
</style>