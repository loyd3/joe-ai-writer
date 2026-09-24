<template>
  <div class="project-settings-manager">
    <aside class="settings-nav">
      <button
        v-for="tab in tabs"
        :key="tab.name"
        type="button"
        class="nav-item"
        :class="{ active: activeTab === tab.name }"
        @click="activeTab = tab.name"
      >
        <span class="nav-label">{{ tab.label }}</span>
        <span class="nav-hint">{{ tab.hint }}</span>
      </button>
    </aside>

    <div class="settings-main">
      <div class="main-toolbar">
        <div class="save-status">
          <template v-if="saving">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>保存中…</span>
          </template>
          <template v-else-if="dirty">
            <span class="pending">有未保存更改</span>
          </template>
          <template v-else-if="lastSaved">
            <el-icon><CircleCheck /></el-icon>
            <span>已自动保存</span>
          </template>
          <template v-else>
            <span class="muted">编辑后自动保存</span>
          </template>
        </div>
        <div class="toolbar-actions">
          <el-button class="btn" @click="activeTab = 'rewrite'">
            根据设定重写
          </el-button>
          <el-button
            class="btn btn-primary"
            type="primary"
            :loading="saving"
            @click="saveSettings(true)"
          >
            <el-icon><Check /></el-icon>
            立即保存
          </el-button>
        </div>
      </div>

      <div class="main-scroll">
        <!-- 大纲 -->
        <section v-show="activeTab === 'outline'" class="panel">
          <p class="hint">为每章写清标题与简述，AI 写作会按此展开。</p>
          <div class="outline-list">
            <div v-for="(item, index) in memory.outline" :key="index" class="outline-card">
              <div class="outline-card-head">
                <span class="order-num">{{ index + 1 }}</span>
                <div class="field-with-ai grow">
                  <el-input v-model="item.title" placeholder="章节标题" @input="markDirty" />
                  <AiAssistButton
                    :project-id="projectId"
                    field="outline_title"
                    :current-value="item.title"
                    :extra="{ sibling_titles: siblingTitles(index) }"
                    @result="(v) => applyOutlineTitle(index, v)"
                  />
                </div>
                <div class="card-actions">
                  <el-button link :disabled="index === 0" @click="moveOutline(index, -1)">
                    <el-icon><ArrowUp /></el-icon>
                  </el-button>
                  <el-button
                    link
                    :disabled="index === (memory.outline?.length || 0) - 1"
                    @click="moveOutline(index, 1)"
                  >
                    <el-icon><ArrowDown /></el-icon>
                  </el-button>
                  <el-button link class="delete-btn" @click="removeOutline(index)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
              </div>
              <div class="field-with-ai stacked">
                <div class="mini-label">
                  <span>章节简述</span>
                  <AiAssistButton
                    :project-id="projectId"
                    field="outline_description"
                    :current-value="item.description || ''"
                    :extra="{ outline_title: item.title }"
                    @result="(v) => applyOutlineDesc(index, v)"
                  />
                </div>
                <el-input
                  v-model="item.description"
                  type="textarea"
                  :rows="3"
                  placeholder="本章发生什么、冲突与推进…"
                  class="coffee-textarea"
                  @input="markDirty"
                />
              </div>
              <div class="outline-card-foot">
                <el-button
                  type="primary"
                  plain
                  size="small"
                  class="btn create-chapter-btn"
                  :loading="creatingChapterIndex === index"
                  :disabled="creatingChapterIndex !== null && creatingChapterIndex !== index"
                  @click="createArticleFromChapter(index)"
                >
                  <el-icon v-if="creatingChapterIndex !== index"><DocumentAdd /></el-icon>
                  {{ creatingChapterIndex === index ? '正在生成…' : '创建文章' }}
                </el-button>
              </div>
            </div>
            <el-button class="btn btn-dashed" @click="addOutline">
              <el-icon><Plus /></el-icon> 添加章节
            </el-button>
          </div>
        </section>

        <!-- 故事线：线性缩略 + 详情 -->
        <section v-show="activeTab === 'storyline'" class="panel wide">
          <div class="field-head">
            <p class="hint no-margin">总览 + 线性阶段列表，点击节点展开编辑</p>
            <AiAssistButton
              :project-id="projectId"
              field="storyline"
              :current-value="storyline.summary"
              @result="(v) => { storyline.summary = v; markDirty() }"
            />
          </div>
          <el-input
            v-model="storyline.summary"
            type="textarea"
            :rows="3"
            placeholder="故事线总览（可选）…"
            class="coffee-textarea"
            @input="markDirty"
          />

          <div class="rail-toolbar">
            <span class="rail-title">阶段缩略</span>
            <div class="rail-actions">
              <el-button size="small" @click="seedStoryStages" :disabled="storyline.stages.length > 0">
                填入起承转合
              </el-button>
              <el-button size="small" type="primary" plain @click="addStoryStage">
                <el-icon><Plus /></el-icon> 添加阶段
              </el-button>
            </div>
          </div>

          <div v-if="!storyline.stages.length" class="empty-rail">暂无阶段，点击上方添加</div>
          <div v-else class="linear-rail">
            <div
              v-for="(stage, index) in storyline.stages"
              :key="index"
              class="rail-node"
              :class="{ active: activeStage === index }"
              @click="activeStage = index"
            >
              <div class="rail-dot">{{ index + 1 }}</div>
              <div class="rail-body">
                <div class="rail-name">{{ stage.title || `阶段 ${index + 1}` }}</div>
                <div class="rail-snippet">{{ truncateText(stage.summary, 56) || '暂无简述' }}</div>
              </div>
              <div v-if="index < storyline.stages.length - 1" class="rail-line" />
            </div>
          </div>

          <div v-if="activeStageData" class="node-editor">
            <div class="node-editor-head">
              <span>编辑阶段 {{ activeStage! + 1 }}</span>
              <div class="card-actions">
                <el-button link :disabled="activeStage === 0" @click="moveStoryStage(activeStage!, -1)">
                  <el-icon><ArrowUp /></el-icon>
                </el-button>
                <el-button
                  link
                  :disabled="activeStage === storyline.stages.length - 1"
                  @click="moveStoryStage(activeStage!, 1)"
                >
                  <el-icon><ArrowDown /></el-icon>
                </el-button>
                <el-button link class="delete-btn" @click="removeStoryStage(activeStage!)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
            <div class="field-with-ai stacked">
              <div class="mini-label">
                <span>阶段标题</span>
                <AiAssistButton
                  :project-id="projectId"
                  field="storyline_stage_title"
                  :current-value="activeStageData.title"
                  @result="(v) => { activeStageData!.title = v; markDirty() }"
                />
              </div>
              <el-input v-model="activeStageData.title" placeholder="如：开端 / 第一次转折" @input="markDirty" />
            </div>
            <div class="field-with-ai stacked" style="margin-top: 10px">
              <div class="mini-label">
                <span>阶段简述</span>
                <AiAssistButton
                  :project-id="projectId"
                  field="storyline_stage_summary"
                  :current-value="activeStageData.summary"
                  :extra="{ stage_title: activeStageData.title }"
                  @result="(v) => { activeStageData!.summary = v; markDirty() }"
                />
              </div>
              <el-input
                v-model="activeStageData.summary"
                type="textarea"
                :rows="4"
                placeholder="这一阶段发生什么…"
                class="coffee-textarea"
                @input="markDirty"
              />
            </div>
          </div>
        </section>

        <!-- 角色卡 -->
        <section v-show="activeTab === 'characters'" class="panel wide">
          <p class="hint">角色卡一览，点击卡片编辑详情</p>
          <div class="char-grid">
            <button
              v-for="(char, index) in characters"
              :key="index"
              type="button"
              class="char-tile"
              :class="{ active: activeChar === index }"
              @click="activeChar = index"
            >
              <div class="char-avatar" :style="{ background: char.color || CHAR_COLORS[index % CHAR_COLORS.length] }">
                {{ char.avatar || charInitial(char.name) }}
              </div>
              <div class="char-tile-meta">
                <div class="char-tile-name">{{ char.name || '未命名角色' }}</div>
                <div class="char-tile-role">{{ char.role || '配角' }}</div>
                <div class="char-tile-snip">{{ truncateText(char.personality || char.description, 40) || '暂无简介' }}</div>
              </div>
            </button>
            <button type="button" class="char-tile add" @click="addCharacter">
              <el-icon :size="22"><Plus /></el-icon>
              <span>添加角色卡</span>
            </button>
          </div>

          <div v-if="activeCharData" class="char-detail">
            <div class="node-editor-head">
              <span>编辑角色卡</span>
              <el-button link class="delete-btn" @click="removeCharacter(activeChar!)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            <div class="char-detail-row">
              <div class="field-with-ai grow">
                <el-input v-model="activeCharData.name" placeholder="角色名称" @input="markDirty" />
                <AiAssistButton
                  :project-id="projectId"
                  field="character_name"
                  :current-value="activeCharData.name"
                  @result="(v) => { activeCharData!.name = v; markDirty() }"
                />
              </div>
              <el-select v-model="activeCharData.role" placeholder="身份" style="width: 130px" @change="markDirty">
                <el-option v-for="r in CHAR_ROLES" :key="r" :label="r" :value="r" />
              </el-select>
              <el-input
                v-model="activeCharData.avatar"
                placeholder="头像字/emoji"
                style="width: 100px"
                maxlength="2"
                @input="markDirty"
              />
            </div>
            <div class="field-with-ai stacked" style="margin-top: 10px">
              <div class="mini-label">
                <span>角色描述</span>
                <AiAssistButton
                  :project-id="projectId"
                  field="character_description"
                  :current-value="activeCharData.description"
                  :extra="{ character_name: activeCharData.name }"
                  @result="(v) => { activeCharData!.description = v; markDirty() }"
                />
              </div>
              <el-input
                v-model="activeCharData.description"
                type="textarea"
                :rows="2"
                class="coffee-textarea"
                @input="markDirty"
              />
            </div>
            <div class="char-fields">
              <div class="field-with-ai stacked">
                <div class="mini-label">
                  <span>性格</span>
                  <AiAssistButton
                    :project-id="projectId"
                    field="character_personality"
                    :current-value="activeCharData.personality || ''"
                    :extra="{ character_name: activeCharData.name }"
                    @result="(v) => { activeCharData!.personality = v; markDirty() }"
                  />
                </div>
                <el-input v-model="activeCharData.personality" @input="markDirty" />
              </div>
              <div class="field-with-ai stacked">
                <div class="mini-label">
                  <span>目标/动机</span>
                  <AiAssistButton
                    :project-id="projectId"
                    field="character_goals"
                    :current-value="activeCharData.goals || ''"
                    :extra="{ character_name: activeCharData.name }"
                    @result="(v) => { activeCharData!.goals = v; markDirty() }"
                  />
                </div>
                <el-input v-model="activeCharData.goals" @input="markDirty" />
              </div>
            </div>
            <div class="field-with-ai stacked" style="margin-top: 10px">
              <div class="mini-label">
                <span>背景经历</span>
                <AiAssistButton
                  :project-id="projectId"
                  field="character_background"
                  :current-value="activeCharData.background || ''"
                  :extra="{ character_name: activeCharData.name }"
                  @result="(v) => { activeCharData!.background = v; markDirty() }"
                />
              </div>
              <el-input
                v-model="activeCharData.background"
                type="textarea"
                :rows="2"
                class="coffee-textarea"
                @input="markDirty"
              />
            </div>
          </div>
        </section>

        <!-- 世界观分类 -->
        <section v-show="activeTab === 'world'" class="panel wide">
          <div class="field-head">
            <p class="hint no-margin">按分类管理世界观条目</p>
            <el-button size="small" @click="addWorldCategory">
              <el-icon><Plus /></el-icon> 新分类
            </el-button>
          </div>

          <div class="world-cats">
            <button
              v-for="(cat, index) in world.categories"
              :key="index"
              type="button"
              class="world-cat-chip"
              :class="{ active: activeWorldCat === index }"
              @click="activeWorldCat = index"
            >
              <span>{{ cat.name || '未命名' }}</span>
              <em>{{ cat.items?.length || 0 }}</em>
            </button>
          </div>

          <div v-if="activeWorldCatData" class="world-panel">
            <div class="node-editor-head">
              <el-input
                v-model="activeWorldCatData.name"
                placeholder="分类名称"
                style="max-width: 220px"
                @input="markDirty"
              />
              <div class="card-actions">
                <el-button size="small" @click="addWorldItem(activeWorldCat!)">
                  <el-icon><Plus /></el-icon> 添加条目
                </el-button>
                <el-button link class="delete-btn" @click="removeWorldCategory(activeWorldCat!)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>

            <div
              v-for="(item, iIdx) in activeWorldCatData.items"
              :key="iIdx"
              class="world-item"
            >
              <div class="field-with-ai">
                <el-input
                  v-model="item.title"
                  placeholder="条目标题"
                  @input="markDirty"
                />
                <AiAssistButton
                  :project-id="projectId"
                  field="world_item_title"
                  :current-value="item.title"
                  :extra="{ category_name: activeWorldCatData.name }"
                  @result="(v) => { item.title = v; markDirty() }"
                />
                <el-button link class="delete-btn" @click="removeWorldItem(activeWorldCat!, iIdx)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
              <div class="field-with-ai stacked" style="margin-top: 6px">
                <div class="mini-label">
                  <span>内容</span>
                  <AiAssistButton
                    :project-id="projectId"
                    field="world_item_content"
                    :current-value="item.content"
                    :extra="{ category_name: activeWorldCatData.name }"
                    @result="(v) => { item.content = v; markDirty() }"
                  />
                </div>
                <el-input
                  v-model="item.content"
                  type="textarea"
                  :rows="2"
                  class="coffee-textarea"
                  placeholder="设定说明…"
                  @input="markDirty"
                />
              </div>
            </div>
            <div v-if="!activeWorldCatData.items?.length" class="empty-rail">该分类暂无条目</div>
          </div>
        </section>

        <!-- 文风：跳转独立页 -->
        <section v-show="activeTab === 'style'" class="panel">
          <div class="style-cta">
            <p class="hint">
              文风智能体已移至独立页面，可配置多套语气、节奏、禁忌与笔触范例。默认智能体会自动注入 AI 写作。
            </p>
            <el-button type="primary" class="btn btn-primary" @click="goWritingStylePage">
              打开文风设置
            </el-button>
          </div>
        </section>

        <!-- 关键情节：线性缩略 -->
        <section v-show="activeTab === 'keypoints'" class="panel wide">
          <div class="rail-toolbar">
            <p class="hint no-margin" style="flex:1">线性关键情节点，点击展开编辑</p>
            <el-button size="small" type="primary" plain @click="addKeyPoint">
              <el-icon><Plus /></el-icon> 添加节点
            </el-button>
          </div>

          <div v-if="!keyPoints.length" class="empty-rail">暂无情节点</div>
          <div v-else class="linear-rail">
            <div
              v-for="(point, index) in keyPoints"
              :key="index"
              class="rail-node"
              :class="{ active: activeKeyPoint === index }"
              @click="activeKeyPoint = index"
            >
              <div class="rail-dot star"><el-icon><Star /></el-icon></div>
              <div class="rail-body">
                <div class="rail-name">{{ point.title || `情节点 ${index + 1}` }}</div>
                <div class="rail-snippet">{{ truncateText(point.summary, 56) || '暂无简述' }}</div>
              </div>
              <div v-if="index < keyPoints.length - 1" class="rail-line" />
            </div>
          </div>

          <div v-if="activeKeyPointData" class="node-editor">
            <div class="node-editor-head">
              <span>编辑情节点 {{ activeKeyPoint! + 1 }}</span>
              <div class="card-actions">
                <el-button link :disabled="activeKeyPoint === 0" @click="moveKeyPoint(activeKeyPoint!, -1)">
                  <el-icon><ArrowUp /></el-icon>
                </el-button>
                <el-button
                  link
                  :disabled="activeKeyPoint === keyPoints.length - 1"
                  @click="moveKeyPoint(activeKeyPoint!, 1)"
                >
                  <el-icon><ArrowDown /></el-icon>
                </el-button>
                <el-button link class="delete-btn" @click="removeKeyPoint(activeKeyPoint!)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
            <div class="field-with-ai stacked">
              <div class="mini-label">
                <span>标题</span>
                <AiAssistButton
                  :project-id="projectId"
                  field="key_point"
                  :current-value="activeKeyPointData.title"
                  :extra="{ existing_points: otherKeyPoints(activeKeyPoint!) }"
                  @result="(v) => { activeKeyPointData!.title = v; markDirty() }"
                />
              </div>
              <el-input v-model="activeKeyPointData.title" placeholder="情节点标题" @input="markDirty" />
            </div>
            <div class="field-with-ai stacked" style="margin-top: 10px">
              <div class="mini-label">
                <span>简述</span>
                <AiAssistButton
                  :project-id="projectId"
                  field="key_point_summary"
                  :current-value="activeKeyPointData.summary"
                  @result="(v) => { activeKeyPointData!.summary = v; markDirty() }"
                />
              </div>
              <el-input
                v-model="activeKeyPointData.summary"
                type="textarea"
                :rows="4"
                class="coffee-textarea"
                placeholder="该情节点的具体说明…"
                @input="markDirty"
              />
            </div>
          </div>
        </section>

        <!-- 备注 -->
        <section v-show="activeTab === 'notes'" class="panel">
          <div class="field-head">
            <p class="hint no-margin">伏笔、禁忌、待办等其他信息</p>
            <AiAssistButton
              :project-id="projectId"
              field="notes"
              :current-value="memory.notes || ''"
              @result="(v) => { memory.notes = v; markDirty() }"
            />
          </div>
          <el-input
            v-model="memory.notes"
            type="textarea"
            :rows="16"
            class="coffee-textarea"
            @input="markDirty"
          />
        </section>

        <!-- 根据设定重写 -->
        <section v-show="activeTab === 'rewrite'" class="panel">
          <p class="hint">设定大改后：重建大纲并生成新文档；小改可用对齐重写。</p>
          <AIRewriteFromSettings :project-id="projectId" />
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/project'
import { ElMessage } from 'element-plus'
import {
  Plus, Delete, Check, Star, Loading, CircleCheck, ArrowUp, ArrowDown, DocumentAdd
} from '@element-plus/icons-vue'
import AiAssistButton from '@/components/AiAssistButton.vue'
import AIRewriteFromSettings from '@/components/AIRewriteFromSettings.vue'
import { aiApi, styleAgentApi } from '@/api'
import { parseFormattedTextToBlocks } from '@/utils/formatToBlocks'
import {
  normalizeStoryline,
  normalizeKeyPoints,
  normalizeCharacters,
  normalizeWorldBuilding,
  charInitial,
  truncateText,
  CHAR_ROLES,
  CHAR_COLORS,
  type StorylineData,
  type KeyPointItem,
  type CharacterCard,
  type WorldBuildingData
} from '@/utils/memoryNormalize'

