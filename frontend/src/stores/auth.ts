import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, checkBackendHealth } from '@/api'
import { ElMessage } from 'element-plus'
import { useThemeStore } from '@/stores/theme'

export interface User {
  id: number
  username: string
  email: string
  avatar_url?: string
}

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem('token'))
  const loading = ref(false)
  const initialized = ref(false)

  // Getters
  const isLoggedIn = computed(() => !!token.value && !!user.value)
  const currentUser = computed(() => user.value)

  // Actions
  async function init() {
    if (initialized.value) return
    
    const savedToken = localStorage.getItem('token')
    const savedUser = localStorage.getItem('user')
    
    if (savedToken && savedUser) {
      token.value = savedToken
      try {
        const res = await authApi.getMe()
        user.value = res.data
        useThemeStore().loadFromServer()
      } catch {
        // Token 无效，清除本地存储
        logout()
      }
    }
    initialized.value = true
  }

  async function login(username: string, password: string) {
    loading.value = true

    // 首先检查后端健康状态
    const health = await checkBackendHealth()
    if (!health.ok) {
      ElMessage.error({
        message: `${health.message}\n请运行: python start.py`,
        duration: 5000
      })
      loading.value = false
      return false
    }

    try {
      const res = await authApi.login(username, password)
      const { access_token } = res.data

      token.value = access_token
      localStorage.setItem('token', access_token)

      // 获取用户信息
      const userRes = await authApi.getMe()
      user.value = userRes.data
      localStorage.setItem('user', JSON.stringify(userRes.data))
      useThemeStore().loadFromServer()
      ElMessage.success('登录成功')
      return true
    } catch (error: any) {
      // 处理超时和连接错误
      let msg = '登录失败'
      const errMsg = error.message?.toLowerCase() || ''
      const errCode = error.code?.toUpperCase() || ''

      if (errCode.includes('CONNECTION_TIMED_OUT') || errMsg.includes('timed out')) {
        msg = '连接超时 (ERR_CONNECTION_TIMED_OUT)：后端服务无响应\n请确保服务已启动: python start.py'
      } else if (errCode.includes('CONNECTION_REFUSED') || errMsg.includes('refused')) {
        msg = '连接被拒绝 (ERR_CONNECTION_REFUSED)：后端服务未启动\n请运行: python start.py'
      } else if (error.code === 'ECONNABORTED') {
        msg = '请求超时：后端服务响应时间过长'
      } else if (error.code === 'ETIMEDOUT') {
        msg = '连接超时：无法连接到后端服务'
      } else if (error.code === 'ERR_NETWORK' || errMsg.includes('network error')) {
        msg = '网络错误：无法连接到后端服务'
      } else if (error.response?.data?.detail) {
        msg = error.response.data.detail
      }

      ElMessage.error({
        message: msg,
        duration: 5000,
        showClose: true
      })
      return false
    } finally {
      loading.value = false
    }
  }

  async function register(username: string, email: string, password: string) {
    loading.value = true
    try {
      await authApi.register({ username, email, password })
      ElMessage.success('注册成功，请登录')
      return true
    } catch (error: any) {
      const msg = error.response?.data?.detail || '注册失败'
      ElMessage.error(msg)
      return false
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    try {
      await authApi.logout()
    } catch {
      // 忽略错误
    }
    
    user.value = null
    token.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    ElMessage.success('已退出登录')
  }

  async function fetchProfile() {
    try {
      const res = await authApi.getProfile()
      return res.data
    } catch (error: any) {
      ElMessage.error('获取用户信息失败')
      return null
    }
  }

  function setUser(profile: { id: number; username: string; email: string; avatar_url?: string }) {
    user.value = { id: profile.id, username: profile.username, email: profile.email, avatar_url: profile.avatar_url }
    localStorage.setItem('user', JSON.stringify(user.value))
  }

  async function updateProfile(data: { username?: string; email?: string; avatar_url?: string }) {
    try {
      const res = await authApi.updateProfile(data)
      setUser(res.data)
      ElMessage.success('资料已更新')
      return true
    } catch (error: any) {
      const msg = error.response?.data?.detail || '更新失败'
      ElMessage.error(msg)
      return false
    }
  }

  async function changePassword(oldPassword: string, newPassword: string) {
    try {
      await authApi.changePassword({ old_password: oldPassword, new_password: newPassword })
      ElMessage.success('密码已修改')
      return true
    } catch (error: any) {
      const msg = error.response?.data?.detail || '修改失败'
      ElMessage.error(msg)
      return false
    }
  }

  async function uploadAvatar(file: File) {
    try {
      const res = await authApi.uploadAvatar(file)
      setUser(res.data)
      ElMessage.success('头像已更新')
      return true
    } catch (error: any) {
      const msg = error.response?.data?.detail || '上传失败'
      ElMessage.error(msg)
      return false
    }
  }

  return {
    user,
    token,
    loading,
    initialized,
    isLoggedIn,
    currentUser,
    init,
    login,
    register,
    logout,
    fetchProfile,
    updateProfile,
    changePassword,
    uploadAvatar,
    setUser
  }
})
