<template>
  <div class="cookies-container">
    <!-- 顶部标题栏 -->
    <div class="page-header">
      <div class="header-left">
        <h2 class="header-title">Cookie 池管理</h2>
        <p class="header-subtitle">管理账号 Cookie 资源，支持频率控制、自动检测与分组调度</p>
      </div>
      <div class="header-actions">
        <el-button 
          v-if="selectedIds.length > 0"
          type="danger" 
          @click="handleBatchDelete" 
          :loading="loading"
          class="custom-btn-danger"
        >
          <el-icon><Delete /></el-icon>
          <span>批量删除 ({{ selectedIds.length }})</span>
        </el-button>
        <el-button @click="fetchData" :loading="loading" class="custom-btn-outline">
          <el-icon><Refresh /></el-icon>
          <span>刷新</span>
        </el-button>
        <el-button @click="handleCheckAll" :loading="checkingAll" class="custom-btn-outline">
          <el-icon><Connection /></el-icon>
          <span>一键检测</span>
        </el-button>
        <el-button @click="handleImport" class="custom-btn-outline">
          <el-icon><Upload /></el-icon>
          <span>批量导入</span>
        </el-button>
        <el-button @click="handleExport" class="custom-btn-outline">
          <el-icon><Download /></el-icon>
          <span>导出 Cookie</span>
        </el-button>
        <el-button type="primary" @click="handleAdd" class="custom-btn">
          <el-icon><Plus /></el-icon>
          <span>添加 Cookie</span>
        </el-button>
      </div>
    </div>

    <!-- 统计概览 - Bento Grid Style -->
    <div class="stats-grid">
      <div class="stats-card-wrapper total">
        <div class="stats-card-inner">
          <div class="card-icon"><el-icon><List /></el-icon></div>
          <div class="card-info">
            <div class="card-label">总账号数</div>
            <div class="card-value">{{ stats.total || 0 }}</div>
          </div>
        </div>
      </div>
      <div class="stats-card-wrapper active">
        <div class="stats-card-inner">
          <div class="card-icon"><el-icon><Check /></el-icon></div>
          <div class="card-info">
            <div class="card-label">可用账号</div>
            <div class="card-value">{{ stats.active || 0 }}</div>
          </div>
        </div>
      </div>
      <div class="stats-card-wrapper inactive">
        <div class="stats-card-inner">
          <div class="card-icon"><el-icon><Close /></el-icon></div>
          <div class="card-info">
            <div class="card-label">失效账号</div>
            <div class="card-value">{{ stats.invalid || 0 }}</div>
          </div>
        </div>
      </div>
      <div class="stats-card-wrapper config clickable" @click="handleEditConfig">
        <div class="stats-card-inner">
          <div class="card-icon"><el-icon><Search /></el-icon></div>
          <div class="card-info">
            <div class="card-label">
              检测配置
              <el-tag 
                :type="settings.cookie_enable_check ? 'success' : 'info'" 
                size="small" 
                class="status-tag"
              >
                {{ settings.cookie_enable_check ? '开启' : '关闭' }}
              </el-tag>
              <el-icon class="edit-hint-icon"><Edit /></el-icon>
            </div>
            <div class="config-details">
              <template v-if="settings.cookie_enable_check">
                <div class="detail-row">
                  <span class="detail-item">间隔: {{ settings.cookie_check_interval }}s</span>
                  <span class="detail-item">超时: {{ settings.cookie_check_timeout }}s</span>
                </div>
                <div class="detail-row">
                  <span class="detail-item">阈值: {{ settings.cookie_fail_threshold }}次</span>
                  <span class="detail-item">默认频控: {{ settings.cookie_default_rate_limit }}次/分</span>
                </div>
              </template>
              <div v-else class="config-disabled-msg">
                自动检测功能已禁用
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 过滤器 -->
    <el-card shadow="never" class="filter-card custom-card">
      <div class="filter-header">
        <div class="filter-title">
          <el-icon><Filter /></el-icon>
          <span>筛选与查询</span>
        </div>
      </div>
      <el-form :inline="true" :model="filter" class="filter-form">
        <el-form-item label="域名">
          <el-select v-model="filter.domain" placeholder="全部域名" clearable @change="fetchData" class="custom-select">
            <el-option v-for="d in stats.domains" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="分组">
          <el-select v-model="filter.group" placeholder="全部分组" clearable @change="fetchData" class="custom-select">
            <el-option v-for="g in stats.groups" :key="g" :label="g" :value="g" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filter.status" placeholder="全部状态" clearable @change="fetchData" class="custom-select">
            <el-option label="可用" value="active" />
            <el-option label="不可用" value="inactive" />
          </el-select>
        </el-form-item>
        <el-form-item class="filter-actions">
          <el-button type="primary" @click="fetchData" class="custom-btn">
            <el-icon><Search /></el-icon>
            <span>查询</span>
          </el-button>
          <el-button @click="resetFilter" class="custom-btn-outline">
            <el-icon><RefreshRight /></el-icon>
            <span>重置</span>
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 数据表格 -->
    <el-card shadow="never" class="table-card custom-card">
      <el-table 
        :data="cookies" 
        v-loading="loading" 
        style="width: 100%;" 
        class="custom-table"
        @selection-change="handleSelectionChange"
        :header-cell-style="{ background: '#f8fafc', color: '#64748b', fontWeight: '600' }"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column label="域名 / 账号" min-width="200">
          <template #default="{ row }">
            <div class="cookie-info-cell">
              <el-tag size="small" effect="dark" class="domain-tag">
                {{ row.domain }}
              </el-tag>
              <span class="username-text">{{ row.username }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="group" label="分组" width="120">
          <template #default="{ row }">
            <el-tag type="warning" effect="plain" class="group-tag">{{ row.group }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="rate_limit" label="频控限制" width="120">
          <template #default="{ row }">
            <span>{{ row.rate_limit }} 次/分</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <div class="status-cell">
              <span :class="['status-dot', row.status === 'active' ? 'active' : 'inactive']"></span>
              <span :class="['status-text', row.status === 'active' ? 'active' : 'inactive']">
                {{ row.status === 'active' ? '可用' : '不可用' }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="使用统计" width="180">
          <template #default="{ row }">
            <div class="stats-cell">
              <span class="stats-item">总计: {{ row.total_count }}</span>
              <span class="stats-item fail" v-if="row.fail_count > 0">连续失败: {{ row.fail_count }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="last_check_at" label="最后检测" width="180">
          <template #default="{ row }">
            <span class="time-text">{{ formatTime(row.last_check_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="action-btns">
              <el-button link type="primary" @click="handleCheck(row)" :loading="row.checking" class="action-link">检测</el-button>
              <el-divider direction="vertical" />
              <el-button link type="primary" @click="handleEdit(row)" class="action-link">编辑</el-button>
              <el-divider direction="vertical" />
              <el-button link type="danger" @click="handleDelete(row)" class="action-link">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页组件 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100, 200]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 添加/编辑对话框 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="isEdit ? '编辑 Cookie' : '添加 Cookie'" 
      width="600px"
      destroy-on-close
    >
      <el-form :model="form" label-width="100px" :rules="formRules" ref="formRef">
        <el-form-item label="域名" prop="domain">
          <el-input v-model="form.domain" placeholder="example.com" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="user1" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="可选，用于自动登录" />
        </el-form-item>
        <el-form-item label="Cookie 内容" prop="value">
          <el-input 
            v-model="form.valueStr" 
            type="textarea" 
            :rows="6" 
            placeholder='{"name": "value", ...} 或 [{"name": "...", "value": "..."}]' 
          />
          <div class="input-tip">支持 JSON 对象或 JSON 数组格式</div>
        </el-form-item>
        <el-form-item label="分组" prop="group">
          <el-input v-model="form.group" placeholder="default" />
        </el-form-item>
        <el-form-item label="频率限制" prop="rate_limit">
          <el-input-number v-model="form.rate_limit" :min="0" :max="10000" style="width: 100%" />
          <div class="input-tip">每分钟最大调用次数 (0 为不限制)</div>
        </el-form-item>
        <el-form-item label="状态" prop="status" v-if="isEdit">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="可用" value="active" />
            <el-option label="不可用" value="inactive" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 导入对话框 -->
    <el-dialog v-model="importVisible" title="批量导入 Cookie" width="700px">
      <el-form label-position="top">
        <el-form-item label="Cookie 列表 (JSON 数组格式)">
          <el-input 
            v-model="importText" 
            type="textarea" 
            :rows="12" 
            placeholder='[
  {
    "domain": "example.com",
    "username": "user1",
    "value": {...},
    "group": "default",
    "rate_limit": 60
  },
  ...
]' 
          />
          <div class="input-tip">请粘贴包含 domain, username, value 字段的 JSON 数组</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" @click="submitImport" :loading="submitting">开始导入</el-button>
      </template>
    </el-dialog>

    <!-- 配置对话框 -->
    <el-dialog v-model="configDialogVisible" title="Cookie 检测配置" width="500px">
      <el-form :model="configForm" label-width="140px">
        <el-form-item label="启用检测">
          <el-switch v-model="configForm.cookie_enable_check" />
          <div class="input-tip">开启后，系统将定期自动检测 Cookie 的有效性</div>
        </el-form-item>
        <el-form-item label="检测间隔 (秒)" v-if="configForm.cookie_enable_check">
          <el-input-number v-model="configForm.cookie_check_interval" :min="10" :max="3600" style="width: 100%" />
        </el-form-item>
        <el-form-item label="超时时间 (秒)" v-if="configForm.cookie_enable_check">
          <el-input-number v-model="configForm.cookie_check_timeout" :min="1" :max="60" style="width: 100%" />
        </el-form-item>
        <el-form-item label="失败阈值 (次)" v-if="configForm.cookie_enable_check">
          <el-input-number v-model="configForm.cookie_fail_threshold" :min="1" :max="10" style="width: 100%" />
          <div class="input-tip">连续失败多少次后，将 Cookie 标记为不可用</div>
        </el-form-item>
        <el-form-item label="默认频控 (次/分)">
          <el-input-number v-model="configForm.cookie_default_rate_limit" :min="1" :max="10000" style="width: 100%" />
          <div class="input-tip">新添加 Cookie 的默认频率限制</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="configDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitConfigForm" :loading="submitting">保存配置</el-button>
      </template>
    </el-dialog>

    <!-- 导出确认对话框 -->
    <el-dialog v-model="exportVisible" title="导出 Cookie" width="400px">
      <div class="export-options">
        <p class="export-tip">将导出所有 Cookie 数据为 JSON 文件。</p>
      </div>
      <template #footer>
        <el-button @click="exportVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmExport">确定导出</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.stats-item {
  display: block;
  font-size: 12px;
  color: #64748b;
}

.stats-item.fail {
  color: #ef4444;
}

.export-options {
  padding: 10px 0;
}

.export-tip {
  margin-bottom: 15px;
  color: #64748b;
}
</style>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Upload, Download, Connection, List, Check, Close, Search, Refresh, Edit, Delete, RefreshRight } from '@element-plus/icons-vue'
import { 
  getCookies, 
  getCookieStats, 
  createCookie, 
  updateCookie, 
  deleteCookie, 
  batchDeleteCookies,
  importCookies,
  exportCookies,
  getCookieConfig,
  updateCookieConfig,
  checkAllCookies,
  checkCookie
} from '@/api'
import dayjs from 'dayjs'

const loading = ref(false)
const checkingAll = ref(false)
const submitting = ref(false)
const cookies = ref([])
const stats = ref({})
const selectedIds = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const settings = ref({
  cookie_enable_check: true,
  cookie_check_interval: 300,
  cookie_check_timeout: 15,
  cookie_fail_threshold: 3,
  cookie_default_rate_limit: 60
})
const filter = ref({
  domain: '',
  group: '',
  status: ''
})

const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const form = ref({
  domain: '',
  username: '',
  password: '',
  valueStr: '',
  value: {},
  group: 'default',
  rate_limit: 60,
  status: 'active'
})

const formRules = {
  domain: [{ required: true, message: '请输入域名', trigger: 'blur' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  valueStr: [{ required: true, message: '请输入 Cookie 内容', trigger: 'blur' }]
}

const importVisible = ref(false)
const importText = ref('')

const configDialogVisible = ref(false)
const configForm = ref({
  cookie_enable_check: true,
  cookie_check_interval: 300,
  cookie_check_timeout: 15,
  cookie_fail_threshold: 3,
  cookie_default_rate_limit: 60
})

const exportVisible = ref(false)

const fetchData = async () => {
  loading.value = true
  try {
    const params = {
      ...filter.value,
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value
    }
    const [cookiesResponse, statsData, configData] = await Promise.all([
      getCookies(params),
      getCookieStats(),
      getCookieConfig()
    ])
    cookies.value = cookiesResponse.items
    total.value = cookiesResponse.total
    stats.value = statsData
    
    if (configData) {
      settings.value = { ...settings.value, ...configData }
    }
  } catch (error) {
    console.error('Fetch error:', error)
    ElMessage.error('获取 Cookie 数据失败')
  } finally {
    loading.value = false
  }
}

const resetFilter = () => {
  filter.value = { domain: '', group: '', status: '' }
  currentPage.value = 1
  fetchData()
}

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  fetchData()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchData()
}

const handleAdd = () => {
  isEdit.value = false
  form.value = {
    domain: '',
    username: '',
    password: '',
    valueStr: '',
    value: {},
    group: 'default',
    rate_limit: settings.value.cookie_default_rate_limit,
    status: 'active'
  }
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  form.value = { 
    ...row,
    valueStr: JSON.stringify(row.value, null, 2)
  }
  dialogVisible.value = true
}

const handleCheck = async (row) => {
  row.checking = true
  try {
    const res = await checkCookie(row.id)
    if (res.active) {
      ElMessage.success(`Cookie ${row.username}@${row.domain} 检测可用`)
    } else {
      ElMessage.warning(`Cookie ${row.username}@${row.domain} 检测不可用`)
    }
    setTimeout(() => {
      fetchData()
    }, 500)
  } catch (error) {
    console.error('Check cookie error:', error)
    ElMessage.error('检测失败')
  } finally {
    row.checking = false
  }
}

const handleCheckAll = async () => {
  checkingAll.value = true
  try {
    await checkAllCookies()
    ElMessage.success('已开始全量检测，请稍后刷新查看结果')
    setTimeout(() => {
      fetchData()
    }, 2000)
  } catch (error) {
    console.error('Check all error:', error)
    ElMessage.error('启动全量检测失败')
  } finally {
    checkingAll.value = false
  }
}

const handleDelete = (row) => {
  ElMessageBox.confirm(`确定删除 Cookie ${row.username}@${row.domain} 吗？`, '警告', {
    type: 'warning'
  }).then(async () => {
    await deleteCookie(row.id)
    ElMessage.success('删除成功')
    fetchData()
  })
}

const handleSelectionChange = (selection) => {
  selectedIds.value = selection.map(item => item.id)
}

const handleBatchDelete = () => {
  if (selectedIds.value.length === 0) return
  
  ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.length} 个 Cookie 吗？`, '批量删除警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    loading.value = true
    try {
      await batchDeleteCookies(selectedIds.value)
      ElMessage.success('批量删除成功')
      selectedIds.value = []
      fetchData()
    } catch (error) {
      console.error('Batch delete error:', error)
      ElMessage.error('批量删除失败')
    } finally {
      loading.value = false
    }
  })
}

const submitForm = async () => {
  if (!formRef.value) return
  await formRef.value.validate()
  
  try {
    const valueObj = JSON.parse(form.value.valueStr)
    form.value.value = valueObj
  } catch (e) {
    ElMessage.error('Cookie 内容必须是有效的 JSON 格式')
    return
  }
  
  submitting.value = true
  try {
    if (isEdit.value) {
      await updateCookie(form.value.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await createCookie(form.value)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch (error) {
    ElMessage.error(isEdit.value ? '更新失败' : '添加失败')
  } finally {
    submitting.value = false
  }
}

const handleImport = () => {
  importText.value = ''
  importVisible.value = true
}

const submitImport = async () => {
  if (!importText.value.trim()) return
  
  let parsedCookies = []
  try {
    parsedCookies = JSON.parse(importText.value)
    if (!Array.isArray(parsedCookies)) {
      throw new Error('必须是 JSON 数组')
    }
  } catch (e) {
    ElMessage.error('JSON 格式错误: ' + e.message)
    return
  }
  
  submitting.value = true
  try {
    const count = await importCookies(parsedCookies)
    ElMessage.success(`成功导入 ${count} 个 Cookie`)
    importVisible.value = false
    fetchData()
  } catch (error) {
    ElMessage.error('导入失败')
  } finally {
    submitting.value = false
  }
}

const handleExport = () => {
  exportVisible.value = true
}

const confirmExport = async () => {
  try {
    const data = await exportCookies()
    const content = JSON.stringify(data, null, 2)
    const filename = `cookies_export_${dayjs().format('YYYYMMDD_HHmmss')}.json`
    const mimeType = 'application/json'

    const blob = new Blob([content], { type: mimeType })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    window.URL.revokeObjectURL(url)
    exportVisible.value = false
    ElMessage.success('导出成功')
  } catch (error) {
    console.error('Export error:', error)
    ElMessage.error('导出失败')
  }
}

const handleEditConfig = () => {
  configForm.value = { ...settings.value }
  configDialogVisible.value = true
}

const submitConfigForm = async () => {
  submitting.value = true
  try {
    await updateCookieConfig(configForm.value)
    ElMessage.success('配置更新成功')
    configDialogVisible.value = false
    fetchData()
  } catch (error) {
    console.error('Update config error:', error)
    ElMessage.error('配置更新失败')
  } finally {
    submitting.value = false
  }
}

const formatTime = (time) => {
  if (!time) return '-'
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

onMounted(() => {
  window.scrollTo(0, 0)
  fetchData()
})
</script>

<style scoped>
/* Base Layout */
.cookies-container {
  padding: 24px;
  background-color: #f8fafc;
  min-height: calc(100vh - 60px);
  font-family: 'Fira Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.username-text {
  font-family: 'Fira Code', monospace;
  font-weight: 500;
  color: #1e293b;
}

/* Page Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.header-title {
  margin: 0 0 4px 0;
  font-size: 24px;
  font-weight: 700;
  color: #1e293b;
}

.header-subtitle {
  margin: 0;
  font-size: 14px;
  color: #64748b;
}

/* Bento Grid Stats */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.stats-card-wrapper {
  background: white;
  border-radius: 14px;
  padding: 20px;
  border: 1px solid #e2e8f0;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  min-height: 100px;
  display: flex;
  align-items: center;
}

.stats-card-wrapper:hover {
  border-color: #3b82f6;
  box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.1), 0 8px 10px -6px rgba(59, 130, 246, 0.1);
  transform: translateY(-2px);
}

.stats-card-wrapper.clickable {
  cursor: pointer;
}

.stats-card-inner {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.card-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex-shrink: 0;
}

.card-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.total .card-icon { background: #eff6ff; color: #3b82f6; }
.active .card-icon { background: #f0fdf4; color: #22c55e; }
.inactive .card-icon { background: #fef2f2; color: #ef4444; }
.config .card-icon { background: #faf5ff; color: #a855f7; }

.card-label {
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.status-tag {
  border-radius: 4px;
  font-weight: 500;
}

.config-disabled-msg {
  font-size: 13px;
  color: #94a3b8;
  margin-top: 4px;
  font-style: italic;
}

.card-value {
  font-size: 26px;
  font-weight: 800;
  color: #1e293b;
  line-height: 1;
  white-space: nowrap;
}

.config-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
}

.detail-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.detail-item {
  font-size: 13px;
  color: #64748b;
  white-space: nowrap;
}

.edit-hint-icon {
  font-size: 14px;
  color: #3b82f6;
  opacity: 0;
  transition: opacity 0.2s;
}

.stats-card-wrapper:hover .edit-hint-icon {
  opacity: 1;
}

/* Custom Card & Table */
.custom-card {
  border-radius: 12px;
  border: 1px solid #e2e8f0 !important;
  margin-bottom: 24px;
}

/* Filter Card */
.filter-card {
  margin-bottom: 24px;
}

.filter-header {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f1f5f9;
}

.filter-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #475569;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.filter-form :deep(.el-form-item) {
  margin-right: 0;
  margin-bottom: 0;
}

.filter-form :deep(.el-form-item__label) {
  font-weight: 500;
  color: #64748b;
  padding-right: 12px;
}

/* Custom Select */
.custom-select {
  width: 160px;
}

.custom-select :deep(.el-input__wrapper) {
  border-radius: 8px;
  background-color: #f8fafc;
  box-shadow: 0 0 0 1px #e2e8f0 inset;
  transition: all 0.2s ease;
  padding: 4px 12px;
}

.custom-select :deep(.el-input__wrapper):hover {
  box-shadow: 0 0 0 1px #3b82f6 inset;
}

.custom-select :deep(.el-input__wrapper).is-focus {
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2), 0 0 0 1px #3b82f6 inset !important;
  background-color: #fff;
}

/* Custom Buttons */
.custom-btn {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
  border: none !important;
  color: white !important;
  font-weight: 600;
  height: 40px;
  padding: 0 20px;
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.custom-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.3);
  opacity: 0.9;
}

.custom-btn:active {
  transform: translateY(0);
}

.custom-btn-outline {
  background: white !important;
  border: 1px solid #e2e8f0 !important;
  color: #475569 !important;
  font-weight: 600;
  height: 40px;
  padding: 0 20px;
  border-radius: 10px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.custom-btn-outline:hover {
  border-color: #3b82f6 !important;
  color: #3b82f6 !important;
  background-color: #f0f7ff !important;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.custom-btn :deep(.el-icon),
.custom-btn-outline :deep(.el-icon) {
  margin-right: 6px;
  font-size: 16px;
}

.custom-table {
  border-radius: 8px;
  overflow: hidden;
}

.cookie-info-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.domain-tag {
  border-radius: 4px;
  font-weight: 700;
  padding: 0 6px;
}

.status-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.active { background-color: #22c55e; box-shadow: 0 0 8px rgba(34, 197, 94, 0.4); }
.status-dot.inactive { background-color: #ef4444; }

.status-text {
  font-size: 13px;
  font-weight: 600;
}

.status-text.active { color: #166534; }
.status-text.inactive { color: #991b1b; }

.time-text {
  font-size: 13px;
  color: #64748b;
}

.action-link {
  font-weight: 600;
  font-size: 13px;
}

.input-tip {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
  line-height: 1.4;
}

/* Dialog Styling */
:deep(.el-dialog) {
  border-radius: 16px;
  overflow: hidden;
}

:deep(.el-dialog__header) {
  margin-right: 0;
  padding: 20px 24px;
  background-color: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

:deep(.el-dialog__title) {
  font-weight: 700;
  color: #1e293b;
}

:deep(.el-dialog__body) {
  padding: 24px;
}

:deep(.el-dialog__footer) {
  padding: 16px 24px;
  border-top: 1px solid #e2e8f0;
}

/* Responsive */
@media (max-width: 1400px) {
  .stats-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .page-header {
    flex-direction: column;
    gap: 16px;
  }
}
</style>
