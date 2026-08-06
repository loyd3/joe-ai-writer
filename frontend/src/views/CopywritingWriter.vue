<template>
  <div class="copywriting-writing">
    <div class="page-header">
      <h1>📣 文案写作</h1>
      <p class="subtitle">广告、推销、引流文案生成；一键适配微信公众号/小红书/知乎等平台风格</p>
    </div>

    <el-steps :active="currentStep" finish-status="success" class="steps">
      <el-step title="填写需求" description="输入产品、卖点与引流方式" />
      <el-step title="生成文案" description="AI生成标题与正文" />
      <el-step title="保存/发布" description="保存到项目并适配多平台" />
    </el-steps>

    <!-- Step 1 -->
    <div v-if="currentStep === 0" class="step-content">
      <el-card class="config-card">
        <template #header>
          <div class="card-header">
            <span>📝 文案需求配置</span>
          </div>
        </template>

        <el-form :model="form" label-position="top">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="文案目标">
                <el-select v-model="form.copyObjective" placeholder="选择文案目标" style="width: 100%">
                  <el-option label="广告投放" value="广告" />
                  <el-option label="推销转化" value="推销" />
                  <el-option label="引流获客" value="引流" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="预期长度">
                <el-slider
                  v-model="form.wordCount"
                  :min="300"
                  :max="1800"
                  :step="100"
                  show-stops
                />
                <span class="slider-value">{{ form.wordCount }} 字</span>
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item label="产品/服务">
            <el-input v-model="form.product" placeholder="例如：护肤品/课程/软件/服务项目" show-word-limit />
          </el-form-item>

          <el-form-item label="目标人群">
            <el-input v-model="form.targetAudience" placeholder="例如：25-35岁职场女性/新手妈妈/健身人群..." />
          </el-form-item>

          <el-form-item label="核心卖点/差异化">
            <el-input
              v-model="form.sellingPoints"
              type="textarea"
              :rows="3"
              placeholder="尽量写清：你比别人更好的点是什么？"
            />
          </el-form-item>

          <el-form-item label="核心痛点（可选）">
            <el-input
              v-model="form.painPoints"
              type="textarea"
              :rows="3"
              placeholder="让读者产生共鸣的“问题/焦虑/阻碍”"
            />
          </el-form-item>

          <el-form-item label="证据/案例/体验（可选）">
            <el-input
              v-model="form.evidenceCases"
              type="textarea"
              :rows="3"
              placeholder="例如：数据、用户反馈、解决前后对比"
            />
          </el-form-item>

          <el-form-item label="行动引导/引流方式（可选）">
            <el-input
              v-model="form.cta"
              type="textarea"
              :rows="2"
              placeholder="例如：评论关键词领取资料/私信获取方案/加群咨询..."
            />
          </el-form-item>

          <el-form-item label="写作语气">
            <el-radio-group v-model="form.tone">
              <el-radio-button label="专业且有说服力" />
              <el-radio-button label="活泼种草风" />
              <el-radio-button label="温柔治愈风" />
              <el-radio-button label="犀利反差风" />
            </el-radio-group>
          </el-form-item>

          <el-form-item label="额外要求（可选）">
            <el-input
              v-model="form.additionalRequirements"
              type="textarea"
              :rows="2"
              placeholder="例如：更短句/更强节奏/更强调低门槛与可执行步骤"
            />
          </el-form-item>
        </el-form>

        <div class="action-buttons">
          <el-button class="btn-primary btn-lg" @click="generateCopywriting" :loading="generating" :disabled="!canGenerate">
            <el-icon><MagicStick /></el-icon> 生成文案
          </el-button>
        </div>
      </el-card>
    </div>

    <!-- Step 2 -->
    <div v-if="currentStep === 1" class="step-content">
      <el-card class="article-preview-card">
        <template #header>
          <div class="card-header">
            <span>✍️ 生成结果</span>
            <div>
              <el-button size="small" @click="regenerate" :loading="generating">
                <el-icon><Refresh /></el-icon> 重新生成
              </el-button>
            </div>
          </div>
        </template>

        <div v-if="generating" class="article-generating">
          <el-skeleton :rows="10" animated />
        </div>

        <div v-else-if="generatedArticle" class="article-content">
          <div class="article-title">{{ generatedArticle.title }}</div>
          <div class="article-body" v-html="renderedContent"></div>

          <div class="action-buttons">
            <el-button @click="currentStep = 0">上一步</el-button>
            <el-button type="primary" @click="currentStep = 2">下一步：保存/发布</el-button>
          </div>
        </div>
      </el-card>
    </div>

    <!-- Step 3 -->
    <div v-if="currentStep === 2" class="step-content">
      <el-card class="save-card">
        <template #header>
          <div class="card-header">
            <span>💾 保存到项目 & 发布</span>
          </div>
        </template>

        <el-form :model="saveConfig" label-position="top">
          <el-form-item label="选择项目">
            <el-select
              v-model="saveConfig.projectId"
              placeholder="选择要保存的项目"
              style="width: 100%"
              filterable
            >
              <el-option :key="'__new__'" :label="'➕ 新建项目'" :value="-1" />
              <el-option
                v-for="p in projects"
                :key="p.id"
                :label="p.title"
                :value="p.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item v-if="saveConfig.projectId === -1" label="新项目名称">
            <el-input v-model="newProjectName" placeholder="请输入新项目名称" />
          </el-form-item>

          <el-form-item label="文档标题">
            <el-input v-model="saveConfig.title" placeholder="输入文档标题" />
          </el-form-item>
        </el-form>

        <div class="action-buttons">
          <el-button
            @click="saveDocument"
            class="btn-primary"
            :loading="saving"
            :disabled="!canSave"
          >
            <el-icon><DocumentChecked /></el-icon> 保存文档
          </el-button>

          <el-button
            class="btn-primary"
            :loading="quickWriting"
            @click="quickWrite"
            v-if="!savedDoc"
          >
            <el-icon><MagicStick /></el-icon> 一键生成并保存
          </el-button>
        </div>

        <el-divider v-if="generatedArticle" />

        <div v-if="generatedArticle" class="publish-section">
          <el-button type="warning" size="large" @click="showPublishDialog = true">
            <el-icon><Promotion /></el-icon> 一键适配并预览多平台风格
          </el-button>
          <el-button type="primary" size="large" @click="showVideoScriptDialog = true" style="margin-left: 12px">
            <el-icon><VideoCamera /></el-icon> 转视频文案 / AI提示词
          </el-button>
        </div>
      </el-card>

      <PublishDialog
        v-model="showPublishDialog"
        :document-id="savedDoc?.id"
        :raw-title="generatedArticle?.title"
        :raw-content="generatedArticle?.content"
        :rawBlocks="generatedArticle?.blocks"
      />

      <VideoScriptDialog
        v-model="showVideoScriptDialog"
        :document-id="savedDoc?.id"
        :raw-title="generatedArticle?.title"
        :raw-content="generatedArticle?.content"
        :raw-blocks="generatedArticle?.blocks"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, MagicStick, DocumentChecked, Promotion, VideoCamera } from '@element-plus/icons-vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import PublishDialog from '@/components/PublishDialog.vue'
