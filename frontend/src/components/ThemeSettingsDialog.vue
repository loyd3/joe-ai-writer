<template>
  <el-dialog
    v-model="visible"
    title="主题设置"
    width="440px"
    class="theme-dialog"
    :close-on-click-modal="true"
    @closed="onClosed"
  >
    <ThemeSettingsPanel />
    <template #footer>
      <el-button type="primary" @click="visible = false">完成</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import ThemeSettingsPanel from '@/components/ThemeSettingsPanel.vue'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const visible = ref(props.modelValue)

watch(
  () => props.modelValue,
  (v) => {
    visible.value = v
  },
)
watch(visible, (v) => emit('update:modelValue', v))

function onClosed() {
  emit('update:modelValue', false)
}
</script>
