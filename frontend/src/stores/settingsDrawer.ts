import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export type SettingsPanel = 'profile' | 'writing-style' | 'ai-config' | 'theme'

const PANEL_META: Record<SettingsPanel, { title: string; subtitle: string }> = {
  profile: { title: '个人中心', subtitle: '头像、资料与密码' },
  'writing-style': { title: '文风库', subtitle: '系统级文风：预设、手建或从范文提炼' },
  'ai-config': { title: '大模型设置', subtitle: '本地 Ollama 与线上模型' },
  theme: { title: '主题设置', subtitle: '外观模式、预设与自定义主题色' },
}

export const useSettingsDrawerStore = defineStore('settingsDrawer', () => {
  const open = ref(false)
  const panel = ref<SettingsPanel>('ai-config')

  const meta = computed(() => PANEL_META[panel.value])

  function show(next: SettingsPanel) {
    panel.value = next
    open.value = true
  }

  function close() {
    open.value = false
  }

  return { open, panel, meta, show, close }
})
