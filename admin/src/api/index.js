import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000
})

// Request interceptor to add token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const isLoginPage = window.location.pathname === '/login'
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      if (!isLoginPage) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export const login = async (username, password) => {
  const formData = new FormData()
  formData.append('username', username)
  formData.append('password', password)
  const response = await api.post('/auth/login', formData)
  return response.data
}

export const getMe = async () => {
  const response = await api.get('/auth/me')
  return response.data
}

export const getUsers = async () => {
  const response = await api.get('/users/')
  return response.data
}

export const createUser = async (data) => {
  const response = await api.post('/users/', data)
  return response.data
}

export const updateUser = async (userId, data) => {
  const response = await api.put(`/users/${userId}`, data)
  return response.data
}

export const deleteUser = async (userId) => {
  const response = await api.delete(`/users/${userId}`)
  return response.data
}

export const scrape = async (data) => {
  const response = await api.post('/scrape/', data)
  return response.data
}

export const scrapeAsync = async (data) => {
  const response = await api.post('/scrape/async', data)
  return response.data
}

export const scrapeBatch = async (data) => {
  const response = await api.post('/scrape/batch', data)
  return response.data
}

export const getTask = async (taskId, params = {}) => {
  const response = await api.get(`/tasks/${taskId}`, { params })
  return response.data
}

export const getTasks = async (params) => {
  const response = await api.get('/tasks/', { params })
  return response.data
}

export const deleteTask = async (taskId) => {
  const response = await api.delete(`/tasks/${taskId}`)
  return response.data
}

// Rules API
export const getRules = async (params = {}) => {
  const response = await api.get('/rules/', { params })
  return response.data
}

export const getRulesByDomain = async (domain) => {
  const response = await api.get(`/rules/domain/${domain}`)
  return response.data
}

export const createRule = async (data) => {
  const response = await api.post('/rules/', data)
  return response.data
}

export const updateRule = async (ruleId, data) => {
  const response = await api.put(`/rules/${ruleId}`, data)
  return response.data
}

export const deleteRule = async (ruleId) => {
  const response = await api.delete(`/rules/${ruleId}`)
  return response.data
}

export const deleteTasksBatch = async (taskIds) => {
  const response = await api.delete('/tasks/batch', { data: { task_ids: taskIds } })
  return response.data
}

export const retryTask = async (taskId, data = null) => {
  const response = await api.post(`/tasks/${taskId}/retry`, data)
  return response.data
}

// 定时任务相关 API
export const getSchedules = async (params) => {
  const response = await api.get('/schedules/', { params })
  return response.data
}

export const getSchedule = async (scheduleId) => {
  const response = await api.get(`/schedules/${scheduleId}`)
  return response.data
}

export const createSchedule = async (data) => {
  const response = await api.post('/schedules/', data)
  return response.data
}

export const updateSchedule = async (scheduleId, data) => {
  const response = await api.put(`/schedules/${scheduleId}`, data)
  return response.data
}

export const deleteSchedule = async (scheduleId) => {
  const response = await api.delete(`/schedules/${scheduleId}`)
  return response.data
}

export const toggleSchedule = async (scheduleId) => {
  const response = await api.post(`/schedules/${scheduleId}/toggle`)
  return response.data
}

export const runScheduleNow = async (scheduleId) => {
  const response = await api.post(`/schedules/${scheduleId}/run`)
  return response.data
}

export const getStats = async () => {
  const response = await api.get('/stats/')
  return response.data
}

export const getConfigs = async () => {
  const response = await api.get('/configs/')
  return response.data
}

export const getConfigSchema = async () => {
  const response = await api.get('/configs/schema')
  return response.data
}

export const restartSystem = async () => {
  const response = await api.post('/configs/restart')
  return response.data
}

export const createConfig = async (data) => {
  const response = await api.post('/configs/', data)
  return response.data
}

export const updateConfig = async (key, data) => {
  const response = await api.put(`/configs/${key}`, data)
  return response.data
}

// Proxy API
export const getProxies = async (params) => {
  const response = await api.get('/proxy/', { params })
  return response.data
}

export const getProxyStats = async () => {
  const response = await api.get('/proxy/stats')
  return response.data
}

export const createProxy = async (data) => {
  const response = await api.post('/proxy/', data)
  return response.data
}

export const updateProxy = async (proxyId, data) => {
  const response = await api.put(`/proxy/${proxyId}`, data)
  return response.data
}

export const deleteProxy = async (proxyId) => {
  const response = await api.delete(`/proxy/${proxyId}`)
  return response.data
}

export const batchDeleteProxies = async (proxyIds) => {
  const response = await api.post('/proxy/batch-delete', proxyIds)
  return response.data
}

export const importProxies = async (data) => {
  const response = await api.post('/proxy/import', data)
  return response.data
}

export const checkAllProxies = async () => {
  const response = await api.post('/proxy/check-all')
  return response.data
}

export const checkProxy = async (proxyId) => {
  const response = await api.post(`/proxy/${proxyId}/check`)
  return response.data
}

export const exportProxies = async () => {
  const response = await api.get('/proxy/export-all')
  return response.data
}

export const getRandomProxy = async (group = 'default') => {
  const response = await api.get('/proxy/random', { params: { group } })
  return response.data
}

export const getProxyConfig = async () => {
  const response = await api.get('/proxy/config')
  return response.data
}

export const updateProxyConfig = async (data) => {
  const response = await api.put('/proxy/config', data)
  return response.data
}

export const exportConfigs = async () => {
  const response = await api.get('/configs/export', { responseType: 'blob' })
  return response
}

export const deleteConfig = async (key) => {
  const response = await api.delete(`/configs/${key}`)
  return response.data
}

// Node management
export const getNodes = async () => {
  const response = await api.get('/nodes/')
  return response.data
}

export const createNode = async (data) => {
  const response = await api.post('/nodes/', data)
  return response.data
}

export const updateNode = async (nodeId, data) => {
  const response = await api.put(`/nodes/${nodeId}`, data)
  return response.data
}

export const startNode = async (nodeId) => {
  const response = await api.post(`/nodes/${nodeId}/start`)
  return response.data
}

export const stopNode = async (nodeId) => {
  const response = await api.post(`/nodes/${nodeId}/stop`)
  return response.data
}

export const deleteNode = async (nodeId) => {
  const response = await api.delete(`/nodes/${nodeId}`)
  return response.data
}

export const getNodeLogs = (nodeId, params) => {
  return api.get(`/nodes/${nodeId}/logs`, { params, responseType: 'text' })
}

// Scrapers API
export const getScrapers = async () => {
  const response = await api.get('/scrapers/')
  return response.data
}

export const getScraper = async (id) => {
  const response = await api.get(`/scrapers/${id}`)
  return response.data
}

export const createScraper = async (data) => {
  const response = await api.post('/scrapers/', data)
  return response.data
}

export const updateScraper = async (id, data) => {
  const response = await api.put(`/scrapers/${id}`, data)
  return response.data
}

export const deleteScraper = async (id) => {
  const response = await api.delete(`/scrapers/${id}`)
  return response.data
}

export const testScraper = async (data) => {
  const response = await api.post('/scrapers/test', data, { timeout: 120000 })
  return response.data
}

export const aiGenerateRules = async (data) => {
  const response = await api.post('/scrapers/ai-generate-rules', data, { timeout: 120000 })
  return response.data
}

export const runScraper = async (id) => {
  const response = await api.post(`/scrapers/${id}/run`)
  return response.data
}

export const getScraperData = async (id, params) => {
  const response = await api.get(`/scrapers/${id}/data`, { params })
  return response.data
}
