<template>
  <div class="ai-config-panel settings-fill" v-loading="loading">
    <div class="top-bar">
      <div class="status-models">
        <div class="status-model">
          <div class="provider-badge local">本</div>
          <div class="min-w-0">
            <div class="status-title">
              本地
              <el-tag v-if="form.local_model && form.local_base_url" size="small" type="success">已填</el-tag>
              <el-tag v-else size="small" type="warning">待配置</el-tag>
            </div>
            <div class="status-sub">Ollama · {{ form.local_model || '未填模型' }}</div>
          </div>
        </div>
        <div class="status-model">
          <div class="provider-badge">线</div>
          <div class="min-w-0">
            <div class="status-title">
              线上
              <el-tag v-if="hasOnlineKey" size="small" type="success">可用</el-tag>
              <el-tag v-else size="small" type="warning">待配置</el-tag>
            </div>
            <div class="status-sub">{{ currentProvider?.name || form.provider }} · {{ form.model || '未填模型' }}</div>
          </div>
        </div>
      </div>
      <div class="top-bar-right">
        <el-tag size="small" :type="configSource === 'database' ? 'success' : 'info'" effect="plain">
          {{ configSource === 'database' ? '已保存' : '环境默认' }}
        </el-tag>
        <el-radio-group v-model="form.preferred_mode" size="small" class="mode-group" @change="onPreferredModeChange">
          <el-radio-button value="local">用本地</el-radio-button>
          <el-radio-button value="online">用线上</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <div class="config-columns">
      <section class="config-section draft-box">
        <div class="section-title">本地 Ollama</div>
        <p class="hint">
          Docker 访问本机用 <code>http://host.docker.internal:11434/v1</code>；中文建议 <code>qwen2.5:14b</code>
        </p>
        <el-form label-position="top" class="config-form">
          <el-form-item label="模型">
            <el-input v-model="form.local_model" placeholder="例如 qwen2.5:14b" clearable />
          </el-form-item>
          <el-form-item label="Ollama 地址">
            <el-input v-model="form.local_base_url" placeholder="http://localhost:11434/v1" />
          </el-form-item>
          <el-form-item label="思考模式">
            <el-switch v-model="form.local_think" active-text="开启" inactive-text="关闭" />
            <div class="form-hint">Qwen3 / qwen3.8 等支持思考的模型生效。关闭后直接写正文，更省时间和显存。</div>
          </el-form-item>
          <el-form-item>
            <el-checkbox v-model="form.local_fallback">本地失败时提示改用线上</el-checkbox>
          </el-form-item>
          <el-button :loading="testingLocal" @click="testLocal">测试本地连接</el-button>
        </el-form>
      </section>

      <section class="config-section">
        <div class="section-title">线上模型</div>
        <div class="provider-grid">
          <button
            v-for="p in providers"
            :key="p.id"
            type="button"
            class="provider-card"
            :class="{ active: form.provider === p.id }"
            @click="selectProvider(p.id)"
          >
            <strong>{{ p.name }}</strong>
            <span>{{ p.description }}</span>
          </button>
        </div>

        <el-form :model="form" label-position="top" class="config-form">
          <el-form-item label="API Key" required>
            <el-input
              v-model="form.apiKey"
              type="password"
              show-password
              :placeholder="apiKeyPlaceholder"
            />
          </el-form-item>

          <div class="form-row">
            <el-form-item label="模型" class="grow">
              <el-select v-model="form.model" style="width: 100%" filterable allow-create default-first-option>
                <el-option v-for="m in currentProvider?.models || []" :key="m" :label="m" :value="m" />
              </el-select>
            </el-form-item>
          </div>

          <el-form-item v-if="form.provider === 'custom'" label="API 地址" required>
            <el-input v-model="form.baseUrl" placeholder="https://your-api-endpoint.com/v1" />
          </el-form-item>

          <el-collapse v-model="advancedOpen">
            <el-collapse-item title="采样参数" name="advanced">
              <el-form-item label="Temperature">
                <el-slider v-model="form.temperature" :min="0" :max="2" :step="0.1" show-input />
              </el-form-item>
              <el-form-item label="Max Tokens">
                <el-slider v-model="form.maxTokens" :min="256" :max="16384" :step="256" show-input />
              </el-form-item>
            </el-collapse-item>
          </el-collapse>

          <div class="actions">
            <el-button :loading="testing" @click="testOnline">测试线上</el-button>
          </div>
        </el-form>
      </section>
    </div>

    <div class="footer-bar">
      <el-alert
        v-if="testResult"
        class="test-alert"
        :title="testResult.success ? '连接成功' : '连接失败'"
        :type="testResult.success ? 'success' : 'error'"
        :closable="true"
        show-icon
        @close="testResult = null"
      >
        <div>{{ testResult.message }}</div>
      </el-alert>
      <div class="actions">
        <el-button @click="resetToDefault">重置</el-button>
        <el-button type="primary" :loading="saving" @click="saveConfig">保存配置</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { systemApi } from '@/api'
