<template>
  <div class="dashboard-view">
    <div class="dashboard-header">
      <h1>
        <el-icon><DataLine /></el-icon>
        写作数据看板
      </h1>
      <p class="subtitle">追踪你的创作进度和 AI 使用情况</p>
    </div>

    <!-- 概览卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon projects">
          <el-icon><FolderOpened /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ stats.totalProjects }}</span>
          <span class="stat-label">项目总数</span>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon documents">
          <el-icon><Document /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ stats.totalDocuments }}</span>
          <span class="stat-label">文档总数</span>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon words">
          <el-icon><EditPen /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ formatNumber(stats.totalWords) }}</span>
          <span class="stat-label">总字数</span>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon ai">
          <el-icon><Cpu /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ stats.totalAIInteractions }}</span>
          <span class="stat-label">AI 交互次数</span>
        </div>
      </div>
    </div>

    <!-- 详细数据 -->
    <div class="dashboard-content">
      <!-- 最近活跃项目 -->
      <div class="dashboard-section">
        <h3>
          <el-icon><TrendCharts /></el-icon>
          最近活跃
        </h3>
        <div class="recent-list">
          <div 
            v-for="project in recentProjects" 
            :key="project.id"
            class="recent-item"
            @click="goToProject(project.id)"
          >
            <div class="recent-info">
              <span class="recent-title">{{ project.title }}</span>
              <span class="recent-meta">
                {{ project.documentCount }} 篇文档 · {{ formatNumber(project.wordCount) }} 字
              </span>
            </div>
            <el-progress 
              :percentage="project.progress" 
              :stroke-width="6"
              :show-text="false"
              class="recent-progress"
            />
          </div>
        </div>
      </div>

      <!-- AI 使用统计 -->
      <div class="dashboard-section">
        <h3>
          <el-icon><MagicStick /></el-icon>
          AI 助手使用统计
        </h3>
        <div class="ai-stats">
          <div class="ai-stat-item">
            <span class="ai-label">润色</span>
            <el-progress 
              :percentage="getAIUsagePercentage('polish')" 
              :format="() => aiUsage.polish"
              :stroke-width="8"
            />
          </div>
          <div class="ai-stat-item">
            <span class="ai-label">续写</span>
            <el-progress 
              :percentage="getAIUsagePercentage('continue')" 
              :format="() => aiUsage.continue"
              :stroke-width="8"
            />
          </div>
          <div class="ai-stat-item">
            <span class="ai-label">头脑风暴</span>
            <el-progress 
              :percentage="getAIUsagePercentage('brainstorm')" 
              :format="() => aiUsage.brainstorm"
              :stroke-width="8"
            />
          </div>
          <div class="ai-stat-item">
            <span class="ai-label">对话</span>
            <el-progress 
              :percentage="getAIUsagePercentage('chat')" 
              :format="() => aiUsage.chat"
              :stroke-width="8"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 写作目标 -->
    <div class="dashboard-section goals-section">
      <h3>
        <el-icon><Aim /></el-icon>
        写作目标
      </h3>
      <div class="goals-grid">
        <div class="goal-card">
          <div class="goal-header">
            <span class="goal-title">今日目标</span>
            <el-button link size="small" @click="editGoal('daily')">
              <el-icon><Edit /></el-icon>
            </el-button>
          </div>
          <div class="goal-progress">
            <el-progress
              type="dashboard"
              :percentage="dailyGoalProgress"
              :color="goalColors"
            />
            <div class="goal-detail">
              <span class="current">{{ stats.todayWords }}</span>
              <span class="target">/ {{ goals.daily }} 字</span>
            </div>
          </div>
        </div>
        
        <div class="goal-card">
          <div class="goal-header">
            <span class="goal-title">本周目标</span>
            <el-button link size="small" @click="editGoal('weekly')">
              <el-icon><Edit /></el-icon>
            </el-button>
          </div>
          <div class="goal-progress">
            <el-progress
              type="dashboard"
              :percentage="weeklyGoalProgress"
              :color="goalColors"
            />
            <div class="goal-detail">
              <span class="current">{{ stats.weekWords }}</span>
              <span class="target">/ {{ goals.weekly }} 字</span>
            </div>
          </div>
        </div>

        <div class="goal-card streak-card">
          <div class="streak-header">
            <el-icon><Calendar /></el-icon>
            <span>连续打卡</span>
          </div>
          <div class="streak-number">{{ stats.streakDays }}</div>
          <div class="streak-label">天</div>
        </div>
      </div>
    </div>

    <!-- 编辑目标对话框 -->
    <el-dialog
      v-model="showGoalDialog"
      title="设置写作目标"
      width="400px"
      class="coffee-dialog"
    >
      <el-form label-width="100px">
        <el-form-item :label="goalLabel">
          <el-input-number 
            v-model="editingGoalValue" 
            :min="100" 
            :max="100000"
            :step="500"
          />
          <span class="unit">字</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showGoalDialog = false">取消</el-button>
        <el-button type="primary" @click="saveGoal">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import {
  DataLine,
  FolderOpened,
  Document,
  EditPen,
  Cpu,
  TrendCharts,
  MagicStick,
  Aim,
  Edit,
  Calendar
} from '@element-plus/icons-vue'

