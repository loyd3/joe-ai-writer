<template>
  <el-popover
    v-model:visible="visible"
    placement="bottom-end"
    :width="300"
    trigger="click"
    :persistent="true"
    popper-class="ai-assist-popper"
  >
    <template #reference>
      <el-button
        class="ai-assist-trigger"
        link
        type="primary"
        :loading="loading"
        :disabled="disabled"
      >
        <el-icon><MagicStick /></el-icon>
        <span>AI</span>
      </el-button>
    </template>

    <div class="ai-assist-panel" @click.stop>
      <div class="modes">
        <button
          v-for="m in modes"
          :key="m.value"
          type="button"
          class="mode-btn"
          :class="{ active: mode === m.value }"
          @click="mode = m.value"
        >
          {{ m.label }}
        </button>
      </div>
      <el-input
        v-model="instruction"
        type="textarea"
        :rows="2"
        placeholder="可选：补充要求，如更暗黑、更简洁…"
        maxlength="200"
      />
      <div class="actions">
        <el-button size="small" :disabled="loading" @click="visible = false">取消</el-button>
        <el-button type="primary" size="small" :loading="loading" @click="runAssist">
          {{ runLabel }}
        </el-button>
      </div>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { MagicStick } from '@element-plus/icons-vue'
import { memoryApi } from '@/api'

const props = withDefaults(defineProps<{
  projectId: number
  field: string
  currentValue?: string
  extra?: Record<string, any>
  disabled?: boolean
}>(), {
  currentValue: '',
  disabled: false
})

const emit = defineEmits<{
  (e: 'result', value: string): void
}>()

const visible = ref(false)
const loading = ref(false)
const instruction = ref('')
const mode = ref<'auto' | 'generate' | 'expand' | 'refine'>('auto')
let reqId = 0

const modes = [
  { value: 'auto' as const, label: '智能' },
  { value: 'generate' as const, label: '生成' },
  { value: 'expand' as const, label: '扩写' },
  { value: 'refine' as const, label: '精炼' }
]

const runLabel = computed(() => {
  if (mode.value === 'generate') return '生成'
  if (mode.value === 'expand') return '扩写'
  if (mode.value === 'refine') return '精炼'
  return props.currentValue?.trim() ? '完善' : '生成'
})

async function runAssist() {
  if (!props.projectId) {
    ElMessage.warning('缺少项目信息')
    return
  }
  const myId = ++reqId
  const baseline = props.currentValue || ''
  const resolvedMode =
    mode.value === 'auto'
      ? (baseline.trim() ? 'expand' : 'generate')
      : (!baseline.trim() && (mode.value === 'expand' || mode.value === 'refine')
          ? 'generate'
          : mode.value)

  loading.value = true
  try {
    const res = await memoryApi.assist(props.projectId, {
      field: props.field,
      mode: resolvedMode,
      current_value: baseline,
      instruction: instruction.value || undefined,
      extra: props.extra
    })
    if (myId !== reqId) return
    if ((props.currentValue || '') !== baseline) {
      ElMessage.warning('字段已改动，未自动填入')
      return
    }
    const text = (res.data?.result || '').trim()
    if (!text) {
      ElMessage.warning('AI 未返回有效内容')
      return
    }
    emit('result', text)
    visible.value = false
    instruction.value = ''
    ElMessage.success('已填入')
  } catch (e: any) {
    if (myId === reqId) {
      ElMessage.error(e?.response?.data?.detail || e?.message || 'AI 辅助失败')
    }
  } finally {
    if (myId === reqId) loading.value = false
  }
}
</script>

<style scoped lang="scss">
.ai-assist-trigger {
  padding: 0 6px;
  height: 28px;
  font-size: 12px;
  font-weight: 600;
  gap: 2px;
  flex-shrink: 0;

  .el-icon {
    font-size: 14px;
  }
}

.ai-assist-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.modes {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
}

.mode-btn {
  border: 1px solid var(--coffee-border, #e8e0d5);
  background: var(--coffee-bg-card, #fff);
  color: var(--coffee-text-muted, #8a7a6a);
  border-radius: 6px;
  padding: 6px 0;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    border-color: var(--coffee-primary, #8b6914);
    color: var(--coffee-primary, #8b6914);
  }

  &.active {
    background: var(--coffee-primary, #8b6914);
    border-color: var(--coffee-primary, #8b6914);
    color: #fff;
  }
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
