<template>
  <div class="style-agents-panel">
    <div class="panel-toolbar">
      <p class="hint">
        系统级文风库，所有项目写作时可选用。标记为「默认」的会在未指定时自动注入；也可粘贴或上传多份范文自动提炼。
      </p>
      <div class="toolbar-actions">
        <el-button @click="showExtract = true">从范文提炼</el-button>
        <el-dropdown trigger="click" @command="addFromPreset">
          <el-button type="primary" plain>
            <el-icon><Plus /></el-icon> 从预设添加
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item
                v-for="p in stylePresets"
                :key="p.key"
                :command="p.key"
              >
                <div class="preset-item">
                  <strong>{{ p.name }}</strong>
                  <span>{{ p.description }}</span>
                </div>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button @click="addBlankStyleAgent">空白智能体</el-button>
      </div>
    </div>

    <el-dialog
      v-model="showExtract"
      title="从范文提炼文风"
      width="640px"
      class="coffee-dialog"
      destroy-on-close
      @closed="resetExtractForm"
    >
      <p class="extract-hint">
        可粘贴文本，或一次选择多个文件（.txt / .md / .docx / .pdf）。Word 与 PDF 由服务器解析；系统会分段采样后综合提炼文风。
      </p>
      <el-input
        v-model="extractName"
        placeholder="文风名称（可选）"
        class="coffee-input"
        style="margin-bottom: 12px"
      />
      <div class="extract-files">
        <input
          ref="fileInputRef"
          type="file"
          multiple
          accept=".txt,.md,.markdown,.text,.json,.csv,.html,.htm,.log,.docx,.pdf,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          class="file-input-hidden"
          @change="onFilesPicked"
        />
        <el-button :loading="parsingFiles" @click="triggerFilePick">选择文件（可多选）</el-button>
        <span v-if="extractFiles.length" class="file-summary">
          已选 {{ extractFiles.length }} 个 · 约 {{ extractFilesChars }} 字
        </span>
      </div>
      <ul v-if="extractFiles.length" class="file-list">
        <li v-for="(f, idx) in extractFiles" :key="f.id">
          <span class="fname" :title="f.name">{{ f.name }}</span>
          <span class="fmeta">{{ f.chars }} 字</span>
          <button type="button" class="remove-btn" @click="removeExtractFile(idx)">移除</button>
        </li>
      </ul>
      <el-input
        v-model="extractText"
        type="textarea"
        :rows="8"
        class="coffee-textarea"
        placeholder="也可在此粘贴范文（可与文件同时使用）…"
        style="margin-top: 12px"
      />
      <p class="extract-total">合计约 {{ totalExtractChars }} 字（建议 ≥ 200）</p>
      <template #footer>
        <el-button @click="showExtract = false">取消</el-button>
        <el-button type="primary" plain :loading="extracting" @click="runExtract(false)">
          提炼加入
        </el-button>
        <el-button type="primary" class="btn btn-primary" :loading="extracting" @click="runExtract(true)">
          提炼并设为默认
        </el-button>
      </template>
    </el-dialog>

    <div v-if="loading" class="empty-state">加载中…</div>
    <div v-else-if="!styleAgents.length" class="empty-state">
      暂无文风智能体，请从预设添加或创建空白智能体
    </div>
    <div v-else class="panel-body">
      <aside class="agent-list">
        <button
          v-for="agent in styleAgents"
          :key="agent.id"
          type="button"
          class="agent-item"
          :class="{ active: activeId === agent.id }"
          @click="selectAgent(agent.id)"
        >
          <span class="name">{{ agent.name }}</span>
          <el-tag v-if="agent.is_default" size="small" type="success">默认</el-tag>
          <el-tag v-if="agent.source === 'extract'" size="small" type="info">提炼</el-tag>
        </button>
      </aside>

      <div v-if="active" class="agent-editor">
        <div class="editor-head">
          <el-input
            v-model="active.name"
            placeholder="智能体名称"
            class="coffee-input name-input"
            @input="markDirty"
          />
          <el-button
            size="small"
            :disabled="active.is_default"
            @click="setDefault(active.id)"
          >
            设为默认
          </el-button>
          <el-button
            size="small"
            type="danger"
            plain
            :disabled="styleAgents.length <= 1"
            @click="removeAgent(active.id)"
          >
            删除
          </el-button>
        </div>

        <el-input
          v-model="active.description"
          type="textarea"
          :rows="2"
          placeholder="一句话定位（可选）"
          class="coffee-textarea"
          @input="markDirty"
        />

        <div class="style-grid">
          <label>
            语气
            <el-select v-model="active.config.tone" @change="markDirty">
              <el-option v-for="o in STYLE_TONES" :key="o" :label="o" :value="o" />
            </el-select>
          </label>
          <label>
            视角
            <el-select v-model="active.config.pov" @change="markDirty">
              <el-option v-for="o in STYLE_POVS" :key="o" :label="o" :value="o" />
            </el-select>
          </label>
          <label>
            节奏
            <el-select v-model="active.config.pace" @change="markDirty">
              <el-option v-for="o in STYLE_PACES" :key="o" :label="o" :value="o" />
            </el-select>
          </label>
          <label>
            句式
            <el-select v-model="active.config.sentence" @change="markDirty">
              <el-option v-for="o in STYLE_SENTENCES" :key="o" :label="o" :value="o" />
            </el-select>
          </label>
          <label>
            用词
            <el-select v-model="active.config.diction" @change="markDirty">
              <el-option v-for="o in STYLE_DICTIONS" :key="o" :label="o" :value="o" />
            </el-select>
          </label>
          <label>
            对白占比
            <el-select v-model="active.config.dialogue_ratio" @change="markDirty">
              <el-option v-for="o in STYLE_LEVELS" :key="o" :label="o" :value="o" />
            </el-select>
          </label>
          <label>
            细节浓度
            <el-select v-model="active.config.detail_level" @change="markDirty">
              <el-option v-for="o in STYLE_DETAILS" :key="o" :label="o" :value="o" />
            </el-select>
          </label>
        </div>

        <p class="field-label">额外禁忌（每行一条）</p>
        <el-input
          :model-value="(active.config.taboo || []).join('\n')"
          type="textarea"
          :rows="3"
          class="coffee-textarea"
          placeholder="例如：排比抒情"
          @update:model-value="onTabooInput"
        />

        <p class="field-label">自由补充（详细文风说明）</p>
        <el-input
          v-model="active.config.custom_text"
          type="textarea"
          :rows="8"
          class="coffee-textarea"
          placeholder="叙述视角、语言节奏、情感基调等补充说明…"
          @input="markDirty"
        />

        <p class="field-label">笔触范例（可选，每段一个范例，用空行分隔；写作时作参考）</p>
        <el-input
          :model-value="(active.config.samples || []).join('\n\n')"
          type="textarea"
          :rows="8"
          class="coffee-textarea"
          placeholder="贴一段你认可的人手写法，便于模型贴近笔触…"
          @update:model-value="onSamplesInput"
        />

        <div v-if="active.compiled_preview" class="preview-box">
          <p class="field-label">注入预览</p>
          <pre>{{ active.compiled_preview }}</pre>
        </div>

        <div class="editor-foot">
          <el-button
            type="primary"
            class="btn btn-primary"
            :loading="saving"
            :disabled="!dirty"
            @click="saveActive"
          >
            保存文风智能体
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { styleAgentApi } from '@/api'
import type { StyleAgent, StyleAgentPreset } from '@/api/types'

