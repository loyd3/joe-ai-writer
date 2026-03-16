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
  
  // 导出文档为 PDF
  exportDocumentPdf: (documentId: number, includeMemory: boolean = true) => {
    return api.get(`/export/document/${documentId}/pdf?include_memory=${includeMemory}`, {
      responseType: 'blob'
    })
  },
  
  // 导出文档为 Word
  exportDocumentDocx: (documentId: number, includeMemory: boolean = true) => {
    return api.get(`/export/document/${documentId}/docx?include_memory=${includeMemory}`, {
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
  },

  // 导出整个项目为 JSON 项目包（可再导入为新项目）
  exportProjectJson: (projectId: number, includeMemory: boolean = true) => {
    return api.get(`/export/project/${projectId}/json?include_memory=${includeMemory}`, {
      responseType: 'blob'
    })
  }
}

// 导入 API
export const importApi = {
  // 导入项目包（JSON 对象，与导出格式一致）
  importProject: (data: { version?: number; project: Record<string, unknown>; documents: Record<string, unknown>[]; memory?: Record<string, unknown> | null }) => {
    return api.post<{ success: boolean; message: string; project_id: number; project_title: string; documents_count: number }>('/import/project', data)
  }
}

// 下载文件辅助函数
export function downloadFile(blob: Blob, filename: string, mimeType?: string) {
  // 如果 blob 没有 type，使用提供的 mimeType
  const finalBlob = mimeType && (!blob.type || blob.type === 'application/octet-stream') 
    ? new Blob([blob], { type: mimeType })
    : blob
  
  const url = window.URL.createObjectURL(finalBlob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}
