/**
 * 将 AI 返回的带格式文本解析为文档块（Block）列表。
 * 约定：## 小节标题、### 子标题、> 引用/对话、- 列表、--- 分隔线，段落之间空一行。
 */
import type { Block } from '@/api/types'

const BLOCK_TYPES = ['paragraph', 'heading', 'subheading', 'quote', 'list', 'code', 'divider'] as const
type BlockType = (typeof BLOCK_TYPES)[number]

function genId(prefix: string, index: number): string {
  return `${prefix}-${Date.now()}-${index}`
}

export function parseFormattedTextToBlocks(text: string, idPrefix = 'block'): Block[] {
  if (!text || typeof text !== 'string') {
    return [{ id: genId(idPrefix, 0), type: 'paragraph', content: '', props: {} }]
  }

  const blocks: Block[] = []
  const lines = text.split(/\r?\n/)
  let paragraphLines: string[] = []
  let index = 0

  function flushParagraph() {
    const s = paragraphLines.join('\n').trim()
    if (s) {
      blocks.push({
        id: genId(idPrefix, index++),
        type: 'paragraph',
        content: s,
        props: {}
      })
    }
    paragraphLines = []
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const trimmed = line.trim()

    if (trimmed === '' || trimmed === '\n') {
      flushParagraph()
      continue
    }

    if (/^---+\s*$|^——+\s*$/.test(trimmed)) {
      flushParagraph()
      blocks.push({
        id: genId(idPrefix, index++),
        type: 'divider',
        content: '',
        props: {}
      })
      continue
    }

    if (trimmed.startsWith('### ')) {
      flushParagraph()
      blocks.push({
        id: genId(idPrefix, index++),
        type: 'subheading',
        content: trimmed.slice(4).trim(),
        props: {}
      })
      continue
    }

    if (trimmed.startsWith('## ')) {
      flushParagraph()
      blocks.push({
        id: genId(idPrefix, index++),
        type: 'heading',
        content: trimmed.slice(3).trim(),
        props: { level: 2 }
      })
      continue
    }

    if (trimmed.startsWith('##')) {
      flushParagraph()
      blocks.push({
        id: genId(idPrefix, index++),
        type: 'heading',
        content: trimmed.slice(2).trim(),
        props: { level: 2 }
      })
      continue
    }

    if (trimmed.startsWith('>')) {
      flushParagraph()
      const content = trimmed.slice(1).replace(/^[\s\u00A0]+/, '')
      blocks.push({
        id: genId(idPrefix, index++),
        type: 'quote',
        content,
        props: {}
      })
      continue
    }

    if (trimmed.startsWith('- ')) {
      flushParagraph()
      blocks.push({
        id: genId(idPrefix, index++),
        type: 'list',
        content: trimmed.slice(2).trim(),
        props: {}
      })
      continue
    }

    paragraphLines.push(line)
  }

  flushParagraph()

  if (blocks.length === 0) {
    blocks.push({
      id: genId(idPrefix, 0),
      type: 'paragraph',
      content: text.trim(),
      props: {}
    })
  }

  return blocks
}
