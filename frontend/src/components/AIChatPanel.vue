<template>
  <div class="ai-chat-panel">
    <div class="panel-header">
      <div class="header-title">
        <div class="ai-avatar">
          <el-icon><Star /></el-icon>
        </div>
        <div class="title-text">
          <h3>AI 写作助手</h3>
          <span>随时为您提供创作灵感</span>
        </div>
      </div>
    </div>
    
    <div class="quick-actions">
      <div class="actions-title">快捷操作</div>
      <div class="action-buttons">
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
      </div>
    </div>

    <div class="chat-messages" ref="messagesContainer">
      <div
        v-for="(msg, index) in messages"
        :key="index"
        class="message"
        :class="msg.role"
      >
        <div class="message-avatar">
          <el-icon v-if="msg.role === 'assistant'"><Star /></el-icon>
          <el-icon v-else><User /></el-icon>
        </div>
        <div class="message-content">
          <div class="message-text markdown-body" v-html="formatMessage(msg.content)" />
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
        <div class="message-avatar">
          <el-icon><Star /></el-icon>
        </div>
        <div class="message-content">
          <div class="message-text markdown-body">
            <span v-html="formatMessage(streamingContent)"></span><span class="cursor">|</span>
          </div>
        </div>
      </div>
    </div>

    <div class="chat-input">
      <el-input
        v-model="inputMessage"
        type="textarea"
        :rows="3"
        placeholder="输入你的问题或指令...&#10;选中文字后点击上方按钮可直接修改"
        class="coffee-textarea"
        @keydown.enter.ctrl.prevent="sendMessage"
      />
      <div class="input-actions">
        <span class="hint">
          <el-icon><InfoFilled /></el-icon>
          Ctrl + Enter 发送
        </span>
        <el-button type="primary" @click="sendMessage" :loading="loading" class="send-btn">
          <el-icon><Promotion /></el-icon> 发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { marked } from 'marked'
import { aiApi } from '@/api'
import { ElMessage } from 'element-plus'
import { Star, Compass, Edit, Brush, Right, User, DocumentAdd, CopyDocument, Promotion, InfoFilled } from '@element-plus/icons-vue'

marked.setOptions({ gfm: true, breaks: true })

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

function formatMessage(text: string): string {
  if (!text || typeof text !== 'string') return ''
  try {
    return marked.parse(text.trim()) as string
  } catch {
    return text.replace(/\n/g, '<br>')
  }
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
  const selection = window.getSelection()?.toString()
  await runAssistAction(action, selection || undefined)
}

/** 由父组件调用：对指定文本执行润色（如从编辑器快捷栏「AI 润色」触发） */
async function polishWithText(text: string) {
  await runAssistAction('polish', text)
}

/** 根据操作类型和选中文本生成展示用的用户消息 */
function getActionUserMessage(action: string, selectedText?: string): string {
  const t = selectedText?.trim()
  const actionLabels: Record<string, string> = {
    guide: '请对当前文档给出写作指导',
    revise: t ? `请修改以下内容：\n\n${t}` : '请修改选中的内容',
    polish: t ? `请润色以下内容：\n\n${t}` : '请润色选中的内容',
    continue: '请根据已有内容续写下一段',
    brainstorm: '请围绕当前内容进行头脑风暴',
    expand: t ? `请扩展以下内容：\n\n${t}` : '请扩展选中的内容',
    summarize: '请总结当前文档要点',
  }
  return actionLabels[action] || (t ? `请求：\n\n${t}` : `执行操作：${action}`)
}

