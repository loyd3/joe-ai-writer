<template>
  <SettingsPageShell
    title="大模型设置"
    subtitle="本地与线上分栏配置 · 顶部可切换当前通道"
    layout="fluid"
  >
    <AIConfigPanel />
  </SettingsPageShell>
</template>

<script setup lang="ts">
import SettingsPageShell from '@/components/SettingsPageShell.vue'
import AIConfigPanel from '@/components/AIConfigPanel.vue'
</script>
