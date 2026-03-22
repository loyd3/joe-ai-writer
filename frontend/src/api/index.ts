import axios, { AxiosError, AxiosRequestConfig } from 'axios'
import type {
  User, UserCreate, UserProfile, ProfileUpdate, PasswordChange,
  Project, ProjectCreate, ProjectUpdate,
  Document, DocumentCreate, DocumentUpdate, Block,
  AIMemory, AIMemoryUpdate,
  AIRequest, AIAssistResponse, AIChatRequest, AIGenerateRequest, AIBatchGenerateRequest,
  LiteraryAnalysisRequest, LiteraryAnalysisResult, CreateProjectFromLiteratureRequest,
  Template, TemplateCreate,
  AIConfig, Theme
} from './types'

// API 基础 URL 配置
// 优先使用环境变量 VITE_API_URL，否则根据运行环境自动判断
// - 本地开发（vite）：使用 http://localhost:8000
// - Docker 环境：使用 http://localhost:9000
const API_BASE_URL = import.meta.env.VITE_API_URL || 
  (import.meta.env.DEV ? 'http://localhost:8000' : 'http://localhost:9000')

// 请求配置常量
const REQUEST_TIMEOUT = 10000 // 10秒超时
const MAX_RETRIES = 3
const RETRY_DELAY = 1000 // 1秒

const api = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  headers: {
    'Content-Type': 'application/json'
  },
  timeout: REQUEST_TIMEOUT
})

// 重试请求的工具函数 - 支持指数退避
async function retryRequest<T>(
  requestFn: () => Promise<T>,
  maxRetries: number = MAX_RETRIES,
  baseDelay: number = RETRY_DELAY
): Promise<T> {
  let lastError: Error | undefined

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await requestFn()
    } catch (error) {
      lastError = error as Error
      const axiosError = error as AxiosError

      // 如果是 4xx 错误（客户端错误），不重试
      if (axiosError.response?.status && axiosError.response.status >= 400 && axiosError.response.status < 500) {
        throw error
      }

      // 检查是否是可重试的网络错误（含浏览器 ERR_CONNECTION_TIMED_OUT）
      const code = axiosError.code ?? ''
      const msg = axiosError.message ?? ''
      const isRetryableError =
        code === 'ECONNABORTED' ||           // 请求超时
        code === 'ERR_NETWORK' ||            // 网络错误
        code === 'ETIMEDOUT' ||              // 连接超时
        code === 'ERR_CONNECTION_TIMED_OUT' || // 浏览器：连接超时
        code === 'ERR_CONNECTION_REFUSED' ||   // 连接被拒绝
        msg.includes('timeout') ||
        msg.includes('Network Error') ||
        msg.includes('ERR_CONNECTION_TIMED_OUT') ||
        !axiosError.response                  // 无响应（服务器未启动）

      // 如果是连接错误且不是最后一次尝试，等待后重试
      if (isRetryableError && attempt < maxRetries) {
        // 指数退避：1s, 2s, 4s...
        const delay = baseDelay * Math.pow(2, attempt - 1)
        console.log(`[API] 连接失败，${delay}ms 后重试 (${attempt}/${maxRetries})...`)
        await new Promise(resolve => setTimeout(resolve, delay))
        continue
      }

      // 最后一次尝试或不可重试的错误
      throw error
    }
  }

  throw lastError
}

// 健康检查 - 检查后端是否可用（带重试）
export async function checkBackendHealth(retries = 2): Promise<{ ok: boolean; message: string }> {
  for (let i = 0; i < retries; i++) {
    try {
      const response = await api.get('/health', {
        timeout: 3000
      })
      return { ok: true, message: '后端服务正常' }
    } catch (error: any) {
      // 最后一次失败才返回错误
      if (i === retries - 1) {
        const msg = error.message?.toLowerCase() || ''
        if (msg.includes('timed out') || msg.includes('timeout') || error.code?.includes('TIMEOUT')) {
          return { ok: false, message: '连接超时：后端服务未响应 (ERR_CONNECTION_TIMED_OUT)' }
        }
        if (msg.includes('refused') || error.code?.includes('REFUSED')) {
          return { ok: false, message: '连接被拒绝：后端服务未启动 (ERR_CONNECTION_REFUSED)' }
        }
        if (error.code === 'ERR_NETWORK' || msg.includes('network')) {
          return { ok: false, message: '网络错误：无法连接到后端服务' }
        }
        return { ok: false, message: '无法连接到后端服务，请检查服务是否已启动' }
      }
      // 等待后重试
      await new Promise(r => setTimeout(r, 1000))
    }
  }
  return { ok: false, message: '无法连接到后端服务' }
}

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

