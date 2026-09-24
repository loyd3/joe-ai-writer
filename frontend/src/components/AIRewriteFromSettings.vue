<template>
  <div class="rewrite-from-settings">
    <div class="header">
      <h3>
        <el-icon><RefreshRight /></el-icon>
        设定变更后同步正文
      </h3>
      <p class="subtitle">
        项目已经写了很多、又改了设定？选「重建文稿」：按新设定重梳大纲，再生成新章节；旧稿可归档保留。
      </p>
    </div>

    <el-radio-group v-model="action" class="action-switch" :disabled="busy">
      <el-radio-button value="rebuild">重建文稿（推荐）</el-radio-button>
      <el-radio-button value="rewrite">对齐重写旧章</el-radio-button>
    </el-radio-group>

    <!-- ===== 重建 ===== -->
    <el-form v-if="action === 'rebuild'" label-position="top" class="form">
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="流程：读旧稿要点 → 按新设定重梳大纲并写回设定 → 生成新文档；旧文档默认归档到「设定变更前旧稿」"
        style="margin-bottom: 14px"
      />

      <el-form-item label="目标章数">
        <el-slider v-model="chapterCount" :min="3" :max="20" :step="1" show-stops show-input />
      </el-form-item>

      <el-form-item label="每章约字数">
        <el-select v-model="wordsPerChapter" style="width: 100%">
          <el-option label="约 1000 字" :value="1000" />
          <el-option label="约 1500 字" :value="1500" />
          <el-option label="约 2000 字" :value="2000" />
          <el-option label="约 3000 字" :value="3000" />
        </el-select>
      </el-form-item>

      <el-form-item label="旧文档处理">
        <el-radio-group v-model="archiveOld">
          <el-radio :value="true">归档保留（推荐）</el-radio>
          <el-radio :value="false">直接删除旧稿</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="额外要求（可选）">
        <el-input
          v-model="customInstruction"
          type="textarea"
          :rows="2"
          :disabled="busy"
          placeholder="例如：主线改为复仇线；保留旧稿里的感情线；不要再用旧魔法体系"
        />
      </el-form-item>

      <el-button type="primary" size="large" class="full-btn" :loading="busy" @click="startRebuild">
        {{ busy ? '重建中…' : '开始重建大纲并生成文档' }}
      </el-button>
    </el-form>

    <!-- ===== 对齐重写 ===== -->
    <el-form v-else label-position="top" class="form">
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        title="在原有章节上按新设定改写正文（不改变章节结构）。大改设定请用「重建文稿」。"
        style="margin-bottom: 14px"
      />

      <el-form-item label="重写范围">
        <el-radio-group v-model="scope" :disabled="busy">
          <el-radio value="current" :disabled="!documentId">当前文档</el-radio>
          <el-radio value="selected">选择章节</el-radio>
          <el-radio value="all">项目全部文档</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item v-if="scope === 'selected'" label="选择要重写的文档">
        <el-checkbox-group v-model="selectedIds" class="doc-checks">
          <el-checkbox
            v-for="d in documents"
            :key="d.id"
            :value="d.id"
            :label="d.title || `文档 ${d.id}`"
          />
        </el-checkbox-group>
      </el-form-item>

      <el-form-item label="重写模式">
        <el-select v-model="rewriteMode" style="width: 100%" :disabled="busy">
          <el-option v-for="m in modes" :key="m.value" :label="m.label" :value="m.value">
            <div class="mode-opt">
              <span>{{ m.label }}</span>
              <small>{{ m.desc }}</small>
            </div>
          </el-option>
        </el-select>
      </el-form-item>

      <el-form-item label="额外要求（可选）">
        <el-input v-model="customInstruction" type="textarea" :rows="2" :disabled="busy" />
      </el-form-item>

      <el-button type="primary" size="large" class="full-btn" :loading="busy" @click="startRewrite">
        {{ busy ? '重写中…' : '开始对齐重写' }}
      </el-button>
    </el-form>

    <div v-if="progressLogs.length || statusMessage" class="progress">
      <p class="status">{{ statusMessage }}</p>
      <ul>
        <li v-for="(log, i) in progressLogs" :key="i">{{ log }}</li>
      </ul>
      <div v-if="outlinePreview.length" class="outline-preview">
        <h4>新大纲</h4>
        <ol>
          <li v-for="(o, i) in outlinePreview" :key="i">
            <strong>{{ o.title }}</strong>
            <span v-if="o.description"> — {{ o.description }}</span>
          </li>
        </ol>
      </div>
      <div v-if="streamingPreview" class="stream-preview">
        <h4>当前输出预览</h4>
        <pre>{{ streamingPreview }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { RefreshRight } from '@element-plus/icons-vue'
import { aiApi, documentApi } from '@/api'
import { useProjectStore } from '@/stores/project'

const props = defineProps<{
  projectId: number
  documentId?: number
}>()

const emit = defineEmits<{
  (e: 'done', payload: { documentIds: number[]; rebuilt?: boolean }): void
}>()

const store = useProjectStore()

const action = ref<'rebuild' | 'rewrite'>('rebuild')
const modes = [
  { value: 'align', label: '对齐修正（推荐）', desc: '保情节，修冲突设定' },
  { value: 'characters', label: '角色对齐', desc: '重点改人名/性格/对白' },
  { value: 'world', label: '世界观对齐', desc: '重点改背景/规则描写' },
  { value: 'style', label: '文风对齐', desc: '重点改语气与节奏' },
  { value: 'full', label: '完整重写', desc: '可大幅改写表述' },
]

const scope = ref<'current' | 'selected' | 'all'>(props.documentId ? 'current' : 'all')
const rewriteMode = ref('align')
const customInstruction = ref('')
const chapterCount = ref(6)
const wordsPerChapter = ref(1500)
const archiveOld = ref(true)
const documents = ref<Array<{ id: number; title: string }>>([])
const selectedIds = ref<number[]>([])
const busy = ref(false)
const statusMessage = ref('')
const progressLogs = ref<string[]>([])
const streamingPreview = ref('')
const outlinePreview = ref<Array<{ title: string; description?: string }>>([])
const doneDocIds = ref<number[]>([])

watch(
  () => props.documentId,
  (id) => {
    if (id) scope.value = 'current'
  }
)

onMounted(() => loadDocuments())

async function loadDocuments() {
  try {
    const res = await documentApi.list(props.projectId)
    documents.value = (res.data || []).map((d: any) => ({
      id: d.id,
      title: d.title || `文档 ${d.id}`,
    }))
  } catch {
    documents.value = []
  }
}

function resolveDocIds(): number[] {
  if (scope.value === 'current') {
    if (!props.documentId) {
      ElMessage.warning('当前没有打开的文档')
      return []
    }
    return [props.documentId]
  }
  if (scope.value === 'selected') {
    if (!selectedIds.value.length) {
      ElMessage.warning('请先勾选要重写的文档')
      return []
    }
    return [...selectedIds.value]
  }
  return documents.value.map((d) => d.id)
}

function resetProgress() {
  statusMessage.value = '准备中…'
  progressLogs.value = []
  streamingPreview.value = ''
  outlinePreview.value = []
  doneDocIds.value = []
}

async function consumeSse(
  res: Response,
  onEvent: (evt: any) => void
) {
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || '请求失败')
  }
  const reader = res.body?.getReader()
  const decoder = new TextDecoder()
  if (!reader) throw new Error('无法读取响应')

  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const raw of lines) {
      const line = raw.trim()
      if (!line.startsWith('data: ')) continue
      const data = line.slice(6).trim()
      if (!data || data === '[DONE]') continue
      try {
        onEvent(JSON.parse(data))
      } catch {
        // ignore
      }
    }
  }
}

