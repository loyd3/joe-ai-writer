// API 类型定义

// 用户相关
export interface User {
  id: number
  username: string
  email: string
  is_active: boolean
  created_at: string
  avatar_url?: string
}

export interface UserProfile {
  id: number
  username: string
  email: string
  project_count: number
  created_at: string
  avatar_url?: string
}

export interface UserCreate {
  username: string
  email: string
  password: string
}

export interface ProfileUpdate {
  username?: string
  email?: string
  avatar_url?: string
}

export interface PasswordChange {
  old_password: string
  new_password: string
}

// 项目相关
export interface Project {
  id: number
  title: string
  description?: string
  owner_id: number
  created_at: string
  updated_at: string
  documents?: Document[]
  ai_memory?: AIMemory
}

export interface ProjectCreate {
  title: string
  description?: string
}

export interface ProjectUpdate {
  title?: string
  description?: string
}

// 文档相关
export interface Block {
  id: string
  type: 'paragraph' | 'heading' | 'subheading' | 'quote' | 'list' | 'code' | 'divider'
  content: string
  props?: Record<string, any>
}

export interface Document {
  id: number
  title: string
  content: Block[]
  project_id: number
  parent_id?: number
  order_index: number
  created_at: string
  updated_at: string
}

export interface DocumentCreate {
  title: string
  content?: Block[]
  parent_id?: number
}

export interface DocumentUpdate {
  title?: string
  content?: Block[]
}

// AI 记忆相关
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
  outline: Array<{ title: string; description?: string }>
  storyline?: string
  characters: Character[]
  world_building: Record<string, any>
  writing_style?: string
  key_points: string[]
  notes?: string
  updated_at: string
}

export interface AIMemoryUpdate {
  outline?: Array<{ title: string; description?: string }>
  storyline?: string
  characters?: Character[]
  world_building?: Record<string, any>
  writing_style?: string
  key_points?: string[]
  notes?: string
}

// AI 请求
export interface AIRequest {
  document_id: number
  action: 'guide' | 'revise' | 'polish' | 'continue' | 'brainstorm' | 'expand' | 'summarize'
  selected_text?: string
  instruction?: string
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export interface AIChatRequest {
  document_id: number
  messages: ChatMessage[]
  include_memory?: boolean
}

export interface AIGenerateRequest {
  project_id: number
  document_id?: number
  generate_type: 'opening' | 'continue' | 'outline_section' | 'scene' | 'custom'
  custom_instruction?: string
  current_content?: string
}

// 批量/多轮次 AI 写作
export interface OutlineNode {
  title: string
  description?: string
}

export interface AIBatchGenerateRequest {
  project_id: number
  document_id: number
  outline_nodes: OutlineNode[]
  max_tokens_per_chapter: number
  continue_on_complete: boolean
  custom_instruction?: string
}

export interface AIGenerateProgress {
  total_chapters: number
  current_chapter: number
  current_title: string
  status: 'generating' | 'completed' | 'error' | 'paused'
  generated_chars: number
  estimated_total_chars: number
  content_preview: string
}

export interface AIGenerateChunk {
  type: 'content' | 'progress' | 'chapter_complete' | 'error' | 'done'
  content?: string
  progress?: AIGenerateProgress
  chapter_index?: number
  chapter_title?: string
  chapter_content?: string  // 完整的章节内容
  chapter_chars?: number
  total_chars?: number
  error_message?: string
}

// 文学作品分析
export interface LiteraryAnalysisRequest {
  content: string
  title?: string
  author?: string
  category?: string
}

export interface LiteraryAnalysisResult {
  title: string
  description: string
  category: string
  outline: OutlineNode[]
  storyline?: string
  characters: Character[]
  world_building: Record<string, any>
  writing_style?: string
  key_points: string[]
  themes: string[]
}

/** 创建项目请求：只传解析后的设定，不传原文档 */
export interface CreateProjectFromLiteratureRequest {
  analysis: LiteraryAnalysisResult
}

export interface CreateProjectFromLiteratureResponse {
  project_id: number
  project_title: string
  analysis: LiteraryAnalysisResult
  message: string
}

// 模板
export interface Template {
  id: number
  name: string
  description?: string
  category: 'novel' | 'blog' | 'work'
  icon: string
  outline: Array<{ title: string; description?: string }>
  storyline?: string
  characters: Character[]
  world_building: Record<string, any>
  writing_style?: string
  is_system: boolean
  created_at: string
}

export interface TemplateCreate {
  name: string
  description?: string
  category: string
  icon?: string
  outline?: Array<{ title: string; description?: string }>
  storyline?: string
  characters?: Character[]
  world_building?: Record<string, any>
  writing_style?: string
}

// 文档版本
export interface DocumentVersion {
  id: number
  document_id: number
  title: string
  content: Block[]
  version_number: number
  change_summary?: string
  created_at: string
}

// 系统配置
export interface AIConfig {
  provider: 'openai' | 'deepseek' | 'siliconflow' | 'custom'
  model?: string
  api_key?: string
  base_url?: string
  temperature?: number
  max_tokens?: number
}

// 主题
export interface Theme {
  preset_id: string
  custom_color?: string
}
