<template>
  <div class="block-editor" :class="{ 'focus-mode': isFocusMode }" @click="handleEditorClick">
    <div
      v-for="(block, index) in modelValue"
      :key="block.id"
      class="block-wrapper"
      :class="{ 'is-focused': focusedIndex === index, 'is-toolbar-visible': toolbarVisibleIndex === index, [`type-${block.type}`]: true }"
      @mouseenter="onBlockMouseEnter(index)"
      @mouseleave="onBlockMouseLeave"
    >
      <!-- 快捷操作栏：悬停 3s 或选中内容 3s 后显示 -->
      <Transition name="toolbar">
        <div v-show="toolbarVisibleIndex === index" class="quick-toolbar" @mousedown.prevent>
          <button type="button" class="toolbar-btn" :disabled="!canUndo" @click.stop="undo()" title="撤销 (Ctrl+Z)">
            <el-icon><RefreshLeft /></el-icon>
            <span>撤销</span>
          </button>
          <button type="button" class="toolbar-btn" :disabled="!canRedo" @click.stop="redo()" title="重做 (Ctrl+Shift+Z)">
            <el-icon><RefreshRight /></el-icon>
            <span>重做</span>
          </button>
          <span class="toolbar-divider" />
          <button type="button" class="toolbar-btn" :class="{ active: block.type === 'heading' }" @click.stop="handleCommand('heading', index)" title="标题 (Ctrl+1)">
            <el-icon><Top /></el-icon>
            <span>标题</span>
          </button>
          <button type="button" class="toolbar-btn" :class="{ active: block.type === 'subheading' }" @click.stop="handleCommand('subheading', index)" title="小标题 (Ctrl+2)">
            <el-icon><Rank /></el-icon>
            <span>小标题</span>
          </button>
          <button type="button" class="toolbar-btn" :class="{ active: block.type === 'quote' }" @click.stop="handleCommand('quote', index)" title="引用 (Ctrl+3)">
            <el-icon><ChatDotRound /></el-icon>
            <span>引用</span>
          </button>
          <button type="button" class="toolbar-btn" :class="{ active: block.type === 'list' }" @click.stop="handleCommand('list', index)" title="列表 (Ctrl+4)">
            <el-icon><List /></el-icon>
            <span>列表</span>
          </button>
          <button type="button" class="toolbar-btn" :class="{ active: block.type === 'code' }" @click.stop="handleCommand('code', index)" title="代码块 (Ctrl+5)">
            <el-icon><Operation /></el-icon>
            <span>代码</span>
          </button>
          <button type="button" class="toolbar-btn" :class="{ active: block.type === 'divider' }" @click.stop="handleCommand('divider', index)" title="分割线 (Ctrl+6)">
            <el-icon><Minus /></el-icon>
            <span>分割线</span>
          </button>
          <button type="button" class="toolbar-btn" :class="{ active: block.type === 'paragraph' }" @click.stop="handleCommand('paragraph', index)" title="正文 (Ctrl+0)">
            <el-icon><Document /></el-icon>
            <span>正文</span>
          </button>
          <span class="toolbar-divider" />
          <button type="button" class="toolbar-btn ai-btn" @click.stop="emitPolish(index)" title="AI 润色">
            <el-icon><Brush /></el-icon>
            <span>AI 润色</span>
          </button>
          <span class="toolbar-divider" />
          <button type="button" class="toolbar-btn format-btn" :class="{ active: isFormatActive(index, 'bold') }" @click.stop="applyFormat(index, 'bold')" title="加粗 (Ctrl+B)">
            <span class="fmt-bold">B</span>
          </button>
          <button type="button" class="toolbar-btn format-btn" :class="{ active: isFormatActive(index, 'italic') }" @click.stop="applyFormat(index, 'italic')" title="斜体 (Ctrl+I)">
            <span class="fmt-italic">I</span>
          </button>
          <button type="button" class="toolbar-btn format-btn" :class="{ active: isFormatActive(index, 'underline') }" @click.stop="applyFormat(index, 'underline')" title="下划线 (Ctrl+U)">
            <span class="fmt-underline">U</span>
          </button>
          <span class="toolbar-divider" />
          <button type="button" class="toolbar-btn delete" :disabled="modelValue.length <= 1" @click.stop="handleCommand('delete', index)" title="删除块 (Ctrl+Shift+D)">
            <el-icon><Delete /></el-icon>
          </button>
        </div>
      </Transition>
      <div class="block-handle" @click.stop="addBlock(index)">
        <el-icon><Plus /></el-icon>
      </div>
      
      <div
        :ref="el => setBlockRef(el, index)"
        class="block-content"
        :data-type="block.type"
        contenteditable="true"
        @input="updateBlock(index)"
        @focus="onBlockFocus(index)"
        @blur="handleBlur"
        @contextmenu.prevent="onBlockContextMenu(index, $event)"
        @keydown.enter.prevent="handleEnter(index, $event)"
        @keydown.backspace="handleBackspace(index, $event)"
        @keydown.up="moveFocus(index, -1, $event)"
        @keydown.down="moveFocus(index, 1, $event)"
        @keydown="handleKeydown(index, $event)"
      />
      
      <div class="block-actions">
        <el-dropdown trigger="click" @command="(cmd: string) => handleCommand(cmd, index)">
          <el-icon class="action-icon" @click.stop><MoreFilled /></el-icon>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="heading">
                <el-icon><Top /></el-icon> 大标题 <span class="shortcut">Ctrl+1</span>
              </el-dropdown-item>
              <el-dropdown-item command="subheading">
                <el-icon><Rank /></el-icon> 小标题 <span class="shortcut">Ctrl+2</span>
              </el-dropdown-item>
              <el-dropdown-item command="quote">
                <el-icon><ChatDotRound /></el-icon> 引用 <span class="shortcut">Ctrl+3</span>
              </el-dropdown-item>
              <el-dropdown-item command="list">
                <el-icon><List /></el-icon> 列表 <span class="shortcut">Ctrl+4</span>
              </el-dropdown-item>
              <el-dropdown-item command="code">
                <el-icon><Operation /></el-icon> 代码块 <span class="shortcut">Ctrl+5</span>
              </el-dropdown-item>
              <el-dropdown-item command="divider">
                <el-icon><Minus /></el-icon> 分割线 <span class="shortcut">Ctrl+6</span>
              </el-dropdown-item>
              <el-dropdown-item divided command="paragraph">
                <el-icon><Document /></el-icon> 正文 <span class="shortcut">Ctrl+0</span>
              </el-dropdown-item>
              <el-dropdown-item command="delete" class="delete-item">
                <el-icon><Delete /></el-icon> 删除
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
    
    <!-- 右键快捷菜单 -->
    <Teleport to="body">
      <Transition name="context-menu">
        <div
          v-show="contextMenu.visible"
          class="context-menu"
          :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
          @mousedown.prevent
          @click.stop
        >
          <div class="context-menu-section">
            <button type="button" class="context-item" :disabled="!canUndo" @click="handleContextAction('undo')">
              <el-icon><RefreshLeft /></el-icon>
              <span>撤销</span>
              <span class="shortcut">Ctrl+Z</span>
            </button>
            <button type="button" class="context-item" :disabled="!canRedo" @click="handleContextAction('redo')">
              <el-icon><RefreshRight /></el-icon>
              <span>重做</span>
              <span class="shortcut">Ctrl+Y</span>
            </button>
          </div>
          <div class="context-menu-divider" />
          <div class="context-menu-section">
            <button type="button" class="context-item" :class="{ active: contextBlock && modelValue[contextMenu.blockIndex]?.type === 'heading' }" @click="handleContextAction('heading')">
              <el-icon><Top /></el-icon>
              <span>大标题</span>
              <span class="shortcut">Ctrl+1</span>
            </button>
            <button type="button" class="context-item" :class="{ active: contextBlock && modelValue[contextMenu.blockIndex]?.type === 'subheading' }" @click="handleContextAction('subheading')">
              <el-icon><Rank /></el-icon>
              <span>小标题</span>
              <span class="shortcut">Ctrl+2</span>
            </button>
            <button type="button" class="context-item" :class="{ active: contextBlock && modelValue[contextMenu.blockIndex]?.type === 'quote' }" @click="handleContextAction('quote')">
              <el-icon><ChatDotRound /></el-icon>
              <span>引用</span>
              <span class="shortcut">Ctrl+3</span>
            </button>
            <button type="button" class="context-item" :class="{ active: contextBlock && modelValue[contextMenu.blockIndex]?.type === 'list' }" @click="handleContextAction('list')">
              <el-icon><List /></el-icon>
              <span>列表</span>
              <span class="shortcut">Ctrl+4</span>
            </button>
            <button type="button" class="context-item" :class="{ active: contextBlock && modelValue[contextMenu.blockIndex]?.type === 'code' }" @click="handleContextAction('code')">
              <el-icon><Operation /></el-icon>
              <span>代码块</span>
              <span class="shortcut">Ctrl+5</span>
            </button>
            <button type="button" class="context-item" :class="{ active: contextBlock && modelValue[contextMenu.blockIndex]?.type === 'divider' }" @click="handleContextAction('divider')">
              <el-icon><Minus /></el-icon>
              <span>分割线</span>
              <span class="shortcut">Ctrl+6</span>
            </button>
            <button type="button" class="context-item" :class="{ active: contextBlock && modelValue[contextMenu.blockIndex]?.type === 'paragraph' }" @click="handleContextAction('paragraph')">
              <el-icon><Document /></el-icon>
              <span>正文</span>
              <span class="shortcut">Ctrl+0</span>
            </button>
          </div>
          <div class="context-menu-divider" />
          <div class="context-menu-section">
            <button type="button" class="context-item ai-item" @click="handleContextAction('polish')">
              <el-icon><Brush /></el-icon>
              <span>AI 润色</span>
            </button>
          </div>
          <div class="context-menu-divider" />
          <div class="context-menu-section">
            <button type="button" class="context-item" :class="{ active: contextBlock && isFormatActive(contextMenu.blockIndex, 'bold') }" @click="handleContextAction('formatBold')">
              <span class="fmt-bold">B</span>
              <span>加粗</span>
              <span class="shortcut">Ctrl+B</span>
            </button>
            <button type="button" class="context-item" :class="{ active: contextBlock && isFormatActive(contextMenu.blockIndex, 'italic') }" @click="handleContextAction('formatItalic')">
              <span class="fmt-italic">I</span>
              <span>斜体</span>
              <span class="shortcut">Ctrl+I</span>
            </button>
            <button type="button" class="context-item" :class="{ active: contextBlock && isFormatActive(contextMenu.blockIndex, 'underline') }" @click="handleContextAction('formatUnderline')">
              <span class="fmt-underline">U</span>
              <span>下划线</span>
              <span class="shortcut">Ctrl+U</span>
            </button>
          </div>
          <div class="context-menu-divider" />
          <div class="context-menu-section">
            <button type="button" class="context-item" @click="handleContextAction('insertAbove')">
              <el-icon><Plus /></el-icon>
              <span>在上方插入块</span>
            </button>
            <button type="button" class="context-item" @click="handleContextAction('insertBelow')">
              <el-icon><Plus /></el-icon>
              <span>在下方插入块</span>
            </button>
          </div>
          <div class="context-menu-divider" />
          <div class="context-menu-section">
            <button type="button" class="context-item danger" :disabled="modelValue.length <= 1" @click="handleContextAction('delete')">
              <el-icon><Delete /></el-icon>
              <span>删除块</span>
              <span class="shortcut">Ctrl+Shift+D</span>
            </button>
          </div>
        </div>
      </Transition>
    </Teleport>

    <div
      v-if="!modelValue.length"
      class="empty-state"
      @click="addBlock(-1)"
      @contextmenu.prevent="onEmptyAreaContextMenu($event)"
    >
      <div class="empty-icon">
        <el-icon><EditPen /></el-icon>
      </div>
      <span>点击开始写作，记录您的灵感...</span>
      <span class="shortcut-hint">Ctrl+1~6 切换块类型 · Ctrl+B/I/U 格式 · Ctrl+Z/Y 撤销重做 · Ctrl+F 专注模式</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import type { Block } from '@/stores/project'
