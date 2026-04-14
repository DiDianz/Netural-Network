<!-- src/layout/components/Navbar.vue -->
<template>
  <div class="navbar">
    <!-- 左侧 -->
    <div class="navbar-left">
      <div class="hamburger" @click="$emit('toggleSidebar')">
        <el-icon :size="18">
          <Fold v-if="!isCollapse" />
          <Expand v-else />
        </el-icon>
      </div>
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
        <el-breadcrumb-item v-for="item in breadcrumbs" :key="item.path">
          {{ item.meta && item.meta.title }}
        </el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- 右侧 -->
    <div class="navbar-right">
      <!-- 主题切换 -->
      <ThemeSwitcher />

      <!-- 分隔线 -->
      <div class="navbar-divider"></div>

      <!-- 用户下拉 -->
      <el-dropdown trigger="click" @command="handleCommand">
        <div class="user-wrapper">
          <el-avatar :size="30" class="user-avatar">
            {{ userInitial }}
          </el-avatar>
          <span class="user-name">{{ displayName }}</span>
          <el-icon class="arrow-icon"><ArrowDown /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">
              <el-icon><User /></el-icon>
              <span>个人中心</span>
            </el-dropdown-item>
            <el-dropdown-item command="logout" divided>
              <el-icon><SwitchButton /></el-icon>
              <span>退出登录</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { Fold, Expand, ArrowDown, User, SwitchButton } from '@element-plus/icons-vue'
import { useUserStore } from '../../stores/user'
import { usePermissionStore } from '../../stores/permission'
import ThemeSwitcher from '../../components/ThemeSwitcher.vue'

defineProps({ isCollapse: Boolean })
defineEmits(['toggleSidebar'])

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const permissionStore = usePermissionStore()

const breadcrumbs = computed(() => {
  return route.matched.filter(item => item.meta && item.meta.title && item.path !== '/')
})

const displayName = computed(() => {
  return userStore.nickName || userStore.userName || '用户'
})

const userInitial = computed(() => {
  var name = displayName.value
  return name ? name.charAt(0).toUpperCase() : 'U'
})

async function handleCommand(command) {
  if (command === 'logout') {
    await ElMessageBox.confirm('确认退出系统？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await userStore.logout()
    permissionStore.resetRoutes()
    router.push('/login')
  }
}
</script>

<style scoped>
.navbar {
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-primary);
  flex-shrink: 0;
}

/* ========== 左侧 ========== */
.navbar-left {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
  flex: 1;
}

.hamburger {
  cursor: pointer;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  flex-shrink: 0;
  transition: all 0.2s;
}

.hamburger:hover {
  color: var(--text-primary);
  background: var(--accent-bg-light);
}

/* ========== 右侧 ========== */
.navbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

/* 分隔线 */
.navbar-divider {
  width: 1px;
  height: 24px;
  background: var(--border-primary);
  flex-shrink: 0;
}

/* 用户区域 */
.user-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 10px;
  transition: all 0.2s;
  white-space: nowrap;
}

.user-wrapper:hover {
  background: var(--accent-bg-light);
}

.user-avatar {
  background: var(--accent) !important;
  color: #fff !important;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.user-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.arrow-icon {
  color: var(--text-muted);
  font-size: 12px;
  transition: transform 0.2s;
  flex-shrink: 0;
}

.user-wrapper:hover .arrow-icon {
  color: var(--text-secondary);
}
</style>
