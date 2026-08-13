<template>
  <div class="export-menu">
    <el-dropdown v-if="showButton" trigger="click" placement="bottom-end" popper-class="coffee-dropdown" @command="handleExport">
      <el-button :class="buttonClass">
        <el-icon><Download /></el-icon>
        <span>导出</span>
        <el-icon class="arrow-icon"><ArrowDown /></el-icon>
      </el-button>
      <template #dropdown>
        <el-dropdown-menu class="coffee-dropdown-menu">
          <template v-if="mode === 'project'">
            <el-dropdown-item command="project">
              <div class="dd-item">
                <span class="dd-icon"><el-icon><Folder /></el-icon></span>
                <div class="dd-meta">
                  <span class="dd-title">导出整个项目</span>
                  <span class="dd-desc">Markdown，包含所有文档</span>
                </div>
              </div>
            </el-dropdown-item>
            <el-dropdown-item command="project-json">
              <div class="dd-item">
                <span class="dd-icon"><el-icon><Folder /></el-icon></span>
                <div class="dd-meta">
                  <span class="dd-title">导出为项目包</span>
                  <span class="dd-desc">JSON，可导入为新项目</span>
                </div>
              </div>
            </el-dropdown-item>
          </template>
          <template v-else>
            <el-dropdown-item command="markdown">
              <div class="dd-item">
                <span class="dd-icon"><el-icon><Document /></el-icon></span>
                <div class="dd-meta">
                  <span class="dd-title">Markdown</span>
                  <span class="dd-desc">通用标记格式</span>
                </div>
              </div>
            </el-dropdown-item>
            <el-dropdown-item command="pdf">
              <div class="dd-item">
                <span class="dd-icon"><el-icon><Collection /></el-icon></span>
                <div class="dd-meta">
                  <span class="dd-title">PDF</span>
                  <span class="dd-desc">适合打印和分享</span>
                </div>
              </div>
            </el-dropdown-item>
            <el-dropdown-item command="docx">
              <div class="dd-item">
                <span class="dd-icon"><el-icon><Files /></el-icon></span>
                <div class="dd-meta">
                  <span class="dd-title">Word 文档</span>
                  <span class="dd-desc">DOCX 格式，可编辑</span>
                </div>
              </div>
            </el-dropdown-item>
            <el-dropdown-item command="txt">
              <div class="dd-item">
                <span class="dd-icon"><el-icon><Document /></el-icon></span>
                <div class="dd-meta">
                  <span class="dd-title">纯文本</span>
                  <span class="dd-desc">仅导出文本内容</span>
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
    buttonClass?: string
    documentId?: number
    projectId?: number
    documentTitle?: string
    projectTitle?: string
  }>(),
  { mode: 'document', showButton: true, buttonClass: 'btn' }
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
  display: inline-flex;
  align-items: center;
}

.form-hint {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: var(--coffee-text-light);
}
</style>
