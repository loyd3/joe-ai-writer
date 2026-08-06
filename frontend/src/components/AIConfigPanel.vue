<template>
  <div class="ai-config-panel">
    <h3>
      <el-icon><Setting /></el-icon>
      AI 模型配置
    </h3>
    
    <!-- 当前状态 -->
    <el-card class="status-card" :class="{ 'is-active': isConfigured }">
      <div class="status-header">
        <el-avatar 
          :size="40" 
          :class="`provider-${currentProvider?.id || 'default'}`"
        >
          {{ currentProvider?.name?.charAt(0) || '?' }}
        </el-avatar>
        <div class="status-info">
          <div class="status-title">
            {{ currentProvider?.name || '未配置' }}
            <el-tag v-if="isConfigured" type="success" size="small">已配置</el-tag>
            <el-tag v-else type="warning" size="small">未配置</el-tag>
          </div>
          <div class="status-model">{{ config?.model || '请选择模型' }}</div>
        </div>
      </div>
    </el-card>
    
    <!-- 配置表单 -->
    <el-form :model="form" label-width="100px" v-loading="loading" class="config-form">
      
      <!-- 提供商选择 -->
      <el-form-item label="AI 提供商">
        <el-radio-group v-model="form.provider" @change="onProviderChange" size="large">
          <el-radio-button 
            v-for="p in providers" 
            :key="p.id" 
            :label="p.id"
          >
            <el-icon v-if="p.id === 'deepseek'"><ChromeFilled /></el-icon>
            <el-icon v-else-if="p.id === 'openai'"><Open /></el-icon>
            <el-icon v-else-if="p.id === 'siliconflow'"><Cpu /></el-icon>
            <el-icon v-else><Link /></el-icon>
            {{ p.name }}
          </el-radio-button>
        </el-radio-group>
        <div class="form-hint">{{ currentProvider?.description }}</div>
      </el-form-item>
      
      <!-- 模型选择 -->
      <el-form-item label="选择模型">
        <el-select v-model="form.model" style="width: 100%" size="large" placeholder="请选择模型">
          <el-option-group label="推荐模型">
            <el-option
              v-for="m in currentProvider?.models?.slice(0, 3) || []"
              :key="m"
              :label="m"
              :value="m"
            >
              <span>{{ m }}</span>
              <el-tag v-if="m.includes('deepseek-chat')" size="small" type="success" style="margin-left: 8px">推荐</el-tag>
            </el-option>
          </el-option-group>
          <el-option-group label="其他模型" v-if="currentProvider?.models?.length > 3">
            <el-option
              v-for="m in currentProvider?.models?.slice(3) || []"
              :key="m"
              :label="m"
              :value="m"
            />
          </el-option-group>
        </el-select>
      </el-form-item>
      
      <!-- API Key -->
      <el-form-item label="API Key" required>
        <el-input
          v-model="form.apiKey"
          type="password"
          show-password
          placeholder="输入你的 API Key"
          size="large"
        >
          <template #prefix>
            <el-icon><Key /></el-icon>
          </template>
        </el-input>
        <div class="form-hint">
          <el-icon><InfoFilled /></el-icon>
          保存后优先使用你填写的 API Key；未配置时才使用服务器环境变量
        </div>
      </el-form-item>
      
      <!-- 自定义 API 地址 -->
      <el-form-item label="API 地址" v-if="form.provider === 'custom'" required>
        <el-input
          v-model="form.baseUrl"
          placeholder="https://your-api-endpoint.com/v1"
          size="large"
        />
      </el-form-item>
      
      <!-- 高级设置折叠面板 -->
      <el-collapse v-model="activeCollapse">
        <el-collapse-item title="高级设置" name="advanced">
          
          <!-- Temperature -->
          <el-form-item label="Temperature">
            <el-slider 
              v-model="form.temperature" 
              :min="0" 
              :max="2" 
              :step="0.1" 
              show-stops 
              show-input
            />
            <div class="slider-labels">
              <span>精确</span>
              <span>平衡</span>
              <span>创造性</span>
            </div>
          </el-form-item>
          
          <!-- Max Tokens -->
          <el-form-item label="最大长度">
            <el-slider 
              v-model="form.maxTokens" 
              :min="256" 
              :max="8192" 
              :step="256" 
              show-stops
              :marks="{1024: '1K', 4096: '4K', 8192: '8K'}"
            />
          </el-form-item>
          
        </el-collapse-item>
      </el-collapse>
      
      <!-- 操作按钮 -->
      <el-form-item class="action-buttons">
        <el-button 
          type="primary" 
          @click="testConnection" 
          :loading="testing"
          size="large"
          plain
        >
          <el-icon><Connection /></el-icon>
          测试连接
        </el-button>
        <el-button 
          @click="saveConfig" 
          type="success" 
          :loading="saving"
          size="large"
        >
          <el-icon><Check /></el-icon>
          保存配置
        </el-button>
        <el-button 
          @click="resetToDefault" 
          size="large"
        >
          <el-icon><RefreshLeft /></el-icon>
          重置
        </el-button>
      </el-form-item>
    </el-form>
    
    <!-- 测试结果 -->
    <el-alert
      v-if="testResult"
      :title="testResult.success ? '连接成功' : '连接失败'"
      :type="testResult.success ? 'success' : 'error'"
      :closable="true"
      @close="testResult = null"
      style="margin-top: 20px"
    >
      <template #default>
        <div>{{ testResult.message }}</div>
        <div v-if="testResult.response" class="test-response">
          响应: {{ testResult.response }}
        </div>
      </template>
    </el-alert>
    
    <!-- 帮助信息 -->
    <el-divider />
    <div class="help-section">
      <h4>如何获取 API Key</h4>
      <div v-if="form.provider === 'deepseek'" class="help-content">
        <p>1. 访问 <el-link href="https://platform.deepseek.com" target="_blank" type="primary">DeepSeek 开放平台</el-link></p>
        <p>2. 注册/登录账号</p>
        <p>3. 进入「API Keys」页面创建密钥</p>
        <p>4. 复制密钥并粘贴到上方输入框</p>
      </div>
      <div v-else-if="form.provider === 'openai'" class="help-content">
        <p>1. 访问 <el-link href="https://platform.openai.com" target="_blank" type="primary">OpenAI 平台</el-link></p>
        <p>2. 进入「API Keys」页面</p>
        <p>3. 点击「Create new secret key」</p>
      </div>
      <div v-else-if="form.provider === 'siliconflow'" class="help-content">
        <p>1. 访问 <el-link href="https://cloud.siliconflow.cn" target="_blank" type="primary">SiliconFlow 云平台</el-link></p>
        <p>2. 注册/登录账号</p>
        <p>3. 进入「API 密钥」页面创建密钥</p>
      </div>
      <div v-else class="help-content">
        <p>请输入兼容 OpenAI API 格式的自定义端点地址</p>
      </div>
    </div>
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
const testResult = ref<{ success: boolean; message: string; response?: string } | null>(null)
const activeCollapse = ref<string[]>([])

