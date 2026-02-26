<template>
  <div class="project-view">
    <div class="project-header">
      <div class="header-content">
        <div class="breadcrumb">
          <el-button link @click="goHome" class="back-btn">
            <el-icon><ArrowLeft /></el-icon>
          </el-button>
          <div class="title-section">
            <h1>{{ project?.title }}</h1>
            <p class="desc">{{ project?.description || '暂无描述' }}</p>
          </div>
        </div>
        <div class="actions">
          <el-button class="memory-btn" @click="showTemplateLibrary = true">
            <el-icon><Upload /></el-icon>
            <span>导入模板</span>
          </el-button>
          <el-button class="memory-btn" @click="showMemoryDrawer = true">
            <el-icon><Collection /></el-icon>
            <span>项目设定</span>
          </el-button>
          <el-dropdown trigger="click" @command="handleProjectCommand" class="project-actions-dropdown">
            <el-button class="more-btn">
              <el-icon><MoreFilled /></el-icon>
              <span>项目操作</span>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="edit">
                  <el-icon><Edit /></el-icon> 编辑项目
                </el-dropdown-item>
                <el-dropdown-item command="delete" divided class="delete-item">
                  <el-icon><Delete /></el-icon> 删除项目
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button type="primary" class="create-btn" @click="showCreateDocDialog = true">
            <el-icon><Plus /></el-icon>
            <span>新建文档</span>
          </el-button>
          <!-- 导出项目按钮 -->
          <ExportMenu
            :project-id="Number(projectId)"
            :project-title="project?.title"
          />
        </div>
      </div>
    </div>

    <div class="documents-section">
      <div class="section-header">
        <h2>
          <el-icon><DocumentIcon /></el-icon>
          文档列表
        </h2>
        <span class="count">共 {{ documents?.length || 0 }} 篇</span>
      </div>
      
      <el-empty v-if="!documents?.length" description="暂无文档" class="custom-empty">
        <el-button type="primary" @click="showCreateDocDialog = true">
          创建第一篇文档
        </el-button>
      </el-empty>
      
      <div v-else class="documents-grid">
        <div 
          v-for="(doc, index) in documents" 
          :key="`doc-${doc.id}-${index}`" 
          class="doc-card"
          @click="openDocument(doc.id)"
        >
          <div class="doc-header">
            <div class="doc-icon">
              <el-icon><DocumentIcon /></el-icon>
            </div>
            <el-dropdown trigger="click" @command="(cmd) => handleDocCommand(cmd, doc)">
              <el-icon class="more-icon" @click.stop><MoreFilled /></el-icon>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="rename">
                    <el-icon><Edit /></el-icon> 重命名
                  </el-dropdown-item>
                  <el-dropdown-item command="delete" divided class="delete-item">
                    <el-icon><Delete /></el-icon> 删除
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          <h4 class="doc-title">{{ doc.title }}</h4>
          <p class="doc-preview">{{ getDocPreview(doc) }}</p>
          <div class="doc-meta">
            <el-icon><Calendar /></el-icon>
            <span>{{ formatDate(doc.updated_at) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 项目设定抽屉 -->
    <el-drawer
      v-model="showMemoryDrawer"
      title="项目设定管理"
      size="520px"
      class="memory-drawer"
      :destroy-on-close="false"
    >
      <ProjectSettingsManager :project-id="Number(projectId)" />
    </el-drawer>

    <!-- 新建文档对话框 -->
    <el-dialog 
      v-model="showCreateDocDialog" 
      title="新建文档" 
      width="420px"
      class="coffee-dialog"
    >
      <el-form :model="newDoc" label-width="80px" class="coffee-form">
        <el-form-item label="文档标题">
          <el-input 
            v-model="newDoc.title" 
            placeholder="输入文档标题"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDocDialog = false">取消</el-button>
        <el-button type="primary" @click="createDocument" :loading="creating">
          创建
        </el-button>
      </template>
    </el-dialog>

    <!-- 导入模板对话框 -->
    <el-dialog
      v-model="showTemplateLibrary"
      title="导入模板到当前项目"
      width="900px"
      class="template-dialog"
      :destroy-on-close="true"
    >
      <TemplateLibrary
        mode="applyToProject"
        :project-id="Number(projectId)"
        @applied="onTemplateApplied"
      />
    </el-dialog>

    <!-- 编辑项目对话框 -->
    <el-dialog 
      v-model="showEditProjectDialog" 
      title="编辑项目" 
      width="420px"
      class="coffee-dialog"
    >
      <el-form :model="editProjectForm" label-width="80px" class="coffee-form">
        <el-form-item label="项目名称">
          <el-input 
            v-model="editProjectForm.title" 
            placeholder="输入项目名称"
            maxlength="50"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="editProjectForm.description"
            type="textarea"
            :rows="3"
            placeholder="项目描述（可选）"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditProjectDialog = false">取消</el-button>
        <el-button type="primary" @click="saveProjectEdit" :loading="savingProject">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore, type Document } from '@/stores/project'
import { ElMessage, ElMessageBox } from 'element-plus'
import ProjectSettingsManager from '@/components/ProjectSettingsManager.vue'
import { ArrowLeft, Collection, Plus, Document as DocumentIcon, MoreFilled, Edit, Delete, Calendar, Upload } from '@element-plus/icons-vue'
import ExportMenu from '@/components/ExportMenu.vue'
import TemplateLibrary from '@/components/TemplateLibrary.vue'

const route = useRoute()
const router = useRouter()
const store = useProjectStore()

const projectId = computed(() => route.params.id as string)
const project = computed(() => store.currentProject)
const documents = computed(() => store.currentProject?.documents || [])

const showMemoryDrawer = ref(false)
const showTemplateLibrary = ref(false)
const showCreateDocDialog = ref(false)
const showEditProjectDialog = ref(false)
const creating = ref(false)
const savingProject = ref(false)
const newDoc = ref({ title: '' })
const editProjectForm = ref({ title: '', description: '' })

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

function onTemplateApplied() {
  showTemplateLibrary.value = false
  loadProject()
}

function goHome() {
  router.push('/')
}

function formatDate(date: string) {
  const d = new Date(date)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function getDocPreview(doc: Document) {
  if (!doc.content?.length) return '空白文档'
  const text = doc.content.map(b => b.content).join(' ')
  return text.slice(0, 80) + (text.length > 80 ? '...' : '')
}

function openDocument(id: number) {
  router.push(`/document/${id}`)
}

async function createDocument() {
  if (!newDoc.value.title.trim()) {
    ElMessage.warning('请输入文档标题')
    return
  }
  
  creating.value = true
  try {
    const doc = await store.createDocument(Number(projectId.value), {
      title: newDoc.value.title,
      content: []
    })
    showCreateDocDialog.value = false
    newDoc.value = { title: '' }
    router.push(`/document/${doc.id}`)
    ElMessage.success('文档创建成功')
  } finally {
    creating.value = false
  }
}

function handleDocCommand(cmd: string, doc: Document) {
  if (cmd === 'rename') {
    ElMessageBox.prompt('新标题', '重命名文档', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputValue: doc.title,
      inputPattern: /.{1,100}/,
      inputErrorMessage: '标题不能为空'
    }).then(async ({ value }) => {
      await store.updateDocument(doc.id, { title: value })
      ElMessage.success('已重命名')
    })
  } else if (cmd === 'delete') {
    ElMessageBox.confirm(
      `确定要删除文档 "${doc.title}" 吗？`,
      '删除文档',
      { 
        confirmButtonText: '删除', 
        cancelButtonText: '取消', 
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    ).then(async () => {
      await store.deleteDocument(doc.id)
      ElMessage.success('已删除')
    })
  }
}

function handleProjectCommand(cmd: string) {
  if (cmd === 'edit' && project.value) {
    editProjectForm.value = {
      title: project.value.title,
      description: project.value.description || ''
    }
    showEditProjectDialog.value = true
  } else if (cmd === 'delete') {
    ElMessageBox.confirm(
      `确定要删除项目「${project.value?.title}」吗？项目下的所有文档将被删除，此操作不可恢复。`,
      '删除项目',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    ).then(async () => {
      if (projectId.value) {
        await store.deleteProject(Number(projectId.value))
        ElMessage.success('项目已删除')
        router.push('/')
      }
    }).catch(() => {})
  }
}

async function saveProjectEdit() {
  if (!editProjectForm.value.title.trim()) {
    ElMessage.warning('请输入项目名称')
    return
  }
  if (!projectId.value) return
  savingProject.value = true
  try {
    await store.updateProject(Number(projectId.value), editProjectForm.value)
    ElMessage.success('项目已更新')
    showEditProjectDialog.value = false
  } finally {
    savingProject.value = false
  }
}
</script>

<style scoped lang="scss">
.project-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 32px 40px;
}

.project-header {
  flex-shrink: 0;
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--coffee-border);
  
  .header-content {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: wrap;
  }
}

