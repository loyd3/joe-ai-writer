import axios from 'axios'

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

// 响应拦截器 - 处理认证错误
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ========== 认证 API ==========
export const authApi = {
  register: (data: { username: string; email: string; password: string }) =>
    api.post('/auth/register', data),
  
  login: (username: string, password: string) => {
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)
    return axios.post(`${API_BASE_URL}/api/auth/login`, formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
  },
  
  logout: () => api.post('/auth/logout'),
  
  getMe: () => api.get('/auth/me'),
  
  getProfile: () => api.get('/auth/profile'),

  getTheme: () => api.get('/auth/theme'),
  updateTheme: (data: { preset_id?: string; custom_color?: string }) =>
    api.put('/auth/theme', data)
}

// ========== 项目 API ==========
export const projectApi = {
  list: () => api.get('/projects'),
  get: (id: number) => api.get(`/projects/${id}`),
  create: (data: any) => api.post('/projects', data),
  update: (id: number, data: any) => api.put(`/projects/${id}`, data),
  delete: (id: number) => api.delete(`/projects/${id}`)
}

// ========== 文档 API ==========
export const documentApi = {
  list: (projectId: number) => api.get(`/projects/${projectId}/documents`),
  get: (id: number) => api.get(`/documents/${id}`),
  create: (projectId: number, data: any) => api.post(`/projects/${projectId}/documents`, data),
  update: (id: number, data: any) => api.put(`/documents/${id}`, data),
  delete: (id: number) => api.delete(`/documents/${id}`),
  reorder: (projectId: number, documentIds: number[]) => 
    api.post(`/projects/${projectId}/documents/reorder`, documentIds)
}

// ========== 项目设定 API ==========
export const memoryApi = {
  get: (projectId: number) => api.get(`/projects/${projectId}/memory`),
  update: (projectId: number, data: any) => api.put(`/projects/${projectId}/memory`, data)
}

// ========== AI 写作 API ==========
export const aiApi = {
  assist: (data: any) => api.post('/ai/assist', data),
  assistStream: (data: any) => {
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
  chatStream: (data: any) => {
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
  generateFromMemoryStream: (data: {
    project_id: number
    document_id?: number
    generate_type: 'opening' | 'continue' | 'outline_section' | 'scene' | 'custom'
    custom_instruction?: string
    current_content?: string
  }) => {
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
  aiConfig: () => api.get('/system/ai-config'),
  testAI: (data: { provider: string; model?: string; api_key?: string; base_url?: string; temperature?: number }) =>
    api.post('/system/ai-config/test', data),
  saveUserAIConfig: (data: {
    provider: string
    model?: string
    api_key?: string
    base_url?: string
    temperature?: number
    max_tokens?: number
  }) => api.post('/system/user-ai-config', data),
}

export default api
export { API_BASE_URL }