const props = defineProps<{
  projectId: number
}>()

const router = useRouter()
const store = useProjectStore()
const activeTab = ref('outline')
const saving = ref(false)
const dirty = ref(false)
const lastSaved = ref(false)
const loaded = ref(false)
/** 正在按章节创建文章的大纲下标；null 表示空闲 */
const creatingChapterIndex = ref<number | null>(null)
let saveTimer: ReturnType<typeof setTimeout> | null = null
let editGen = 0

const activeStage = ref<number | null>(null)
const activeChar = ref<number | null>(null)
const activeWorldCat = ref(0)
const activeKeyPoint = ref<number | null>(null)

const tabs = [
  { name: 'outline', label: '文章大纲', hint: '章节结构' },
  { name: 'storyline', label: '故事线', hint: '线性阶段' },
  { name: 'characters', label: '角色设定', hint: '角色卡' },
  { name: 'world', label: '世界观', hint: '分类条目' },
  { name: 'style', label: '文风设置', hint: '独立页面' },
  { name: 'keypoints', label: '关键情节', hint: '线性节点' },
  { name: 'notes', label: '备注', hint: '其他约束' },
  { name: 'rewrite', label: '根据设定重写', hint: '对齐正文' },
]

const memory = ref<{
  outline: Array<{ title: string; description?: string }>
  writing_style: string
  notes: string
}>({
  outline: [],
  writing_style: '',
  notes: ''
})

