<template>
  <div class="document-editor">
    <div class="editor-header">
      <div class="breadcrumb">
        <el-button link @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <span class="project-name">{{ project?.title }}</span>
        <el-icon><ArrowRight /></el-icon>
        <el-input
          v-model="documentTitle"
          class="title-input"
          placeholder="文档标题"
          @blur="saveTitle"
        />
      </div>
      <div class="actions">
        <el-button @click="showChatPanel = !showChatPanel" :type="showChatPanel ? 'primary' : 'default'">
          <el-icon><ChatDotRound /></el-icon> AI 助手
        </el-button>
        <el-button type="success" @click="saveDocument" :loading="saving">
          <el-icon><Check /></el-icon> 保存
        </el-button>
      </div>
    </div>

    <div class="editor-container">
      <div class="editor-main" :class="{ 'with-chat': showChatPanel }">
        <BlockEditor 
          v-model="content" 
          @update:modelValue="onContentChange"
        />
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
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore, type Block } from '@/stores/project'
import { ElMessage } from 'element-plus'
import BlockEditor from '@/components/BlockEditor.vue'
import AIChatPanel from '@/components/AIChatPanel.vue'

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

onMounted(() => {
  loadDocument()
})

watch(documentId, () => {
  loadDocument()
})

async function loadDocument() {
  await store.fetchDocument(Number(documentId.value))
  if (document.value) {
    documentTitle.value = document.value.title
    content.value = document.value.content || []
    // 加载项目信息用于记忆
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
  saving.value = true
  try {
    await store.updateDocument(Number(documentId.value), {
      title: documentTitle.value,
      content: content.value
    })
    hasChanges.value = false
    ElMessage.success('文档已保存')
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
  // 查找并替换文本
  for (const block of content.value) {
    if (block.content.includes(oldText)) {
      block.content = block.content.replace(oldText, newText)
      hasChanges.value = true
      return
    }
  }
}

// 自动保存（每 30 秒）
setInterval(() => {
  if (hasChanges.value && documentId.value) {
    saveDocument()
  }
}, 30000)
</script>

<style scoped>
.document-editor {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.editor-header {
  height: 60px;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #e4e7ed;
  background: #fff;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 10px;
}

.project-name {
  color: #606266;
  font-size: 14px;
}

.title-input {
  width: 300px;
}

.title-input :deep(.el-input__wrapper) {
  box-shadow: none;
  padding: 0;
}

.title-input :deep(.el-input__inner) {
  font-size: 16px;
  font-weight: 500;
  border: none;
  padding: 0;
}

.actions {
  display: flex;
  gap: 10px;
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
}

.editor-main.with-chat {
  flex: 0 0 60%;
}
</style>