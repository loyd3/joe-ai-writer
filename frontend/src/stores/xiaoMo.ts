import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Block } from '@/api/types'

export type XiaoMoAssistRequest = {
  nonce: number
  kind: 'action' | 'attach' | 'ask'
  action?: string
  text: string
  blockIndex?: number
  blockIndices?: number[]
  /** 块 ID，供智能体 focus.block_ids 使用 */
  blockIds?: string[]
  instruction?: string
}

type InsertPos = 'cursor' | 'end'

export type XiaoMoEditFocus = {
  text: string
  blockIndex?: number
  blockIndices?: number[]
  blockIds?: string[]
}

export type XiaoMoDocumentBridge = {
  insert: (text: string, position?: InsertPos) => void
  insertBlocks: (blocks: Block[], position?: InsertPos) => void
  replace: (
    oldText: string,
    newText: string,
    blockIndex?: number,
    blocks?: Block[],
    blockIndices?: number[],
  ) => void
  preview: (payload: {
    blockIndex?: number
    blockIndices?: number[]
    text: string
    blocks?: Block[]
  }) => void
  previewCancel: () => void
  /** 读取编辑器当前选区/多选块，供智能体 focus */
  getEditFocus?: () => XiaoMoEditFocus | null
}

/** 全局小墨：统一浮窗入口 + 文档桥接（润色/替换等） */
export const useXiaoMoStore = defineStore('xiaoMo', () => {
  const openNonce = ref(0)
  const pendingAssist = ref<XiaoMoAssistRequest | null>(null)
  const documentBridge = ref<XiaoMoDocumentBridge | null>(null)

  function openFloating() {
    openNonce.value += 1
  }

  function registerDocumentBridge(bridge: XiaoMoDocumentBridge | null) {
    documentBridge.value = bridge
  }

  function requestAssist(payload: Omit<XiaoMoAssistRequest, 'nonce'>) {
    pendingAssist.value = { ...payload, nonce: Date.now() }
    openFloating()
  }

  function consumeAssist(nonce: number) {
    if (pendingAssist.value?.nonce === nonce) pendingAssist.value = null
  }

  return {
    openNonce,
    pendingAssist,
    documentBridge,
    openFloating,
    registerDocumentBridge,
    requestAssist,
    consumeAssist,
  }
})
