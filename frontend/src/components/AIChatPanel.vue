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
        <el-button size="small" @click="quickAction('format_style')">
          <el-icon><SetUp /></el-icon> 调整样式
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
          <div
            v-if="msg.role === 'assistant' && msg.format === 'markdown' && index > 0"
            class="format-meta"
          >
            <span class="format-tag">Markdown</span>
            <span v-if="msg.blocks && msg.blocks.length > 1" class="block-count">已解析 {{ msg.blocks.length }} 个块</span>
          </div>
          <div v-if="msg.role === 'assistant' && index > 0" class="message-actions">
            <!-- 如果是改写类操作，显示预览修改按钮 -->
            <template v-if="msg.actionType && ['polish', 'revise', 'expand', 'format_style'].includes(msg.actionType)">
              <el-button link size="small" type="primary" @click="showDiffForMessage(msg)">
                <el-icon><View /></el-icon> 预览修改
              </el-button>
            </template>
            <el-button link size="small" @click="insertToDoc(msg)">
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
            <span v-if="assistStreamDisplay === 'full'" v-html="formatMessage(streamingContent)"></span>
            <span v-else>生成中...</span>
            <span v-if="assistStreamDisplay === 'full'" class="cursor">|</span>
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
        <el-button type="primary" @click="sendMessage" :loading="loading" class="btn btn-primary btn-sm">
          <el-icon><Promotion /></el-icon> 发送
        </el-button>
      </div>
    </div>

    <!-- AI Diff 查看器 -->
    <AIDiffViewer
      v-model:visible="diffVisible"
      :original-text="diffOriginalText"
      :rewritten-text="diffRewrittenText"
      @accept="onDiffAccept"
      @reject="onDiffReject"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { aiApi } from '@/api'
import type { Block } from '@/api/types'
import { ElMessage } from 'element-plus'
import { Star, Compass, Edit, Brush, Right, User, DocumentAdd, CopyDocument, Promotion, InfoFilled, View, SetUp } from '@element-plus/icons-vue'
import AIDiffViewer from './AIDiffViewer.vue'

marked.setOptions({ gfm: true, breaks: true })

type AssistChatMessage = {
  role: string
  content: string
  format?: string
  blocks?: Block[]
  actionType?: string
  originalText?: string
  blockIndex?: number
  blockIndices?: number[]
}

function feedSseChunk(chunk: string, acc: { buf: string }, onPayload: (data: string) => void) {
  acc.buf += chunk
  const parts = acc.buf.split('\n')
  acc.buf = parts.pop() ?? ''
  for (const line of parts) {
    if (line.startsWith('data: ')) {
      onPayload(line.slice(6))
    }
  }
}

function flushSse(acc: { buf: string }, onPayload: (data: string) => void) {
  if (!acc.buf) return
  const tail = acc.buf
  acc.buf = ''
  for (const line of tail.split('\n')) {
    if (line.startsWith('data: ')) {
      onPayload(line.slice(6))
    }
  }
}

const props = defineProps<{
  documentId: number
}>()

const emit = defineEmits<{
  (e: 'insert', text: string): void
  (e: 'insertBlocks', blocks: Block[]): void
  (e: 'replace', oldText: string, newText: string, blockIndex?: number, blocks?: Block[], blockIndices?: number[]): void
  (e: 'preview', payload: { blockIndex?: number; blockIndices?: number[]; text: string; blocks?: Block[] }): void
  (e: 'previewCancel'): void
}>()

const messages = ref<AssistChatMessage[]>([
  { role: 'assistant', content: '你好！我是你的 AI 写作助手。我可以帮你指导写作、修改润色、续写文章等。有什么可以帮你的吗？' }
])

const inputMessage = ref('')
const loading = ref(false)
const streaming = ref(false)
const streamingContent = ref('')
const messagesContainer = ref<HTMLElement>()

// Diff 查看器状态（类似 Cursor：改写后展示对照，用户选择接受/拒绝）
const diffVisible = ref(false)
const diffOriginalText = ref('')
const diffRewrittenText = ref('')
const lastSelectedText = ref('')
/** 当前 diff 对应的块索引，用于接受时精确替换到该块 */
const pendingReplaceBlockIndex = ref<number | undefined>(undefined)
/** 当前 diff 对应的块索引集合，用于接受时批量替换 */
const pendingReplaceBlockIndices = ref<number[] | undefined>(undefined)
/** 当前 diff 对应的结构化 blocks，接受时优先用于替换 */
const pendingReplaceBlocks = ref<Block[] | undefined>(undefined)
/** 是否在对话框中展示流式内容（Cursor 风格：改写类只展示在 diff/编辑器预览里） */
const assistStreamDisplay = ref<'full' | 'minimal'>('full')

