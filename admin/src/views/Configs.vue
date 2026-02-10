<template>
  <div class="configs-container">
    <!-- 顶部标题栏 -->
    <div class="page-header">
      <div class="header-left">
        <h2 class="header-title">系统配置</h2>
        <p class="header-subtitle">管理系统运行参数及默认抓取设置</p>
      </div>
      <div class="header-actions">
        <el-button type="info" size="large" @click="handleViewSystemLogs" class="action-btn">
          <el-icon><Document /></el-icon> 系统日志
        </el-button>
        <el-button type="warning" size="large" @click="handleExport" class="action-btn">
          <el-icon><Download /></el-icon> 导出配置
        </el-button>
        <el-button type="danger" size="large" @click="handleRestart" :loading="restarting" class="action-btn">
          <el-icon><Cpu /></el-icon> 强制重启
        </el-button>
        <el-button type="primary" size="large" @click="showAddDialog = true" class="action-btn">
          <el-icon><Plus /></el-icon> 新增配置
        </el-button>
        <el-button size="large" @click="loadConfigs" :loading="loading" class="action-btn">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <!-- 重启提示 -->
    <el-alert
      v-if="needsRestart"
      title="配置已更改"
      type="warning"
      description="部分配置更改需要重启系统才能生效。请点击右上角的“强制重启”按钮。"
      show-icon
      class="restart-alert"
    >
      <template #default>
        <div class="alert-content">
          <span>部分配置更改需要重启系统才能生效。</span>
          <el-button type="warning" link @click="handleRestart">立即重启</el-button>
        </div>
      </template>
    </el-alert>

    <!-- 搜索过滤区 -->
    <div class="filter-section">
      <el-input
        v-model="searchQuery"
        placeholder="搜索配置键、值或说明..."
        class="search-input"
        clearable
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>

    <!-- 分类标签页 -->
    <div class="category-tabs">
      <el-tabs v-model="activeTab" class="modern-tabs">
        <el-tab-pane v-for="(cat, key) in categories" :key="key" :name="key">
          <template #label>
            <span class="tab-label">
              <el-icon><component :is="cat.icon" /></el-icon>
              <span>{{ cat.name }}</span>
              <el-badge :value="getCategoryCount(key)" :hidden="getCategoryCount(key) === 0" type="info" class="tab-badge" />
            </span>
          </template>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 配置列表表格 -->
    <div class="table-container">
      <el-table 
        :data="filteredConfigs" 
        v-loading="loading" 
        style="width: 100%" 
        class="modern-table"
        :header-cell-style="{ background: '#f8fafc', color: '#475569', fontWeight: '600', height: '50px' }"
      >
        <el-table-column prop="key" label="配置键 (Key)" width="380">
          <template #default="{ row }">
            <div class="key-wrapper">
              <div class="key-icon-bg" :class="{ 'is-schema': row.isSchema && !row.isDynamic }">
                <el-icon><Setting /></el-icon>
              </div>
              <code class="key-code" :class="{ 'is-schema': row.isSchema && !row.isDynamic }">{{ row.key }}</code>
              <el-tag v-if="row.value === null || row.value === undefined || row.value === ''" size="small" type="danger" effect="plain" class="status-tag">未配置</el-tag>
              <template v-else>
                <el-tag v-if="!row.isDynamic" size="small" type="info" effect="plain" class="status-tag">系统默认</el-tag>
                <el-tag v-else size="small" type="success" effect="plain" class="status-tag">已配置</el-tag>
              </template>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="value" label="配置值 (Value)" min-width="300">
          <template #default="{ row }">
            <el-tooltip :content="String(row.value)" placement="top" :disabled="String(row.value).length < 60">
              <div class="value-container">
                <span class="value-text" :class="{ 'is-schema': row.isSchema && !row.isDynamic }">{{ row.value }}</span>
                <el-icon class="copy-icon" @click.stop="copyValue(row.value)"><DocumentCopy /></el-icon>
              </div>
            </el-tooltip>
            <div v-if="row.value === null || row.value === undefined || row.value === ''" class="unconfigured-hint is-empty">
              <el-icon><Warning /></el-icon> 该项尚未配置，可能会影响系统相关功能
            </div>
            <div v-else-if="!row.isDynamic" class="unconfigured-hint">
              <el-icon><InfoFilled /></el-icon> 当前使用系统默认值，点击编辑可自定义
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="description" label="说明" min-width="200">
          <template #default="{ row }">
             <div class="desc-wrapper">
               <span class="desc-text" :class="{ 'no-desc': !row.description }">
                 {{ row.description || '暂无说明' }}
               </span>
             </div>
          </template>
        </el-table-column>

        <el-table-column prop="updated_at" label="最后更新" width="200" align="center">
          <template #default="{ row }">
            <div class="time-wrapper">
              <el-icon><Timer /></el-icon>
              <span>{{ formatDate(row.updated_at) }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="150" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-links">
              <el-button link type="primary" @click="editConfig(row)">
                <el-icon><Edit /></el-icon> 编辑
              </el-button>
              <el-button link type="danger" @click="confirmDelete(row.key)">
                <el-icon><Delete /></el-icon> 删除
              </el-button>
            </div>
          </template>
        </el-table-column>

        <!-- 空状态 -->
        <template #empty>
          <el-empty description="暂无配置项" :image-size="120" />
        </template>
      </el-table>
    </div>

    <!-- 新增配置对话框 -->
    <el-dialog 
      v-model="showAddDialog" 
      title="新增配置项" 
      width="600px"
      class="modern-dialog"
      destroy-on-close
    >
      <el-form :model="configForm" label-width="100px" label-position="top">
        <el-form-item label="配置键 (Key)" required>
          <el-input v-model="configForm.key" placeholder="例如: browser.max_tabs" />
          <div class="form-tip">建议使用小写字母和点号分隔，如 browser.timeout</div>
        </el-form-item>
        <el-form-item label="配置值 (Value)" required>
          <el-input 
            v-model="configForm.value" 
            type="textarea" 
            :rows="4" 
            placeholder="请输入配置内容，支持 JSON 字符串" 
          />
        </el-form-item>
        <el-form-item label="配置说明">
          <el-input v-model="configForm.description" placeholder="简单描述该配置的用途" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showAddDialog = false" size="large">取消</el-button>
          <el-button type="primary" @click="saveConfig" :loading="loading" size="large">保存配置</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 编辑配置对话框 -->
    <el-dialog 
      v-model="showEditDialog" 
      title="编辑配置项" 
      width="600px"
      class="modern-dialog"
      destroy-on-close
    >
      <el-form :model="editForm" label-width="100px" label-position="top">
        <el-form-item label="配置键 (Key)">
          <el-input v-model="editForm.key" disabled />
          <div class="form-tip">配置键不可修改</div>
        </el-form-item>
        <el-form-item label="配置值 (Value)" required>
          <el-input 
            v-model="editForm.value" 
            type="textarea" 
            :rows="6" 
            placeholder="请输入新配置内容" 
          />
        </el-form-item>
        <el-form-item label="配置说明">
          <el-input v-model="editForm.description" placeholder="更新配置说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showEditDialog = false" size="large">取消</el-button>
          <el-button type="primary" @click="updateConfig" :loading="loading" size="large">提交更新</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 系统日志抽屉 -->
    <el-drawer
      v-model="logDrawerVisible"
      title="系统主日志"
      size="60%"
      @closed="stopLogStream"
      class="log-drawer"
    >
      <div class="log-header">
        <div class="log-controls-left">
          <el-select
            v-model="selectedLogDate"
            placeholder="实时日志"
            size="small"
            style="width: 140px; margin-right: 10px;"
            clearable
            @change="handleLogDateChange"
          >
            <el-option
              v-for="date in availableLogDates"
              :key="date"
              :label="date"
              :value="date"
            />
          </el-select>
          <el-checkbox v-model="autoScroll" :disabled="!!selectedLogDate">自动滚动</el-checkbox>
        </div>
        <div class="log-controls-right">
          <el-button size="small" @click="logContent = ''">清空屏幕</el-button>
          <el-button size="small" type="primary" @click="startLogStream" :disabled="!!selectedLogDate">重新连接</el-button>
          <el-button size="small" type="success" @click="downloadLog">
            <el-icon style="margin-right: 4px;"><Download /></el-icon>导出
          </el-button>
        </div>
      </div>
      <div 
        class="log-container" 
        ref="logContainer" 
        @scroll="handleScroll"
      >
        <div v-if="loadingMore" class="loading-more">正在加载历史日志...</div>
        <div v-if="noMoreLogs" class="no-more">已加载全部历史日志</div>
        <pre class="log-content">{{ logContent || (selectedLogDate ? '该日期暂无日志' : '正在加载日志...') }}</pre>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Plus, Refresh, Delete, Setting, Timer, Search, 
  Edit, DocumentCopy, InfoFilled, Cpu, Document, Download, Warning,
  Monitor, Box, Connection, Cpu as CpuIcon, MagicStick, Cloudy, Share, List
} from '@element-plus/icons-vue'
import { 
  getConfigs, 
  getConfigSchema,
  restartSystem,
  exportConfigs,
  createConfig as createConfigApi, 
  updateConfig as updateConfigApi, 
  deleteConfig as deleteConfigApi 
} from '../api'
import dayjs from 'dayjs'