import { ElMessage } from 'element-plus'
import { Plus, MoreFilled, Top, ChatDotRound, List, Document, Delete, EditPen, Brush, Rank, Operation, Minus, RefreshLeft, RefreshRight } from '@element-plus/icons-vue'

const props = defineProps<{
  modelValue: Block[]
  focusMode?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: Block[]): void
  (e: 'polish', payload: { index: number; text: string }): void
  (e: 'toggleFocusMode'): void
}>()

const focusedIndex = ref(-1)
const blockRefs = ref<Map<number, HTMLElement>>(new Map())
/** 当前显示快捷栏的块索引，-1 为不显示。悬停 3s 或选中 3s 后赋值 */
const toolbarVisibleIndex = ref(-1)
/** 右键快捷菜单状态 */
const contextMenu = ref({ visible: false, x: 0, y: 0, blockIndex: -1 })
const contextBlock = computed(() =>
  contextMenu.value.visible && contextMenu.value.blockIndex >= 0 && props.modelValue[contextMenu.value.blockIndex]
    ? props.modelValue[contextMenu.value.blockIndex]
    : null
)
const isFocusMode = ref(props.focusMode || false)
const TOOLBAR_DELAY_MS = 3000
const TOOLBAR_HIDE_DELAY_MS = 300
let hoverTimer: ReturnType<typeof setTimeout> | null = null
let selectionTimer: ReturnType<typeof setTimeout> | null = null
let leaveTimer: ReturnType<typeof setTimeout> | null = null

