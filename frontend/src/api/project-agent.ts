import api from './index'

export type ProjectAgentStatus =
  | 'queued' | 'running' | 'proposed' | 'completed'
  | 'failed' | 'cancelled' | 'applied' | 'reverted'

export interface ProjectAgentChange {
  id: string
  kind: string
  target_id?: number
  project_id?: number
  title: string
  before: unknown
  after: unknown
  reason: string
}

export interface ProjectAgentRun {
  id: string
  scope?: 'project' | 'system'
  project_id?: number | null
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

/** 文档编辑焦点：让智能体优先处理当前打开的文档/选区 */
export type ProjectAgentFocus = {
  document_id: number
  selection?: string
  block_ids?: string[]
}

/** projectId 为空时走系统级 /agent/runs（无项目会话） */
const runsBase = (projectId?: number | null) =>
  projectId && projectId > 0 ? `/projects/${projectId}/agent/runs` : '/agent/runs'

const config = (signal?: AbortSignal) => ({ signal, timeout: 30000 })

// Use the authenticated shared client directly: mutations must never be retried.
export const projectAgentApi = {
  async list(projectId: number | null | undefined, signal?: AbortSignal): Promise<ProjectAgentRun[]> {
    return (await api.get<ProjectAgentRun[]>(runsBase(projectId), config(signal))).data
  },
  async get(
    projectId: number | null | undefined,
    runId: string,
    signal?: AbortSignal,
  ): Promise<ProjectAgentRun> {
    return (
      await api.get<ProjectAgentRun>(
        `${runsBase(projectId)}/${encodeURIComponent(runId)}`,
        config(signal),
      )
    ).data
  },
  async create(
    projectId: number | null | undefined,
    instruction: string,
    conversationId?: string,
    signal?: AbortSignal,
    focus?: ProjectAgentFocus | null,
  ): Promise<ProjectAgentRun> {
    return (
      await api.post<ProjectAgentRun>(
        runsBase(projectId),
        {
          instruction,
          ...(conversationId ? { conversation_id: conversationId } : {}),
          ...(projectId && focus?.document_id ? { focus } : {}),
        },
        config(signal),
      )
    ).data
  },
  async action(
    projectId: number | null | undefined,
    runId: string,
    action: ProjectAgentAction,
    signal?: AbortSignal,
  ): Promise<ProjectAgentRun> {
    return (
      await api.post<ProjectAgentRun>(
        `${runsBase(projectId)}/${encodeURIComponent(runId)}/${action}`,
        {},
        config(signal),
      )
    ).data
  },
}
