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
  { id: 'ink', name: '墨蓝', primary: '#3E4BC4', primaryLight: '#5C68D4', primaryDark: '#323D8F' },
  { id: 'coffee', name: '咖啡棕', primary: '#8F4E22', primaryLight: '#A65E2E', primaryDark: '#633510' },
  { id: 'rose', name: '樱花粉', primary: '#B04F6A', primaryLight: '#C46B83', primaryDark: '#8A3A52' },
  { id: 'mint', name: '薄荷绿', primary: '#3F9575', primaryLight: '#5AAF8F', primaryDark: '#2D7560' },
  { id: 'lavender', name: '香芋紫', primary: '#6B5899', primaryLight: '#8574B2', primaryDark: '#524275' },
  { id: 'sky', name: '天空蓝', primary: '#457FA0', primaryLight: '#5E9AB8', primaryDark: '#336682' },
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
    primaryLight: mixHex(primary, WHITE, 0.18),
    primaryDark: mixHex(primary, BLACK, 0.22),
    bg: mixHex(primary, [248, 248, 249], 0.96),
    bgWarm: mixHex(primary, [240, 240, 242], 0.92),
    bgCard: '#ffffff',
    text: mixHex(primary, [18, 20, 24], 0.92),
    textSecondary: mixHex(primary, [52, 56, 62], 0.9),
    textMuted: mixHex(primary, [100, 105, 112], 0.84),
    textLight: mixHex(primary, [140, 145, 152], 0.78),
    border: mixHex(primary, [210, 212, 218], 0.86),
    borderLight: mixHex(primary, [226, 227, 232], 0.88),
    divider: mixHex(primary, [236, 236, 239], 0.9),
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
    text: '#f2f0f4',
    textSecondary: '#c9c6ce',
    textMuted: '#9f9ba5',
    textLight: '#7c7884',
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
      bg: '#f5f5f7',
      bgWarm: '#ececf1',
      bgCard: '#ffffff',
      text: '#15181d',
      textSecondary: '#3a3e45',
      textMuted: '#6b7078',
      textLight: '#8e939a',
      border: '#d5d6dc',
      borderLight: '#e3e4e8',
      divider: '#ececef',
    }
  }
  if (preset.id === 'coffee') {
    return {
      primary: preset.primary,
      primaryLight: preset.primaryLight,
      primaryDark: preset.primaryDark,
      bg: '#faf7f3',
      bgWarm: '#f2ebe2',
      bgCard: '#ffffff',
      text: '#2a1c12',
      textSecondary: '#4a3828',
      textMuted: '#7d664d',
      textLight: '#a58c6e',
      border: '#d9cbb8',
      borderLight: '#e8ddd0',
      divider: '#f0e8dd',
    }
  }
  if (preset.id === 'rose') {
    return {
      primary: preset.primary,
      primaryLight: preset.primaryLight,
      primaryDark: preset.primaryDark,
      bg: '#faf4f5',
      bgWarm: '#f2e4e8',
      bgCard: '#ffffff',
      text: '#2a141c',
      textSecondary: '#4a2c37',
      textMuted: '#7a5764',
      textLight: '#9a7d87',
      border: '#d9c4cb',
      borderLight: '#e8d6dc',
      divider: '#f0e6e9',
    }
  }
  if (preset.id === 'mint') {
    return {
      primary: preset.primary,
      primaryLight: preset.primaryLight,
      primaryDark: preset.primaryDark,
      bg: '#f3f7f5',
      bgWarm: '#e4efe9',
      bgCard: '#ffffff',
      text: '#14261e',
      textSecondary: '#2a4436',
      textMuted: '#5a7a6a',
      textLight: '#84a394',
      border: '#bdd4c8',
      borderLight: '#d2e2da',
      divider: '#e4efe9',
    }
  }
  if (preset.id === 'lavender') {
    return {
      primary: preset.primary,
      primaryLight: preset.primaryLight,
      primaryDark: preset.primaryDark,
      bg: '#f5f4f8',
      bgWarm: '#eae6f1',
      bgCard: '#ffffff',
      text: '#1c1728',
      textSecondary: '#3a334d',
      textMuted: '#6f6688',
      textLight: '#948cac',
      border: '#cdc5d9',
      borderLight: '#ddd7e5',
      divider: '#eae6f1',
    }
  }
  if (preset.id === 'sky') {
    return {
      primary: preset.primary,
      primaryLight: preset.primaryLight,
      primaryDark: preset.primaryDark,
      bg: '#f2f6f9',
      bgWarm: '#e3ecf2',
      bgCard: '#ffffff',
      text: '#142430',
      textSecondary: '#2e4452',
      textMuted: '#5c7a8c',
      textLight: '#849eb0',
      border: '#bcd0db',
      borderLight: '#d0dde4',
      divider: '#e3ecf2',
    }
  }
  return deriveFullPalette(preset.primary) as unknown as Record<string, string>
}

function getPrimaryOfCurrent(presetId: ThemePresetId, customColor: string): string {
  if (presetId === 'custom') return customColor
  return THEME_PRESETS.find((p) => p.id === presetId)?.primary ?? '#3E4BC4'
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
  const customColor = ref('#3E4BC4')
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