import { useAiModeStore, type AiPreferredMode } from '@/stores/aiMode'

interface Provider {
  id: string
  name: string
  description: string
  models: string[]
}

const emit = defineEmits<{ saved: [] }>()
const aiModeStore = useAiModeStore()

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const testingLocal = ref(false)
const advancedOpen = ref<string[]>([])
const providers = ref<Provider[]>([])
const configSource = ref('env')
const testResult = ref<{ success: boolean; message: string } | null>(null)

const form = ref({
  provider: 'deepseek',
  model: 'deepseek-chat',
  apiKey: '',
  baseUrl: '',
  temperature: 0.7,
  maxTokens: 4096,
  preferred_mode: 'online' as 'online' | 'local',
  local_model: 'qwen2.5:14b',
  local_base_url: 'http://localhost:11434/v1',
  local_fallback: true,
  local_think: false,
})

const currentProvider = computed(() => providers.value.find((p) => p.id === form.value.provider))
const hasOnlineKey = computed(() => !!form.value.apiKey && !String(form.value.apiKey).endsWith('...'))
const apiKeyPlaceholder = computed(() =>
  form.value.apiKey && String(form.value.apiKey).endsWith('...')
    ? `已配置（${form.value.apiKey}），留空或重填`
    : '输入 API Key'
)

onMounted(() => loadConfig())

watch(
  () => aiModeStore.preferredMode,
  (mode) => {
    if (form.value.preferred_mode !== mode) form.value.preferred_mode = mode
  },
)

async function loadConfig() {
  loading.value = true
  try {
    const res = await systemApi.aiConfig()
    providers.value = (res.data.available_providers || []).filter((p: Provider) => p.id !== 'ollama')
    if (res.data.provider && res.data.provider !== 'ollama') {
      form.value.provider = res.data.provider
      form.value.model = res.data.model || form.value.model
    }
    let serverMode: 'online' | 'local' | null = null
    try {
      const userRes = await systemApi.getUserAIConfig()
      const u = userRes.data
      if (u?.provider && u.provider !== 'ollama') {
        form.value.provider = u.provider
        form.value.model = u.model || form.value.model
        form.value.baseUrl = u.base_url || ''
        form.value.temperature = u.temperature ?? form.value.temperature
        form.value.maxTokens = u.max_tokens ?? form.value.maxTokens
        if (u.api_key) form.value.apiKey = u.api_key
      }
      serverMode = u.preferred_mode === 'local' ? 'local' : 'online'
      form.value.preferred_mode = serverMode
      form.value.local_model = u.local_model || form.value.local_model
      form.value.local_base_url = u.local_base_url || form.value.local_base_url
      form.value.local_fallback = u.local_fallback !== false
      form.value.local_think = u.local_think === true
      configSource.value = u.source || 'env'
    } catch {
      /* env fallback */
    }
    loadFromLocalStorage({ keepPreferredMode: serverMode })
    aiModeStore.syncFromConfig(form.value.preferred_mode, {
      local_model: form.value.local_model,
      provider: form.value.provider,
      model: form.value.model,
    })
  } catch (e) {
    console.error(e)
    loadFromLocalStorage()
  } finally {
    loading.value = false
  }
}

async function onPreferredModeChange(mode: string | number | boolean | undefined) {
  if (mode !== 'local' && mode !== 'online') return
  const ok = await aiModeStore.setMode(mode as AiPreferredMode)
  if (!ok) {
    form.value.preferred_mode = aiModeStore.preferredMode
  }
}

