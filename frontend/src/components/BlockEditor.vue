<template>
  <div class="block-editor" @click="handleEditorClick">
    <div
      v-for="(block, index) in modelValue"
      :key="block.id"
      class="block-wrapper"
      :class="{ 'is-focused': focusedIndex === index, [`type-${block.type}`]: true }"
    >
      <div class="block-handle" @click.stop="addBlock(index)">
        <el-icon><Plus /></el-icon>
      </div>
      
      <div
        :ref="el => setBlockRef(el, index)"
        class="block-content"
        :data-type="block.type"
        contenteditable="true"
        @input="updateBlock(index)"
        @focus="focusedIndex = index"
        @blur="handleBlur"
        @keydown.enter.prevent="handleEnter(index, $event)"
        @keydown.backspace="handleBackspace(index, $event)"
        @keydown.up="moveFocus(index, -1, $event)"
        @keydown.down="moveFocus(index, 1, $event)"
      />
      
      <div class="block-actions">
        <el-dropdown trigger="click" @command="(cmd) => handleCommand(cmd, index)">
          <el-icon class="action-icon" @click.stop><MoreFilled /></el-icon>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="heading">
                <el-icon><Top /></el-icon> 转为标题
              </el-dropdown-item>
              <el-dropdown-item command="quote">
                <el-icon><ChatDotRound /></el-icon> 转为引用
              </el-dropdown-item>
              <el-dropdown-item command="list">
                <el-icon><List /></el-icon> 转为列表
              </el-dropdown-item>
              <el-dropdown-item divided command="paragraph">
                <el-icon><Document /></el-icon> 转为正文
              </el-dropdown-item>
              <el-dropdown-item command="delete" class="delete-item">
                <el-icon><Delete /></el-icon> 删除
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
    
    <div v-if="!modelValue.length" class="empty-state" @click="addBlock(-1)">
      <div class="empty-icon">
        <el-icon><EditPen /></el-icon>
      </div>
      <span>点击开始写作，记录您的灵感...</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, watch } from 'vue'
import type { Block } from '@/stores/project'
import { Plus, MoreFilled, Top, ChatDotRound, List, Document, Delete, EditPen } from '@element-plus/icons-vue'

const props = defineProps<{
  modelValue: Block[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: Block[]): void
}>()

const focusedIndex = ref(-1)
const blockRefs = ref<Map<number, HTMLElement>>(new Map())

// 初始化块内容
onMounted(() => {
  initBlockContents()
})

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
    if (el && el.textContent !== block.content) {
      el.textContent = block.content || ''
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
  
  nextTick(() => {
    const newIndex = index + 1
    const el = blockRefs.value.get(newIndex)
    if (el) {
      el.focus()
    }
  })
}

function updateBlock(index: number) {
  const el = blockRefs.value.get(index)
  if (!el) return
  
  const content = el.textContent || ''
  const newBlocks = [...props.modelValue]
  newBlocks[index] = { ...newBlocks[index], content }
  emit('update:modelValue', newBlocks)
}

function handleBlur() {
  // 延迟清除焦点状态，避免下拉菜单点击时失去焦点
  setTimeout(() => {
    focusedIndex.value = -1
  }, 200)
}

function handleEnter(index: number, event: Event) {
  const target = event.target as HTMLElement
  const cursorPosition = getCursorPosition(target)
  const text = target.textContent || ''
  const before = text.slice(0, cursorPosition)
  const after = text.slice(cursorPosition)
  
  // 更新当前块
  const newBlocks = [...props.modelValue]
  newBlocks[index] = { ...newBlocks[index], content: before }
  
  // 创建新块
  const newBlock: Block = {
    id: generateId(),
    type: 'paragraph',
    content: after,
    props: {}
  }
  newBlocks.splice(index + 1, 0, newBlock)
  emit('update:modelValue', newBlocks)
  
  nextTick(() => {
    const newIndex = index + 1
    const el = blockRefs.value.get(newIndex)
    if (el) {
      el.focus()
      setCursorToStart(el)
    }
  })
}

function handleBackspace(index: number, event: Event) {
  const target = event.target as HTMLElement
  const text = target.textContent || ''
  
  if (text === '' && props.modelValue.length > 1) {
    event.preventDefault()
    const newBlocks = props.modelValue.filter((_, i) => i !== index)
    emit('update:modelValue', newBlocks)
    
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

function handleCommand(command: string, index: number) {
  if (command === 'delete') {
    const newBlocks = props.modelValue.filter((_, i) => i !== index)
    emit('update:modelValue', newBlocks)
  } else {
    const newBlocks = [...props.modelValue]
    newBlocks[index] = { ...newBlocks[index], type: command }
    emit('update:modelValue', newBlocks)
    
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
  
  &[data-type="paragraph"]:empty::before {
    content: '输入正文...';
    color: var(--coffee-text-light);
  }
  
  &:focus {
    background: rgba(93, 58, 26, 0.04);
  }
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
}

:deep(.delete-item) {
  color: #f56c6c;
}
</style>
