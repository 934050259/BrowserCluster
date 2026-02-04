import { defineStore } from 'pinia'
import { getStats } from '../api'

export const useStatsStore = defineStore('stats', {
  state: () => ({
    stats: {
      today: { total: 0, success: 0, failed: 0, avg_duration: 0 },
      yesterday: { total: 0, success: 0, failed: 0, avg_duration: 0 },
      trends: { total: 0, success: 0, failed: 0, avg_duration: 0 },
      queue: { pending: 0, processing: 0, success: 0, failed: 0 },
      nodes: { total: 0, active: 0, inactive: 0 },
      system_load: 0,
      history: []
    },
    loading: false,
    lastUpdated: null,
    pollingInterval: null
  }),

  getters: {
    totalQueue: (state) => (state.stats.queue?.pending || 0) + (state.stats.queue?.processing || 0)
  },

  actions: {
    async fetchStats() {
      this.loading = true
      try {
        const data = await getStats()
        this.stats = data
        this.lastUpdated = new Date()
      } catch (error) {
        console.error('Failed to fetch stats:', error)
      } finally {
        this.loading = false
      }
    },

    startPolling(intervalMs = 10000) {
      if (this.pollingInterval) return
      
      this.fetchStats()
      this.pollingInterval = setInterval(() => {
        this.fetchStats()
      }, intervalMs)
    },

    stopPolling() {
      if (this.pollingInterval) {
        clearInterval(this.pollingInterval)
        this.pollingInterval = null
      }
    }
  }
})
