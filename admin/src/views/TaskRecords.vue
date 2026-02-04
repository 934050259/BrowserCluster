<template>
  <div class="task-records-container">
    <el-card class="records-card" :body-style="{ padding: '0' }">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-button @click="goBack" circle :icon="ArrowLeft" class="back-btn" />
            <div class="header-info">
              <span class="title">采集记录</span>
              <span class="subtitle" v-if="scheduleName">{{ scheduleName }}</span>
            </div>
          </div>
          <div class="header-actions">
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
          
          <el-form-item label="任务 ID">
            <el-input 
              v-model="filterForm.url" 
              placeholder="搜索任务 ID..." 
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
        class="records-table" 
        border 
        stripe
      >
        <el-table-column prop="task_id" label="任务 ID" width="250">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ row.task_id }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="url" label="目标 URL" min-width="250">
          <template #default="{ row }">
            <el-link :href="row.url" target="_blank" type="primary" :underline="false">
              <el-icon><Link /></el-icon> {{ row.url }}
            </el-link>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusColor(row.status)">{{ formatStatus(row.status) }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="耗时" width="120" align="center">
          <template #default="{ row }">
            <div class="duration-tags" v-if="row.duration || row.result?.metadata?.load_time">
              <el-tooltip content="总耗时" placement="top">
                <el-tag size="small" effect="dark" v-if="row.duration">
                  {{ row.duration.toFixed(1) }}s
                </el-tag>
              </el-tooltip>
              <el-tooltip content="页面加载" placement="top" v-if="row.result?.metadata?.load_time">
                <el-tag size="small" effect="plain" type="warning">
                  {{ row.result.metadata.load_time.toFixed(1) }}s
                </el-tag>
              </el-tooltip>
            </div>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column label="创建时间" width="180" align="center">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="120" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link :icon="View" @click="viewTaskDetail(row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @size-change="loadTasks"
          @current-change="loadTasks"
        />
      </div>
    </el-card>

    <!-- 任务详情对话框 -->
    <el-dialog 
      v-model="showDetailDialog" 
      title="采集记录详情" 
      width="1000px" 
      top="5vh"
      destroy-on-close
    >
      <div v-if="currentTask" class="task-details">
        <el-tabs v-model="activeTab">

          <el-tab-pane label="基础信息" name="info">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="任务 ID">{{ currentTask.task_id }}</el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag :type="getStatusColor(currentTask.status)">{{ formatStatus(currentTask.status) }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="目标 URL" :span="2">
                <el-link :href="currentTask.url" target="_blank">{{ currentTask.url }}</el-link>
              </el-descriptions-item>
              <el-descriptions-item label="创建时间">{{ formatDate(currentTask.created_at) }}</el-descriptions-item>
              <el-descriptions-item label="完成时间">{{ formatDate(currentTask.completed_at) || '-' }}</el-descriptions-item>
              <el-descriptions-item label="加载耗时" v-if="currentTask.result?.metadata?.load_time">
                {{ currentTask.result.metadata.load_time.toFixed(2) }}s
              </el-descriptions-item>
              <el-descriptions-item label="缓存状态">
                <el-tag :type="currentTask.cached ? 'success' : 'info'">{{ currentTask.cached ? '缓存命中' : '实时抓取' }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="节点 ID">{{ currentTask.node_id || '-' }}</el-descriptions-item>
            </el-descriptions>
          </el-tab-pane>

          <el-tab-pane label="采集数据" name="data">
            <div class="detail-section">
              <div class="section-header">
                <span class="section-title">解析结果</span>
                <el-button size="small" :icon="CopyDocument" @click="copyJson(currentTask.result?.parsed_data)">复制 JSON</el-button>
              </div>
              <div class="json-content">
                <pre v-if="currentTask.result?.parsed_data"><code>{{ JSON.stringify(currentTask.result.parsed_data, null, 2) }}</code></pre>
                <el-empty v-else description="暂无解析数据" />
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="网页截图" name="screenshot" v-if="currentTask.result?.screenshot || currentTask.params?.screenshot">
            <div class="screenshot-container" v-loading="loadingScreenshot">
              <el-image 
                v-if="currentTask.result?.screenshot"
                :src="`data:image/png;base64,${currentTask.result.screenshot}`" 
                :preview-src-list="[`data:image/png;base64,${currentTask.result.screenshot}`]"
                fit="contain"
              >
                <template #error>
                  <div class="image-error">截图加载失败</div>
                </template>
              </el-image>
              <el-empty v-else description="正在加载截图..." />
            </div>
          </el-tab-pane>

          <el-tab-pane label="HTML 源码" name="html" v-if="currentTask.result?.html || currentTask.status === 'success'">
            <div class="detail-section">
              <div class="section-header">
                <span class="section-title">原始 HTML</span>
                <el-button size="small" :icon="CopyDocument" @click="copyText(currentTask.result?.html)" :disabled="!currentTask.result?.html">复制 HTML</el-button>
              </div>
              <div class="code-content" v-loading="loadingHtml">
                <pre v-if="currentTask.result?.html"><code>{{ currentTask.result.html }}</code></pre>
                <el-empty v-else description="正在加载 HTML..." />
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="错误日志" name="error" v-if="currentTask.status === 'failed'">
            <div class="error-container">
              <el-alert
                v-if="currentTask.error"
                :title="currentTask.error.message"
                type="error"
                :description="currentTask.error.stack"
                show-icon
                :closable="false"
              />
              <el-empty v-else description="暂无错误详情" />
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Refresh, Search, Link, View, CopyDocument } from '@element-plus/icons-vue'
import { getTasks, getTask, getSchedule } from '../api'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()
const scheduleId = route.query.schedule_id
const scheduleName = ref('')

const loading = ref(false)
const loadingHtml = ref(false)
const loadingScreenshot = ref(false)
const tasks = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)

