<template>
  <div class="version-history">
    <div class="version-header">
      <h3>
        <el-icon><Clock /></el-icon>
        版本历史
      </h3>
      <el-button type="primary" size="small" @click="saveVersion">
        <el-icon><Plus /></el-icon>
        保存版本
      </el-button>
    </div>

    <div v-if="versions.length === 0" class="empty-versions">
      <el-icon><Document /></el-icon>
      <p>暂无版本记录</p>
      <span>点击上方按钮保存当前版本</span>
    </div>

    <div v-else class="versions-timeline">
      <div
        v-for="version in versions"
        :key="version.id"
        class="version-item"
        :class="{ 'is-auto': !version.change_summary }"
      >
        <div class="version-marker"></div>
        <div class="version-content">
          <div class="version-info">
            <span class="version-number">版本 {{ version.version_number }}</span>
            <span class="version-time">{{ formatTime(version.created_at) }}</span>
          </div>
          <div class="version-title">{{ version.title }}</div>
          <div v-if="version.change_summary" class="version-summary">
            {{ version.change_summary }}
          </div>
          <div v-else class="version-auto">自动保存</div>
          <div class="version-actions">
            <el-button link size="small" @click="previewVersion(version)">
              <el-icon><View /></el-icon>
              预览
            </el-button>
            <el-button link size="small" type="primary" @click="restoreVersion(version)">
              <el-icon><RefreshLeft /></el-icon>
              恢复
            </el-button>
            <el-button link size="small" type="danger" @click="deleteVersion(version)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 保存版本对话框 -->
    <el-dialog v-model="showSaveDialog" title="保存版本" width="400px">
      <el-form>
        <el-form-item label="版本说明">
          <el-input
            v-model="versionSummary"
            type="textarea"
            placeholder="描述本次保存的主要变更..."
            rows="3"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSaveDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmSave" :loading="saving">
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 版本预览对话框 -->
    <el-dialog v-model="showPreviewDialog" title="版本预览" width="600px">
      <div v-if="previewVersionData" class="version-preview-content">
        <h4>{{ previewVersionData.title }}</h4>
        <div class="preview-blocks">
          <div
            v-for="(block, index) in previewVersionData.content"
            :key="index"
            class="preview-block"
            :class="`type-${block.type}`"
          >
            {{ block.content }}
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { versionApi } from '@/api/version'
import { Clock, Plus, Document, View, RefreshLeft, Delete } from '@element-plus/icons-vue'

const props = defineProps<{
  documentId: number
  documentTitle: string
  documentContent: any[]
}>()

const versions = ref<any[]>([])
const showSaveDialog = ref(false)
const showPreviewDialog = ref(false)
const versionSummary = ref('')
const saving = ref(false)
const previewVersionData = ref<any>(null)

onMounted(() => {
  loadVersions()
})

async function loadVersions() {
  try {
    const res = await versionApi.list(props.documentId)
    versions.value = res.data
  } catch (error) {
    ElMessage.error('加载版本历史失败')
  }
}

function formatTime(isoTime: string) {
  const date = new Date(isoTime)
  return date.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function saveVersion() {
  versionSummary.value = ''
  showSaveDialog.value = true
}

async function confirmSave() {
  saving.value = true
  try {
    await versionApi.create(props.documentId, {
      title: props.documentTitle,
      content: props.documentContent,
      change_summary: versionSummary.value
    })
    ElMessage.success('版本保存成功')
    showSaveDialog.value = false
    await loadVersions()
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

function previewVersion(version: any) {
  previewVersionData.value = version
  showPreviewDialog.value = true
}

async function restoreVersion(version: any) {
  try {
    await ElMessageBox.confirm(
      `确定要恢复到版本 ${version.version_number} 吗？当前内容将被备份。`,
      '恢复版本',
      {
        confirmButtonText: '恢复',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await versionApi.restore(version.id)
    ElMessage.success('版本恢复成功')
    emit('restored')
    await loadVersions()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('恢复失败')
    }
  }
}

async function deleteVersion(version: any) {
  try {
    await ElMessageBox.confirm(
      `确定要删除版本 ${version.version_number} 吗？`,
      '删除版本',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'danger'
      }
    )
    
    await versionApi.delete(version.id)
    ElMessage.success('版本已删除')
    await loadVersions()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const emit = defineEmits<{
  (e: 'restored'): void
}>()
</script>

<style scoped lang="scss">
.version-history {
  padding: 16px;
}

.version-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;

  h3 {
    font-size: 16px;
    color: var(--coffee-text);
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0;

    .el-icon {
      color: var(--coffee-primary);
    }
  }
}

.empty-versions {
  text-align: center;
  padding: 40px 20px;
  color: var(--coffee-text-light);

  .el-icon {
    font-size: 48px;
    margin-bottom: 12px;
    opacity: 0.5;
  }

  p {
    margin-bottom: 8px;
  }
}

.versions-timeline {
  position: relative;
  padding-left: 24px;

  &::before {
    content: '';
    position: absolute;
    left: 7px;
    top: 0;
    bottom: 0;
    width: 2px;
    background: var(--coffee-border);
  }
}

.version-item {
  position: relative;
  margin-bottom: 20px;

  &.is-auto {
    .version-marker {
      background: var(--coffee-text-light);
    }
  }
}

.version-marker {
  position: absolute;
  left: -20px;
  top: 4px;
  width: 12px;
  height: 12px;
  background: var(--coffee-primary);
  border-radius: 50%;
  border: 2px solid var(--coffee-bg-card);
}

.version-content {
  background: var(--coffee-bg-warm);
  border-radius: 10px;
  padding: 12px 16px;
}

.version-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;

  .version-number {
    font-weight: 600;
    color: var(--coffee-primary);
  }

  .version-time {
    font-size: 12px;
    color: var(--coffee-text-light);
  }
}

.version-title {
  font-weight: 500;
  color: var(--coffee-text);
  margin-bottom: 6px;
}

.version-summary {
  font-size: 13px;
  color: var(--coffee-text-secondary);
  margin-bottom: 8px;
}

.version-auto {
  font-size: 12px;
  color: var(--coffee-text-light);
  font-style: italic;
  margin-bottom: 8px;
}

.version-actions {
  display: flex;
  gap: 12px;

  .el-button {
    padding: 4px 0;
  }
}

.version-preview-content {
  h4 {
    margin-bottom: 16px;
    color: var(--coffee-text);
  }

  .preview-blocks {
    max-height: 400px;
    overflow-y: auto;
  }

  .preview-block {
    margin-bottom: 12px;
    padding: 8px;
    background: var(--coffee-bg-warm);
    border-radius: 6px;
    color: var(--coffee-text-secondary);

    &.type-heading {
      font-weight: 600;
      color: var(--coffee-text);
    }

    &.type-quote {
      border-left: 3px solid var(--coffee-primary);
      padding-left: 12px;
    }
  }
}
</style>
