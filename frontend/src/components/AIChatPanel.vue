<template>
  <div class="ai-chat-panel">
    <div class="panel-header">
      <div class="header-top">
        <div class="header-title">
          <div class="ai-avatar">
            <span class="avatar-glyph">墨</span>
          </div>
          <div class="title-text">
            <h3>小墨</h3>
            <span>墨心里的写作搭档</span>
          </div>
        </div>
      </div>

      <div class="style-picker">
        <span class="style-label">文风</span>
        <div class="style-chips">
          <button
            type="button"
            class="style-chip"
            :class="{ active: !selectedStyleAgentId }"
            @click="selectedStyleAgentId = undefined"
          >默认</button>
          <button
            v-for="a in styleAgents"
            :key="a.id"
            type="button"
            class="style-chip"
            :class="{ active: selectedStyleAgentId === a.id }"
            :title="a.is_default ? `${a.name}（默认）` : a.name"
            @click="selectedStyleAgentId = a.id"
          >
            {{ a.name }}
            <span v-if="a.is_default" class="chip-badge">默</span>
          </button>
        </div>
      </div>
    </div>

    <div class="quick-actions">
      <div class="actions-title">快捷操作</div>
      <div class="action-buttons">
        <el-button size="small" @click="quickAction('guide')" style="margin-left: 10px;">
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
          <span v-if="msg.role === 'assistant'" class="mini-glyph">墨</span>
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
            <el-button
              v-if="canReplaceOriginal(msg)"
              link
              size="small"
              type="primary"
              @click="replaceOriginal(msg)"
            >
              <el-icon><Edit /></el-icon> 替换原文
            </el-button>
            <el-dropdown trigger="click" @command="(cmd: string) => insertToDoc(msg, cmd as InsertPos)">
              <el-button link size="small">
                <el-icon><DocumentAdd /></el-icon> 插入文档
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="cursor">插入到光标处</el-dropdown-item>
                  <el-dropdown-item command="end">插入到文末</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button link size="small" @click="copyToClipboard(msg.content)">
              <el-icon><CopyDocument /></el-icon> 复制
            </el-button>
          </div>
        </div>
      </div>

      <div v-if="streaming" class="message assistant streaming">
        <div class="message-avatar">
          <span class="mini-glyph">墨</span>
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
      <div v-if="attachedContext" class="attached-context">
        <div class="attached-head">
          <span class="attached-title">已引用段落</span>
          <button type="button" class="attached-clear" title="清除引用" @click="clearAttachedContext">×</button>
        </div>
        <div class="attached-preview">{{ attachedPreview }}</div>
        <div class="attached-quick">
          <el-button size="small" :disabled="loading" @click="runOnAttached('revise')">修改</el-button>
          <el-button size="small" :disabled="loading" @click="runOnAttached('polish')">润色</el-button>
          <el-button size="small" :disabled="loading" @click="runOnAttached('expand')">扩展</el-button>
        </div>
      </div>
      <el-input
        ref="inputRef"
        v-model="inputMessage"
        type="textarea"
        :rows="3"
        :placeholder="attachedContext
          ? '针对上方引用提出修改要求，例如：语气更轻松、缩短一半…'
          : '输入问题或指令…\n也可在正文点「送到助手」引用段落'"
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
import { ref, computed, nextTick, watch } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { aiApi, styleAgentApi } from '@/api'
import type { Block, StyleAgent } from '@/api/types'
import { ElMessage } from 'element-plus'
import { Compass, Edit, Brush, Right, User, DocumentAdd, CopyDocument, Promotion, InfoFilled, View, SetUp } from '@element-plus/icons-vue'
import AIDiffViewer from './AIDiffViewer.vue'

marked.setOptions({ gfm: true, breaks: true })

type InsertPos = 'cursor' | 'end'

const WELCOME_DEFAULT =
  '你好，我是小墨～可以把正文「送到助手」后提修改要求，或用上方快捷按钮。生成结果可插入到光标处或文末。'

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

type AttachedContext = {
  text: string
  blockIndex?: number
  blockIndices?: number[]
}

function feedSseChunk(chunk: string, acc: { buf: string }, onPayload: (data: string) => void) {
  acc.buf += chunk
  // 按 SSE 事件边界（空行）拆分；同一事件内多行 data: 需用 \n 拼接，否则会丢掉换行导致排版标记失效
  const events = acc.buf.split('\n\n')
  acc.buf = events.pop() ?? ''
  for (const event of events) {
    if (!event.trim()) continue
    const dataLines: string[] = []
    for (const line of event.split('\n')) {
      if (line.startsWith('data: ')) dataLines.push(line.slice(6))
      else if (line.startsWith('data:')) dataLines.push(line.slice(5))
    }
    if (dataLines.length) onPayload(dataLines.join('\n'))
  }
}

