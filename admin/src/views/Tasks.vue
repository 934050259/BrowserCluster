<template>
  <div class="tasks-container">
    <el-card class="tasks-card" :body-style="{ padding: '0' }">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="title">任务管理</span>
            <span class="subtitle">实时监控和管理自动化抓取任务</span>
          </div>
          <div class="header-actions">
            <el-button 
              type="danger" 
              plain 
              :disabled="selectedTasks.length === 0"
              @click="confirmBatchDelete"
            >
              <el-icon><DeleteFilled /></el-icon> 批量删除 ({{ selectedTasks.length }})
            </el-button>
            <el-button type="primary" @click="showScrapeDialog = true">
              <el-icon><Plus /></el-icon> 新建任务
            </el-button>
            <el-button @click="loadTasks" :loading="loading">
              <el-icon><Refresh /></el-icon> 刷新
            </el-button>
          </div>
        </div>
      </template>

      <div class="filter-bar">
        <el-form :inline="true" :model="filterForm" class="filter-form">
          <el-form-item label="任务状态">
            <el-radio-group v-model="filterForm.status" @change="handleFilter" size="default">
              <el-radio-button label="">全部</el-radio-button>
              <el-radio-button label="pending">等待中</el-radio-button>
              <el-radio-button label="processing">处理中</el-radio-button>
              <el-radio-button label="success">成功</el-radio-button>
              <el-radio-button label="failed">失败</el-radio-button>
            </el-radio-group>
          </el-form-item>
          
          <el-form-item label="关键词搜索">
            <el-input 
              v-model="filterForm.url" 
              placeholder="搜索 URL 或 任务 ID..." 
              clearable 
              style="width: 280px"
              @keyup.enter="handleFilter"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-form-item>
          
          <el-form-item>
            <el-button type="primary" @click="handleFilter">查询</el-button>
            <el-button @click="resetFilter">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-table 
        :data="tasks" 
        v-loading="loading" 
        style="width: 100%" 
        class="tasks-table" 
        border 
        stripe
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="40" align="center" />
        <el-table-column prop="task_id" label="任务 ID" width="250">
          <template #default="{ row }">
            <div class="task-id-row">
              <el-tag size="small"  effect="plain" class="id-tag-simple">
                {{ row.task_id }}
              </el-tag>
              <el-button link type="primary" :icon="CopyDocument" @click="copyToClipboard(row.task_id)" class="copy-btn-mini" />
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="url" label="目标 URL" min-width="250">
          <template #default="{ row }">
            <div class="task-url-row">
              <el-tooltip :content="row.url" placement="top" :show-after="500">
                <el-link :href="row.url" target="_blank" class="url-link-bold" :underline="false">
                  <el-icon><Link /></el-icon>
                  <span>{{ row.url }}</span>
                </el-link>
              </el-tooltip>
              <!-- 显示重定向后的实际 URL -->
              <div v-if="row.result?.metadata?.actual_url && row.result.metadata.actual_url !== row.url" class="actual-url-info">
                <el-tooltip :content="'实际访问: ' + row.result.metadata.actual_url" placement="bottom">
                  <span class="actual-url-text">
                    <el-icon><Right /></el-icon>
                    {{ row.result.metadata.actual_url }}
                  </span>
                </el-tooltip>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="140" align="center">
          <template #default="{ row }">
            <div class="status-container">
              <el-tag :type="getStatusType(row.status)" size="default" effect="dark" class="status-tag">
                <div class="status-content">
                  <span class="status-dot-mini" :class="row.status"></span>
                  {{ getStatusText(row.status) }}
                </div>
              </el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="执行统计" width="220">
          <template #default="{ row }">
            <div class="stats-group">
              <div class="stat-item timing-row">
                <el-icon><Timer /></el-icon>
                <span class="label">耗时:</span>
                <div class="timing-tags">
                  <el-tooltip content="总执行耗时" placement="top">
                    <el-tag size="small" effect="dark" class="time-tag total">
                      {{ row.duration ? row.duration.toFixed(1) + 's' : '-' }}
                    </el-tag>
                  </el-tooltip>
                  <el-tooltip v-if="row.result?.metadata?.load_time" content="页面加载耗时" placement="top">
                    <el-tag size="small" effect="plain" type="warning" class="time-tag load">
                      <el-icon class="mini-icon"><Loading /></el-icon>
                      {{ row.result.metadata.load_time.toFixed(1) }}s
                    </el-tag>
                  </el-tooltip>
                </div>
              </div>
              <div class="stat-item">
                <el-icon><Cpu /></el-icon>
                <span class="label">缓存:</span>
                <el-tag :type="row.cached ? 'success' : 'info'" size="small" effect="light" class="cache-tag">
                  {{ row.cached ? '命中' : '跳过' }}
                </el-tag>
              </div>
              <div class="stat-item">
                <el-icon><Monitor /></el-icon>
                <span class="label">节点:</span>
                <el-tag v-if="row.node_id" :type="getNodeColor(row.node_id)" size="small" effect="light" class="node-tag">
                  {{ row.node_id }}
                </el-tag>
                <span v-else class="empty-text">-</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="时间轨迹" width="180">
          <template #default="{ row }">
            <div class="timeline-mini">
              <div class="time-row">
                <span class="dot create"></span>
                <span class="label">创建:</span>
                <span class="time">{{ formatTimeOnly(row.created_at) }}</span>
              </div>
              <div class="time-row" v-if="row.completed_at">
                <span class="dot complete"></span>
                <span class="label">完成:</span>
                <span class="time">{{ formatTimeOnly(row.completed_at) }}</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="160" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip content="查看详情" placement="top">
                <el-button circle size="small" :icon="View" @click="viewTask(row)" />
              </el-tooltip>
              
              <el-tooltip content="重试任务" placement="top">
                <el-button 
                  circle 
                  size="small" 
                  type="warning" 
                  :icon="VideoPlay" 
                  @click="confirmRetry(row)"
                  :disabled="row.status === 'pending' || row.status === 'processing'"
                />
              </el-tooltip>

              <el-tooltip content="删除任务" placement="top">
                <el-button 
                  circle 
                  size="small" 
                  type="danger" 
                  :icon="DeleteFilled" 
                  @click="confirmDelete(row.task_id)"
                />
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadTasks"
          @current-change="loadTasks"
        />
      </div>
    </el-card>

    <!-- 新建任务对话框 -->
    <el-dialog 
      v-model="showScrapeDialog" 
      title="新建抓取任务" 
      width="900px" 
      destroy-on-close 
      top="5vh"
      class="bento-dialog"
    >
      <el-form :model="scrapeForm" label-width="100px" label-position="top">
        <div class="bento-grid">
          <!-- 1. 目标与基础 (占据较大空间) -->
          <el-card shadow="hover" class="bento-item target-card">
            <template #header>
              <div class="bento-header">
                <div class="header-icon-box target">
                  <el-icon><Link /></el-icon>
                </div>
                <div class="header-text">
                  <span class="main-title">目标配置</span>
                  <span class="sub-title">设置抓取地址与优先级</span>
                </div>
              </div>
            </template>
            <el-form-item label="目标 URL" required>
              <el-input v-model="scrapeForm.url" placeholder="https://example.com" clearable>
                <template #prefix><el-icon><Connection /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-row :gutter="15">
              <el-col :span="14">
                <el-form-item label="任务优先级">
                  <el-select v-model="scrapeForm.priority" style="width: 100%">
                    <el-option label="最高 (10)" :value="10" />
                    <el-option label="普通 (5)" :value="5" />
                    <el-option label="最低 (1)" :value="1" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="10">
                <el-form-item label="数据缓存">
                  <div class="compact-switch">
                    <el-switch v-model="scrapeForm.cache.enabled" />
                    <span class="status-text">{{ scrapeForm.cache.enabled ? '开启' : '关闭' }}</span>
                  </div>
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="缓存时长 (TTL)" v-if="scrapeForm.cache.enabled">
              <el-input-number v-model="scrapeForm.cache.ttl" :min="60" :step="60" style="width: 100%" />
            </el-form-item>
          </el-card>

          <!-- 2. 加载与性能 -->
          <el-card shadow="hover" class="bento-item performance-card">
            <template #header>
              <div class="bento-header">
                <div class="header-icon-box performance">
                  <el-icon><Timer /></el-icon>
                </div>
                <div class="header-text">
                  <span class="main-title">加载策略</span>
                  <span class="sub-title">控制等待与超时</span>
                </div>
              </div>
            </template>
            <el-form-item>
              <template #label>
                <div class="label-with-tip">
                  <span>等待条件</span>
                  <el-tooltip content="控制浏览器在何时认为页面已加载完成" placement="top">
                    <el-icon class="help-icon"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </div>
              </template>
              <el-select v-model="scrapeForm.params.wait_for" style="width: 100%" :teleported="false">
                <el-option label="Network Idle" value="networkidle">
                  <div class="option-item">
                    <span class="option-label">Network Idle</span>
                    <span class="option-desc">等待网络连接停止，适用于单页应用</span>
                  </div>
                </el-option>
                <el-option label="Page Load" value="load">
                  <div class="option-item">
                    <span class="option-label">Page Load</span>
                    <span class="option-desc">等待整个页面及所有资源加载完成</span>
                  </div>
                </el-option>
                <el-option label="DOM Ready" value="domcontentloaded">
                  <div class="option-item">
                    <span class="option-label">DOM Ready</span>
                    <span class="option-desc">仅等待 HTML 文档解析完成</span>
                  </div>
                </el-option>
              </el-select>
            </el-form-item>
            <el-form-item label="超时时间 (ms)">
              <el-input-number v-model="scrapeForm.params.timeout" :min="5000" :step="5000" style="width: 100%" />
            </el-form-item>
            <el-form-item label="额外等待 (ms)">
              <el-input-number v-model="scrapeForm.params.wait_time" :min="0" :step="500" style="width: 100%" />
            </el-form-item>
          </el-card>

          <!-- 3. 浏览器特征 -->
          <el-card shadow="hover" class="bento-item browser-card">
            <template #header>
              <div class="bento-header">
                <div class="header-icon-box browser">
                  <el-icon><Monitor /></el-icon>
                </div>
                <div class="header-text">
                  <span class="main-title">环境模拟</span>
                  <span class="sub-title">伪装浏览器特征</span>
                </div>
              </div>
            </template>
            <el-form-item label="视口尺寸 (宽 × 高)">
              <div class="viewport-group">
                <el-input-number v-model="scrapeForm.params.viewport.width" :min="320" controls-position="right" />
                <span class="v-sep">×</span>
                <el-input-number v-model="scrapeForm.params.viewport.height" :min="240" controls-position="right" />
              </div>
            </el-form-item>
            <div class="feature-grid">
              <div class="feature-cell">
                <span class="label">反检测 (Stealth)</span>
                <el-switch v-model="scrapeForm.params.stealth" size="small" />
              </div>
              <div class="feature-cell">
                <span class="label">自动截图</span>
                <el-switch v-model="scrapeForm.params.screenshot" size="small" />
              </div>
              <div class="feature-cell" v-if="scrapeForm.params.screenshot">
                <span class="label">全屏截图</span>
                <el-switch v-model="scrapeForm.params.is_fullscreen" size="small" />
              </div>
              <div class="feature-cell">
                <span class="label">无图模式</span>
                <el-switch v-model="scrapeForm.params.block_images" size="small" />
              </div>
            </div>
          </el-card>

          <!-- 4. 代理与拦截 -->
          <el-card shadow="hover" class="bento-item proxy-card">
            <template #header>
              <div class="bento-header">
                <div class="header-icon-box proxy">
                  <el-icon><Lock /></el-icon>
                </div>
                <div class="header-text">
                  <span class="main-title">高级选项</span>
                  <span class="sub-title">代理与接口拦截</span>
                </div>
              </div>
            </template>
            <el-form-item label="代理服务器 (可选)">
              <el-input v-model="scrapeForm.params.proxy.server" placeholder="http://proxy.com:8080" clearable />
            </el-form-item>
            <el-row :gutter="12" v-if="scrapeForm.params.proxy.server">
              <el-col :span="12">
                <el-form-item label="用户名">
                  <el-input v-model="scrapeForm.params.proxy.username" placeholder="可选" clearable />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="密码">
                  <el-input v-model="scrapeForm.params.proxy.password" type="password" placeholder="可选" show-password clearable />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="接口拦截模式">
              <el-select
                v-model="scrapeForm.params.intercept_apis"
                multiple
                filterable
                allow-create
                collapse-tags
                placeholder="如: */api/v1/*"
                style="width: 100%"
              />
            </el-form-item>
            <div class="form-tip">输入模式并回车即可添加多条规则</div>
          </el-card>
        </div>
      </el-form>
      <template #footer>
        <div class="bento-footer">
          <el-button @click="showScrapeDialog = false" round>取消</el-button>
          <el-button type="primary" @click="submitTask" :loading="loading" class="bento-submit" round>
            <el-icon><Promotion /></el-icon>
            <span>立即投递任务</span>
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 任务详情对话框 -->
    <el-dialog v-model="showTaskDialog" title="任务详情" width="900px" top="5vh">
      <div v-if="currentTask" class="task-details">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="基本信息" name="info">
            <el-descriptions :column="2" border size="default" class="detail-descriptions">
              <el-descriptions-item label="任务 ID">{{ currentTask.task_id }}</el-descriptions-item>
              <el-descriptions-item label="当前状态">
                <el-tag :type="getStatusType(currentTask.status)" size="default">{{ getStatusText(currentTask.status) }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="目标 URL" :span="2">
                <el-link :href="currentTask.url" target="_blank" type="primary" class="detail-url-link">{{ currentTask.url }}</el-link>
              </el-descriptions-item>
              <el-descriptions-item label="创建时间">{{ formatDate(currentTask.created_at) }}</el-descriptions-item>
              <el-descriptions-item label="完成时间">{{ formatDate(currentTask.completed_at) || '-' }}</el-descriptions-item>
              <el-descriptions-item label="缓存命中">
                <el-tag :type="currentTask.cached ? 'success' : 'info'" size="default">
                  {{ currentTask.cached ? '命中' : '未命中' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="节点 ID">{{ currentTask.node_id || '-' }}</el-descriptions-item>
            </el-descriptions>

            <div v-if="currentTask.result" class="metadata-section">
              <el-divider content-position="left">页面元数据</el-divider>
              <el-descriptions :column="2" border size="default" class="detail-descriptions">
                <el-descriptions-item label="页面标题" :span="2" width="120px">{{ currentTask.result.metadata?.title || '-' }}</el-descriptions-item>
                <el-descriptions-item label="实际 URL" :span="2" v-if="currentTask.result.metadata?.actual_url">
                  <el-link :href="currentTask.result.metadata.actual_url" target="_blank" type="success" class="detail-url-link">
                    {{ currentTask.result.metadata.actual_url }}
                  </el-link>
                </el-descriptions-item>
                <el-descriptions-item label="加载用时">
                  <el-tag type="warning" effect="plain" size="default">
                    {{ currentTask.result.metadata?.load_time?.toFixed(2) }}s
                  </el-tag>
                </el-descriptions-item>
              </el-descriptions>
            </div>

            <div v-if="currentTask.error" class="error-section">
              <el-divider content-position="left">错误详情</el-divider>
              <el-alert :title="currentTask.error.message" type="error" :closable="false" show-icon>
                <template #default>
                  <pre class="error-stack">{{ currentTask.error.stack }}</pre>
                </template>
              </el-alert>
            </div>
          </el-tab-pane>

          <el-tab-pane label="拦截数据" name="intercept" v-if="currentTask.result?.intercepted_apis">
            <div v-for="(requests, pattern) in currentTask.result.intercepted_apis" :key="pattern" class="intercept-group">
              <div class="pattern-header">
                <el-tag size="small">模式: {{ pattern }}</el-tag>
                <span class="count">共 {{ requests.length }} 条记录</span>
              </div>
              <el-collapse>
                <el-collapse-item v-for="(req, index) in requests" :key="index" :title="`${req.method} ${req.url.substring(0, 80)}...`">
                  <div class="req-detail">
                    <p><strong>完整 URL:</strong> {{ req.url }}</p>
                    <p><strong>状态码:</strong> <el-tag :type="req.status < 400 ? 'success' : 'danger'" size="small">{{ req.status }}</el-tag></p>
                    <div class="json-box">
                      <strong>响应内容:</strong>
                      <pre>{{ formatJSON(req.content) }}</pre>
                    </div>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </el-tab-pane>

          <el-tab-pane label="截图预览" name="screenshot" v-if="currentTask.result?.screenshot">
            <div class="screenshot-container">
              <el-image 
                :src="'data:image/png;base64,' + currentTask.result.screenshot" 
                :preview-src-list="['data:image/png;base64,' + currentTask.result.screenshot]"
                fit="contain"
              >
                <template #error>
                  <div class="image-slot">
                    <el-icon><picture /></el-icon>
                  </div>
                </template>
              </el-image>
            </div>
          </el-tab-pane>

          <el-tab-pane label="HTML 源码" name="html" v-if="currentTask.result?.html">
            <div class="html-container">
              <pre><code>{{ currentTask.result.html }}</code></pre>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Picture, WarningFilled, DeleteFilled, Setting, Connection, Monitor, Timer, Search, CopyDocument, View, VideoPlay, Link, Lock, Promotion, QuestionFilled, Cpu, Right } from '@element-plus/icons-vue'
import { getTasks, deleteTask as deleteTaskApi, getTask, scrapeAsync, retryTask, deleteTasksBatch } from '../api'
import dayjs from 'dayjs'

const loading = ref(false)
const tasks = ref([])
const selectedTasks = ref([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const activeTab = ref('info')

const filterForm = ref({
  status: '',
  url: ''
})

const handleFilter = () => {
  currentPage.value = 1
  loadTasks()
}

const handleSelectionChange = (val) => {
  selectedTasks.value = val
}

const confirmBatchDelete = () => {
  const taskIds = selectedTasks.value.map(task => task.task_id)
  ElMessageBox.confirm(
    `确定要删除选中的 ${taskIds.length} 个任务吗？此操作不可恢复。`,
    '批量删除确认',
    {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'error',
      icon: DeleteFilled,
      buttonSize: 'default'
    }
  ).then(async () => {
    try {
      loading.value = true
      await deleteTasksBatch(taskIds)
      ElMessage.success(`成功删除 ${taskIds.length} 个任务`)
      selectedTasks.value = []
      loadTasks()
    } catch (error) {
      ElMessage.error('批量删除失败: ' + (error.response?.data?.detail || error.message))
    } finally {
      loading.value = false
    }
  }).catch(() => {})
}

const resetFilter = () => {
  filterForm.value = {
    status: '',
    url: ''
  }
  handleFilter()
}

const showScrapeDialog = ref(false)
const showTaskDialog = ref(false)
const scrapeForm = ref({
  url: '',
  params: {
    wait_for: 'networkidle',
    wait_time: 3000,
    timeout: 30000,
    selector: '',
    screenshot: true,
    is_fullscreen: false,
    block_images: false,
    block_media: false,
    user_agent: '',
    viewport: {
      width: 1920,
      height: 1080
    },
    proxy: {
      server: '',
      username: '',
      password: ''
    },
    stealth: true,
    intercept_apis: [],
    intercept_continue: false
  },
  cache: {
    enabled: true,
    ttl: 3600
  },
  priority: 1
})

const currentTask = ref(null)

// 根据节点名称生成固定颜色
const getNodeColor = (nodeId) => {
  if (!nodeId) return 'info'
  const colors = ['success', 'warning', 'danger', 'primary', '']
  let hash = 0
  for (let i = 0; i < nodeId.length; i++) {
    hash = nodeId.charCodeAt(i) + ((hash << 5) - hash)
  }
  const index = Math.abs(hash) % colors.length
  return colors[index]
}

const loadTasks = async () => {
  loading.value = true
  try {
    const params = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value
    }
    if (filterForm.value.status) {
      params.status = filterForm.value.status
    }
    if (filterForm.value.url) {
      params.url = filterForm.value.url
    }
    
    const data = await getTasks(params)
    tasks.value = data.tasks
    total.value = data.total
  } catch (error) {
    ElMessage.error('获取任务列表失败')
  } finally {
    loading.value = false
  }
}

const confirmDelete = (taskId) => {
  ElMessageBox.confirm(
    '确定要删除该任务吗？此操作不可恢复。',
    '提示',
    {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'error',
      icon: DeleteFilled,
      buttonSize: 'default'
    }
  ).then(() => {
    deleteTask(taskId)
  }).catch(() => {})
}

const deleteTask = async (taskId) => {
  try {
    await deleteTaskApi(taskId)
    ElMessage.success('删除成功')
    loadTasks()
  } catch (error) {
    ElMessage.error('删除失败: ' + (error.response?.data?.detail || error.message))
  }
}

const confirmRetry = (row) => {
  ElMessageBox.confirm(
    `确定要重新执行任务吗？\nURL: ${row.url}`,
    '重试确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
      icon: WarningFilled,
      buttonSize: 'default'
    }
  ).then(() => {
    handleRetry(row.task_id)
  }).catch(() => {})
}

const handleRetry = async (taskId) => {
  try {
    loading.value = true
    await retryTask(taskId)
    ElMessage.success('已重新提交任务')
    loadTasks()
  } catch (error) {
    ElMessage.error('重试失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const viewTask = async (task) => {
  try {
    const data = await getTask(task.task_id)
    currentTask.value = data
    activeTab.value = 'info'
    showTaskDialog.value = true
  } catch (error) {
    ElMessage.error('获取任务详情失败')
  }
}

const submitTask = async () => {
  if (!scrapeForm.value.url) {
    ElMessage.warning('请输入目标 URL')
    return
  }

  loading.value = true
  try {
    // 深度克隆表单数据，避免修改原始数据
    const submitData = JSON.parse(JSON.stringify(scrapeForm.value))
    
    // 处理可选参数：如果为空则设置为 null，以匹配后端 Optional 类型
    if (!submitData.params.user_agent) {
      submitData.params.user_agent = null
    }
    if (!submitData.params.selector) {
      submitData.params.selector = null
    }
    
    // 代理配置处理
    if (!submitData.params.proxy || !submitData.params.proxy.server) {
      submitData.params.proxy = null
    } else {
      // 如果 server 存在但用户名/密码为空，也清理一下
      if (!submitData.params.proxy.username) delete submitData.params.proxy.username
      if (!submitData.params.proxy.password) delete submitData.params.proxy.password
    }
    
    // 拦截配置处理
    if (!submitData.params.intercept_apis || submitData.params.intercept_apis.length === 0) {
      submitData.params.intercept_apis = null
    }
    
    // 视口配置处理：如果宽高为 0 或无效，则设为 null 使用默认值
    if (!submitData.params.viewport || !submitData.params.viewport.width || !submitData.params.viewport.height) {
      submitData.params.viewport = null
    }
    
    await scrapeAsync(submitData)
    ElMessage.success('任务提交成功 (异步)')
    showScrapeDialog.value = false
    loadTasks()
    
    // 重置表单
    resetForm()
  } catch (error) {
    ElMessage.error('任务提交失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  scrapeForm.value = {
    url: '',
    params: {
      wait_for: 'networkidle',
      wait_time: 3000,
      timeout: 30000,
      selector: '',
      screenshot: true,
      block_images: false,
      block_media: false,
      user_agent: '',
      viewport: {
        width: 1280,
        height: 720
      },
      proxy: {
        server: '',
        username: '',
        password: ''
      },
      stealth: true,
      intercept_apis: [],
      intercept_continue: false
    },
    cache: {
      enabled: true,
      ttl: 3600
    },
    priority: 1
  }
}

const getStatusType = (status) => {
  const types = {
    pending: 'info',
    processing: 'warning',
    success: 'success',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const map = {
    'pending': '等待中',
    'processing': '抓取中',
    'success': '已成功',
    'failed': '已失败'
  }
  return map[status] || status
}

const formatDate = (date) => {
  if (!date) return ''
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

const formatTimeOnly = (date) => {
  if (!date) return ''
  return dayjs(date).format('HH:mm:ss')
}

const copyToClipboard = (text) => {
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

const formatJSON = (content) => {
  if (typeof content === 'string') {
    try {
      return JSON.stringify(JSON.parse(content), null, 2)
    } catch (e) {
      return content
    }
  }
  return JSON.stringify(content, null, 2)
}

onMounted(() => {
  loadTasks()
})
</script>

<style scoped>
/* 列表 UI 优化 */
.task-info-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.id-tag-simple {
  font-size: 14px;
  color: #64748b;
  background-color: #f1f5f9;
  border: none;
  padding: 0 5px;
}

.task-id-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.copy-btn-mini {
  padding: 0;
  height: auto;
  font-size: 12px;
}

.task-url-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.actual-url-info {
  margin-top: 2px;
}

.actual-url-text {
  font-size: 12px;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 4px;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.actual-url-text .el-icon {
  font-size: 14px;
  color: #3b82f6;
}

.url-link-bold {
  font-size: 14px;
  font-weight: 600;
  color: #328ee4;
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  transition: color 0.2s;
}

.url-link-bold:hover {
  color: #3b82f6;
}

.url-link-bold span {
  display: inline-block;
  max-width: 550px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}

.url-link-bold .el-icon {
  color: #3b82f6;
  font-size: 15px;
  padding: 0 2px;
}

.status-tag {
  border: none;
  min-width: 90px;
  border-radius: 20px;
}

.status-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.status-dot-mini {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #fff;
}

.status-dot-mini.processing {
  animation: blink 1.5s infinite;
}

.stats-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #475569;
}

.stat-item .el-icon {
  font-size: 15px;
  color: #64748b;
}

.stat-item .label {
  color: #94a3b8;
  font-size: 14px;
  min-width: 35px;
}

.timing-row {
  align-items: flex-start !important;
  padding-top: 2px;
}

.timing-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.time-tag {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  font-size: 12px !important;
  border: none;
  height: 26px;
  line-height: 26px;
}

.time-tag.total {
  background: linear-gradient(135deg, #73d494 0%, #47b66c 100%);
}

.time-tag.load {
  background-color: #fffbeb;
  border: 1px solid #fde68a;
  color: #b45309;
}

.cache-tag {
  font-size: 12px !important;
  height: 24px;
  line-height: 24px;
}

.mini-icon {
  font-size: 10px;
  margin-right: 2px;
}

.timeline-mini {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.time-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #64748b;
}

.time-row .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.time-row .dot.create { background-color: #3b82f6; }
.time-row .dot.complete { background-color: #22c55e; }

.time-row .label {
  color: #94a3b8;
  min-width: 30px;
}

.time-row .time {
  font-family: monospace;
}

/* 原有样式保持或替换 */
.tasks-container {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: calc(100vh - 60px);
}

.tasks-card {
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left .title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.header-left .subtitle {
  font-size: 13px;
  color: #909399;
  margin-left: 12px;
}

.filter-bar {
  padding: 20px;
  background-color: #fff;
  border-bottom: 1px solid #ebeef5;
}

/* Bento 风格新建任务对话框 */
.bento-dialog :deep(.el-dialog__body) {
  padding: 20px;
  background-color: #f8fafc;
}

.bento-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  grid-template-rows: auto auto;
  gap: 10px;
}

.bento-item {
  border: none;
  border-radius: 16px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.bento-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 24px -10px rgba(0, 0, 0, 0.1) !important;
}

.target-card {
  grid-column: span 1;
}

.bento-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon-box {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.header-icon-box.target { background-color: #eff6ff; color: #3b82f6; }
.header-icon-box.performance { background-color: #fef2f2; color: #ef4444; }
.header-icon-box.browser { background-color: #f0fdf4; color: #22c55e; }
.header-icon-box.proxy { background-color: #faf5ff; color: #a855f7; }

.header-text {
  display: flex;
  flex-direction: column;
}

.main-title {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}

.sub-title {
  font-size: 12px;
  color: #64748b;
}

.compact-switch {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 32px;
}

.status-text {
  font-size: 12px;
  color: #64748b;
}

.label-with-tip {
  display: flex;
  align-items: center;
  gap: 4px;
}

.help-icon {
  font-size: 14px;
  color: #94a3b8;
  cursor: help;
}

.viewport-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.viewport-group :deep(.el-input-number) {
  flex: 1;
}

.v-sep {
  color: #94a3b8;
  font-weight: bold;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-top: 10px;
}

.feature-cell {
  background-color: #f1f5f9;
  padding: 8px 12px;
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.feature-cell .label {
  font-size: 12px;
  color: #475569;
}

.bento-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 10px 0;
}

.bento-submit {
  padding-left: 24px;
  padding-right: 24px;
  font-weight: 600;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  border: none;
}

.bento-submit:hover {
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
}

/* 下拉选项样式 */
.option-item {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.option-label {
  font-weight: 600;
  color: #1e293b;
  font-size: 14px;
}

.option-desc {
  font-size: 12px;
  color: #64748b;
}

:deep(.el-select-dropdown__item) {
    height: auto !important;
    padding: 12px !important;
    line-height: 1.2 !important;
    white-space: normal !important;
  }
 
 :deep(.el-select-dropdown__item.selected) {
   background-color: #eff6ff;
 }
 
 :deep(.el-select-dropdown__wrap) {
   max-height: 400px !important;
 }

/* 详情页样式 */
.task-details {
  padding: 10px;
}

.detail-descriptions :deep(.el-descriptions__label) {
  font-size: 14px;
  font-weight: 600;
  color: #475569;
  background-color: #f8fafc !important;
}

.detail-descriptions :deep(.el-descriptions__content) {
  font-size: 14px;
  color: #1e293b;
}

.detail-url-link {
  font-size: 14px;
  word-break: break-all;
}

.metadata-section, .error-section {
  margin-top: 20px;
}

.error-stack {
  margin-top: 10px;
  padding: 12px;
  background: #fef0f0;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  color: #f56c6c;
}

.intercept-group {
  margin-bottom: 20px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}

.pattern-header {
  padding: 10px;
  background: #f5f7fa;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #ebeef5;
}

.count {
  font-size: 12px;
  color: #909399;
}

.node-tag {
  font-weight: bold;
  font-size: 12px;
}

.req-detail {
  padding: 10px;
}

.json-box {
  margin-top: 10px;
}

.json-box pre {
  margin-top: 5px;
  padding: 10px;
  background: #282c34;
  color: #abb2bf;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 12px;
  max-height: 300px;
}

.screenshot-container {
  display: flex;
  justify-content: center;
  background: #f5f7fa;
  padding: 20px;
  border-radius: 4px;
  min-height: 400px;
}

.html-container pre {
  padding: 15px;
  background: #000000;
  color: #d6d6d6;
  border-radius: 4px;
  font-family: monospace;
  font-size: 14px;
  overflow-x: auto;
  max-height: 500px;
}

.id-cell, .url-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.truncated-id {
  font-family: monospace;
  font-size: 12px;
}

.url-text {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 8px;
  display: inline-block;
}

.status-dot.pending { background-color: #909399; }
.status-dot.processing { background-color: #409eff; animation: blink 1.5s infinite; }
.status-dot.success { background-color: #67c23a; }
.status-dot.failed { background-color: #f56c6c; }

@keyframes blink {
  0% { opacity: 1; }
  50% { opacity: 0.4; }
  100% { opacity: 1; }
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 8px;
}

.pagination-container {
  padding: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
