<template>
  <div class="settings-page">
    <div class="page-header">
      <div class="title-block">
        <h1 class="page-title">{{ title }}</h1>
        <p v-if="subtitle" class="sub">{{ subtitle }}</p>
      </div>
      <div v-if="$slots.actions" class="header-actions">
        <slot name="actions" />
      </div>
    </div>
    <div class="page-body" :class="[`layout-${layout}`, { flush }]">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    title: string
    subtitle?: string
    /** 内容区不额外加 padding（如文风库自带布局） */
    flush?: boolean
    /** narrow=表单页居中；wide=铺满；fluid=限制可读宽度但不居中挤中间 */
    layout?: 'narrow' | 'wide' | 'fluid'
  }>(),
  { layout: 'fluid' },
)
</script>

<style scoped lang="scss">
.settings-page {
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
  gap: 16px;
  padding: 14px 28px;
  border-bottom: 1px solid var(--coffee-border);
  background: var(--coffee-bg-card);
  flex-shrink: 0;
}

.title-block {
  flex: 1;
  min-width: 0;
}

.page-title {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  color: var(--coffee-text);
  line-height: 1.35;
}

.sub {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--coffee-text-muted);
  line-height: 1.4;
}

.header-actions {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 20px 28px 28px;
  box-sizing: border-box;

  &.flush {
    padding: 0;
    overflow: hidden;
  }

  &.layout-narrow {
    display: flex;
    justify-content: flex-start;

    > :deep(*) {
      width: 100%;
      max-width: 720px;
    }
  }

  &.layout-fluid > :deep(*) {
    width: 100%;
    max-width: 1120px;
  }

  &.layout-wide {
    padding: 0;
  }
}
</style>
