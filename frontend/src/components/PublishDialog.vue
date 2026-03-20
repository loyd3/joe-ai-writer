<template>
  <el-dialog
    v-model="visible"
    title="发布到自媒体平台"
    width="720px"
    :close-on-click-modal="false"
    class="publish-dialog"
    @close="handleClose"
  >
    <!-- 平台选择网格 -->
    <div v-if="currentStep === 'select'" class="platform-grid">
      <div
        v-for="p in platforms"
        :key="p.id"
        class="platform-card"
        :class="{ selected: selectedPlatform?.id === p.id }"
        @click="selectPlatform(p)"
      >
        <div class="platform-icon" :style="{ background: p.color }">
          <span class="icon-text">{{ p.name.charAt(0) }}</span>
        </div>
        <div class="platform-info">
          <span class="platform-name">{{ p.name }}</span>
          <span class="platform-desc">{{ p.description }}</span>
        </div>
        <el-tag v-if="p.supports_api" type="success" size="small" class="api-tag">API</el-tag>
        <el-tag v-else type="info" size="small" class="api-tag">复制</el-tag>
      </div>
    </div>

    <!-- 内容预览与操作 -->
    <div v-if="currentStep === 'preview'" class="preview-step">
      <div class="preview-header">
        <el-button link @click="currentStep = 'select'">
          <el-icon><ArrowLeft /></el-icon> 返回选择
        </el-button>
        <div class="platform-badge" :style="{ background: selectedPlatform?.color }">
          {{ selectedPlatform?.name }}
        </div>
      </div>

      <el-skeleton v-if="formatting" :rows="8" animated />

      <template v-else-if="formattedContent">
        <el-form label-position="top" class="preview-form">
          <el-form-item v-if="formattedContent.title" label="标题">
            <el-input v-model="editableTitle" maxlength="100" show-word-limit />
          </el-form-item>

          <el-form-item label="正文内容">
            <div class="content-toolbar">
              <span class="char-info">
                {{ formattedContent.char_count?.toLocaleString() }} 字
                <el-tag
                  v-if="formattedContent.over_limit"
                  type="danger"
                  size="small"
                >超出限制</el-tag>
              </span>
              <span class="content-type">{{ contentTypeLabel }}</span>
            </div>
            <el-input
              v-model="editableContent"
              type="textarea"
              :rows="12"
              class="content-textarea"
            />
          </el-form-item>

          <el-form-item v-if="formattedContent.tags?.length" label="推荐标签">
            <div class="tag-list">
              <el-tag v-for="tag in formattedContent.tags" :key="tag" size="small" class="tag-item">
                {{ tag }}
              </el-tag>
            </div>
          </el-form-item>

          <el-alert
            v-if="formattedContent.tips"
            :title="formattedContent.tips"
            type="info"
            show-icon
            :closable="false"
            class="tips-alert"
          />

          <!-- 微信公众号特有配置 -->
          <template v-if="selectedPlatform?.id === 'wechat' && props.documentId">
            <el-divider>公众号发布设置</el-divider>
            <el-form-item label="作者">
              <el-input v-model="wechatConfig.author" placeholder="作者名称" />
            </el-form-item>
            <el-form-item label="摘要">
              <el-input v-model="wechatConfig.digest" type="textarea" :rows="2" placeholder="文章摘要" />
            </el-form-item>
            <el-form-item>
              <el-checkbox v-model="wechatConfig.needOpenComment">开启评论</el-checkbox>
              <el-checkbox v-model="wechatConfig.onlyFansCanComment">仅粉丝可评论</el-checkbox>
            </el-form-item>
          </template>
        </el-form>
      </template>

      <el-result v-else-if="formatError" icon="error" :title="formatError">
        <template #extra>
          <el-button type="primary" @click="doFormat">重试</el-button>
        </template>
      </el-result>
    </div>

    <!-- 发布成功 -->
    <div v-if="currentStep === 'done'" class="done-step">
      <el-result icon="success" title="操作完成" :sub-title="doneMessage" />
    </div>

    <template #footer>
      <div class="dialog-footer" v-if="currentStep === 'select'">
        <el-button @click="visible = false">关闭</el-button>
        <el-button
          type="primary"
          :disabled="!selectedPlatform"
          @click="doFormat"
        >
          下一步：预览内容
        </el-button>
      </div>

      <div class="dialog-footer" v-if="currentStep === 'preview' && formattedContent">
        <el-button @click="currentStep = 'select'">返回</el-button>

        <el-button type="success" @click="copyContent">
          <el-icon><DocumentCopy /></el-icon>
          一键复制
        </el-button>

        <el-button
          v-if="selectedPlatform?.id === 'wechat' && props.documentId"
          type="warning"
          :loading="publishing"
          @click="publishToWechat(false)"
        >
          <el-icon><Promotion /></el-icon>
          保存为草稿
        </el-button>

        <el-button
          v-if="selectedPlatform?.id === 'wechat' && props.documentId"
          type="danger"
          :loading="publishing"
          @click="publishToWechat(true)"
        >
          <el-icon><Promotion /></el-icon>
          立即发布
        </el-button>

        <el-button
          v-if="selectedPlatform && !selectedPlatform.supports_api"
          type="primary"
          @click="openPlatform"
        >
          <el-icon><Link /></el-icon>
          打开{{ selectedPlatform.name }}
        </el-button>
      </div>

      <div class="dialog-footer" v-if="currentStep === 'done'">
        <el-button @click="currentStep = 'select'">继续发布其他平台</el-button>
        <el-button type="primary" @click="visible = false">完成</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { publishApi } from '@/api'
