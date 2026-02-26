import axios from 'axios'
import type {
  User, UserCreate, UserProfile, ProfileUpdate, PasswordChange,
  Project, ProjectCreate, ProjectUpdate,
  Document, DocumentCreate, DocumentUpdate,
  AIMemory, AIMemoryUpdate,
  AIRequest, AIChatRequest, AIGenerateRequest,
  Template, TemplateCreate,
  AIConfig, Theme
} from './types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器 - 添加 token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器 - 统一错误处理
import { ElMessage } from 'element-plus'

api.interceptors.response.use(
  (response) => response,
  (error) => {
    // 网络错误
    if (!error.response) {
      ElMessage.error('网络连接失败，请检查网络')
      return Promise.reject(error)
    }

    const { status, data } = error.response

    // 认证错误
    if (status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
      return Promise.reject(error)
    }

    // 权限错误
    if (status === 403) {
      ElMessage.error('没有权限执行此操作')
      return Promise.reject(error)
    }

    // 限流错误
    if (status === 429) {
      ElMessage.warning('请求过于频繁，请稍后再试')
      return Promise.reject(error)
    }

    // 服务器错误
    if (status >= 500) {
      ElMessage.error('服务器繁忙，请稍后重试')
      return Promise.reject(error)
    }

    // 业务错误，显示后端返回的消息
    const message = data?.detail || data?.message || '操作失败'
    ElMessage.error(message)

    return Promise.reject(error)
  }
)

// ========== 认证 API ==========
export const authApi = {
  register: (data: UserCreate) =>
    api.post<User>('/auth/register', data),

  login: (username: string, password: string) => {
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)
    return axios.post<{ access_token: string; token_type: string }>(
      `${API_BASE_URL}/api/auth/login`,
      formData,
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    )
  },

  logout: () => api.post('/auth/logout'),

  getMe: () => api.get<User>('/auth/me'),

  getProfile: () => api.get<UserProfile>('/auth/profile'),
  updateProfile: (data: ProfileUpdate) =>
    api.put<UserProfile>('/auth/profile', data),
  changePassword: (data: PasswordChange) =>
    api.put('/auth/password', data),
  uploadAvatar: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.put<UserProfile>('/auth/avatar', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  getTheme: () => api.get<Theme>('/auth/theme'),
  updateTheme: (data: Theme) =>
    api.put<Theme>('/auth/theme', data)
}

// ========== 项目 API ==========
export const projectApi = {
  list: () => api.get<Project[]>('/projects'),
  get: (id: number) => api.get<Project>(`/projects/${id}`),
  create: (data: ProjectCreate) => api.post<Project>('/projects', data),
  update: (id: number, data: ProjectUpdate) => api.put<Project>(`/projects/${id}`, data),
  delete: (id: number) => api.delete(`/projects/${id}`)
}

// ========== 文档 API ==========
export const documentApi = {
  list: (projectId: number) => api.get<Document[]>(`/projects/${projectId}/documents`),
  get: (id: number) => api.get<Document>(`/documents/${id}`),
  create: (projectId: number, data: DocumentCreate) => api.post<Document>(`/projects/${projectId}/documents`, data),
  update: (id: number, data: DocumentUpdate) => api.put<Document>(`/documents/${id}`, data),
  delete: (id: number) => api.delete(`/documents/${id}`),
  reorder: (projectId: number, documentIds: number[]) =>
    api.post<Document[]>(`/projects/${projectId}/documents/reorder`, documentIds)
}

// ========== 项目设定 API ==========
export const memoryApi = {
  get: (projectId: number) => api.get<AIMemory>(`/projects/${projectId}/memory`),
  update: (projectId: number, data: AIMemoryUpdate) => api.put<AIMemory>(`/projects/${projectId}/memory`, data)
}

// ========== AI 写作 API ==========
export const aiApi = {
  assist: (data: AIRequest) => api.post<{ response: string }>('/ai/assist', data),
  assistStream: (data: AIRequest) => {
    const token = localStorage.getItem('token')
    return fetch(`${API_BASE_URL}/api/ai/assist/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(data)
    })
  },
  chatStream: (data: AIChatRequest) => {
    const token = localStorage.getItem('token')
    return fetch(`${API_BASE_URL}/api/ai/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(data)
    })
  },
  /** 根据项目设定生成内容（流式） */
  generateFromMemoryStream: (data: AIGenerateRequest) => {
    const token = localStorage.getItem('token')
    return fetch(`${API_BASE_URL}/api/ai/generate-from-memory/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(data)
    })
  }
}

// ========== 系统 / AI 配置 API ==========
export const systemApi = {
  aiConfig: () => api.get<AIConfig>('/system/ai-config'),
  testAI: (data: AIConfig) =>
    api.post<{ success: boolean; message?: string }>('/system/ai-config/test', data),
  saveUserAIConfig: (data: AIConfig) =>
    api.post('/system/user-ai-config', data),
}

export default api
export { API_BASE_URL }
export * from './types'