import VideoScriptDialog from '@/components/VideoScriptDialog.vue'
import { useProjectStore } from '@/stores/project'
import { API_BASE_URL } from '@/api'

marked.setOptions({
  breaks: false,
  gfm: true,
})

const API_BASE = import.meta.env.VITE_API_URL || API_BASE_URL

const projectStore = useProjectStore()

const currentStep = ref(0)
const generating = ref(false)
const saving = ref(false)
const quickWriting = ref(false)

const generatedArticle = ref<{ title: string; content: string; keywords?: string[]; blocks?: any[] } | null>(null)
const savedDoc = ref<any>(null)

const showPublishDialog = ref(false)
const showVideoScriptDialog = ref(false)

const form = ref({
  copyObjective: '广告',
  wordCount: 900,
  product: '',
  targetAudience: '',
  sellingPoints: '',
  painPoints: '',
  evidenceCases: '',
  cta: '',
  tone: '专业且有说服力',
  additionalRequirements: '',
})

const saveConfig = ref({
  projectId: null as number | null,
  title: '',
})

const newProjectName = ref('')

const projects = computed(() => projectStore.projects)

const canGenerate = computed(() => {
  return !!form.value.product.trim() && !!form.value.targetAudience.trim() && !!form.value.sellingPoints.trim()
})

const canSave = computed(() => {
  const pid = saveConfig.value.projectId
  return !!generatedArticle.value && typeof pid === 'number' && !!saveConfig.value.title.trim()
})

const renderedContent = computed(() => {
  if (!generatedArticle.value?.content) return ''
  return DOMPurify.sanitize(marked(generatedArticle.value.content) as string)
})

async function ensureProjectSelected() {
  if (saveConfig.value.projectId === -1) {
    if (!newProjectName.value.trim()) {
      ElMessage.warning('请输入新项目名称')
      return null
    }
    const project = await projectStore.createProject({ title: newProjectName.value.trim() } as any)
    newProjectName.value = ''
    saveConfig.value.projectId = project.id
    return project.id
  }
  return saveConfig.value.projectId
}

