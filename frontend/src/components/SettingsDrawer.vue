<template>
  <el-drawer
    v-model="store.open"
    direction="rtl"
    :size="drawerSize"
    class="settings-drawer"
    :with-header="false"
    append-to-body
  >
    <div class="drawer-shell">
      <header class="drawer-header">
        <div class="title-block">
          <h2 class="drawer-title">{{ store.meta.title }}</h2>
          <p class="drawer-sub">{{ store.meta.subtitle }}</p>
        </div>
        <el-button class="close-btn" text @click="store.close()">
          <el-icon :size="18"><Close /></el-icon>
        </el-button>
      </header>

      <div class="drawer-body" :class="{ flush: store.panel === 'writing-style' }">
        <ProfileCenter v-if="store.panel === 'profile'" hide-title />
        <StyleAgentsPanel v-else-if="store.panel === 'writing-style'" compact />
        <AIConfigPanel v-else-if="store.panel === 'ai-config'" />
        <ThemeSettingsPanel v-else-if="store.panel === 'theme'" />
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Close } from '@element-plus/icons-vue'
import { useSettingsDrawerStore } from '@/stores/settingsDrawer'
import ProfileCenter from '@/components/ProfileCenter.vue'
import StyleAgentsPanel from '@/components/StyleAgentsPanel.vue'
import AIConfigPanel from '@/components/AIConfigPanel.vue'
import ThemeSettingsPanel from '@/components/ThemeSettingsPanel.vue'

const store = useSettingsDrawerStore()

const drawerSize = computed(() => {
  if (typeof window === 'undefined') return '720px'
  const w = window.innerWidth
  if (w < 768) return '100%'
  if (store.panel === 'writing-style' || store.panel === 'ai-config') {
    return `${Math.min(840, Math.floor(w * 0.72))}px`
  }
  return `${Math.min(640, Math.floor(w * 0.55))}px`
})
</script>

<style scoped lang="scss">
.drawer-shell {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--coffee-bg);
}

.drawer-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px 20px 12px;
  border-bottom: 1px solid var(--coffee-border);
  background: var(--coffee-bg-card);
  flex-shrink: 0;
}

.title-block {
  flex: 1;
  min-width: 0;
}

.drawer-title {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  color: var(--coffee-text);
  line-height: 1.3;
}

.drawer-sub {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--coffee-text-muted);
  line-height: 1.4;
}

.close-btn {
  margin: -4px -8px 0 0;
  color: var(--coffee-text-muted);
}

.drawer-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 16px 20px 24px;

  &.flush {
    padding: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
}
</style>

<style lang="scss">
.settings-drawer.el-drawer {
  .el-drawer__body {
    padding: 0;
    height: 100%;
    overflow: hidden;
  }
}
</style>
