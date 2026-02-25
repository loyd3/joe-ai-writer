import api from './index'

// 搜索 API
export const searchApi = {
  // 全局搜索
  search: (q: string, projectId?: number) => {
    const params = new URLSearchParams()
    params.append('q', q)
    if (projectId) params.append('project_id', projectId.toString())
    return api.get(`/search/?${params.toString()}`)
  },
  
  // 搜索建议
  suggestions: (q: string) => {
    return api.get(`/search/suggest?q=${encodeURIComponent(q)}`)
  }
}

// 导出 API
export const exportApi = {
  // 导出文档为 Markdown
  exportDocumentMarkdown: (documentId: number, includeMemory: boolean = true) => {
    return api.get(`/export/document/${documentId}/markdown?include_memory=${includeMemory}`, {
      responseType: 'blob'
    })
  },
  
  // 导出文档为纯文本
  exportDocumentTxt: (documentId: number) => {
    return api.get(`/export/document/${documentId}/txt`, {
      responseType: 'blob'
    })
  },
  
  // 导出整个项目为 Markdown
  exportProjectMarkdown: (projectId: number, includeMemory: boolean = true) => {
    return api.get(`/export/project/${projectId}/markdown?include_memory=${includeMemory}`, {
      responseType: 'blob'
    })
  }
}

// 下载文件辅助函数
export function downloadFile(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}
