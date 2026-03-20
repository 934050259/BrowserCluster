<template>
  <div class="workflows-container">
    <div class="page-header">
      <div class="header-left">
        <h2>流程编排</h2>
        <p class="subtitle">通过拖拽组件构建跨页面的自动化操作流程</p>
      </div>
    </div>

    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <el-input
            v-model="searchQuery"
            placeholder="搜索流程名称"
            clearable
            class="search-input"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            <span>新建流程</span>
          </el-button>
          <el-button 
            type="danger" 
            plain 
            :disabled="!selectedIds.length" 
            @click="handleBatchDelete"
            v-if="selectedIds.length"
          >
            <el-icon><Delete /></el-icon>
            <span>批量删除 ({{ selectedIds.length }})</span>
          </el-button>
        </div>
        <div class="toolbar-right">
          <el-button @click="fetchData">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
      </div>

      <el-table 
        :data="pagedWorkflows" 
        v-loading="loading" 
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="name" label="流程名称" min-width="200" />
        <el-table-column prop="description" label="描述" min-width="250" show-overflow-tooltip />
        <el-table-column label="节点数" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.nodes?.length || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.is_active" @change="(val) => handleStatusChange(row, val)" />
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="最后修改" width="180">
          <template #default="{ row }">
            {{ formatTime(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="400" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button 
                type="success" 
                size="small" 
                icon="VideoPlay" 
                :loading="executingStates[row._id]"
                @click="handleExecute(row, 'test')"
              >
                {{ executingStates[row._id] ? (executingProgress[row._id] || '执行中...') : '测试' }}
              </el-button>
              <el-button type="warning" size="small" icon="List" @click="handleViewResults(row)">数据详情</el-button>
              <el-button type="info" size="small" icon="Document" @click="handleViewLogs(row)">日志</el-button>
              <el-button type="primary" size="small" icon="Edit" @click="handleEdit(row)">编辑</el-button>
              <el-button type="danger" size="small" icon="Delete" @click="handleDelete(row)">删除</el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          :total="filteredWorkflows.length"
        />
      </div>
    </el-card>

    <!-- Logs Dialog -->
    <el-dialog v-model="logsVisible" :title="`执行日志 - ${currentWorkflow?.name}`" width="900px">
      <div class="dialog-toolbar" style="margin-bottom: 15px;">
        <el-radio-group v-model="logMode" size="small" @change="() => fetchLogs(currentWorkflow._id, logMode)">
          <el-radio-button label="prod">正式日志</el-radio-button>
          <el-radio-button label="test">测试日志</el-radio-button>
        </el-radio-group>
      </div>
      <el-table :data="workflowLogs" stripe height="500px" v-loading="logsLoading">
        <el-table-column prop="timestamp" label="时间" width="180" />
        <el-table-column prop="level" label="级别" width="90">
          <template #default="{ row }">
            <el-tag :type="row.level === 'ERROR' ? 'danger' : 'info'" size="small">{{ row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="消息" />
        <el-table-column label="详情" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.data" size="small" type="success">有数据</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="logsVisible = false">关闭</el-button>
        <el-button type="primary" @click="fetchLogs(currentWorkflow?._id, logMode)">刷新</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, reactive, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Refresh, VideoPlay, Document, Edit, Delete } from '@element-plus/icons-vue'
import { getWorkflows, deleteWorkflow, updateWorkflow, executeWorkflow, getWorkflowLogs, getExecutionStatus, getActiveExecutions, batchDeleteWorkflows } from '@/api'

const router = useRouter()
const workflows = ref([])
const loading = ref(false)
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const selectedIds = ref([])
const executingStates = reactive({})
const executingProgress = reactive({})
const activePolls = {}

const handleSelectionChange = (selection) => {
  selectedIds.value = selection.map(item => item._id)
}

const startPolling = (workflowId, executionId) => {
  if (activePolls[workflowId]) clearInterval(activePolls[workflowId])
  
  executingStates[workflowId] = true
  
  activePolls[workflowId] = setInterval(async () => {
    try {
      const statusRes = await getExecutionStatus(executionId)
      if (statusRes.status === 'completed' || statusRes.status === 'failed') {
        clearInterval(activePolls[workflowId])
        delete activePolls[workflowId]
        executingStates[workflowId] = false
        delete executingProgress[workflowId]
        if (statusRes.status === 'completed') {
          ElMessage.success('流程执行完成')
        } else {
          ElMessage.error('流程执行失败')
        }
      } else {
        executingProgress[workflowId] = `${statusRes.completed_nodes}/${statusRes.total_nodes}`
      }
    } catch (err) {
      clearInterval(activePolls[workflowId])
      delete activePolls[workflowId]
      executingStates[workflowId] = false
      delete executingProgress[workflowId]
    }
  }, 1000)
}

const logsVisible = ref(false)
const logsLoading = ref(false)
const workflowLogs = ref([])
const currentWorkflow = ref(null)
const logMode = ref('test')

const handleViewLogs = (row) => {
  currentWorkflow.value = row
  logsVisible.value = true
  logMode.value = 'test'
  fetchLogs(row._id, 'test')
}

const handleViewResults = (row) => {
  router.push({ name: 'WorkflowResults', params: { id: row._id } })
}

const fetchLogs = async (id, mode) => {
  logsLoading.value = true
  try {
    const res = await getWorkflowLogs(id, mode)
    workflowLogs.value = res.logs.map(log => ({
      ...log,
      timestamp: new Date(log.timestamp).toLocaleString()
    }))
  } catch (error) {
    ElMessage.error('获取日志失败')
  } finally {
    logsLoading.value = false
  }
}

const getImageUrl = (url) => {
  if (!url) return ''
  // 如果已经是 base64 数据，直接返回
  if (url.startsWith('data:')) return url
  const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
  return `${apiBase}${url}`
}

const filteredWorkflows = computed(() => {
  if (!searchQuery.value) return workflows.value
  return workflows.value.filter(w => w.name.toLowerCase().includes(searchQuery.value.toLowerCase()))
})

const pagedWorkflows = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredWorkflows.value.slice(start, start + pageSize.value)
})

const fetchData = async () => {
  console.log('Workflows fetchData called')
  loading.value = true
  try {
    const res = await getWorkflows()
    console.log('Workflows response:', res)
    workflows.value = res || []
    
    // 获取活跃任务并开始轮询
    const activeEx = await getActiveExecutions()
    activeEx.forEach(ex => {
      startPolling(ex.workflow_id, ex._id)
    })
  } catch (error) {
    console.error('Fetch workflows failed:', error)
    ElMessage.error('获取流程列表失败')
  } finally {
    loading.value = false
    console.log('Workflows loading set to false')
  }
}

const handleAdd = () => {
  router.push({ name: 'WorkflowEditor' })
}

const handleEdit = (row) => {
  router.push({ name: 'WorkflowEditor', params: { id: row._id } })
}

const handleStatusChange = async (row, val) => {
  try {
    await updateWorkflow(row._id, { is_active: val })
    ElMessage.success(`流程已${val ? '启用' : '禁用'}`)
  } catch (error) {
    row.is_active = !val
    ElMessage.error('更新状态失败')
  }
}

const handleDelete = (row) => {
  ElMessageBox.confirm('确定要删除该流程吗？', '提示', { type: 'warning' }).then(async () => {
    try {
      await deleteWorkflow(row._id)
      ElMessage.success('删除成功')
      fetchData()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

const handleBatchDelete = () => {
  if (!selectedIds.value.length) return
  
  ElMessageBox.confirm(`确定要删除选中的 ${selectedIds.value.length} 个流程吗？`, '批量删除提示', {
    type: 'warning',
    confirmButtonText: '确定',
    cancelButtonText: '取消'
  }).then(async () => {
    try {
      await batchDeleteWorkflows(selectedIds.value)
      ElMessage.success('批量删除成功')
      selectedIds.value = []
      fetchData()
    } catch (error) {
      ElMessage.error('批量删除失败')
    }
  }).catch(() => {})
}

const handleExecute = async (row, mode = 'prod') => {
  if (executingStates[row._id]) return
  
  executingStates[row._id] = true
  executingProgress[row._id] = '准备中'
  
  try {
    const res = await executeWorkflow(row._id, mode)
    startPolling(row._id, res.execution_id)
  } catch (error) {
    const errorMsg = error.response?.data?.detail || '执行失败'
    ElMessage.error(errorMsg)
    executingStates[row._id] = false
    delete executingProgress[row._id]
  }
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString()
}

onMounted(fetchData)

onUnmounted(() => {
  Object.values(activePolls).forEach(clearInterval)
})
</script>

<style scoped>
.workflows-container {
  padding: 0;
}
.page-header {
  margin-bottom: 20px;
}
.subtitle {
  color: #909399;
  font-size: 14px;
  margin-top: 4px;
}
.table-toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
}
.toolbar-left {
  display: flex;
  gap: 12px;
}
.search-input {
  width: 250px;
}
.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

/* Log Details Styles */
.log-details {
  padding: 15px;
  background: #f8fafc;
  border-radius: 4px;
}
.detail-label {
  font-weight: bold;
  margin-bottom: 8px;
  color: #606266;
  font-size: 13px;
}
.log-image {
  max-width: 100%;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1);
}
.variables-preview {
  margin-top: 15px;
}
.json-code {
  background: #272822;
  color: #f8f8f2;
  padding: 12px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  overflow-x: auto;
  margin: 0;
}
.no-details {
  text-align: center;
  color: #909399;
  padding: 10px;
}
.image-slot {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 200px;
  background: #f5f7fa;
  color: #909399;
}
</style>