const router = useRouter()
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// 创建 axios 实例
const api = axios.create({
  baseURL: `${API_BASE_URL}/api`
})

// 请求拦截器
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 统计数据
const stats = ref({
  totalProjects: 0,
  totalDocuments: 0,
  totalWords: 0,
  totalAIInteractions: 0,
  todayWords: 0,
  weekWords: 0,
  streakDays: 0
})

// 写作目标
const goals = ref({
  daily: 1000,
  weekly: 7000
})

// AI 使用统计
const aiUsage = ref({
  polish: 0,
  continue: 0,
  brainstorm: 0,
  chat: 0,
  total: 0
})

// 最近活跃项目
const recentProjects = ref<any[]>([])

// 编辑目标
const showGoalDialog = ref(false)
const editingGoalType = ref<'daily' | 'weekly'>('daily')
const editingGoalValue = ref(1000)

const goalLabel = computed(() => 
  editingGoalType.value === 'daily' ? '每日目标' : '每周目标'
)

const dailyGoalProgress = computed(() => {
  const progress = Math.round((stats.value.todayWords / goals.value.daily) * 100)
  return Math.min(progress, 100)
})

const weeklyGoalProgress = computed(() => {
  const progress = Math.round((stats.value.weekWords / goals.value.weekly) * 100)
  return Math.min(progress, 100)
})

const goalColors = [
  { color: '#f56c6c', percentage: 20 },
  { color: '#e6a23c', percentage: 40 },
  { color: '#5cb87a', percentage: 60 },
  { color: '#1989fa', percentage: 80 },
  { color: '#6f7ad3', percentage: 100 }
]

onMounted(async () => {
  await loadDashboardData()
})

async function loadDashboardData() {
  try {
    const res = await api.get('/dashboard/stats')
    const data = res.data
    
    // 更新统计数据
    stats.value = data.stats
    aiUsage.value = data.aiUsage
    recentProjects.value = data.recentProjects
  } catch (error) {
    ElMessage.error('加载数据失败')
    console.error('Dashboard load error:', error)
  }
}

function getAIUsagePercentage(type: keyof typeof aiUsage.value): number {
  if (aiUsage.value.total === 0) return 0
  return Math.round((aiUsage.value[type] / aiUsage.value.total) * 100)
}

function formatNumber(num: number): string {
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  return num.toLocaleString()
}

function goToProject(id: number) {
  router.push(`/project/${id}`)
}

function editGoal(type: 'daily' | 'weekly') {
  editingGoalType.value = type
  editingGoalValue.value = goals.value[type]
  showGoalDialog.value = true
}

function saveGoal() {
  goals.value[editingGoalType.value] = editingGoalValue.value
  // 保存到 localStorage
  localStorage.setItem('writing_goals', JSON.stringify(goals.value))
  showGoalDialog.value = false
  ElMessage.success('目标已保存')
}