const STYLE_TONES = ['自然克制', '冷峻疏离', '温暖细腻', '轻松幽默', '压抑紧张', '庄重开阔']
const STYLE_POVS = ['第三人称有限', '第三人称全知', '第一人称', '第二人称']
const STYLE_PACES = ['紧凑', '适中', '舒缓', '轻快']
const STYLE_SENTENCES = ['短句为主', '长短交错', '长句可多']
const STYLE_DICTIONS = ['白话', '口语', '白话精简', '略带文学性', '书面']
const STYLE_LEVELS = ['低', '中', '高']
const STYLE_DETAILS = ['克制', '适中', '浓墨']

const styleAgents = ref<StyleAgent[]>([])
const stylePresets = ref<StyleAgentPreset[]>([])
const activeId = ref<number | null>(null)
const loading = ref(false)
const dirty = ref(false)
const saving = ref(false)

const showExtract = ref(false)
const extractText = ref('')
const extractName = ref('')
const extracting = ref(false)
const parsingFiles = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)

interface ExtractFileItem {
  id: string
  name: string
  text: string
  chars: number
}
const extractFiles = ref<ExtractFileItem[]>([])

const extractFilesChars = computed(() =>
  extractFiles.value.reduce((sum, f) => sum + f.chars, 0)
)
const totalExtractChars = computed(
  () => extractFilesChars.value + extractText.value.trim().length
)

