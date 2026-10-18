/** 小墨意图分流：文档页优先走项目智能体（可带编辑焦点），仅非文档场景才偏聊天助手。 */

export type XiaoMoIntent = 'assist' | 'agent'

export type XiaoMoIntentContext = {
  /** 是否已引用当前文档段落 */
  hasAttachment?: boolean
  /** 是否有浏览器选区 */
  hasSelection?: boolean
  /** 是否在文档编辑页 */
  inDocument?: boolean
}

const AGENT_PATTERNS: RegExp[] = [
  /全项目|整个项目|所有章节|所有文档|全部文档|跨章|全文排查/,
  /项目设定|改设定|丰富设定|世界观|角色卡|大纲|故事线|关键情节/,
  /所有出现|全局替换|统一改名|全文搜索|搜一下|排查一下/,
  /新建(?:一)?(?:篇|个)?文档|创建章节|拆成多章|拆分章节/,
  /梳理(?:一下)?(?:项目|设定|故事|大纲)/,
  /帮我(?:把|将).{0,20}(?:全部|所有|到处)/,
  /润色|改写|扩写|续写|缩短|加强|更顺|不通顺|这段|选中/,
]

/**
 * 根据用户输入与上下文决定走写作助手还是项目智能体。
 * 文档页默认走智能体（带焦点改稿）；非文档页仍以项目协作为主。
 */
export function resolveXiaoMoIntent(
  text: string,
  ctx: XiaoMoIntentContext = {},
): XiaoMoIntent {
  const raw = (text || '').trim()
  if (!raw) return ctx.inDocument ? 'agent' : 'assist'

  // 文档编辑页：一律走智能体，用 focus + 工具真正改稿，而不是死板的 assist 动作
  if (ctx.inDocument) return 'agent'

  if (AGENT_PATTERNS.some((re) => re.test(raw))) return 'agent'
  if (raw.length > 60) return 'agent'
  return 'assist'
}

export function intentLabel(intent: XiaoMoIntent): string {
  return intent === 'agent' ? '智能编辑' : '写作助手'
}

/** 快捷动作 → 自然语言指令（避免「润色/修改」功能腔） */
export function actionToInstruction(action: string): string {
  const map: Record<string, string> = {
    polish: '请润色这段文字，让表达更流畅自然，保留原意与语气，直接改好。',
    revise: '请改写这段文字，修正生硬或不通顺处，提升可读性，保留核心信息。',
    expand: '请在这段基础上扩写，补充细节与画面感，风格与上下文一致。',
    format_style: '请只调整这段的结构与排版层次，不要改写措辞内容本身。',
    continue: '请根据这段已有内容自然续写下一段。',
  }
  return map[action] || '请根据上下文处理这段文字，直接给出可用改稿。'
}

/** 文档页「AI 工具」→ 小墨快捷功能（展示用元数据） */
export const DOCUMENT_AI_SHORTCUTS: Array<{
  tool: string
  label: string
  description: string
}> = [
  { tool: 'format_style', label: '调整样式', description: '优化结构与排版' },
  { tool: 'generate', label: '根据设定生成', description: '用设定续写或生成' },
  { tool: 'rewrite_settings', label: '根据设定重写', description: '对齐设定改正文' },
  { tool: 'extract', label: '智能扩展', description: '扩成长篇骨架' },
  { tool: 'video_script', label: '转视频文案', description: '新建口播文案' },
  { tool: 'film_script', label: '转影视脚本', description: '新建分场剧本' },
]

/** 项目级写作能力 → 小墨快捷（独立页面仍保留） */
export const PROJECT_WRITING_SHORTCUTS: Array<{
  tool: string
  label: string
  description: string
}> = [
  { tool: 'brainstorm', label: '脑洞写作', description: '选题后写大纲与正文' },
  { tool: 'hot_topics', label: '热点写作', description: '热点选题并成文' },
  { tool: 'copywriting', label: '文案写作', description: '生成营销文案' },
  { tool: 'story', label: '故事生成', description: '生成设定并写入项目' },
]

