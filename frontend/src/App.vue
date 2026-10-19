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
  --coffee-primary-rgb: 74, 91, 184;
  /* 主色调 */
  --coffee-primary: #4A5BB8;
  --coffee-primary-light: #6B78C9;
  --coffee-primary-dark: #3A4894;

  /* 背景色 */
  --coffee-bg: #f4f5f8;
  --coffee-bg-warm: #eceef4;
  --coffee-bg-card: #ffffff;

  /* 文字色（降对比） */
  --coffee-text: #3a3f4a;
  --coffee-text-secondary: #5c6370;
  --coffee-text-muted: #848b98;
  --coffee-text-light: #a4abb6;

  /* 边框/分隔线 */
  --coffee-border: #d8dae2;
  --coffee-border-light: #e6e7ed;
  --coffee-divider: #eef0f4;

  /* 主色 tint 层次（theme store 按模式改写） */
  --coffee-primary-tint: #f0f2fa;
  --coffee-primary-tint-strong: #d5daf0;

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
  --el-color-primary: #4A5BB8;
  --el-color-primary-rgb: 74, 91, 184;
  --el-color-primary-light-3: #7884ca;
  --el-color-primary-light-5: #a5addc;
  --el-color-primary-light-7: #c9cee9;
  --el-color-primary-light-8: #dde0f1;
  --el-color-primary-light-9: #f0f2fa;
  --el-color-primary-dark-2: #3a4894;

  /* 语义色（低饱和，theme store 按模式改写） */
  --coffee-success: #4a9e7f;
  --coffee-success-rgb: 74, 158, 127;
  --coffee-warning: #d9a03f;
  --coffee-warning-rgb: 217, 160, 63;
  --coffee-danger: #d96a6a;
  --coffee-danger-rgb: 217, 106, 106;
  --coffee-info: #6b8cae;
  --coffee-info-rgb: 107, 140, 174;

  /* Element Plus 语义色初值（与 coffee-* 对齐） */
  --el-color-success: var(--coffee-success);
  --el-color-warning: var(--coffee-warning);
  --el-color-danger: var(--coffee-danger);
  --el-color-info: var(--coffee-info);
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
  font-weight: 400;
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
  font-weight: 400;
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
