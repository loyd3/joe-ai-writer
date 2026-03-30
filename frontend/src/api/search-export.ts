import api from './index'

export interface SearchResultItem {
  document_id: number
  document_title: string
  project_id: number
  project_title: string
  chunk_index: number
  content: string
  start_offset: number
  end_offset: number
  block_id?: string
  block_type?: string
  score: number
  match_type: string
  highlights: number[][]
  context_before: string
  context_after: string
}

export interface EnhancedSearchResponse {
  results: SearchResultItem[]
  total: number
  query: string
  search_type: string
  stats?: Record<string, unknown>
}

export interface SearchStats {
  total_chunks: number
  total_documents: number
  projects: Record<number, number>
  embedding_model_loaded: boolean
}

export const searchApi = {
  search: (q: string, projectId?: number) => {
    const params = new URLSearchParams()
    params.append('q', q)
    if (projectId) params.append('project_id', projectId.toString())
    return api.get(`/search/?${params.toString()}`)
  },
  
  suggestions: (q: string) => {
    return api.get(`/search/suggest?q=${encodeURIComponent(q)}`)
  },
  
  enhancedSearch: (params: {
    q: string
    project_id?: number
    use_semantic?: boolean
    use_keyword?: boolean
    top_k?: number
    min_score?: number
  }) => {
    const searchParams = new URLSearchParams()
    searchParams.append('q', params.q)
    if (params.project_id) searchParams.append('project_id', params.project_id.toString())
    if (params.use_semantic !== undefined) searchParams.append('use_semantic', params.use_semantic.toString())
    if (params.use_keyword !== undefined) searchParams.append('use_keyword', params.use_keyword.toString())
    if (params.top_k) searchParams.append('top_k', params.top_k.toString())
    if (params.min_score !== undefined) searchParams.append('min_score', params.min_score.toString())
    return api.get<EnhancedSearchResponse>(`/search/enhanced?${searchParams.toString()}`)
  },
  
  searchInDocument: (documentId: number, q: string, topK?: number) => {
    const params = new URLSearchParams()
    params.append('q', q)
    if (topK) params.append('top_k', topK.toString())
    return api.get<EnhancedSearchResponse>(`/search/document/${documentId}?${params.toString()}`)
  },
  
  getStats: () => {
    return api.get<SearchStats>('/search/stats')
  },
  
  indexDocument: (documentId: number) => {
    return api.post<{ success: boolean; document_id: number; indexed_chunks: number }>(`/search/index/document/${documentId}`)
  },
  
  indexProject: (projectId: number) => {
    return api.post<{ success: boolean; project_id: number; indexed_documents: number; total_chunks: number }>(`/search/index/project/${projectId}`)
  },
  
  indexAll: () => {
    return api.post<{ success: boolean; indexed_documents: number; total_chunks: number; total_projects: number }>('/search/index/all')
  },
  
  removeDocumentIndex: (documentId: number) => {
    return api.delete<{ success: boolean; message: string }>(`/search/index/document/${documentId}`)
  }
}

export const exportApi = {
  exportDocumentMarkdown: (documentId: number, includeMemory: boolean = true) => {
    return api.get(`/export/document/${documentId}/markdown?include_memory=${includeMemory}`, {
      responseType: 'blob'
    })
  },
  
  exportDocumentPdf: (documentId: number, includeMemory: boolean = true) => {
    return api.get(`/export/document/${documentId}/pdf?include_memory=${includeMemory}`, {
      responseType: 'blob'
    })
  },
  
  exportDocumentDocx: (documentId: number, includeMemory: boolean = true) => {
    return api.get(`/export/document/${documentId}/docx?include_memory=${includeMemory}`, {
      responseType: 'blob'
    })
  },
  
  exportDocumentTxt: (documentId: number) => {
    return api.get(`/export/document/${documentId}/txt`, {
      responseType: 'blob'
    })
  },
  
  exportProjectMarkdown: (projectId: number, includeMemory: boolean = true) => {
    return api.get(`/export/project/${projectId}/markdown?include_memory=${includeMemory}`, {
      responseType: 'blob'
    })
  },

  exportProjectJson: (projectId: number, includeMemory: boolean = true) => {
    return api.get(`/export/project/${projectId}/json?include_memory=${includeMemory}`, {
      responseType: 'blob'
    })
  }
}

export const importApi = {
  importProject: (data: { version?: number; project: Record<string, unknown>; documents: Record<string, unknown>[]; memory?: Record<string, unknown> | null }) => {
    return api.post<{ success: boolean; message: string; project_id: number; project_title: string; documents_count: number }>('/import/project', data)
  }
}

export function downloadFile(blob: Blob, filename: string, mimeType?: string) {
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
