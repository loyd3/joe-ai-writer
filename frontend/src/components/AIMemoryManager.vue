<template>
  <div class="memory-manager">
    <el-tabs v-model="activeTab" type="border-card">
      <el-tab-pane label="文章大纲" name="outline">
        <div class="tab-content">
          <p class="hint">定义文章的整体结构，帮助 AI 理解内容框架</p>
          <div class="outline-list">
            <div v-for="(item, index) in memory.outline" :key="index" class="outline-item">
              <el-input v-model="item.title" placeholder="章节标题">
                <template #append>
                  <el-button @click="removeOutline(index)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </template>
              </el-input>
            </div>
            <el-button type="primary" plain @click="addOutline" style="width: 100%; margin-top: 10px">
              <el-icon><Plus /></el-icon> 添加章节
            </el-button>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="故事线" name="storyline">
        <div class="tab-content">
          <p class="hint">描述故事的主要情节发展</p>
          <el-input
            v-model="memory.storyline"
            type="textarea"
            :rows="10"
            placeholder="例如：主角在普通世界 → 遭遇变故 → 踏上旅程 → 最终战胜困难..."
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="角色设定" name="characters">
        <div class="tab-content">
          <p class="hint">定义故事中的角色，让 AI 保持一致性</p>
          <div v-for="(char, index) in memory.characters" :key="index" class="character-card">
            <el-card>
              <template #header>
                <div class="char-header">
                  <el-input v-model="char.name" placeholder="角色名称" style="width: 200px" />
                  <el-button type="danger" link @click="removeCharacter(index)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
              </template>
              <el-input v-model="char.description" type="textarea" :rows="2" placeholder="角色描述" />
              <el-input v-model="char.personality" placeholder="性格特点" style="margin-top: 10px" />
              <el-input v-model="char.goals" placeholder="目标/动机" style="margin-top: 10px" />
            </el-card>
          </div>
          <el-button type="primary" plain @click="addCharacter" style="width: 100%">
            <el-icon><Plus /></el-icon> 添加角色
          </el-button>
        </div>
      </el-tab-pane>

      <el-tab-pane label="世界观" name="world">
        <div class="tab-content">
          <p class="hint">设定故事发生的世界背景</p>
          <el-input
            v-model="worldBuildingText"
            type="textarea"
            :rows="12"
            placeholder="例如：&#10;- 时代背景：现代都市&#10;- 特殊设定：存在超能力者&#10;- 社会结构：能力者受到特殊监管..."
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="写作风格" name="style">
        <div class="tab-content">
          <p class="hint">描述你想要的写作风格</p>
          <el-input
            v-model="memory.writing_style"
            type="textarea"
            :rows="8"
            placeholder="例如：&#10;- 叙述方式：第一人称视角&#10;- 语言风格：简洁明快&#10;- 情感基调：温暖治愈..."
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="关键情节" name="keypoints">
        <div class="tab-content">
          <p class="hint">记录重要的情节点，确保不遗漏</p>
          <div v-for="(point, index) in memory.key_points" :key="index" class="keypoint-item">
            <el-input v-model="memory.key_points[index]" placeholder="关键情节点">
              <template #append>
                <el-button @click="removeKeyPoint(index)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </el-input>
          </div>
          <el-button type="primary" plain @click="addKeyPoint" style="width: 100%; margin-top: 10px">
            <el-icon><Plus /></el-icon> 添加情节点
          </el-button>
        </div>
      </el-tab-pane>

      <el-tab-pane label="备注" name="notes">
        <div class="tab-content">
          <p class="hint">其他需要记住的信息</p>
          <el-input
            v-model="memory.notes"
            type="textarea"
            :rows="12"
            placeholder="任何其他信息..."
          />
        </div>
      </el-tab-pane>
    </el-tabs>

    <div class="save-bar">
      <el-button type="primary" size="large" @click="saveMemory" :loading="saving">
        <el-icon><Check /></el-icon> 保存记忆
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useProjectStore, type AIMemory } from '@/stores/project'
import { ElMessage } from 'element-plus'

const props = defineProps<{
  projectId: number
}>()

const store = useProjectStore()
const activeTab = ref('outline')
const saving = ref(false)

const memory = ref<Partial<AIMemory>>({
  outline: [],
  storyline: '',
  characters: [],
  world_building: {},
  writing_style: '',
  key_points: [],
  notes: ''
})

const worldBuildingText = computed({
  get() {
    return Object.entries(memory.value.world_building || {})
      .map(([k, v]) => `${k}: ${v}`)
      .join('\n')
  },
  set(val: string) {
    const obj: Record<string, string> = {}
    val.split('\n').forEach(line => {
      const [k, ...v] = line.split(':')
      if (k && v.length) obj[k.trim()] = v.join(':').trim()
    })
    memory.value.world_building = obj
  }
})

onMounted(() => {
  loadMemory()
})

watch(() => props.projectId, () => {
  loadMemory()
})

async function loadMemory() {
  await store.fetchMemory(props.projectId)
  if (store.currentProject?.ai_memory) {
    memory.value = { ...store.currentProject.ai_memory }
  }
}

function addOutline() {
  memory.value.outline = [...(memory.value.outline || []), { title: '' }]
}

function removeOutline(index: number) {
  memory.value.outline?.splice(index, 1)
}

function addCharacter() {
  memory.value.characters = [...(memory.value.characters || []), {
    name: '',
    description: '',
    personality: '',
    goals: ''
  }]
}

function removeCharacter(index: number) {
  memory.value.characters?.splice(index, 1)
}

function addKeyPoint() {
  memory.value.key_points = [...(memory.value.key_points || []), '']
}

function removeKeyPoint(index: number) {
  memory.value.key_points?.splice(index, 1)
}

async function saveMemory() {
  saving.value = true
  try {
    await store.updateMemory(props.projectId, memory.value)
    ElMessage.success('记忆已保存')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.memory-manager {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.tab-content {
  padding: 15px;
}

.hint {
  color: #909399;
  font-size: 13px;
  margin-bottom: 15px;
}

.outline-item, .keypoint-item {
  margin-bottom: 10px;
}

.character-card {
  margin-bottom: 15px;
}

.char-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.save-bar {
  padding: 15px;
  text-align: center;
  border-top: 1px solid #e4e7ed;
  background: #f5f7fa;
}
</style>