const storyline = ref<StorylineData>({ summary: '', stages: [] })
const characters = ref<CharacterCard[]>([])
const world = ref<WorldBuildingData>({ categories: [] })
const keyPoints = ref<KeyPointItem[]>([])

const activeStageData = computed(() =>
  activeStage.value != null ? storyline.value.stages[activeStage.value] : null
)
const activeCharData = computed(() =>
  activeChar.value != null ? characters.value[activeChar.value] : null
)
const activeWorldCatData = computed(() =>
  world.value.categories[activeWorldCat.value] || null
)
const activeKeyPointData = computed(() =>
  activeKeyPoint.value != null ? keyPoints.value[activeKeyPoint.value] : null
)

onMounted(() => {
  loadSettings()
})

onBeforeUnmount(async () => {
  if (saveTimer) {
    clearTimeout(saveTimer)
    saveTimer = null
  }
  if (dirty.value) await saveSettings(false)
})

watch(() => props.projectId, () => {
  loadSettings()
})

function applyMemory(m: any) {
  memory.value = {
    outline: (m.outline || []).map((o: any) => ({
      title: o.title || '',
      description: o.description || o.content || ''
    })),
    writing_style: m.writing_style || '',
    notes: m.notes || ''
  }
  storyline.value = normalizeStoryline(m.storyline)
  characters.value = normalizeCharacters(m.characters)
  world.value = normalizeWorldBuilding(m.world_building)
  keyPoints.value = normalizeKeyPoints(m.key_points)

  activeStage.value = storyline.value.stages.length ? 0 : null
  activeChar.value = characters.value.length ? 0 : null
  activeWorldCat.value = 0
  activeKeyPoint.value = keyPoints.value.length ? 0 : null
}