.breadcrumb {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  
  .back-btn {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    background: var(--coffee-bg-warm);
    color: var(--coffee-text-muted);
    
    &:hover {
      background: var(--coffee-border-light);
      color: var(--coffee-primary);
    }
  }
  
  .title-section {
    h1 {
      font-size: 28px;
      font-weight: 700;
      color: var(--coffee-text);
      margin-bottom: 8px;
    }
    
    .desc {
      font-size: 15px;
      color: var(--coffee-text-muted);
      max-width: 600px;
    }
  }
}

.actions {
  display: flex;
  align-items: center;
  gap: 12px;
  
  .project-actions-dropdown .more-btn {
    height: 44px;
    padding: 0 16px;
    border-radius: 10px;
    border-color: var(--coffee-border);
    color: var(--coffee-text-secondary);
    .el-icon { margin-right: 6px; }
    &:hover {
      border-color: var(--coffee-primary);
      color: var(--coffee-primary);
    }
  }
  
  :deep(.delete-item) {
    color: var(--el-color-danger);
  }
  
  .memory-btn {
    height: 44px;
    padding: 0 20px;
    border-radius: 10px;
    border-color: var(--coffee-border);
    color: var(--coffee-text-secondary);
    
    &:hover {
      border-color: var(--coffee-primary);
      color: var(--coffee-primary);
      background: rgba(166, 94, 46, 0.04);
    }
    
    .el-icon {
      margin-right: 6px;
    }
  }
  
  .create-btn {
    height: 44px;
    padding: 0 24px;
    border-radius: 10px;
    background: linear-gradient(135deg, var(--coffee-primary) 0%, var(--coffee-primary-light) 100%);
    border: none;
    font-weight: 500;
    
    &:hover {
      transform: translateY(-1px);
      box-shadow: 0 6px 16px rgba(166, 94, 46, 0.25);
    }
    
    .el-icon {
      margin-right: 6px;
    }
  }
}

