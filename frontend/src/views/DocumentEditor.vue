<template>
  <div class="document-editor">
    <div class="editor-header">
      <div class="header-left">
        <el-button link class="back-btn" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <div class="breadcrumb">
          <span class="project-name">{{ project?.title }}</span>
          <el-icon class="separator"><ArrowRight /></el-icon>
          <el-input
            v-model="documentTitle"
            class="title-input"
            placeholder="文档标题"
            @blur="saveTitle"
          />
        </div>
      </div>
      <div class="header-right">
        <div class="save-status" v-if="saving">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>保存中...</span>
        </div>
        <div class="save-status saved" v-else-if="lastSaved">
          <el-icon><CircleCheck /></el-icon>
          <span>已保存 {{ formatTime(lastSaved) }}</span>
        </div>
        <el-button 
          class="chat-toggle" 
          :type="showChatPanel ? 'primary' : 'default'"
          @click="showChatPanel = !showChatPanel"
        >
          <el-icon><ChatDotRound /></el-icon>
          <span>AI 助手</span>
        </el-button>
        <el-button type="primary" class="save-btn" @click="saveDocument" :loading="saving">
          <el-icon><Check /></el-icon>
          <span>保存</span>
        </el-button>
      </div>
    </div>

    <div class="editor-container">
      <div class="editor-main" :class="{ 'with-chat': showChatPanel }">
        <div class="editor-content">
          <BlockEditor 
            v-model="content" 
            @update:modelValue="onContentChange"
          />
        </div>
      </div>
      
      <AIChatPanel
        v-if="showChatPanel"
        :document-id="Number(documentId)"
        :content="content"
        @insert="insertText"
        @replace="replaceText"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, onUnmounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore, type Block } from '@/stores/project'
import { ElMessage } from 'element-plus'
import BlockEditor from '@/components/BlockEditor.vue'
import AIChatPanel from '@/components/AIChatPanel.vue'
import { ArrowLeft, ArrowRight, ChatDotRound, Check, Loading, CircleCheck } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const store = useProjectStore()

const documentId = computed(() => route.params.id as string)
const document = computed(() => store.currentDocument)
const project = computed(() => store.currentProject)

const documentTitle = ref('')
const content = ref<Block[]>([])
const saving = ref(false)
const showChatPanel = ref(true)
const hasChanges = ref(false)
const lastSaved = ref<Date | null>(null)

let autoSaveInterval: number | null = null

onMounted(() => {
  loadDocument()
  // 启动自动保存
  autoSaveInterval = window.setInterval(() => {
    if (hasChanges.value && documentId.value) {
      saveDocument()
    }
  }, 30000)
})

onUnmounted(() => {
  if (autoSaveInterval) {
    clearInterval(autoSaveInterval)
  }
})

watch(documentId, () => {
  loadDocument()
})

async function loadDocument() {
  await store.fetchDocument(Number(documentId.value))
  if (document.value) {
    documentTitle.value = document.value.title
    content.value = document.value.content || []
    if (document.value.project_id) {
      await store.fetchProject(document.value.project_id)
    }
  }
}

function onContentChange() {
  hasChanges.value = true
}

async function saveTitle() {
  if (documentTitle.value !== document.value?.title) {
    await store.updateDocument(Number(documentId.value), {
      title: documentTitle.value
    })
    ElMessage.success('标题已保存')
  }
}

async function saveDocument() {
  if (!hasChanges.value && !saving.value) return
  
  saving.value = true
  try {
    await store.updateDocument(Number(documentId.value), {
      title: documentTitle.value,
      content: content.value
    })
    hasChanges.value = false
    lastSaved.value = new Date()
  } finally {
    saving.value = false
  }
}

function goBack() {
  if (project.value) {
    router.push(`/project/${project.value.id}`)
  } else {
    router.push('/')
  }
}

function insertText(text: string) {
  content.value.push({
    id: Date.now().toString(),
    type: 'paragraph',
    content: text,
    props: {}
  })
  hasChanges.value = true
}

function replaceText(oldText: string, newText: string) {
  for (const block of content.value) {
    if (block.content.includes(oldText)) {
      block.content = block.content.replace(oldText, newText)
      hasChanges.value = true
      return
    }
  }
}

function formatTime(date: Date) {
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

// 监听页面关闭，提示未保存
onBeforeUnmount(() => {
  if (hasChanges.value) {
    saveDocument()
  }
})
</script>

<style scoped lang="scss">
.document-editor {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--coffee-bg);
}

.editor-header {
  height: 64px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--coffee-bg-card);
  border-bottom: 1px solid var(--coffee-border);
  box-shadow: 0 2px 8px var(--coffee-shadow);
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  
  .back-btn {
    width: 36px;
    height: 36px;
    border-radius: 8px;
    color: var(--coffee-text-muted);
    
    &:hover {
      background: var(--coffee-bg-warm);
      color: var(--coffee-primary);
    }
  }
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 10px;
  
  .project-name {
    font-size: 14px;
    color: var(--coffee-text-muted);
    max-width: 150px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  .separator {
    font-size: 12px;
    color: var(--coffee-text-light);
  }
  
  .title-input {
    width: 280px;
    
    :deep(.el-input__wrapper) {
      box-shadow: none;
      padding: 0;
    }
    
    :deep(.el-input__inner) {
      font-size: 16px;
      font-weight: 600;
      color: var(--coffee-text);
      border: none;
      padding: 0;
      
      &::placeholder {
        color: var(--coffee-text-light);
      }
    }
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.save-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--coffee-text-light);
  padding: 6px 12px;
  border-radius: 6px;
  background: var(--coffee-bg-warm);
  
  .el-icon {
    font-size: 14px;
  }
  
  &.saved {
    color: #67c23a;
  }
}

.chat-toggle {
  height: 40px;
  padding: 0 16px;
  border-radius: 8px;
  border-color: var(--coffee-border);
  color: var(--coffee-text-secondary);
  
  &:hover, &.el-button--primary {
    border-color: var(--coffee-primary);
    color: var(--coffee-primary);
    background: rgba(166, 94, 46, 0.06);
  }
  
  &.el-button--primary {
    background: var(--coffee-primary);
    color: #fff;
  }
  
  .el-icon {
    margin-right: 6px;
  }
}

.save-btn {
  height: 40px;
  padding: 0 20px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--coffee-primary) 0%, var(--coffee-primary-light) 100%);
  border: none;
  font-weight: 500;
  
  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(166, 94, 46, 0.25);
  }
  
  .el-icon {
    margin-right: 6px;
  }
}

.editor-container {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.editor-main {
  flex: 1;
  overflow-y: auto;
  padding: 40px;
  
  &.with-chat {
    flex: 0 0 60%;
  }
}

.editor-content {
  max-width: 800px;
  margin: 0 auto;
  background: var(--coffee-bg-card);
  border-radius: 16px;
  padding: 48px;
  box-shadow: 0 4px 20px var(--coffee-shadow);
  min-height: calc(100vh - 180px);
}

@media (max-width: 768px) {
  .editor-header {
    padding: 0 16px;
  }
  
  .breadcrumb {
    .title-input {
      width: 160px;
    }
  }
  
  .editor-main {
    padding: 20px;
    
    &.with-chat {
      flex: 0 0 100%;
    }
  }
  
  .editor-content {
    padding: 24px;
  }
  
  .save-status span {
    display: none;
  }
}
</style>
