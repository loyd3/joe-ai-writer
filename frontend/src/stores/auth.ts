import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api'
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

      if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
        msg = '连接超时：后端服务未响应，请检查服务是否已启动'
      } else if (error.code === 'ERR_NETWORK' || error.message?.includes('Network Error')) {
        msg = '无法连接到服务器，请检查：\n1. 后端服务是否已启动 (python start.py)\n2. 网络连接是否正常'
      } else if (error.response?.data?.detail) {
        msg = error.response.data.detail
      }

      ElMessage.error(msg)
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
