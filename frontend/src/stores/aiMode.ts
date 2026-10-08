import { defineStore } from 'pinia'
import { ref } from 'vue'
import { systemApi } from '@/api'
import { ElMessage } from 'element-plus'

export type AiPreferredMode = 'online' | 'local'

export const useAiModeStore = defineStore('aiMode', () => {
  const preferredMode = ref<AiPreferredMode>('online')
  const loading = ref(false)
  const switching = ref(false)
  const localModel = ref('qwen2.5:14b')
  const onlineLabel = ref('线上模型')

  async function load() {
    loading.value = true
    try {
      const { data } = await systemApi.getUserAIConfig()
      preferredMode.value = data.preferred_mode === 'local' ? 'local' : 'online'
      localModel.value = data.local_model || localModel.value
      if (data.provider && data.model) {
        onlineLabel.value = `${data.provider} · ${data.model}`
      }
    } catch {
      /* 未登录或接口失败时保持默认 */
    } finally {
      loading.value = false
    }
  }

  function syncFromConfig(mode?: string | null, extras?: { local_model?: string; provider?: string; model?: string }) {
    if (mode === 'local' || mode === 'online') preferredMode.value = mode
    if (extras?.local_model) localModel.value = extras.local_model
    if (extras?.provider && extras?.model) {
      onlineLabel.value = `${extras.provider} · ${extras.model}`
    }
  }

  async function setMode(mode: AiPreferredMode, opts?: { silent?: boolean }) {
    if (mode === preferredMode.value) return true
    switching.value = true
    try {
      const { data } = await systemApi.setPreferredMode(mode)
      preferredMode.value = mode
      try {
        const saved = localStorage.getItem('joe-ai-config')
        if (saved) {
          const parsed = JSON.parse(saved)
          parsed.preferred_mode = mode
          localStorage.setItem('joe-ai-config', JSON.stringify(parsed))
        }
      } catch {
        /* ignore */
      }
      if (!opts?.silent) {
        ElMessage.success(data.message || (mode === 'local' ? '已切换到本地 AI' : '已切换到线上 AI'))
      }
      return true
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || '切换失败'
      ElMessage.error(typeof msg === 'string' ? msg : '切换失败')
      return false
    } finally {
      switching.value = false
    }
  }

  return {
    preferredMode,
    loading,
    switching,
    localModel,
    onlineLabel,
    load,
    syncFromConfig,
    setMode,
  }
})
