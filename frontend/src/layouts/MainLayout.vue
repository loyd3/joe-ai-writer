<template>
  <div class="main-layout">
    <el-container class="layout-container">
      <el-aside width="260px" class="sidebar">
        <div class="logo">
          <el-icon class="logo-icon"><EditPen /></el-icon>
          <span class="logo-text">Joe AI Writer</span>
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
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import ProjectSidebar from '@/components/ProjectSidebar.vue'
import { EditPen, UserFilled, ArrowDown, User, Setting, SwitchButton } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()

async function handleUserCommand(command: string) {
  switch (command) {
    case 'profile':
      ElMessage.info('个人中心功能开发中')
      break
    case 'settings':
      ElMessage.info('设置功能开发中')
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
  background: #faf8f5;
}

.layout-container {
  height: 100%;
}

.sidebar {
  background: linear-gradient(180deg, #fdfbf7 0%, #f8f4ed 100%);
  border-right: 1px solid #e8e0d5;
  display: flex;
  flex-direction: column;
  box-shadow: 4px 0 20px rgba(92, 64, 51, 0.04);
}

.logo {
  height: 70px;
  display: flex;
  align-items: center;
  padding: 0 24px;
  gap: 12px;
  border-bottom: 1px solid #f0e6d8;
  
  .logo-icon {
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, #8b5a2b 0%, #a67c52 100%);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    color: #fff;
  }
  
  .logo-text {
    font-size: 18px;
    font-weight: 700;
    color: #5c4033;
    letter-spacing: 1px;
  }
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
}

.user-section {
  padding: 0 16px 16px;
  
  .coffee-divider {
    margin: 8px 0 16px;
    border-color: #e8e0d5;
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
    background: rgba(139, 90, 43, 0.06);
  }
  
  .user-avatar {
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, #d4c4a8 0%, #c4b49a 100%);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #5c4033;
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
      color: #5c4033;
    }
    
    .user-role {
      font-size: 12px;
      color: #a68b6a;
    }
  }
  
  .arrow-icon {
    font-size: 12px;
    color: #a68b6a;
  }
}

.main-content {
  padding: 0;
  background: linear-gradient(135deg, #faf8f5 0%, #f5f0e8 100%);
  overflow: hidden;
}

/* 下拉菜单样式 */
:deep(.user-dropdown) {
  .el-dropdown-menu__item {
    padding: 10px 16px;
    
    .el-icon {
      margin-right: 8px;
      color: #8b7355;
    }
    
    &:hover {
      background: #faf6f1;
      color: #8b5a2b;
      
      .el-icon {
        color: #8b5a2b;
      }
    }
  }
}
</style>
