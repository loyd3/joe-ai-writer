import type { ProjectAgentRun } from '@/api/project-agent'

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
