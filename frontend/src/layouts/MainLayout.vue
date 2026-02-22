<template>
  <div class="main-layout">
    <el-container class="layout-container">
      <el-aside width="250px" class="sidebar">
        <div class="logo">
          <el-icon><Document /></el-icon>
          <span>Joe AI Writer</span>
        </div>
        <ProjectSidebar />
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
import ProjectSidebar from '@/components/ProjectSidebar.vue'
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.sidebar {
  background: #fff;
  border-right: 1px solid #e4e7ed;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  font-size: 18px;
  font-weight: 600;
  color: #409eff;
  border-bottom: 1px solid #e4e7ed;
  gap: 10px;
}

.main-content {
  padding: 0;
  background: #f5f5f5;
  overflow: hidden;
}
</style>