async function startRebuild() {
  try {
    await ElMessageBox.confirm(
      archiveOld.value
        ? `将按新设定重梳约 ${chapterCount.value} 章大纲，生成新文档，并把旧稿归档。是否继续？`
        : `将按新设定重梳约 ${chapterCount.value} 章大纲并生成新文档，旧稿会被删除。是否继续？`,
      '确认重建文稿',
      { type: 'warning', confirmButtonText: '开始重建', cancelButtonText: '取消' }
    )
  } catch {
    return
  }

  busy.value = true
  resetProgress()
  try {
    const res = await aiApi.rebuildFromMemoryStream({
      project_id: props.projectId,
      chapter_count: chapterCount.value,
      words_per_chapter: wordsPerChapter.value,
      custom_instruction: customInstruction.value.trim() || undefined,
      archive_old_docs: archiveOld.value,
      update_outline: true,
    })

    let completed = false
    await consumeSse(res, (evt) => {
      if (evt.message) {
        statusMessage.value = evt.message
        if (evt.type !== 'content') {
          progressLogs.value = [...progressLogs.value, evt.message].slice(-40)
        }
      }
      if (evt.type === 'outline_ready' && Array.isArray(evt.outline)) {
        outlinePreview.value = evt.outline
      }
      if (evt.type === 'doc_start') streamingPreview.value = ''
      if (evt.type === 'content' && evt.chunk) {
        streamingPreview.value = (streamingPreview.value + evt.chunk).slice(-1200)
      }
      if (evt.type === 'doc_done' && evt.document_id) {
        doneDocIds.value.push(evt.document_id)
      }
      if (evt.type === 'error' && evt.message) ElMessage.error(evt.message)
      if (evt.type === 'complete') {
        completed = true
        ElMessage.success(evt.message || '重建完成')
        emit('done', { documentIds: [...doneDocIds.value], rebuilt: true })
      }
    })

    if (completed) {
      try {
        await store.fetchProject(props.projectId)
      } catch {
        // ignore
      }
      await loadDocuments()
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '重建失败')
  } finally {
    busy.value = false
  }
}

