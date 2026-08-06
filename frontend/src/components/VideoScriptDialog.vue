<template>
  <el-dialog
    v-model="visible"
    title="一键转视频文案"
    width="880px"
    :close-on-click-modal="false"
    class="video-script-dialog"
    @open="onOpen"
    @close="handleClose"
  >
    <div class="options-row">
      <el-form :inline="true" label-position="top" class="options-form">
        <el-form-item label="目标平台">
          <el-select v-model="platform" style="width: 140px">
            <el-option label="抖音" value="抖音" />
            <el-option label="视频号" value="视频号" />
            <el-option label="小红书" value="小红书" />
            <el-option label="B站" value="B站" />
          </el-select>
        </el-form-item>
        <el-form-item label="视频风格">
          <el-select v-model="style" style="width: 160px">
            <el-option label="口播解说" value="口播解说" />
            <el-option label="知识干货" value="知识干货" />
            <el-option label="剧情演绎" value="剧情演绎" />
            <el-option label="情绪共鸣" value="情绪共鸣" />
            <el-option label="种草安利" value="种草安利" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标时长">
          <el-slider v-model="durationSec" :min="15" :max="180" :step="5" show-input style="width: 260px" />
        </el-form-item>
      </el-form>
      <el-button type="primary" :loading="loading" @click="doConvert">
        {{ result ? '重新生成' : '开始转换' }}
      </el-button>
    </div>

    <el-skeleton v-if="loading" :rows="10" animated />

    <el-result v-else-if="error" icon="error" :title="error">
      <template #extra>
        <el-button type="primary" @click="doConvert">重试</el-button>
      </template>
    </el-result>

    <template v-else-if="result">
      <div class="meta-line">
        <el-tag type="warning">{{ result.platform }}</el-tag>
        <el-tag>{{ result.style }}</el-tag>
        <el-tag type="info">约 {{ result.duration_sec }} 秒</el-tag>
      </div>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="口播文案" name="script">
          <div class="pane-toolbar">
            <strong>{{ result.video_title }}</strong>
            <el-button size="small" @click="copyText(fullScriptText)">复制文案</el-button>
          </div>
          <el-alert
            v-if="result.hook"
            :title="`前3秒钩子：${result.hook}`"
            type="success"
            :closable="false"
            show-icon
            class="hook-alert"
          />
          <el-input v-model="editableScript" type="textarea" :rows="12" />
          <div v-if="result.cta" class="cta-line">结尾引导：{{ result.cta }}</div>
          <div v-if="result.hashtags?.length" class="tag-list">
            <el-tag v-for="tag in result.hashtags" :key="tag" size="small">#{{ tag }}</el-tag>
          </div>
        </el-tab-pane>

        <el-tab-pane label="AI 视频提示词" name="prompt">
          <div class="pane-toolbar">
            <span>可直接粘贴到 Runway / Kling / Luma 等工具</span>
            <el-button size="small" type="primary" @click="copyText(editablePrompt)">复制提示词</el-button>
          </div>
          <el-input v-model="editablePrompt" type="textarea" :rows="10" />
        </el-tab-pane>

        <el-tab-pane label="分镜" name="scenes">
          <div v-if="!result.scenes?.length" class="empty-scenes">暂无分镜</div>
          <div v-else class="scene-list">
            <div v-for="scene in result.scenes" :key="scene.order" class="scene-card">
              <div class="scene-head">
                <strong>镜 {{ scene.order }}</strong>
                <el-tag size="small" type="info">{{ scene.duration_sec }}s</el-tag>
                <el-button link type="primary" @click="copyText(scene.video_prompt || scene.visual)">
                  复制本镜提示词
                </el-button>
              </div>
              <p v-if="scene.narration"><b>口播：</b>{{ scene.narration }}</p>
              <p v-if="scene.visual"><b>画面：</b>{{ scene.visual }}</p>
              <p v-if="scene.video_prompt" class="en-prompt"><b>Prompt：</b>{{ scene.video_prompt }}</p>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </template>

    <el-empty v-else description="选择参数后点击「开始转换」" />

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
      <el-button v-if="result" @click="copyText(fullScriptText)">复制口播文案</el-button>
      <el-button v-if="result" type="primary" @click="copyText(editablePrompt)">复制 AI 视频提示词</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { aiApi } from '@/api'
