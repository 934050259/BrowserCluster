<template>
  <div class="nodes-container">
    <div class="page-header">
      <div class="header-left">
        <h2>节点管理</h2>
        <p class="subtitle">管理分布式浏览器节点及其运行状态</p>
      </div>
      <el-button type="primary" @click="handleAdd">
        <el-icon><Plus /></el-icon>添加节点
      </el-button>
    </div>

    <el-card shadow="never" class="table-card">
      <el-table :data="nodes" v-loading="loading" style="width: 100%">
        <el-table-column prop="node_id" label="节点 ID" min-width="120" />
        <el-table-column prop="queue_name" label="任务队列" min-width="120" />
        <el-table-column prop="max_concurrent" label="最大并发" width="100" align="center" />
        <el-table-column prop="task_count" label="任务总数" width="100" align="center">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ row.task_count || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="运行状态" width="120">
          <template #default="{ row }">
            <el-tag 
              :type="row.status === 'running' ? 'success' : (row.status === 'offline' ? 'danger' : 'info')" 
              effect="dark"
            >
              {{ row.status === 'running' ? '运行中' : (row.status === 'offline' ? '已离线' : '已停止') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_seen" label="最后在线" width="180">
          <template #default="{ row }">
            {{ row.last_seen ? formatTime(row.last_seen) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button 
                v-if="row.status !== 'running'"
                type="success" 
                size="small" 
                @click="handleStart(row)"
              >启动</el-button>
              <el-button 
                v-else
                type="warning" 
                size="small" 
                @click="handleStop(row)"
              >停止</el-button>
              <el-button type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
              <el-button type="info" size="small" @click="handleViewLogs(row)">日志</el-button>
              <el-button type="danger" size="small" @click="handleDelete(row)">删除</el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Log Viewer Drawer -->
    <el-drawer
      v-model="logDrawerVisible"
      :title="`节点日志: ${currentLogNodeId}`"
      size="60%"
      direction="rtl"
      destroy-on-close
      @close="stopLogStream"
    >
      <div class="log-viewer" ref="logContainer">
        <pre v-if="logContent">{{ logContent }}</pre>
        <el-empty v-else description="暂无日志或正在加载..." />
      </div>
      <template #footer>
        <div class="drawer-footer">
          <el-checkbox v-model="autoScroll">自动滚动</el-checkbox>
          <el-button @click="stopLogStream">停止</el-button>
          <el-button type="primary" @click="startLogStream">重新连接</el-button>
        </div>
      </template>
    </el-drawer>

    <!-- Add/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑节点' : '添加节点'"
      width="500px"
    >
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <el-form-item label="节点 ID" prop="node_id">
          <el-input v-model="form.node_id" :disabled="isEdit" placeholder="例如: worker-01" />
        </el-form-item>
        <el-form-item label="任务队列" prop="queue_name">
          <el-input v-model="form.queue_name" placeholder="task_queue" />
        </el-form-item>
        <el-form-item label="最大并发" prop="max_concurrent">
          <el-input-number v-model="form.max_concurrent" :min="1" :max="20" />
          <div v-if="isEdit && form.status === 'running'" class="form-tip warning-tip">
            <el-icon><Warning /></el-icon> 节点运行中，修改最大并发将导致节点自动重启。
          </div>
          <div v-else class="form-tip">建议在节点停止状态下修改。</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Plus, Warning } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getNodes, createNode, updateNode, deleteNode, startNode, stopNode } from '../api'
import dayjs from 'dayjs'

const nodes = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref(null)

// 日志相关状态
const logDrawerVisible = ref(false)
const currentLogNodeId = ref('')
const logContent = ref('')
const logContainer = ref(null)
const autoScroll = ref(true)
let logAbortController = null

const form = ref({
  node_id: '',
  queue_name: 'task_queue',
  max_concurrent: 1
})

const rules = {
  node_id: [{ required: true, message: '请输入节点 ID', trigger: 'blur' }],
  queue_name: [{ required: true, message: '请输入队列名称', trigger: 'blur' }]
}

const fetchNodes = async () => {
  loading.value = true
  try {
    const data = await getNodes()
    nodes.value = data
  } catch (error) {
    ElMessage.error('获取节点列表失败')
  } finally {
    loading.value = false
  }
}

const handleAdd = () => {
  isEdit.value = false
  form.value = {
    node_id: '',
    queue_name: 'task_queue',
    max_concurrent: 1
  }
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  form.value = { ...row }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      try {
        if (isEdit.value) {
          await updateNode(form.value.node_id, form.value)
          ElMessage.success('更新成功')
        } else {
          await createNode(form.value)
          ElMessage.success('添加成功')
        }
        dialogVisible.value = false
        fetchNodes()
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || '操作失败')
      } finally {
        submitting.value = false
      }
    }
  })
}

const handleStart = async (row) => {
  try {
    await startNode(row.node_id)
    ElMessage.success(`节点 ${row.node_id} 启动成功`)
    fetchNodes()
  } catch (error) {
    ElMessage.error('启动失败')
  }
}

const handleStop = async (row) => {
  try {
    await stopNode(row.node_id)
    ElMessage.success(`节点 ${row.node_id} 已停止`)
    fetchNodes()
  } catch (error) {
    ElMessage.error('停止失败')
  }
}

const handleViewLogs = (row) => {
  currentLogNodeId.value = row.node_id
  logContent.value = ''
  logDrawerVisible.value = true
  startLogStream()
}

const startLogStream = async () => {
  if (logAbortController) {
    logAbortController.abort()
  }
  
  logAbortController = new AbortController()
  const nodeId = currentLogNodeId.value
  
  try {
    const response = await fetch(`/api/v1/nodes/${nodeId}/logs?stream=true&lines=100`, {
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
      
      // 限制日志显示长度，防止内存占用过大
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

const handleDelete = (row) => {
  ElMessageBox.confirm(
    `确定要删除节点 ${row.node_id} 吗？如果节点正在运行将被停止。`,
    '提示',
    { type: 'warning' }
  ).then(async () => {
    try {
      await deleteNode(row.node_id)
      ElMessage.success('删除成功')
      fetchNodes()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

const formatTime = (time) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

onMounted(() => {
  fetchNodes()
})
</script>

<style scoped>
.nodes-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left h2 {
  margin: 0 0 4px 0;
  font-size: 24px;
  color: #303133;
}

.subtitle {
  margin: 0;
  font-size: 14px;
  color: #909399;
}

.table-card {
  border-radius: 8px;
}

.log-viewer {
  background-color: #1e1e1e;
  color: #d4d4d4;
  padding: 15px;
  height: calc(100vh - 200px);
  overflow-y: auto;
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  line-height: 1.5;
  border-radius: 4px;
}

.log-viewer pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.drawer-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 15px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  display: flex;
  align-items: center;
}

.warning-tip {
  color: #e6a23c;
}
</style>
