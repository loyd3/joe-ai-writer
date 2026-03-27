<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="ai-diff-overlay"
      @click="handleOverlayClick"
    >
      <div class="ai-diff-panel" @click.stop>
        <div class="diff-header">
          <div class="header-title">
            <el-icon class="ai-icon"><Star /></el-icon>
            <span>AI 改写建议</span>
          </div>
          <div class="header-actions">
            <el-button size="small" @click="reject">
              <el-icon><Close /></el-icon>
              拒绝
            </el-button>
            <el-button size="small" type="primary" @click="accept">
              <el-icon><Check /></el-icon>
              接受
            </el-button>
          </div>
        </div>

        <div class="diff-content">
          <div class="diff-section">
            <div class="section-label">原文</div>
            <div class="section-content original">{{ originalText }}</div>
          </div>

          <div class="diff-divider">
            <el-icon><ArrowDown /></el-icon>
          </div>

          <div class="diff-section">
            <div class="section-label">改写后</div>
            <div class="section-content rewritten">{{ rewrittenText }}</div>
          </div>

          <div class="diff-section inline-diff" v-if="hasChanges">
            <div class="section-label">差异对比</div>
            <div class="section-content diff-view" v-html="diffHtml"></div>
          </div>
        </div>

        <div class="diff-footer">
          <div class="diff-stats">
            <span class="stat removed">
              <span class="dot"></span>
              删除 {{ removedCount }} 字
            </span>
            <span class="stat added">
              <span class="dot"></span>
              新增 {{ addedCount }} 字
            </span>
          </div>
          <div class="footer-hint">
            按 <kbd>Esc</kbd> 取消，<kbd>Enter</kbd> 接受
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { Star, Check, Close, ArrowDown } from '@element-plus/icons-vue'

const props = defineProps<{
  visible: boolean
  originalText: string
  rewrittenText: string
}>()

const emit = defineEmits<{
  (e: 'accept', text: string): void
  (e: 'reject'): void
  (e: 'update:visible', visible: boolean): void
}>()

// 简单的 diff 算法
function computeDiff(original: string, rewritten: string): Array<{ type: 'same' | 'removed' | 'added'; text: string }> {
  const result: Array<{ type: 'same' | 'removed' | 'added'; text: string }> = []

  // 按行分割
  const originalLines = original.split('\n')
  const rewrittenLines = rewritten.split('\n')

  let i = 0, j = 0

  while (i < originalLines.length || j < rewrittenLines.length) {
    const origLine = originalLines[i]
    const newLine = rewrittenLines[j]

    if (i >= originalLines.length) {
      // 新增的行
      result.push({ type: 'added', text: newLine })
      j++
    } else if (j >= rewrittenLines.length) {
      // 删除的行
      result.push({ type: 'removed', text: origLine })
      i++
    } else if (origLine === newLine) {
      // 相同的行
      result.push({ type: 'same', text: origLine })
      i++
      j++
    } else {
      // 不同的行，标记为删除旧 + 新增新
      result.push({ type: 'removed', text: origLine })
      result.push({ type: 'added', text: newLine })
      i++
      j++
    }
  }

  return result
}

const diffResult = computed(() => {
  return computeDiff(props.originalText, props.rewrittenText)
})

const diffHtml = computed(() => {
  return diffResult.value.map(item => {
    const escaped = escapeHtml(item.text)
    if (item.type === 'same') {
      return `<div class="diff-line same">${escaped || '&nbsp;'}</div>`
    } else if (item.type === 'removed') {
      return `<div class="diff-line removed"><span class="mark">-</span> ${escaped || '&nbsp;'}</div>`
    } else {
      return `<div class="diff-line added"><span class="mark">+</span> ${escaped || '&nbsp;'}</div>`
    }
  }).join('')
})

const hasChanges = computed(() => {
  return props.originalText !== props.rewrittenText
})

const removedCount = computed(() => {
  return diffResult.value
    .filter(item => item.type === 'removed')
    .reduce((sum, item) => sum + item.text.length, 0)
})

