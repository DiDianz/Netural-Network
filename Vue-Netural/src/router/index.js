// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '../utils/auth'
import Layout from '../layout/index.vue'
import path from 'node:path'

// ========== 所有路由全部写死 ==========
const routes = [
  // 登录（不需要登录）
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/login/index.vue'),
    meta: { title: '登录', hidden: true }
  },

  // 404
  {
    path: '/404',
    name: 'NotFound',
    component: () => import('../views/404.vue'),
    meta: { title: '404', hidden: true }
  },

  // 首页
  {
    path: '/',
    component: Layout,
    redirect: '/index',
    children: [
      {
        path: 'index',
        name: 'Index',
        component: () => import('../views/index.vue'),
        meta: { title: '首页', icon: 'home', affix: true }
      }
    ]
  },

  // 系统管理
  {
    path: '/system',
    component: Layout,
    redirect: '/system/user',
    meta: { title: '系统管理', icon: 'system' },
    children: [
      {
        path: 'user',
        name: 'SystemUser',
        component: () => import('../views/system/user/index.vue'),
        meta: { title: '用户管理', icon: 'user' }
      },
      {
        path: 'role',
        name: 'SystemRole',
        component: () => import('../views/system/role/index.vue'),
        meta: { title: '角色管理', icon: 'peoples' }
      },
      {
        path: 'menu',
        name: 'SystemMenu',
        component: () => import('../views/system/menu/index.vue'),
        meta: { title: '菜单管理', icon: 'tree-table' }
      }
    ]
  },

  // 神经网络预测
  {
    path: '/prediction',
    component: Layout,
    redirect: '/prediction/realtime',
    meta: { title: '神经网络预测', icon: 'chart' },
    children: [
      {
        path: 'realtime',
        name: 'PredictionRealtime',
        component: () => import('../views/prediction/realtime/index.vue'),
        meta: { title: '实时预测', icon: 'monitor' }
      },
      {
        path: 'history',
        name: 'PredictionHistory',
        component: () => import('../views/prediction/history/index.vue'),
        meta: { title: '历史记录', icon: 'date' }
      },
      {
        path: 'models',
        name: 'PredictionModels',
        component: () => import('../views/prediction/models/index.vue'),
        meta: { title: '模型管理', icon: 'code' }
      },
      {
        path:'training',
        name:'PredictionTraining',
        component: () => import('../views/prediction/training/index.vue'),
        meta: { title: '模型训练', icon: 'cpu' }
      }
    ]
  },

  // 兜底 404
  {
    path: '/:pathMatch(.*)*',
    redirect: '/404'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes: routes,
  scrollBehavior: () => ({ top: 0 })
})

// ========== 路由守卫（极简版）==========
router.beforeEach(async (to, from, next) => {
  // 设置标题
  document.title = (to.meta && to.meta.title)
    ? to.meta.title + ' - Neural Predict'
    : 'Neural Predict'

  const hasToken = getToken()

  if (to.path === '/login') {
    // 已登录访问登录页 → 跳首页
    if (hasToken) {
      next({ path: '/' })
    } else {
      next()
    }
    return
  }

  if (hasToken) {
    // 已登录，获取用户信息（如果还没有）
    try {
      const { useUserStore } = await import('../stores/user')
      const userStore = useUserStore()

      if (!userStore.userId) {
        await userStore.fetchUserInfo()
      }

      next()
    } catch (error) {
      console.error('获取用户信息失败:', error)
      // Token 无效，清除并跳转登录
      const { useUserStore } = await import('../stores/user')
      const userStore = useUserStore()
      userStore.logout()
      next('/login')
    }
  } else {
    // 未登录
    next('/login')
  }
})

export default router
