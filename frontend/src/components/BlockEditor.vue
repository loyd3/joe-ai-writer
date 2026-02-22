<template>
  <div class="block-editor" @click="focusLast">
    <div
      v-for="(block, index) in modelValue"
      :key="block.id"
      class="block-wrapper"
      :class="{ 'is-focused': focusedIndex === index }"
    >
      <div class="block-handle">
        <el-icon><Plus /></el-icon>
      </div>
      
      <div
        class="block-content"
        :data-type="block.type"
        contenteditable="true"
        @input="updateBlock(index, $event)"
        @focus="focusedIndex = index"
        @keydown.enter.prevent="handleEnter(index, $event)"
        @keydown.backspace="handleBackspace(index, $event)"
        @keydown.up="moveFocus(index, -1, $event)"
        @keydown.down="moveFocus(index, 1, $event)"
        v-html="block.content"
      />
      
      <div class="block-actions">
        <el-dropdown trigger="click" @command="(cmd) => handleCommand(cmd, index)">
          <el-icon class="action-icon"><More /></el-icon>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="heading">转为标题</el-dropdown-item>
              <el-dropdown-item command="quote">转为引用</el-dropdown-item>
              <el-dropdown-item command="list">转为列表</el-dropdown-item>
              <el-dropdown-item divided command="delete">删除</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
    
    <div v-if="!modelValue.length" class="empty-state" @click="addBlock(0)">
      <el-icon><EditPen /></el-icon>
      <span>点击开始写作，输入 / 查看命令</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import type { Block } from '@/stores/project'

const props = defineProps<{
  modelValue: Block[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: Block[]): void
}>()

const focusedIndex = ref(-1)

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
    const blocks = document.querySelectorAll('.block-content')
    if (blocks[index + 1]) {
      (blocks[index + 1] as HTMLElement).focus()
    }
  })
}

function updateBlock(index: number, event: Event) {
  const target = event.target as HTMLElement
  const newBlocks = [...props.modelValue]
  newBlocks[index] = { ...newBlocks[index], content: target.innerText }
  emit('update:modelValue', newBlocks)
}

function handleEnter(index: number, event: Event) {
  const target = event.target as HTMLElement
  const cursorPosition = getCursorPosition(target)
  const text = target.innerText
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
    const blocks = document.querySelectorAll('.block-content')
    if (blocks[index + 1]) {
      const el = blocks[index + 1] as HTMLElement
      el.focus()
      setCursorToStart(el)
    }
  })
}

function handleBackspace(index: number, event: Event) {
  const target = event.target as HTMLElement
  if (target.innerText === '' && props.modelValue.length > 1) {
    event.preventDefault()
    const newBlocks = props.modelValue.filter((_, i) => i !== index)
    emit('update:modelValue', newBlocks)
    
    nextTick(() => {
      const blocks = document.querySelectorAll('.block-content')
      if (blocks[index - 1]) {
        (blocks[index - 1] as HTMLElement).focus()
      }
    })
  }
}

function moveFocus(index: number, direction: number, event: Event) {
  const newIndex = index + direction
  if (newIndex >= 0 && newIndex < props.modelValue.length) {
    event.preventDefault()
    const blocks = document.querySelectorAll('.block-content')
    if (blocks[newIndex]) {
      (blocks[newIndex] as HTMLElement).focus()
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
  }
}

function focusLast() {
  if (!props.modelValue.length) {
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
</script>

<style scoped>
.block-editor {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px 0;
}

.block-wrapper {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 4px 0;
  border-radius: 4px;
  transition: background 0.2s;
}

.block-wrapper:hover {
  background: #f5f7fa;
}

.block-wrapper:hover .block-handle,
.block-wrapper:hover .block-actions {
  opacity: 1;
}

.block-handle {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: grab;
  opacity: 0;
  color: #c0c4cc;
}

.block-content {
  flex: 1;
  min-height: 32px;
  padding: 6px 8px;
  line-height: 1.6;
  outline: none;
  border-radius: 4px;
  transition: background 0.2s;
}

.block-content:focus {
  background: #f5f7fa;
}

.block-content[data-type="heading"] {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.block-content[data-type="quote"] {
  border-left: 4px solid #409eff;
  padding-left: 16px;
  color: #606266;
  font-style: italic;
}

.block-content[data-type="list"] {
  padding-left: 24px;
}

.block-content[data-type="list"]::before {
  content: "• ";
  color: #409eff;
}

.block-actions {
  opacity: 0;
  display: flex;
  align-items: center;
}

.action-icon {
  padding: 4px;
  cursor: pointer;
  color: #c0c4cc;
  border-radius: 4px;
}

.action-icon:hover {
  color: #409eff;
  background: #ecf5ff;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 60px;
  color: #c0c4cc;
  cursor: pointer;
}

.empty-state:hover {
  color: #909399;
}
</style>