// 默认配置 - DeepSeek
const defaultConfig = {
  provider: 'deepseek' as const,
  model: 'deepseek-chat',
  apiKey: '',
  baseUrl: '',
  temperature: 0.7,
  maxTokens: 4096
}

const form = ref({ ...defaultConfig })

const currentProvider = computed(() => {
  return providers.value.find(p => p.id === form.value.provider)
})

const isConfigured = computed(() => {
  return !!form.value.apiKey && !!form.value.model
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
    
    // 使用后端默认配置初始化
    if (res.data.provider) {
      form.value.provider = res.data.provider
      form.value.model = res.data.model
    }

    // 优先加载已保存到服务端的用户配置（真正会被后端 AI 调用使用）
    try {
      const userRes = await systemApi.getUserAIConfig()
      const userCfg = userRes.data
      if (userCfg?.provider) {
        form.value.provider = userCfg.provider
        form.value.model = userCfg.model || form.value.model
        form.value.baseUrl = userCfg.base_url || ''
        form.value.temperature = userCfg.temperature ?? form.value.temperature
        form.value.maxTokens = userCfg.max_tokens ?? form.value.maxTokens
        // 脱敏 key 仅作占位提示；真正完整 key 优先从本地读取
        if (userCfg.api_key && !form.value.apiKey) {
          form.value.apiKey = userCfg.api_key
        }
        config.value = {
          ...config.value!,
          provider: userCfg.provider,
          model: userCfg.model || config.value?.model || ''
        }
      }
    } catch (e) {
      console.log('尚未保存用户 AI 配置，将使用环境变量回退')
    }

    // 本地完整 API Key 覆盖脱敏占位
    loadFromLocalStorage()
  } catch (e) {
    console.error('加载配置失败:', e)
    // 使用默认 DeepSeek 配置
    form.value.provider = 'deepseek'
    form.value.model = 'deepseek-chat'
    loadFromLocalStorage()
  } finally {
    loading.value = false
  }
}