const loading = ref(false)
const restarting = ref(false)
const needsRestart = ref(false)
const configs = ref([])
const schema = ref([])
const searchQuery = ref('')
const activeTab = ref('all')
const selectedLogDate = ref('')

// 分类定义
const categories = {
  all: { name: '全部配置', icon: 'List' },
  basic: { name: '基础配置', icon: 'Setting' },
  browser: { name: '浏览器', icon: 'Monitor' },
  database: { name: '数据库/队列', icon: 'Box' },
  worker: { name: '节点/Worker', icon: 'CpuIcon' },
  proxy: { name: '代理池', icon: 'Connection' },
  llm: { name: '大模型', icon: 'MagicStick' },
  oss: { name: '存储(OSS)', icon: 'Cloudy' },
  other: { name: '其他', icon: 'Share' }
}

// 键到分类的映射逻辑
const getCategory = (key) => {
  if (key.startsWith('app_') || ['debug', 'host', 'port', 'secret_key', 'algorithm', 'access_token_expire_minutes', 'log_level', 'log_file'].includes(key)) {
    return 'basic'
  }
  if (key.startsWith('browser_') || key.startsWith('default_') || ['headless', 'block_images', 'block_media', 'user_agent', 'stealth_mode', 'browser_idle_timeout'].includes(key)) {
    return 'browser'
  }
  if (key.includes('mongo') || key.includes('redis') || key.includes('rabbitmq')) {
    // 代理池也用 redis，但如果有 proxy 前缀则归类到 proxy
    if (key.startsWith('proxy_')) return 'proxy'
    return 'database'
  }
  if (key.startsWith('worker_') || key.startsWith('node_') || ['retry_enabled', 'max_retries', 'retry_delay', 'heartbeat_interval', 'max_node_auto_retries'].includes(key)) {
    return 'worker'
  }
  if (key.startsWith('llm_')) return 'llm'
  if (key.startsWith('oss_')) return 'oss'
  if (key.startsWith('proxy_')) return 'proxy'
  if (key.includes('cache')) return 'database' // 缓存也归类到数据库/队列
  return 'other'
}

