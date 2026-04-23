// src/router/index.js — 添加 PLC 设备管理路由
import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '../utils/auth'
import Layout from '../layout/index.vue'

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
      },
      {
        path: 'config',
        name: 'SystemConfig',
        component: () => import('../views/system/config/index.vue'),
        meta: { title: '系统设置', icon: 'setting' }
      },
      {
        path: 'log',
        name: 'SystemLog',
        component: () => import('../views/system/log/index.vue'),
        meta: { title: '操作日志', icon: 'document' }
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
        path: 'realtime/:id',
        name: 'PredictionInstance',
        component: () => import('../views/prediction/realtime/index.vue'),
        meta: { title: '实例预测', icon: 'monitor', hidden: true }
      },
      {
        path: 'instances',
        name: 'PredictionInstances',
        component: () => import('../views/prediction/instances/index.vue'),
        meta: { title: '预测实例管理', icon: 'list' }
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
        path: 'saved-models',
        name: 'PredictionSavedModels',
        component: () => import('../views/prediction/saved-models/index.vue'),
        meta: { title: '已保存模型', icon: 'folder' }
      },
      {
        path: 'training',
        name: 'PredictionTraining',
        component: () => import('../views/prediction/training/index.vue'),
        meta: { title: '模型训练', icon: 'cpu' }
      },
      {
        path: 'features',
        name: 'Features',
        component: () => import('../views/prediction/features/index.vue'),
        meta: { title: '特征方案', icon: 'setting' }
      },
      {
        path: 'dryer',
        name: 'PredictionDryer',
        component: () => import('../views/prediction/dryer/index.vue'),
        meta: { title: '烘丝机出口水分模型', icon: 'trend-charts' }
      }
    ]
  },

  // PLC 管理
  {
    path: '/plc',
    component: Layout,
    redirect: '/plc/device',
    meta: { title: 'PLC管理', icon: 'international' },
    children: [
      {
        path: 'device',
        name: 'PlcDevice',
        component: () => import('../views/plc/device/index.vue'),
        meta: { title: 'PLC设备管理', icon: 'cpu' }
      },
      {
        path: 'point',
        name: 'PlcPoint',
        component: () => import('../views/plc/point/index.vue'),
        meta: { title: 'PLC点位管理', icon: 'list' }
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

// 路由守卫
router.beforeEach(async (to, from, next) => {
  document.title = (to.meta && to.meta.title)
    ? to.meta.title + ' - Neural Predict'
    : 'Neural Predict'

  const hasToken = getToken()

  if (to.path === '/login') {
    if (hasToken) {
      next({ path: '/' })
    } else {
      next()
    }
    return
  }

  if (hasToken) {
    try {
      const { useUserStore } = await import('../stores/user')
      const userStore = useUserStore()
      if (!userStore.userId) {
        await userStore.fetchUserInfo()
      }
      next()
    } catch (error) {
      console.error('获取用户信息失败:', error)
      const { useUserStore } = await import('../stores/user')
      const userStore = useUserStore()
      userStore.logout()
      next('/login')
    }
  } else {
    next('/login')
  }
})

export default router