// ========== 撤销重做系统 ==========
const history = ref<Block[][]>([])
const historyIndex = ref(-1)
const maxHistorySize = 50
let isUndoing = false

const canUndo = computed(() => historyIndex.value > 0)
const canRedo = computed(() => historyIndex.value >= 0 && historyIndex.value < history.value.length - 1)

// 保存历史状态
function saveHistory() {
  if (isUndoing) return
  
  // 如果当前不是最新状态，删除当前之后的历史
  if (historyIndex.value < history.value.length - 1) {
    history.value = history.value.slice(0, historyIndex.value + 1)
  }
  
  // 深拷贝当前内容
  const snapshot = JSON.parse(JSON.stringify(props.modelValue))
  history.value.push(snapshot)
  
  // 限制历史记录大小
  if (history.value.length > maxHistorySize) {
    history.value.shift()
  } else {
    historyIndex.value++
  }
}

// 撤销
function undo() {
  if (historyIndex.value > 0) {
    isUndoing = true
    historyIndex.value--
    const snapshot = history.value[historyIndex.value]
    emit('update:modelValue', JSON.parse(JSON.stringify(snapshot)))
    nextTick(() => {
      initBlockContents()
      isUndoing = false
    })
  }
}

// 重做
function redo() {
  if (historyIndex.value < history.value.length - 1) {
    isUndoing = true
    historyIndex.value++
    const snapshot = history.value[historyIndex.value]
    emit('update:modelValue', JSON.parse(JSON.stringify(snapshot)))
    nextTick(() => {
      initBlockContents()
      isUndoing = false
    })
  }
}