const filteredConfigs = computed(() => {
  // 合并 schema 和现有配置
  const dbConfigsMap = new Map(configs.value.map(c => [c.key, c]))
  
  const allItems = schema.value.map(s => {
    const dbConfig = dbConfigsMap.get(s.key)
    const item = dbConfig ? {
      ...dbConfig,
      isDynamic: true,
      isSchema: true,
      title: s.title,
      type: s.type,
      default: s.default
    } : {
      key: s.key,
      value: s.current_value !== undefined ? s.current_value : s.default,
      description: s.description,
      isDynamic: false,
      isSchema: true,
      title: s.title,
      type: s.type,
      default: s.default,
      updated_at: null
    }
    return { ...item, category: getCategory(item.key) }
  })

  // 添加不在 schema 中的配置
  const schemaKeys = new Set(schema.value.map(s => s.key))
  configs.value.forEach(c => {
    if (!schemaKeys.has(c.key)) {
      allItems.push({
        ...c,
        isDynamic: true,
        isSchema: false,
        category: getCategory(c.key)
      })
    }
  })

  // 按分类过滤
  let result = allItems
  if (activeTab.value !== 'all') {
    result = allItems.filter(item => item.category === activeTab.value)
  }

  // 按搜索查询过滤
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(item => 
      item.key.toLowerCase().includes(query) || 
      (item.description && item.description.toLowerCase().includes(query)) ||
      (item.value && String(item.value).toLowerCase().includes(query))
    )
  }

  return result
})

