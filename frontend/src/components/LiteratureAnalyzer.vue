<template>
  <div class="literature-analyzer">
    <div class="analyzer-header">
      <h3>
        <el-icon><Reading /></el-icon>
        文学作品分析
      </h3>
      <p class="subtitle">导入文学作品，AI 自动拆解并生成项目设定</p>
    </div>

    <!-- 步骤一：输入作品 -->
    <div v-if="step === 'input'" class="step-panel">
      <h4>导入文学作品</h4>
      
      <el-form label-position="top">
        <el-form-item label="作品信息（可选）">
          <div class="info-row">
            <el-input v-model="workInfo.title" placeholder="作品标题" class="info-input" />
            <el-input v-model="workInfo.author" placeholder="作者" class="info-input" />
            <el-select v-model="workInfo.category" placeholder="类型" class="info-select">
              <el-option label="小说" value="novel" />
              <el-option label="短篇故事" value="short_story" />
              <el-option label="散文" value="essay" />
              <el-option label="剧本" value="script" />
            </el-select>
          </div>
        </el-form-item>

        <el-form-item label="作品文本">
          <div class="upload-area">
            <el-upload
              drag
              accept=".txt,.md,.doc,.docx"
              :auto-upload="false"
              :on-change="handleFileChange"
              :show-file-list="false"
              class="file-uploader"
            >
              <el-icon class="el-icon--upload"><upload-filled /></el-icon>
              <div class="el-upload__text">
                拖拽文件到此处或 <em>点击上传</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  支持 .txt, .md, .doc, .docx 格式，文件大小不超过 10MB
                </div>
              </template>
            </el-upload>
          </div>
          
          <el-input
            v-model="content"
            type="textarea"
            :rows="12"
            placeholder="或直接粘贴作品文本内容（建议至少 1000 字以获得更好的分析效果）"
            class="content-input"
          />
          <div class="char-count" :class="{ 'is-valid': content.length >= 100 }">
            {{ content.length.toLocaleString() }} 字符
            <span v-if="content.length < 100" class="hint">（至少需要 100 字符）</span>
          </div>
        </el-form-item>
      </el-form>

      <div class="step-actions">
        <el-button @click="emit('close')">取消</el-button>
        <el-button 
          type="primary" 
          :disabled="content.length < 100 || analyzing"
          :loading="analyzing"
          @click="startAnalysis"
        >
          <el-icon><MagicStick /></el-icon>
          {{ analyzing ? '分析中...' : '开始分析' }}
        </el-button>
      </div>
    </div>

    <!-- 步骤二：分析中 -->
    <div v-if="step === 'analyzing'" class="step-panel analyzing">
      <h4>AI 正在深度分析作品...</h4>
      
      <div class="analysis-progress">
        <el-progress :percentage="analysisProgress" :stroke-width="18" status="success" />
        <p class="progress-text">{{ analysisStatus }}</p>
      </div>

      <div class="analysis-visual">
        <div class="pulse-icon">
          <el-icon :size="64" color="var(--el-color-primary)"><Reading /></el-icon>
        </div>
        <div class="analysis-steps">
          <div v-for="(step, idx) in analysisSteps" :key="idx" 
               class="step-item" 
               :class="{ active: currentStep >= idx, completed: currentStep > idx }">
            <el-icon v-if="currentStep > idx" class="completed-icon"><Check /></el-icon>
            <el-icon v-else-if="currentStep === idx" class="active-icon"><Loading /></el-icon>
            <el-icon v-else><CircleCheck /></el-icon>
            <span>{{ step }}</span>
          </div>
        </div>
      </div>

      <div class="tip-box">
        <el-icon><InfoFilled /></el-icon>
        <span>分析时间取决于作品长度，通常需要 10-30 秒</span>
      </div>
    </div>

    <!-- 步骤三：分析结果 -->
    <div v-if="step === 'result' && analysisResult" class="step-panel result">
      <div class="result-header">
        <h4>📚 {{ analysisResult.title }}</h4>
        <el-tag type="success" size="large">分析完成</el-tag>
      </div>

      <el-descriptions :column="1" border class="result-overview">
        <el-descriptions-item label="作品简介">
          {{ analysisResult.description }}
        </el-descriptions-item>
        <el-descriptions-item label="写作风格">
          {{ analysisResult.writing_style }}
        </el-descriptions-item>
        <el-descriptions-item label="核心主题">
          <el-tag v-for="theme in analysisResult.themes" :key="theme" class="theme-tag">
            {{ theme }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <el-collapse v-model="activeCollapse" class="result-collapse">
        <el-collapse-item name="outline" class="custom-collapse-item">
          <template #title>
            <div class="collapse-title">
              <el-icon><Document /></el-icon>
              <span>故事大纲 ({{ analysisResult.outline.length }} 章节)</span>
            </div>
          </template>
          <div class="outline-list">
            <div v-for="(item, idx) in analysisResult.outline" :key="idx" class="outline-item">
              <div class="outline-number">{{ idx + 1 }}</div>
              <div class="outline-content">
                <div class="outline-title">{{ item.title }}</div>
                <div class="outline-desc">{{ item.description }}</div>
              </div>
            </div>
          </div>
        </el-collapse-item>

        <el-collapse-item name="characters" class="custom-collapse-item">
          <template #title>
            <div class="collapse-title">
              <el-icon><User /></el-icon>
              <span>角色设定 ({{ analysisResult.characters.length }} 个角色)</span>
            </div>
          </template>
          <div class="characters-list">
            <el-card v-for="(char, idx) in analysisResult.characters" :key="idx" class="character-card">
              <template #header>
                <div class="character-header">
                  <span class="character-name">{{ char.name }}</span>
                </div>
              </template>
              <div class="character-body">
                <p><strong>描述：</strong>{{ char.description }}</p>
                <p><strong>性格：</strong>{{ char.personality }}</p>
                <p><strong>背景：</strong>{{ char.background }}</p>
                <p><strong>目标：</strong>{{ char.goals }}</p>
              </div>
            </el-card>
          </div>
        </el-collapse-item>

        <el-collapse-item name="world" class="custom-collapse-item">
          <template #title>
            <div class="collapse-title">
              <el-icon><OfficeBuilding /></el-icon>
              <span>世界观设定</span>
            </div>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item 
              v-for="(value, key) in analysisResult.world_building" 
              :key="key"
              :label="key"
            >
              {{ value }}
            </el-descriptions-item>
          </el-descriptions>
        </el-collapse-item>

        <el-collapse-item name="plot" class="custom-collapse-item">
          <template #title>
            <div class="collapse-title">
              <el-icon><Star /></el-icon>
              <span>关键情节点 ({{ analysisResult.key_points.length }} 个)</span>
            </div>
          </template>
          <ul class="key-points-list">
            <li v-for="(point, idx) in analysisResult.key_points" :key="idx">
              {{ point }}
            </li>
          </ul>
        </el-collapse-item>

        <el-collapse-item name="storyline" class="custom-collapse-item">
          <template #title>
            <div class="collapse-title">
              <el-icon><DocumentCopy /></el-icon>
              <span>故事主线</span>
            </div>
          </template>
          <p class="storyline-content">{{ analysisResult.storyline }}</p>
        </el-collapse-item>
      </el-collapse>

      <div class="create-project-box">
        <h5>🎯 基于此分析创建新项目</h5>
        <p>将自动创建一个包含上述设定的项目，你可以在此基础上进行二次创作</p>
        <el-button 
          type="primary" 
          size="large"
          :loading="creatingProject"
          @click="createProject"
        >
          <el-icon><Plus /></el-icon>
          {{ creatingProject ? '创建中...' : '创建项目' }}
        </el-button>
      </div>

      <div class="step-actions">
        <el-button @click="resetAndClose">关闭</el-button>
        <el-button @click="step = 'input'">重新分析</el-button>
      </div>
    </div>

    <!-- 步骤四：创建成功 -->
    <div v-if="step === 'success' && createdProject" class="step-panel success">
      <div class="success-content">
        <el-icon class="success-icon" :size="80" color="#67c23a"><CircleCheck /></el-icon>
        <h4>项目创建成功！</h4>
        <p class="success-desc">{{ createdProject.message }}</p>
        
        <el-descriptions border :column="1" class="project-summary">
          <el-descriptions-item label="项目名称">
            {{ createdProject.project_title }}
          </el-descriptions-item>
          <el-descriptions-item label="角色数量">
            {{ createdProject.analysis.characters.length }} 个
          </el-descriptions-item>
          <el-descriptions-item label="章节数量">
            {{ createdProject.analysis.outline.length }} 个
          </el-descriptions-item>
        </el-descriptions>

        <div class="action-buttons">
          <el-button type="primary" size="large" @click="goToProject">
            <el-icon><Right /></el-icon>
            进入项目
          </el-button>
          <el-button size="large" @click="resetAndClose">
            继续分析其他作品
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { aiApi } from '@/api'
import type { LiteraryAnalysisResult, CreateProjectFromLiteratureResponse } from '@/api/types'
import type { UploadFile } from 'element-plus'
import {
  Reading, UploadFilled, MagicStick, Check, Loading, CircleCheck,
  InfoFilled, Document, User, OfficeBuilding, Star, DocumentCopy, Plus, Right
} from '@element-plus/icons-vue'

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'project-created', projectId: number): void
}>()

