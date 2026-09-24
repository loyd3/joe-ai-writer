/** 项目设定结构化数据规范化（兼容旧格式） */

export interface StoryStage {
  title: string
  summary: string
}

export interface StorylineData {
  summary: string
  stages: StoryStage[]
}

export interface KeyPointItem {
  title: string
  summary: string
}

export interface WorldItem {
  title: string
  content: string
}

export interface WorldCategory {
  name: string
  items: WorldItem[]
}

export interface WorldBuildingData {
  categories: WorldCategory[]
}

export interface CharacterCard {
  name: string
  description: string
  personality?: string
  background?: string
  goals?: string
  role?: string
  avatar?: string
  color?: string
}

export const DEFAULT_WORLD_CATEGORIES = [
  '时代背景',
  '地理环境',
  '力量/规则',
  '社会结构',
  '文化习俗',
  '其他设定'
]

export const CHAR_ROLES = ['主角', '重要配角', '反派', '配角', '其他']

export const CHAR_COLORS = [
  '#c4a574',
  '#7a9e7e',
  '#6b8cae',
  '#b87a7a',
  '#8b7aad',
  '#c49a6c',
  '#5a8a8a',
  '#a67c52'
]

export function normalizeStoryline(raw: any): StorylineData {
  if (raw == null || raw === '') return { summary: '', stages: [] }
  if (typeof raw === 'string') {
    const s = raw.trim()
    if (s.startsWith('{')) {
      try {
        return normalizeStoryline(JSON.parse(s))
      } catch {
        return { summary: raw, stages: [] }
      }
    }
    return { summary: raw, stages: [] }
  }
  if (Array.isArray(raw)) {
    return { summary: '', stages: raw.map(normalizeStage) }
  }
  if (typeof raw === 'object') {
    const stages = raw.stages || raw.nodes || []
    return {
      summary: String(raw.summary || raw.overview || ''),
      stages: Array.isArray(stages) ? stages.map(normalizeStage) : []
    }
  }
  return { summary: '', stages: [] }
}

function normalizeStage(item: any): StoryStage {
  if (typeof item === 'string') return { title: item.slice(0, 40), summary: item }
  if (item && typeof item === 'object') {
    return {
      title: String(item.title || item.name || ''),
      summary: String(item.summary || item.description || item.content || '')
    }
  }
  return { title: '', summary: '' }
}

export function normalizeKeyPoints(raw: any): KeyPointItem[] {
  if (!Array.isArray(raw)) return []
  return raw.map((item) => {
    if (typeof item === 'string') {
      return { title: item.length > 40 ? item.slice(0, 40) : item, summary: item }
    }
    if (item && typeof item === 'object') {
      const summary = String(item.summary || item.description || item.content || item.point || '')
      const title = String(item.title || item.name || '') || summary.slice(0, 40)
      return { title, summary }
    }
    return { title: '', summary: '' }
  })
}

export function normalizeCharacter(raw: any, index = 0): CharacterCard {
  if (!raw || typeof raw !== 'object') {
    return {
      name: '',
      description: '',
      personality: '',
      background: '',
      goals: '',
      role: '配角',
      avatar: '',
      color: CHAR_COLORS[index % CHAR_COLORS.length]
    }
  }
  return {
    name: String(raw.name || ''),
    description: String(raw.description || ''),
    personality: String(raw.personality || ''),
    background: String(raw.background || ''),
    goals: String(raw.goals || ''),
    role: String(raw.role || '配角'),
    avatar: String(raw.avatar || ''),
    color: String(raw.color || CHAR_COLORS[index % CHAR_COLORS.length])
  }
}

export function normalizeCharacters(raw: any): CharacterCard[] {
  if (!Array.isArray(raw)) return []
  return raw.map((c, i) => normalizeCharacter(c, i))
}

export function normalizeWorldBuilding(raw: any): WorldBuildingData {
  if (!raw) {
    return { categories: DEFAULT_WORLD_CATEGORIES.map((name) => ({ name, items: [] })) }
  }
  if (typeof raw === 'string') {
    try {
      return normalizeWorldBuilding(JSON.parse(raw))
    } catch {
      return { categories: DEFAULT_WORLD_CATEGORIES.map((name) => ({ name, items: [] })) }
    }
  }
  if (raw.categories && Array.isArray(raw.categories)) {
    const cats = raw.categories
      .filter((c: any) => c && typeof c === 'object')
      .map((c: any) => ({
        name: String(c.name || c.title || '未命名分类'),
        items: Array.isArray(c.items)
          ? c.items.map((it: any) => {
              if (typeof it === 'string') return { title: it.slice(0, 30), content: it }
              return {
                title: String(it?.title || it?.key || it?.name || ''),
                content: String(it?.content || it?.value || it?.description || '')
              }
            })
          : []
      }))
    return {
      categories: cats.length
        ? cats
        : DEFAULT_WORLD_CATEGORIES.map((name) => ({ name, items: [] }))
    }
  }
  // 旧扁平 dict
  if (typeof raw === 'object' && !Array.isArray(raw)) {
    const items = Object.entries(raw)
      .filter(([k]) => k !== 'categories')
      .map(([k, v]) => ({ title: String(k), content: v == null ? '' : String(v) }))
    return {
      categories: [
        { name: '综合设定', items },
        ...DEFAULT_WORLD_CATEGORIES
          .filter((n) => n !== '其他设定')
          .map((name) => ({ name, items: [] as WorldItem[] }))
      ]
    }
  }
  return { categories: DEFAULT_WORLD_CATEGORIES.map((name) => ({ name, items: [] })) }
}

export function charInitial(name: string) {
  const n = (name || '').trim()
  return n ? n[0]!.toUpperCase() : '?'
}

export function truncateText(text: string, max = 48) {
  const t = (text || '').replace(/\s+/g, ' ').trim()
  if (t.length <= max) return t
  return t.slice(0, max) + '…'
}