import {
  ArrowLeft, DocumentCopy, Promotion, Link
} from '@element-plus/icons-vue'

interface Platform {
  id: string
  name: string
  icon: string
  color: string
  max_title_len: number
  max_content_len: number | null
  supports_api: boolean
  post_url: string
  description: string
}

const props = defineProps<{
  modelValue: boolean
  documentId?: number
  rawTitle?: string
  rawContent?: string
  rawBlocks?: any[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const currentStep = ref<'select' | 'preview' | 'done'>('select')
const platforms = ref<Platform[]>([])
const selectedPlatform = ref<Platform | null>(null)
const formatting = ref(false)
const formatError = ref('')
const publishing = ref(false)
const doneMessage = ref('')

const formattedContent = ref<any>(null)
const editableTitle = ref('')
const editableContent = ref('')

const wechatConfig = ref({
  author: '',
  digest: '',
  needOpenComment: true,
  onlyFansCanComment: false,
})

const contentTypeLabel = computed(() => {
  const t = formattedContent.value?.content_type
  if (t === 'html') return 'HTML'
  if (t === 'markdown') return 'Markdown'
  return '纯文本'
})

watch(visible, async (val) => {
  if (val && platforms.value.length === 0) {
    await loadPlatforms()
  }
  if (val) {
    currentStep.value = 'select'
    selectedPlatform.value = null
    formattedContent.value = null
  }
})

async function loadPlatforms() {
  try {
    const res = await publishApi.getPlatforms()
    platforms.value = res.data.platforms
  } catch {
    ElMessage.error('获取平台列表失败')
  }
}

function selectPlatform(p: Platform) {
  selectedPlatform.value = p
}

async function doFormat() {
  if (!selectedPlatform.value) return
  formatting.value = true
  formatError.value = ''
  currentStep.value = 'preview'

  try {
    const payload: any = { platform_id: selectedPlatform.value.id }
    if (props.documentId) {
      payload.document_id = props.documentId
    } else {
      payload.raw_title = props.rawTitle || '未命名文章'
      payload.raw_content = props.rawContent || ''
      if (props.rawBlocks) payload.raw_blocks = props.rawBlocks
    }
    const res = await publishApi.formatForPlatform(payload)
    formattedContent.value = res.data
    editableTitle.value = res.data.title || ''
    editableContent.value = res.data.content || ''

    if (selectedPlatform.value.id === 'wechat' && res.data.digest) {
      wechatConfig.value.digest = res.data.digest
    }
  } catch (e: any) {
    formatError.value = e?.response?.data?.detail || e?.message || '格式化失败'
  } finally {
    formatting.value = false
  }
}

async function copyContent() {
  try {
    const text = editableTitle.value
      ? `${editableTitle.value}\n\n${editableContent.value}`
      : editableContent.value
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch {
    const ta = document.createElement('textarea')
    ta.value = editableTitle.value
      ? `${editableTitle.value}\n\n${editableContent.value}`
      : editableContent.value
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    ElMessage.success('已复制到剪贴板')
  }
}

function openPlatform() {
  if (selectedPlatform.value?.post_url) {
    window.open(selectedPlatform.value.post_url, '_blank')
  }
}

async function publishToWechat(publishNow: boolean) {
  if (!props.documentId) {
    ElMessage.warning('请先保存文档后再使用API发布')
    return
  }
  publishing.value = true
  try {
    const res = await publishApi.wechatDraft({
      document_id: props.documentId,
      title: editableTitle.value,
      author: wechatConfig.value.author,
      digest: wechatConfig.value.digest,
      need_open_comment: wechatConfig.value.needOpenComment,
      only_fans_can_comment: wechatConfig.value.onlyFansCanComment,
      publish_now: publishNow,
      mock_mode: false,
    })
    if (res.data.success) {
      doneMessage.value = publishNow
        ? '文章已提交发布！请到公众号后台查看'
        : `草稿已创建！Media ID: ${res.data.draft?.media_id}`
      currentStep.value = 'done'
    }
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    ElMessage.error(typeof detail === 'string' ? detail : '发布失败，请检查公众号配置')
  } finally {
    publishing.value = false
  }
}

function handleClose() {
  currentStep.value = 'select'
  formattedContent.value = null
  formatError.value = ''
}
</script>

<style scoped lang="scss">
.publish-dialog {
  :deep(.el-dialog__body) {
    padding: 16px 24px;
    max-height: 65vh;
    overflow-y: auto;
  }
}

.platform-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.platform-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 2px solid var(--el-border-color-light);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.25s ease;
  position: relative;

  &:hover {
    border-color: var(--el-color-primary-light-5);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    transform: translateY(-2px);
  }

  &.selected {
    border-color: var(--el-color-primary);
    background: var(--el-color-primary-light-9);
    box-shadow: 0 4px 16px rgba(var(--el-color-primary-rgb), 0.15);
  }

  .platform-icon {
    width: 42px;
    height: 42px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;

    .icon-text {
      font-size: 18px;
      font-weight: 700;
      color: #fff;
    }
  }

  .platform-info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .platform-name {
    font-size: 15px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }

  .platform-desc {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .api-tag {
    position: absolute;
    top: 8px;
    right: 8px;
  }
}

.preview-step {
  .preview-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
  }

  .platform-badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    color: #fff;
    font-size: 13px;
    font-weight: 600;
  }
}

.preview-form {
  .content-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
    font-size: 13px;
    color: var(--el-text-color-secondary);
  }

  .content-type {
    padding: 2px 8px;
    background: var(--el-fill-color-light);
    border-radius: 4px;
    font-size: 12px;
  }

  .content-textarea {
    :deep(.el-textarea__inner) {
      font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
      font-size: 13px;
      line-height: 1.7;
    }
  }

  .tag-list {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;

    .tag-item {
      cursor: pointer;
      &:hover { opacity: 0.8; }
    }
  }

  .tips-alert {
    margin-bottom: 12px;
  }
}

.done-step {
  padding: 20px 0;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

@media (max-width: 640px) {
  .platform-grid {
    grid-template-columns: 1fr;
  }
}
</style>
