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

    <!-- 配置列表表格 -->
    <div class="table-container">
      <el-table 
        :data="filteredConfigs" 
        v-loading="loading" 
        style="width: 100%" 
        class="modern-table"
        :header-cell-style="{ background: '#f8fafc', color: '#475569', fontWeight: '600', height: '50px' }"
      >
        <el-table-column prop="key" label="配置键 (Key)" width="350">
          <template #default="{ row }">
            <div class="key-wrapper">
              <div class="key-icon-bg" :class="{ 'is-schema': row.isSchema && !row.isDynamic }">
                <el-icon><Setting /></el-icon>
              </div>
              <code class="key-code" :class="{ 'is-schema': row.isSchema && !row.isDynamic }">{{ row.key }}</code>
              <el-tag v-if="!row.isDynamic" size="small" type="info" effect="plain" class="status-tag">系统默认</el-tag>
              <el-tag v-else size="small" type="success" effect="plain" class="status-tag">已配置</el-tag>
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
            <div v-if="!row.isDynamic" class="unconfigured-hint">
              <el-icon><InfoFilled /></el-icon> 当前使用系统默认值，点击编辑可自定义
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="description" label="说明" min-width="180">
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
      size="50%"
      @closed="stopLogStream"
      class="log-drawer"
    >
      <div class="log-header">
        <el-checkbox v-model="autoScroll">自动滚动</el-checkbox>
        <el-button size="small" @click="logContent = ''">清空屏幕</el-button>
        <el-button size="small" type="primary" @click="startLogStream">重新连接</el-button>
      </div>
      <div class="log-container" ref="logContainer">
        <pre class="log-content">{{ logContent || '正在加载日志...' }}</pre>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Plus, Refresh, Delete, Setting, Timer, Search, 
  Edit, DocumentCopy, InfoFilled, Cpu, Document
} from '@element-plus/icons-vue'
import { 
  getConfigs, 
  getConfigSchema,
  restartSystem,
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

// 日志相关
const logDrawerVisible = ref(false)
const logContent = ref('')
const autoScroll = ref(true)
const logContainer = ref(null)
let logAbortController = null

const filteredConfigs = computed(() => {
  // 合并 schema 和现有配置
  const dbConfigsMap = new Map(configs.value.map(c => [c.key, c]))
  
  const allItems = schema.value.map(s => {
    const dbConfig = dbConfigsMap.get(s.key)
    if (dbConfig) {
      return {
        ...dbConfig,
        isDynamic: true,
        isSchema: true,
        title: s.title,
        type: s.type,
        default: s.default
      }
    } else {
      return {
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
    }
  })

  // 添加不在 schema 中的配置（如果有的话）
  const schemaKeys = new Set(schema.value.map(s => s.key))
  configs.value.forEach(c => {
    if (!schemaKeys.has(c.key)) {
      allItems.push({
        ...c,
        isDynamic: true,
        isSchema: false
      })
    }
  })

  if (!searchQuery.value) return allItems
  const query = searchQuery.value.toLowerCase()
  return allItems.filter(item => 
    item.key.toLowerCase().includes(query) || 
    (item.description && item.description.toLowerCase().includes(query)) ||
    (item.value && String(item.value).toLowerCase().includes(query))
  )
})

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

// 日志处理方法
const handleViewSystemLogs = () => {
  logContent.value = ''
  logDrawerVisible.value = true
  startLogStream()
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
    
    const response = await fetch(`/api/v1/configs/logs?stream=true&lines=100`, {
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
      
      // 限制日志显示长度
      if (logContent.value.length > 50000) {
        logContent.value = logContent.value.substring(logContent.value.length - 50000)
      }
      
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

/* 日志抽屉样式 */
.log-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 20px;
  background-color: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.log-container {
  height: calc(100% - 45px);
  background-color: #0f172a;
  color: #e2e8f0;
  padding: 15px;
  overflow-y: auto;
  font-family: 'Fira Code', 'Courier New', Courier, monospace;
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
  font-size: 13px;
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
