<template>
  <div class="event-manager">
    <div class="event-header">
      <h3>事件设定</h3>
      <el-button type="primary" size="small" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon> 添加事件
      </el-button>
    </div>

    <!-- 事件时间线 -->
    <div class="event-timeline">
      <el-timeline>
        <el-timeline-item
          v-for="event in sortedEvents"
          :key="event.id"
          :type="getTimelineType(event)"
          :color="getTimelineColor(event)"
          :hollow="event.is_completed"
          :timestamp="event.timeline_position || event.chapter || '未定位'"
        >
          <el-card class="event-card" :class="{ 'is-completed': event.is_completed }">
            <div class="event-card-header">
              <div class="event-title-section">
                <span class="event-name">{{ event.name }}</span>
                <el-tag size="small" :type="getImportanceType(event.importance)">
                  {{ getImportanceLabel(event.importance) }}
                </el-tag>
                <el-tag size="small" :type="getEventTypeColor(event.event_type)" style="margin-left: 5px">
                  {{ getEventTypeLabel(event.event_type) }}
                </el-tag>
              </div>
              <div class="event-actions">
                <el-checkbox 
                  v-model="event.is_completed" 
                  @change="toggleCompleted(event)"
                  title="标记完成"
                >
                  完成
                </el-checkbox>
                <el-dropdown trigger="click" @command="(cmd) => handleCommand(cmd, event)">
                  <el-icon class="more-icon"><More /></el-icon>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="edit">编辑</el-dropdown-item>
                      <el-dropdown-item command="delete" divided type="danger">删除</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </div>
            
            <p v-if="event.description" class="event-description">{{ event.description }}</p>
            
            <div v-if="event.involved_characters?.length" class="event-characters">
              <el-tag 
                v-for="charId in event.involved_characters" 
                :key="charId"
                size="small"
                effect="plain"
              >
                {{ getCharacterName(charId) }}
              </el-tag>
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>
      
      <el-empty v-if="!events.length" description="暂无事件，点击上方按钮添加" />
    </div>

    <!-- 创建/编辑事件对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingEvent ? '编辑事件' : '添加事件'"
      width="600px"
    >
      <el-form :model="eventForm" label-width="100px">
        <el-form-item label="事件名称" required>
          <el-input v-model="eventForm.name" placeholder="输入事件名称" />
        </el-form-item>
        
        <el-form-item label="事件描述">
          <el-input
            v-model="eventForm.description"
            type="textarea"
            :rows="3"
            placeholder="描述事件的内容"
          />
        </el-form-item>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="所属章节">
              <el-input v-model="eventForm.chapter" placeholder="如：第三章" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="时间线位置">
              <el-input v-model="eventForm.timeline_position" placeholder="如：中段" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="重要程度">
              <el-select v-model="eventForm.importance" style="width: 100%">
                <el-option label="次要" value="minor" />
                <el-option label="普通" value="normal" />
                <el-option label="重要" value="major" />
                <el-option label="关键" value="critical" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="事件类型">
              <el-select v-model="eventForm.event_type" style="width: 100%">
                <el-option label="剧情发展" value="plot" />
                <el-option label="冲突" value="conflict" />
                <el-option label="揭示" value="revelation" />
                <el-option label="高潮" value="climax" />
                <el-option label="结局" value="ending" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item label="参与角色">
          <el-select
            v-model="eventForm.involved_characters"
            multiple
            placeholder="选择参与的角色"
            style="width: 100%"
          >
            <el-option
              v-for="(char, index) in characters"
              :key="index"
              :label="char.name"
              :value="index"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="内容备注">
          <el-input
            v-model="eventForm.content_notes"
            type="textarea"
            :rows="4"
            placeholder="事件的草稿或额外备注"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" @click="saveEvent" :loading="saving">
          {{ editingEvent ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useProjectStore, type Event, type Character } from '@/stores/project'
import { ElMessage, ElMessageBox } from 'element-plus'

const props = defineProps<{
  projectId: number
  characters?: Character[]
}>()

const store = useProjectStore()
const events = computed(() => store.events)
const sortedEvents = computed(() => {
  return [...events.value].sort((a, b) => a.order_index - b.order_index)
})

const showCreateDialog = ref(false)
const editingEvent = ref<Event | null>(null)
const saving = ref(false)

const defaultForm = {
  name: '',
  description: '',
  chapter: '',
  timeline_position: '',
  importance: 'normal' as const,
  event_type: 'plot' as const,
  involved_characters: [] as number[],
  content_notes: '',
  is_completed: false
}

const eventForm = ref({ ...defaultForm })

onMounted(() => {
  loadEvents()
})

watch(() => props.projectId, () => {
  loadEvents()
})

async function loadEvents() {
  await store.fetchEvents(props.projectId)
}

function getCharacterName(index: number): string {
  if (!props.characters || !props.characters[index]) {
    return `角色${index + 1}`
  }
  return props.characters[index].name || `角色${index + 1}`
}

function getTimelineType(event: Event): string {
  const types: Record<string, string> = {
    'climax': 'danger',
    'conflict': 'warning',
    'revelation': 'success',
    'ending': 'info',
    'plot': ''
  }
  return types[event.event_type] || ''
}

function getTimelineColor(event: Event): string {
  const colors: Record<string, string> = {
    'critical': '#f56c6c',
    'major': '#e6a23c',
    'normal': '#409eff',
    'minor': '#909399'
  }
  return event.is_completed ? '#67c23a' : (colors[event.importance] || '#409eff')
}

function getImportanceType(importance: string): string {
  const types: Record<string, string> = {
    'critical': 'danger',
    'major': 'warning',
    'normal': '',
    'minor': 'info'
  }
  return types[importance] || ''
}

function getImportanceLabel(importance: string): string {
  const labels: Record<string, string> = {
    'critical': '关键',
    'major': '重要',
    'normal': '普通',
    'minor': '次要'
  }
  return labels[importance] || importance
}

function getEventTypeColor(type: string): string {
  const colors: Record<string, string> = {
    'climax': 'danger',
    'conflict': 'warning',
    'revelation': 'success',
    'ending': 'info',
    'plot': ''
  }
  return colors[type] || ''
}

function getEventTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    'plot': '剧情',
    'conflict': '冲突',
    'revelation': '揭示',
    'climax': '高潮',
    'ending': '结局'
  }
  return labels[type] || type
}

