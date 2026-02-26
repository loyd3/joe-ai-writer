import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { authApi } from '@/api'

let saveToServerTimer: ReturnType<typeof setTimeout> | null = null
function debouncedSaveToServer(fn: () => void, ms: number) {
  if (saveToServerTimer) clearTimeout(saveToServerTimer)
  saveToServerTimer = setTimeout(fn, ms)
}

const STORAGE_KEY = 'joe-writer-theme'

export type ThemePresetId = 'coffee' | 'rose' | 'mint' | 'lavender' | 'sky' | 'custom'

export interface ThemePreset {
  id: ThemePresetId
  name: string
  primary: string
  primaryLight: string
  primaryDark: string
}

export const THEME_PRESETS: ThemePreset[] = [
  { id: 'coffee', name: '咖啡棕', primary: '#a65e2e', primaryLight: '#c97f4a', primaryDark: '#7a4318' },
  { id: 'rose', name: '樱花粉', primary: '#C46B83', primaryLight: '#D4889D', primaryDark: '#A8526B' },
  { id: 'mint', name: '薄荷绿', primary: '#5AAF8F', primaryLight: '#78C4A6', primaryDark: '#3E9475' },
  { id: 'lavender', name: '香芋紫', primary: '#8574B2', primaryLight: '#A090C8', primaryDark: '#6A5A96' },
  { id: 'sky', name: '天空蓝', primary: '#5E9AB8', primaryLight: '#7DB2CC', primaryDark: '#4680A0' },
]