async function loadSettings() {
  loaded.value = false
  dirty.value = false
  lastSaved.value = false
  try {
    const m = await store.fetchMemory(props.projectId)
    if (m) applyMemory(m)
  } catch (e: any) {
    ElMessage.error(e?.message || '加载设定失败')
  }
  loaded.value = true
}

function markDirty() {
  if (!loaded.value) return
  dirty.value = true
  lastSaved.value = false
  editGen += 1
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(() => saveSettings(false), 1200)
}

function siblingTitles(index: number) {
  return (memory.value.outline || [])
    .map((o, i) => (i === index ? '' : o.title))
    .filter(Boolean)
}

function otherKeyPoints(index: number) {
  return keyPoints.value.filter((_, i) => i !== index)
}

function applyOutlineTitle(index: number, v: string) {
  if (!memory.value.outline[index]) return
  memory.value.outline[index].title = v
  markDirty()
}

function applyOutlineDesc(index: number, v: string) {
  if (!memory.value.outline[index]) return
  memory.value.outline[index].description = v
  markDirty()
}

function addOutline() {
  memory.value.outline = [...memory.value.outline, { title: '', description: '' }]
  markDirty()
}

function removeOutline(index: number) {
  memory.value.outline.splice(index, 1)
  markDirty()
}

function moveOutline(index: number, delta: number) {
  const list = memory.value.outline
  const target = index + delta
  if (target < 0 || target >= list.length) return
  ;[list[index], list[target]] = [list[target], list[index]]
  markDirty()
}