// 防抖保存历史
let historyTimer: ReturnType<typeof setTimeout> | null = null
function debouncedSaveHistory() {
  if (historyTimer) clearTimeout(historyTimer)
  historyTimer = setTimeout(() => {
    saveHistory()
  }, 500)
}

// 初始化历史
onMounted(() => {
  if (props.modelValue.length > 0) {
    saveHistory()
  }
})

function toggleFocusMode() {
  isFocusMode.value = !isFocusMode.value
  emit('toggleFocusMode')
}

// 初始化块内容
function onBlockContextMenu(index: number, event: MouseEvent) {
  contextMenu.value = {
    visible: true,
    x: event.clientX,
    y: event.clientY,
    blockIndex: index
  }
}

function onEmptyAreaContextMenu(event: MouseEvent) {
  contextMenu.value = {
    visible: true,
    x: event.clientX,
    y: event.clientY,
    blockIndex: -1
  }
}

function closeContextMenu() {
  contextMenu.value = { ...contextMenu.value, visible: false }
}

function handleContextAction(action: string) {
  const idx = contextMenu.value.blockIndex
  if (idx < 0 && action !== 'undo' && action !== 'redo') {
    closeContextMenu()
    return
  }
  switch (action) {
    case 'undo':
      undo()
      break
    case 'redo':
      redo()
      break
    case 'heading':
    case 'subheading':
    case 'quote':
    case 'list':
    case 'code':
    case 'divider':
    case 'paragraph':
      handleCommand(action, idx)
      break
    case 'polish':
      emitPolish(idx)
      break
    case 'formatBold':
      applyFormat(idx, 'bold')
      break
    case 'formatItalic':
      applyFormat(idx, 'italic')
      break
    case 'formatUnderline':
      applyFormat(idx, 'underline')
      break
    case 'insertAbove':
      addBlock(idx - 1)
      nextTick(() => {
        const el = blockRefs.value.get(idx)
        if (el) el.focus()
      })
      break
    case 'insertBelow':
      addBlock(idx >= 0 ? idx : -1)
      break
    case 'delete':
      if (props.modelValue.length > 1) handleCommand('delete', idx)
      break
    default:
      break
  }
  closeContextMenu()
}

onMounted(() => {
  initBlockContents()
  document.addEventListener('selectionchange', onSelectionChange)
  document.addEventListener('click', closeContextMenu)
})

onUnmounted(() => {
  document.removeEventListener('selectionchange', onSelectionChange)
  document.removeEventListener('click', closeContextMenu)
  if (hoverTimer) clearTimeout(hoverTimer)
  if (selectionTimer) clearTimeout(selectionTimer)
  if (leaveTimer) clearTimeout(leaveTimer)
})

function onBlockMouseEnter(index: number) {
  if (leaveTimer) {
    clearTimeout(leaveTimer)
    leaveTimer = null
  }
  if (selectionTimer) {
    clearTimeout(selectionTimer)
    selectionTimer = null
  }
  if (hoverTimer) clearTimeout(hoverTimer)
  hoverTimer = setTimeout(() => {
    hoverTimer = null
    toolbarVisibleIndex.value = index
  }, TOOLBAR_DELAY_MS)
}

function onBlockMouseLeave() {
  if (hoverTimer) {
    clearTimeout(hoverTimer)
    hoverTimer = null
  }
  if (leaveTimer) clearTimeout(leaveTimer)
  leaveTimer = setTimeout(() => {
    leaveTimer = null
    toolbarVisibleIndex.value = -1
  }, TOOLBAR_HIDE_DELAY_MS)
}

