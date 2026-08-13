<template>
  <div class="main-layout">
    <el-container class="layout-container">
      <el-aside width="260px" class="sidebar">
        <div class="logo" @click="goToHome" @keydown.enter="goToHome" role="button" tabindex="0" title="回到我的创作空间">
          <el-icon class="logo-icon"><EditPen /></el-icon>
          <div class="logo-text-wrap">
            <span class="logo-text">墨心</span>
            <span class="logo-sub">AI 辅助写作</span>
          </div>
        </div>

        <!-- 全局搜索 -->
        <div class="search-section">
          <GlobalSearch />
        </div>

        <!-- 导航菜单 -->
        <div class="nav-menu">
          <div 
            class="nav-item" 
            :class="{ active: $route.path === '/' }"
            @click="$router.push('/')"
          >
            <el-icon><HomeFilled /></el-icon>
            <span>我的项目</span>
          </div>
          <div 
            class="nav-item" 
            :class="{ active: $route.path === '/dashboard' }"
            @click="$router.push('/dashboard')"
          >
            <el-icon><DataLine /></el-icon>
            <span>数据看板</span>
          </div>
          <div 
            class="nav-item" 
            :class="{ active: $route.path === '/hot-topics' }"
            @click="$router.push('/hot-topics')"
          >
            <el-icon><TrendCharts /></el-icon>
            <span>热点写作</span>
          </div>
          <div 
            class="nav-item" 
            :class="{ active: $route.path === '/brainstorm-writing' }"
            @click="$router.push('/brainstorm-writing')"
          >
            <el-icon><Lightning /></el-icon>
            <span>脑洞写作</span>
          </div>
          <div 
            class="nav-item" 
            :class="{ active: $route.path === '/copywriting-writing' }"
            @click="$router.push('/copywriting-writing')"
          >
            <el-icon><Promotion /></el-icon>
            <span>文案写作</span>
          </div>
          <div 
            class="nav-item" 
            :class="{ active: $route.path === '/ai-story-generator' }"
            @click="$router.push('/ai-story-generator')"
          >
            <el-icon><MagicStick /></el-icon>
            <span>AI故事生成</span>
          </div>
        </div>

        <div class="sidebar-content">
          <ProjectSidebar />
        </div>
        
        <!-- 用户信息区 -->
        <div class="user-section">
          <el-divider class="coffee-divider" />
          <div class="user-row">
            <button
              type="button"
              class="mode-toggle"
              :title="themeStore.isDark() ? '切换为浅色模式' : '切换为深色模式'"
              @click="themeStore.toggleMode()"
            >
              <el-icon><Moon v-if="themeStore.isDark()" /><Sunny v-else /></el-icon>
            </button>
            <el-dropdown trigger="click" @command="handleUserCommand" class="user-dropdown-wrap">
              <div class="user-info">
                <div class="user-avatar">
                  <el-avatar v-if="authStore.currentUser?.avatar_url" :size="36" :src="sidebarAvatarUrl" />
                  <el-icon v-else><UserFilled /></el-icon>
                </div>
                <div class="user-meta">
                  <span class="username">{{ authStore.currentUser?.username }}</span>
                  <span class="user-role">创作者</span>
                </div>
                <el-icon class="arrow-icon"><ArrowDown /></el-icon>
              </div>
              <template #dropdown>
                <el-dropdown-menu class="user-dropdown">
                  <el-dropdown-item command="profile">
                    <el-icon><User /></el-icon> 个人中心
                  </el-dropdown-item>
                  <el-dropdown-item command="aiConfig">
                    <el-icon><Cpu /></el-icon> AI 模型配置
                  </el-dropdown-item>
                  <el-dropdown-item command="settings">
                    <el-icon><Setting /></el-icon> 主题设置
                  </el-dropdown-item>
                  <el-dropdown-item divided command="logout">
                    <el-icon><SwitchButton /></el-icon> 退出登录
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </el-aside>
      
      <el-container>
        <el-main class="main-content">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
    <ThemeSettingsDialog v-model="showSettingsDialog" />
    <el-drawer
      v-model="showAIConfigDrawer"
      title="AI 模型配置"
      size="520px"
      direction="rtl"
      class="ai-config-drawer"
      destroy-on-close
    >
      <AIConfigPanel />
    </el-drawer>
    <el-drawer
      v-model="showProfileDrawer"
      title="个人中心"
      size="480px"
      direction="rtl"
      class="profile-drawer"
      destroy-on-close
    >
      <ProfileCenter />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { computed } from 'vue'