// 错误消息映射
const getErrorMessage = (error: AxiosError): string => {
  // 连接超时 (请求发送后超时)
  if (error.code === 'ECONNABORTED') {
    return '请求超时，后端服务响应时间过长'
  }

  // 连接超时 (TCP 连接阶段超时)
  if (error.code === 'ETIMEDOUT') {
    return '连接超时：无法连接到后端服务，请检查服务是否已启动'
  }

  // 连接超时（浏览器常见）
  if (error.code === 'ERR_CONNECTION_TIMED_OUT' || error.message?.includes('ERR_CONNECTION_TIMED_OUT')) {
    return '连接超时：后端服务未响应，请检查是否已启动 (python start.py)'
  }

  // 网络错误（连接被拒绝、服务器未启动等）
  if (error.code === 'ERR_NETWORK' || error.code === 'ERR_CONNECTION_REFUSED' || error.message?.includes('Network Error')) {
    return '无法连接到服务器，请检查后端服务是否已启动 (python start.py)'
  }

  // 超时相关的其他情况
  if (error.message?.includes('timeout')) {
    return '连接超时，请检查后端服务是否已启动'
  }

  // 没有响应（服务器无响应）
  if (!error.response) {
    return '网络连接失败，请检查网络或后端服务状态'
  }

  return ''
}

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const customMessage = getErrorMessage(error)

    // 网络错误或超时
    if (!error.response || customMessage) {
      // 避免重复显示错误（登录接口会单独处理）
      if (!error.config?.url?.includes('/auth/login')) {
        ElMessage.error(customMessage || '网络连接失败，请检查网络')
      }
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

  login: async (username: string, password: string) => {
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)

    // 登录请求使用更长的超时时间（15秒），因为可能需要初始化
    const LOGIN_TIMEOUT = 15000

    return retryRequest(() =>
      api.post<{ access_token: string; token_type: string }>(
        '/auth/login',
        formData,
        {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          timeout: LOGIN_TIMEOUT
        }
      ),
      3,  // 最多重试3次
      2000  // 初始重试间隔2秒
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
  assist: (data: AIRequest) => api.post<AIAssistResponse>('/ai/assist', data),
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
  },
  /** 批量/多轮次写作（流式） */
  batchGenerateStream: (data: AIBatchGenerateRequest) => {
    const token = localStorage.getItem('token')
    return fetch(`${API_BASE_URL}/api/ai/batch-generate/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(data)
    })
  },
  /** 分析文学作品 - 设置 3 分钟超时 */
  analyzeLiterature: (data: LiteraryAnalysisRequest) =>
    api.post<LiteraryAnalysisResult>('/ai/analyze-literature', data, { timeout: 180000 }),
  /** 从文学作品创建项目 */
  createProjectFromLiterature: (data: CreateProjectFromLiteratureRequest) =>
    api.post<CreateProjectFromLiteratureResponse>('/ai/create-project-from-literature', data),
  /** 将文学作品分析应用到已有项目（覆盖项目设定） */
  applyProjectFromLiterature: (data: any) =>
    api.post('/ai/apply-project-from-literature', data),

  /** 根据文档正文生成 AI 插图（插入 image 块），耗时较长 */
  generateArticleImage: (data: {
    document_id: number
    style?: string
    extra_hint?: string
    /** 非空时仅用选中段落等文本作为上下文 */
    context_text?: string | null
    /** 当前编辑器块（与未保存内容一致）；不传则服务端仅用数据库正文 */
    blocks?: Block[] | null
  }) =>
    api.post<{ success: boolean; image_url: string; prompt: string; block: Block }>(
      '/ai/generate-article-image',
      data,
      { timeout: 180000 }
    ),

  /** 上传本地图片到服务器 static，返回 /static/... URL */
  uploadDocumentImage: (documentId: number, file: File) => {
    const fd = new FormData()
    fd.append('document_id', String(documentId))
    fd.append('file', file)
    return api.post<{ success: boolean; url: string }>('/ai/upload-document-image', fd, {
      timeout: 120000,
    })
  },
}

// ========== 系统 / AI 配置 API ==========
export const systemApi = {
  aiConfig: () => api.get<AIConfig>('/system/ai-config'),
  testAI: (data: AIConfig) =>
    api.post<{ success: boolean; message?: string }>('/system/ai-config/test', data),
  saveUserAIConfig: (data: AIConfig) =>
    api.post('/system/user-ai-config', data),
}

// ========== 多平台发布 API ==========
export const publishApi = {
  getPlatforms: () => api.get('/publish/platforms'),

  formatForPlatform: (data: {
    document_id?: number
    raw_title?: string
    raw_content?: string
    raw_blocks?: any[]
    platform_id: string
  }) => api.post('/publish/format', data),

  formatBatch: (data: {
    document_id?: number
    raw_title?: string
    raw_content?: string
    raw_blocks?: any[]
    platform_ids: string[]
  }) => api.post('/publish/format-batch', data),

  wechatDraft: (data: {
    document_id: number
    title?: string
    author?: string
    digest?: string
    content_source_url?: string
    thumb_media_id?: string
    need_open_comment?: boolean
    only_fans_can_comment?: boolean
    publish_now?: boolean
    mock_mode?: boolean
  }) => api.post('/publish/wechat/draft', data),
}

export default api
export { API_BASE_URL }
export * from './types'