async function runAssistAction(action: string, selectedText?: string) {
  loading.value = true
  streaming.value = true
  streamingContent.value = ''
  messages.value.push({ role: 'user', content: getActionUserMessage(action, selectedText) })
  scrollToBottom()
  try {
    const response = await aiApi.assistStream({
      document_id: props.documentId,
      action,
      selected_text: selectedText,
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

defineExpose({ polishWithText })

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

<style scoped lang="scss">
.ai-chat-panel {
  width: 380px;
  flex-shrink: 0;
  position: relative;
  z-index: 1; /* 低于编辑区，保证快捷栏能浮在上方 */
  border-left: 1px solid var(--coffee-border);
  display: flex;
  flex-direction: column;
  background: var(--coffee-bg-card);
}

.panel-header {
  padding: 20px;
  border-bottom: 1px solid var(--coffee-border);
  background: linear-gradient(135deg, var(--coffee-bg-warm) 0%, var(--coffee-bg) 100%);
  
  .header-title {
    display: flex;
    align-items: center;
    gap: 12px;
    
    .ai-avatar {
      width: 44px;
      height: 44px;
      background: linear-gradient(135deg, var(--coffee-primary) 0%, var(--coffee-primary-light) 100%);
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      
      .el-icon {
        font-size: 22px;
        color: #fff;
      }
    }
    
    .title-text {
      h3 {
        font-size: 16px;
        font-weight: 600;
        color: var(--coffee-text);
        margin: 0 0 2px;
      }
      
      span {
        font-size: 12px;
        color: var(--coffee-text-light);
      }
    }
  }
}

.quick-actions {
  padding: 16px 20px;
  border-bottom: 1px solid var(--coffee-border);
  background: var(--coffee-bg);
  
  .actions-title {
    font-size: 12px;
    font-weight: 600;
    color: var(--coffee-text-light);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 12px;
  }
  
  .action-buttons {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    
    .el-button {
      height: 36px;
      border-radius: 8px;
      border-color: var(--coffee-border);
      color: var(--coffee-text-secondary);
      background: var(--coffee-bg-card);
      
      &:hover {
        border-color: var(--coffee-primary);
        color: var(--coffee-primary);
        background: rgba(166, 94, 46, 0.04);
      }
      
      .el-icon {
        margin-right: 4px;
      }
    }
  }
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: var(--coffee-bg);
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  
  .message-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--coffee-border);
    color: var(--coffee-text-light);
    flex-shrink: 0;
  }
  
  .message-content {
    flex: 1;
    min-width: 0;
  }
  
  .message-text {
    padding: 12px 16px;
    border-radius: 12px;
    background: var(--coffee-bg-card);
    font-size: 14px;
    line-height: 1.7;
    color: var(--coffee-text);
    box-shadow: 0 2px 8px var(--coffee-shadow);

    &.markdown-body {
      :deep(p) { margin: 0 0 0.75em; &:last-child { margin-bottom: 0; } }
      :deep(p + p) { margin-top: 0.75em; }
      :deep(strong) { font-weight: 700; color: var(--coffee-text); }
      :deep(em) { font-style: italic; }
      :deep(code) {
        padding: 0.15em 0.4em;
        font-size: 0.9em;
        background: rgba(93, 58, 26, 0.08);
        border-radius: 4px;
        font-family: ui-monospace, monospace;
      }
      :deep(pre) {
        margin: 0.75em 0;
        padding: 12px;
        overflow-x: auto;
        background: rgba(93, 58, 26, 0.06);
        border-radius: 8px;
        font-size: 13px;
        code { padding: 0; background: none; }
      }
      :deep(ul), :deep(ol) { margin: 0.5em 0; padding-left: 1.5em; }
      :deep(li) { margin: 0.25em 0; }
      :deep(blockquote) {
        margin: 0.75em 0;
        padding-left: 1em;
        border-left: 3px solid var(--coffee-primary-light);
        color: var(--coffee-text-secondary);
      }
      :deep(h1), :deep(h2), :deep(h3) {
        margin: 1em 0 0.5em;
        font-weight: 600;
        color: var(--coffee-text);
        line-height: 1.3;
      }
      :deep(h1) { font-size: 1.25em; }
      :deep(h2) { font-size: 1.1em; }
      :deep(h3) { font-size: 1em; }
      :deep(a) {
        color: var(--coffee-primary);
        text-decoration: none;
        &:hover { text-decoration: underline; }
      }
      :deep(hr) { border: none; border-top: 1px solid var(--coffee-border); margin: 1em 0; }
    }
  }
  
  &.assistant {
    .message-avatar {
      background: linear-gradient(135deg, var(--coffee-primary-light) 0%, var(--coffee-primary) 100%);
      color: #fff;
    }
    
    .message-text {
      background: linear-gradient(135deg, #fff 0%, var(--coffee-bg-warm) 100%);
      border: 1px solid var(--coffee-border-light);
    }
  }
  
  .message-actions {
    margin-top: 8px;
    display: flex;
    gap: 8px;
    
    .el-button {
      color: var(--coffee-text-light);
      font-size: 12px;
      
      &:hover {
        color: var(--coffee-primary);
      }
    }
  }
}

.streaming .message-text {
  background: linear-gradient(135deg, #fff 0%, var(--coffee-bg-warm) 100%);
}

.cursor {
  animation: blink 1s infinite;
  color: var(--coffee-primary);
  font-weight: bold;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.chat-input {
  padding: 16px 20px;
  border-top: 1px solid var(--coffee-border);
  background: var(--coffee-bg-card);
}

.coffee-textarea {
  :deep(.el-textarea__inner) {
    background: var(--coffee-bg);
    border-color: var(--coffee-border);
    color: var(--coffee-text);
    border-radius: 10px;
    padding: 12px;
    
    &:focus {
      border-color: var(--coffee-primary-light);
    }
    
    &::placeholder {
      color: var(--coffee-text-light);
    }
  }
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  
  .hint {
    font-size: 12px;
    color: var(--coffee-text-light);
    display: flex;
    align-items: center;
    gap: 4px;
    
    .el-icon {
      font-size: 14px;
    }
  }
  
  .send-btn {
    height: 36px;
    padding: 0 20px;
    border-radius: 8px;
    background: linear-gradient(135deg, var(--coffee-primary) 0%, var(--coffee-primary-light) 100%);
    border: none;
    
    &:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(166, 94, 46, 0.25);
    }
    
    .el-icon {
      margin-right: 4px;
    }
  }
}

@media (max-width: 768px) {
  .ai-chat-panel {
    width: 100%;
    border-left: none;
    border-top: 1px solid var(--coffee-border);
  }
}
</style>
