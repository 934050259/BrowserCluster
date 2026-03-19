<template>
  <div class="workflow-results-container">
    <div class="page-header">
      <div class="header-left">
        <el-button @click="$router.back()"><el-icon><ArrowLeft /></el-icon>返回</el-button>
        <el-divider direction="vertical" />
        <h2>流程执行数据 - {{ workflowName }}</h2>
      </div>
    </div>

    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <el-radio-group v-model="mode" @change="handleModeChange">
            <el-radio-button label="prod">正式数据</el-radio-button>
            <el-radio-button label="test">测试数据</el-radio-button>
          </el-radio-group>
        </div>
        <div class="toolbar-right">
          <el-button v-if="mode === 'test' && executions.length" type="danger" plain @click="handleClearTestData">
            <el-icon><Delete /></el-icon> 清除测试数据
          </el-button>
          <el-button @click="fetchData">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
      </div>

      <el-table :data="executions" v-loading="loading" style="width: 100%">
        <el-table-column prop="timestamp" label="执行时间" width="200">
          <template #default="{ row }">
            {{ formatTime(row.timestamp) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'">
              {{ row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="提取变量数" width="120">
          <template #default="{ row }">
            {{ Object.keys(row.variables || {}).length }}
          </template>
        </el-table-column>
        <el-table-column label="操作">
          <template #default="{ row }">
            <el-button type="primary" link @click="viewDetail(row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="fetchData"
        />
      </div>
    </el-card>

    <!-- Detail Dialog -->
    <el-dialog v-model="detailVisible" title="执行数据详情" width="800px">
      <div v-if="selectedExecution">
        <el-descriptions border :column="1">
          <el-descriptions-item label="执行时间">{{ formatTime(selectedExecution.timestamp) }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="selectedExecution.status === 'success' ? 'success' : 'danger'">
              {{ selectedExecution.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="提取变量数" v-if="selectedExecution.variables">
            {{ Object.keys(selectedExecution.variables).length }}
          </el-descriptions-item>
          <el-descriptions-item label="错误信息" v-if="selectedExecution.error">
            <span class="text-danger">{{ selectedExecution.error }}</span>
          </el-descriptions-item>
        </el-descriptions>
        <div class="variables-section">
          <p class="section-title">提取的数据变量</p>
          <pre class="json-code">{{ JSON.stringify(selectedExecution.variables, null, 2) }}</pre>
        </div>
        <div class="screenshots-section">
          <p class="section-title">执行截图</p>
          <div class="screenshot-list" v-if="selectedExecution.screenshots?.length">
            <el-image 
              v-for="(url, index) in selectedExecution.screenshots" 
              :key="index"
              :src="getImageUrl(url)" 
              :preview-src-list="selectedExecution.screenshots.map(getImageUrl)"
              :initial-index="index"
              fit="contain"
              class="screenshot-item"
              lazy
              preview-teleported
            >
              <template #placeholder>
                <div class="image-slot">加载中...</div>
              </template>
              <template #error>
                <div class="image-slot">图片渲染失败</div>
              </template>
            </el-image>
          </div>
          <el-empty v-else description="本次执行未保存截图" :image-size="100" />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Refresh, Delete } from '@element-plus/icons-vue'
import { getWorkflowExecutions, getWorkflow, clearWorkflowTestData } from '@/api'

const route = useRoute()
const workflowId = route.params.id
const workflowName = ref('')
const loading = ref(false)
const executions = ref([])
const mode = ref('prod')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const detailVisible = ref(false)
const selectedExecution = ref(null)

const handleModeChange = () => {
  currentPage.value = 1
  fetchData()
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getWorkflowExecutions(workflowId, {
      mode: mode.value,
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value
    })
    executions.value = res
    // Note: total might need backend support, currently just showing current page size
    total.value = res.length === pageSize.value ? currentPage.value * pageSize.value + 1 : (currentPage.value - 1) * pageSize.value + res.length
  } catch (error) {
    ElMessage.error('获取执行数据失败')
  } finally {
    loading.value = false
  }
}

const fetchWorkflow = async () => {
  try {
    const data = await getWorkflow(workflowId)
    workflowName.value = data.name
  } catch (error) {}
}

const viewDetail = (row) => {
  selectedExecution.value = row
  detailVisible.value = true
}

const handleClearTestData = () => {
  ElMessageBox.confirm('确定要清除所有测试数据（包括日志、结果和执行记录）吗？', '提示', {
    type: 'warning',
    confirmButtonText: '确定',
    cancelButtonText: '取消'
  }).then(async () => {
    try {
      await clearWorkflowTestData(workflowId)
      ElMessage.success('测试数据已清除')
      fetchData()
    } catch (error) {
      ElMessage.error('清除测试数据失败')
    }
  }).catch(() => {})
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString()
}

const getImageUrl = (url) => {
  if (!url) return ''
  // 如果已经是 base64 数据，直接返回
  if (url.startsWith('data:')) return url
  const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
  return `${apiBase}${url}`
}

onMounted(() => {
  fetchWorkflow()
  fetchData()
})
</script>

<style scoped>
.workflow-results-container {
  padding: 0;
}
.page-header {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.table-toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
}
.result-details {
  padding: 20px;
  background: #f8fafc;
}
.detail-label {
  font-weight: bold;
  margin-bottom: 10px;
  display: block;
}
.json-code {
  background: #272822;
  color: #f8f8f2;
  padding: 15px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 13px;
  overflow-x: auto;
}
.error-info {
  margin-top: 15px;
}
.screenshots-preview {
  margin-top: 15px;
}
.screenshot-list-mini {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.screenshot-item-mini {
  width: 120px;
  height: 80px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
}
.image-slot-mini {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
  background: #f5f7fa;
  color: #909399;
  font-size: 12px;
}
.image-slot {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
  background: #f5f7fa;
  color: #909399;
}
.variables-section {
  margin-top: 20px;
}
.screenshots-section {
  margin-top: 20px;
}
.screenshot-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 15px;
}
.screenshot-item {
  width: 100%;
  height: 150px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}
.screenshot-item:hover {
  transform: scale(1.02);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
.section-title {
  font-weight: bold;
  margin-bottom: 10px;
}
.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