// 步骤控制
const step = ref<'input' | 'analyzing' | 'result' | 'success'>('input')

// 作品信息
const workInfo = ref({
  title: '',
  author: '',
  category: 'novel'
})

// 作品内容（上传或粘贴的全文）
const content = ref('')
const analyzing = ref(false)
const analysisProgress = ref(0)
const analysisStatus = ref('准备分析...')
const currentStep = ref(0)
const analysisSteps = ['解析文本结构', '提取故事大纲', '分析角色设定', '构建世界观', '总结写作风格']

// 分析结果
const analysisResult = ref<LiteraryAnalysisResult | null>(null)
const activeCollapse = ref(['outline', 'characters'])

// 创建项目
const creatingProject = ref(false)
const createdProject = ref<CreateProjectFromLiteratureResponse | null>(null)

// 检测并转换编码
async function readFileWithEncoding(file: File): Promise<string> {
  const buffer = await file.arrayBuffer()
  const bytes = new Uint8Array(buffer)
  
  // 检测 UTF-8 BOM
  if (bytes.length >= 3 && bytes[0] === 0xEF && bytes[1] === 0xBB && bytes[2] === 0xBF) {
    return new TextDecoder('utf-8').decode(bytes.slice(3))
  }

  // UTF-16 LE BOM（Windows 记事本等）
  if (bytes.length >= 2 && bytes[0] === 0xFF && bytes[1] === 0xFE) {
    try {
      return new TextDecoder('utf-16le').decode(bytes.slice(2))
    } catch {
      // ignore
    }
  }

  // UTF-16 BE BOM
  if (bytes.length >= 2 && bytes[0] === 0xFE && bytes[1] === 0xFF) {
    try {
      return new TextDecoder('utf-16be').decode(bytes.slice(2))
    } catch {
      // ignore
    }
  }

  // 尝试 UTF-8
  try {
    const utf8Text = new TextDecoder('utf-8', { fatal: true }).decode(bytes)
    // 检查是否包含乱码特征
    if (!utf8Text.includes('锟斤拷') && !utf8Text.includes('\uFFFD')) {
      return utf8Text
    }
  } catch {
    // UTF-8 解码失败，继续尝试其他编码
  }
  
  // 尝试 GB18030 / GBK（兼容中文 Windows 保存的 .txt）
  for (const enc of ['gb18030', 'gbk']) {
    try {
      const decoded = new TextDecoder(enc).decode(bytes)
      if (!decoded.includes('锟斤拷') && !decoded.includes('\uFFFD')) return decoded
    } catch {
      // 浏览器不支持该编码则跳过
    }
  }

  return new TextDecoder('utf-8', { fatal: false }).decode(bytes)
}