function loadFromLocalStorage(opts?: { keepPreferredMode?: 'online' | 'local' | null }) {
  try {
    const saved = localStorage.getItem('joe-ai-config')
    if (!saved) return
    const parsed = JSON.parse(saved)
    const { preferred_mode: _mode, ...rest } = parsed
    if (parsed.apiKey && !String(parsed.apiKey).endsWith('...')) {
      form.value = { ...form.value, ...rest }
    } else {
      const { apiKey: _i, ...withoutKey } = rest
      form.value = { ...form.value, ...withoutKey }
    }
    if (opts?.keepPreferredMode) {
      form.value.preferred_mode = opts.keepPreferredMode
    }
  } catch { /* ignore */ }
}

function selectProvider(id: string) {
  form.value.provider = id
  const provider = providers.value.find((p) => p.id === id)
  if (provider?.models?.length) {
    const recommended = provider.models.find((m) =>
      (id === 'deepseek' && m === 'deepseek-chat') ||
      (id === 'openai' && m === 'gpt-4') ||
      (id === 'siliconflow' && m.includes('DeepSeek-V3')) ||
      (id === 'yxai' && m === 'deepseek-flash')
    )
    form.value.model = recommended || provider.models[0]
  }
  form.value.apiKey = ''
  form.value.baseUrl = ''
  testResult.value = null
}

async function testOnline() {
  if (!form.value.apiKey || String(form.value.apiKey).endsWith('...')) {
    ElMessage.warning('请输入完整的线上 API Key')
    return
  }
  testing.value = true
  testResult.value = null
  try {
    const res = await systemApi.testAI({
      provider: form.value.provider as any,
      model: form.value.model,
      api_key: form.value.apiKey,
      base_url: form.value.baseUrl || undefined,
      temperature: form.value.temperature,
    })
    testResult.value = { success: !!res.data.success, message: res.data.message || '' }
    if (res.data.success) ElMessage.success('线上连接成功')
    else ElMessage.error('线上连接失败')
  } catch {
    testResult.value = { success: false, message: '请求失败，请检查网络' }
  } finally {
    testing.value = false
  }
}

async function testLocal() {
  if (!form.value.local_base_url.trim()) {
    ElMessage.warning('请填写 Ollama 地址')
    return
  }
  testingLocal.value = true
  testResult.value = null
  try {
    const res = await systemApi.testAI({
      provider: 'ollama',
      model: form.value.local_model,
      api_key: 'ollama',
      base_url: form.value.local_base_url,
    })
    testResult.value = { success: !!res.data.success, message: res.data.message || '' }
    if (res.data.success) ElMessage.success('本地 Ollama 连接成功')
    else ElMessage.error('本地连接失败，请确认 Ollama 已启动')
  } catch {
    testResult.value = { success: false, message: '本地连接失败' }
  } finally {
    testingLocal.value = false
  }
}

async function saveConfig() {
  const preferredMode = aiModeStore.preferredMode
  if (preferredMode === 'online') {
    if (!form.value.apiKey) {
      ElMessage.warning('使用线上模式时请填写 API Key')
      return
    }
    // 脱敏 key（sk-xxx...）表示库里已有真实 key，后端会保留，不必重填
  }
  if (preferredMode === 'local' && !form.value.local_base_url.trim()) {
    ElMessage.warning('使用本地模式时请填写 Ollama 地址')
    return
  }
  if (form.value.provider === 'custom' && !form.value.baseUrl.trim()) {
    ElMessage.warning('自定义提供商需要填写 API 地址')
    return
  }

  saving.value = true
  try {
    const preferredMode = aiModeStore.preferredMode
    form.value.preferred_mode = preferredMode
    const payload: any = {
      provider: form.value.provider,
      model: form.value.model,
      base_url: form.value.baseUrl || undefined,
      temperature: form.value.temperature,
      max_tokens: form.value.maxTokens,
      preferred_mode: preferredMode,
      local_model: form.value.local_model,
      local_base_url: form.value.local_base_url,
      local_fallback: form.value.local_fallback,
      local_think: form.value.local_think,
    }
    if (form.value.apiKey && !String(form.value.apiKey).endsWith('...')) {
      payload.api_key = form.value.apiKey
    } else if (preferredMode === 'online') {
      payload.api_key = form.value.apiKey
    }

    await systemApi.saveUserAIConfig(payload)
    localStorage.setItem('joe-ai-config', JSON.stringify({
      provider: form.value.provider,
      model: form.value.model,
      apiKey: form.value.apiKey,
      baseUrl: form.value.baseUrl,
      temperature: form.value.temperature,
      maxTokens: form.value.maxTokens,
      preferred_mode: preferredMode,
      local_model: form.value.local_model,
      local_base_url: form.value.local_base_url,
      local_fallback: form.value.local_fallback,
      local_think: form.value.local_think,
    }))
    configSource.value = 'database'
    aiModeStore.syncFromConfig(preferredMode, {
      local_model: form.value.local_model,
      provider: form.value.provider,
      model: form.value.model,
    })
    ElMessage.success(
      preferredMode === 'local'
        ? '已保存，当前默认使用本地 Ollama'
        : '已保存，当前默认使用线上模型'
    )
    emit('saved')
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || '保存失败'
    ElMessage.error(typeof msg === 'string' ? msg : '保存失败')
  } finally {
    saving.value = false
  }
}

