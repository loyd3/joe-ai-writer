<template>
  <div class="project-settings-page">
    <div class="page-header">
      <div class="header-left">
        <el-button link class="btn-icon" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <div class="title-block">
          <div class="breadcrumb">
            <span class="crumb" @click="goProject">{{ projectTitle }}</span>
            <el-icon class="sep"><ArrowRight /></el-icon>
            <span class="current">项目设定</span>
          </div>
          <p class="sub">大纲、故事线、角色卡、世界观与关键情节</p>
        </div>
      </div>
      <div class="header-right">
        <el-button class="btn" @click="goWritingStyle">文风设置</el-button>
      </div>
    </div>

    <div class="page-body">
      <ProjectSettingsManager
        v-if="projectIdNum"
        :project-id="projectIdNum"
      />
      <el-empty v-else description="无效的项目" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import { useProjectStore } from '@/stores/project'
import ProjectSettingsManager from '@/components/ProjectSettingsManager.vue'

const route = useRoute()
const router = useRouter()
const store = useProjectStore()

const projectIdNum = computed(() => Number(route.params.id))
const projectTitle = ref('项目')

onMounted(async () => {
  const id = projectIdNum.value
  if (!id || Number.isNaN(id)) return
  try {
    if (store.currentProject?.id === id) {
      projectTitle.value = store.currentProject.title || '项目'
      return
    }
    await store.fetchProject(id)
    projectTitle.value = store.currentProject?.title || '项目'
  } catch {
    projectTitle.value = '项目'
  }
})

function goBack() {
  if (window.history.length > 1) router.back()
  else goProject()
}

function goProject() {
  router.push(`/project/${projectIdNum.value}`)
}

function goWritingStyle() {
  router.push(`/project/${projectIdNum.value}/writing-style`)
}
</script>

<style scoped lang="scss">
.project-settings-page {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--coffee-bg);
  box-sizing: border-box;
}

.page-header {
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 28px;
  border-bottom: 1px solid var(--coffee-border);
  background: var(--coffee-bg-card);
}

.header-left {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.btn-icon {
  margin-top: 2px;
  font-size: 20px;
  color: var(--coffee-text-muted);

  &:hover {
    color: var(--coffee-primary);
  }
}

.title-block {
  min-width: 0;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 18px;
  font-weight: 600;
  color: var(--coffee-text);

  .crumb {
    color: var(--coffee-text-muted);
    cursor: pointer;
    font-weight: 500;

    &:hover {
      color: var(--coffee-primary);
    }
  }

  .sep {
    font-size: 14px;
    color: var(--coffee-text-light);
  }

  .current {
    color: var(--coffee-text);
  }
}

.sub {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--coffee-text-light);
}

.page-body {
  flex: 1;
  min-height: 0;
  width: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  :deep(.project-settings-manager) {
    flex: 1;
    min-height: 0;
    width: 100%;
  }
}
</style>
