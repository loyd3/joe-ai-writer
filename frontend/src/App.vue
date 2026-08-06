<template>
  <router-view />
</template>

<script setup lang="ts">
import { useThemeStore } from '@/stores/theme'
useThemeStore()
</script>

<style>
/* ===== 全局样式变量 - 鲜艳咖啡色调主题 ===== */
:root {
  /* 主色调 RGB 分量（用于灵活 rgba） */
  --coffee-primary-rgb: 166, 94, 46;
  /* 主色调 */
  --coffee-primary: #a65e2e;
  --coffee-primary-light: #c97f4a;
  --coffee-primary-dark: #7a4318;
  
  /* 背景色 */
  --coffee-bg: #fdfbf7;
  --coffee-bg-warm: #f8f3ec;
  --coffee-bg-card: #ffffff;
  
  /* 文字色 */
  --coffee-text: #4a2c17;
  --coffee-text-secondary: #6b4423;
  --coffee-text-muted: #a67c52;
  --coffee-text-light: #c9a86c;
  
  /* 边框/分隔线 */
  --coffee-border: #e8dcd0;
  --coffee-border-light: #f2e9e0;
  --coffee-divider: #f5ebe0;
  
  /* 阴影 */
  --coffee-shadow: rgba(var(--coffee-primary-rgb), 0.08);
  --coffee-shadow-hover: rgba(var(--coffee-primary-rgb), 0.15);
  --coffee-selection: rgba(var(--coffee-primary-rgb), 0.25);
  --coffee-bg-hover: rgba(var(--coffee-primary-rgb), 0.06);
  --coffee-sidebar-shadow: rgba(var(--coffee-primary-rgb), 0.04);
  
  /* 渐变 */
  --coffee-gradient-primary: linear-gradient(135deg, var(--coffee-primary) 0%, var(--coffee-primary-light) 100%);
  --coffee-gradient-light: linear-gradient(135deg, var(--coffee-bg-warm) 0%, var(--coffee-divider) 100%);

  /* Element Plus 主色初值（默认咖啡棕，theme store 初始化后会按当前主题改写） */
  --el-color-primary: #a65e2e;
  --el-color-primary-rgb: 166, 94, 46;
  --el-color-primary-light-3: #c18e6d;
  --el-color-primary-light-5: #d3af97;
  --el-color-primary-light-7: #e4cfc0;
  --el-color-primary-light-8: #eddfd5;
  --el-color-primary-light-9: #f6efea;
  --el-color-primary-dark-2: #854b25;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
  background: var(--coffee-bg);
  color: var(--coffee-text);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ===== Element Plus 主题覆盖 ===== */

/* 输入框 */
.el-input__wrapper {
  --el-input-bg-color: var(--coffee-bg);
  --el-input-border-color: var(--coffee-border);
  --el-input-hover-border-color: var(--coffee-primary-light);
  --el-input-focus-border-color: var(--coffee-primary);
}

/* 菜单 */
.el-menu {
  --el-menu-bg-color: transparent;
  --el-menu-hover-bg-color: var(--coffee-shadow);
  --el-menu-text-color: var(--coffee-text-secondary);
  --el-menu-hover-text-color: var(--coffee-primary);
  --el-menu-active-color: var(--coffee-primary);
}

/* 卡片 */
.el-card {
  --el-card-bg-color: var(--coffee-bg-card);
  --el-card-border-color: var(--coffee-border-light);
}

/* 对话框 */
.el-dialog {
  --el-dialog-bg-color: var(--coffee-bg-card);
  --el-dialog-title-font-size: 18px;
  border-radius: 16px;
  overflow: hidden;
}

.el-dialog__header {
  border-bottom: 1px solid var(--coffee-border-light);
  padding: 20px 24px;
}

.el-dialog__title {
  color: var(--coffee-text);
  font-weight: 600;
}

.el-dialog__body {
  padding: 24px;
  color: var(--coffee-text-secondary);
}

.el-dialog__footer {
  border-top: 1px solid var(--coffee-border-light);
  padding: 16px 24px;
}

/* 下拉菜单 */
.el-dropdown-menu {
  --el-dropdown-menuItem-hover-fill: var(--coffee-shadow);
  --el-dropdown-menuItem-hover-color: var(--coffee-primary);
}

/* 滚动条 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: var(--coffee-border);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--coffee-text-light);
}

/* 选中文字 */
::selection {
  background: var(--coffee-selection);
  color: var(--coffee-text);
}

/* 链接 */
a {
  color: var(--coffee-primary);
  text-decoration: none;
  transition: color 0.2s;
}

a:hover {
  color: var(--coffee-primary-light);
}

/* 加载动画 */
.el-loading-mask {
  background: var(--coffee-bg);
}

/* 消息提示 */
.el-message {
  --el-message-bg-color: var(--coffee-bg-card);
  --el-message-border-color: var(--coffee-border);
}

/* 空状态 */
.el-empty {
  --el-empty-fill-color-0: var(--coffee-border);
  --el-empty-fill-color-1: var(--coffee-border-light);
  --el-empty-description-margin-top: 16px;
  color: var(--coffee-text-muted);
}

/* 分割线 */
.el-divider {
  --el-border-color: var(--coffee-border);
}

/* 表单 */
.el-form-item__label {
  color: var(--coffee-text);
}

/* 消息框 */
.el-message-box {
  --el-messagebox-title-color: var(--coffee-text);
  --el-messagebox-content-color: var(--coffee-text-secondary);
  border-radius: 16px;
}
</style>