// 处理文件上传
async function handleFileChange(file: UploadFile) {
  if (!file.raw) return
  
  const isValidType = ['text/plain', 'text/markdown', 'application/msword', 
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
    .includes(file.raw.type) || file.raw.name.endsWith('.txt') || file.raw.name.endsWith('.md')
  
  if (!isValidType) {
    ElMessage.error('请上传 .txt, .md, .doc 或 .docx 格式的文件')
    return
  }
  
  if (file.raw.size > 10 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过 10MB')
    return
  }
  
  try {
    const name = file.raw.name.toLowerCase()
    const isDoc = name.endsWith('.doc') || name.endsWith('.docx')

    if (isDoc) {
      ElMessage.warning('暂不支持 .doc/.docx 文件直接预览。请将 Word 另存为 .txt 或 .md 后上传，或直接粘贴文本到下方输入框。')
      return
    }

    const text = await readFileWithEncoding(file.raw)
    content.value = text

    if (!workInfo.value.title && file.name) {
      workInfo.value.title = file.name.replace(/\.[^/.]+$/, '')
    }

    ElMessage.success(`文件 "${file.name}" 已加载，共 ${text.length.toLocaleString()} 字符`)
  } catch (error) {
    ElMessage.error('文件读取失败，请检查文件编码或使用 UTF-8 保存')
  }
}

// 开始分析
async function startAnalysis() {
  if (content.value.length < 100) {
    ElMessage.warning('文本内容至少需要 100 字符')
    return
  }
  step.value = 'analyzing'
  analyzing.value = true
  analysisProgress.value = 0
  currentStep.value = 0

  // 模拟进度动画
  const progressInterval = setInterval(() => {
    if (analysisProgress.value < 90) {
      analysisProgress.value += Math.random() * 10
      currentStep.value = Math.min(Math.floor(analysisProgress.value / 20), 4)
      analysisStatus.value = analysisSteps[currentStep.value] + '...'
    }
  }, 1000)
  
  try {
    const res = await aiApi.analyzeLiterature({
      content: content.value,
      title: workInfo.value.title || undefined,
      author: workInfo.value.author || undefined,
      category: workInfo.value.category
    })
    
    clearInterval(progressInterval)
    analysisProgress.value = 100
    analysisResult.value = res.data
    
    setTimeout(() => {
      step.value = 'result'
      analyzing.value = false
    }, 500)
    
  } catch (error: any) {
    clearInterval(progressInterval)
    analyzing.value = false
    ElMessage.error(error?.message || '分析失败，请重试')
    step.value = 'input'
  }
}

// 创建项目
async function createProject() {
  creatingProject.value = true
  
  try {
    if (!analysisResult.value) {
      ElMessage.error('请先完成作品分析')
      return
    }
    const res = await aiApi.createProjectFromLiterature({
      analysis: analysisResult.value
    })
    
    createdProject.value = res.data
    step.value = 'success'
    ElMessage.success('项目创建成功！')
    emit('project-created', res.data.project_id)
    
  } catch (error: any) {
    ElMessage.error(error?.message || '创建项目失败')
  } finally {
    creatingProject.value = false
  }
}

// 跳转到项目
function goToProject() {
  if (createdProject.value) {
    emit('project-created', createdProject.value.project_id)
    emit('close')
  }
}

// 重置并关闭
function resetAndClose() {
  step.value = 'input'
  content.value = ''
  workInfo.value = { title: '', author: '', category: 'novel' }
  analysisResult.value = null
  createdProject.value = null
  analysisProgress.value = 0
  currentStep.value = 0
  emit('close')
}
</script>

<style scoped lang="scss">
.literature-analyzer {
  padding: 24px;
  max-width: 700px;
  margin: 0 auto;
}

.analyzer-header {
  text-align: center;
  margin-bottom: 32px;
  padding: 28px;
  background: linear-gradient(135deg, var(--el-color-primary-light-9) 0%, var(--el-fill-color-light) 100%);
  border-radius: 16px;
  border: 1px solid var(--el-color-primary-light-7);
  box-shadow: 0 4px 16px rgba(var(--el-color-primary-rgb), 0.1);

  h3 {
    margin: 0 0 12px;
    font-size: 22px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    color: var(--el-color-primary);
    font-weight: 600;
  }

  .subtitle {
    margin: 0;
    color: var(--el-text-color-secondary);
    font-size: 14px;
  }
}

.step-panel {
  animation: fadeInUp 0.4s ease-out;

  h4 {
    margin: 0 0 20px;
    font-size: 18px;
    color: var(--el-text-color-primary);
    font-weight: 600;
  }
}

.info-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 12px;
}