async function generateCopywriting() {
  generating.value = true
  try {
    generatedArticle.value = null
    savedDoc.value = null
    showPublishDialog.value = false

    const res = await fetch(`${API_BASE}/api/copywriting/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify({
        copy_objective: form.value.copyObjective,
        product: form.value.product,
        target_audience: form.value.targetAudience,
        selling_points: form.value.sellingPoints,
        pain_points: form.value.painPoints,
        evidence_cases: form.value.evidenceCases,
        cta: form.value.cta,
        tone: form.value.tone,
        word_count: form.value.wordCount,
        additional_requirements: form.value.additionalRequirements,
      }),
    })

    if (!res.ok) throw new Error('生成文案失败')
    const data = await res.json()
    if (!data?.success) throw new Error(data?.detail || '生成失败')

    generatedArticle.value = data.data || null
    saveConfig.value.title = generatedArticle.value?.title || ''
    currentStep.value = 1
  } catch (e: any) {
    ElMessage.error(e?.message || '生成文案失败')
    console.error(e)
  } finally {
    generating.value = false
  }
}

function regenerate() {
  if (!canGenerate.value) return
  generateCopywriting()
}

async function saveDocument() {
  if (!generatedArticle.value) return
  if (!canSave.value) {
    ElMessage.warning('请选择项目并填写文档标题')
    return
  }

  const projectId = await ensureProjectSelected()
  if (!projectId) return

  saving.value = true
  try {
    const res = await fetch(`${API_BASE}/api/copywriting/create-document`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify({
        project_id: projectId,
        title: saveConfig.value.title,
        content: generatedArticle.value.content,
      }),
    })

    if (!res.ok) throw new Error('保存文档失败')
    const data = await res.json()
    savedDoc.value = data.document
    ElMessage.success('文档保存成功')
  } catch (e: any) {
    ElMessage.error(e?.message || '保存文档失败')
    console.error(e)
  } finally {
    saving.value = false
  }
}

async function quickWrite() {
  if (quickWriting.value) return
  if (!canGenerate.value) {
    ElMessage.warning('请先填写完整的需求信息')
    return
  }

  if (!saveConfig.value.projectId) {
    ElMessage.warning('请选择要保存的项目')
    return
  }

  const projectId = await ensureProjectSelected()
  if (!projectId) return

  quickWriting.value = true
  try {
    const res = await fetch(`${API_BASE}/api/copywriting/quick-write`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify({
        project_id: projectId,
        copy_objective: form.value.copyObjective,
        product: form.value.product,
        target_audience: form.value.targetAudience,
        selling_points: form.value.sellingPoints,
        pain_points: form.value.painPoints,
        evidence_cases: form.value.evidenceCases,
        cta: form.value.cta,
        tone: form.value.tone,
        word_count: form.value.wordCount,
        additional_requirements: form.value.additionalRequirements,
      }),
    })

    if (!res.ok) throw new Error('一键生成并保存失败')
    const data = await res.json()
    savedDoc.value = data.document
    generatedArticle.value = {
      title: data.title || data.document?.title,
      content: data.content || generatedArticle.value?.content || '',
      keywords: data.keywords || [],
      blocks: data.blocks || generatedArticle.value?.blocks || [],
    }
    saveConfig.value.title = generatedArticle.value.title
    ElMessage.success('已生成并保存')
  } catch (e: any) {
    ElMessage.error(e?.message || '一键生成并保存失败')
    console.error(e)
  } finally {
    quickWriting.value = false
  }
}

onMounted(async () => {
  await projectStore.fetchProjects()
})
</script>

<style scoped lang="scss">
.copywriting-writing {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  text-align: center;
  margin-bottom: 24px;
  h1 {
    font-size: 28px;
    margin-bottom: 8px;
  }
  .subtitle {
    color: #666;
    font-size: 14px;
  }
}

.steps {
  margin-bottom: 28px;
}

.step-content {
  min-height: 420px;
}

.config-card,
.article-preview-card,
.save-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.slider-value {
  color: #409eff;
  font-weight: 600;
  margin-top: 8px;
  display: inline-block;
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid #e4e7ed;
  flex-wrap: wrap;
}

.article-generating {
  padding: 22px 0;
}

.article-content {
  .article-title {
    font-size: 24px;
    font-weight: 700;
    color: #303133;
    margin: 8px 0 12px;
  }
  .article-body {
    background: #fafafa;
    border-radius: 8px;
    padding: 18px;
    line-height: 1.9;
    font-size: 15px;
    color: #303133;

    :deep(h2) {
      font-size: 19px;
      font-weight: 600;
      margin: 18px 0 10px;
    }
    :deep(p) {
      margin-bottom: 14px;
      text-indent: 2em;
    }
    :deep(ul) {
      margin-bottom: 14px;
    }
  }
}

.publish-section {
  margin-top: 12px;
  text-align: center;
}
</style>

