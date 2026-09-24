<template>
  <router-view />
</template>

<script setup lang="ts">
import { useThemeStore } from '@/stores/theme'
useThemeStore()
</script>

<style>
/* ===== 全局样式变量 - 默认「墨蓝」浅色主题（theme store 初始化后按当前主题改写） ===== */
:root {
  /* 主色调 RGB 分量（用于灵活 rgba） */
  --coffee-primary-rgb: 62, 75, 196;
  /* 主色调 */
  --coffee-primary: #3E4BC4;
  --coffee-primary-light: #5C68D4;
  --coffee-primary-dark: #323D8F;

  /* 背景色 */
  --coffee-bg: #f5f5f7;
  --coffee-bg-warm: #ececf1;
  --coffee-bg-card: #ffffff;

  /* 文字色 */
  --coffee-text: #15181d;
  --coffee-text-secondary: #3a3e45;
  --coffee-text-muted: #6b7078;
  --coffee-text-light: #8e939a;

  /* 边框/分隔线 */
  --coffee-border: #d5d6dc;
  --coffee-border-light: #e3e4e8;
  --coffee-divider: #ececef;

  /* 阴影 */
  --coffee-shadow: rgba(var(--coffee-primary-rgb), 0.08);
  --coffee-shadow-hover: rgba(var(--coffee-primary-rgb), 0.15);
  --coffee-selection: rgba(var(--coffee-primary-rgb), 0.25);
  --coffee-bg-hover: rgba(var(--coffee-primary-rgb), 0.06);
  --coffee-sidebar-shadow: rgba(var(--coffee-primary-rgb), 0.04);

  /* 中性多层阴影 token（theme store 按模式改写） */
  --app-shadow-sm: 0 1px 2px rgba(16, 18, 24, 0.05);
  --app-shadow-md: 0 2px 6px rgba(16, 18, 24, 0.04), 0 8px 24px rgba(16, 18, 24, 0.06);
  --app-shadow-lg: 0 4px 12px rgba(16, 18, 24, 0.06), 0 16px 40px rgba(16, 18, 24, 0.1);

  /* 圆角规范 */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;

  /* 渐变 */
  --coffee-gradient-primary: linear-gradient(135deg, var(--coffee-primary) 0%, var(--coffee-primary-light) 100%);
  --coffee-gradient-light: linear-gradient(135deg, var(--coffee-bg-warm) 0%, var(--coffee-divider) 100%);

  /* Element Plus 主色初值 */
  --el-color-primary: #3E4BC4;
  --el-color-primary-rgb: 62, 75, 196;
  --el-color-primary-light-3: #6e78d3;
  --el-color-primary-light-5: #9ea4e2;
  --el-color-primary-light-7: #c6c9ef;
  --el-color-primary-light-8: #dbddf5;
  --el-color-primary-light-9: #eff0fb;
  --el-color-primary-dark-2: #323d8f;
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
  font-weight: 500;
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
  border-radius: var(--radius-sm);
  transition: box-shadow 0.2s, border-color 0.2s;
}

.el-input__wrapper.is-focus {
  box-shadow: 0 0 0 3px rgba(var(--coffee-primary-rgb), 0.14);
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
  border-radius: var(--radius-lg);
  box-shadow: var(--app-shadow-sm);
}

/* 对话框 */
.el-dialog {
  --el-dialog-bg-color: var(--coffee-bg-card);
  --el-dialog-title-font-size: 17px;
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--app-shadow-lg);
}

.el-dialog__header {
  border-bottom: 1px solid var(--coffee-border-light);
  padding: 18px 24px;
}

.el-dialog__title {
  color: var(--coffee-text);
  font-weight: 700;
}

.el-dialog__body {
  padding: 24px;
  color: var(--coffee-text-secondary);
  font-weight: 500;
}

.el-dialog__footer {
  border-top: 1px solid var(--coffee-border-light);
  padding: 14px 24px;
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
  border-radius: var(--radius-md);
  box-shadow: var(--app-shadow-md);
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
  border-radius: var(--radius-lg);
  box-shadow: var(--app-shadow-lg);
}
</style>
