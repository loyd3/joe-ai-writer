<template>
  <div class="style-agents-panel">
    <div class="panel-toolbar">
      <p class="hint">
        为项目配置多套文风智能体。写作时可选其一；标记为「默认」的会自动注入生成请求。
      </p>
      <div class="toolbar-actions">
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

const props = defineProps<{
  projectId: number
}>()

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
      styleAgentApi.list(props.projectId),
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
    const { data: updated } = await styleAgentApi.update(props.projectId, agent.id, {
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
    const { data: created } = await styleAgentApi.fromPreset(props.projectId, key, false)
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
    const { data: created } = await styleAgentApi.create(props.projectId, {
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
    await styleAgentApi.setDefault(props.projectId, id)
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
    await styleAgentApi.delete(props.projectId, id)
    await load()
    ElMessage.success('已删除')
  } catch (e: any) {
    ElMessage.error(e?.message || '删除失败')
  }
}

onMounted(() => load())
watch(() => props.projectId, () => load())

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