function onSelectionChange() {
  const sel = window.getSelection()
  if (!sel || sel.rangeCount === 0) {
    if (selectionTimer) {
      clearTimeout(selectionTimer)
      selectionTimer = null
    }
    toolbarVisibleIndex.value = -1
    return
  }
  const anchor = sel.anchorNode
  if (!anchor || !sel.toString().trim()) {
    if (selectionTimer) {
      clearTimeout(selectionTimer)
      selectionTimer = null
    }
    toolbarVisibleIndex.value = -1
    return
  }
  let blockIndex = -1
  for (const [idx, el] of blockRefs.value) {
    if (el && el.contains(anchor)) {
      blockIndex = idx
      break
    }
  }
  if (blockIndex < 0) {
    if (selectionTimer) clearTimeout(selectionTimer)
    selectionTimer = null
    toolbarVisibleIndex.value = -1
    return
  }
  if (selectionTimer) clearTimeout(selectionTimer)
  selectionTimer = setTimeout(() => {
    selectionTimer = null
    toolbarVisibleIndex.value = blockIndex
  }, TOOLBAR_DELAY_MS)
}

// 监听数据变化，只在块数量变化时更新
watch(() => props.modelValue.length, () => {
  nextTick(() => {
    initBlockContents()
  })
})

function setBlockRef(el: any, index: number) {
  if (el) {
    blockRefs.value.set(index, el as HTMLElement)
  }
}

function initBlockContents() {
  props.modelValue.forEach((block, index) => {
    const el = blockRefs.value.get(index)
    if (!el) return
    const raw = block.content || ''
    const hasHtml = /<(b|i|u|strong|em)\b/i.test(raw)
    if (!hasHtml) {
      if (el.textContent !== raw) el.textContent = raw
    } else {
      if (el.innerHTML !== raw) el.innerHTML = raw
    }
  })
}

function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).substr(2)
}

function addBlock(index: number, type = 'paragraph') {
  const newBlock: Block = {
    id: generateId(),
    type,
    content: '',
    props: {}
  }
  const newBlocks = [...props.modelValue]
  newBlocks.splice(index + 1, 0, newBlock)
  emit('update:modelValue', newBlocks)
  saveHistory()

  nextTick(() => {
    const newIndex = index + 1
    const el = blockRefs.value.get(newIndex)
    if (el) {
      el.focus()
    }
  })
}

function sanitizeBlockContent(html: string): string {
  const trimmed = html.trim()
  if (!trimmed || /^(<br\s*\/?>)+$/i.test(trimmed)) return ''
  return trimmed
}

function updateBlock(index: number) {
  const el = blockRefs.value.get(index)
  if (!el) return
  const content = sanitizeBlockContent(el.innerHTML || '')
  const newBlocks = [...props.modelValue]
  newBlocks[index] = { ...newBlocks[index], content }
  emit('update:modelValue', newBlocks)
  debouncedSaveHistory()
}

function onBlockFocus(index: number) {
  focusedIndex.value = index
  toolbarVisibleIndex.value = index
}

function handleBlur() {
  // 延迟清除焦点状态，避免下拉菜单点击时失去焦点
  setTimeout(() => {
    focusedIndex.value = -1
  }, 200)
}

function handleEnter(index: number, event: Event) {
  const target = event.target as HTMLElement
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) return
  const range = selection.getRangeAt(0)
  const hasHtml = /<(b|i|u|strong|em)\b/i.test(target.innerHTML || '')
  let beforeContent: string
  let afterContent: string
  if (hasHtml) {
    const beforeRange = document.createRange()
    beforeRange.setStart(target, 0)
    beforeRange.setEnd(range.startContainer, range.startOffset)
    const afterRange = document.createRange()
    afterRange.setStart(range.endContainer, range.endOffset)
    afterRange.setEnd(target, target.childNodes.length)
    beforeContent = sanitizeBlockContent(rangeToHtml(beforeRange))
    afterContent = sanitizeBlockContent(rangeToHtml(afterRange))
  } else {
    const text = target.textContent || ''
    const cursorPosition = getCursorPosition(target)
    beforeContent = text.slice(0, cursorPosition)
    afterContent = text.slice(cursorPosition)
  }
  const newBlocks = [...props.modelValue]
  newBlocks[index] = { ...newBlocks[index], content: beforeContent }
  const newBlock: Block = {
    id: generateId(),
    type: 'paragraph',
    content: afterContent,
    props: {}
  }
  newBlocks.splice(index + 1, 0, newBlock)
  emit('update:modelValue', newBlocks)
  saveHistory()
  nextTick(() => {
    const el = blockRefs.value.get(index + 1)
    if (el) {
      el.focus()
      setCursorToStart(el)
    }
  })
}