const getCategoryCount = (categoryKey) => {
  // 计算每个分类的数量，考虑搜索过滤
  const dbConfigsMap = new Map(configs.value.map(c => [c.key, c]))
  const allKeys = new Set([...schema.value.map(s => s.key), ...configs.value.map(c => c.key)])
  
  const allItems = Array.from(allKeys).map(key => {
    const s = schema.value.find(item => item.key === key)
    const dbConfig = dbConfigsMap.get(key)
    const item = dbConfig ? {
      ...dbConfig,
      isDynamic: true,
      isSchema: !!s,
      description: dbConfig.description || (s ? s.description : '')
    } : {
      key: key,
      value: s.current_value !== undefined ? s.current_value : s.default,
      description: s.description,
      isDynamic: false,
      isSchema: true
    }
    return { ...item, category: getCategory(key) }
  })

  let filtered = allItems
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = allItems.filter(item => 
      item.key.toLowerCase().includes(query) || 
      (item.description && item.description.toLowerCase().includes(query)) ||
      (item.value && String(item.value).toLowerCase().includes(query))
    )
  }

  if (categoryKey === 'all') return filtered.length
  return filtered.filter(item => item.category === categoryKey).length
}

// 日志相关
const logDrawerVisible = ref(false)
const logContent = ref('')
const autoScroll = ref(true)
const logContainer = ref(null)
const availableLogDates = ref([])
const loadingMore = ref(false)
const noMoreLogs = ref(false)
let currentOffset = ref(0)
let logAbortController = null
const PAGE_SIZE = 100

const fetchAvailableLogDates = async () => {
  try {
    const token = localStorage.getItem('token')
    const headers = {}
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    
    const response = await fetch('/api/v1/configs/logs/dates', { headers })
    if (response.ok) {
      availableLogDates.value = await response.json()
    }
  } catch (error) {
    console.error('Failed to fetch log dates:', error)
  }
}

const showAddDialog = ref(false)
const showEditDialog = ref(false)
const configForm = ref({
  key: '',
  value: '',
  description: ''
})
const editForm = ref({
  key: '',
  value: '',
  description: ''
})

const loadConfigs = async () => {
  loading.value = true
  try {
    const [dbData, schemaData] = await Promise.all([
      getConfigs(),
      getConfigSchema()
    ])
    configs.value = dbData
    schema.value = schemaData
  } catch (error) {
    ElMessage.error('获取配置信息失败')
  } finally {
    loading.value = false
  }
}

const handleRestart = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要强制重启后端系统吗？重启期间服务将暂时不可用。',
      '强制重启确认',
      {
        confirmButtonText: '确定重启',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    restarting.value = true
    await restartSystem()
    ElMessage.success('重启指令已发送，请稍后刷新页面')
    needsRestart.value = false
    
    // 延迟几秒后尝试刷新页面
    setTimeout(() => {
      window.location.reload()
    }, 3000)
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('重启请求失败')
    }
  } finally {
    restarting.value = false
  }
}

