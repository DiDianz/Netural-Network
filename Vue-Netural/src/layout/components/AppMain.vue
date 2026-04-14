<!-- src/layout/components/AppMain.vue -->
<template>
  <div class="app-main">
    <router-view v-slot="{ Component, route: r }">
      <transition name="fade-transform" mode="out-in">
        <keep-alive>
          <component :is="Component" :key="r.path" />
        </keep-alive>
      </transition>
    </router-view>
  </div>
</template>

<style scoped>
.app-main {
  flex: 1;
  padding: 16px 20px;
  overflow-y: auto;
  overflow-x: hidden;
  background: var(--bg-primary);
}

.app-main::-webkit-scrollbar { width: 6px; }
.app-main::-webkit-scrollbar-thumb { background: var(--scrollbar-thumb); border-radius: 3px; }

.fade-transform-enter-active,
.fade-transform-leave-active { transition: all 0.15s ease; }
.fade-transform-enter-from { opacity: 0; transform: translateX(-8px); }
.fade-transform-leave-to { opacity: 0; transform: translateX(8px); }
</style>