function rangeToHtml(range: Range): string {
  const fragment = range.cloneContents()
  const div = document.createElement('div')
  div.appendChild(fragment)
  return div.innerHTML
}

function handleBackspace(index: number, event: Event) {
  const target = event.target as HTMLElement
  const text = target.textContent || ''
  
  if (text === '' && props.modelValue.length > 1) {
    event.preventDefault()
    const newBlocks = props.modelValue.filter((_, i) => i !== index)
    emit('update:modelValue', newBlocks)
    saveHistory()

    nextTick(() => {
      const prevIndex = index - 1
      const el = blockRefs.value.get(prevIndex)
      if (el) {
        el.focus()
        // 将光标移到末尾
        setCursorToEnd(el)
      }
    })
  }
}

function moveFocus(index: number, direction: number, event: Event) {
  const newIndex = index + direction
  if (newIndex >= 0 && newIndex < props.modelValue.length) {
    event.preventDefault()
    const el = blockRefs.value.get(newIndex)
    if (el) {
      el.focus()
    }
  }
}

function handleKeydown(index: number, event: KeyboardEvent) {
  const isMod = event.ctrlKey || event.metaKey
  if (!isMod) return
  const key = event.key.toLowerCase()

  // 撤销 Ctrl+Z
  if (key === 'z' && !event.shiftKey) {
    event.preventDefault()
    undo()
    return
  }

  // 重做 Ctrl+Y 或 Ctrl+Shift+Z
  if (key === 'y' || (key === 'z' && event.shiftKey)) {
    event.preventDefault()
    redo()
    return
  }

  if (key === '1') {
    event.preventDefault()
    handleCommand('heading', index)
    return
  }
  if (key === '2') {
    event.preventDefault()
    handleCommand('subheading', index)
    return
  }
  if (key === '3') {
    event.preventDefault()
    handleCommand('quote', index)
    return
  }
  if (key === '4') {
    event.preventDefault()
    handleCommand('list', index)
    return
  }
  if (key === '5') {
    event.preventDefault()
    handleCommand('code', index)
    return
  }
  if (key === '6') {
    event.preventDefault()
    handleCommand('divider', index)
    return
  }
  if (key === '0') {
    event.preventDefault()
    handleCommand('paragraph', index)
    return
  }
  if (key === 'd' && event.shiftKey) {
    event.preventDefault()
    if (props.modelValue.length > 1) handleCommand('delete', index)
    return
  }
  if (key === 'b') {
    event.preventDefault()
    applyFormat(index, 'bold')
    return
  }
  if (key === 'i') {
    event.preventDefault()
    applyFormat(index, 'italic')
    return
  }
  if (key === 'u') {
    event.preventDefault()
    applyFormat(index, 'underline')
    return
  }
  // 专注模式快捷键
  if (key === 'f') {
    event.preventDefault()
    toggleFocusMode()
    return
  }
}

function emitPolish(index: number) {
  const block = props.modelValue[index]
  const text = block?.content ? stripHtml(block.content) : ''
  if (!text.trim()) {
    ElMessage.warning('请先输入要润色的内容')
    return
  }
  emit('polish', { index, text })
}

function stripHtml(html: string): string {
  const div = document.createElement('div')
  div.innerHTML = html
  return div.textContent || ''
}

function applyFormat(index: number, command: 'bold' | 'italic' | 'underline') {
  const el = blockRefs.value.get(index)
  if (!el) return
  el.focus()
  document.execCommand(command, false)
  updateBlock(index)
}

function isFormatActive(index: number, command: 'bold' | 'italic' | 'underline'): boolean {
  const el = blockRefs.value.get(index)
  if (!el || document.activeElement !== el) return false
  return document.queryCommandState(command)
}

function handleCommand(command: string, index: number) {
  if (command === 'delete') {
    if (props.modelValue.length <= 1) return
    const newBlocks = props.modelValue.filter((_, i) => i !== index)
    emit('update:modelValue', newBlocks)
    saveHistory()
  } else {
    const newBlocks = [...props.modelValue]
    newBlocks[index] = { ...newBlocks[index], type: command }
    emit('update:modelValue', newBlocks)
    saveHistory()

    // 保持焦点
    nextTick(() => {
      const el = blockRefs.value.get(index)
      if (el) {
        el.focus()
      }
    })
  }
}

function handleEditorClick(event: Event) {
  // 如果点击的是编辑器空白区域，添加新块
  const target = event.target as HTMLElement
  if (target.classList.contains('block-editor') && !props.modelValue.length) {
    addBlock(-1)
  }
}

