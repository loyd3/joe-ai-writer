import api from './index'

export type ProjectAgentStatus =
  | 'queued' | 'running' | 'proposed' | 'completed'
  | 'failed' | 'cancelled' | 'applied' | 'reverted'

export interface ProjectAgentChange {
  id: string
  kind: string
  target_id?: number
  title: string
  before: unknown
  after: unknown
  reason: string
}

export interface ProjectAgentRun {
  id: string
  conversation_id: string
  instruction: string
  status: ProjectAgentStatus
  answer: string
  messages?: Array<{ role: string; content: string; step?: number; streaming?: boolean }>
  error?: string
  events: Array<{ sequence: number; type: string; message: string }>
  changes: ProjectAgentChange[]
  created_at: string
}

export type ProjectAgentAction = 'cancel' | 'resume' | 'apply' | 'revert'
const base = (projectId: number) => `/projects/${projectId}/agent/runs`
const config = (signal?: AbortSignal) => ({ signal, timeout: 30000 })

// Use the authenticated shared client directly: mutations must never be retried.
export const projectAgentApi = {
  async list(projectId: number, signal?: AbortSignal): Promise<ProjectAgentRun[]> {
    return (await api.get<ProjectAgentRun[]>(base(projectId), config(signal))).data
  },
  async get(projectId: number, runId: string, signal?: AbortSignal): Promise<ProjectAgentRun> {
    return (await api.get<ProjectAgentRun>(`${base(projectId)}/${encodeURIComponent(runId)}`, config(signal))).data
  },
  async create(projectId: number, instruction: string, conversationId?: string, signal?: AbortSignal): Promise<ProjectAgentRun> {
    return (await api.post<ProjectAgentRun>(base(projectId), {
      instruction,
      ...(conversationId ? { conversation_id: conversationId } : {})
    }, config(signal))).data
  },
  async action(projectId: number, runId: string, action: ProjectAgentAction, signal?: AbortSignal): Promise<ProjectAgentRun> {
    return (await api.post<ProjectAgentRun>(`${base(projectId)}/${encodeURIComponent(runId)}/${action}`, {}, config(signal))).data
  }
}
