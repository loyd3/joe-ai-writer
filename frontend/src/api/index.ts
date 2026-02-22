import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json'
  }
})

// 项目 API
export const projectApi = {
  list: () => api.get('/projects'),
  get: (id: number) => api.get(`/projects/${id}`),
  create: (data: any) => api.post('/projects', data),
  update: (id: number, data: any) => api.put(`/projects/${id}`, data),
  delete: (id: number) => api.delete(`/projects/${id}`)
}

// 文档 API
export const documentApi = {
  list: (projectId: number) => api.get(`/projects/${projectId}/documents`),
  get: (id: number) => api.get(`/documents/${id}`),
  create: (projectId: number, data: any) => api.post(`/projects/${projectId}/documents`, data),
  update: (id: number, data: any) => api.put(`/documents/${id}`, data),
  delete: (id: number) => api.delete(`/documents/${id}`)
}

// AI 记忆 API
export const memoryApi = {
  get: (projectId: number) => api.get(`/projects/${projectId}/memory`),
  update: (projectId: number, data: any) => api.put(`/projects/${projectId}/memory`, data)
}

// AI 写作 API
export const aiApi = {
  assist: (data: any) => api.post('/ai/assist', data),
  assistStream: (data: any) => {
    return fetch('/api/ai/assist/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  },
  chatStream: (data: any) => {
    return fetch('/api/ai/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
  }
}

export default api