<template>
  <div class="project-settings-manager">
    <el-tabs v-model="activeTab" type="card" class="coffee-tabs">
      <el-tab-pane label="📋 文章大纲" name="outline">
        <div class="tab-content">
          <p class="hint">定义文章的整体结构，帮助 AI 理解内容框架</p>
          <div class="outline-list">
            <div v-for="(item, index) in memory.outline" :key="index" class="outline-item">
              <span class="order-num">{{ index + 1 }}</span>
              <el-input v-model="item.title" placeholder="章节标题" class="outline-input" />
              <el-button class="delete-btn" link @click="removeOutline(index)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            <el-button class="add-btn" @click="addOutline">
              <el-icon><Plus /></el-icon> 添加章节
            </el-button>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="📖 故事线" name="storyline">
        <div class="tab-content">
          <p class="hint">描述故事的主要情节发展</p>
          <el-input
            v-model="memory.storyline"
            type="textarea"
            :rows="12"
            placeholder="例如：主角在普通世界 → 遭遇变故 → 踏上旅程 → 最终战胜困难..."
            class="coffee-textarea"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="👤 角色设定" name="characters">
        <div class="tab-content">
          <p class="hint">定义故事中的角色，让 AI 保持一致性</p>
          <div v-for="(char, index) in memory.characters" :key="index" class="character-card">
            <div class="card-header">
              <el-input v-model="char.name" placeholder="角色名称" class="char-name" />
              <el-button link class="delete-btn" @click="removeCharacter(index)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            <div class="card-body">
              <el-input 
                v-model="char.description" 
                type="textarea" 
                :rows="2" 
                placeholder="角色描述" 
                class="coffee-textarea"
              />
              <div class="char-fields">
                <el-input v-model="char.personality" placeholder="性格特点" />
                <el-input v-model="char.goals" placeholder="目标/动机" />
              </div>
            </div>
          </div>
          <el-button class="add-btn" @click="addCharacter">
            <el-icon><Plus /></el-icon> 添加角色
          </el-button>
        </div>
      </el-tab-pane>

      <el-tab-pane label="🌍 世界观" name="world">
        <div class="tab-content">
          <p class="hint">设定故事发生的世界背景</p>
          <el-input
            v-model="worldBuildingText"
            type="textarea"
            :rows="14"
            placeholder="例如：&#10;- 时代背景：现代都市&#10;- 特殊设定：存在超能力者&#10;- 社会结构：能力者受到特殊监管..."
            class="coffee-textarea"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="✍️ 写作风格" name="style">
        <div class="tab-content">
          <p class="hint">描述你想要的写作风格</p>
          <el-input
            v-model="memory.writing_style"
            type="textarea"
            :rows="12"
            placeholder="例如：&#10;- 叙述方式：第一人称视角&#10;- 语言风格：简洁明快&#10;- 情感基调：温暖治愈..."
            class="coffee-textarea"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="⭐ 关键情节" name="keypoints">
        <div class="tab-content">
          <p class="hint">记录重要的情节点，确保不遗漏</p>
          <div class="keypoints-list">
            <div v-for="(point, index) in memory.key_points" :key="index" class="keypoint-item">
              <el-icon class="point-icon"><Star /></el-icon>
              <el-input v-model="memory.key_points[index]" placeholder="关键情节点" />
              <el-button link class="delete-btn" @click="removeKeyPoint(index)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            <el-button class="add-btn" @click="addKeyPoint">
              <el-icon><Plus /></el-icon> 添加情节点
            </el-button>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="📝 备注" name="notes">
        <div class="tab-content">
          <p class="hint">其他备注信息</p>
          <el-input
            v-model="memory.notes"
            type="textarea"
            :rows="14"
            placeholder="任何其他信息..."
            class="coffee-textarea"
          />
        </div>
      </el-tab-pane>
    </el-tabs>

    <div class="save-bar">
      <el-button type="primary" size="large" @click="saveSettings" :loading="saving" class="save-btn">
        <el-icon><Check /></el-icon> 保存设定
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useProjectStore, type AIMemory } from '@/stores/project'
import { ElMessage } from 'element-plus'
import { Plus, Delete, Check, Star } from '@element-plus/icons-vue'

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
  loadSettings()
})

watch(() => props.projectId, () => {
  loadSettings()
})

