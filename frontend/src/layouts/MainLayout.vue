<template>
  <div class="main-layout">
    <el-container class="layout-container">
      <el-aside width="260px" class="sidebar">
        <div class="logo">
          <el-icon class="logo-icon"><EditPen /></el-icon>
          <div class="logo-text-wrap">
            <span class="logo-text">墨言</span>
            <span class="logo-sub">AI 辅助写作</span>
          </div>
        </div>

        <!-- 全局搜索 -->
        <div class="search-section">
          <GlobalSearch />
        </div>

        <div class="sidebar-content">
          <ProjectSidebar />
        </div>
        
        <!-- 用户信息区 -->
        <div class="user-section">
          <el-divider class="coffee-divider" />
          <el-dropdown trigger="click" @command="handleUserCommand">
            <div class="user-info">
              <div class="user-avatar">
                <el-icon><UserFilled /></el-icon>
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
                <el-dropdown-item command="settings">
                  <el-icon><Setting /></el-icon> 设置
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon> 退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-aside>
      
      <el-container>
        <el-main class="main-content">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
    <ThemeSettingsDialog v-model="showSettingsDialog" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import ProjectSidebar from '@/components/ProjectSidebar.vue'
import ThemeSettingsDialog from '@/components/ThemeSettingsDialog.vue'
import GlobalSearch from '@/components/GlobalSearch.vue'
import { EditPen, UserFilled, ArrowDown, User, Setting, SwitchButton } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()
const showSettingsDialog = ref(false)

async function handleUserCommand(command: string) {
  switch (command) {
    case 'profile':
      ElMessage.info('个人中心功能开发中')
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
  background: linear-gradient(180deg, var(--coffee-bg) 0%, var(--coffee-bg-warm) 100%);
  border-right: 1px solid var(--coffee-border);
  display: flex;
  flex-direction: column;
  box-shadow: 4px 0 20px var(--coffee-sidebar-shadow);
}

.logo {
  height: 70px;
  display: flex;
  align-items: center;
  padding: 0 24px;
  gap: 12px;
  border-bottom: 1px solid var(--coffee-border-light);
  
  .logo-icon {
    width: 40px;
    height: 40px;
    background: var(--coffee-gradient-primary);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    color: #fff;
  }
  
  .logo-text-wrap {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .logo-text {
    font-size: 18px;
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

.user-section {
  padding: 0 16px 16px;
  
  .coffee-divider {
    margin: 8px 0 16px;
    border-color: var(--coffee-border);
  }
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  
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
  overflow: hidden;
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