function getCursorPosition(element: HTMLElement): number {
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) return 0
  const range = selection.getRangeAt(0)
  const preCaretRange = range.cloneRange()
  preCaretRange.selectNodeContents(element)
  preCaretRange.setEnd(range.endContainer, range.endOffset)
  return preCaretRange.toString().length
}

function setCursorToStart(element: HTMLElement) {
  const range = document.createRange()
  const selection = window.getSelection()
  range.selectNodeContents(element)
  range.collapse(true)
  selection?.removeAllRanges()
  selection?.addRange(range)
}

function setCursorToEnd(element: HTMLElement) {
  const range = document.createRange()
  const selection = window.getSelection()
  range.selectNodeContents(element)
  range.collapse(false)
  selection?.removeAllRanges()
  selection?.addRange(range)
}
</script>

<style scoped lang="scss">
.block-editor {
  min-height: 400px;
  padding: 20px 0;
  transition: all 0.3s ease;
  
  &.focus-mode {
    .block-wrapper:not(.is-focused) {
      opacity: 0.3;
      filter: blur(1px);
    }
    
    .block-wrapper.is-focused {
      transform: scale(1.01);
      transition: all 0.3s ease;
    }
  }
}

.block-wrapper {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 0;
  border-radius: 8px;
  transition: all 0.2s ease;
  position: relative;
  
  &:hover {
    background: rgba(93, 58, 26, 0.03);
    
    .block-handle,
    .block-actions {
      opacity: 1;
    }
  }
  
  &.is-focused {
    .block-content {
      background: rgba(93, 58, 26, 0.04);
    }
  }
}

.block-handle {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  opacity: 0;
  color: var(--coffee-text-light);
  border-radius: 4px;
  transition: all 0.2s;
  flex-shrink: 0;
  margin-top: 4px;
  
  &:hover {
    background: rgba(93, 58, 26, 0.1);
    color: var(--coffee-primary);
  }
}

.block-content {
  flex: 1;
  min-height: 36px;
  padding: 6px 12px;
  line-height: 1.8;
  outline: none;
  border-radius: 6px;
  transition: all 0.2s;
  color: var(--coffee-text);
  font-size: 16px;
  white-space: pre-wrap;
  word-break: break-word;
  
  &[data-type="heading"] {
    font-size: 24px;
    font-weight: 700;
    color: var(--coffee-text);
    margin: 8px 0;
    
    &:empty::before {
      content: '标题';
      color: var(--coffee-text-light);
    }
  }
  
  &[data-type="subheading"] {
    font-size: 18px;
    font-weight: 600;
    color: var(--coffee-text);
    margin: 6px 0;
    
    &:empty::before {
      content: '小标题';
      color: var(--coffee-text-light);
    }
  }
  
  &[data-type="quote"] {
    border-left: 3px solid var(--coffee-primary-light);
    padding-left: 20px;
    color: var(--coffee-text-secondary);
    font-style: italic;
    background: rgba(93, 58, 26, 0.04);
    
    &:empty::before {
      content: '引用内容';
      color: var(--coffee-text-light);
    }
  }
  
  &[data-type="list"] {
    padding-left: 32px;
    position: relative;
    
    &::before {
      content: "•";
      position: absolute;
      left: 12px;
      color: var(--coffee-primary);
      font-weight: bold;
    }
    
    &:empty::before {
      content: "• 列表项";
      color: var(--coffee-text-light);
    }
  }
  
  &[data-type="code"] {
    font-family: 'Fira Code', 'Monaco', 'Consolas', monospace;
    font-size: 14px;
    background: #f5f5f5;
    padding: 16px;
    border-radius: 8px;
    white-space: pre-wrap;
    color: #333;
    
    &:empty::before {
      content: '// 代码块';
      color: var(--coffee-text-light);
      font-style: italic;
    }
  }
  
  &[data-type="divider"] {
    height: 1px;
    background: linear-gradient(to right, transparent, var(--coffee-border), transparent);
    padding: 0;
    min-height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    pointer-events: none;
    
    &::before {
      content: '***';
      color: var(--coffee-text-light);
      font-size: 12px;
      letter-spacing: 4px;
    }
  }
  
  &[data-type="paragraph"]:empty::before {
    content: '输入正文...';
    color: var(--coffee-text-light);
  }
  
  &:focus {
    background: rgba(93, 58, 26, 0.04);
  }
}

/* 快捷操作栏：绝对定位浮动在块上方，过长时换行避免被右侧面板遮挡 */
.quick-toolbar {
  position: absolute;
  left: 32px;
  bottom: 100%;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  max-width: min(520px, calc(100vw - 440px));
  padding: 6px 8px;
  background: var(--coffee-bg-card);
  border: 1px solid var(--coffee-border);
  border-radius: 8px;
  box-shadow: 0 4px 12px var(--coffee-shadow);
  z-index: 9999;
}

