/**
 * 将 AI 返回的带格式文本解析为文档块（Block）列表，并做轻度规范化，
 * 便于编辑器直接展示标题 / 引用 / 列表等结构。
 *
 * 约定：
 * - ## 小节标题、### 子标题、# 大标题
 * - > 引用/对话、- / * / 数字. 列表、--- 分隔线
 * - 段落之间空一行
 * - 自动去掉 **加粗** / *斜体* / ``` 代码围栏标记（保留文字）
 */
import type { Block } from '@/api/types'

function genId(prefix: string, index: number): string {
  return `${prefix}-${Date.now()}-${index}`
}

/** 去掉常见 Markdown 装饰，保留纯文本语义 */
export function stripInlineMarkdown(text: string): string {
  if (!text) return ''
  let s = text
  // 围栏代码块：保留内部文本
  s = s.replace(/```[\w]*\n?([\s\S]*?)```/g, (_, inner) => String(inner || '').trim())
  // 加粗
  s = s.replace(/\*\*([^*]+)\*\*/g, '$1')
  s = s.replace(/__([^_]+)__/g, '$1')
  // 斜体（避免误伤已处理的 **）
  s = s.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, '$1$2')
  s = s.replace(/(^|[^_])_([^_\n]+)_(?!_)/g, '$1$2')
  // 行内代码
  s = s.replace(/`([^`]+)`/g, '$1')
  // 链接 [text](url) → text
  s = s.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
  return s.trim()
}

function looksLikeListItem(trimmed: string): { content: string } | null {
  const bullet = trimmed.match(/^[-*•]\s+(.+)$/)
  if (bullet) return { content: bullet[1].trim() }
  const numbered = trimmed.match(/^\d+[.)、]\s+(.+)$/)
  if (numbered) return { content: numbered[1].trim() }
  return null
}

/**
 * 解析 AI 文本为编辑器 Block；写入前再走一遍规范化。
 */
export function parseFormattedTextToBlocks(text: string, idPrefix = 'block'): Block[] {
  if (!text || typeof text !== 'string') {
    return [{ id: genId(idPrefix, 0), type: 'paragraph', content: '', props: {} }]
  }

  // 统一换行，去掉首尾多余空行
  let raw = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim()
  // 去掉整段被 ```markdown 包裹的情况
  const fence = raw.match(/^```(?:markdown|md|text)?\n([\s\S]*?)\n```$/i)
  if (fence) raw = fence[1].trim()

  const blocks: Block[] = []
  const lines = raw.split('\n')
  let paragraphLines: string[] = []
  let index = 0

  function flushParagraph() {
    const s = stripInlineMarkdown(paragraphLines.join('\n'))
    if (s) {
      blocks.push({
        id: genId(idPrefix, index++),
        type: 'paragraph',
        content: s,
        props: {},
      })
    }
    paragraphLines = []
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const trimmed = line.trim()

    if (!trimmed) {
      flushParagraph()
      continue
    }

    if (/^---+\s*$|^——+\s*$|^___+\s*$/.test(trimmed)) {
      flushParagraph()
      blocks.push({
        id: genId(idPrefix, index++),
        type: 'divider',
        content: '',
        props: {},
      })
      continue
    }

    // ### 子标题
    if (/^#{3}\s+/.test(trimmed)) {
      flushParagraph()
      blocks.push({
        id: genId(idPrefix, index++),
        type: 'subheading',
        content: stripInlineMarkdown(trimmed.replace(/^#{3}\s+/, '')),
        props: {},
      })
      continue
    }

    // ## 或 # 标题（编辑器 heading 统一 level 2；# 也当标题）
    if (/^#{1,2}\s+/.test(trimmed)) {
      flushParagraph()
      const level = trimmed.startsWith('##') ? 2 : 1
      blocks.push({
        id: genId(idPrefix, index++),
        type: 'heading',
        content: stripInlineMarkdown(trimmed.replace(/^#{1,2}\s+/, '')),
        props: { level },
      })
      continue
    }

    // 兼容「##标题」无空格
    if (/^##[^#\s]/.test(trimmed)) {
      flushParagraph()
      blocks.push({
        id: genId(idPrefix, index++),
        type: 'heading',
        content: stripInlineMarkdown(trimmed.slice(2).trim()),
        props: { level: 2 },
      })
      continue
    }

    if (trimmed.startsWith('>')) {
      flushParagraph()
      const content = stripInlineMarkdown(trimmed.replace(/^>\s?/, ''))
      blocks.push({
        id: genId(idPrefix, index++),
        type: 'quote',
        content,
        props: {},
      })
      continue
    }

    const listItem = looksLikeListItem(trimmed)
    if (listItem) {
      flushParagraph()
      blocks.push({
        id: genId(idPrefix, index++),
        type: 'list',
        content: stripInlineMarkdown(listItem.content),
        props: {},
      })
      continue
    }

    paragraphLines.push(line)
  }

  flushParagraph()

  const normalized = normalizeBlocks(blocks, idPrefix)

  if (normalized.length === 0) {
    return [
      {
        id: genId(idPrefix, 0),
        type: 'paragraph',
        content: stripInlineMarkdown(raw),
        props: {},
      },
    ]
  }

  return normalized
}

/** 去掉空块、合并连续 divider、清理内容空白 */
export function normalizeBlocks(blocks: Block[], idPrefix = 'block'): Block[] {
  const out: Block[] = []
  let index = 0
  for (const b of blocks) {
    const type = b.type || 'paragraph'
    const content = typeof b.content === 'string' ? b.content.trim() : ''
    if (type !== 'divider' && !content) continue
    if (type === 'divider' && out.length && out[out.length - 1].type === 'divider') continue
    out.push({
      id: b.id || genId(idPrefix, index),
      type,
      content: type === 'divider' ? '' : content,
      props: b.props && typeof b.props === 'object' ? { ...b.props } : {},
    })
    index += 1
  }
  // 首尾不要 divider
  while (out.length && out[0].type === 'divider') out.shift()
  while (out.length && out[out.length - 1].type === 'divider') out.pop()
  return out
}

/**
 * 章节写入用：解析正文格式，并保证有章节标题块。
 * 若正文开头已是同名标题，不再重复插入。
 */
export function prepareChapterBlocks(
  content: string,
  chapterTitle: string,
  idPrefix = 'chapter'
): Block[] {
  const blocks = parseFormattedTextToBlocks(content, idPrefix)
  const title = (chapterTitle || '').trim()
  if (!title) return blocks

  const norm = (s: string) => s.replace(/\s+/g, '')
  const first = blocks[0]
  if (
    first &&
    (first.type === 'heading' || first.type === 'subheading') &&
    norm(first.content) === norm(title)
  ) {
    return blocks
  }

  return [
    {
      id: genId(`${idPrefix}-h`, 0),
      type: 'heading',
      content: title,
      props: { level: 2 },
    },
    ...blocks,
  ]
}
