<template>
  <div class="block-editor" :class="{ 'focus-mode': isFocusMode, 'multi-select': isMultiSelectMode }" @click="handleEditorClick">
    <!-- 多选块工具栏 -->
    <Teleport to="body">
      <Transition name="multi-select-toolbar">
        <div v-if="isMultiSelectMode && selectedBlocks.size > 0" class="multi-select-toolbar">
          <span class="selected-count">已选 {{ selectedBlocks.size }} 个块</span>
          <button type="button" class="toolbar-btn" @click="copySelectedBlocks" title="复制 (Ctrl+C)">
            <el-icon><DocumentCopy /></el-icon>
            <span>复制</span>
          </button>
          <button type="button" class="toolbar-btn" @click="cutSelectedBlocks" title="剪切 (Ctrl+X)">
            <el-icon><Scissor /></el-icon>
            <span>剪切</span>
          </button>
          <button
            type="button"
            class="toolbar-btn ai-btn"
            @click="emitPolishSelected"
            title="AI 润色（选中多个块）"
          >
            <el-icon><Brush /></el-icon>
            <span>AI 润色</span>
          </button>
          <button
            type="button"
            class="toolbar-btn ai-btn"
            @click="emitReviseSelected"
            title="AI 修改（选中多个块）"
          >
            <el-icon><EditPen /></el-icon>
            <span>AI 修改</span>
          </button>
          <button
            type="button"
            class="toolbar-btn ai-btn"
            @click="emitExpandSelected"
            title="AI 扩展（选中多个块）"
          >
            <el-icon><MagicStick /></el-icon>
            <span>AI 扩展</span>
          </button>
          <button type="button" class="toolbar-btn delete" @click="deleteSelectedBlocks" title="删除 (Delete)">
            <el-icon><Delete /></el-icon>
            <span>删除</span>
          </button>
          <button type="button" class="toolbar-btn" @click="clearBlockSelection" title="取消选择 (Esc)">
            <el-icon><Close /></el-icon>
            <span>取消</span>
          </button>
        </div>
      </Transition>
    </Teleport>

    <!-- 斜杠命令菜单 -->
    <Teleport to="body">
      <Transition name="slash-menu">
        <div
          v-if="slashMenuVisible"
          class="slash-menu"
          :style="slashMenuStyle"
        >
          <div class="slash-menu-header">基本块</div>
          <div
            v-for="(cmd, idx) in filteredSlashCommands"
            :key="cmd.id"
            class="slash-menu-item"
            :class="{ active: selectedSlashIndex === idx }"
            @mousedown.prevent
            @click="applySlashCommand(idx, currentSlashBlockIndex)"
          >
            <div class="slash-icon">
              <el-icon v-if="cmd.icon === 'Top'"><Top /></el-icon>
              <el-icon v-else-if="cmd.icon === 'Rank'"><Rank /></el-icon>
              <el-icon v-else-if="cmd.icon === 'ChatDotRound'"><ChatDotRound /></el-icon>
              <el-icon v-else-if="cmd.icon === 'List'"><List /></el-icon>
              <el-icon v-else-if="cmd.icon === 'Operation'"><Operation /></el-icon>
              <el-icon v-else-if="cmd.icon === 'Minus'"><Minus /></el-icon>
              <el-icon v-else-if="cmd.icon === 'Document'"><Document /></el-icon>
            </div>
            <div class="slash-info">
              <span class="slash-label">{{ cmd.label }}</span>
              <span class="slash-shortcut">{{ cmd.shortcut }}</span>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <div
      v-for="(block, index) in modelValue"
      :key="block.id"
      class="block-wrapper"
      :class="{
        'is-focused': focusedIndex === index,
        'is-toolbar-visible': toolbarVisibleIndex === index,
        'is-selected': selectedBlocks.has(index),
        [`type-${block.type}`]: true
      }"
      @mouseenter="onBlockMouseEnter(index)"
      @mouseleave="onBlockMouseLeave"
      @mousedown="handleBlockMouseDown(index, $event)"
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
        @keydown.ctrl.a.prevent="handleSelectAll(index, $event)"
        @keydown.meta.a.prevent="handleSelectAll(index, $event)"
        @mouseup="handleMouseUp(index, $event)"
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
          ref="contextMenuRef"
          class="context-menu"
          :style="contextMenuStyle"
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
      <span class="shortcut-hint">Ctrl+1~6 切换块 · Ctrl+B/I/U 格式 · Ctrl+Z/Y 撤销 · Ctrl+Shift+F 整理排版 · Ctrl+↑↓ 导航 · / 斜杠命令 · Ctrl+点击多选 · Ctrl+C/X/V 复制剪切粘贴</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import type { Block } from '@/stores/project'
