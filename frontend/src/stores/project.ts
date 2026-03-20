import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { projectApi, documentApi, memoryApi } from '@/api'
import type { Project, Document, AIMemory, Block, ProjectCreate, ProjectUpdate, DocumentCreate, DocumentUpdate, AIMemoryUpdate } from '@/api'

// 从 API 模块重新导出类型，保持兼容性
export type { Project, Document, AIMemory, Block }

export const useProjectStore = defineStore('project', () => {
  // State
  const projects = ref<Project[]>([])
  const currentProject = ref<Project | null>(null)
  const currentDocument = ref<Document | null>(null)
  const loading = ref(false)

  // Getters
  const projectList = computed(() => projects.value)
  
  // Actions
  async function fetchProjects() {
    loading.value = true
    try {
      const res = await projectApi.list()
      projects.value = res.data
    } finally {
      loading.value = false
    }
  }

  async function fetchProject(id: number) {
    loading.value = true
    try {
      const [projectRes, docsRes] = await Promise.all([
        projectApi.get(id),
        documentApi.list(id)
      ])
      const project = { ...projectRes.data, documents: docsRes.data || [] }
      currentProject.value = project
      return project
    } finally {
      loading.value = false
    }
  }

  async function createProject(data: ProjectCreate) {
    const res = await projectApi.create(data)
    projects.value.push(res.data)
    return res.data
  }

  async function updateProject(id: number, data: ProjectUpdate) {
    const res = await projectApi.update(id, data)
    const index = projects.value.findIndex(p => p.id === id)
    if (index !== -1) {
      projects.value[index] = { ...projects.value[index], ...res.data }
    }
    if (currentProject.value?.id === id) {
      currentProject.value = { ...currentProject.value, ...res.data }
    }
    return res.data
  }

  async function deleteProject(id: number) {
    await projectApi.delete(id)
    projects.value = projects.value.filter(p => p.id !== id)
  }

  // Document actions
  async function fetchDocument(id: number) {
    const res = await documentApi.get(id)
    currentDocument.value = res.data
    return res.data
  }

  async function createDocument(projectId: number, data: DocumentCreate) {
    const res = await documentApi.create(projectId, data)
    if (currentProject.value) {
      currentProject.value.documents = currentProject.value.documents || []
      currentProject.value.documents.push(res.data)
    }
    return res.data
  }

  async function updateDocument(id: number, data: DocumentUpdate) {
    const res = await documentApi.update(id, data)
    if (currentDocument.value?.id === id) {
      currentDocument.value = { ...currentDocument.value, ...res.data }
    }
    return res.data
  }

  async function deleteDocument(id: number) {
    await documentApi.delete(id)
    if (currentProject.value?.documents) {
      currentProject.value.documents = currentProject.value.documents.filter(d => d.id !== id)
    }
  }

  async function reorderDocuments(projectId: number, documentIds: number[]) {
    const res = await documentApi.reorder(projectId, documentIds)
    if (currentProject.value?.id === projectId) {
      currentProject.value.documents = res.data
    }
    return res.data
  }

  // Memory actions
  async function fetchMemory(projectId: number) {
    const res = await memoryApi.get(projectId)
    if (currentProject.value) {
      currentProject.value.ai_memory = res.data
    }
    return res.data
  }

  async function updateMemory(projectId: number, data: AIMemoryUpdate) {
    const res = await memoryApi.update(projectId, data)
    if (currentProject.value) {
      currentProject.value.ai_memory = res.data
    }
    return res.data
  }

  return {
    projects,
    currentProject,
    currentDocument,
    loading,
    projectList,
    fetchProjects,
    fetchProject,
    createProject,
    updateProject,
    deleteProject,
    fetchDocument,
    createDocument,
    updateDocument,
    deleteDocument,
    reorderDocuments,
    fetchMemory,
    updateMemory
  }
})
