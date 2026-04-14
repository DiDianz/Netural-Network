// src/stores/user.js
import { defineStore } from 'pinia'
import { login as loginApi, logout as logoutApi } from '../api/auth'
import { getUserInfo } from '../api/user'
import { setToken, removeToken, getToken } from '../utils/auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: getToken() || '',
    userId: null,
    userName: '',
    nickName: '',
    avatar: '',
    roles: [],
    permissions: [],
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    isAdmin: (state) => state.roles.includes('admin'),
  },

  actions: {
    async login(loginForm) {
      const res = await loginApi(loginForm)
      this.token = res.token
      setToken(res.token)
      return res
    },

    async fetchUserInfo() {
      const res = await getUserInfo()
      this.userId = res.user_id
      this.userName = res.user_name
      this.nickName = res.nick_name
      this.avatar = res.avatar || ''
      this.roles = res.roles || []
      this.permissions = res.permissions || []
      return res
    },

    async logout() {
      try {
        await logoutApi()
      } catch (e) {
        // 忽略
      }
      this.$reset()
      removeToken()
    },

    $reset() {
      this.token = ''
      this.userId = null
      this.userName = ''
      this.nickName = ''
      this.avatar = ''
      this.roles = []
      this.permissions = []
    }
  }
})