import { ElMessage } from 'element-plus'
import { Plus, MoreFilled, Top, ChatDotRound, List, Document, Delete, EditPen, Brush, Rank, Operation, Minus, RefreshLeft, RefreshRight, DocumentCopy, Scissor, Close, MagicStick } from '@element-plus/icons-vue'

const props = defineProps<{
  modelValue: Block[]
  focusMode?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: Block[]): void
  (e: 'polish', payload: { index: number; text: string }): void
  (e: 'polish-selected', payload: { indices: number[]; text: string }): void
  (e: 'revise-selected', payload: { indices: number[]; text: string }): void
  (e: 'expand-selected', payload: { indices: number[]; text: string }): void
  (e: 'toggleFocusMode'): void
  (e: 'replace', payload: { index: number; oldText: string; newText: string }): void
}>()

const focusedIndex = ref(-1)
const blockRefs = ref<Map<number, HTMLElement>>(new Map())
/** 当前显示快捷栏的块索引，-1 为不显示。悬停 3s 或选中 3s 后赋值 */
const toolbarVisibleIndex = ref(-1)
/** 右键快捷菜单状态 */
const contextMenu = ref({ visible: false, x: 0, y: 0, blockIndex: -1 })
const contextMenuRef = ref<HTMLElement | null>(null)
const contextBlock = computed(() =>
  contextMenu.value.visible && contextMenu.value.blockIndex >= 0 && props.modelValue[contextMenu.value.blockIndex]
    ? props.modelValue[contextMenu.value.blockIndex]
    : null
)

// 动态计算右键菜单位置，确保不超出屏幕
const contextMenuStyle = computed(() => {
  const menuWidth = 280 // 菜单最大宽度
  const menuHeight = 400 // 预估菜单高度（滚动区域）
  const padding = 10 // 屏幕边缘留白

  let x = contextMenu.value.x
  let y = contextMenu.value.y

  // 获取屏幕尺寸
  const screenWidth = window.innerWidth
  const screenHeight = window.innerHeight

  // 水平方向：如果超出右边界，则向左显示
  if (x + menuWidth + padding > screenWidth) {
    x = screenWidth - menuWidth - padding
  }

  // 垂直方向：如果超出下边界，则向上显示
  if (y + menuHeight + padding > screenHeight) {
    y = screenHeight - menuHeight - padding
    // 如果向上显示也会超出上边界，则显示在屏幕顶部附近
    if (y < padding) {
      y = padding
    }
  }

  // 确保不会显示在屏幕左上角之外
  x = Math.max(padding, x)
  y = Math.max(padding, y)

  return {
    left: x + 'px',
    top: y + 'px'
  }
})

// 动态计算斜杠菜单位置
const slashMenuStyle = computed(() => {
  const menuWidth = 320 // 菜单最大宽度
  const menuHeight = 350 // 预估菜单高度
  const padding = 10 // 屏幕边缘留白

  let x = slashMenuPosition.value.x
  let y = slashMenuPosition.value.y

  // 获取屏幕尺寸
  const screenWidth = window.innerWidth
  const screenHeight = window.innerHeight

  // 水平方向：如果超出右边界，则向左显示
  if (x + menuWidth + padding > screenWidth) {
    x = Math.max(padding, screenWidth - menuWidth - padding)
  }

  // 垂直方向：优先向下显示，如果超出下边界则向上显示
  if (y + menuHeight + padding > screenHeight) {
    // 向上显示（在光标上方）
    y = Math.max(padding, y - menuHeight - 40) // 40是块的高度
  }

  // 确保不会显示在屏幕之外
  x = Math.max(padding, x)
  y = Math.max(padding, y)

  return {
    left: x + 'px',
    top: y + 'px'
  }
})
const isFocusMode = ref(props.focusMode || false)
const TOOLBAR_DELAY_MS = 3000
const TOOLBAR_HIDE_DELAY_MS = 300
let hoverTimer: ReturnType<typeof setTimeout> | null = null
let selectionTimer: ReturnType<typeof setTimeout> | null = null
let leaveTimer: ReturnType<typeof setTimeout> | null = null

