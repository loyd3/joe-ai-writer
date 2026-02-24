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

// 事件设定 API
export const eventApi = {
  list: (projectId: number) => api.get(`/projects/${projectId}/events`),
  get: (projectId: number, eventId: number) => api.get(`/projects/${projectId}/events/${eventId}`),
  create: (projectId: number, data: any) => api.post(`/projects/${projectId}/events`, data),
  update: (projectId: number, eventId: number, data: any) => api.put(`/projects/${projectId}/events/${eventId}`, data),
  delete: (projectId: number, eventId: number) => api.delete(`/projects/${projectId}/events/${eventId}`),
  reorder: (projectId: number, eventId: number, newIndex: number) => 
    api.post(`/projects/${projectId}/events/${eventId}/reorder`, null, { params: { new_index: newIndex } })
}

// 系统 API
export const systemApi = {
  health: () => api.get('/system/health'),
  aiConfig: () => api.get('/system/ai-config'),
  providers: () => api.get('/system/ai-config/providers'),
  testAI: (data: any) => api.post('/system/ai-config/test', data)
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