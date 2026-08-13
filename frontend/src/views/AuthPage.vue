<template>
  <div class="auth-page">
    <div class="auth-container">
      <div class="auth-brand">
        <div class="logo">
          <el-icon><EditPen /></el-icon>
        </div>
        <h1>墨心</h1>
        <p class="tagline">AI 辅助写作 - 用文字书写灵魂</p>
      </div>

      <div class="auth-card">
        <h2>{{ isLogin ? '欢迎回来' : '创建账号' }}</h2>
        <p class="subtitle">{{ isLogin ? '登录以继续您的创作之旅' : '开始您的写作旅程' }}</p>

        <el-form 
          ref="formRef"
          :model="form" 
          :rules="rules"
          class="auth-form"
          @keyup.enter="handleSubmit"
        >
          <el-form-item prop="username">
            <el-input 
              v-model="form.username" 
              placeholder="用户名"
              size="large"
              :prefix-icon="User"
            />
          </el-form-item>

          <el-form-item v-if="!isLogin" prop="email">
            <el-input 
              v-model="form.email" 
              placeholder="邮箱"
              size="large"
              :prefix-icon="Message"
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input 
              v-model="form.password" 
              type="password" 
              placeholder="密码"
              size="large"
              :prefix-icon="Lock"
              show-password
            />
          </el-form-item>

          <el-form-item v-if="!isLogin" prop="confirmPassword">
            <el-input 
              v-model="form.confirmPassword" 
              type="password" 
              placeholder="确认密码"
              size="large"
              :prefix-icon="Lock"
              show-password
            />
          </el-form-item>

          <el-button 
            type="primary" 
            size="large" 
            class="btn btn-primary btn-lg btn-block auth-submit"
            :loading="authStore.loading"
            @click="handleSubmit"
          >
            {{ isLogin ? '登录' : '注册' }}
          </el-button>
        </el-form>

        <div class="auth-footer">
          <p>
            {{ isLogin ? '还没有账号？' : '已有账号？' }}
            <el-button link type="primary" @click="toggleMode">
              {{ isLogin ? '立即注册' : '立即登录' }}
            </el-button>
          </p>
        </div>
      </div>

      <div class="auth-quote">
        <p>"写作是一种灵魂的独白，每一行字都是心灵的印记。"</p>
        <span class="author">— 墨心</span>
      </div>
    </div>

    <!-- 装饰元素 -->
    <div class="decoration coffee-bean bean-1"></div>
    <div class="decoration coffee-bean bean-2"></div>
    <div class="decoration coffee-bean bean-3"></div>
    <div class="decoration feather"></div>
    <div class="decoration paper"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import { User, Lock, Message, EditPen } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()

const isLogin = ref(true)

const form = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const validateConfirmPassword = (rule: any, value: string, callback: any) => {
  if (!isLogin.value && value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = reactive<FormRules>({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '长度在 3 到 20 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
})

function toggleMode() {
  isLogin.value = !isLogin.value
  formRef.value?.resetFields()
}

async function handleSubmit() {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      if (isLogin.value) {
        const success = await authStore.login(form.username, form.password)
        if (success) {
          router.push('/')
        }
      } else {
        const success = await authStore.register(form.username, form.email, form.password)
        if (success) {
          isLogin.value = true
          form.password = ''
          form.confirmPassword = ''
        }
      }
    }
  })
}
</script>

<style scoped lang="scss">
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--coffee-bg) 0%, var(--coffee-bg-warm) 50%, var(--coffee-divider) 100%);
  position: relative;
  overflow: hidden;
}

.auth-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 40px;
  z-index: 10;
  padding: 40px 20px;
}

.auth-brand {
  text-align: center;
  
  .logo {
    width: 80px;
    height: 80px;
    background: var(--coffee-gradient-primary);
    border-radius: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 10px;
    box-shadow: 0 10px 40px rgba(var(--coffee-primary-rgb), 0.3);
    
    .el-icon {
      font-size: 40px;
      color: #fff;
    }
  }
  
  h1 {
    font-size: 32px;
    font-weight: 700;
    color: var(--coffee-text);
    margin-bottom: 8px;
    letter-spacing: 2px;
  }
  
  .tagline {
    font-size: 16px;
    color: #a67c52;
    font-style: italic;
  }
}

.auth-card {
  background: var(--coffee-bg-card);
  backdrop-filter: blur(10px);
  border-radius: 24px;
  padding: 40px;
  width: 100%;
  max-width: 400px;
  box-shadow: 
    0 20px 60px var(--coffee-shadow-hover),
    0 0 0 1px rgba(var(--coffee-primary-rgb), 0.05);
  
  h2 {
    font-size: 24px;
    font-weight: 600;
    color: var(--coffee-text);
    margin-bottom: 8px;
    text-align: center;
  }
  
  .subtitle {
    font-size: 14px;
    color: #a67c52;
    text-align: center;
    margin-bottom: 30px;
  }
}

.auth-form {
  .el-input {
    --el-input-border-radius: 12px;
    --el-input-bg-color: var(--coffee-bg);
    --el-input-border-color: var(--coffee-border);
    --el-input-hover-border-color: var(--coffee-primary-light);
    --el-input-focus-border-color: var(--coffee-primary-light);
    
    :deep(.el-input__wrapper) {
      box-shadow: 0 2px 8px var(--coffee-sidebar-shadow);
      padding: 4px 16px;
    }
    
    :deep(.el-input__inner) {
      height: 44px;
    }
  }

  .auth-submit {
    margin-top: 10px;
  }
}

.auth-footer {
  text-align: center;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--coffee-border-light);
  
  p {
    color: #a67c52;
    font-size: 14px;
  }
  
  .el-button {
    font-weight: 500;
    color: var(--coffee-primary);
  }
}

.auth-quote {
  text-align: center;
  max-width: 400px;
  
  p {
    font-size: 15px;
    color: #a67c52;
    font-style: italic;
    line-height: 1.8;
    margin-bottom: 8px;
  }
  
  .author {
    font-size: 13px;
    color: #c9a86c;
  }
}

/* 装饰元素 */
.decoration {
  position: absolute;
  pointer-events: none;
}

.coffee-bean {
  width: 40px;
  height: 60px;
  background: linear-gradient(135deg, var(--coffee-primary-dark) 0%, var(--coffee-primary) 100%);
  border-radius: 50% 50% 50% 50% / 60% 60% 40% 40%;
  opacity: 0.1;
  
  &.bean-1 {
    top: 10%;
    left: 10%;
    transform: rotate(-30deg);
  }
  
  &.bean-2 {
    top: 20%;
    right: 15%;
    transform: rotate(45deg);
    width: 30px;
    height: 45px;
  }
  
  &.bean-3 {
    bottom: 15%;
    left: 20%;
    transform: rotate(15deg);
    width: 25px;
    height: 38px;
  }
}

.feather {
  bottom: 20%;
  right: 10%;
  width: 80px;
  height: 120px;
  background: linear-gradient(135deg, #d4c4a8 0%, #c4b49a 100%);
  border-radius: 0 100% 0 100%;
  opacity: 0.08;
  transform: rotate(-20deg);
}

.paper {
  top: 15%;
  right: 8%;
  width: 100px;
  height: 140px;
  background: #f5ebe0;
  border-radius: 4px;
  opacity: 0.15;
  transform: rotate(5deg);
  box-shadow: 0 4px 20px rgba(0,0,0,0.1);
}

@media (max-width: 768px) {
  .auth-card {
    padding: 30px 24px;
    margin: 0 16px;
  }
  
  .auth-brand h1 {
    font-size: 28px;
  }
}
</style>