// 加载保存的目标
try {
  const savedGoals = localStorage.getItem('writing_goals')
  if (savedGoals) {
    goals.value = { ...goals.value, ...JSON.parse(savedGoals) }
  }
} catch {
  // 忽略解析错误
}
</script>

<style scoped lang="scss">
.dashboard-view {
  padding: 32px 40px;
  max-width: 1200px;
  margin: 0 auto;
}

.dashboard-header {
  margin-bottom: 32px;
  
  h1 {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 28px;
    font-weight: 700;
    color: var(--coffee-text);
    margin-bottom: 8px;
    
    .el-icon {
      color: var(--coffee-primary);
    }
  }
  
  .subtitle {
    color: var(--coffee-text-muted);
    font-size: 15px;
  }
}

// 统计卡片
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 32px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px;
  background: var(--coffee-bg-card);
  border-radius: 16px;
  border: 1px solid var(--coffee-border-light);
  transition: all 0.3s ease;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px var(--coffee-shadow-hover);
  }
  
  .stat-icon {
    width: 56px;
    height: 56px;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    
    .el-icon {
      font-size: 28px;
    }
    
    &.projects {
      background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
      color: #1976d2;
    }
    
    &.documents {
      background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
      color: #7b1fa2;
    }
    
    &.words {
      background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
      color: #388e3c;
    }
    
    &.ai {
      background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
      color: #f57c00;
    }
  }
  
  .stat-info {
    display: flex;
    flex-direction: column;
    gap: 4px;
    
    .stat-value {
      font-size: 28px;
      font-weight: 700;
      color: var(--coffee-text);
    }
    
    .stat-label {
      font-size: 14px;
      color: var(--coffee-text-muted);
    }
  }
}

// 内容区域
.dashboard-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 24px;
}

.dashboard-section {
  background: var(--coffee-bg-card);
  border-radius: 16px;
  padding: 24px;
  border: 1px solid var(--coffee-border-light);
  
  h3 {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 16px;
    font-weight: 600;
    color: var(--coffee-text);
    margin-bottom: 20px;
    
    .el-icon {
      color: var(--coffee-primary);
    }
  }
}

// 最近列表
.recent-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.recent-item {
  padding: 16px;
  background: var(--coffee-bg-warm);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    background: var(--coffee-border-light);
  }
  
  .recent-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
    
    .recent-title {
      font-weight: 500;
      color: var(--coffee-text);
    }
    
    .recent-meta {
      font-size: 13px;
      color: var(--coffee-text-light);
    }
  }
}

// AI 统计
.ai-stats {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.ai-stat-item {
  display: flex;
  align-items: center;
  gap: 12px;
  
  .ai-label {
    width: 70px;
    font-size: 14px;
    color: var(--coffee-text-secondary);
    flex-shrink: 0;
  }
  
  .el-progress {
    flex: 1;
  }
}

// 目标区域
.goals-section {
  grid-column: 1 / -1;
}

.goals-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.goal-card {
  background: var(--coffee-bg-warm);
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  
  .goal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    
    .goal-title {
      font-weight: 500;
      color: var(--coffee-text);
    }
  }
  
  .goal-progress {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    
    .goal-detail {
      .current {
        font-size: 24px;
        font-weight: 700;
        color: var(--coffee-primary);
      }
      
      .target {
        font-size: 14px;
        color: var(--coffee-text-muted);
      }
    }
  }
  
  &.streak-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, var(--coffee-bg-warm) 0%, var(--coffee-bg-card) 100%);
    
    .streak-header {
      display: flex;
      align-items: center;
      gap: 6px;
      color: var(--coffee-text-muted);
      margin-bottom: 8px;
      
      .el-icon {
        font-size: 18px;
      }
    }
    
    .streak-number {
      font-size: 48px;
      font-weight: 700;
      color: var(--coffee-primary);
      line-height: 1;
    }
    
    .streak-label {
      font-size: 14px;
      color: var(--coffee-text-muted);
    }
  }
}

.unit {
  margin-left: 8px;
  color: var(--coffee-text-muted);
}

@media (max-width: 1024px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .dashboard-content {
    grid-template-columns: 1fr;
  }
  
  .goals-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .dashboard-view {
    padding: 20px;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
