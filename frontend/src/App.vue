<template>
  <router-view />
</template>

<script setup lang="ts">
</script>

<style>
/* ===== 全局样式变量 - 深邃咖啡色调主题 ===== */
:root {
  /* 主色调 - 加深 */
  --coffee-primary: #5d3a1a;
  --coffee-primary-light: #8b5a2b;
  --coffee-primary-dark: #3d2916;
  
  /* 背景色 */
  --coffee-bg: #faf8f5;
  --coffee-bg-warm: #f5f0e8;
  --coffee-bg-card: #ffffff;
  
  /* 文字色 - 加深 */
  --coffee-text: #3d2916;
  --coffee-text-secondary: #5d3a1a;
  --coffee-text-muted: #8b5a2b;
  --coffee-text-light: #a67c52;
  
  /* 边框/分隔线 */
  --coffee-border: #e0d5c8;
  --coffee-border-light: #ede5dc;
  --coffee-divider: #f0e8dc;
  
  /* 阴影 */
  --coffee-shadow: rgba(61, 41, 22, 0.08);
  --coffee-shadow-hover: rgba(61, 41, 22, 0.15);
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

/* 主要按钮 */
.el-button--primary {
  --el-button-bg-color: var(--coffee-primary);
  --el-button-border-color: var(--coffee-primary);
  --el-button-hover-bg-color: var(--coffee-primary-light);
  --el-button-hover-border-color: var(--coffee-primary-light);
  --el-button-active-bg-color: var(--coffee-primary-dark);
  --el-button-active-border-color: var(--coffee-primary-dark);
}

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
  --el-menu-hover-bg-color: rgba(93, 58, 26, 0.06);
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
  --el-dropdown-menuItem-hover-fill: rgba(93, 58, 26, 0.06);
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
  background: rgba(93, 58, 26, 0.2);
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
  background: rgba(250, 248, 245, 0.9);
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