const saveConfig = async () => {
  if (!configForm.value.key || configForm.value.value === undefined || configForm.value.value === '') {
    ElMessage.warning('请填写必填项')
    return
  }
  loading.value = true
  try {
    await createConfigApi(configForm.value)
    ElMessage.success('配置已创建')
    showAddDialog.value = false
    needsRestart.value = true
    // 重置表单
    configForm.value = { key: '', value: '', description: '' }
    loadConfigs()
  } catch (error) {
    ElMessage.error('创建配置失败')
  } finally {
    loading.value = false
  }
}

const editConfig = (row) => {
  editForm.value = { 
    key: row.key,
    value: typeof row.value === 'object' ? JSON.stringify(row.value, null, 2) : String(row.value),
    description: row.description
  }
  showEditDialog.value = true
}

const updateConfig = async () => {
  if (editForm.value.value === undefined || editForm.value.value === '') {
    ElMessage.warning('配置值不能为空')
    return
  }
  loading.value = true
  try {
    // 尝试解析 JSON
    let finalValue = editForm.value.value
    try {
      if ((finalValue.startsWith('{') && finalValue.endsWith('}')) || 
          (finalValue.startsWith('[') && finalValue.endsWith(']'))) {
        finalValue = JSON.parse(finalValue)
      }
    } catch (e) {
      // 不是有效的 JSON，按原样发送
    }

    // 如果是新配置（从 schema 转来的），使用 create
    const isNew = !configs.value.find(c => c.key === editForm.value.key)
    
    if (isNew) {
      await createConfigApi({
        key: editForm.value.key,
        value: finalValue,
        description: editForm.value.description || ''
      })
    } else {
      await updateConfigApi(editForm.value.key, { 
        value: finalValue,
        description: editForm.value.description
      })
    }
    
    ElMessage.success('配置已更新')
    showEditDialog.value = false
    needsRestart.value = true
    loadConfigs()
  } catch (error) {
    ElMessage.error('更新配置失败')
  } finally {
    loading.value = false
  }
}

const confirmDelete = (key) => {
  ElMessageBox.confirm(
    `确定要永久删除配置项 "${key}" 吗？此操作不可恢复。`,
    '安全警告',
    {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'error',
      confirmButtonClass: 'el-button--danger',
    }
  ).then(() => {
    deleteConfig(key)
  }).catch(() => {})
}

const deleteConfig = async (key) => {
  try {
    await deleteConfigApi(key)
    ElMessage.success('配置已删除')
    loadConfigs()
  } catch (error) {
    ElMessage.error('删除配置失败')
  }
}

const copyValue = (value) => {
  navigator.clipboard.writeText(String(value)).then(() => {
    ElMessage.success('配置值已复制到剪贴板')
  })
}

const formatDate = (date) => {
  if (!date) return '-'
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

const handleExport = async () => {
  try {
    const response = await exportConfigs()
    
    // 获取文件名
    let filename = 'configs.env'
    const contentDisposition = response.headers['content-disposition']
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename=(.+)/)
      if (filenameMatch.length > 1) filename = filenameMatch[1]
    }
    
    // 创建下载链接
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    
    // 清理
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('配置导出成功')
  } catch (error) {
    console.error('Export failed:', error)
    ElMessage.error('导出配置失败')
  }
}

// 日志处理方法
const handleViewSystemLogs = () => {
  logContent.value = ''
  selectedLogDate.value = ''
  logDrawerVisible.value = true
  fetchAvailableLogDates()
  startLogStream()
}

const handleLogDateChange = (val) => {
  logContent.value = ''
  currentOffset.value = 0
  noMoreLogs.value = false
  startLogStream()
}

const handleScroll = async (e) => {
  if (autoScroll.value) {
    // 检查是否手动向上滚动，如果是则关闭自动滚动
    const { scrollTop, scrollHeight, clientHeight } = e.target
    if (scrollTop + clientHeight < scrollHeight - 50) {
      autoScroll.value = false
    }
  }

  // 向上滚动加载更多
  if (e.target.scrollTop === 0 && !loadingMore.value && !noMoreLogs.value) {
    await loadMoreLogs()
  }
}

