<!-- src/components/ThemeSwitcher.vue -->
<template>
  <el-popover
    placement="bottom-end"
    :width="300"
    trigger="click"
    popper-class="theme-popover"
    :teleported="true"
  >
    <template #reference>
      <div class="theme-trigger">
        <span class="theme-icon">{{ currentThemeInfo.icon }}</span>
        <span class="theme-name">{{ currentThemeInfo.name }}</span>
      </div>
    </template>
    <div class="theme-panel">
      <div class="theme-panel-title">选择主题</div>
      <div class="theme-grid">
        <div
          v-for="theme in themes"
          :key="theme.key"
          class="theme-option"
          :class="{ active: currentTheme === theme.key }"
          @click="handleSwitch(theme.key)"
        >
          <div class="theme-preview" :style="{ background: theme.bg }">
            <div class="preview-bar" :style="{ background: theme.primary }"></div>
            <div class="preview-lines">
              <div class="preview-line" :style="{ background: theme.primary, opacity: 0.3 }"></div>
              <div class="preview-line short" :style="{ background: theme.primary, opacity: 0.15 }"></div>
            </div>
          </div>
          <div class="theme-info">
            <span class="theme-label-icon">{{ theme.icon }}</span>
            <span class="theme-label-name">{{ theme.name }}</span>
          </div>
          <div v-if="currentTheme === theme.key" class="check-mark">✓</div>
        </div>
      </div>
    </div>
  </el-popover>
</template>

<script setup>
import { computed } from 'vue'
import { useThemeStore } from '../stores/theme'

const themeStore = useThemeStore()

const themes = computed(() => themeStore.themes)
const currentTheme = computed(() => themeStore.currentTheme)
const currentThemeInfo = computed(() => themeStore.currentThemeInfo)

function handleSwitch(key) {
  themeStore.setTheme(key)
}
</script>

<style scoped>
.theme-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 10px;
  transition: all 0.2s;
  white-space: nowrap;
}

.theme-trigger:hover {
  background: var(--accent-bg-light);
}

.theme-icon {
  font-size: 16px;
  line-height: 1;
}

.theme-name {
  font-size: 13px;
  color: var(--text-muted);
  font-weight: 500;
}

.theme-trigger:hover .theme-name {
  color: var(--text-secondary);
}

/* ========== 面板 ========== */
.theme-panel {
  padding: 4px;
}

.theme-panel-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
  padding: 0 4px;
}

.theme-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
}

.theme-option {
  position: relative;
  border-radius: 10px;
  border: 2px solid var(--border-secondary);
  padding: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.theme-option:hover {
  border-color: var(--border-hover);
  transform: translateY(-1px);
}

.theme-option.active {
  border-color: var(--accent);
}

.theme-preview {
  height: 36px;
  border-radius: 6px;
  padding: 6px;
  margin-bottom: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow: hidden;
}

.preview-bar {
  width: 18px;
  height: 3px;
  border-radius: 2px;
}

.preview-lines {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.preview-line {
  height: 2px;
  border-radius: 1px;
  width: 100%;
}

.preview-line.short {
  width: 60%;
}

.theme-info {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 2px;
}

.theme-label-icon {
  font-size: 11px;
}

.theme-label-name {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
}

.check-mark {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
