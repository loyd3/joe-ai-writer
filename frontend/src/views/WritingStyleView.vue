<template>
  <SettingsPageShell
    title="文风库"
    subtitle="系统级文风：预设、手建，或从范文提炼后在写作中选用"
    layout="wide"
    flush
  >
    <StyleAgentsPanel compact />
  </SettingsPageShell>
</template>

<script setup lang="ts">
import SettingsPageShell from '@/components/SettingsPageShell.vue'
import StyleAgentsPanel from '@/components/StyleAgentsPanel.vue'
</script>