/** 消费 batch-generate SSE，收集单章正文 */
async function consumeChapterGenerateStream(res: Response): Promise<string> {
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    const detail = (err as { detail?: string }).detail
    throw new Error(typeof detail === 'string' ? detail : '生成失败')
  }
  const reader = res.body?.getReader()
  if (!reader) throw new Error('无法读取响应流')
  const decoder = new TextDecoder()
  let buf = ''
  let chapterContent = ''
  let streamError = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    const parts = buf.split('\n\n')
    buf = parts.pop() ?? ''
    for (const event of parts) {
      const dataLines: string[] = []
      for (const line of event.split('\n')) {
        if (line.startsWith('data: ')) dataLines.push(line.slice(6))
        else if (line.startsWith('data:')) dataLines.push(line.slice(5))
      }
      if (!dataLines.length) continue
      const raw = dataLines.join('\n').trim()
      if (!raw || raw === '[DONE]') continue
      let parsed: {
        type?: string
        content?: string
        chapter_content?: string
        error_message?: string
      }
      try {
        parsed = JSON.parse(raw)
      } catch {
        continue
      }
      if (parsed.type === 'error' && parsed.error_message) {
        streamError = parsed.error_message
      } else if (parsed.type === 'chapter_complete' && parsed.chapter_content) {
        chapterContent = parsed.chapter_content
      } else if (parsed.type === 'content' && parsed.content) {
        chapterContent += parsed.content
      }
    }
  }

  if (streamError) throw new Error(streamError)
  return chapterContent.trim()
}