// ========== 斜杠命令菜单 ==========
const slashMenuVisible = ref(false)
const slashMenuPosition = ref({ x: 0, y: 0 })
const selectedSlashIndex = ref(0)
const slashQuery = ref('')
const currentSlashBlockIndex = ref(-1)

const slashCommands = [
  { id: 'heading', label: '大标题', icon: 'Top', shortcut: 'Ctrl+1', type: 'heading' },
  { id: 'subheading', label: '小标题', icon: 'Rank', shortcut: 'Ctrl+2', type: 'subheading' },
  { id: 'quote', label: '引用', icon: 'ChatDotRound', shortcut: 'Ctrl+3', type: 'quote' },
  { id: 'list', label: '列表', icon: 'List', shortcut: 'Ctrl+4', type: 'list' },
  { id: 'code', label: '代码块', icon: 'Operation', shortcut: 'Ctrl+5', type: 'code' },
  { id: 'divider', label: '分割线', icon: 'Minus', shortcut: 'Ctrl+6', type: 'divider' },
  { id: 'paragraph', label: '正文', icon: 'Document', shortcut: 'Ctrl+0', type: 'paragraph' },
]

const filteredSlashCommands = computed(() => {
  if (!slashQuery.value) return slashCommands
  const query = slashQuery.value.toLowerCase()
  return slashCommands.filter(cmd =>
    cmd.label.toLowerCase().includes(query) ||
    cmd.id.toLowerCase().includes(query)
  )
})

function showSlashMenu(index: number, rect: DOMRect) {
  currentSlashBlockIndex.value = index
  slashMenuPosition.value = {
    x: rect.left,
    y: rect.bottom + 8
  }
  slashMenuVisible.value = true
  selectedSlashIndex.value = 0
  slashQuery.value = ''
}

function hideSlashMenu() {
  slashMenuVisible.value = false
  slashQuery.value = ''
  currentSlashBlockIndex.value = -1
}

function applySlashCommand(commandIndex: number, blockIndex?: number) {
  const commands = filteredSlashCommands.value
  if (commandIndex < 0 || commandIndex >= commands.length) return

  const command = commands[commandIndex]
  const targetIndex = blockIndex !== undefined ? blockIndex : currentSlashBlockIndex.value
  if (targetIndex < 0) return

  // 清除斜杠命令文本
  const el = blockRefs.value.get(targetIndex)
  if (el) {
    const text = el.textContent || ''
    const newText = text.replace(/\/[^\s]*$/, '').trim()
    el.textContent = newText
    updateBlock(targetIndex)
  }

  handleCommand(command.type, targetIndex)
  hideSlashMenu()
}

// ========== 多选块功能 ==========
const selectedBlocks = ref<Set<number>>(new Set())
const isMultiSelectMode = ref(false)

function toggleBlockSelection(index: number, event?: MouseEvent) {
  if (event) {
    if (event.ctrlKey || event.metaKey) {
      // Ctrl/Cmd + 点击：切换选择
      if (selectedBlocks.value.has(index)) {
        selectedBlocks.value.delete(index)
      } else {
        selectedBlocks.value.add(index)
      }
      isMultiSelectMode.value = true
    } else if (event.shiftKey && selectedBlocks.value.size > 0) {
      // Shift + 点击：范围选择
      const lastSelected = Math.max(...selectedBlocks.value)
      const start = Math.min(lastSelected, index)
      const end = Math.max(lastSelected, index)
      for (let i = start; i <= end; i++) {
        selectedBlocks.value.add(i)
      }
      isMultiSelectMode.value = true
    } else {
      // 普通点击：清除其他选择，只选当前
      selectedBlocks.value.clear()
      selectedBlocks.value.add(index)
      isMultiSelectMode.value = false
    }
  } else {
    selectedBlocks.value.clear()
    selectedBlocks.value.add(index)
    isMultiSelectMode.value = false
  }
}

function clearBlockSelection() {
  selectedBlocks.value.clear()
  isMultiSelectMode.value = false
}

function selectAllBlocks() {
  selectedBlocks.value.clear()
  for (let i = 0; i < props.modelValue.length; i++) {
    selectedBlocks.value.add(i)
  }
  isMultiSelectMode.value = true
}

