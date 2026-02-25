import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { projectApi, documentApi, memoryApi } from '@/api'

export interface Project {
  id: number
  title: string
  description?: string
  created_at: string
  updated_at: string
  documents?: Document[]
  ai_memory?: AIMemory
}

export interface Document {
  id: number
  title: string
  content: Block[]
  project_id: number
  parent_id?: number
  created_at: string
  updated_at: string
}

export interface Block {
  id: string
  type: string
  content: string
  props?: Record<string, any>
}

export interface Character {
  name: string
  description: string
  personality?: string
  background?: string
  goals?: string
}

export interface AIMemory {
  id: number
  project_id: number
  outline: any[]
  storyline?: string
  characters: Character[]
  world_building: Record<string, any>
  writing_style?: string
  key_points: string[]
  notes?: string
}

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
      const res = await projectApi.get(id)
      currentProject.value = res.data
      return res.data
    } finally {
      loading.value = false
    }
  }

  async function createProject(data: Partial<Project>) {
    const res = await projectApi.create(data)
    projects.value.push(res.data)
    return res.data
  }

  async function updateProject(id: number, data: Partial<Project>) {
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

  async function createDocument(projectId: number, data: Partial<Document>) {
    const res = await documentApi.create(projectId, data)
    if (currentProject.value) {
      currentProject.value.documents = currentProject.value.documents || []
      currentProject.value.documents.push(res.data)
    }
    return res.data
  }

  async function updateDocument(id: number, data: Partial<Document>) {
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

  // Memory actions
  async function fetchMemory(projectId: number) {
    const res = await memoryApi.get(projectId)
    if (currentProject.value) {
      currentProject.value.ai_memory = res.data
    }
    return res.data
  }

  async function updateMemory(projectId: number, data: Partial<AIMemory>) {
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
    fetchMemory,
    updateMemory
  }
})