function flushSse(acc: { buf: string }, onPayload: (data: string) => void) {
  if (!acc.buf) return
  const tail = acc.buf
  acc.buf = ''
  const dataLines: string[] = []
  for (const line of tail.split('\n')) {
    if (line.startsWith('data: ')) dataLines.push(line.slice(6))
    else if (line.startsWith('data:')) dataLines.push(line.slice(5))
  }
  if (dataLines.length) onPayload(dataLines.join('\n'))
}

const props = defineProps<{
  documentId: number
  projectId?: number
}>()

const emit = defineEmits<{
  (e: 'insert', text: string, position?: InsertPos): void
  (e: 'insertBlocks', blocks: Block[], position?: InsertPos): void
  (e: 'replace', oldText: string, newText: string, blockIndex?: number, blocks?: Block[], blockIndices?: number[]): void
  (e: 'preview', payload: { blockIndex?: number; blockIndices?: number[]; text: string; blocks?: Block[] }): void
  (e: 'previewCancel'): void
}>()

const styleAgents = ref<StyleAgent[]>([])
const selectedStyleAgentId = ref<number | undefined>(undefined)

async function loadStyleAgents() {
  try {
    const { data } = await styleAgentApi.list()
    styleAgents.value = Array.isArray(data) ? data : []
    const def = styleAgents.value.find((a) => a.is_default)
    selectedStyleAgentId.value = def?.id
  } catch {
    styleAgents.value = []
  }
}

watch(
  () => props.documentId,
  () => loadStyleAgents(),
  { immediate: true }
)

const messages = ref<AssistChatMessage[]>([
  {
    role: 'assistant',
    content: WELCOME_DEFAULT,
  },
])

const inputMessage = ref('')
const inputRef = ref<{ focus?: () => void; textarea?: HTMLTextAreaElement } | null>(null)
const loading = ref(false)
const streaming = ref(false)
const streamingContent = ref('')
const messagesContainer = ref<HTMLElement | null>(null)

const attachedContext = ref<AttachedContext | null>(null)
/** 发送自由对话时暂存引用，便于回复后「替换原文」 */
const pendingAskContext = ref<AttachedContext | null>(null)

const attachedPreview = computed(() => {
  const t = attachedContext.value?.text?.trim() || ''
  if (t.length <= 120) return t
  return `${t.slice(0, 120)}…`
})

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

function clearAttachedContext() {
  attachedContext.value = null
}

function attachContext(payload: AttachedContext) {
  const text = (payload.text || '').trim()
  if (!text) {
    ElMessage.warning('没有可引用的内容')
    return
  }
  attachedContext.value = {
    text,
    blockIndex: payload.blockIndex,
    blockIndices: payload.blockIndices,
  }
  nextTick(() => {
    const el = inputRef.value?.textarea || (inputRef.value as any)?.$el?.querySelector?.('textarea')
    el?.focus?.()
  })
  ElMessage.success('已引用到助手，可直接提修改要求')
}

function runOnAttached(action: string) {
  const ctx = attachedContext.value
  if (!ctx?.text.trim()) {
    ElMessage.warning('请先引用段落')
    return
  }
  void runAssistAction(action, ctx.text, ctx.blockIndex, ctx.blockIndices)
}

function canReplaceOriginal(msg: AssistChatMessage) {
  if (!msg.content?.trim()) return false
  if (msg.blockIndex != null && msg.blockIndex >= 0) return true
  if (msg.blockIndices?.length) return true
  return false
}

