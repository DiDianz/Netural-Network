// src/stores/permission.js
import { defineStore } from 'pinia'

export const usePermissionStore = defineStore('permission', {
  state: () => ({
    sidebarMenus: []
  }),

  actions: {
    async generateRoutes() {
      try {
        const { getMenuList } = await import('../api/menu')
        const res = await getMenuList()
        let apiMenus = res.data || res || []
        // 过滤掉首页（侧边栏已硬编码），再合并默认菜单
        apiMenus = apiMenus.filter(m => m.path !== '/index')
        this.sidebarMenus = mergeDefaultMenus(apiMenus)
      } catch (error) {
        console.warn('获取菜单失败，使用默认菜单:', error)
        this.sidebarMenus = getDefaultMenus()
      }
    },

    resetRoutes() {
      this.sidebarMenus = []
    }
  }
})

function mergeDefaultMenus(apiMenus) {
  const defaults = getDefaultMenus()

  // 收集所有 API 菜单的父级路径
  const apiParentPaths = new Set(apiMenus.map(m => m.path))

  // 对于 API 中已存在的父级菜单，检查并补充缺失的子菜单
  for (const dm of defaults) {
    const existing = apiMenus.find(m => m.path === dm.path)
    if (existing) {
      // 父级已存在，合并缺失的子菜单
      const childPaths = new Set((existing.children || []).map(c => c.path))
      for (const dc of (dm.children || [])) {
        if (!childPaths.has(dc.path)) {
          if (!existing.children) existing.children = []
          existing.children.push(dc)
        }
      }
    } else {
      // 父级不存在，整体加入
      apiMenus.push(dm)
    }
  }

  return apiMenus
}

function getDefaultMenus() {
  return [
    {
      name: 'System',
      path: '/system',
      hidden: false,
      meta: { title: '系统管理', icon: 'system' },
      children: [
        { name: 'SystemUser', path: 'user', meta: { title: '用户管理', icon: 'user' } },
        { name: 'SystemRole', path: 'role', meta: { title: '角色管理', icon: 'peoples' } },
        { name: 'SystemMenu', path: 'menu', meta: { title: '菜单管理', icon: 'tree-table' } },
        { name: 'SystemConfig', path: 'config', meta: { title: '系统设置', icon: 'setting' } }
      ]
    },
    {
      name: 'Prediction',
      path: '/prediction',
      hidden: false,
      meta: { title: '神经网络预测', icon: 'chart' },
      children: [
        { name: 'PredictionRealtime', path: 'realtime', meta: { title: '实时预测', icon: 'monitor' } },
        { name: 'PredictionHistory', path: 'history', meta: { title: '历史记录', icon: 'date' } },
        { name: 'PredictionModels', path: 'models', meta: { title: '模型管理', icon: 'code' } },
        { name: 'PredictionSavedModels', path: 'saved-models', meta: { title: '已保存模型', icon: 'folder' } },
        { name: 'PredictionInstances', path: 'instances', meta: { title: '预测实例管理', icon: 'list' } },
        { name: 'PredictionTraining', path: 'training', meta: { title: '模型训练', icon: 'cpu' } },
        { name: 'PredictionDryer', path: 'dryer', meta: { title: '烘丝机出口水分模型', icon: 'trend-charts' } }
      ]
    },
    {
      name: 'Plc',
      path: '/plc',
      hidden: false,
      meta: { title: 'PLC管理', icon: 'international' },
      children: [
        { name: 'PlcDevice', path: 'device', meta: { title: 'PLC设备管理', icon: 'cpu' } },
        { name: 'PlcPoint', path: 'point', meta: { title: 'PLC点位管理', icon: 'list' } }
      ]
    }
  ]
}