async function startRewrite() {
  const ids = resolveDocIds()
  if (!ids.length) {
    if (scope.value === 'all') ElMessage.warning('项目下没有文档可重写')
    return
  }
  try {
    await ElMessageBox.confirm(
      `将按最新设定对齐重写 ${ids.length} 篇文档并覆盖原文，是否继续？`,
      '确认对齐重写',
      { type: 'warning', confirmButtonText: '开始重写', cancelButtonText: '取消' }
    )
  } catch {
    return
  }

  busy.value = true
  resetProgress()
  try {
    const res = await aiApi.rewriteFromMemoryStream({
      project_id: props.projectId,
      document_ids: ids,
      rewrite_mode: rewriteMode.value,
      custom_instruction: customInstruction.value.trim() || undefined,
      apply_to_documents: true,
    })

    await consumeSse(res, (evt) => {
      if (evt.message) {
        statusMessage.value = evt.message
        if (evt.type !== 'content') {
          progressLogs.value = [...progressLogs.value, evt.message].slice(-30)
        }
      }
      if (evt.type === 'doc_start') streamingPreview.value = ''
      if (evt.type === 'content' && evt.chunk) {
        streamingPreview.value = (streamingPreview.value + evt.chunk).slice(-1200)
      }
      if (evt.type === 'doc_done' && evt.document_id) doneDocIds.value.push(evt.document_id)
      if (evt.type === 'error' && evt.message) ElMessage.error(evt.message)
      if (evt.type === 'complete') {
        ElMessage.success(evt.message || '重写完成')
        emit('done', { documentIds: [...doneDocIds.value], rebuilt: false })
      }
    })
  } catch (e: any) {
    ElMessage.error(e?.message || '重写失败')
  } finally {
    busy.value = false
  }
}
</script>

<style scoped lang="scss">
.rewrite-from-settings {
  padding: 8px 4px 20px;
}

.header {
  margin-bottom: 14px;
  h3 {
    margin: 0 0 6px;
    font-size: 17px;
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--coffee-text);
  }
  .subtitle {
    margin: 0;
    font-size: 13px;
    line-height: 1.55;
    color: var(--coffee-text-muted);
  }
}

.action-switch {
  margin-bottom: 16px;
  width: 100%;
  :deep(.el-radio-button) {
    flex: 1;
  }
  :deep(.el-radio-button__inner) {
    width: 100%;
  }
}

.form {
  margin-bottom: 16px;
}

.doc-checks {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 180px;
  overflow-y: auto;
}

.mode-opt {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
  small {
    color: var(--el-text-color-secondary);
    font-size: 12px;
  }
}

.full-btn {
  width: 100%;
}

.progress {
  margin-top: 16px;
  padding: 12px;
  border-radius: 8px;
  background: var(--coffee-bg-warm);
  border: 1px solid var(--coffee-border);

  .status {
    margin: 0 0 8px;
    font-weight: 600;
    color: var(--coffee-primary);
    font-size: 14px;
  }

  ul {
    margin: 0;
    padding-left: 18px;
    max-height: 140px;
    overflow-y: auto;
    font-size: 12px;
    color: var(--coffee-text-muted);
    line-height: 1.7;
  }
}

.outline-preview {
  margin-top: 10px;
  h4 {
    margin: 0 0 6px;
    font-size: 13px;
  }
  ol {
    margin: 0;
    padding-left: 18px;
    font-size: 12px;
    color: var(--coffee-text-secondary);
    line-height: 1.6;
  }
}

.stream-preview {
  margin-top: 10px;
  h4 {
    margin: 0 0 6px;
    font-size: 13px;
  }
  pre {
    margin: 0;
    max-height: 160px;
    overflow: auto;
    white-space: pre-wrap;
    word-break: break-word;
    font-size: 12px;
    line-height: 1.5;
    color: var(--coffee-text-secondary);
  }
}
</style>