async function toggleCompleted(event: Event) {
  await store.updateEvent(props.projectId, event.id, { is_completed: event.is_completed })
  ElMessage.success(event.is_completed ? '已标记为完成' : '已取消完成标记')
}

function handleCommand(cmd: string, event: Event) {
  if (cmd === 'edit') {
    editingEvent.value = event
    eventForm.value = {
      name: event.name,
      description: event.description || '',
      chapter: event.chapter || '',
      timeline_position: event.timeline_position || '',
      importance: event.importance,
      event_type: event.event_type,
      involved_characters: event.involved_characters || [],
      content_notes: event.content_notes || '',
      is_completed: event.is_completed
    }
    showCreateDialog.value = true
  } else if (cmd === 'delete') {
    ElMessageBox.confirm(
      `确定要删除事件 "${event.name}" 吗？`,
      '确认删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    ).then(() => {
      store.deleteEvent(props.projectId, event.id)
      ElMessage.success('事件已删除')
    })
  }
}

function closeDialog() {
  showCreateDialog.value = false
  editingEvent.value = null
  eventForm.value = { ...defaultForm }
}

async function saveEvent() {
  if (!eventForm.value.name.trim()) {
    ElMessage.warning('请输入事件名称')
    return
  }
  
  saving.value = true
  try {
    if (editingEvent.value) {
      await store.updateEvent(props.projectId, editingEvent.value.id, eventForm.value)
      ElMessage.success('事件已更新')
    } else {
      await store.createEvent(props.projectId, {
        ...eventForm.value,
        order_index: events.value.length
      })
      ElMessage.success('事件已创建')
    }
    closeDialog()
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.event-manager {
  padding: 20px;
}

.event-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.event-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 500;
}

.event-timeline {
  max-height: 70vh;
  overflow-y: auto;
}

.event-card {
  transition: all 0.3s;
}

.event-card.is-completed {
  opacity: 0.7;
  background: #f5f7fa;
}

.event-card.is-completed .event-name {
  text-decoration: line-through;
  color: #909399;
}

.event-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}

.event-title-section {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.event-name {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

.event-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.more-icon {
  padding: 4px;
  cursor: pointer;
  color: #909399;
  border-radius: 4px;
}

.more-icon:hover {
  color: #409eff;
  background: #ecf5ff;
}

.event-description {
  color: #606266;
  font-size: 14px;
  margin: 10px 0;
  line-height: 1.5;
}

.event-characters {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 10px;
}
</style>