/** 根据大纲某一章直接创建文档并生成正文 */
async function createArticleFromChapter(index: number) {
  const item = memory.value.outline[index]
  if (!item) return
  const title = (item.title || '').trim()
  if (!title) {
    ElMessage.warning('请先填写章节标题')
    return
  }
  if (creatingChapterIndex.value !== null) return

  creatingChapterIndex.value = index
  try {
    if (dirty.value) {
      await saveSettings(false)
    }

    const doc = await store.createDocument(props.projectId, {
      title,
      content: [],
    })

    const prevOutline = (memory.value.outline || [])
      .slice(0, index)
      .map((o, i) => `${i + 1}. ${(o.title || '').trim() || '未命名'}`)
      .filter(Boolean)
      .join('\n')

    const customParts = [
      `这是项目大纲第 ${index + 1} 章「${title}」，请只写本章正文。`,
      item.description?.trim() ? `本章简述：${item.description.trim()}` : '',
      prevOutline ? `前文章节顺序（勿重复写完）：\n${prevOutline}` : '',
    ].filter(Boolean)

    const styleAgentId = await resolveDefaultStyleAgentId()
    const res = await aiApi.batchGenerateStream({
      project_id: props.projectId,
      document_id: doc.id,
      outline_nodes: [{ title, description: item.description || '' }],
      max_tokens_per_chapter: 4000,
      continue_on_complete: false,
      custom_instruction: customParts.join('\n'),
      style_agent_id: styleAgentId,
    })

    const text = await consumeChapterGenerateStream(res)
    if (!text || text.startsWith('[错误]') || text.startsWith('[配置错误]')) {
      ElMessage.error(text || '未生成到有效内容')
      // 仍打开空文档，方便手动写
      router.push(`/document/${doc.id}`)
      return
    }

    const blocks = parseFormattedTextToBlocks(text, 'doc')
    // 若首块不是标题，补上本章标题
    if (!blocks.length || (blocks[0].type !== 'heading' && blocks[0].type !== 'subheading')) {
      blocks.unshift({
        id: `ch-${Date.now()}`,
        type: 'heading',
        content: title,
        props: { level: 2 },
      })
    }
    await store.updateDocument(doc.id, { content: blocks })
    ElMessage.success(`已创建「${title}」`)
    router.push(`/document/${doc.id}`)
  } catch (e: any) {
    console.error(e)
    ElMessage.error(e?.message || '创建文章失败')
  } finally {
    creatingChapterIndex.value = null
  }
}

function seedStoryStages() {
  storyline.value.stages = [
    { title: '开端', summary: '' },
    { title: '发展', summary: '' },
    { title: '高潮', summary: '' },
    { title: '结局', summary: '' }
  ]
  activeStage.value = 0
  markDirty()
}

function addStoryStage() {
  storyline.value.stages.push({ title: '', summary: '' })
  activeStage.value = storyline.value.stages.length - 1
  markDirty()
}

function removeStoryStage(index: number) {
  storyline.value.stages.splice(index, 1)
  if (!storyline.value.stages.length) activeStage.value = null
  else activeStage.value = Math.min(index, storyline.value.stages.length - 1)
  markDirty()
}

function moveStoryStage(index: number, delta: number) {
  const list = storyline.value.stages
  const target = index + delta
  if (target < 0 || target >= list.length) return
  ;[list[index], list[target]] = [list[target], list[index]]
  activeStage.value = target
  markDirty()
}

function addCharacter() {
  const idx = characters.value.length
  characters.value.push({
    name: '',
    description: '',
    personality: '',
    background: '',
    goals: '',
    role: idx === 0 ? '主角' : '配角',
    avatar: '',
    color: CHAR_COLORS[idx % CHAR_COLORS.length]
  })
  activeChar.value = characters.value.length - 1
  markDirty()
}

function removeCharacter(index: number) {
  characters.value.splice(index, 1)
  if (!characters.value.length) activeChar.value = null
  else activeChar.value = Math.min(index, characters.value.length - 1)
  markDirty()
}

function addWorldCategory() {
  world.value.categories.push({ name: '新分类', items: [] })
  activeWorldCat.value = world.value.categories.length - 1
  markDirty()
}

function removeWorldCategory(index: number) {
  if (world.value.categories.length <= 1) {
    ElMessage.warning('至少保留一个分类')
    return
  }
  world.value.categories.splice(index, 1)
  activeWorldCat.value = Math.min(index, world.value.categories.length - 1)
  markDirty()
}

function addWorldItem(catIndex: number) {
  world.value.categories[catIndex]?.items.push({ title: '', content: '' })
  markDirty()
}

function removeWorldItem(catIndex: number, itemIndex: number) {
  world.value.categories[catIndex]?.items.splice(itemIndex, 1)
  markDirty()
}