.upload-area {
  margin-bottom: 16px;
}

.file-uploader {
  :deep(.el-upload-dragger) {
    padding: 32px;
    background: var(--el-fill-color-light);
    border: 2px dashed var(--el-border-color);
    border-radius: 12px;
    transition: all 0.3s;

    &:hover {
      border-color: var(--el-color-primary);
      background: var(--el-color-primary-light-9);
    }
  }
}

.content-input {
  :deep(.el-textarea__inner) {
    font-family: inherit;
    line-height: 1.8;
  }
}

.char-count {
  margin-top: 8px;
  text-align: right;
  font-size: 13px;
  color: var(--el-text-color-secondary);

  &.is-valid {
    color: var(--el-color-success);
  }

  .hint {
    color: var(--el-color-danger);
    margin-left: 8px;
  }
}

.step-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 28px;
  padding-top: 20px;
  border-top: 1px solid var(--el-border-color-lighter);
}

// 分析中状态
.analyzing {
  text-align: center;
  padding: 20px 0;

  .analysis-progress {
    margin-bottom: 32px;
  }

  .progress-text {
    margin-top: 12px;
    color: var(--el-text-color-secondary);
    font-size: 14px;
  }

  .analysis-visual {
    padding: 40px;
    background: var(--el-fill-color-light);
    border-radius: 16px;
    margin-bottom: 24px;

    .pulse-icon {
      margin-bottom: 32px;
      animation: pulse 2s infinite;
    }

    .analysis-steps {
      display: flex;
      flex-direction: column;
      gap: 16px;
      max-width: 300px;
      margin: 0 auto;

      .step-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        background: var(--el-bg-color);
        border-radius: 8px;
        color: var(--el-text-color-secondary);
        transition: all 0.3s;

        &.active {
          background: var(--el-color-primary-light-9);
          color: var(--el-color-primary);
          font-weight: 500;
        }

        &.completed {
          background: var(--el-color-success-light-9);
          color: var(--el-color-success);
        }

        .el-icon {
          font-size: 18px;
        }
      }
    }
  }

  .tip-box {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    color: var(--el-text-color-secondary);
    font-size: 13px;
  }
}

