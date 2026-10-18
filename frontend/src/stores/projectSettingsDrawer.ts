import { defineStore } from 'pinia'
import { ref } from 'vue'

type PrepareFn = () => Promise<boolean>
type ChangedFn = () => Promise<void>

export const useProjectSettingsDrawerStore = defineStore('projectSettingsDrawer', () => {
  const open = ref(false)
  const projectId = ref<number | null>(null)

  let prepareFn: PrepareFn | null = null
  let changedFn: ChangedFn | null = null

  function show(id: number) {
    if (!id || Number.isNaN(id)) return
    projectId.value = id
    open.value = true
  }

  function close() {
    open.value = false
  }

  function registerHandlers(prepare: PrepareFn | null, changed: ChangedFn | null) {
    prepareFn = prepare
    changedFn = changed
  }

  async function prepareProjectAgent() {
    if (!open.value || !prepareFn) return true
    return prepareFn()
  }

  async function onAgentProjectChanged() {
    if (!open.value || !changedFn) return
    await changedFn()
  }

  return {
    open,
    projectId,
    show,
    close,
    registerHandlers,
    prepareProjectAgent,
    onAgentProjectChanged,
  }
})