function handleSelectAll(index: number, event: Event) {
  const el = blockRefs.value.get(index)
  if (!el) return

  const selection = window.getSelection()
  if (!selection) return

  const range = document.createRange()
  range.selectNodeContents(el)
  selection.removeAllRanges()
  selection.addRange(range)

  // 如果已经在全选状态，则跨块选择
  const text = selection.toString()
  const elText = el.textContent || ''
  if (text === elText && props.modelValue.length > 1) {
    selectAllBlocks()
  }
}

function handleMouseUp(index: number, event: MouseEvent) {
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) return

  // 检查是否是跨块选择
  const range = selection.getRangeAt(0)
  let startBlock = -1
  let endBlock = -1

  for (const [idx, el] of blockRefs.value) {
    if (el && range.intersectsNode(el)) {
      if (startBlock === -1) startBlock = idx
      endBlock = idx
    }
  }

  if (startBlock !== -1 && endBlock !== -1 && startBlock !== endBlock) {
    // 跨块选择
    selectedBlocks.value.clear()
    for (let i = startBlock; i <= endBlock; i++) {
      selectedBlocks.value.add(i)
    }
    isMultiSelectMode.value = true
  } else if (event.ctrlKey || event.metaKey || event.shiftKey) {
    toggleBlockSelection(index, event)
  }
}

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
      el.focus({ preventScroll: true })
      scrollElementIntoView(el)
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

  // 检查是否是斜杠命令菜单激活状态
  if (slashMenuVisible.value) {
    event.preventDefault()
    applySlashCommand(selectedSlashIndex.value, index)
    return
  }

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
      // 使用 preventScroll 选项阻止自动滚动，页面保持不动
      el.focus({ preventScroll: true })
      setCursorToStart(el)
    }
  })
}