function loadFromLocalStorage() {
  try {
    const saved = localStorage.getItem('joe-ai-config')
    if (saved) {
      const parsed = JSON.parse(saved)
      // 本地有完整 key 时覆盖脱敏值
      if (parsed.apiKey && !String(parsed.apiKey).endsWith('...')) {
        form.value = { ...form.value, ...parsed }
      } else {
        const { apiKey: _ignored, ...rest } = parsed
        form.value = { ...form.value, ...rest }
      }
    }
  } catch (e) {
    console.error('加载本地配置失败:', e)
  }
}

function onProviderChange() {
  // 切换提供商时，自动选择推荐模型
  const provider = currentProvider.value
  if (provider?.models.length) {
    // 优先选择推荐的模型
    const recommendedModel = provider.models.find(m => 
      (provider.id === 'deepseek' && m === 'deepseek-chat') ||
      (provider.id === 'openai' && m === 'gpt-4') ||
      (provider.id === 'siliconflow' && m.includes('DeepSeek-V3'))
    )
    form.value.model = recommendedModel || provider.models[0]
  }
  
  // 重置 API Key
  form.value.apiKey = ''
  form.value.baseUrl = ''
  
  // 清除测试结果
  testResult.value = null
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
    
    if (res.data.success) {
      ElMessage.success('连接测试成功！')
    } else {
      ElMessage.error('连接测试失败')
    }
  } catch (e) {
    testResult.value = {
      success: false,
      message: '请求失败，请检查网络连接'
    }
    ElMessage.error('测试请求失败')
  } finally {
    testing.value = false
  }
}

async function saveConfig() {
  if (!form.value.apiKey) {
    ElMessage.warning('请输入 API Key 后再保存')
    return
  }
  if (String(form.value.apiKey).endsWith('...')) {
    ElMessage.warning('请重新输入完整的 API Key 后再保存')
    return
  }
  
  saving.value = true
  try {
    // 1. 必须先保存到后端（AI 调用实际读取服务端配置）
    await systemApi.saveUserAIConfig({
      provider: form.value.provider,
      model: form.value.model,
      api_key: form.value.apiKey,
      base_url: form.value.baseUrl || undefined,
      temperature: form.value.temperature,
      max_tokens: form.value.maxTokens
    })

    // 2. 同步本地缓存（方便下次打开表单回填完整 key）
    localStorage.setItem('joe-ai-config', JSON.stringify({
      provider: form.value.provider,
      model: form.value.model,
      apiKey: form.value.apiKey,
      baseUrl: form.value.baseUrl,
      temperature: form.value.temperature,
      maxTokens: form.value.maxTokens
    }))
    
    ElMessage.success('配置已保存，将优先使用你的 API Key')
    
    // 更新状态显示
    config.value = {
      ...config.value!,
      provider: form.value.provider,
      model: form.value.model
    }
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || '保存失败'
    ElMessage.error(typeof msg === 'string' ? msg : '保存失败，请确认已登录')
  } finally {
    saving.value = false
  }
}

async function resetToDefault() {
  form.value = { ...defaultConfig }
  localStorage.removeItem('joe-ai-config')
  try {
    await systemApi.deleteUserAIConfig()
    ElMessage.success('已清除用户配置，将使用服务器环境变量')
  } catch {
    ElMessage.success('已重置本地配置（服务端清除失败，可能未登录）')
  }
  testResult.value = null
}
</script>

<style scoped>
.ai-config-panel {
  padding: 0 20px;
  max-width: 800px;
  margin: 0 auto;
}

.ai-config-panel h3 {
  margin: 0 0 20px 0;
  font-size: 20px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-card {
  margin-bottom: 24px;
  transition: all 0.3s;
}

.status-card.is-active {
  border-color: #67c23a;
  background: #f0f9ff;
}

.status-header {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-info {
  flex: 1;
}

.status-title {
  font-size: 16px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.status-model {
  font-size: 14px;
  color: #606266;
}

/* Provider colors */
:deep(.provider-deepseek) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-weight: bold;
}

:deep(.provider-openai) {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  color: white;
  font-weight: bold;
}

:deep(.provider-siliconflow) {
  background: linear-gradient(135deg, #fc4a1a 0%, #f7b733 100%);
  color: white;
  font-weight: bold;
}

:deep(.provider-custom) {
  background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
  color: white;
  font-weight: bold;
}

:deep(.provider-default) {
  background: #909399;
  color: white;
}

.config-form {
  margin-top: 20px;
}

.form-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.action-buttons {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #e4e7ed;
}

.test-response {
  margin-top: 8px;
  padding: 8px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 13px;
  color: #606266;
}

.help-section {
  margin-top: 20px;
}

.help-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #606266;
}

.help-content {
  font-size: 13px;
  color: #606266;
  line-height: 1.8;
}

.help-content p {
  margin: 4px 0;
}
</style>