/** 项目写作快捷 → 用户可见短句 + （系统：…）工具编排 */
export function writingToolInstruction(
  tool: string,
  projectId?: number | null,
  documentId?: number | null,
): string {
  const hasProject = !!(projectId && projectId > 0)
  const proj = hasProject ? `project_id=${projectId}` : '无项目会话'
  const bindHint = hasProject
    ? ''
    : '若尚未绑定项目，写完后先 create_project(title=…) 再 propose_*。'
  const docHint = documentId
    ? `用户打开了 document_id=${documentId}，专项写作请新建文档勿覆盖原文。`
    : ''
  const userLines: Record<string, string> = {
    brainstorm: hasProject
      ? '请帮我做脑洞写作：先选题再成文，写入项目。'
      : '请用脑洞写作帮我选题成文，并智能创建项目写入。',
    hot_topics: hasProject
      ? '请帮我做热点写作：先选题再成文，写入项目。'
      : '请用热点写作帮我选题成文，并智能创建项目写入。',
    copywriting: hasProject
      ? '请帮我生成一篇营销文案并写入项目。'
      : '请生成营销文案，并智能创建项目写入。',
    story: hasProject
      ? '请帮我生成故事设定并写入项目设定。'
      : '请生成故事设定，并智能创建项目写入设定。',
  }
  const systemNotes: Record<string, string> = {
    brainstorm:
      `${proj}。${docHint}${bindHint}先 list_brainstorm_ideas，再 brainstorm_write；` +
      `propose_writing_draft 后 finish。复杂表单可提示 /brainstorm-writing。`,
    hot_topics:
      `${proj}。${docHint}${bindHint}先 list_hot_topics，再 hot_topic_write；` +
      `propose_writing_draft 后 finish。可提示 /hot-topics。`,
    copywriting:
      `${proj}。${docHint}${bindHint}用 copywriting_write（可合理推断产品/受众/卖点）；` +
      `propose_writing_draft 后 finish。可提示 /copywriting-writing。`,
    story:
      `${proj}。${docHint}${bindHint}story_generate 后 propose_story_settings，再 finish。` +
      `可提示 /ai-story-generator。`,
  }
  const user = userLines[tool] || `请帮我完成：${tool}。`
  const note = systemNotes[tool] || `用专项写作工具完成 ${tool}，propose_* 后 finish。`
  return `${user}\n\n（系统：${note}）`
}

/** 文档快捷功能 → 用户可见短句 + （系统：…）编排说明 */
export function documentToolInstruction(
  tool: string,
  documentId?: number | null,
): string {
  const doc = documentId ? `当前打开的文档（document_id=${documentId}）` : '当前文档'
  const userLines: Record<string, string> = {
    format_style: '请帮我调整当前文档的结构与排版。',
    extract: '请基于当前文档做智能扩展，补设定并视需要新建章节。',
    generate: '请根据项目设定为当前文档续写或生成下一段。',
    rewrite_settings: '请对照项目设定重写当前文档里不一致的段落。',
    video_script: '请把当前文档改成短视频口播文案，新建一篇文档。',
    film_script: '请把当前文档改成影视分场脚本，新建一篇文档。',
  }
  const systemNotes: Record<string, string> = {
    format_style:
      `通读${doc}，只调整结构与排版层次（标题层级、分段），不要改写措辞。读一页改一页，改完 finish。`,
    extract:
      `基于${doc}做智能扩展：先 read_document / read_memory，扩成长篇骨架，` +
      `补充设定并用 propose_create_document 新建章节；有改动就提案，完成后 finish。`,
    generate:
      `先 read_memory，再为${doc}续写；用 propose_block_rewrite 或文末扩写，必要时新建章节。改完 finish。`,
    rewrite_settings:
      `先 read_memory，对照设定重写${doc}冲突段落；读一页改 1～3 块，优先 propose_block_rewrite。改完 finish。`,
    video_script:
      `阅读${doc}，改成短视频口播文案；propose_create_document 新建（标题含「视频文案」），勿覆盖原文。finish。`,
    film_script:
      `阅读${doc}，改成影视分场脚本；propose_create_document 新建（标题含「影视脚本」），勿覆盖原文。finish。`,
  }
  const user = userLines[tool] || '请根据上下文处理当前文档。'
  const note = systemNotes[tool] || actionToInstruction(tool)
  return `${user}\n\n（系统：${note}）`
}