import type { Block } from '@/api/types'

export interface VideoScriptResult {
  video_title: string
  hook?: string
  video_script: string
  scenes: Array<{
    order: number
    duration_sec: number
    narration: string
    visual: string
    video_prompt: string
  }>
  video_prompt: string
  hashtags: string[]
  cta?: string
  duration_sec: number
  style: string
  platform: string
}

const props = defineProps<{
  modelValue: boolean
  documentId?: number | null
  rawTitle?: string
  rawContent?: string
  rawBlocks?: Block[] | Record<string, any>[] | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const platform = ref('抖音')
const style = ref('口播解说')
const durationSec = ref(60)
const loading = ref(false)
const error = ref('')
const result = ref<VideoScriptResult | null>(null)
const activeTab = ref('script')
const editableScript = ref('')
const editablePrompt = ref('')

const fullScriptText = computed(() => {
  if (!result.value) return ''
  const parts = [
    result.value.video_title,
    result.value.hook ? `【钩子】${result.value.hook}` : '',
    editableScript.value || result.value.video_script,
    result.value.cta ? `【引导】${result.value.cta}` : '',
    result.value.hashtags?.length ? result.value.hashtags.map((t) => `#${t}`).join(' ') : '',
  ]
  return parts.filter(Boolean).join('\n\n')
})

watch(
  () => result.value,
  (val) => {
    editableScript.value = val?.video_script || ''
    editablePrompt.value = val?.video_prompt || ''
  }
)

function onOpen() {
  // 每次打开保留上次结果，方便对比；不清空
}

function handleClose() {
  error.value = ''
}

async function copyText(text: string) {
  if (!text?.trim()) {
    ElMessage.warning('没有可复制的内容')
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败，请手动选择复制')
  }
}

async function doConvert() {
  loading.value = true
  error.value = ''
  try {
    const payload: any = {
      duration_sec: durationSec.value,
      style: style.value,
      platform: platform.value,
    }
    if (props.documentId) {
      payload.document_id = props.documentId
      if (props.rawBlocks?.length) payload.blocks = props.rawBlocks
    } else {
      payload.raw_title = props.rawTitle || ''
      payload.raw_content = props.rawContent || ''
      if (props.rawBlocks?.length) payload.raw_blocks = props.rawBlocks
    }

    const res = await aiApi.convertToVideoScript(payload)
    result.value = res.data.data
    activeTab.value = 'script'
    ElMessage.success('转换完成')
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    error.value = typeof detail === 'string' ? detail : e?.message || '转换失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
.video-script-dialog {
  .options-row {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }

  .options-form {
    flex: 1;
  }

  .meta-line {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
  }

  .pane-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
    gap: 12px;
  }

  .hook-alert {
    margin-bottom: 10px;
  }

  .cta-line {
    margin-top: 10px;
    color: #8a6d3b;
  }

  .tag-list {
    margin-top: 12px;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .scene-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
    max-height: 420px;
    overflow: auto;
  }

  .scene-card {
    border: 1px solid #eee0d0;
    border-radius: 10px;
    padding: 12px 14px;
    background: #fffaf5;

    .scene-head {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
    }

    p {
      margin: 4px 0;
      line-height: 1.6;
      color: #4a3b2a;
    }

    .en-prompt {
      font-size: 13px;
      color: #6b5a45;
    }
  }

  .empty-scenes {
    color: #999;
    padding: 24px;
    text-align: center;
  }
}
</style>
