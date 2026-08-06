<template>
  <div class="ai-generate">
    <div class="generate-header">
      <h3>
        <el-icon><MagicStick /></el-icon>
        根据项目设定生成
      </h3>
      <p class="subtitle">基于项目设定中的角色、大纲、世界观等，由 AI 自动生成正文</p>
    </div>

    <div class="generate-form">
      <el-form label-position="top">
        <el-form-item label="生成类型">
          <el-select
            v-model="generateType"
            placeholder="选择生成类型"
            style="width: 100%"
            size="large"
          >
            <el-option label="生成开头" value="opening" />
            <el-option label="续写当前文档" value="continue" />
            <el-option label="根据大纲生成一节" value="outline_section" />
            <el-option label="场景片段" value="scene" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>

        <el-form-item v-if="generateType === 'custom'" label="自定义要求">
          <el-input
            v-model="customInstruction"
            type="textarea"
            :rows="3"
            placeholder="例如：写一段主角与反派的第一次对峙"
          />
        </el-form-item>
      </el-form>

      <div class="generate-actions">
        <el-button
          type="primary"
          size="large"
          class="full-width-btn"
          @click="generate"
          :loading="generating"
        >
          <el-icon><Promotion /></el-icon>
          {{ generating ? '生成中...' : '开始生成' }}
        </el-button>
      </div>
    </div>

    <div v-if="generatedText" class="generate-result">
      <h4>生成结果</h4>
      <div class="result-content">{{ generatedText }}</div>
      <div class="result-actions">
        <el-button type="primary" @click="insertToDoc">
          <el-icon><DocumentAdd /></el-icon>
          插入到文档
        </el-button>
        <el-button @click="copyResult">
          <el-icon><CopyDocument /></el-icon>
          复制
        </el-button>
      </div>
    </div>

    <div v-else-if="generating" class="streaming-preview">
      <h4>生成中</h4>
      <div class="streaming-content">
        {{ streamingContent }}<span class="cursor">|</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { aiApi } from '@/api'
import { MagicStick, Promotion, DocumentAdd, CopyDocument } from '@element-plus/icons-vue'

const props = defineProps<{
  projectId: number
  documentId?: number
  currentContent: any[]  // 当前文档 content blocks，续写时取末尾
}>()

const generateType = ref<'opening' | 'continue' | 'outline_section' | 'scene' | 'custom'>('opening')
const customInstruction = ref('')
const generating = ref(false)
const streamingContent = ref('')
const generatedText = ref('')

const currentContentText = computed(() => {
  if (!props.currentContent?.length) return ''
  const text = props.currentContent
    .map((b: { content?: string }) => b.content || '')
    .join('\n')
  return text.length > 2000 ? text.slice(-2000) : text
})

const emit = defineEmits<{
  (e: 'insert', text: string): void
}>()

async function generate() {
  if (generateType.value === 'custom' && !customInstruction.value.trim()) {
    ElMessage.warning('请输入自定义生成要求')
    return
  }
  generating.value = true
  streamingContent.value = ''
  generatedText.value = ''
  try {
    const res = await aiApi.generateFromMemoryStream({
      project_id: props.projectId,
      document_id: props.documentId,
      generate_type: generateType.value,
      custom_instruction: generateType.value === 'custom' ? customInstruction.value.trim() : undefined,
      current_content: generateType.value === 'continue' ? currentContentText.value || undefined : undefined
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || '生成失败')
    }
    const reader = res.body?.getReader()
    const decoder = new TextDecoder()
    if (!reader) throw new Error('无法读取响应')
    let full = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value, { stream: true })
      const lines = chunk.split('\n')
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') continue
          full += data
          streamingContent.value = full
        }
      }
    }
    generatedText.value = full
    if (full) ElMessage.success('生成完成')
    else ElMessage.warning('未生成到有效内容')
  } catch (e: any) {
    ElMessage.error(e?.message || '生成失败')
  } finally {
    generating.value = false
  }
}

function insertToDoc() {
  if (generatedText.value) {
    emit('insert', generatedText.value)
    ElMessage.success('已插入到文档')
  }
}

function copyResult() {
  if (!generatedText.value) return
  navigator.clipboard.writeText(generatedText.value).then(() => {
    ElMessage.success('已复制到剪贴板')
  })
}
</script>

<style scoped lang="scss">
.ai-generate {
  padding: 20px;
}

.generate-header {
  text-align: center;
  margin-bottom: 24px;

  h3 {
    margin: 0 0 8px;
    font-size: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }

  .subtitle {
    margin: 0;
    color: var(--el-text-color-secondary);
    font-size: 13px;
  }
}

.generate-form {
  margin-bottom: 24px;
}

.generate-actions {
  margin-top: 16px;
}

.generate-result,
.streaming-preview {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--el-border-color-lighter);

  h4 {
    margin: 0 0 12px;
    font-size: 14px;
    color: var(--el-text-color-regular);
  }
}

.result-content,
.streaming-content {
  white-space: pre-wrap;
  word-break: break-word;
  padding: 16px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
  max-height: 320px;
  overflow-y: auto;
  font-size: 14px;
  line-height: 1.7;
  margin-bottom: 12px;
}

.streaming-content .cursor {
  animation: blink 0.8s step-end infinite;
}

@keyframes blink {
  50% { opacity: 0; }
}

.result-actions {
  display: flex;
  gap: 12px;
}
</style>
