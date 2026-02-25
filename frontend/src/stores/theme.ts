import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const STORAGE_KEY = 'joe-writer-theme'

export type ThemePresetId = 'coffee' | 'teal' | 'indigo' | 'custom'

export interface ThemePreset {
  id: ThemePresetId
  name: string
  primary: string
  primaryLight: string
  primaryDark: string
}

export const THEME_PRESETS: ThemePreset[] = [
  { id: 'coffee', name: '咖啡棕', primary: '#a65e2e', primaryLight: '#c97f4a', primaryDark: '#7a4318' },
  { id: 'teal', name: '青绿色', primary: '#0d9488', primaryLight: '#14b8a6', primaryDark: '#0f766e' },
  { id: 'indigo', name: '靛蓝色', primary: '#4f46e5', primaryLight: '#6366f1', primaryDark: '#4338ca' },
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
  if (preset.id === 'teal') {
    return {
      primary: preset.primary,
      primaryLight: preset.primaryLight,
      primaryDark: preset.primaryDark,
      bg: '#f0fdfa',
      bgWarm: '#ccfbf1',
      bgCard: '#ffffff',
      text: '#134e4a',
      textSecondary: '#0f766e',
      textMuted: '#5eead4',
      textLight: '#99f6e4',
      border: '#99f6e4',
      borderLight: '#ccfbf1',
      divider: '#f0fdfa',
    }
  }
  if (preset.id === 'indigo') {
    return {
      primary: preset.primary,
      primaryLight: preset.primaryLight,
      primaryDark: preset.primaryDark,
      bg: '#eef2ff',
      bgWarm: '#e0e7ff',
      bgCard: '#ffffff',
      text: '#312e81',
      textSecondary: '#3730a3',
      textMuted: '#818cf8',
      textLight: '#a5b4fc',
      border: '#c7d2fe',
      borderLight: '#e0e7ff',
      divider: '#eef2ff',
    }
  }
  return deriveFullPalette(preset.primary) as unknown as Record<string, string>
}

function setCssVars(palette: Record<string, string>) {
  const { primary, primaryLight, primaryDark } = palette
  const [r, g, b] = hexToRgb(primary)
  const root = document.documentElement
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
  })

  return {
    presetId,
    customColor,
    setPreset,
    setCustomColor,
    applyTheme,
    loadSaved,
  }
})
