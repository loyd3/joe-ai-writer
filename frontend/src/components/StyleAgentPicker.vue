<template>
  <div class="style-agent-picker" :class="{ compact }">
    <span v-if="label" class="picker-label">{{ label }}</span>
    <div class="picker-chips">
      <button
        type="button"
        class="style-chip"
        :class="{ active: modelValue == null }"
        @click="emit('update:modelValue', undefined)"
      >
        {{ defaultLabel }}
      </button>
      <button
        v-for="a in agents"
        :key="a.id"
        type="button"
        class="style-chip"
        :class="{ active: modelValue === a.id }"
        :title="a.is_default ? `${a.name}（默认）` : (a.description || a.name)"
        @click="emit('update:modelValue', a.id)"
      >
        {{ a.name }}
        <span v-if="a.is_default" class="chip-badge">默</span>
      </button>
      <router-link v-if="showManageLink" class="manage-link" to="/writing-style">
        管理文风
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { styleAgentApi } from '@/api'
import type { StyleAgent } from '@/api/types'

const props = withDefaults(
  defineProps<{
    modelValue?: number
    label?: string
    defaultLabel?: string
    compact?: boolean
    showManageLink?: boolean
    /** 加载后若未选中，是否自动选中用户默认文风 */
    autoSelectDefault?: boolean
  }>(),
  {
    label: '文风',
    defaultLabel: '默认',
    compact: false,
    showManageLink: true,
    autoSelectDefault: true,
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: number | undefined]
}>()

const agents = ref<StyleAgent[]>([])

async function load() {
  try {
    const { data } = await styleAgentApi.list()
    agents.value = Array.isArray(data) ? data : []
    if (props.autoSelectDefault && props.modelValue == null) {
      const def = agents.value.find((a) => a.is_default)
      if (def) emit('update:modelValue', def.id)
    }
  } catch {
    agents.value = []
  }
}

onMounted(load)
watch(
  () => props.modelValue,
  () => {
    /* keep */
  }
)

defineExpose({ reload: load, agents })
</script>

<style scoped lang="scss">
.style-agent-picker {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;

  &.compact {
    flex-direction: row;
    align-items: flex-start;
    gap: 10px;

    .picker-label {
      padding-top: 6px;
      flex-shrink: 0;
    }
  }
}

.picker-label {
  font-size: 13px;
  color: var(--coffee-text-muted, #8a7a6a);
  font-weight: 500;
}

.picker-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.style-chip {
  appearance: none;
  border: 1px solid var(--coffee-border, #e0d5c8);
  background: var(--coffee-bg-card, #fff);
  color: var(--coffee-text, #3d3429);
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  line-height: 1.4;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s, color 0.15s;

  &:hover {
    border-color: var(--coffee-primary, #8b6914);
  }

  &.active {
    border-color: var(--coffee-primary, #8b6914);
    background: color-mix(in srgb, var(--coffee-primary, #8b6914) 12%, transparent);
    color: var(--coffee-primary, #8b6914);
    font-weight: 600;
  }
}

.chip-badge {
  margin-left: 2px;
  font-size: 10px;
  opacity: 0.75;
}

.manage-link {
  font-size: 12px;
  color: var(--coffee-primary, #8b6914);
  text-decoration: none;
  margin-left: 4px;

  &:hover {
    text-decoration: underline;
  }
}
</style>