function replaceOriginal(msg: AssistChatMessage) {
  const original = msg.originalText || ''
  try {
    emit('replace', original, msg.content, msg.blockIndex, msg.blocks, msg.blockIndices)
    ElMessage.success('已替换原文')
  } catch (e) {
    console.error(e)
    ElMessage.error('替换失败')
  }
}

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

  const instruction = inputMessage.value.trim()
  const ctx = attachedContext.value
  let userMsg = instruction
  if (ctx?.text.trim()) {
    userMsg =
      `请针对以下文稿内容进行修改或回答（优先直接给出可用正文）：\n\n` +
      `---\n${ctx.text.trim()}\n---\n\n` +
      `我的要求：${instruction}`
    pendingAskContext.value = { ...ctx }
  } else {
    pendingAskContext.value = null
  }

  messages.value.push({ role: 'user', content: userMsg })
  inputMessage.value = ''
  loading.value = true
  streaming.value = true
  streamingContent.value = ''
  assistStreamDisplay.value = 'full'

  scrollToBottom()

  try {
    const response = await aiApi.chatStream({
      document_id: props.documentId,
      messages: messages.value.map(m => ({ role: m.role, content: m.content })),
      include_memory: true,
      style_agent_id: selectedStyleAgentId.value,
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
        const ask = pendingAskContext.value
        pendingAskContext.value = null
        messages.value.push({
          role: 'assistant',
          content: streamingContent.value,
          format: meta?.format,
          blocks: meta?.blocks,
          originalText: ask?.text,
          blockIndex: ask?.blockIndex,
          blockIndices: ask?.blockIndices,
          actionType: ask ? 'revise' : undefined,
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
    pendingAskContext.value = null
  } finally {
    loading.value = false
  }
}

async function quickAction(action: string) {
  const fromAttach = attachedContext.value?.text?.trim()
  const selection = window.getSelection()?.toString()?.trim()
  const text = fromAttach || selection || undefined
  const blockIndex = fromAttach ? attachedContext.value?.blockIndex : undefined
  const blockIndices = fromAttach ? attachedContext.value?.blockIndices : undefined
  await runAssistAction(action, text, blockIndex, blockIndices)
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
      instruction: undefined,
      style_agent_id: selectedStyleAgentId.value,
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
  attachContext,
})

function insertToDoc(msg: AssistChatMessage, position: InsertPos = 'cursor') {
  if (msg.blocks?.length) {
    emit('insertBlocks', msg.blocks, position)
  } else {
    emit('insert', msg.content, position)
  }
  ElMessage.success(position === 'end' ? '已插入到文档末尾' : '已插入到光标处')
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
  padding: 16px 20px;
  border-bottom: 1px solid var(--coffee-border);
  background: linear-gradient(135deg, var(--coffee-bg-warm) 0%, var(--coffee-bg) 100%);
  display: flex;
  flex-direction: column;
  gap: 14px;

  .header-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .style-picker {
    display: flex;
    align-items: flex-start;
    gap: 10px;
  }

  .style-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--coffee-text-muted);
    flex-shrink: 0;
    line-height: 30px;
  }

  .style-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    flex: 1;
    min-width: 0;
  }

  .style-chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    max-width: 120px;
    padding: 5px 10px;
    border-radius: 8px;
    border: 1px solid var(--coffee-border);
    background: var(--coffee-bg-card);
    color: var(--coffee-text-secondary);
    font-size: 12px;
    cursor: pointer;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    transition: border-color 0.15s, background 0.15s, color 0.15s;
    &:hover {
      border-color: var(--coffee-primary);
      color: var(--coffee-primary);
      background: var(--coffee-bg-warm);
    }
    &.active {
      border-color: var(--coffee-primary);
      background: var(--coffee-bg-warm);
      color: var(--coffee-primary);
      font-weight: 600;
    }
    .chip-badge {
      flex-shrink: 0;
      font-size: 10px;
      line-height: 1;
      padding: 2px 4px;
      border-radius: 4px;
      background: var(--coffee-primary);
      color: #fff;
    }
  }

  .header-title {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;

    .ai-avatar {
      width: 44px;
      height: 44px;
      background: linear-gradient(135deg, var(--coffee-primary) 0%, var(--coffee-primary-light) 100%);
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;

      .avatar-glyph {
        font-size: 18px;
        font-weight: 700;
        color: #fff;
        letter-spacing: 0.02em;
      }
    }

    .title-text {
      min-width: 0;
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

      .mini-glyph {
        font-size: 13px;
        font-weight: 700;
        line-height: 1;
      }
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

.attached-context {
  margin-bottom: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--coffee-border);
  background: var(--coffee-bg-warm, var(--coffee-bg));
}

.attached-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.attached-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--coffee-primary);
}

.attached-clear {
  border: none;
  background: transparent;
  color: var(--coffee-text-light);
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
  padding: 0 4px;

  &:hover {
    color: var(--coffee-text);
  }
}

.attached-preview {
  font-size: 13px;
  line-height: 1.5;
  color: var(--coffee-text);
  white-space: pre-wrap;
  max-height: 72px;
  overflow: hidden;
}

.attached-quick {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
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
