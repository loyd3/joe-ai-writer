<template>
  <div class="theme-settings-panel settings-fill">
    <div class="theme-grid">
      <section class="theme-card">
        <div class="section-label">外观模式</div>
        <el-radio-group :model-value="themeStore.mode" class="mode-group" @change="onModeChange">
          <el-radio-button value="light">
            <el-icon><Sunny /></el-icon> 浅色
          </el-radio-button>
          <el-radio-button value="dark">
            <el-icon><Moon /></el-icon> 深色
          </el-radio-button>
          <el-radio-button value="system">
            <el-icon><Monitor /></el-icon> 跟随系统
          </el-radio-button>
        </el-radio-group>
      </section>

      <section class="theme-card">
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
        <div class="custom-hint">选择颜色后自动应用为「自定义」主题</div>
      </section>

      <section class="theme-card span-full">
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
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Sunny, Moon, Monitor } from '@element-plus/icons-vue'
import { useThemeStore, THEME_PRESETS, type ThemeMode } from '@/stores/theme'

const themeStore = useThemeStore()
const customColorLocal = ref(themeStore.customColor)

const predefineColors = [
  '#8F4E22',
  '#B04F6A',
  '#3F9575',
  '#6B5899',
  '#457FA0',
  '#C46B83',
  '#5AAF8F',
  '#8574B2',
  '#A65E2E',
  '#5E9AB8',
]

watch(
  () => themeStore.customColor,
  (v) => {
    if (v !== customColorLocal.value) customColorLocal.value = v
  },
)

function onModeChange(val: string | number | boolean | undefined) {
  themeStore.setMode(val as ThemeMode)
}

function onCustomColorChange(val: string | undefined) {
  const v = (val ?? (customColorLocal.value || '')).trim()
  if (!v) return
  if (/^#[0-9A-Fa-f]{6}$/.test(v) || /^#[0-9A-Fa-f]{8}$/.test(v)) {
    themeStore.setCustomColor(v)
  }
}
</script>

<style scoped lang="scss">
.theme-settings-panel {
  width: 100%;
}

.theme-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;

  @media (min-width: 640px) {
    grid-template-columns: 1fr 1fr;
  }
}

.theme-card {
  border: 1px solid var(--coffee-border);
  border-radius: 12px;
  padding: 16px 18px;
  background: var(--coffee-bg-card);
  min-width: 0;

  &.span-full {
    grid-column: 1 / -1;
  }
}

.section-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--coffee-text);
  margin-bottom: 12px;
}

.mode-group {
  width: 100%;
  display: flex;

  :deep(.el-radio-button) {
    flex: 1;

    .el-radio-button__inner {
      width: 100%;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
    }
  }
}

.preset-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px;
}

.preset-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border: 2px solid var(--coffee-border);
  border-radius: 10px;
  background: var(--coffee-bg);
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
    width: 22px;
    height: 22px;
    border-radius: 6px;
    flex-shrink: 0;
  }

  .preset-name {
    font-size: 13px;
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
  max-width: 180px;
}

.custom-hint {
  font-size: 12px;
  color: var(--coffee-text-muted);
  margin-top: 10px;
}
</style>
