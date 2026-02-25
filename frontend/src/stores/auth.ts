import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api'
import { ElMessage } from 'element-plus'

export interface User {
  id: number
  username: string
  email: string
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
      
      ElMessage.success('登录成功')
      return true
    } catch (error: any) {
      const msg = error.response?.data?.detail || '登录失败'
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
    fetchProfile
  }
})
