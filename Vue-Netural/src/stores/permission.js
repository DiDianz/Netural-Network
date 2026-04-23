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
        // 过滤掉首页（侧边栏已硬编码），数据库为菜单唯一来源
        apiMenus = apiMenus.filter(m => m.path !== '/index')
        this.sidebarMenus = apiMenus
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

// 仅作为 API 不可用时的兜底，正常情况不使用
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
