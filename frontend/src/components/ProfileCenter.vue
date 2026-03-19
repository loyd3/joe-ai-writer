<template>
  <div class="profile-center">
    <h3>
      <el-icon><User /></el-icon>
      个人中心
    </h3>

    <div class="profile-form" v-loading="loading">
      <!-- 头像 -->
      <div class="avatar-section">
        <div class="avatar-preview">
          <el-avatar :size="80" :src="avatarDisplayUrl">
            {{ profile?.username?.charAt(0) || '?' }}
          </el-avatar>
        </div>
        <div class="avatar-actions">
          <el-upload
            :show-file-list="false"
            :before-upload="beforeAvatarUpload"
            :http-request="handleAvatarUpload"
            accept="image/jpeg,image/png,image/gif,image/webp"
          >
            <el-button type="primary" size="small" :loading="uploading">
              <el-icon><Upload /></el-icon>
              上传头像
            </el-button>
          </el-upload>
          <span class="avatar-hint">支持 JPG、PNG、GIF、WebP，不超过 2MB</span>
        </div>
      </div>

      <!-- 用户名、邮箱 -->
      <el-form :model="form" label-width="80px" label-position="top" class="profile-fields">
        <el-form-item label="用户名">
          <el-input
            v-model="form.username"
            placeholder="3-50 个字符"
            maxlength="50"
            show-word-limit
            clearable
          />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input
            v-model="form.email"
            type="email"
            placeholder="用于登录与找回"
            clearable
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveProfile" :loading="saving">
            保存资料
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 修改密码 -->
      <el-divider />
      <h4>修改密码</h4>
      <el-form :model="passwordForm" label-width="100px" label-position="top" class="password-form">
        <el-form-item label="当前密码">
          <el-input
            v-model="passwordForm.old_password"
            type="password"
            placeholder="请输入当前密码"
            show-password
            clearable
          />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input
            v-model="passwordForm.new_password"
            type="password"
            placeholder="6-100 位"
            show-password
            clearable
          />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input
            v-model="passwordForm.confirm_password"
            type="password"
            placeholder="再次输入新密码"
            show-password
            clearable
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="savePassword" :loading="changingPassword">
            修改密码
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import { User, Upload } from '@element-plus/icons-vue'
import { API_BASE_URL } from '@/api'

const authStore = useAuthStore()
const loading = ref(false)
const saving = ref(false)
const uploading = ref(false)
const changingPassword = ref(false)

// 支持环境变量覆盖 API_BASE_URL
const BASE_URL = import.meta.env.VITE_API_URL || API_BASE_URL

const profile = ref<{
  id: number
  username: string
  email: string
  avatar_url?: string
  project_count?: number
  created_at?: string
} | null>(null)

const form = ref({ username: '', email: '' })
const passwordForm = ref({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const avatarDisplayUrl = computed(() => {
  if (!profile.value?.avatar_url) return ''
  const base = BASE_URL.replace(/\/api\/?$/, '')
  return base + profile.value.avatar_url
})

async function loadProfile() {
  loading.value = true
  try {
    const data = await authStore.fetchProfile()
    profile.value = data || null
    if (data) {
      form.value.username = data.username
      form.value.email = data.email
    }
  } finally {
    loading.value = false
  }
}

function beforeAvatarUpload(file: File) {
  const isImage = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'].includes(file.type)
  const isLt2M = file.size / 1024 / 1024 < 2
  if (!isImage) {
    ElMessage.warning('请上传 JPG、PNG、GIF 或 WebP 图片')
    return false
  }
  if (!isLt2M) {
    ElMessage.warning('头像大小不能超过 2MB')
    return false
  }
  return true
}

async function handleAvatarUpload(options: { file: File }) {
  uploading.value = true
  try {
    const ok = await authStore.uploadAvatar(options.file)
    if (ok && authStore.user) {
      profile.value = {
        ...profile.value!,
        avatar_url: authStore.user.avatar_url,
        username: authStore.user.username,
        email: authStore.user.email
      }
    }
  } finally {
    uploading.value = false
  }
}

async function saveProfile() {
  if (!form.value.username.trim()) return
  saving.value = true
  try {
    const ok = await authStore.updateProfile({
      username: form.value.username.trim(),
      email: form.value.email.trim() || undefined
    })
    if (ok && authStore.user) profile.value = { ...profile.value!, ...authStore.user }
  } finally {
    saving.value = false
  }
}

async function savePassword() {
  const { old_password, new_password, confirm_password } = passwordForm.value
  if (!old_password || !new_password) {
    ElMessage.warning('请填写当前密码和新密码')
    return
  }
  if (new_password !== confirm_password) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  changingPassword.value = true
  try {
    const ok = await authStore.changePassword(old_password, new_password)
    if (ok) {
      passwordForm.value = { old_password: '', new_password: '', confirm_password: '' }
    }
  } finally {
    changingPassword.value = false
  }
}

onMounted(() => {
  loadProfile()
})
</script>

<style scoped lang="scss">
.profile-center {
  padding: 20px;

  h3 {
    margin: 0 0 24px;
    font-size: 18px;
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--coffee-text);

    .el-icon {
      color: var(--coffee-primary);
    }
  }

  h4 {
    margin: 0 0 16px;
    font-size: 14px;
    color: var(--coffee-text-secondary);
  }
}

.avatar-section {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 28px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.avatar-preview {
  flex-shrink: 0;
}

.avatar-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;

  .avatar-hint {
    font-size: 12px;
    color: var(--coffee-text-light);
  }
}

.profile-fields,
.password-form {
  max-width: 400px;
}
</style>
