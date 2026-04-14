<!-- src/layout/components/SidebarItem.vue -->
<template>
  <el-sub-menu
    v-if="item.children && item.children.length"
    :index="resolvePath('')"
  >
    <template #title>
      <el-icon v-if="item.meta && item.meta.icon"><component :is="getIcon(item.meta.icon)" /></el-icon>
      <span>{{ item.meta && item.meta.title }}</span>
    </template>
    <SidebarItem
      v-for="child in item.children"
      :key="child.path"
      :item="child"
      :base-path="resolvePath(child.path)"
    />
  </el-sub-menu>

  <el-menu-item v-else :index="resolvePath('')">
    <el-icon v-if="item.meta && item.meta.icon"><component :is="getIcon(item.meta.icon)" /></el-icon>
    <template #title>
      <span>{{ item.meta && item.meta.title }}</span>
    </template>
  </el-menu-item>
</template>

<script setup>
import {
  Monitor, Setting, User, List, Document,
  TrendCharts, Menu as IconMenu
} from '@element-plus/icons-vue'

const props = defineProps({
  item: { type: Object, required: true },
  basePath: { type: String, default: '' }
})

const iconMap = {
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
}

function getIcon(name) {
  return iconMap[name] || Document
}

function resolvePath(routePath) {
  if (!routePath) return props.basePath
  if (routePath.startsWith('/')) return routePath
  if (props.basePath === '/') return '/' + routePath
  return props.basePath + '/' + routePath
}
</script>