// 滚动元素到可视区域，但避免跳转到页面底部
function scrollElementIntoView(element: HTMLElement) {
  const rect = element.getBoundingClientRect()
  const viewportHeight = window.innerHeight
  const headerOffset = 100 // 预留头部空间

  // 只有当元素在可视区域外时才滚动
  if (rect.bottom > viewportHeight - headerOffset) {
    element.scrollIntoView({ behavior: 'smooth', block: 'center' })
  } else if (rect.top < headerOffset) {
    element.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
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
  const cursorPosition = getCursorPosition(target)

  // 如果在斜杠命令菜单中，隐藏菜单
  if (slashMenuVisible.value) {
    hideSlashMenu()
  }

  // 在块的最开始位置按 Backspace，且不是第一个块
  if (index > 0 && cursorPosition === 0) {
    event.preventDefault()

    const currentBlock = props.modelValue[index]
    const prevBlock = props.modelValue[index - 1]

    // 将当前块内容合并到上一个块
    const newContent = prevBlock.content + currentBlock.content
    const newBlocks = [...props.modelValue]
    newBlocks[index - 1] = { ...prevBlock, content: newContent }
    newBlocks.splice(index, 1)

    emit('update:modelValue', newBlocks)
    saveHistory()

    nextTick(() => {
      const el = blockRefs.value.get(index - 1)
      if (el) {
        el.focus({ preventScroll: true })
        // 将光标移到合并前的位置（即上一个块原来的末尾）
        setCursorToPosition(el, prevBlock.content.length)
      }
    })
    return
  }

  // 空块删除（原有逻辑）
  if (text === '' && props.modelValue.length > 1) {
    event.preventDefault()
    const newBlocks = props.modelValue.filter((_, i) => i !== index)
    emit('update:modelValue', newBlocks)
    saveHistory()

    nextTick(() => {
      const prevIndex = index - 1
      const el = blockRefs.value.get(prevIndex)
      if (el) {
        el.focus({ preventScroll: true })
        scrollElementIntoView(el)
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
      el.focus({ preventScroll: true })
      scrollElementIntoView(el)
    }
  }
}

function handleKeydown(index: number, event: KeyboardEvent) {
  // 斜杠命令菜单导航
  if (slashMenuVisible.value) {
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault()
        selectedSlashIndex.value = (selectedSlashIndex.value + 1) % filteredSlashCommands.value.length
        return
      case 'ArrowUp':
        event.preventDefault()
        selectedSlashIndex.value = (selectedSlashIndex.value - 1 + filteredSlashCommands.value.length) % filteredSlashCommands.value.length
        return
      case 'Enter':
        event.preventDefault()
        applySlashCommand(selectedSlashIndex.value, index)
        return
      case 'Escape':
        event.preventDefault()
        hideSlashMenu()
        return
      case 'Backspace':
        // 更新斜杠查询
        if (slashQuery.value.length > 0) {
          slashQuery.value = slashQuery.value.slice(0, -1)
          selectedSlashIndex.value = 0
        } else {
          hideSlashMenu()
        }
        return
      default:
        // 累积查询字符
        if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
          slashQuery.value += event.key
          selectedSlashIndex.value = 0
          return
        }
        break
    }
  }

  // 检测斜杠命令触发
  if (event.key === '/' && !event.ctrlKey && !event.metaKey) {
    const el = blockRefs.value.get(index)
    if (el) {
      const text = el.textContent || ''
      const selection = window.getSelection()
      if (selection && selection.rangeCount > 0) {
        const range = selection.getRangeAt(0)
        const cursorPos = getCursorPosition(el)
        // 只有在开头或空格后才触发斜杠命令
        if (cursorPos === 0 || text[cursorPos - 1] === ' ' || text[cursorPos - 1] === '\n') {
          const rect = range.getBoundingClientRect()
          showSlashMenu(index, rect)
        }
      }
    }
    return
  }

  // Esc 清除多选
  if (event.key === 'Escape') {
    clearBlockSelection()
    return
  }

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

  // 全选所有块
  if (key === 'a') {
    event.preventDefault()
    selectAllBlocks()
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

  // 多选块操作：复制、粘贴、删除
  if (selectedBlocks.value.size > 0) {
    // 复制选中的块
    if (key === 'c') {
      event.preventDefault()
      copySelectedBlocks()
      return
    }
    // 剪切选中的块
    if (key === 'x') {
      event.preventDefault()
      cutSelectedBlocks()
      return
    }
    // 删除选中的块
    if (key === 'delete' || key === 'backspace') {
      event.preventDefault()
      deleteSelectedBlocks()
      return
    }
  }

  // 粘贴块
  if (key === 'v') {
    const pasted = pasteBlocks(index)
    if (pasted) {
      event.preventDefault()
      return
    }
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

// ========== 多选块操作：复制、剪切、删除 ==========
const copiedBlocks = ref<Block[]>([])

function copySelectedBlocks() {
  if (selectedBlocks.value.size === 0) return

  const sortedIndices = Array.from(selectedBlocks.value).sort((a, b) => a - b)
  copiedBlocks.value = sortedIndices.map(i => ({ ...props.modelValue[i], id: generateId() }))

  // 也复制到系统剪贴板
  const textContent = sortedIndices.map(i => stripHtml(props.modelValue[i].content)).join('\n\n')
  navigator.clipboard.writeText(textContent).catch(() => {
    // 忽略剪贴板权限错误
  })

  ElMessage.success(`已复制 ${copiedBlocks.value.length} 个块`)
  clearBlockSelection()
}

function cutSelectedBlocks() {
  if (selectedBlocks.value.size === 0) return

  copySelectedBlocks()
  deleteSelectedBlocks()
}

function deleteSelectedBlocks() {
  if (selectedBlocks.value.size === 0) return

  const selectedSet = new Set(selectedBlocks.value)
  let newBlocks = props.modelValue.filter((_, i) => !selectedSet.has(i))

  // 确保至少保留一个块
  if (newBlocks.length === 0) {
    newBlocks = [{
      id: generateId(),
      type: 'paragraph',
      content: '',
      props: {}
    }]
  }

  emit('update:modelValue', newBlocks)
  saveHistory()
  clearBlockSelection()
  ElMessage.success('已删除选中的块')
}

function pasteBlocks(afterIndex: number): boolean {
  if (copiedBlocks.value.length === 0) return false

  const newBlocks = [...props.modelValue]
  const blocksToInsert = copiedBlocks.value.map(b => ({ ...b, id: generateId() }))

  newBlocks.splice(afterIndex + 1, 0, ...blocksToInsert)
  emit('update:modelValue', newBlocks)
  saveHistory()

  nextTick(() => {
    const focusIndex = afterIndex + blocksToInsert.length
    const el = blockRefs.value.get(focusIndex)
    if (el) {
      el.focus({ preventScroll: true })
    }
  })

  ElMessage.success(`已粘贴 ${blocksToInsert.length} 个块`)
  return true
}

function emitPolish(index: number) {
  const block = props.modelValue[index]
  if (!block) return

  // 多选状态下：如果当前块在选中集合中，则对“全部选中块”执行润色
  if (selectedBlocks.value.size > 1 && selectedBlocks.value.has(index)) {
    emitPolishSelected()
    return
  }

  const text = block?.content ? stripHtml(block.content) : ''
  if (!text.trim()) {
    ElMessage.warning('请先输入要润色的内容')
    return
  }
  emit('polish', { index, text })
}

function emitPolishSelected() {
  emitRewriteSelected('polish')
}

function emitReviseSelected() {
  emitRewriteSelected('revise')
}

function emitExpandSelected() {
  emitRewriteSelected('expand')
}

function emitRewriteSelected(action: 'polish' | 'revise' | 'expand') {
  const indices = Array.from(selectedBlocks.value).sort((a, b) => a - b)
  if (indices.length === 0) return

  const parts = indices
    .map(i => {
      const b = props.modelValue[i]
      return b?.content ? stripHtml(b.content) : ''
    })
    .filter(t => t.trim())

  const text = parts.join('\n\n')
  if (!text.trim()) {
    const msg = action === 'polish'
      ? '请先输入要润色的内容'
      : action === 'revise'
        ? '请先输入要修改的内容'
        : '请先输入要扩展的内容'
    ElMessage.warning(msg)
    return
  }

  // 启动 AI 前清空选择，避免替换后下标变化导致高亮错位
  clearBlockSelection()

  if (action === 'polish') {
    emit('polish-selected', { indices, text })
  } else if (action === 'revise') {
    emit('revise-selected', { indices, text })
  } else {
    emit('expand-selected', { indices, text })
  }
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
        el.focus({ preventScroll: true })
        scrollElementIntoView(el)
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
  // 点击编辑器空白区域时清除选择
  if (target.classList.contains('block-editor')) {
    clearBlockSelection()
  }
}

function handleBlockMouseDown(index: number, event: MouseEvent) {
  // 如果正在多选模式或按住修饰键
  if (isMultiSelectMode.value || event.ctrlKey || event.metaKey || event.shiftKey) {
    event.preventDefault()
    toggleBlockSelection(index, event)
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

function setCursorToPosition(element: HTMLElement, position: number) {
  const selection = window.getSelection()
  if (!selection) return

  const range = document.createRange()
  const textNodes = getTextNodes(element)
  let currentPos = 0

  for (const node of textNodes) {
    const nodeLength = node.textContent?.length || 0
    if (currentPos + nodeLength >= position) {
      const offset = position - currentPos
      range.setStart(node, offset)
      range.setEnd(node, offset)
      break
    }
    currentPos += nodeLength
  }

  if (textNodes.length === 0) {
    range.selectNodeContents(element)
    range.collapse(true)
  }

  selection.removeAllRanges()
  selection.addRange(range)
}

function getTextNodes(element: Node): Text[] {
  const textNodes: Text[] = []
  const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, null)
  let node: Node | null
  while ((node = walker.nextNode()) !== null) {
    textNodes.push(node as Text)
  }
  return textNodes
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
    background: rgba(var(--coffee-primary-rgb), 0.03);
    
    .block-handle,
    .block-actions {
      opacity: 1;
    }
  }
  
  &.is-focused {
    .block-content {
      background: var(--coffee-sidebar-shadow);
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
    background: rgba(var(--coffee-primary-rgb), 0.1);
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
    background: var(--coffee-sidebar-shadow);
    
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
    background: var(--coffee-sidebar-shadow);
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
    background: var(--coffee-shadow);
    color: var(--coffee-primary);
  }
  &.active {
    background: var(--coffee-shadow-hover);
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

/* 多选块的视觉反馈 */
.block-wrapper.is-selected {
  background: rgba(var(--coffee-primary-rgb), 0.08) !important;
  border-left: 3px solid var(--coffee-primary);
}

.block-editor.multi-select .block-wrapper {
  cursor: pointer;
}

.block-editor.multi-select .block-wrapper:hover {
  background: rgba(var(--coffee-primary-rgb), 0.04);
}

/* 斜杠命令菜单 */
.slash-menu {
  position: fixed;
  z-index: 10000;
  min-width: 240px;
  max-width: 320px;
  max-height: 400px;
  overflow-y: auto;
  background: var(--coffee-bg-card);
  border: 1px solid var(--coffee-border);
  border-radius: 10px;
  box-shadow: 0 8px 24px var(--coffee-shadow);
  padding: 8px 0;
}

.slash-menu-header {
  padding: 8px 16px;
  font-size: 12px;
  font-weight: 600;
  color: var(--coffee-text-light);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.slash-menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  cursor: pointer;
  transition: all 0.15s ease;
  margin: 0 6px;
  border-radius: 6px;
}

.slash-menu-item:hover,
.slash-menu-item.active {
  background: var(--coffee-shadow);
}

.slash-menu-item.active {
  background: rgba(var(--coffee-primary-rgb), 0.12);
}

.slash-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--coffee-bg-warm);
  border-radius: 8px;
  color: var(--coffee-primary);
  font-size: 18px;
}

.slash-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}

.slash-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--coffee-text);
}

.slash-shortcut {
  font-size: 12px;
  color: var(--coffee-text-light);
}

.slash-menu-enter-active,
.slash-menu-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.slash-menu-enter-from,
.slash-menu-leave-to {
  opacity: 0;
  transform: scale(0.96) translateY(-8px);
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
    background: var(--coffee-shadow);
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
    background: rgba(var(--coffee-primary-rgb), 0.02);
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
  max-height: 70vh;
  overflow-y: auto;
  overflow-x: hidden;
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
  background: var(--coffee-shadow);
  color: var(--coffee-primary);
}
.context-item.active {
  background: rgba(var(--coffee-primary-rgb), 0.12);
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

/* 多选块的视觉反馈 */
.block-wrapper.is-selected {
  background: rgba(var(--coffee-primary-rgb), 0.08) !important;
  border-left: 3px solid var(--coffee-primary);
}

.block-editor.multi-select .block-wrapper {
  cursor: pointer;
}

.block-editor.multi-select .block-wrapper:hover {
  background: rgba(var(--coffee-primary-rgb), 0.04);
}

/* 斜杠命令菜单 */
.slash-menu {
  position: fixed;
  z-index: 10000;
  min-width: 240px;
  max-width: 320px;
  max-height: 400px;
  overflow-y: auto;
  background: var(--coffee-bg-card);
  border: 1px solid var(--coffee-border);
  border-radius: 10px;
  box-shadow: 0 8px 24px var(--coffee-shadow);
  padding: 8px 0;
}

.slash-menu-header {
  padding: 8px 16px;
  font-size: 12px;
  font-weight: 600;
  color: var(--coffee-text-light);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.slash-menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  cursor: pointer;
  transition: all 0.15s ease;
  margin: 0 6px;
  border-radius: 6px;
}

.slash-menu-item:hover,
.slash-menu-item.active {
  background: var(--coffee-shadow);
}

.slash-menu-item.active {
  background: rgba(var(--coffee-primary-rgb), 0.12);
}

.slash-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--coffee-bg-warm);
  border-radius: 8px;
  color: var(--coffee-primary);
  font-size: 18px;
}

.slash-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}

