import api from './index'

export const extractApi = {
  // 从文档提取信息
  extract: (documentId: number) => {
    return api.post(`/extract/document/${documentId}`)
  },

  // 应用提取的信息到项目设定
  apply: (documentId: number, data: { extracted: any }) => {
    return api.post(`/extract/document/${documentId}/apply`, data)
  },

  // 分析故事线
  analyzeStoryline: (documentId: number) => {
    return api.post('/extract/analyze-storyline', null, {
      params: { document_id: documentId }
    })
  },

  // 建议新角色
  suggestCharacters: (documentId: number) => {
    return api.post('/extract/suggest-characters', null, {
      params: { document_id: documentId }
    })
  }
}
