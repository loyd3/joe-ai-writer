<template>
  <el-dialog
    v-model="visible"
    title="主题设置"
    width="420px"
    class="theme-dialog"
    :close-on-click-modal="true"
    @closed="onClosed"
  >
    <div class="theme-section">
      <div class="section-label">预设主题</div>
      <div class="preset-list">
        <button
          v-for="preset in THEME_PRESETS"
          :key="preset.id"
          type="button"
          class="preset-item"
          :class="{ active: themeStore.presetId === preset.id }"
          @click="themeStore.setPreset(preset.id)"
        >
          <span class="preset-swatch" :style="{ background: preset.primary }" />
          <span class="preset-name">{{ preset.name }}</span>
        </button>
      </div>
    </div>
    <div class="theme-section">
      <div class="section-label">自定义主题色</div>
      <div class="custom-row">
        <el-color-picker
          v-model="customColorLocal"
          :predefine="predefineColors"
          @change="onCustomColorChange"
        />
        <el-input
          v-model="customColorLocal"
          class="custom-hex-input"
          placeholder="#a65e2e"
          maxlength="9"
          @change="onCustomColorChange"
        />
      </div>
      <div class="custom-hint">选择颜色后将自动应用为「自定义」主题</div>
    </div>
    <template #footer>
      <el-button type="primary" @click="visible = false">完成</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useThemeStore, THEME_PRESETS } from '@/stores/theme'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const themeStore = useThemeStore()
const visible = ref(props.modelValue)
const customColorLocal = ref(themeStore.customColor)

const predefineColors = [
  '#a65e2e',
  '#C46B83',
  '#5AAF8F',
  '#8574B2',
  '#5E9AB8',
  '#D4889D',
  '#78C4A6',
  '#A090C8',
  '#C48A6A',
  '#7DB2CC',
]

watch(
  () => props.modelValue,
  (v) => {
    visible.value = v
    if (v) customColorLocal.value = themeStore.customColor
  }
)
watch(visible, (v) => emit('update:modelValue', v))

function onCustomColorChange(val: string | undefined) {
  const v = (val ?? (customColorLocal.value || '')).trim()
  if (!v) return
  if (/^#[0-9A-Fa-f]{6}$/.test(v) || /^#[0-9A-Fa-f]{8}$/.test(v)) {
    themeStore.setCustomColor(v)
  }
}

function onClosed() {
  emit('update:modelValue', false)
}
</script>

<style scoped lang="scss">
.theme-section {
  margin-bottom: 20px;

  &:last-of-type {
    margin-bottom: 0;
  }
}

.section-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--coffee-text);
  margin-bottom: 10px;
}

.preset-list {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.preset-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border: 2px solid var(--coffee-border);
  border-radius: 10px;
  background: var(--coffee-bg-card);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--coffee-primary-light);
    background: var(--coffee-bg-warm);
  }

  &.active {
    border-color: var(--coffee-primary);
    background: var(--coffee-bg-warm);
    box-shadow: 0 0 0 1px var(--coffee-primary);
  }

  .preset-swatch {
    width: 24px;
    height: 24px;
    border-radius: 6px;
    flex-shrink: 0;
  }

  .preset-name {
    font-size: 14px;
    color: var(--coffee-text);
  }
}

.custom-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.custom-hex-input {
  flex: 1;
  max-width: 140px;
}

.custom-hint {
  font-size: 12px;
  color: var(--coffee-text-muted);
  margin-top: 8px;
}
</style>
