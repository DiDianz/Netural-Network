// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '../utils/auth'
import { useUserStore } from '../stores/user'
import { usePermissionStore } from '../stores/permission'

// 静态路由
const constantRoutes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/login/index.vue'),
    meta: { title: '登录', hidden: true }
  },
  {
    path: '/redirect',
    component: () => import('../layout/index.vue'),
    hidden: true,
    children: [
      {
        path: '/redirect/:path(.*)',
        component: () => import('../views/index.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes: constantRoutes,
  scrollBehavior: () => ({ top: 0 })
})

// 白名单 — 不需要登录即可访问
const whiteList = ['/login']

// 路由守卫
router.beforeEach(async (to, from, next) => {
  document.title = to.meta?.title ? `${to.meta.title} - 神经网络预测` : '神经网络预测系统'

  const hasToken = getToken()

  if (hasToken) {
    if (to.path === '/login') {
      // 已登录，跳转首页
      next({ path: '/' })
    } else {
      const userStore = useUserStore()
      const permissionStore = usePermissionStore()

      if (userStore.userId) {
        // 已获取用户信息，直接放行
        next()
      } else {
        try {
          // 获取用户信息
          await userStore.fetchUserInfo()

          // 动态生成路由
          const accessRoutes = await permissionStore.generateRoutes()

          // 添加动态路由
          accessRoutes.forEach(route => {
            router.addRoute(route)
          })

          // 添加兜底 404 路由
          router.addRoute({
            path: '/:pathMatch(.*)*',
            redirect: '/404',
            hidden: true
          })

          // hack: 确保路由已添加
          next({ ...to, replace: true })
        } catch (error) {
          console.error('路由守卫错误:', error)
          // Token 过期，清除并跳转登录
          await userStore.logout()
          next(`/login?redirect=${to.path}`)
        }
      }
    }
  } else {
    // 未登录
    if (whiteList.includes(to.path)) {
      next()
    } else {
      next(`/login?redirect=${to.path}`)
    }
  }
})

export default router