function addKeyPoint() {
  keyPoints.value.push({ title: '', summary: '' })
  activeKeyPoint.value = keyPoints.value.length - 1
  markDirty()
}

function removeKeyPoint(index: number) {
  keyPoints.value.splice(index, 1)
  if (!keyPoints.value.length) activeKeyPoint.value = null
  else activeKeyPoint.value = Math.min(index, keyPoints.value.length - 1)
  markDirty()
}

function moveKeyPoint(index: number, delta: number) {
  const list = keyPoints.value
  const target = index + delta
  if (target < 0 || target >= list.length) return
  ;[list[index], list[target]] = [list[target], list[index]]
  activeKeyPoint.value = target
  markDirty()
}

function goWritingStylePage() {
  router.push(`/project/${props.projectId}/writing-style`)
}

async function resolveDefaultStyleAgentId(): Promise<number | undefined> {
  try {
    const { data } = await styleAgentApi.list(props.projectId)
    const list = Array.isArray(data) ? data : []
    return list.find((a) => a.is_default)?.id
  } catch {
    return undefined
  }
}

function buildPayload() {
  return {
    outline: memory.value.outline,
    storyline: {
      summary: storyline.value.summary,
      stages: storyline.value.stages.map((s) => ({
        title: s.title || '',
        summary: s.summary || ''
      }))
    },
    characters: characters.value.map((c) => ({
      name: c.name || '',
      description: c.description || '',
      personality: c.personality || '',
      background: c.background || '',
      goals: c.goals || '',
      role: c.role || '配角',
      avatar: c.avatar || '',
      color: c.color || ''
    })),
    world_building: {
      categories: world.value.categories.map((cat) => ({
        name: cat.name || '未命名',
        items: (cat.items || []).map((it) => ({
          title: it.title || '',
          content: it.content || ''
        }))
      }))
    },
    writing_style: memory.value.writing_style,
    key_points: keyPoints.value.map((p) => ({
      title: p.title || '',
      summary: p.summary || ''
    })),
    notes: memory.value.notes
  }
}

async function saveSettings(showToast = true) {
  if (saveTimer) {
    clearTimeout(saveTimer)
    saveTimer = null
  }
  const genAtStart = editGen
  const snapshot = buildPayload()
  saving.value = true
  try {
    await store.updateMemory(props.projectId, snapshot)
    if (genAtStart !== editGen) {
      dirty.value = true
      if (!saveTimer) saveTimer = setTimeout(() => saveSettings(false), 300)
      return
    }
    dirty.value = false
    lastSaved.value = true
    if (showToast) ElMessage.success('设定已保存')
  } catch (e: any) {
    ElMessage.error(e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped lang="scss">
.project-settings-manager {
  height: 100%;
  width: 100%;
  display: flex;
  background: var(--coffee-bg);
  min-height: 0;
}

.settings-nav {
  width: 200px;
  flex-shrink: 0;
  padding: 16px 10px;
  border-right: 1px solid var(--coffee-border);
  background: var(--coffee-bg-card);
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto;
}

.nav-item {
  text-align: left;
  border: none;
  background: transparent;
  border-radius: 10px;
  padding: 10px 12px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 2px;
  transition: background 0.15s;

  &:hover { background: var(--coffee-bg-warm); }

  &.active {
    background: var(--coffee-bg-warm);
    box-shadow: inset 3px 0 0 var(--coffee-primary);
    .nav-label { color: var(--coffee-primary); font-weight: 600; }
  }

  .nav-label { font-size: 14px; color: var(--coffee-text); }
  .nav-hint { font-size: 11px; color: var(--coffee-text-light); }
}

.settings-main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.main-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 32px;
  border-bottom: 1px solid var(--coffee-border);
  background: var(--coffee-bg-card);
  flex-shrink: 0;
}

.save-status {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  font-size: 13px;
  color: var(--coffee-text-muted);
  .pending { color: var(--coffee-primary); }
  .muted { color: var(--coffee-text-light); }
}

.toolbar-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex-shrink: 0;
  margin-left: auto;
}

.main-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 24px 32px 40px;
  width: 100%;
  box-sizing: border-box;
}

.panel {
  width: 100%;
  max-width: none;
  &.wide { max-width: none; }
}

.hint {
  color: var(--coffee-text-light);
  font-size: 13px;
  margin-bottom: 16px;
  padding: 10px 14px;
  background: var(--coffee-bg-warm);
  border-radius: 8px;
  border-left: 3px solid var(--coffee-primary-light);
  &.no-margin { margin: 0; flex: 1; }
}

.field-head {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 12px;
}

.field-with-ai {
  display: flex;
  align-items: center;
  gap: 6px;
  &.grow { flex: 1; min-width: 0; }
  &.stacked { flex-direction: column; align-items: stretch; gap: 6px; }
}

.mini-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--coffee-text-muted);
}

.outline-list { display: flex; flex-direction: column; gap: 14px; }