// 结果展示
.result {
  .result-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;

    h4 {
      margin: 0;
      color: var(--el-color-primary);
    }
  }

  .result-overview {
    margin-bottom: 24px;

    .theme-tag {
      margin-right: 8px;
      margin-bottom: 4px;
    }
  }

  .result-collapse {
    margin-bottom: 24px;

    .custom-collapse-item {
      :deep(.el-collapse-item__header) {
        padding: 16px;
        font-size: 15px;
        font-weight: 500;
      }

      :deep(.el-collapse-item__content) {
        padding: 16px;
      }
    }

    .collapse-title {
      display: flex;
      align-items: center;
      gap: 8px;
    }
  }

  .outline-list {
    display: flex;
    flex-direction: column;
    gap: 12px;

    .outline-item {
      display: flex;
      gap: 16px;
      padding: 16px;
      background: var(--el-fill-color-light);
      border-radius: 10px;

      .outline-number {
        width: 28px;
        height: 28px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--el-color-primary);
        color: white;
        border-radius: 50%;
        font-weight: 600;
        font-size: 14px;
        flex-shrink: 0;
      }

      .outline-content {
        flex: 1;

        .outline-title {
          font-weight: 600;
          margin-bottom: 6px;
          color: var(--el-text-color-primary);
        }

        .outline-desc {
          font-size: 13px;
          color: var(--el-text-color-secondary);
          line-height: 1.6;
        }
      }
    }
  }

  .characters-list {
    display: grid;
    gap: 16px;

    .character-card {
      :deep(.el-card__header) {
        padding: 14px 18px;
        background: var(--el-fill-color-light);
      }

      .character-header {
        .character-name {
          font-weight: 600;
          font-size: 16px;
          color: var(--el-color-primary);
        }
      }

      .character-body {
        p {
          margin: 8px 0;
          font-size: 14px;
          line-height: 1.6;

          strong {
            color: var(--el-text-color-secondary);
          }
        }
      }
    }
  }

  .key-points-list {
    padding-left: 20px;

    li {
      margin: 10px 0;
      font-size: 14px;
      line-height: 1.6;
      color: var(--el-text-color-primary);
    }
  }

  .storyline-content {
    font-size: 14px;
    line-height: 1.8;
    color: var(--el-text-color-primary);
    padding: 16px;
    background: var(--el-fill-color-light);
    border-radius: 10px;
  }

  .create-project-box {
    text-align: center;
    padding: 28px;
    background: linear-gradient(135deg, var(--el-color-success-light-9) 0%, var(--el-fill-color-light) 100%);
    border-radius: 16px;
    border: 2px solid var(--el-color-success-light-5);
    margin-bottom: 24px;

    h5 {
      margin: 0 0 12px;
      font-size: 18px;
      color: var(--el-text-color-primary);
    }

    p {
      margin: 0 0 20px;
      color: var(--el-text-color-secondary);
      font-size: 14px;
    }

    .el-button {
      padding: 16px 32px;
      font-size: 16px;
    }
  }
}

// 成功状态
.success {
  .success-content {
    text-align: center;
    padding: 40px;

    .success-icon {
      margin-bottom: 24px;
      animation: scaleIn 0.5s ease-out;
    }

    h4 {
      margin: 0 0 12px;
      font-size: 24px;
      color: var(--el-text-color-primary);
    }

    .success-desc {
      color: var(--el-text-color-secondary);
      font-size: 15px;
      margin-bottom: 28px;
    }

    .project-summary {
      max-width: 400px;
      margin: 0 auto 28px;
      text-align: left;
    }

    .action-buttons {
      display: flex;
      justify-content: center;
      gap: 16px;

      .el-button {
        padding: 14px 28px;
      }
    }
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.05); opacity: 0.8; }
}

@keyframes scaleIn {
  from {
    opacity: 0;
    transform: scale(0.8);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
</style>