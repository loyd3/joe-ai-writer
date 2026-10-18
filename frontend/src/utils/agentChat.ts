import type { ProjectAgentRun } from '@/api/project-agent'

const SYSTEM_NOTE_RE = /\n*（系统(?:说明)?[：:][\s\S]*?）|\n*\(系统(?:说明)?[：:][\s\S]*?\)/g

/** 拆出用户可见正文与隐藏的（系统：…）编排说明。 */
export function extractAgentSystemNotes(text: string): { visible: string; system: string } {
  const parts: string[] = []
  const visible = (text || '')
    .replace(SYSTEM_NOTE_RE, (match) => {
      const note = match.trim()
      if (note) parts.push(note)
      return ''
    })
    .trim()
  return { visible, system: parts.join('\n\n') }
}

/** 去掉绑定进 instruction 的系统注记，用户对话框只看自己说的话。 */
export function stripAgentSystemNotes(text: string): string {
  return extractAgentSystemNotes(text).visible
}

/** 提交时把隐藏系统说明拼回（输入框只显示 visible）。 */
export function mergeAgentSystemNotes(visible: string, system: string): string {
  const user = (visible || '').trim()
  const note = (system || '').trim()
  if (!note) return user
  if (!user) return note
  return `${user}\n\n${note}`
}

/** Never surface model tool instructions, including partially streamed JSON. */
export function assistantMessages(run: Pick<ProjectAgentRun, 'messages' | 'answer'>): string[] {
  const result: string[] = []
  for (const message of run.messages || []) {
    if (message.role !== 'assistant') continue
    const text = message.content.trim().split('```')[0].trim()
    if (!text || text.startsWith('{') || result[result.length - 1] === text) continue
    result.push(text)
  }
  const answer = (run.answer || '').trim()
  if (answer && result[result.length - 1] !== answer) result.push(answer)
  return result
}

/** 终稿与中间思考分开：终稿常显，思考过程可折叠压缩。 */
export function assistantTurnDisplay(
  run: Pick<ProjectAgentRun, 'messages' | 'answer'>,
): { thinking: string[]; final: string } {
  const all = assistantMessages(run)
  if (!all.length) return { thinking: [], final: '' }
  if (all.length === 1) return { thinking: [], final: all[0] }
  return { thinking: all.slice(0, -1), final: all[all.length - 1] }
}

/** 压缩思考摘要：取首句或前 N 字，供折叠标题展示。 */
export function thinkingSummary(thinking: string[], maxLen = 48): string {
  if (!thinking.length) return ''
  const first = thinking[0].replace(/\s+/g, ' ').trim()
  if (first.length <= maxLen) {
    return thinking.length === 1 ? first : `${first}…（共 ${thinking.length} 步）`
  }
  return `${first.slice(0, maxLen)}…（共 ${thinking.length} 步）`
}

export function readablePreview(value: unknown): string {
  if (value == null) return '（无）'
  if (typeof value === 'string') return value
  if (Array.isArray(value)) return value.map(readablePreview).join('\n\n')
  if (typeof value === 'object') {
    const data = value as Record<string, unknown>
    if (Array.isArray(data.content)) {
      return [data.title, ...data.content.map(readablePreview)].filter(Boolean).join('\n\n')
    }
    if (typeof data.content === 'string') return data.content
  }
  return JSON.stringify(value, null, 2)
}