const loadMoreLogs = async () => {
  if (loadingMore.value || noMoreLogs.value) return
  
  loadingMore.value = true
  const oldScrollHeight = logContainer.value.scrollHeight
  
  try {
    const token = localStorage.getItem('token')
    const headers = {}
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    
    // 增加 offset
    currentOffset.value += PAGE_SIZE
    
    let url = `/api/v1/configs/logs?lines=${PAGE_SIZE}&offset=${currentOffset.value}`
    if (selectedLogDate.value) {
      url += `&date=${selectedLogDate.value}`
    }
    
    const response = await fetch(url, { headers })
    if (response.ok) {
      const text = await response.text()
      if (text.trim()) {
        logContent.value = text + logContent.value
        // 保持滚动位置
        nextTick(() => {
          if (logContainer.value) {
            logContainer.value.scrollTop = logContainer.value.scrollHeight - oldScrollHeight
          }
        })
      } else {
        noMoreLogs.value = true
      }
    }
  } catch (error) {
    console.error('Failed to load more logs:', error)
  } finally {
    loadingMore.value = false
  }
}

const downloadLog = () => {
  const token = localStorage.getItem('token')
  const dateParam = selectedLogDate.value ? `&date=${selectedLogDate.value}` : ''
  const url = `/api/v1/configs/logs?download=true${dateParam}&token=${token}`
  
  const link = document.createElement('a')
  link.href = url
  link.target = '_blank'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

const startLogStream = async () => {
  if (logAbortController) {
    logAbortController.abort()
  }
  
  logAbortController = new AbortController()
  
  try {
    const token = localStorage.getItem('token')
    const headers = {}
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    
    // 构建 URL
    let url = '/api/v1/configs/logs?'
    if (selectedLogDate.value) {
      // 选择日期时，先获取最后一页
      url += `date=${selectedLogDate.value}&lines=${PAGE_SIZE}&offset=0`
    } else {
      url += `stream=true&lines=${PAGE_SIZE}`
    }
    
    const response = await fetch(url, {
      headers,
      signal: logAbortController.signal
    })
    
    if (!response.ok) {
      const errorData = await response.json()
      logContent.value = `错误: ${errorData.detail || '无法获取日志'}`
      return
    }
    
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      
      const chunk = decoder.decode(value, { stream: true })
      logContent.value += chunk
      
      if (autoScroll.value) {
        scrollToBottom()
      }
    }
  } catch (error) {
    if (error.name === 'AbortError') {
      console.log('Log stream aborted')
    } else {
      logContent.value += `\n[连接中断: ${error.message}]`
    }
  }
}

const stopLogStream = () => {
  if (logAbortController) {
    logAbortController.abort()
    logAbortController = null
  }
}

const scrollToBottom = () => {
  setTimeout(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  }, 100)
}

onMounted(() => {
  loadConfigs()
})
</script>

<style scoped>
.configs-container {
  padding: 24px;
  background-color: #f1f5f9;
  min-height: calc(100vh - 100px);
}

/* 页面头部 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 24px;
}

.header-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: #1e293b;
}

.header-subtitle {
  margin: 4px 0 0 0;
  font-size: 14px;
  color: #64748b;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.action-btn {
  border-radius: 8px;
  font-weight: 500;
}

/* 重启提示 */
.restart-alert {
  margin-bottom: 24px;
  border-radius: 12px;
  border: 1px solid #fcd34d;
}

.alert-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 搜索过滤 */
.filter-section {
  margin-bottom: 20px;
}

.category-tabs {
  margin-bottom: 20px;
  background: #fff;
  padding: 0 15px;
  border-radius: 12px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.modern-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
  border-bottom: none;
}

.modern-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.modern-tabs :deep(.el-tabs__item) {
  height: 60px;
  font-size: 15px;
  font-weight: 500;
  color: #64748b;
  transition: all 0.3s;
}

