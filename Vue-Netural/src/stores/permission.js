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
        // 合并默认菜单（确保 PLC 等新增模块始终可见）
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

/**
 * 合并默认菜单：如果 API 返回的菜单中缺少某个默认菜单，则补上
 */
function mergeDefaultMenus(apiMenus) {
  const defaults = getDefaultMenus()
  const apiPaths = new Set(apiMenus.map(m => m.path))

  for (const dm of defaults) {
    if (!apiPaths.has(dm.path)) {
      // 默认菜单不在 API 返回中，追加到末尾
      apiMenus.push(dm)
    }
  }
  return apiMenus
}

function getDefaultMenus() {
  return [
    {
      name: 'Index',
      path: '/index',
      hidden: false,
      meta: { title: '首页', icon: 'home' }
    },
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
        { name: 'PredictionTraining', path: 'training', meta: { title: '模型训练', icon: 'cpu' } }
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
