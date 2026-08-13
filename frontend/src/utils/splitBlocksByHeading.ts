import type { Block } from '@/api/types'

export type SplitLevel = 'heading' | 'subheading'

export interface SplitSection {
  title: string
  blocks: Block[]
  /** 原文档中起始块下标 */
  startIndex: number
  /** 原文档中结束块下标（不含） */
  endIndex: number
}

function stripHtml(html: string): string {
  if (typeof document !== 'undefined') {
    const div = document.createElement('div')
    div.innerHTML = html || ''
    return (div.textContent || '').trim()
  }
  return String(html || '')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ')
    .trim()
}

function cloneBlocks(blocks: Block[]): Block[] {
  return blocks.map((b) => ({
    id: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`,
    type: b.type || 'paragraph',
    content: typeof b.content === 'string' ? b.content : '',
    props: b.props && typeof b.props === 'object' ? { ...b.props } : {},
  }))
}

function isSplitMarker(block: Block, level: SplitLevel): boolean {
  if (level === 'heading') return block.type === 'heading'
  // 小标题模式：大标题与小标题都作为分节起点（大标题单独成篇时也切开）
  return block.type === 'heading' || block.type === 'subheading'
}

/**
 * 按大标题 / 小标题把一块文档拆成多个小节。
 * - heading：每个 `heading` 到下一 `heading` 前为一篇
 * - subheading：每个 `heading`/`subheading` 到下一标记前为一篇
 * 首个标题前的内容归入「前言」（若有实质内容）
 */
export function splitBlocksByHeading(blocks: Block[], level: SplitLevel = 'heading'): SplitSection[] {
  if (!blocks?.length) return []

  const markers: number[] = []
  for (let i = 0; i < blocks.length; i++) {
    if (isSplitMarker(blocks[i], level)) markers.push(i)
  }

  if (markers.length === 0) return []

  const sections: SplitSection[] = []

  // 前言：第一个标题之前
  if (markers[0] > 0) {
    const preamble = blocks.slice(0, markers[0])
    const hasText = preamble.some((b) => b.type === 'image' || stripHtml(b.content || ''))
    if (hasText) {
      sections.push({
        title: '前言',
        blocks: cloneBlocks(preamble),
        startIndex: 0,
        endIndex: markers[0],
      })
    }
  }

  for (let m = 0; m < markers.length; m++) {
    const start = markers[m]
    const end = m + 1 < markers.length ? markers[m + 1] : blocks.length
    const slice = blocks.slice(start, end)
    const title = stripHtml(blocks[start].content || '') || `未命名小节 ${m + 1}`
    sections.push({
      title: title.slice(0, 200),
      blocks: cloneBlocks(slice),
      startIndex: start,
      endIndex: end,
    })
  }

  return sections
}

export function countSplitMarkers(blocks: Block[], level: SplitLevel): number {
  return blocks.filter((b) => isSplitMarker(b, level)).length
}