function showDiffForMessage(msg: AssistChatMessage) {
  diffOriginalText.value = msg.originalText || ''
  diffRewrittenText.value = msg.content
  pendingReplaceBlockIndex.value = msg.blockIndex
  pendingReplaceBlockIndices.value = msg.blockIndices
  pendingReplaceBlocks.value = msg.blocks
  diffVisible.value = true
}

function onDiffAccept(text: string) {
  const original = diffOriginalText.value
  const blockIndex = pendingReplaceBlockIndex.value
  try {
    emit('replace', original, text, blockIndex, pendingReplaceBlocks.value, pendingReplaceBlockIndices.value)
  } catch (e) {
    console.error(e)
    ElMessage.error('应用改写失败：请检查控制台错误')
  }
  pendingReplaceBlockIndex.value = undefined
  pendingReplaceBlockIndices.value = undefined
  pendingReplaceBlocks.value = undefined
  ElMessage.success('已应用到文档')
}

function onDiffReject() {
  pendingReplaceBlockIndex.value = undefined
  pendingReplaceBlockIndices.value = undefined
  pendingReplaceBlocks.value = undefined
  try {
    emit('previewCancel')
  } catch (e) {
    console.error(e)
    ElMessage.error('拒绝修改失败：请检查控制台错误')
  }
  ElMessage.info('已拒绝修改')
}

function formatMessage(text: string): string {
  if (!text || typeof text !== 'string') return ''
  try {
    const html = marked.parse(text.trim()) as string
    return DOMPurify.sanitize(html)
  } catch {
    return DOMPurify.sanitize(text.replace(/\n/g, '<br>'))
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
    const sseAcc = { buf: '' }
    let assistMeta: { format?: string; blocks?: Block[] } | null = null

    const handlePayload = (data: string) => {
      if (data === '[DONE]') {
        const meta = assistMeta
        assistMeta = null
        messages.value.push({
          role: 'assistant',
          content: streamingContent.value,
          format: meta?.format,
          blocks: meta?.blocks,
        })
        streamingContent.value = ''
        streaming.value = false
        return
      }
      if (data.startsWith('[ASSIST_META]')) {
        try {
          assistMeta = JSON.parse(data.slice('[ASSIST_META]'.length)) as { format?: string; blocks?: Block[] }
        } catch {
          assistMeta = null
        }
        return
      }
      streamingContent.value += data
      scrollToBottom()
    }

    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        flushSse(sseAcc, handlePayload)
        break
      }
      feedSseChunk(decoder.decode(value, { stream: true }), sseAcc, handlePayload)
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
async function polishWithText(text: string, blockIndex?: number) {
  await runAssistAction('polish', text, blockIndex)
}

/** 由父组件调用：对选中多个块执行润色 */
async function polishWithSelectedText(text: string, blockIndices: number[]) {
  await runAssistAction('polish', text, undefined, blockIndices)
}

/** 由父组件调用：仅排版优化（不改内容） */
async function formatStyleWithText(text: string, blockIndex?: number) {
  await runAssistAction('format_style', text, blockIndex)
}

/** 由父组件调用：对选中多个块仅排版优化 */
async function formatStyleWithSelectedText(text: string, blockIndices: number[]) {
  await runAssistAction('format_style', text, undefined, blockIndices)
}

/** 由父组件调用：对选中多个块执行修改 */
async function reviseWithSelectedText(text: string, blockIndices: number[]) {
  await runAssistAction('revise', text, undefined, blockIndices)
}

/** 由父组件调用：对选中多个块执行扩展 */
async function expandWithSelectedText(text: string, blockIndices: number[]) {
  await runAssistAction('expand', text, undefined, blockIndices)
}

/** 根据操作类型和选中文本生成展示用的用户消息 */
function getActionUserMessage(action: string, selectedText?: string): string {
  const t = selectedText?.trim()
  const actionLabels: Record<string, string> = {
    guide: '请对当前文档给出写作指导',
    revise: t ? `请修改以下内容：\n\n${t}` : '请修改选中的内容',
    polish: t ? `请润色以下内容：\n\n${t}` : '请润色选中的内容',
    format_style: t
      ? `请只调整以下文稿的结构与排版（不要改内容）：\n\n${t}`
      : '请只调整当前文档的结构与排版（不要改内容）',
    continue: '请根据已有内容续写下一段',
    brainstorm: '请围绕当前内容进行头脑风暴',
    expand: t ? `请扩展以下内容：\n\n${t}` : '请扩展选中的内容',
    summarize: '请总结当前文档要点',
  }
  return actionLabels[action] || (t ? `请求：\n\n${t}` : `执行操作：${action}`)
}

async function runAssistAction(action: string, selectedText?: string, blockIndex?: number, blockIndices?: number[]) {
  loading.value = true
  streaming.value = true
  streamingContent.value = ''
  assistStreamDisplay.value = ['polish', 'revise', 'expand', 'continue', 'format_style'].includes(action) ? 'minimal' : 'full'

  const originalText = selectedText || ''
  lastSelectedText.value = originalText

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
    const sseAcc = { buf: '' }
    let assistMeta: { format?: string; blocks?: Block[] } | null = null

    const handlePayload = (data: string) => {
      if (data === '[DONE]') {
        const rewritten = streamingContent.value
        const meta = assistMeta
        assistMeta = null
        const assistantMsg: AssistChatMessage = {
          role: 'assistant',
          content: rewritten,
          format: meta?.format,
          blocks: meta?.blocks,
          actionType: action,
          originalText: originalText,
          blockIndex,
          blockIndices,
        }
        streamingContent.value = ''
        streaming.value = false
        const isRewriteAction = ['polish', 'revise', 'expand', 'continue', 'format_style'].includes(action)
        const canPreview = isRewriteAction && originalText && rewritten
        if (canPreview) {
          nextTick(() => showDiffForMessage(assistantMsg))
          emit('preview', { blockIndex, blockIndices, text: rewritten, blocks: meta?.blocks })
        } else {
          messages.value.push(assistantMsg)
        }
        return
      }
      if (data.startsWith('[ASSIST_META]')) {
        try {
          assistMeta = JSON.parse(data.slice('[ASSIST_META]'.length)) as { format?: string; blocks?: Block[] }
        } catch {
          assistMeta = null
        }
        return
      }
      streamingContent.value += data
      scrollToBottom()
    }

    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        flushSse(sseAcc, handlePayload)
        break
      }
      feedSseChunk(decoder.decode(value, { stream: true }), sseAcc, handlePayload)
    }
  } catch (error) {
    ElMessage.error('请求失败')
    streaming.value = false
  } finally {
    loading.value = false
  }
}