function triggerFilePick() {
  fileInputRef.value?.click()
}

function resetExtractForm() {
  extractText.value = ''
  extractName.value = ''
  extractFiles.value = []
  if (fileInputRef.value) fileInputRef.value.value = ''
}

function removeExtractFile(idx: number) {
  extractFiles.value.splice(idx, 1)
}

function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(new Error(`读取失败：${file.name}`))
    reader.readAsText(file, 'UTF-8')
  })
}

function isBinarySample(file: File): boolean {
  const name = file.name.toLowerCase()
  return name.endsWith('.docx') || name.endsWith('.pdf')
}

function upsertExtractFile(name: string, text: string, sizeHint = 0) {
  const existIdx = extractFiles.value.findIndex((f) => f.name === name)
  const item: ExtractFileItem = {
    id: `${name}-${sizeHint}-${Date.now()}-${Math.random()}`,
    name,
    text,
    chars: text.length,
  }
  if (existIdx >= 0) extractFiles.value.splice(existIdx, 1, item)
  else extractFiles.value.push(item)
}

async function onFilesPicked(ev: Event) {
  const input = ev.target as HTMLInputElement
  const files = Array.from(input.files || [])
  if (!files.length) return

  const maxFiles = 20
  const remaining = maxFiles - extractFiles.value.length
  if (remaining <= 0) {
    ElMessage.warning(`最多同时选择 ${maxFiles} 个文件`)
    input.value = ''
    return
  }

  const picked = files.slice(0, remaining)
  const binaryFiles = picked.filter(isBinarySample)
  const textFiles = picked.filter((f) => !isBinarySample(f))

  let added = 0
  parsingFiles.value = true
  try {
    // Word / PDF → 后端解析
    if (binaryFiles.length) {
      for (const file of binaryFiles) {
        if (file.size > 8 * 1024 * 1024) {
          ElMessage.warning(`「${file.name}」超过 8MB，已跳过`)
          continue
        }
        if (file.name.toLowerCase().endsWith('.doc') && !file.name.toLowerCase().endsWith('.docx')) {
          ElMessage.warning(`「${file.name}」为旧版 .doc，请另存为 .docx`)
          continue
        }
      }
      const okBinary = binaryFiles.filter(
        (f) =>
          f.size <= 8 * 1024 * 1024 &&
          !(f.name.toLowerCase().endsWith('.doc') && !f.name.toLowerCase().endsWith('.docx'))
      )
      if (okBinary.length) {
        try {
          const { data } = await styleAgentApi.parseFiles(okBinary)
          for (const s of data.sources || []) {
            upsertExtractFile(s.name, s.text, s.chars)
            added += 1
          }
          if (data.errors?.length) {
            ElMessage.warning(data.errors.slice(0, 3).join('；'))
          }
        } catch (e: any) {
          ElMessage.error(e?.response?.data?.detail || e?.message || 'Word/PDF 解析失败')
        }
      }
    }

    // 纯文本本地读
    for (const file of textFiles) {
      if (file.size > 2_000_000) {
        ElMessage.warning(`「${file.name}」过大，已跳过（文本单文件建议 ≤ 2MB）`)
        continue
      }
      try {
        const text = (await readFileAsText(file)).trim()
        if (text.length < 20) {
          ElMessage.warning(`「${file.name}」内容过短或非文本，已跳过`)
          continue
        }
        upsertExtractFile(file.name, text, file.size)
        added += 1
      } catch (e: any) {
        ElMessage.error(e?.message || `无法读取 ${file.name}`)
      }
    }
  } finally {
    parsingFiles.value = false
  }

  if (added) ElMessage.success(`已加入 ${added} 个文件`)
  input.value = ''
}

const active = computed(() =>
  styleAgents.value.find((a) => a.id === activeId.value) || null
)

function ensureConfig(agent: StyleAgent): StyleAgent {
  const c = agent.config || ({} as any)
  return {
    ...agent,
    description: agent.description || '',
    config: {
      tone: c.tone || '自然克制',
      pov: c.pov || '第三人称有限',
      pace: c.pace || '适中',
      sentence: c.sentence || '长短交错',
      diction: c.diction || '白话',
      dialogue_ratio: c.dialogue_ratio || '中',
      detail_level: c.detail_level || '适中',
      taboo: Array.isArray(c.taboo) ? [...c.taboo] : [],
      custom_text: c.custom_text || '',
      samples: Array.isArray(c.samples) ? [...c.samples] : [],
    },
  }
}