.toolbar-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--coffee-text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
  &:hover {
    background: rgba(93, 58, 26, 0.08);
    color: var(--coffee-primary);
  }
  &.active {
    background: rgba(139, 90, 43, 0.15);
    color: var(--coffee-primary);
    font-weight: 500;
  }
  &.delete:hover:not(:disabled) {
    background: rgba(245, 108, 108, 0.12);
    color: #f56c6c;
  }
  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
  .el-icon { font-size: 16px; }
  &.ai-btn {
    color: var(--coffee-primary);
    &:hover { color: var(--coffee-primary); }
  }
  &.format-btn {
    min-width: 28px;
    padding: 6px 8px;
    font-weight: 600;
    .fmt-bold { font-weight: 700; }
    .fmt-italic { font-style: italic; font-weight: 600; }
    .fmt-underline { text-decoration: underline; font-weight: 600; }
  }
}

.toolbar-divider {
  width: 1px;
  height: 18px;
  background: var(--coffee-border);
  margin: 0 4px;
}

.toolbar-enter-active,
.toolbar-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.toolbar-enter-from,
.toolbar-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.block-actions {
  opacity: 0;
  display: flex;
  align-items: center;
  flex-shrink: 0;
  margin-top: 4px;
}

.action-icon {
  padding: 6px;
  cursor: pointer;
  color: var(--coffee-text-light);
  border-radius: 4px;
  transition: all 0.2s;
  
  &:hover {
    color: var(--coffee-primary);
    background: rgba(93, 58, 26, 0.08);
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 80px 20px;
  color: var(--coffee-text-light);
  cursor: pointer;
  border-radius: 16px;
  border: 2px dashed var(--coffee-border);
  transition: all 0.3s;
  
  &:hover {
    border-color: var(--coffee-primary-light);
    background: rgba(93, 58, 26, 0.02);
    color: var(--coffee-primary);
  }
  
  .empty-icon {
    width: 64px;
    height: 64px;
    background: linear-gradient(135deg, var(--coffee-bg-warm) 0%, var(--coffee-divider) 100%);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    
    .el-icon {
      font-size: 28px;
      color: var(--coffee-primary-light);
    }
  }
  
  span {
    font-size: 15px;
  }
  .shortcut-hint {
    font-size: 12px;
    opacity: 0.7;
    white-space: nowrap;
    display: block;
  }
}

:deep(.delete-item) {
  color: #f56c6c;
}

:deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  white-space: nowrap;
  gap: 16px;
}

:deep(.shortcut) {
  margin-left: auto;
  padding-left: 12px;
  font-size: 12px;
  color: var(--coffee-text-light);
  flex-shrink: 0;
  white-space: nowrap;
}

/* 右键快捷菜单 */
.context-menu {
  position: fixed;
  z-index: 10000;
  min-width: 200px;
  max-width: 280px;
  padding: 6px 0;
  background: var(--coffee-bg-card);
  border: 1px solid var(--coffee-border);
  border-radius: 10px;
  box-shadow: 0 8px 24px var(--coffee-shadow);
}

.context-menu-section {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.context-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 14px;
  border: none;
  background: transparent;
  color: var(--coffee-text-secondary);
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  border-radius: 6px;
  margin: 0 4px;
  width: calc(100% - 8px);
  box-sizing: border-box;
}
.context-item .el-icon {
  font-size: 16px;
  flex-shrink: 0;
}
.context-item .shortcut {
  margin-left: auto;
  font-size: 11px;
  color: var(--coffee-text-light);
}
.context-item:hover:not(:disabled) {
  background: rgba(93, 58, 26, 0.08);
  color: var(--coffee-primary);
}
.context-item.active {
  background: rgba(139, 90, 43, 0.12);
  color: var(--coffee-primary);
  font-weight: 500;
}
.context-item.ai-item {
  color: var(--coffee-primary);
}
.context-item.ai-item:hover:not(:disabled) {
  color: var(--coffee-primary);
}
.context-item.danger:hover:not(:disabled) {
  background: rgba(245, 108, 108, 0.12);
  color: #f56c6c;
}
.context-item:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.context-item .fmt-bold { font-weight: 700; }
.context-item .fmt-italic { font-style: italic; font-weight: 600; }
.context-item .fmt-underline { text-decoration: underline; font-weight: 600; }

.context-menu-divider {
  height: 1px;
  background: var(--coffee-border);
  margin: 4px 0;
}

.context-menu-enter-active,
.context-menu-leave-active {
  transition: opacity 0.12s ease, transform 0.12s ease;
}
.context-menu-enter-from,
.context-menu-leave-to {
  opacity: 0;
  transform: scale(0.96);
}
</style>