async function loadSettings() {
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

async function saveSettings() {
  saving.value = true
  try {
    await store.updateMemory(props.projectId, memory.value)
    ElMessage.success('设定已保存')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped lang="scss">
.project-settings-manager {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--coffee-bg);
}

.coffee-tabs {
  flex: 1;
  
  :deep(.el-tabs__header) {
    margin: 0;
    background: var(--coffee-bg-card);
    border-bottom: 1px solid var(--coffee-border);
    
    .el-tabs__nav-wrap {
      padding: 0 16px;
    }
    
    .el-tabs__item {
      padding: 0 20px;
      height: 48px;
      line-height: 48px;
      font-size: 14px;
      color: var(--coffee-text-muted);
      border: none;
      
      &.is-active {
        color: var(--coffee-primary);
        background: var(--coffee-bg);
        border-bottom: 2px solid var(--coffee-primary);
      }
      
      &:hover {
        color: var(--coffee-primary);
      }
    }
  }
  
  :deep(.el-tabs__content) {
    flex: 1;
    overflow-y: auto;
    background: var(--coffee-bg);
  }
}

.tab-content {
  padding: 24px;
  max-width: 600px;
  margin: 0 auto;
}

.hint {
  color: var(--coffee-text-light);
  font-size: 13px;
  margin-bottom: 20px;
  padding: 12px 16px;
  background: var(--coffee-bg-warm);
  border-radius: 8px;
  border-left: 3px solid var(--coffee-primary-light);
}

/* 大纲样式 */
.outline-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.outline-item {
  display: flex;
  align-items: center;
  gap: 12px;
  
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
  
  .outline-input {
    flex: 1;
  }
  
  .delete-btn {
    color: var(--coffee-text-light);
    
    &:hover {
      color: #f56c6c;
    }
  }
}

/* 角色卡片 */
.character-card {
  background: var(--coffee-bg-card);
  border: 1px solid var(--coffee-border);
  border-radius: 12px;
  margin-bottom: 16px;
  overflow: hidden;
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px;
    background: var(--coffee-bg-warm);
    border-bottom: 1px solid var(--coffee-border);
    
    .char-name {
      max-width: 200px;
      
      :deep(.el-input__inner) {
        font-weight: 600;
        color: var(--coffee-text);
      }
    }
  }
  
  .card-body {
    padding: 16px;
    
    .char-fields {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-top: 12px;
    }
  }
}

/* 情节点 */
.keypoints-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.keypoint-item {
  display: flex;
  align-items: center;
  gap: 12px;
  
  .point-icon {
    color: var(--coffee-primary-light);
    font-size: 18px;
  }
  
  .el-input {
    flex: 1;
  }
  
  .delete-btn {
    color: var(--coffee-text-light);
    
    &:hover {
      color: #f56c6c;
    }
  }
}

/* 按钮样式 */
.add-btn {
  width: 100%;
  height: 44px;
  border-radius: 10px;
  border: 2px dashed var(--coffee-border);
  color: var(--coffee-text-muted);
  background: transparent;
  
  &:hover {
    border-color: var(--coffee-primary);
    color: var(--coffee-primary);
    background: var(--coffee-sidebar-shadow);
  }
}

.delete-btn {
  padding: 8px;
  
  &:hover {
    background: rgba(245, 108, 108, 0.1);
  }
}

/* 文本域 */
.coffee-textarea {
  :deep(.el-textarea__inner) {
    background: var(--coffee-bg-card);
    border-color: var(--coffee-border);
    color: var(--coffee-text);
    line-height: 1.8;
    padding: 16px;
    border-radius: 10px;
    
    &:focus {
      border-color: var(--coffee-primary);
    }
    
    &::placeholder {
      color: var(--coffee-text-light);
    }
  }
}

/* 保存栏 */
.save-bar {
  padding: 16px 24px;
  text-align: center;
  background: var(--coffee-bg-card);
  border-top: 1px solid var(--coffee-border);
  
  .save-btn {
    min-width: 160px;
    height: 48px;
    border-radius: 10px;
    background: linear-gradient(135deg, var(--coffee-primary) 0%, var(--coffee-primary-light) 100%);
    border: none;
    font-size: 15px;
    font-weight: 500;
    
    &:hover {
      transform: translateY(-1px);
      box-shadow: 0 6px 16px var(--coffee-selection);
    }
  }
}
</style>