async function load() {
  loading.value = true
  dirty.value = false
  try {
    const [agentsRes, presetsRes] = await Promise.all([
      styleAgentApi.list(),
      styleAgentApi.listPresets().catch(() => ({ data: [] as StyleAgentPreset[] })),
    ])
    const agents = Array.isArray(agentsRes?.data) ? agentsRes.data : []
    const presets = Array.isArray(presetsRes?.data) ? presetsRes.data : []
    styleAgents.value = agents.map(ensureConfig)
    stylePresets.value = presets
    const def = styleAgents.value.find((a) => a.is_default)
    activeId.value = def?.id ?? styleAgents.value[0]?.id ?? null
  } catch (e: any) {
    ElMessage.error(e?.message || '加载文风智能体失败')
  } finally {
    loading.value = false
  }
}

function selectAgent(id: number) {
  activeId.value = id
  dirty.value = false
}

function markDirty() {
  dirty.value = true
}

function onTabooInput(val: string) {
  if (!active.value) return
  active.value.config.taboo = val
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean)
  markDirty()
}

function onSamplesInput(val: string) {
  if (!active.value) return
  active.value.config.samples = val
    .split(/\n\s*\n/)
    .map((s) => s.trim())
    .filter(Boolean)
    .slice(0, 3)
  markDirty()
}

async function saveActive() {
  const agent = active.value
  if (!agent) return
  saving.value = true
  try {
    const { data: updated } = await styleAgentApi.update(agent.id, {
      name: agent.name,
      description: agent.description,
      config: agent.config,
    })
    const idx = styleAgents.value.findIndex((a) => a.id === agent.id)
    if (idx >= 0) styleAgents.value[idx] = ensureConfig(updated)
    dirty.value = false
    ElMessage.success('文风智能体已保存')
  } catch (e: any) {
    ElMessage.error(e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function addFromPreset(key: string) {
  try {
    const { data: created } = await styleAgentApi.fromPreset(key, false)
    styleAgents.value.push(ensureConfig(created))
    activeId.value = created.id
    dirty.value = false
    ElMessage.success(`已添加「${created.name}」`)
  } catch (e: any) {
    ElMessage.error(e?.message || '添加失败')
  }
}

async function addBlankStyleAgent() {
  try {
    const { data: created } = await styleAgentApi.create({
      name: '自定义文风',
      description: '',
      config: {
        tone: '自然克制',
        pov: '第三人称有限',
        pace: '适中',
        sentence: '长短交错',
        diction: '白话',
        dialogue_ratio: '中',
        detail_level: '适中',
        taboo: [],
        custom_text: '',
        samples: [],
      },
    })
    styleAgents.value.push(ensureConfig(created))
    activeId.value = created.id
    dirty.value = false
  } catch (e: any) {
    ElMessage.error(e?.message || '创建失败')
  }
}

async function setDefault(id: number) {
  try {
    await styleAgentApi.setDefault(id)
    styleAgents.value = styleAgents.value.map((a) => ({
      ...a,
      is_default: a.id === id,
    }))
    ElMessage.success('已设为默认文风')
  } catch (e: any) {
    ElMessage.error(e?.message || '设置失败')
  }
}

async function removeAgent(id: number) {
  try {
    await ElMessageBox.confirm('确定删除该文风智能体？', '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await styleAgentApi.delete(id)
    await load()
    ElMessage.success('已删除')
  } catch (e: any) {
    ElMessage.error(e?.message || '删除失败')
  }
}

async function runExtract(setAsDefault: boolean) {
  const paste = extractText.value.trim()
  const sources = extractFiles.value
    .filter((f) => f.text.trim().length > 0)
    .map((f) => ({ name: f.name, text: f.text }))

  if (!sources.length && !paste) {
    ElMessage.warning('请粘贴范文或选择至少一个文件')
    return
  }
  if (totalExtractChars.value < 80) {
    ElMessage.warning('合计请至少约 80 字以上的范文')
    return
  }
  extracting.value = true
  try {
    const { data } = await styleAgentApi.extractFromText({
      text: paste || undefined,
      sources: sources.length ? sources : undefined,
      name: extractName.value.trim() || undefined,
      save: true,
      set_default: setAsDefault,
    })
    await load()
    if (data.agent?.id) {
      activeId.value = data.agent.id
    }
    showExtract.value = false
    resetExtractForm()
    const filesHint =
      data.source_files && data.source_files > 1
        ? `，来自 ${data.source_files} 份材料`
        : ''
    ElMessage.success(
      `已提炼文风「${data.name}」（采样 ${data.source_chunks} 段${filesHint}）${
        setAsDefault ? '，并设为默认' : ''
      }`
    )
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '提炼失败')
  } finally {
    extracting.value = false
  }
}

onMounted(() => load())

defineExpose({ reload: load })
</script>

<style scoped lang="scss">
.style-agents-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--coffee-bg);
}

.panel-toolbar {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
  padding: 16px 24px;
  border-bottom: 1px solid var(--coffee-border);
  background: var(--coffee-bg-card);
}

.hint {
  flex: 1;
  min-width: 200px;
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
  color: var(--coffee-text-muted);
}

.toolbar-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.preset-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-width: 240px;
  strong { font-size: 13px; }
  span {
    font-size: 12px;
    color: var(--coffee-text-light);
    white-space: normal;
  }
}

