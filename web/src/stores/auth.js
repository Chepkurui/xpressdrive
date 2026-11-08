import { defineStore } from 'pinia'
import { api, refreshAccessToken, setAccessToken, setAuthLostHandler } from '@/api/client'

export const useAuthStore = defineStore('auth', {
  state: () => ({ user: null, initialized: false }),
  getters: {
    isAuthenticated: (s) => !!s.user,
    isStaff: (s) => !!s.user?.is_staff,
    // can('shipments') / can('users', 'change'): mirrors the API's Django model permissions.
    can: (s) => (section, action = 'view') => !!s.user?.staff_access?.[section]?.[action],
  },
  actions: {
    async init() {
      if (this.initialized) return
      setAuthLostHandler(() => {
        this.user = null
      })
      if (await refreshAccessToken()) {
        try {
          await this.loadMe()
        } catch {
          this.user = null
        }
      }
      this.initialized = true
    },
    async loadMe() {
      this.user = await api('/auth/me/')
      return this.user
    },
    async login(email, password) {
      const data = await api('/auth/login/', { method: 'POST', body: { email, password }, auth: false })
      setAccessToken(data.access)
      await this.loadMe()
    },
    async register(payload) {
      await api('/auth/register/', { method: 'POST', body: payload, auth: false })
      await this.login(payload.email, payload.password)
    },
    async updateProfile(patch) {
      this.user = await api('/auth/me/', { method: 'PATCH', body: patch })
    },
    async logout() {
      try {
        await api('/auth/logout/', { method: 'POST', auth: false })
      } finally {
        setAccessToken(null)
        this.user = null
      }
    },
    clearLocal() {
      setAccessToken(null)
      this.user = null
    },
  },
})
