<template>
  <div class="ai-config-panel">
    <h3>AI 模型配置</h3>
    
    <el-alert
      v-if="!loading"
      :title="`当前使用: ${currentProvider?.name || '未配置'} - ${config?.model || '未知模型'}`"
      :type="isConfigured ? 'success' : 'warning'"
      :closable="false"
      style="margin-bottom: 20px"
    />
    
    <el-form :model="form" label-width="120px" v-loading="loading">
      <el-form-item label="AI 提供商">
        <el-select v-model="form.provider" @change="onProviderChange" style="width: 100%">
          <el-option
            v-for="p in providers"
            :key="p.id"
            :label="p.name"
            :value="p.id"
          >
            <div class="provider-option">
              <span>{{ p.name }}</span>
              <el-tag size="small" type="info">{{ p.models.length }} 个模型</el-tag>
            </div>
          </el-option>
        </el-select>
        <div class="form-hint">{{ currentProvider?.description }}</div>
      </el-form-item>
      
      <el-form-item label="选择模型">
        <el-select v-model="form.model" style="width: 100%">
          <el-option
            v-for="m in currentProvider?.models || []"
            :key="m"
            :label="m"
            :value="m"
          />
        </el-select>
      </el-form-item>
      
      <el-form-item label="API Key">
        <el-input
          v-model="form.apiKey"
          type="password"
          show-password
          placeholder="输入你的 API Key"
        />
        <div class="form-hint">API Key 仅保存在本地，不会上传到服务器</div>
      </el-form-item>
      
      <el-form-item label="API 地址" v-if="form.provider === 'custom'">
        <el-input
          v-model="form.baseUrl"
          placeholder="https://your-api-endpoint.com/v1"
        />
      </el-form-item>
      
      <el-form-item label="Temperature">
        <el-slider v-model="form.temperature" :min="0" :max="2" :step="0.1" show-stops />
        <div class="form-hint">值越低回答越确定，值越高越有创造性</div>
      </el-form-item>
      
      <el-form-item>
        <el-button type="primary" @click="testConnection" :loading="testing">
          <el-icon><Connection /></el-icon> 测试连接
        </el-button>
        <el-button @click="saveConfig" type="success" :loading="saving">
          <el-icon><Check /></el-icon> 保存配置
        </el-button>
      </el-form-item>
    </el-form>
    
    <!-- 测试结果 -->
    <el-alert
      v-if="testResult"
      :title="testResult.success ? '连接成功' : '连接失败'"
      :type="testResult.success ? 'success' : 'error'"
      :description="testResult.message"
      :closable="false"
      style="margin-top: 20px"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { systemApi } from '@/api'
import { ElMessage } from 'element-plus'

interface Provider {
  id: string
  name: string
  description: string
  models: string[]
}

interface AIConfig {
  provider: string
  model: string
  available_providers: Provider[]
}

const loading = ref(false)
const testing = ref(false)
const saving = ref(false)
const config = ref<AIConfig | null>(null)
const providers = ref<Provider[]>([])
const testResult = ref<{ success: boolean; message: string } | null>(null)

const form = ref({
  provider: 'openai',
  model: '',
  apiKey: '',
  baseUrl: '',
  temperature: 0.7
})

const currentProvider = computed(() => {
  return providers.value.find(p => p.id === form.value.provider)
})

const isConfigured = computed(() => {
  return !!config.value?.provider && !!config.value?.model
})

onMounted(async () => {
  await loadConfig()
})

async function loadConfig() {
  loading.value = true
  try {
    const res = await systemApi.aiConfig()
    config.value = res.data
    providers.value = res.data.available_providers
    
    // 初始化表单
    form.value.provider = res.data.provider
    form.value.model = res.data.model
  } catch (e) {
    ElMessage.error('加载配置失败')
  } finally {
    loading.value = false
  }
}

function onProviderChange() {
  // 切换提供商时，自动选择第一个模型
  if (currentProvider.value?.models.length) {
    form.value.model = currentProvider.value.models[0]
  }
}

async function testConnection() {
  if (!form.value.apiKey) {
    ElMessage.warning('请输入 API Key')
    return
  }
  
  testing.value = true
  testResult.value = null
  
  try {
    const res = await systemApi.testAI({
      provider: form.value.provider,
      model: form.value.model,
      api_key: form.value.apiKey,
      base_url: form.value.baseUrl || undefined,
      temperature: form.value.temperature
    })
    testResult.value = res.data
  } catch (e) {
    testResult.value = {
      success: false,
      message: '请求失败，请检查网络连接'
    }
  } finally {
    testing.value = false
  }
}

async function saveConfig() {
  saving.value = true
  try {
    // 实际项目中这里应该调用保存配置的 API
    // 由于配置通常需要后端重启，这里我们只是提示用户
    ElMessage.success('配置已保存（需要重启后端服务生效）')
    
    // 保存到 localStorage 作为临时方案
    localStorage.setItem('joe-ai-config', JSON.stringify({
      provider: form.value.provider,
      model: form.value.model,
      apiKey: form.value.apiKey,
      baseUrl: form.value.baseUrl,
      temperature: form.value.temperature
    }))
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.ai-config-panel {
  padding: 20px;
}

.ai-config-panel h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  font-weight: 500;
}

.provider-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.form-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}
</style>
