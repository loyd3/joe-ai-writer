<template>
  <div class="ai-chat-panel">
    <div class="panel-header">
      <h3><el-icon><Magic /></el-icon> AI 写作助手</h3>
    </div>
    
    <div class="quick-actions">
      <el-button-group>
        <el-button size="small" @click="quickAction('guide')">
          <el-icon><Compass /></el-icon> 指导
        </el-button>
        <el-button size="small" @click="quickAction('revise')">
          <el-icon><Edit /></el-icon> 修改
        </el-button>
        <el-button size="small" @click="quickAction('polish')">
          <el-icon><Brush /></el-icon> 润色
        </el-button>
        <el-button size="small" @click="quickAction('continue')">
          <el-icon><Right /></el-icon> 续写
        </el-button>
      </el-button-group>
    </div>

    <div class="chat-messages" ref="messagesContainer">
      <div
        v-for="(msg, index) in messages"
        :key="index"
        class="message"
        :class="msg.role"
      >
        <div class="message-avatar">
          <el-icon v-if="msg.role === 'assistant'"><Magic /></el-icon>
          <el-icon v-else><User /></el-icon>
        </div>
        <div class="message-content">
          <div class="message-text" v-html="formatMessage(msg.content)" />
          <div v-if="msg.role === 'assistant' && index > 0" class="message-actions">
            <el-button link size="small" @click="insertToDoc(msg.content)">
              <el-icon><DocumentAdd /></el-icon> 插入文档
            </el-button>
            <el-button link size="small" @click="copyToClipboard(msg.content)">
              <el-icon><CopyDocument /></el-icon> 复制
            </el-button>
          </div>
        </div>
      </div>
      
      <div v-if="streaming" class="message assistant streaming">
        <div class="message-avatar"><el-icon><Magic /></el-icon></div>
        <div class="message-content">
          <div class="message-text">{{ streamingContent }}<span class="cursor">|</span></div>
        </div>
      </div>
    </div>

    <div class="chat-input">
      <el-input
        v-model="inputMessage"
        type="textarea"
        :rows="3"
        placeholder="输入你的问题或指令...&#10;选中文字后点击上方按钮可直接修改"
        @keydown.enter.ctrl.prevent="sendMessage"
      />
      <div class="input-actions">
        <span class="hint">Ctrl + Enter 发送</span>
        <el-button type="primary" @click="sendMessage" :loading="loading">
          <el-icon><Promotion /></el-icon> 发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { aiApi } from '@/api'
import { ElMessage } from 'element-plus'

const props = defineProps<{
  documentId: number
  content: any[]
}>()

const emit = defineEmits<{
  (e: 'insert', text: string): void
  (e: 'replace', oldText: string, newText: string): void
}>()

const messages = ref<{ role: string; content: string }[]>([
  { role: 'assistant', content: '你好！我是你的 AI 写作助手。我可以帮你指导写作、修改润色、续写文章等。有什么可以帮你的吗？' }
])

const inputMessage = ref('')
const loading = ref(false)
const streaming = ref(false)
const streamingContent = ref('')
const messagesContainer = ref<HTMLElement>()

function formatMessage(text: string) {
  return text.replace(/\n/g, '<br>')
}

async function sendMessage() {
  if (!inputMessage.value.trim()) return
  
  const userMsg = inputMessage.value
  messages.value.push({ role: 'user', content: userMsg })
  inputMessage.value = ''
  loading.value = true
  streaming.value = true
  streamingContent.value = ''
  
  scrollToBottom()
  
  try {
    const response = await aiApi.chatStream({
      document_id: props.documentId,
      messages: messages.value.map(m => ({ role: m.role, content: m.content })),
      include_memory: true
    })
    
    const reader = response.body?.getReader()
    if (!reader) throw new Error('No reader')
    
    const decoder = new TextDecoder()
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      const text = decoder.decode(value)
      const lines = text.split('\n')
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') {
            messages.value.push({ role: 'assistant', content: streamingContent.value })
            streamingContent.value = ''
            streaming.value = false
          } else {
            streamingContent.value += data
            scrollToBottom()
          }
        }
      }
    }
  } catch (error) {
    ElMessage.error('请求失败，请检查网络连接')
    streaming.value = false
  } finally {
    loading.value = false
  }
}

async function quickAction(action: string) {
  const contentText = props.content.map(b => b.content).join('\n')
  const selection = window.getSelection()?.toString()
  
  loading.value = true
  streaming.value = true
  streamingContent.value = ''
  
  messages.value.push({ 
    role: 'user', 
    content: `[执行操作: ${action}]` 
  })
  
  scrollToBottom()
  
  try {
    const response = await aiApi.assistStream({
      document_id: props.documentId,
      action,
      selected_text: selection || undefined,
      instruction: undefined
    })
    
    const reader = response.body?.getReader()
    if (!reader) throw new Error('No reader')
    
    const decoder = new TextDecoder()
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      const text = decoder.decode(value)
      const lines = text.split('\n')
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') {
            messages.value.push({ role: 'assistant', content: streamingContent.value })
            streamingContent.value = ''
            streaming.value = false
          } else {
            streamingContent.value += data
            scrollToBottom()
          }
        }
      }
    }
  } catch (error) {
    ElMessage.error('请求失败')
    streaming.value = false
  } finally {
    loading.value = false
  }
}

function insertToDoc(text: string) {
  emit('insert', text)
  ElMessage.success('已插入到文档末尾')
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text)
  ElMessage.success('已复制到剪贴板')
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}
</script>

<style scoped>
.ai-chat-panel {
  width: 400px;
  border-left: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.panel-header {
  padding: 15px 20px;
  border-bottom: 1px solid #e4e7ed;
  background: #f5f7fa;
}

.panel-header h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.quick-actions {
  padding: 12px 15px;
  border-bottom: 1px solid #e4e7ed;
  background: #fafafa;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 15px;
}

.message {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e4e7ed;
  color: #909399;
  flex-shrink: 0;
}

.message.assistant .message-avatar {
  background: #409eff;
  color: #fff;
}

.message-content {
  flex: 1;
  min-width: 0;
}

.message-text {
  padding: 10px 14px;
  border-radius: 12px;
  background: #f4f4f5;
  font-size: 14px;
  line-height: 1.6;
  color: #303133;
}

.message.assistant .message-text {
  background: #ecf5ff;
}

.message-actions {
  margin-top: 6px;
  display: flex;
  gap: 8px;
}

.streaming .message-text {
  background: #ecf5ff;
}

.cursor {
  animation: blink 1s infinite;
  color: #409eff;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.chat-input {
  padding: 15px;
  border-top: 1px solid #e4e7ed;
  background: #fafafa;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
}

.hint {
  font-size: 12px;
  color: #909399;
}
</style>