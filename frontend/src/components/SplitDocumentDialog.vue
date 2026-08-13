<template>
  <el-dialog
    :model-value="modelValue"
    title="按小节拆分为多篇文档"
    width="560px"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <p class="hint">
      将当前文档按标题切成多篇，并<strong>按顺序加入项目</strong>。原文内容不变，仅调整结构归属。
    </p>

    <el-form label-position="top">
      <el-form-item label="拆分依据">
        <el-radio-group v-model="level">
          <el-radio-button label="heading">大标题（##）</el-radio-button>
          <el-radio-button label="subheading">小标题（###）</el-radio-button>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="原文档处理">
        <el-radio-group v-model="originalAction">
          <el-radio label="keep">保留原文档不动</el-radio>
          <el-radio label="stub">原文档改为目录索引</el-radio>
          <el-radio label="delete">拆分后删除原文档</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>

    <div v-if="sections.length === 0" class="empty">
      <el-empty
        :description="level === 'heading' ? '未找到大标题，请先用「大标题」标记小节' : '未找到可用的小标题/大标题'"
        :image-size="72"
      />
    </div>
    <div v-else class="preview">
      <div class="preview-title">将生成 {{ sections.length }} 篇文档（预览）</div>
      <ol class="section-list">
        <li v-for="(s, i) in sections" :key="`${s.startIndex}-${i}`">
          <span class="idx">{{ i + 1 }}.</span>
          <span class="name">{{ s.title }}</span>
          <span class="meta">{{ s.blocks.length }} 块</span>
        </li>
      </ol>
    </div>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="loading" :disabled="!sections.length" @click="confirm">
        确认拆分
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { Block, Document } from '@/api/types'
import { useProjectStore } from '@/stores/project'
import { splitBlocksByHeading, type SplitLevel } from '@/utils/splitBlocksByHeading'

const props = defineProps<{
  modelValue: boolean
  blocks: Block[]
  projectId: number
  documentId: number
  documentTitle: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'done', payload: { created: Document[]; deletedOriginal: boolean }): void
}>()

const store = useProjectStore()
const level = ref<SplitLevel>('heading')
const originalAction = ref<'keep' | 'stub' | 'delete'>('keep')
const loading = ref(false)

const sections = computed(() => splitBlocksByHeading(props.blocks || [], level.value))

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      level.value = 'heading'
      originalAction.value = 'keep'
    }
  }
)

async function confirm() {
  if (!sections.value.length || loading.value) return
  loading.value = true
  try {
    const created: Document[] = []
    for (const section of sections.value) {
      const doc = await store.createDocument(props.projectId, {
        title: section.title,
        content: section.blocks,
      })
      created.push(doc)
    }

    // 保证项目文档顺序：原列表中，当前文档之后插入新文档（或替换删除位）
    await store.fetchProject(props.projectId)
    const docs = [...(store.currentProject?.documents || [])].sort(
      (a, b) => (a.order_index ?? 0) - (b.order_index ?? 0) || a.id - b.id
    )
    const currentId = props.documentId
    const createdIds = new Set(created.map((d) => d.id))
    const withoutNew = docs.filter((d) => !createdIds.has(d.id))
    const curPos = withoutNew.findIndex((d) => d.id === currentId)
    const insertAt = curPos >= 0 ? curPos + 1 : withoutNew.length

    let orderedIds: number[]
    if (originalAction.value === 'delete') {
      const base = withoutNew.filter((d) => d.id !== currentId)
      const at = curPos >= 0 ? curPos : base.length
      orderedIds = [
        ...base.slice(0, at).map((d) => d.id),
        ...created.map((d) => d.id),
        ...base.slice(at).map((d) => d.id),
      ]
    } else {
      orderedIds = [
        ...withoutNew.slice(0, insertAt).map((d) => d.id),
        ...created.map((d) => d.id),
        ...withoutNew.slice(insertAt).map((d) => d.id),
      ]
    }

    // 补上项目中可能未出现在 withoutNew 的遗漏 id（保险）
    const known = new Set(orderedIds)
    for (const d of docs) {
      if (!known.has(d.id) && !(originalAction.value === 'delete' && d.id === currentId)) {
        orderedIds.push(d.id)
      }
    }

    await store.reorderDocuments(props.projectId, orderedIds)

    let deletedOriginal = false
    if (originalAction.value === 'stub') {
      const stubBlocks: Block[] = [
        {
          id: `${Date.now().toString(36)}-stub`,
          type: 'heading',
          content: props.documentTitle || '目录',
          props: { level: 2 },
        },
        {
          id: `${Date.now().toString(36)}-intro`,
          type: 'paragraph',
          content: '本文档已按小节拆分为以下篇章：',
          props: {},
        },
        ...created.map((d, i) => ({
          id: `${Date.now().toString(36)}-li-${i}`,
          type: 'list' as const,
          content: d.title,
          props: {},
        })),
      ]
      await store.updateDocument(currentId, { content: stubBlocks })
    } else if (originalAction.value === 'delete') {
      await store.deleteDocument(currentId)
      deletedOriginal = true
    }

    ElMessage.success(`已拆分为 ${created.length} 篇文档并加入项目`)
    emit('update:modelValue', false)
    emit('done', { created, deletedOriginal })
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '拆分失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.hint {
  margin: 0 0 16px;
  color: #606266;
  font-size: 13px;
  line-height: 1.6;
}
.empty {
  padding: 8px 0 16px;
}
.preview-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}
.section-list {
  margin: 0;
  padding: 0;
  list-style: none;
  max-height: 280px;
  overflow: auto;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}
.section-list li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid #f2f3f5;
  font-size: 13px;
}
.section-list li:last-child {
  border-bottom: none;
}
.idx {
  color: #909399;
  width: 28px;
  flex-shrink: 0;
}
.name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #303133;
}
.meta {
  color: #909399;
  flex-shrink: 0;
}
</style>
