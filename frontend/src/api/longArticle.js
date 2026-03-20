// 长篇文章生成API
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function authHeaders() {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export const longArticleApi = {
  // 创建文章任务
  createArticle: async (data) => {
    const response = await axios.post(`${API_BASE_URL}/api/long-article/create`, data, {
      headers: authHeaders()
    });
    return response.data;
  },

  // 生成大纲
  generateOutline: async (articleId, regenerate = false) => {
    const response = await axios.post(`${API_BASE_URL}/api/long-article/generate-outline`, {
      article_id: articleId,
      regenerate
    }, {
      headers: authHeaders()
    });
    return response.data;
  },

  // 获取进度
  getProgress: async (articleId) => {
    const response = await axios.get(`${API_BASE_URL}/api/long-article/progress/${articleId}`, {
      headers: authHeaders()
    });
    return response.data;
  },

  // 获取章节列表
  getChapters: async (articleId) => {
    const response = await axios.get(`${API_BASE_URL}/api/long-article/chapters/${articleId}`, {
      headers: authHeaders()
    });
    return response.data;
  },

  // 导出文章
  exportArticle: async (articleId, format = 'txt') => {
    const response = await axios.get(
      `${API_BASE_URL}/api/long-article/export/${articleId}?format=${format}`,
      { responseType: 'blob', headers: authHeaders() }
    );
    return response.data;
  },

  // 获取文章列表
  listArticles: async (params = {}) => {
    const response = await axios.get(`${API_BASE_URL}/api/long-article/list`, {
      params,
      headers: authHeaders()
    });
    return response.data;
  },

  // 删除文章
  deleteArticle: async (articleId) => {
    const response = await axios.delete(`${API_BASE_URL}/api/long-article/${articleId}`, {
      headers: authHeaders()
    });
    return response.data;
  },

  // 流式生成（SSE）
  generateStream: (articleId) => {
    const token = localStorage.getItem('token')
    const sep = '?'
    return new EventSource(`${API_BASE_URL}/api/long-article/generate/${articleId}${token ? `${sep}token=${token}` : ''}`);
  },

  // 恢复生成
  resumeStream: (articleId) => {
    const token = localStorage.getItem('token')
    const sep = '?'
    return new EventSource(`${API_BASE_URL}/api/long-article/resume/${articleId}${token ? `${sep}token=${token}` : ''}`);
  }
};

// 兼容导出：部分组件使用 API_BASE_URL
export { API_BASE_URL };