defineExpose({
  polishWithText: (text: string, blockIndex?: number) => polishWithText(text, blockIndex),
  polishWithSelectedText: (text: string, blockIndices: number[]) => polishWithSelectedText(text, blockIndices),
  formatStyleWithText: (text: string, blockIndex?: number) => formatStyleWithText(text, blockIndex),
  formatStyleWithSelectedText: (text: string, blockIndices: number[]) => formatStyleWithSelectedText(text, blockIndices),
  reviseWithSelectedText: (text: string, blockIndices: number[]) => reviseWithSelectedText(text, blockIndices),
  expandWithSelectedText: (text: string, blockIndices: number[]) => expandWithSelectedText(text, blockIndices),
})

function insertToDoc(msg: AssistChatMessage) {
  if (msg.blocks?.length) {
    emit('insertBlocks', msg.blocks)
  } else {
    emit('insert', msg.content)
  }
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
        background: var(--coffee-sidebar-shadow);
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

    .format-meta {
      margin: 6px 0 0 4px;
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 11px;
      color: var(--coffee-text-light);

      .format-tag {
        padding: 2px 8px;
        border-radius: 6px;
        background: var(--coffee-bg-hover);
        border: 1px solid var(--coffee-border);
      }

      .block-count {
        opacity: 0.85;
      }
    }
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
        background: var(--coffee-shadow);
        border-radius: 4px;
        font-family: ui-monospace, monospace;
      }
      :deep(pre) {
        margin: 0.75em 0;
        padding: 12px;
        overflow-x: auto;
        background: var(--coffee-bg-hover);
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
      background: linear-gradient(135deg, var(--coffee-bg-card) 0%, var(--coffee-bg-warm) 100%);
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
  background: linear-gradient(135deg, var(--coffee-bg-card) 0%, var(--coffee-bg-warm) 100%);
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
}

@media (max-width: 768px) {
  .ai-chat-panel {
    width: 100%;
    border-left: none;
    border-top: 1px solid var(--coffee-border);
  }
}
</style>