function hexToRgb(hex: string): [number, number, number] {
  const m = hex.replace(/^#/, '').match(/.{2}/g)
  if (!m) return [0, 0, 0]
  return m.map((x) => parseInt(x, 16)) as [number, number, number]
}

function rgbToHex(r: number, g: number, b: number): string {
  return '#' + [r, g, b].map((x) => Math.round(Math.max(0, Math.min(255, x))).toString(16).padStart(2, '0')).join('')
}

/** RGB 混合：amount 为 0 返回 color1，为 1 返回 color2 */
function mixRgb(c1: [number, number, number], c2: [number, number, number], amount: number): [number, number, number] {
  return [
    c1[0] * (1 - amount) + c2[0] * amount,
    c1[1] * (1 - amount) + c2[1] * amount,
    c1[2] * (1 - amount) + c2[2] * amount,
  ]
}

const WHITE: [number, number, number] = [255, 255, 255]
const BLACK: [number, number, number] = [0, 0, 0]

/** 根据主色生成完整配色（支持 #rrggbb 或 #rrggbbaa） */
function deriveFullPalette(hex: string) {
  const hex6 = hex.length === 9 ? hex.slice(0, 7) : hex
  const primary = hexToRgb(hex6)
  const primaryLight = mixRgb(primary, WHITE, 0.22).map((x) => Math.round(x)) as [number, number, number]
  const primaryDark = mixRgb(primary, BLACK, 0.2).map((x) => Math.round(x)) as [number, number, number]
  return {
    primary: hex6,
    primaryLight: rgbToHex(...primaryLight),
    primaryDark: rgbToHex(...primaryDark),
    bg: rgbToHex(...mixRgb(primary, [253, 251, 247], 0.97).map((x) => Math.round(x)) as [number, number, number]),
    bgWarm: rgbToHex(...mixRgb(primary, [248, 243, 236], 0.93).map((x) => Math.round(x)) as [number, number, number]),
    bgCard: '#ffffff',
    text: rgbToHex(...mixRgb(primary, BLACK, 0.72).map((x) => Math.round(x)) as [number, number, number]),
    textSecondary: rgbToHex(...mixRgb(primary, BLACK, 0.58).map((x) => Math.round(x)) as [number, number, number]),
    textMuted: rgbToHex(...mixRgb(primary, WHITE, 0.35).map((x) => Math.round(x)) as [number, number, number]),
    textLight: rgbToHex(...mixRgb(primary, WHITE, 0.21).map((x) => Math.round(x)) as [number, number, number]),
    border: rgbToHex(...mixRgb(primary, [232, 220, 208], 0.85).map((x) => Math.round(x)) as [number, number, number]),
    borderLight: rgbToHex(...mixRgb(primary, [242, 233, 224], 0.9).map((x) => Math.round(x)) as [number, number, number]),
    divider: rgbToHex(...mixRgb(primary, [245, 235, 224], 0.92).map((x) => Math.round(x)) as [number, number, number]),
  }
}

function getPresetPalette(preset: ThemePreset): Record<string, string> {
  if (preset.id === 'coffee') {
    return {
      primary: preset.primary,
      primaryLight: preset.primaryLight,
      primaryDark: preset.primaryDark,
      bg: '#fdfbf7',
      bgWarm: '#f8f3ec',
      bgCard: '#ffffff',
      text: '#4a2c17',
      textSecondary: '#6b4423',
      textMuted: '#a67c52',
      textLight: '#c9a86c',
      border: '#e8dcd0',
      borderLight: '#f2e9e0',
      divider: '#f5ebe0',
    }
  }
  if (preset.id === 'rose') {
    return {
      primary: preset.primary,
      primaryLight: preset.primaryLight,
      primaryDark: preset.primaryDark,
      bg: '#fdf5f7',
      bgWarm: '#f9e8ed',
      bgCard: '#ffffff',
      text: '#4a1e2e',
      textSecondary: '#6e3348',
      textMuted: '#9e6e80',
      textLight: '#c49dab',
      border: '#e8ced6',
      borderLight: '#f2e0e6',
      divider: '#f8eff2',
    }
  }
  if (preset.id === 'mint') {
    return {
      primary: preset.primary,
      primaryLight: preset.primaryLight,
      primaryDark: preset.primaryDark,
      bg: '#f5faf8',
      bgWarm: '#e5f2ec',
      bgCard: '#ffffff',
      text: '#143d2d',
      textSecondary: '#2d5e4a',
      textMuted: '#6a9e8a',
      textLight: '#9dc5b5',
      border: '#bcdccc',
      borderLight: '#d8ece2',
      divider: '#edf6f2',
    }
  }
  if (preset.id === 'lavender') {
    return {
      primary: preset.primary,
      primaryLight: preset.primaryLight,
      primaryDark: preset.primaryDark,
      bg: '#f7f5fb',
      bgWarm: '#ece8f4',
      bgCard: '#ffffff',
      text: '#2a2045',
      textSecondary: '#46386a',
      textMuted: '#8878a5',
      textLight: '#b5a8c8',
      border: '#d2c8e2',
      borderLight: '#e5dfee',
      divider: '#f0edf5',
    }
  }
  if (preset.id === 'sky') {
    return {
      primary: preset.primary,
      primaryLight: preset.primaryLight,
      primaryDark: preset.primaryDark,
      bg: '#f4f8fb',
      bgWarm: '#e3eef5',
      bgCard: '#ffffff',
      text: '#152f40',
      textSecondary: '#2e536e',
      textMuted: '#6e98b0',
      textLight: '#9ec0d2',
      border: '#b8d0de',
      borderLight: '#d6e4ed',
      divider: '#ecf2f6',
    }
  }
  return deriveFullPalette(preset.primary) as unknown as Record<string, string>
}

function setCssVars(palette: Record<string, string>) {
  const { primary, primaryLight, primaryDark } = palette
  const [r, g, b] = hexToRgb(primary)
  const root = document.documentElement
  root.style.setProperty('--coffee-primary-rgb', `${r}, ${g}, ${b}`)
  root.style.setProperty('--coffee-primary', primary)
  root.style.setProperty('--coffee-primary-light', primaryLight)
  root.style.setProperty('--coffee-primary-dark', primaryDark)
  root.style.setProperty('--coffee-bg', palette.bg)
  root.style.setProperty('--coffee-bg-warm', palette.bgWarm)
  root.style.setProperty('--coffee-bg-card', palette.bgCard)
  root.style.setProperty('--coffee-text', palette.text)
  root.style.setProperty('--coffee-text-secondary', palette.textSecondary)
  root.style.setProperty('--coffee-text-muted', palette.textMuted)
  root.style.setProperty('--coffee-text-light', palette.textLight)
  root.style.setProperty('--coffee-border', palette.border)
  root.style.setProperty('--coffee-border-light', palette.borderLight)
  root.style.setProperty('--coffee-divider', palette.divider)
  root.style.setProperty('--coffee-shadow', `rgba(${r}, ${g}, ${b}, 0.08)`)
  root.style.setProperty('--coffee-shadow-hover', `rgba(${r}, ${g}, ${b}, 0.15)`)
  root.style.setProperty('--coffee-selection', `rgba(${r}, ${g}, ${b}, 0.25)`)
  root.style.setProperty('--coffee-gradient-primary', `linear-gradient(135deg, ${primary} 0%, ${primaryLight} 100%)`)
  root.style.setProperty('--coffee-gradient-light', `linear-gradient(135deg, ${palette.bgWarm} 0%, ${palette.divider} 100%)`)
  root.style.setProperty('--coffee-bg-hover', `rgba(${r}, ${g}, ${b}, 0.06)`)
  root.style.setProperty('--coffee-sidebar-shadow', `rgba(${r}, ${g}, ${b}, 0.04)`)
  root.style.setProperty('--el-menu-hover-bg-color', `rgba(${r}, ${g}, ${b}, 0.08)`)
  root.style.setProperty('--el-dropdown-menuItem-hover-fill', `rgba(${r}, ${g}, ${b}, 0.08)`)
}

export const useThemeStore = defineStore('theme', () => {
  const presetId = ref<ThemePresetId>('coffee')
  const customColor = ref('#a65e2e')

  function loadSaved() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) return
      const data = JSON.parse(raw) as { presetId?: ThemePresetId; customColor?: string }
      if (data.presetId) presetId.value = data.presetId
      if (data.customColor) customColor.value = data.customColor
    } catch {
      // ignore
    }
  }

  /** 从服务器加载主题（登录后调用） */
  async function loadFromServer() {
    try {
      const res = await authApi.getTheme()
      const data = res.data as { preset_id?: string; custom_color?: string }
      if (data.preset_id) presetId.value = data.preset_id as ThemePresetId
      if (data.custom_color) customColor.value = data.custom_color
      applyTheme()
      save()
    } catch {
      // 未登录或接口失败，保留本地主题
    }
  }

  /** 保存主题到服务器 */
  async function saveToServer() {
    try {
      await authApi.updateTheme({
        preset_id: presetId.value,
        custom_color: customColor.value
      })
    } catch {
      // 未登录或网络错误，仅保留在本地
    }
  }

  function applyTheme() {
    if (presetId.value === 'custom') {
      const palette = deriveFullPalette(customColor.value)
      setCssVars(palette as unknown as Record<string, string>)
    } else {
      const preset = THEME_PRESETS.find((p) => p.id === presetId.value)
      if (preset) setCssVars(getPresetPalette(preset))
    }
  }

  function setPreset(id: ThemePresetId) {
    presetId.value = id
    if (id !== 'custom') applyTheme()
  }

  function setCustomColor(hex: string) {
    customColor.value = hex
    presetId.value = 'custom'
    applyTheme()
  }

  function save() {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ presetId: presetId.value, customColor: customColor.value })
    )
  }

  loadSaved()
  applyTheme()

  watch([presetId, customColor], () => {
    applyTheme()
    save()
    debouncedSaveToServer(saveToServer, 600)
  })

  return {
    presetId,
    customColor,
    setPreset,
    setCustomColor,
    applyTheme,
    loadSaved,
    loadFromServer,
    saveToServer,
  }
})