.documents-section {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px; /* 留出滚动条空间 */

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    
    h2 {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 18px;
      font-weight: 600;
      color: var(--coffee-text);
      
      .el-icon {
        color: var(--coffee-primary);
      }
    }
    
    .count {
      font-size: 14px;
      color: var(--coffee-text-light);
    }
  }
}

.documents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.doc-card {
  background: var(--coffee-bg-card);
  border-radius: 16px;
  padding: 24px;
  border: 1px solid var(--coffee-border-light);
  cursor: pointer;
  transition: all 0.3s ease;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px var(--coffee-shadow-hover);
    border-color: var(--coffee-border);
    
    .more-icon {
      opacity: 1;
    }
  }
  
  .doc-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    
    .doc-icon {
      width: 44px;
      height: 44px;
      background: linear-gradient(135deg, #fff 0%, var(--coffee-primary) 100%);
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      
      .el-icon {
        font-size: 22px;
        color: #000;
      }
    }
    
    .more-icon {
      font-size: 18px;
      color: var(--coffee-text-light);
      padding: 6px;
      border-radius: 6px;
      opacity: 0;
      transition: all 0.2s;
      
      &:hover {
        background: rgba(166, 94, 46, 0.08);
        color: var(--coffee-primary);
      }
    }
  }
  
  .doc-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--coffee-text);
    margin-bottom: 10px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  .doc-preview {
    font-size: 14px;
    color: var(--coffee-text-muted);
    line-height: 1.6;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    min-height: 44px;
    margin-bottom: 16px;
  }
  
  .doc-meta {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    color: var(--coffee-text-light);
    padding-top: 12px;
    border-top: 1px solid var(--coffee-divider);
    
    .el-icon {
      font-size: 14px;
    }
  }
}

.custom-empty {
  padding: 60px 20px;
}

:deep(.memory-drawer) {
  .el-drawer__header {
    padding: 20px 24px;
    border-bottom: 1px solid var(--coffee-border-light);
    margin-bottom: 0;
    
    span {
      font-size: 18px;
      font-weight: 600;
      color: var(--coffee-text);
    }
  }
  
  .el-drawer__body {
    padding: 0;
    background: var(--coffee-bg);
  }
}

:deep(.delete-item) {
  color: #f56c6c;
}

@media (max-width: 768px) {
  .project-view {
    padding: 20px;
  }
  
  .project-header {
    .header-content {
      flex-direction: column;
      gap: 20px;
    }
  }
  
  .documents-grid {
    grid-template-columns: 1fr;
  }
}
</style>
