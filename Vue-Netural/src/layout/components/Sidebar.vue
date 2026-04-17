<!-- src/layout/components/Sidebar.vue -->
<template>
  <div class="sidebar-container" :class="{ collapsed: isCollapse }">
    <div class="sidebar-logo">
      <div class="logo-icon">
        <svg viewBox="0 0 32 32" fill="none">
          <circle cx="16" cy="16" r="14" stroke="currentColor" stroke-width="1.5"/>
          <circle cx="16" cy="16" r="4" fill="currentColor"/>
          <circle cx="10" cy="12" r="2" fill="currentColor" opacity="0.5"/>
          <circle cx="22" cy="12" r="2" fill="currentColor" opacity="0.5"/>
          <circle cx="10" cy="20" r="2" fill="currentColor" opacity="0.5"/>
          <circle cx="22" cy="20" r="2" fill="currentColor" opacity="0.5"/>
        </svg>
      </div>
      <span v-if="!isCollapse" class="logo-text">Neural Predict</span>
    </div>

    <el-scrollbar class="sidebar-menu-wrap">
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        :collapse-transition="false"
        background-color="transparent"
        text-color="#8a8a9a"
        active-text-color="#4a9eff"
        :unique-opened="true"
        router
      >
        <!-- 首页（固定） -->
        <el-menu-item index="/index">
          <el-icon><HomeFilled /></el-icon>
          <template #title>首页</template>
        </el-menu-item>

        <!-- 遍历菜单，兼容两种格式 -->
        <template v-for="menu in normalizedMenus" :key="menu.path">
          <!-- 有子菜单 -->
          <el-sub-menu v-if="menu.children && menu.children.length" :index="menu.path">
            <template #title>
              <el-icon><component :is="getIcon(menu.icon)" /></el-icon>
              <span>{{ menu.title }}</span>
            </template>
            <el-menu-item
              v-for="child in menu.children"
              :key="child.fullPath"
              :index="child.fullPath"
            >
              <el-icon><component :is="getIcon(child.icon)" /></el-icon>
              <template #title>{{ child.title }}</template>
            </el-menu-item>
          </el-sub-menu>

          <!-- 无子菜单 -->
          <el-menu-item v-else :index="menu.path">
            <el-icon><component :is="getIcon(menu.icon)" /></el-icon>
            <template #title>{{ menu.title }}</template>
          </el-menu-item>
        </template>
      </el-menu>
    </el-scrollbar>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  Monitor, Setting, User, List, Document,
  TrendCharts, Menu as IconMenu, HomeFilled,
  Folder, Connection
} from '@element-plus/icons-vue'

const props = defineProps({
  isCollapse: Boolean,
  menus: { type: Array, default: () => [] }
})

const route = useRoute()
const activeMenu = computed(() => route.path)

const iconMap = {
  home: HomeFilled,
  chart: TrendCharts,
  monitor: Monitor,
  user: User,
  system: Setting,
  'tree-table': List,
  peoples: User,
  date: Document,
  code: Document,
  list: List,
  menu: IconMenu,
  folder: Folder,
  international: Connection,
  设备: Setting,
  操作日志: Document,
}

function getIcon(name) {
  return iconMap[name] || Document
}

const normalizedMenus = computed(() => {
  return props.menus
    .filter(m => !m.hidden)
    .map(menu => {
      const meta = menu.meta || {}
      const result = {
        path: menu.path,
        title: meta.title || menu.menu_name || menu.name || '',
        icon: meta.icon || menu.icon || '',
        children: []
      }

      if (menu.children && menu.children.length) {
        result.children = menu.children
          .filter(c => !c.hidden)
          .map(child => {
            const childMeta = child.meta || {}
            let fullPath = child.path
            if (menu.path && !child.path.startsWith('/')) {
              const parent = menu.path.replace(/\/$/, '').replace(/^\//, '')
              fullPath = '/' + parent + '/' + child.path
            }
            return {
              path: child.path,
              fullPath: fullPath,
              title: childMeta.title || child.menu_name || child.name || '',
              icon: childMeta.icon || child.icon || ''
            }
          })
      }

      return result
    })
})
</script>

<style scoped>
.sidebar-container {
  width: 220px;
  height: 100vh;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-primary);
  display: flex;
  flex-direction: column;
  transition: width 0.25s ease, background 0.4s ease, border-color 0.4s ease;
  flex-shrink: 0;
}

.sidebar-container.collapsed {
  width: 64px;
}

.sidebar-logo {
  height: 56px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 10px;
  border-bottom: 1px solid var(--border-primary);
  flex-shrink: 0;
  transition: border-color 0.4s ease;
}

.logo-icon {
  width: 28px;
  height: 28px;
  color: var(--accent);
  flex-shrink: 0;
  transition: color 0.4s ease;
}

.logo-icon svg {
  width: 100%;
  height: 100%;
}

.logo-text {
  font-size: 15px;
  font-weight: 700;
  color: var(--accent);
  white-space: nowrap;
  transition: color 0.4s ease;
}

.sidebar-menu-wrap {
  flex: 1;
  padding-top: 8px;
}

.sidebar-menu-wrap :deep(.el-menu) {
  border-right: none;
}

.sidebar-menu-wrap :deep(.el-menu-item),
.sidebar-menu-wrap :deep(.el-sub-menu__title) {
  height: 46px;
  line-height: 46px;
  margin: 2px 8px;
  border-radius: 8px;
  color: var(--text-muted) !important;
  transition: all 0.3s ease !important;
}

.sidebar-menu-wrap :deep(.el-menu-item:hover),
.sidebar-menu-wrap :deep(.el-sub-menu__title:hover) {
  background: var(--accent-bg-light) !important;
  color: var(--text-primary) !important;
}

.sidebar-menu-wrap :deep(.el-menu-item.is-active) {
  background: var(--accent-bg) !important;
  color: var(--accent) !important;
}

.sidebar-menu-wrap :deep(.el-menu--popup) {
  background: var(--bg-card) !important;
  border: 1px solid var(--border-secondary) !important;
  border-radius: 10px !important;
  box-shadow: var(--shadow-dropdown) !important;
}

.sidebar-menu-wrap :deep(.el-menu--popup .el-menu-item) {
  color: var(--text-muted) !important;
}

.sidebar-menu-wrap :deep(.el-menu--popup .el-menu-item:hover) {
  background: var(--accent-bg-light) !important;
  color: var(--text-primary) !important;
}

.sidebar-menu-wrap :deep(.el-menu--popup .el-menu-item.is-active) {
  background: var(--accent-bg) !important;
  color: var(--accent) !important;
}
</style>
