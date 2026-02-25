import { api } from './index'

export const versionApi = {
  // 获取版本列表
  list: (documentId: number) => {
    return api.get(`/versions/document/${documentId}`)
  },

  // 创建版本
  create: (documentId: number, data: {
    title: string
    content: any[]
    change_summary?: string
  }) => {
    return api.post(`/versions/document/${documentId}`, data)
  },

  // 获取版本详情
  get: (versionId: number) => {
    return api.get(`/versions/${versionId}`)
  },

  // 恢复版本
  restore: (versionId: number) => {
    return api.post(`/versions/${versionId}/restore`)
  },

  // 删除版本
  delete: (versionId: number) => {
    return api.delete(`/versions/${versionId}`)
  },

  // 对比版本
  compare: (documentId: number, v1: number, v2: number) => {
    return api.get(`/versions/document/${documentId}/compare?v1=${v1}&v2=${v2}`)
  }
}
