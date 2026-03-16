<template>
  <div class="export-menu">
    <el-dropdown v-if="showButton" trigger="click" @command="handleExport">
      <el-button class="export-btn">
        <el-icon><Download /></el-icon>
        <span>导出</span>
        <el-icon class="arrow-icon"><ArrowDown /></el-icon>
      </el-button>
      <template #dropdown>
        <el-dropdown-menu class="export-dropdown">
          <!-- 项目页：仅显示导出项目 -->
          <template v-if="mode === 'project'">
            <el-dropdown-item command="project">
              <div class="export-option">
                <el-icon><Folder /></el-icon>
                <div class="option-info">
                  <span class="option-title">导出整个项目</span>
                  <span class="option-desc">Markdown 格式，包含所有文档</span>
                </div>
              </div>
            </el-dropdown-item>
            <el-dropdown-item command="project-json">
              <div class="export-option">
                <el-icon><Folder /></el-icon>
                <div class="option-info">
                  <span class="option-title">导出为项目包 (JSON)</span>
                  <span class="option-desc">可导入为新项目</span>
                </div>
              </div>
            </el-dropdown-item>
          </template>
          <!-- 文档页：仅显示文档导出，不显示导出项目 -->
          <template v-else>
            <el-dropdown-item command="markdown">
              <div class="export-option">
                <el-icon><Document /></el-icon>
                <div class="option-info">
                  <span class="option-title">Markdown</span>
                  <span class="option-desc">通用标记格式</span>
                </div>
              </div>
            </el-dropdown-item>
            <el-dropdown-item command="pdf">
              <div class="export-option">
                <el-icon><Collection /></el-icon>
                <div class="option-info">
                  <span class="option-title">PDF</span>
                  <span class="option-desc">适合打印和分享</span>
                </div>
              </div>
            </el-dropdown-item>
            <el-dropdown-item command="docx">
              <div class="export-option">
                <el-icon><Files /></el-icon>
                <div class="option-info">
                  <span class="option-title">Word 文档</span>
                  <span class="option-desc">DOCX 格式，可编辑</span>
                </div>
              </div>
            </el-dropdown-item>
            <el-dropdown-item command="txt">
              <div class="export-option">
                <el-icon><Document /></el-icon>
                <div class="option-info">
                  <span class="option-title">纯文本</span>
                  <span class="option-desc">仅文本内容</span>
                </div>
              </div>
            </el-dropdown-item>
          </template>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
    <!-- 无按钮时仅保留对话框，供外部 triggerExport 使用 -->
    
    <!-- 导出设置对话框 -->
    <el-dialog
      v-model="showSettings"
      title="导出设置"
      width="400px"
      class="coffee-dialog"
    >
      <el-form label-width="100px">
        <el-form-item label="包含项目设定">
          <el-switch v-model="includeMemory" />
          <span class="form-hint">在导出中包含项目设定内容</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSettings = false">取消</el-button>
        <el-button type="primary" @click="confirmExport" :loading="exporting">
          确认导出
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { exportApi, downloadFile } from '@/api/search-export'
import { Download, ArrowDown, Document, Folder, Collection, Files } from '@element-plus/icons-vue'

const props = withDefaults(
  defineProps<{
    mode?: 'project' | 'document'
    showButton?: boolean
    documentId?: number
    projectId?: number
    documentTitle?: string
    projectTitle?: string
  }>(),
  { mode: 'document', showButton: true }
)

const showSettings = ref(false)
const includeMemory = ref(true)
const exporting = ref(false)
const pendingCommand = ref('')

function handleExport(command: string) {
  pendingCommand.value = command
  
  if (command === 'txt') {
    // 纯文本不需要设置
    confirmExport()
  } else {
    // Markdown 或项目导出显示设置
    showSettings.value = true
  }
}

async function confirmExport() {
  exporting.value = true
  
  try {
    const command = pendingCommand.value
    let response
    let filename
    let mimeType = 'text/plain'
    
    if (command === 'markdown' && props.documentId) {
      response = await exportApi.exportDocumentMarkdown(props.documentId, includeMemory.value)
      filename = `${props.documentTitle || 'document'}.md`
      mimeType = 'text/markdown'
    } else if (command === 'pdf' && props.documentId) {
      response = await exportApi.exportDocumentPdf(props.documentId, includeMemory.value)
      filename = `${props.documentTitle || 'document'}.pdf`
      mimeType = 'application/pdf'
    } else if (command === 'docx' && props.documentId) {
      response = await exportApi.exportDocumentDocx(props.documentId, includeMemory.value)
      filename = `${props.documentTitle || 'document'}.docx`
      mimeType = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    } else if (command === 'txt' && props.documentId) {
      response = await exportApi.exportDocumentTxt(props.documentId)
      filename = `${props.documentTitle || 'document'}.txt`
      mimeType = 'text/plain'
    } else if (command === 'project' && props.projectId) {
      response = await exportApi.exportProjectMarkdown(props.projectId, includeMemory.value)
      filename = `${props.projectTitle || 'project'}.md`
      mimeType = 'text/markdown'
    } else if (command === 'project-json' && props.projectId) {
      response = await exportApi.exportProjectJson(props.projectId, includeMemory.value)
      filename = `${props.projectTitle || 'project'}.json`
      mimeType = 'application/json'
    } else {
      ElMessage.error('导出参数错误')
      return
    }
    
    // 下载文件
    downloadFile(response.data, filename, mimeType)
    ElMessage.success('导出成功')
    showSettings.value = false
  } catch (error) {
    ElMessage.error('导出失败')
    console.error('Export error:', error)
  } finally {
    exporting.value = false
  }
}

defineExpose({
  triggerExport(command: string) {
    handleExport(command)
  }
})
</script>

<style scoped lang="scss">
.export-menu {
  display: inline-block;
}

.export-btn {
  height: 40px;
  padding: 0 16px;
  border-radius: 8px;
  border-color: var(--coffee-border);
  color: var(--coffee-text-secondary);
  background: var(--coffee-bg-card);
  
  &:hover {
    border-color: var(--coffee-primary);
    color: var(--coffee-primary);
    background: var(--coffee-sidebar-shadow);
  }
  
  .el-icon {
    margin-right: 6px;
  }
  
  .arrow-icon {
    margin-left: 6px;
    margin-right: 0;
    font-size: 12px;
  }
}

.export-dropdown {
  .el-dropdown-menu__item {
    padding: 0;
  }
}

.export-option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  min-width: 200px;
  
  .el-icon {
    font-size: 20px;
    color: var(--coffee-primary);
  }
  
  .option-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
    
    .option-title {
      font-size: 14px;
      font-weight: 500;
      color: var(--coffee-text);
    }
    
    .option-desc {
      font-size: 12px;
      color: var(--coffee-text-light);
    }
  }
}

.form-hint {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: var(--coffee-text-light);
}
</style>
