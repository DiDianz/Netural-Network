// src/stores/theme.js
import { defineStore } from 'pinia'

// 主题配置
const themes = [
  {
    key: 'dark',
    name: '深邃暗夜',
    icon: '🌙',
    primary: '#4a9eff',
    bg: '#08080c'
  },
  {
    key: 'light',
    name: '明亮晨光',
    icon: '☀️',
    primary: '#3b82f6',
    bg: '#f0f2f5'
  },
  {
    key: 'ocean',
    name: '深海蓝调',
    icon: '🌊',
    primary: '#00b4ff',
    bg: '#0a1628'
  },
  {
    key: 'forest',
    name: '森林绿意',
    icon: '🌲',
    primary: '#34d399',
    bg: '#0a1210'
  },
  {
    key: 'galaxy',
    name: '星空紫夜',
    icon: '🌌',
    primary: '#a78bfa',
    bg: '#0d0a18'
  },
  {
    key: 'amber',
    name: '暖阳琥珀',
    icon: '🔥',
    primary: '#fb923c',
    bg: '#12100c'
  }
]

const THEME_KEY = 'neural_predict_theme'

export const useThemeStore = defineStore('theme', {
  state: () => ({
    currentTheme: localStorage.getItem(THEME_KEY) || 'dark',
    themes: themes
  }),

  getters: {
    currentThemeInfo: (state) => {
      return state.themes.find(t => t.key === state.currentTheme) || state.themes[0]
    },
    isLight: (state) => state.currentTheme === 'light'
  },

  actions: {
    setTheme(key) {
      this.currentTheme = key
      localStorage.setItem(THEME_KEY, key)
      applyTheme(key)
    },

    initTheme() {
      applyTheme(this.currentTheme)
    }
  }
})

// 应用主题到 body
function applyTheme(key) {
  // 移除所有 theme- 开头的 class
  var body = document.body
  var classes = body.className.split(' ').filter(function(c) {
    return c.indexOf('theme-') !== 0
  })
  classes.push('theme-' + key)
  body.className = classes.join(' ')

  // light 主题调整 html color-scheme
  if (key === 'light') {
    document.documentElement.style.colorScheme = 'light'
  } else {
    document.documentElement.style.colorScheme = 'dark'
  }
}
