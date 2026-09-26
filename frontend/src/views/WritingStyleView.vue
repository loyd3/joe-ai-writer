<template>
  <div class="writing-style-page">
    <div class="page-header">
      <div class="header-left">
        <div class="title-block">
          <h1 class="page-title">文风库</h1>
          <p class="sub">系统级文风：预设、手建，或从多份范文提炼后在写作中选用（入口：左下角用户菜单）</p>
        </div>
      </div>
    </div>

    <div class="page-body">
      <StyleAgentsPanel />
    </div>
  </div>
</template>

<script setup lang="ts">
import StyleAgentsPanel from '@/components/StyleAgentsPanel.vue'
</script>

<style scoped lang="scss">
.writing-style-page {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--coffee-bg);
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid var(--coffee-border);
  background: var(--coffee-bg-card);
}

.page-title {
  margin: 0 0 4px;
  font-size: 18px;
  font-weight: 600;
  color: var(--coffee-text);
}

.sub {
  margin: 0;
  font-size: 13px;
  color: var(--coffee-text-muted);
}

.page-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
</style>