.modern-tabs :deep(.el-tabs__item.is-active) {
  color: #3b82f6;
  font-weight: 600;
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tab-badge {
  margin-left: 4px;
}

.tab-badge :deep(.el-badge__content) {
  background-color: #f1f5f9;
  color: #64748b;
  border: none;
}

.modern-tabs :deep(.el-tabs__item.is-active) .tab-badge :deep(.el-badge__content) {
  background-color: #eff6ff;
  color: #3b82f6;
}

/* 日志抽屉样式 */
.log-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 20px;
  background-color: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.log-controls-left, .log-controls-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.log-container {
  height: calc(100% - 50px);
  background-color: #0f172a;
  color: #e2e8f0;
  padding: 15px;
  overflow-y: auto;
  font-family: 'Fira Code', 'Courier New', Courier, monospace;
  position: relative;
}

.loading-more, .no-more {
  text-align: center;
  padding: 10px;
  color: #888;
  font-size: 12px;
}

.log-content {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-size: 13px;
  line-height: 1.5;
}

:deep(.log-drawer .el-drawer__body) {
  padding: 0;
  overflow: hidden;
}

.search-input {
  width: 400px;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: 10px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  padding: 8px 12px;
}

/* 表格容器 */
.table-container {
  background: #ffffff;
  border-radius: 12px;
  padding: 8px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.modern-table {
  border-radius: 8px;
  overflow: hidden;
  --el-table-row-hover-bg-color: #f8fafc;
}

/* 单元格样式 */
.key-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}

.key-icon-bg {
  width: 32px;
  height: 32px;
  background: #eff6ff;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3b82f6;
  font-size: 18px;
}

.key-icon-bg.is-schema {
  background: #f1f5f9;
  color: #94a3b8;
}

.key-code {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 14px;
  font-weight: 600;
  color: #3b82f6;
  background: #f0f7ff;
  padding: 2px 8px;
  border-radius: 4px;
}

.key-code.is-schema {
  color: #64748b;
  background: #f1f5f9;
}

.status-tag {
  margin-left: 8px;
  font-size: 10px;
  height: 20px;
  padding: 0 6px;
}

.value-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding-right: 8px;
}

.value-text {
  font-size: 14px;
  color: #475569;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: 'Inter', system-ui, sans-serif;
}

.value-text.is-schema {
  color: #94a3b8;
}

.unconfigured-hint {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.unconfigured-hint.is-empty {
  color: #ef4444;
  font-weight: 500;
}

.copy-icon {
  font-size: 14px;
  color: #94a3b8;
  cursor: pointer;
  transition: color 0.2s;
  opacity: 0;
}

.value-container:hover .copy-icon {
  opacity: 1;
}

.copy-icon:hover {
  color: #3b82f6;
}

.desc-text {
  font-size: 14px;
  color: #475569;
  line-height: 1.5;
}

.desc-text.no-desc {
  color: #94a3b8;
  font-style: italic;
}

.time-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: #64748b;
  font-size: 14px;
}

.action-links {
  display: flex;
  justify-content: center;
  gap: 16px;
}

.action-links :deep(.el-button) {
  padding: 0;
  font-weight: 500;
}

/* 对话框样式 */
.modern-dialog :deep(.el-dialog__header) {
  margin-right: 0;
  padding: 20px 24px;
  border-bottom: 1px solid #f1f5f9;
}

.modern-dialog :deep(.el-dialog__title) {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}

.modern-dialog :deep(.el-dialog__body) {
  padding: 24px;
}

.form-tip {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 12px;
}

:deep(.el-form-item__label) {
  font-weight: 600;
  color: #475569;
  padding-bottom: 8px !important;
}

:deep(.el-input__wrapper), :deep(.el-textarea__inner) {
  box-shadow: 0 0 0 1px #e2e8f0 inset;
  border-radius: 8px;
}

:deep(.el-input__wrapper.is-focus), :deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 1px #3b82f6 inset !important;
}
</style>
