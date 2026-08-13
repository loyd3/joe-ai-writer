import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { authApi } from '@/api'

let saveToServerTimer: ReturnType<typeof setTimeout> | null = null
function debouncedSaveToServer(fn: () => void, ms: number) {
  if (saveToServerTimer) clearTimeout(saveToServerTimer)
  saveToServerTimer = setTimeout(fn, ms)
}

const STORAGE_KEY = 'joe-writer-theme'

export type ThemePresetId = 'ink' | 'coffee' | 'rose' | 'mint' | 'lavender' | 'sky' | 'custom'
export type ThemeMode = 'light' | 'dark' | 'system'

export interface ThemePreset {
  id: ThemePresetId
  name: string
  primary: string
  primaryLight: string
  primaryDark: string
}

export const THEME_PRESETS: ThemePreset[] = [
  { id: 'ink', name: '墨蓝', primary: '#4F5CD5', primaryLight: '#7680DE', primaryDark: '#3F4AAA' },
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

function mixHex(c1: [number, number, number], c2: [number, number, number], amount: number): string {
  return rgbToHex(...(mixRgb(c1, c2, amount).map((x) => Math.round(x)) as [number, number, number]))
}

const WHITE: [number, number, number] = [255, 255, 255]
const BLACK: [number, number, number] = [0, 0, 0]

/** 根据主色生成完整浅色配色（支持 #rrggbb 或 #rrggbbaa） */
function deriveFullPalette(hex: string) {
  const hex6 = hex.length === 9 ? hex.slice(0, 7) : hex
  const primary = hexToRgb(hex6)
  return {
    primary: hex6,
    primaryLight: mixHex(primary, WHITE, 0.22),
    primaryDark: mixHex(primary, BLACK, 0.2),
    bg: mixHex(primary, [250, 250, 251], 0.97),
    bgWarm: mixHex(primary, [243, 243, 245], 0.93),
    bgCard: '#ffffff',
    text: mixHex(primary, [31, 35, 41], 0.9),
    textSecondary: mixHex(primary, [78, 82, 89], 0.88),
    textMuted: mixHex(primary, [139, 144, 150], 0.8),
    textLight: mixHex(primary, [180, 184, 190], 0.75),
    border: mixHex(primary, [227, 228, 232], 0.88),
    borderLight: mixHex(primary, [236, 236, 239], 0.9),
    divider: mixHex(primary, [241, 241, 243], 0.92),
  }
}

/** 根据主色生成暗色配色：中性暗底 + 主色提亮保证对比度 */
function deriveDarkPalette(hex: string) {
  const hex6 = hex.length === 9 ? hex.slice(0, 7) : hex
  const base = hexToRgb(hex6)
  const primary = hexToRgb(mixHex(base, WHITE, 0.12))
  const tint = (neutral: [number, number, number], amount: number) => mixHex(base, neutral, amount)
  return {
    primary: rgbToHex(...primary),
    primaryLight: mixHex(primary, WHITE, 0.22),
    primaryDark: mixHex(primary, BLACK, 0.2),
    bg: tint([19, 19, 23], 0.94),
    bgWarm: tint([26, 26, 31], 0.93),
    bgCard: tint([32, 32, 38], 0.92),
    text: '#e8e6ea',
    textSecondary: '#b3b0b8',
    textMuted: '#8a8791',
    textLight: '#6b6873',
    border: tint([48, 48, 55], 0.9),
    borderLight: tint([40, 40, 46], 0.9),
    divider: tint([35, 35, 40], 0.9),
  }
}

function getPresetPalette(preset: ThemePreset): Record<string, string> {
  if (preset.id === 'ink') {
    return {
      primary: preset.primary,
      primaryLight: preset.primaryLight,
      primaryDark: preset.primaryDark,
      bg: '#f7f7f8',
      bgWarm: '#f0f0f3',
      bgCard: '#ffffff',
      text: '#1f2329',
      textSecondary: '#4e5259',
      textMuted: '#8b9096',
      textLight: '#b4b8be',
      border: '#e3e4e8',
      borderLight: '#ececef',
      divider: '#f1f1f3',
    }
  }
  if (preset.id === 'coffee') {
    return {
      primary: preset.primary,
      primaryLight: preset.primaryLight,
      primaryDark: preset.primaryDark,
      bg: '#fbf9f6',
      bgWarm: '#f5f0e9',
      bgCard: '#ffffff',
      text: '#38281a',
      textSecondary: '#5d4a36',
      textMuted: '#9b8266',
      textLight: '#c0a987',
      border: '#e6dcd0',
      borderLight: '#efe8de',
      divider: '#f3ede4',
    }
  }
  if (preset.id === 'rose') {
    return {
      primary: preset.primary,
      primaryLight: preset.primaryLight,
      primaryDark: preset.primaryDark,
      bg: '#fbf6f7',
      bgWarm: '#f5eaed',
      bgCard: '#ffffff',
      text: '#3d2029',
      textSecondary: '#5d3a47',
      textMuted: '#9a7481',
      textLight: '#bfa3ac',
      border: '#e5d4d9',
      borderLight: '#efe3e7',
      divider: '#f4ecee',
    }
  }
  if (preset.id === 'mint') {
    return {
      primary: preset.primary,
      primaryLight: preset.primaryLight,
      primaryDark: preset.primaryDark,
      bg: '#f6f9f8',
      bgWarm: '#eaf2ef',
      bgCard: '#ffffff',
      text: '#1c3329',
      textSecondary: '#365545',
      textMuted: '#719684',
      textLight: '#a3bfb2',
      border: '#cfe0d8',
      borderLight: '#dfeae5',
      divider: '#ebf2ef',
    }
  }
  if (preset.id === 'lavender') {
    return {
      primary: preset.primary,
      primaryLight: preset.primaryLight,
      primaryDark: preset.primaryDark,
      bg: '#f8f7fa',
      bgWarm: '#efecf4',
      bgCard: '#ffffff',
      text: '#282138',
      textSecondary: '#4a4160',
      textMuted: '#8b81a3',
      textLight: '#b3abc3',
      border: '#ddd7e5',
      borderLight: '#e7e3ee',
      divider: '#efeCF3',
    }
  }
  if (preset.id === 'sky') {
    return {
      primary: preset.primary,
      primaryLight: preset.primaryLight,
      primaryDark: preset.primaryDark,
      bg: '#f5f8fa',
      bgWarm: '#e9f0f4',
      bgCard: '#ffffff',
      text: '#1d303d',
      textSecondary: '#3c5464',
      textMuted: '#7695a6',
      textLight: '#a5bfcc',
      border: '#d0dde4',
      borderLight: '#dfe8ee',
      divider: '#eaf0f4',
    }
  }
  return deriveFullPalette(preset.primary) as unknown as Record<string, string>
}

function getPrimaryOfCurrent(presetId: ThemePresetId, customColor: string): string {
  if (presetId === 'custom') return customColor
  return THEME_PRESETS.find((p) => p.id === presetId)?.primary ?? '#4F5CD5'
}

function setCssVars(palette: Record<string, string>, mode: 'light' | 'dark') {
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

  // 阴影 / 交互态：浅色用主色低透明，深色用黑色系并提高 alpha
  const dark = mode === 'dark'
  root.style.setProperty('--coffee-shadow', dark ? 'rgba(0, 0, 0, 0.32)' : `rgba(${r}, ${g}, ${b}, 0.08)`)
  root.style.setProperty('--coffee-shadow-hover', dark ? 'rgba(0, 0, 0, 0.45)' : `rgba(${r}, ${g}, ${b}, 0.15)`)
  root.style.setProperty('--coffee-selection', `rgba(${r}, ${g}, ${b}, ${dark ? 0.38 : 0.25})`)
  root.style.setProperty('--coffee-bg-hover', `rgba(${r}, ${g}, ${b}, ${dark ? 0.16 : 0.06})`)
  root.style.setProperty('--coffee-sidebar-shadow', dark ? 'rgba(0, 0, 0, 0.2)' : `rgba(${r}, ${g}, ${b}, 0.04)`)
  root.style.setProperty('--coffee-gradient-primary', `linear-gradient(135deg, ${primary} 0%, ${primaryLight} 100%)`)
  root.style.setProperty('--coffee-gradient-light', `linear-gradient(135deg, ${palette.bgWarm} 0%, ${palette.divider} 100%)`)

  // 中性多层阴影 token（弹层/卡片/对话框）
  root.style.setProperty('--app-shadow-sm', dark
    ? '0 1px 2px rgba(0, 0, 0, 0.4)'
    : '0 1px 2px rgba(16, 18, 24, 0.05)')
  root.style.setProperty('--app-shadow-md', dark
    ? '0 4px 16px rgba(0, 0, 0, 0.45)'
    : '0 2px 6px rgba(16, 18, 24, 0.04), 0 8px 24px rgba(16, 18, 24, 0.06)')
  root.style.setProperty('--app-shadow-lg', dark
    ? '0 8px 28px rgba(0, 0, 0, 0.55), 0 0 0 1px rgba(255, 255, 255, 0.05)'
    : '0 4px 12px rgba(16, 18, 24, 0.06), 0 16px 40px rgba(16, 18, 24, 0.1)')

  root.style.setProperty('--el-menu-hover-bg-color', `rgba(${r}, ${g}, ${b}, ${dark ? 0.16 : 0.08})`)
  root.style.setProperty('--el-dropdown-menuItem-hover-fill', `rgba(${r}, ${g}, ${b}, ${dark ? 0.16 : 0.08})`)

  // Element Plus 主色派生：浅色向白混合，深色向卡片底混合，
  // 使 link/text/plain 按钮及引用 --el-color-primary* 的样式跟随主题
  const p = hexToRgb(primary)
  const mixTarget = dark ? hexToRgb(palette.bgCard) : WHITE
  const light = (n: number) => mixHex(p, mixTarget, n / 10)
  root.style.setProperty('--el-color-primary', primary)
  root.style.setProperty('--el-color-primary-rgb', `${r}, ${g}, ${b}`)
  root.style.setProperty('--el-color-primary-light-3', light(3))
  root.style.setProperty('--el-color-primary-light-5', light(5))
  root.style.setProperty('--el-color-primary-light-7', light(7))
  root.style.setProperty('--el-color-primary-light-8', light(8))
  root.style.setProperty('--el-color-primary-light-9', light(9))
  root.style.setProperty('--el-color-primary-dark-2', mixHex(p, BLACK, 0.2))
}

const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

export const useThemeStore = defineStore('theme', () => {
  const presetId = ref<ThemePresetId>('ink')
  const customColor = ref('#4F5CD5')
  const mode = ref<ThemeMode>('system')
  /** 系统当前是否为暗色（mode 为 system 时生效） */
  const systemDark = ref(mediaQuery.matches)

  function resolvedMode(): 'light' | 'dark' {
    if (mode.value === 'system') return systemDark.value ? 'dark' : 'light'
    return mode.value
  }

  function loadSaved() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) return
      const data = JSON.parse(raw) as { presetId?: ThemePresetId; customColor?: string; mode?: ThemeMode }
      if (data.presetId) presetId.value = data.presetId
      if (data.customColor) customColor.value = data.customColor
      if (data.mode === 'light' || data.mode === 'dark' || data.mode === 'system') mode.value = data.mode
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

  /** 保存主题到服务器（外观模式仅存本地，不上服务器） */
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
    const m = resolvedMode()
    const base = getPrimaryOfCurrent(presetId.value, customColor.value)
    let palette: Record<string, string>
    if (m === 'dark') {
      palette = deriveDarkPalette(base)
    } else if (presetId.value === 'custom') {
      palette = deriveFullPalette(customColor.value) as unknown as Record<string, string>
    } else {
      const preset = THEME_PRESETS.find((p) => p.id === presetId.value)
      palette = preset ? getPresetPalette(preset) : (deriveFullPalette(base) as unknown as Record<string, string>)
    }
    setCssVars(palette, m)
    document.documentElement.classList.toggle('dark', m === 'dark')
    document.documentElement.style.colorScheme = m
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

  function setMode(m: ThemeMode) {
    mode.value = m
  }

  /** 侧边栏快捷切换：在浅色/深色间切换（脱离跟随系统） */
  function toggleMode() {
    mode.value = resolvedMode() === 'dark' ? 'light' : 'dark'
  }

  function isDark(): boolean {
    return resolvedMode() === 'dark'
  }

  function save() {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ presetId: presetId.value, customColor: customColor.value, mode: mode.value })
    )
  }

  loadSaved()
  applyTheme()

  // 跟随系统：监听系统外观变化
  mediaQuery.addEventListener('change', (e) => {
    systemDark.value = e.matches
  })
  watch(systemDark, () => {
    if (mode.value === 'system') applyTheme()
  })

  watch([presetId, customColor, mode], () => {
    applyTheme()
    save()
    debouncedSaveToServer(saveToServer, 600)
  })

  return {
    presetId,
    customColor,
    mode,
    systemDark,
    setPreset,
    setCustomColor,
    setMode,
    toggleMode,
    isDark,
    applyTheme,
    loadSaved,
    loadFromServer,
    saveToServer,
  }
})