.extract-hint {
  margin: 0 0 12px;
  font-size: 13px;
  line-height: 1.55;
  color: var(--coffee-text-muted);
}

.extract-files {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.file-input-hidden {
  display: none;
}

.file-summary {
  font-size: 12px;
  color: var(--coffee-text-muted);
}

.file-list {
  list-style: none;
  margin: 0 0 4px;
  padding: 0;
  max-height: 140px;
  overflow: auto;
  border: 1px solid var(--coffee-border);
  border-radius: 8px;
  background: var(--coffee-bg);

  li {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    border-bottom: 1px solid var(--coffee-border);
    font-size: 12px;

    &:last-child {
      border-bottom: none;
    }
  }

  .fname {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--coffee-text);
  }

  .fmeta {
    flex-shrink: 0;
    color: var(--coffee-text-muted);
  }

  .remove-btn {
    flex-shrink: 0;
    border: none;
    background: transparent;
    color: var(--coffee-text-muted);
    cursor: pointer;
    padding: 0 4px;

    &:hover {
      color: var(--el-color-danger);
    }
  }
}

.extract-total {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--coffee-text-muted);
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--coffee-text-light);
  font-size: 14px;
  padding: 48px;
}

.panel-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 220px 1fr;
  overflow: hidden;
}

.agent-list {
  overflow-y: auto;
  padding: 12px;
  border-right: 1px solid var(--coffee-border);
  background: var(--coffee-bg-card);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.agent-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  text-align: left;
  padding: 12px 14px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  color: var(--coffee-text);
  cursor: pointer;
  .name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 14px;
  }
  &:hover { background: var(--coffee-bg-warm); }
  &.active {
    background: var(--coffee-bg-warm);
    border-color: var(--coffee-primary-light);
  }
}

.agent-editor {
  overflow-y: auto;
  padding: 20px 28px 40px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.editor-head {
  display: flex;
  align-items: center;
  gap: 8px;
  .name-input { flex: 1; max-width: 360px; }
}

.field-label {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--coffee-text-muted);
}

.style-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
  label {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 12px;
    color: var(--coffee-text-muted);
  }
}

.preview-box {
  margin-top: 8px;
  padding: 12px 14px;
  border-radius: 10px;
  background: var(--coffee-bg-warm);
  border: 1px solid var(--coffee-border-light);
  pre {
    margin: 8px 0 0;
    white-space: pre-wrap;
    word-break: break-word;
    font-size: 12px;
    line-height: 1.6;
    color: var(--coffee-text-secondary);
    font-family: inherit;
  }
}

.editor-foot {
  margin-top: 8px;
}

.coffee-textarea {
  :deep(.el-textarea__inner) {
    background: var(--coffee-bg-card);
    border-color: var(--coffee-border);
    color: var(--coffee-text);
    line-height: 1.75;
    padding: 12px 14px;
    border-radius: 10px;
    &:focus { border-color: var(--coffee-primary); }
  }
}

@media (max-width: 800px) {
  .panel-body { grid-template-columns: 1fr; }
  .agent-list {
    border-right: none;
    border-bottom: 1px solid var(--coffee-border);
    flex-direction: row;
    flex-wrap: wrap;
    max-height: 140px;
  }
}
</style>