const addedCount = computed(() => {
  return diffResult.value
    .filter(item => item.type === 'added')
    .reduce((sum, item) => sum + item.text.length, 0)
})

function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

function accept() {
  // 先关闭弹窗，避免父组件事件回调抛错时导致 close() 未执行
  close()
  try {
    emit('accept', props.rewrittenText)
  } catch (e) {
    console.error(e)
  }
}

function reject() {
  // 先关闭弹窗，避免父组件事件回调抛错时导致 close() 未执行
  close()
  try {
    emit('reject')
  } catch (e) {
    console.error(e)
  }
}

function close() {
  emit('update:visible', false)
}

function handleOverlayClick() {
  // 同样确保关闭弹窗不会被异常阻断
  reject()
}

function handleKeydown(e: KeyboardEvent) {
  if (!props.visible) return

  if (e.key === 'Escape') {
    e.preventDefault()
    reject()
  } else if (e.key === 'Enter') {
    e.preventDefault()
    accept()
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})

watch(() => props.visible, (visible) => {
  if (visible) {
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
})
</script>

<style scoped lang="scss">
.ai-diff-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  padding: 20px;
}

.ai-diff-panel {
  background: var(--coffee-bg-card);
  border-radius: 16px;
  width: 100%;
  max-width: 720px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.diff-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--coffee-border);
  background: linear-gradient(135deg, var(--coffee-bg-warm) 0%, var(--coffee-bg) 100%);

  .header-title {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 16px;
    font-weight: 600;
    color: var(--coffee-text);

    .ai-icon {
      width: 32px;
      height: 32px;
      background: linear-gradient(135deg, var(--coffee-primary) 0%, var(--coffee-primary-light) 100%);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      font-size: 18px;
    }
  }

  .header-actions {
    display: flex;
    gap: 8px;

    .el-button {
      border-radius: 8px;
    }
  }
}

.diff-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.diff-section {
  margin-bottom: 16px;

  &:last-child {
    margin-bottom: 0;
  }

  .section-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--coffee-text-light);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
  }

  .section-content {
    padding: 12px 16px;
    border-radius: 10px;
    font-size: 14px;
    line-height: 1.7;
    white-space: pre-wrap;
    word-break: break-word;

    &.original {
      background: var(--coffee-bg);
      border: 1px solid var(--coffee-border);
      color: var(--coffee-text);
    }

    &.rewritten {
      background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
      border: 1px solid #bae6fd;
      color: var(--coffee-text);
    }

    &.diff-view {
      background: var(--coffee-bg);
      border: 1px solid var(--coffee-border);
      padding: 0;
      overflow: hidden;
    }
  }
}

.diff-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px 0;
  color: var(--coffee-text-light);

  .el-icon {
    font-size: 20px;
  }
}

.diff-line {
  padding: 4px 16px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;

  &.same {
    color: var(--coffee-text);
  }

  &.removed {
    background: #fee2e2;
    color: #991b1b;

    .mark {
      color: #dc2626;
      font-weight: bold;
      margin-right: 8px;
    }
  }

  &.added {
    background: #dcfce7;
    color: #166534;

    .mark {
      color: #16a34a;
      font-weight: bold;
      margin-right: 8px;
    }
  }
}

.diff-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  border-top: 1px solid var(--coffee-border);
  background: var(--coffee-bg);
}

.diff-stats {
  display: flex;
  gap: 16px;

  .stat {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;

    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
    }

    &.removed {
      color: #dc2626;

      .dot {
        background: #dc2626;
      }
    }

    &.added {
      color: #16a34a;

      .dot {
        background: #16a34a;
      }
    }
  }
}

.footer-hint {
  font-size: 12px;
  color: var(--coffee-text-light);

  kbd {
    display: inline-block;
    padding: 2px 6px;
    background: var(--coffee-bg-hover);
    border: 1px solid var(--coffee-border);
    border-radius: 4px;
    font-family: ui-monospace, monospace;
    font-size: 11px;
    margin: 0 2px;
  }
}
</style>