.slash-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--coffee-text);
}

.slash-shortcut {
  font-size: 12px;
  color: var(--coffee-text-light);
}

.slash-menu-enter-active,
.slash-menu-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.slash-menu-enter-from,
.slash-menu-leave-to {
  opacity: 0;
  transform: scale(0.96) translateY(-8px);
}

/* 多选块工具栏 */
.multi-select-toolbar {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: var(--coffee-bg-card);
  border: 1px solid var(--coffee-border);
  border-radius: 12px;
  box-shadow: 0 8px 24px var(--coffee-shadow);
  z-index: 10001;
}

.selected-count {
  font-size: 13px;
  color: var(--coffee-text-secondary);
  margin-right: 8px;
  padding-right: 12px;
  border-right: 1px solid var(--coffee-border);
  white-space: nowrap;
}

.multi-select-toolbar .toolbar-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 8px 14px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--coffee-text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.multi-select-toolbar .toolbar-btn:hover {
  background: var(--coffee-shadow);
  color: var(--coffee-primary);
}

.multi-select-toolbar .toolbar-btn.delete:hover {
  background: rgba(245, 108, 108, 0.12);
  color: #f56c6c;
}

.multi-select-toolbar .toolbar-btn .el-icon {
  font-size: 16px;
}

.multi-select-toolbar-enter-active,
.multi-select-toolbar-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.multi-select-toolbar-enter-from,
.multi-select-toolbar-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(20px);
}
</style>
