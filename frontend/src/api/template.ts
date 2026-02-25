import api from './index'

export const templateApi = {
  // 获取模板列表
  list: (category?: string) => {
    const params = category && category !== 'all' ? `?category=${category}` : ''
    return api.get(`/templates/${params}`)
  },

  // 应用模板（新建项目）
  apply: (templateId: number, data: { project_name?: string }) => {
    return api.post(`/templates/${templateId}/apply`, data)
  },

  // 应用模板到现有项目（覆盖当前项目）
  applyToProject: (templateId: number, projectId: number) => {
    return api.post(`/templates/${templateId}/apply-to-project?project_id=${projectId}`)
  },

  // 创建自定义模板
  create: (data: any) => {
    return api.post('/templates/', data)
  },

  // 删除模板
  delete: (templateId: number) => {
    return api.delete(`/templates/${templateId}`)
  }
}
