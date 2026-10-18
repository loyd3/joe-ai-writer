<template>
  <el-drawer
    v-model="store.open"
    direction="rtl"
    :size="drawerSize"
    class="project-settings-drawer"
    :with-header="false"
    append-to-body
    destroy-on-close
  >
    <div class="drawer-shell">
      <header class="drawer-header">
        <div class="title-block">
          <h2 class="drawer-title">项目设定</h2>
          <p class="drawer-sub">大纲、故事线、角色卡、世界观与关键情节</p>
        </div>
        <div class="header-actions">
          <el-button class="btn" @click="openWritingStyle">文风设置</el-button>
          <el-button class="close-btn" text @click="store.close()">
            <el-icon :size="18"><Close /></el-icon>
          </el-button>
        </div>
      </header>

      <div class="drawer-body">
        <ProjectSettingsManager
          v-if="store.projectId"
          ref="managerRef"
          :project-id="store.projectId"
          layout="drawer"
        />
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { Close } from '@element-plus/icons-vue'
import ProjectSettingsManager from '@/components/ProjectSettingsManager.vue'
import { useProjectSettingsDrawerStore } from '@/stores/projectSettingsDrawer'
import { useSettingsDrawerStore } from '@/stores/settingsDrawer'

const store = useProjectSettingsDrawerStore()
const managerRef = ref<{
  prepareProjectAgent?: () => Promise<boolean>
  onAgentProjectChanged?: () => Promise<void>
} | null>(null)

const drawerSize = computed(() => {
  if (typeof window === 'undefined') return '920px'
  const w = window.innerWidth
  if (w < 768) return '100%'
  return `${Math.min(960, Math.floor(w * 0.82))}px`
})

function openWritingStyle() {
  useSettingsDrawerStore().show('writing-style')
}

watch(
  () => [store.open, store.projectId] as const,
  async ([open]) => {
    if (!open) {
      store.registerHandlers(null, null)
      return
    }
    await nextTick()
    store.registerHandlers(
      () => managerRef.value?.prepareProjectAgent?.() ?? Promise.resolve(true),
      () => managerRef.value?.onAgentProjectChanged?.() ?? Promise.resolve(),
    )
  },
  { immediate: true },
)
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
  justify-content: space-between;
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.close-btn {
  margin: -4px -8px 0 0;
  color: var(--coffee-text-muted);
}

.drawer-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;

  :deep(.project-settings-manager) {
    flex: 1;
    min-height: 0;
  }
}
</style>

<style lang="scss">
.project-settings-drawer.el-drawer {
  .el-drawer__body {
    padding: 0;
    height: 100%;
    overflow: hidden;
  }
}
</style>
