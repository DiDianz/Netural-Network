<!-- src/layout/index.vue -->
<template>
  <div class="app-wrapper">
    <Sidebar :is-collapse="isCollapse" :menus="sidebarMenus" />
    <div class="main-container">
      <Navbar :is-collapse="isCollapse" @toggle-sidebar="isCollapse = !isCollapse" />
      <TagsView />
      <AppMain />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { usePermissionStore } from '../stores/permission'
import Sidebar from './components/Sidebar.vue'
import Navbar from './components/Navbar.vue'
import TagsView from './components/TagsView.vue'
import AppMain from './components/AppMain.vue'

const permissionStore = usePermissionStore()
const sidebarMenus = computed(() => permissionStore.sidebarMenus)
const isCollapse = ref(false)

onMounted(async () => {
  await permissionStore.generateRoutes()
})
</script>

<style scoped>
.app-wrapper {
  display: flex;
  width: 100%;
  height: 100%;
  background: var(--bg-primary);
  overflow: hidden;
}

.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
  height: 100%;
}
</style>
