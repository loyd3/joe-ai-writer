<template>
  <SettingsPageShell title="主题设置" subtitle="外观模式、预设主题与自定义主题色" layout="fluid">
    <ThemeSettingsPanel />
  </SettingsPageShell>
</template>

<script setup lang="ts">
import SettingsPageShell from '@/components/SettingsPageShell.vue'
import ThemeSettingsPanel from '@/components/ThemeSettingsPanel.vue'
</script>