import ProjectSidebar from '@/components/ProjectSidebar.vue'
import ThemeSettingsDialog from '@/components/ThemeSettingsDialog.vue'
import GlobalSearch from '@/components/GlobalSearch.vue'
import AIConfigPanel from '@/components/AIConfigPanel.vue'
import ProfileCenter from '@/components/ProfileCenter.vue'
import { API_BASE_URL } from '@/api'
import { EditPen, UserFilled, ArrowDown, User, Setting, SwitchButton, Cpu, HomeFilled, DataLine, TrendCharts, MagicStick, Lightning, Promotion, Sunny, Moon } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()
const showSettingsDialog = ref(false)
const showAIConfigDrawer = ref(false)
const showProfileDrawer = ref(false)

// 支持环境变量覆盖 API_BASE_URL
const BASE_URL = import.meta.env.VITE_API_URL || API_BASE_URL

const sidebarAvatarUrl = computed(() => {
  const url = authStore.currentUser?.avatar_url
  if (!url) return ''
  const base = BASE_URL.replace(/\/api\/?$/, '')
  return base + url
})

function goToHome() {
  router.push('/')
}

async function handleUserCommand(command: string) {
  switch (command) {
    case 'profile':
      showProfileDrawer.value = true
      break
    case 'aiConfig':
      showAIConfigDrawer.value = true
      break
    case 'settings':
      showSettingsDialog.value = true
      break
    case 'logout':
      try {
        await ElMessageBox.confirm(
          '确定要退出登录吗？',
          '退出确认',
          {
            confirmButtonText: '退出',
            cancelButtonText: '取消',
            type: 'warning',
          }
        )
        await authStore.logout()
        router.push('/login')
      } catch {
        // 用户取消
      }
      break
  }
}
</script>

<style scoped lang="scss">
.main-layout {
  height: 100vh;
  background: var(--coffee-bg);
}

.layout-container {
  height: 100%;
}

.sidebar {
  background: var(--coffee-bg-warm);
  border-right: 1px solid var(--coffee-border);
  display: flex;
  flex-direction: column;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 10px;
  border-bottom: 1px solid var(--coffee-border-light);
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: var(--coffee-bg-hover);
  }

  .logo-icon {
    width: 34px;
    height: 34px;
    background: var(--coffee-gradient-primary);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 17px;
    color: #fff;
  }

  .logo-text-wrap {
    display: flex;
    flex-direction: column;
    gap: 1px;
  }
  .logo-text {
    font-size: 16px;
    font-weight: 700;
    color: var(--coffee-text);
    letter-spacing: 1px;
  }
  .logo-sub {
    font-size: 11px;
    color: var(--coffee-text-muted);
    letter-spacing: 0.5px;
  }
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
}

.search-section {
  padding: 12px 16px;
  border-bottom: 1px solid var(--coffee-border-light);
}

.nav-menu {
  padding: 8px 16px;
  border-bottom: 1px solid var(--coffee-border-light);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: 2px;
  color: var(--coffee-text-secondary);
  font-size: 14px;

  .el-icon {
    font-size: 17px;
  }

  &:hover {
    background: var(--coffee-bg-hover);
    color: var(--coffee-text);
  }

  &.active {
    background: rgba(var(--coffee-primary-rgb), 0.1);
    color: var(--coffee-primary);
    font-weight: 500;
  }
}

.user-section {
  padding: 0 16px 16px;

  .coffee-divider {
    margin: 8px 0 16px;
    border-color: var(--coffee-border);
  }
}

.user-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mode-toggle {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: var(--coffee-text-muted);
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: var(--coffee-bg-hover);
    color: var(--coffee-primary);
  }
}

.user-dropdown-wrap {
  flex: 1;
  min-width: 0;
  width: 100%;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  width: 100%;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    background: var(--coffee-bg-hover);
  }
  
  .user-avatar {
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, var(--coffee-border) 0%, var(--coffee-text-light) 100%);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--coffee-text);
    font-size: 18px;
  }
  
  .user-meta {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
    
    .username {
      font-size: 14px;
      font-weight: 600;
      color: var(--coffee-text);
    }
    
    .user-role {
      font-size: 12px;
      color: var(--coffee-text-light);
    }
  }
  
  .arrow-icon {
    font-size: 12px;
    color: var(--coffee-text-light);
  }
}

.main-content {
  padding: 0;
  background: var(--coffee-gradient-light);
  overflow-y: auto; /* 内容超出时主区域可滚动 */
  min-height: 0;
}

/* 下拉菜单样式 */
:deep(.user-dropdown) {
  .el-dropdown-menu__item {
    padding: 10px 16px;
    
    .el-icon {
      margin-right: 8px;
      color: var(--coffee-text-muted);
    }
    
    &:hover {
      background: var(--coffee-bg-warm);
      color: var(--coffee-primary);
      
      .el-icon {
        color: var(--coffee-primary);
      }
    }
  }
}
</style>