const filterForm = ref({
  status: '',
  url: ''
})

const showDetailDialog = ref(false)
const currentTask = ref(null)
const activeTab = ref('data')

// 监听标签页切换，按需加载大数据字段
watch(activeTab, async (newTab) => {
  if (!currentTask.value) return
  
  const taskId = currentTask.value.task_id
  if (newTab === 'html' && !currentTask.value.result?.html) {
    loadingHtml.value = true
    try {
      const data = await getTask(taskId, { include_html: true, include_screenshot: false })
      if (data.result?.html) {
        if (!currentTask.value.result) currentTask.value.result = {}
        currentTask.value.result.html = data.result.html
      }
    } catch (e) {
      ElMessage.error('加载 HTML 失败')
    } finally {
      loadingHtml.value = false
    }
  } else if (newTab === 'screenshot' && !currentTask.value.result?.screenshot) {
    loadingScreenshot.value = true
    try {
      const data = await getTask(taskId, { include_html: false, include_screenshot: true })
      if (data.result?.screenshot) {
        if (!currentTask.value.result) currentTask.value.result = {}
        currentTask.value.result.screenshot = data.result.screenshot
      }
    } catch (e) {
      ElMessage.error('加载截图失败')
    } finally {
      loadingScreenshot.value = false
    }
  }
})

const loadTasks = async () => {
  if (!scheduleId) {
    ElMessage.warning('缺少定时任务 ID')
    return
  }
  
  loading.value = true
  try {
    const params = {
      schedule_id: scheduleId,
      status: filterForm.value.status || undefined,
      url: filterForm.value.url || undefined,
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value
    }
    const data = await getTasks(params)
    tasks.value = data.tasks
    total.value = data.total
  } catch (error) {
    ElMessage.error('加载记录失败')
  } finally {
    loading.value = false
  }
}

const loadScheduleInfo = async () => {
  if (!scheduleId) return
  try {
    const data = await getSchedule(scheduleId)
    scheduleName.value = data.name
  } catch (e) {
    console.error('Fetch schedule info failed:', e)
  }
}

const handleFilter = () => {
  currentPage.value = 1
  loadTasks()
}

const resetFilter = () => {
  filterForm.value = { status: '', url: '' }
  handleFilter()
}

const goBack = () => {
  router.push('/schedules')
}

const viewTaskDetail = async (row) => {
  try {
    // 默认不加载 HTML 和截图，只有切换到对应标签页时才加载
    const data = await getTask(row.task_id, { include_html: false, include_screenshot: false })
    currentTask.value = data
    showDetailDialog.value = true
    activeTab.value = data.result?.parsed_data ? 'data' : 'info'
  } catch (error) {
    ElMessage.error('获取详情失败')
  }
}

const getStatusColor = (status) => {
  const colors = {
    pending: 'info',
    processing: 'primary',
    success: 'success',
    failed: 'danger'
  }
  return colors[status] || 'info'
}

const formatStatus = (status) => {
  const labels = {
    pending: '等待中',
    processing: '处理中',
    success: '成功',
    failed: '失败'
  }
  return labels[status] || status
}

const formatDate = (date) => {
  if (!date) return '-'
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

const copyJson = (data) => {
  if (!data) return
  const text = JSON.stringify(data, null, 2)
  copyText(text)
}

const copyText = (text) => {
  if (!text) return
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制到剪贴板')
  })
}

onMounted(() => {
  loadTasks()
  loadScheduleInfo()
})
</script>

<style scoped>
.task-records-container {
  padding: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-info {
  display: flex;
  flex-direction: column;
}

.title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.subtitle {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.filter-bar {
  padding: 16px 24px;
  background-color: #f8f9fb;
  border-bottom: 1px solid #ebeef5;
}

.pagination-container {
  padding: 16px 24px;
  display: flex;
  justify-content: flex-end;
}

.detail-section {
  padding: 16px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-title {
  font-weight: 600;
  color: #303133;
}

.json-content,
.code-content {
  background-color: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 4px;
  max-height: 500px;
  overflow-y: auto;
}

.json-content pre,
.code-content pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Fira Code', 'Courier New', Courier, monospace;
}

.screenshot-container {
  display: flex;
  justify-content: center;
  padding: 20px;
  background-color: #f5f7fa;
}

.image-error {
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
}

.error-container {
  padding: 20px;
}

.duration-tags {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
</style>