.outline-card {
  background: var(--coffee-bg-card);
  border: 1px solid var(--coffee-border);
  border-radius: 12px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.outline-card-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.outline-card-foot {
  display: flex;
  justify-content: flex-end;
  padding-top: 2px;
}

.create-chapter-btn {
  .el-icon {
    margin-right: 4px;
  }
}

.order-num {
  width: 28px;
  height: 28px;
  background: linear-gradient(135deg, var(--coffee-primary) 0%, var(--coffee-primary-light) 100%);
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.card-actions {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

/* 线性缩略轨 */
.rail-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 16px 0 12px;
}

.rail-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--coffee-text);
}

.rail-actions { display: flex; gap: 8px; }

.empty-rail {
  padding: 28px;
  text-align: center;
  color: var(--coffee-text-light);
  background: var(--coffee-bg-warm);
  border-radius: 10px;
  border: 1px dashed var(--coffee-border);
}

.linear-rail {
  display: flex;
  flex-direction: column;
  gap: 0;
  margin-bottom: 16px;
}

.rail-node {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: background 0.15s, border-color 0.15s;

  &:hover { background: var(--coffee-bg-warm); }
  &.active {
    background: var(--coffee-bg-card);
    border-color: var(--coffee-primary-light);
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
  }
}

.rail-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--coffee-primary);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  z-index: 1;

  &.star {
    background: linear-gradient(135deg, #c4a574, #a67c52);
  }
}

.rail-line {
  position: absolute;
  left: 25px;
  top: 40px;
  bottom: -10px;
  width: 2px;
  background: var(--coffee-border);
}

.rail-body { flex: 1; min-width: 0; padding-top: 2px; }
.rail-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--coffee-text);
  margin-bottom: 2px;
}
.rail-snippet {
  font-size: 12px;
  color: var(--coffee-text-light);
  line-height: 1.5;
}

.node-editor {
  background: var(--coffee-bg-card);
  border: 1px solid var(--coffee-border);
  border-radius: 12px;
  padding: 14px 16px;
}

.node-editor-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 13px;
  font-weight: 600;
  color: var(--coffee-text);
}

/* 角色卡网格 */
.char-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

.char-tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 12px;
  border-radius: 14px;
  border: 1px solid var(--coffee-border);
  background: var(--coffee-bg-card);
  cursor: pointer;
  text-align: center;
  transition: border-color 0.15s, box-shadow 0.15s;

  &:hover { border-color: var(--coffee-primary-light); }
  &.active {
    border-color: var(--coffee-primary);
    box-shadow: 0 0 0 2px rgba(139, 105, 20, 0.15);
  }
  &.add {
    border-style: dashed;
    color: var(--coffee-text-muted);
    min-height: 140px;
    justify-content: center;
  }
}

.char-avatar {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  color: #fff;
  font-size: 20px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.char-tile-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--coffee-text);
}
.char-tile-role {
  font-size: 11px;
  color: var(--coffee-primary);
  background: var(--coffee-bg-warm);
  padding: 2px 8px;
  border-radius: 999px;
}
.char-tile-snip {
  font-size: 11px;
  color: var(--coffee-text-light);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.char-detail {
  background: var(--coffee-bg-card);
  border: 1px solid var(--coffee-border);
  border-radius: 12px;
  padding: 14px 16px;
}

.char-detail-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.char-fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 12px;
}

/* 世界观分类 */
.world-cats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}

.world-cat-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid var(--coffee-border);
  background: var(--coffee-bg-card);
  cursor: pointer;
  font-size: 13px;
  color: var(--coffee-text);

  em {
    font-style: normal;
    font-size: 11px;
    color: var(--coffee-text-light);
    background: var(--coffee-bg-warm);
    padding: 0 6px;
    border-radius: 8px;
  }

  &.active {
    border-color: var(--coffee-primary);
    color: var(--coffee-primary);
    background: var(--coffee-bg-warm);
  }
}

.world-panel {
  background: var(--coffee-bg-card);
  border: 1px solid var(--coffee-border);
  border-radius: 12px;
  padding: 14px 16px;
}

.world-item {
  padding: 12px 0;
  border-bottom: 1px solid var(--coffee-border-light, var(--coffee-border));
  &:last-child { border-bottom: none; }
}

.delete-btn {
  color: var(--coffee-text-light);
  padding: 8px;
  &:hover {
    color: #f56c6c;
    background: rgba(245, 108, 108, 0.1);
  }
}

.coffee-textarea {
  :deep(.el-textarea__inner) {
    background: var(--coffee-bg-card);
    border-color: var(--coffee-border);
    color: var(--coffee-text);
    line-height: 1.8;
    padding: 14px;
    border-radius: 10px;
    &:focus { border-color: var(--coffee-primary); }
    &::placeholder { color: var(--coffee-text-light); }
  }
}

.btn-dashed {
  width: 100%;
  border-style: dashed;
  margin-top: 4px;
}

.style-cta {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 16px;
  max-width: 520px;
}

@media (max-width: 720px) {
  .settings-nav { width: 120px; }
  .char-fields { grid-template-columns: 1fr; }
  .char-detail-row { flex-wrap: wrap; }
  .main-scroll { padding: 16px; }
  .main-toolbar { padding: 10px 16px; }
}
</style>