async function resetToDefault() {
  form.value = {
    provider: 'deepseek',
    model: 'deepseek-chat',
    apiKey: '',
    baseUrl: '',
    temperature: 0.7,
    maxTokens: 4096,
    preferred_mode: 'online',
    local_model: 'qwen2.5:14b',
    local_base_url: 'http://localhost:11434/v1',
    local_fallback: true,
    local_think: false,
  }
  localStorage.removeItem('joe-ai-config')
  try {
    await systemApi.deleteUserAIConfig()
    ElMessage.success('已清除用户配置，将使用服务器环境变量')
    configSource.value = 'env'
  } catch {
    ElMessage.success('已重置本地配置')
  }
  aiModeStore.syncFromConfig('online', {
    local_model: form.value.local_model,
    provider: form.value.provider,
    model: form.value.model,
  })
  testResult.value = null
}
</script>

<style scoped lang="scss">
.ai-config-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 8px;
  width: 100%;
  max-width: none;
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding: 14px 16px;
  border: 1px solid var(--coffee-border);
  border-radius: 12px;
  background: var(--coffee-bg-card);
}

.status-models {
  display: flex;
  align-items: center;
  gap: 20px;
  min-width: 0;
  flex: 1;
}

.status-model {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.top-bar-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.provider-badge {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 13px;
  color: #fff;
  background: var(--coffee-primary, #8b6914);
  flex-shrink: 0;
  &.local { background: #3d8b5a; }
}

.status-title {
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--coffee-text);
}

.status-sub {
  font-size: 12px;
  color: var(--coffee-text-muted);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 220px;
}

.form-hint,
.hint {
  font-size: 12px;
  color: var(--coffee-text-muted);
  line-height: 1.5;
  margin: 0 0 12px;
  code {
    font-size: 11px;
    padding: 1px 5px;
    border-radius: 4px;
    background: rgba(0, 0, 0, 0.06);
  }
}

.config-columns {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
  align-items: start;

  @media (min-width: 900px) {
    grid-template-columns: 1fr 1.15fr;
  }
}

.config-section {
  border: 1px solid var(--coffee-border);
  border-radius: 12px;
  padding: 16px 18px;
  background: var(--coffee-bg-card);
  min-width: 0;
}

.draft-box {
  border-color: rgba(61, 139, 90, 0.35);
  background: linear-gradient(180deg, rgba(61, 139, 90, 0.06), var(--coffee-bg-card));
}

.section-title {
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 8px;
  color: var(--coffee-text);
}

.provider-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 8px;
  margin: 0 0 14px;
}

.provider-card {
  text-align: left;
  border: 1px solid var(--coffee-border);
  border-radius: 10px;
  padding: 8px 10px;
  background: transparent;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  strong {
    display: block;
    font-size: 12px;
    color: var(--coffee-text);
    margin-bottom: 2px;
  }
  span {
    font-size: 11px;
    color: var(--coffee-text-muted);
    line-height: 1.3;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  &.active {
    border-color: var(--coffee-primary, #8b6914);
    background: rgba(139, 105, 20, 0.08);
  }
}

.config-form {
  :deep(.el-form-item) { margin-bottom: 12px; }
}

.form-row {
  display: flex;
  gap: 12px;
  .grow { flex: 1; min-width: 0; }
}

.mode-group {
  flex-shrink: 0;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.footer-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding-top: 4px;
}

.test-alert {
  flex: 1;
  min-width: 200px;
  margin: 0;
}
</style>
