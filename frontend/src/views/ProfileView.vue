<template>
  <SettingsPageShell title="个人中心" subtitle="头像、资料与密码" layout="fluid">
    <ProfileCenter hide-title />
  </SettingsPageShell>
</template>

<script setup lang="ts">
import SettingsPageShell from '@/components/SettingsPageShell.vue'
import ProfileCenter from '@/components/ProfileCenter.vue'
</script>
