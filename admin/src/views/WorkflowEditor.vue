<template>
  <div class="workflow-editor">
    <!-- Toolbar -->
    <div class="editor-toolbar">
      <div class="toolbar-left">
        <el-button @click="$router.back()"><el-icon><ArrowLeft /></el-icon>返回</el-button>
        <el-divider direction="vertical" />
        <el-input v-model="workflow.name" placeholder="工作流名称" class="name-input" />
      </div>
      <div class="toolbar-right">
        <el-button type="primary" :loading="saving" @click="handleSave">
          <el-icon><Check /></el-icon>保存
        </el-button>
        <el-button type="success" :loading="executing" @click="handleExecute('test')">
          <el-icon><VideoPlay /></el-icon>{{ executing ? (progress || '执行中...') : '测试' }}
        </el-button>
      </div>
    </div>

    <div class="editor-main">
      <!-- Node Library Sidebar -->
      <div class="node-sidebar">
        <div class="sidebar-title">动作库</div>
        <div class="node-group">
          <div 
            v-for="nodeType in availableNodeTypes" 
            :key="nodeType.type" 
            class="node-item"
            draggable="true"
            @dragstart="onDragStart($event, nodeType.type)"
          >
            <el-icon :class="nodeType.iconClass"><component :is="nodeType.icon" /></el-icon>
            <span>{{ nodeType.label }}</span>
          </div>
        </div>
      </div>

      <!-- Flow Canvas -->
      <div class="flow-container" @drop="onDrop" @dragover.prevent>
        <VueFlow
          v-model="elements"
          :node-types="nodeTypes"
          :default-edge-options="defaultEdgeOptions"
          @connect="onConnect"
          @nodes-initialized="onNodesInitialized"
        >
          <Background />
          <Controls />
          <MiniMap />
        </VueFlow>
      </div>

      <!-- Properties Panel -->
      <div class="properties-panel" v-if="selectedNode">
        <div class="panel-header">
          <span>{{ selectedNode.label }} 配置</span>
          <el-button link @click="selectedNode = null"><el-icon><Close /></el-icon></el-button>
        </div>
        <div class="panel-content">
          <el-form :model="selectedNode.data.params" label-position="top">
            <!-- Dynamic Form based on Node Type -->
            <template v-if="selectedNode.type === 'start'">
              <el-form-item label="执行引擎">
                <el-select v-model="selectedNode.data.params.engine" placeholder="请选择引擎">
                  <el-option label="Playwright (推荐)" value="playwright" />
                  <el-option label="DrissionPage" value="drission" />
                </el-select>
              </el-form-item>
            </template>

            <template v-if="selectedNode.type === 'goto'">
              <el-form-item label="目标 URL">
                <el-input v-model="selectedNode.data.params.url" placeholder="https://..." />
              </el-form-item>
              <el-form-item label="等待策略">
                <el-select v-model="selectedNode.data.params.wait_until">
                  <el-option label="Network Idle" value="networkidle" />
                  <el-option label="Load" value="load" />
                  <el-option label="DOM Content Loaded" value="domcontentloaded" />
                </el-select>
              </el-form-item>
              <el-form-item label="超时时间 (ms)">
                <el-input-number v-model="selectedNode.data.params.timeout" :min="0" :step="1000" />
              </el-form-item>
            </template>

            <template v-if="selectedNode.type === 'click'">
              <el-form-item label="选择器模式">
                <el-radio-group v-model="selectedNode.data.params.selector_type" size="small">
                  <el-radio-button label="css">CSS</el-radio-button>
                  <el-radio-button label="xpath">XPath</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="选择器 (Selector)">
                <el-input v-model="selectedNode.data.params.selector" placeholder="#button-id or .class" />
              </el-form-item>
              <el-form-item label="点击次数">
                <el-input-number v-model="selectedNode.data.params.click_count" :min="1" :max="10" />
              </el-form-item>
              <el-form-item label="延迟 (ms)">
                <el-input-number v-model="selectedNode.data.params.delay" :min="0" :step="100" />
              </el-form-item>
              <el-form-item label="超时时间 (ms)">
                <el-input-number v-model="selectedNode.data.params.timeout" :min="0" :step="1000" />
              </el-form-item>
            </template>

            <template v-if="selectedNode.type === 'type'">
              <el-form-item label="选择器模式">
                <el-radio-group v-model="selectedNode.data.params.selector_type" size="small">
                  <el-radio-button label="css">CSS</el-radio-button>
                  <el-radio-button label="xpath">XPath</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="选择器 (Selector)">
                <el-input v-model="selectedNode.data.params.selector" placeholder="#input-id" />
              </el-form-item>
              <el-form-item label="输入值">
                <el-input v-model="selectedNode.data.params.value" placeholder="Hello world or {{var}}" />
              </el-form-item>
              <el-form-item label="输入延迟 (ms)">
                <el-input-number v-model="selectedNode.data.params.delay" :min="0" :step="50" />
                <div class="branch-tip">每个字符输入之间的间隔。</div>
              </el-form-item>
            </template>

            <template v-if="selectedNode.type === 'wait'">
              <el-form-item label="选择器模式">
                <el-radio-group v-model="selectedNode.data.params.selector_type" size="small">
                  <el-radio-button label="css">CSS</el-radio-button>
                  <el-radio-button label="xpath">XPath</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="选择器 (可选)">
                <el-input v-model="selectedNode.data.params.selector" placeholder="等待该元素出现" />
              </el-form-item>
              <el-form-item label="等待时长 (ms)">
                <el-input-number v-model="selectedNode.data.params.timeout" :min="0" :step="500" />
              </el-form-item>
            </template>

            <template v-if="selectedNode.type === 'extract'">
              <el-form-item label="选择器模式">
                <el-radio-group v-model="selectedNode.data.params.selector_type" size="small">
                  <el-radio-button label="css">CSS</el-radio-button>
                  <el-radio-button label="xpath">XPath</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="选择器">
                <el-input v-model="selectedNode.data.params.selector" placeholder=".price-text" />
              </el-form-item>
              <el-form-item label="提取属性 (为空则提取文本)">
                <el-input v-model="selectedNode.data.params.attribute" placeholder="href, src, value..." />
              </el-form-item>
              <el-form-item label="保存至变量名">
                <el-input v-model="selectedNode.data.params.variable_name" placeholder="price" />
              </el-form-item>
            </template>

            <template v-if="selectedNode.type === 'get_info'">
              <el-form-item label="信息类型">
                <el-select v-model="selectedNode.data.params.info_type" placeholder="请选择要获取的信息">
                  <el-option label="当前 URL" value="url" />
                  <el-option label="页面标题" value="title" />
                  <el-option label="页面 Cookies" value="cookies" />
                  <el-option label="页面内容 (HTML)" value="content" />
                </el-select>
              </el-form-item>
              <el-form-item label="保存至变量名">
                <el-input v-model="selectedNode.data.params.variable_name" placeholder="my_var" />
              </el-form-item>
            </template>

            <template v-if="selectedNode.type === 'if'">
              <el-form-item label="选择器模式">
                <el-radio-group v-model="selectedNode.data.params.selector_type" size="small">
                  <el-radio-button label="css">CSS</el-radio-button>
                  <el-radio-button label="xpath">XPath</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="判断条件 (存在元素)">
                <el-input v-model="selectedNode.data.params.selector" placeholder="例如存在该元素则走 True 分支" />
              </el-form-item>
              <div class="branch-tip">
                请连接两条边，首条连接的边为 True 分支，第二条为 False 分支。
              </div>
            </template>

            <template v-if="selectedNode.type === 'iframe_switch'">
              <el-form-item label="选择器模式">
                <el-radio-group v-model="selectedNode.data.params.selector_type" size="small">
                  <el-radio-button label="css">CSS</el-radio-button>
                  <el-radio-button label="xpath">XPath</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="iframe 选择器">
                <el-input v-model="selectedNode.data.params.selector" placeholder="iframe 选择器，或输入 'main' 返回主页面" />
              </el-form-item>
            </template>

            <template v-if="selectedNode.type === 'tab_switch'">
              <el-form-item label="标签页索引">
                <el-input-number v-model="selectedNode.data.params.index" :min="0" :step="1" />
                <div class="branch-tip">0 为第一个标签页，1 为第二个，以此类推。</div>
              </el-form-item>
            </template>

            <template v-if="selectedNode.type === 'screenshot'">
              <el-form-item label="截图名称">
                <el-input v-model="selectedNode.data.params.name" placeholder="screenshot_name" />
              </el-form-item>
              <el-form-item label="全屏截图">
                <el-switch v-model="selectedNode.data.params.full_page" />
              </el-form-item>
            </template>

            <template v-if="selectedNode.type === 'hover'">
              <el-form-item label="选择器模式">
                <el-radio-group v-model="selectedNode.data.params.selector_type" size="small">
                  <el-radio-button label="css">CSS</el-radio-button>
                  <el-radio-button label="xpath">XPath</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="选择器 (Selector)">
                <el-input v-model="selectedNode.data.params.selector" placeholder="#element-id" />
              </el-form-item>
              <el-form-item label="超时时间 (ms)">
                <el-input-number v-model="selectedNode.data.params.timeout" :min="0" :step="1000" />
              </el-form-item>
            </template>

            <template v-if="selectedNode.type === 'keypress'">
              <el-form-item label="按键名称">
                <el-input v-model="selectedNode.data.params.key" placeholder="Enter, Escape, Tab, etc." />
              </el-form-item>
              <el-form-item label="按键间隔 (ms)">
                <el-input-number v-model="selectedNode.data.params.delay" :min="0" :step="100" />
              </el-form-item>
            </template>

            <div class="danger-zone">
              <el-button type="danger" plain @click="handleDeleteNode(selectedNode.id)">删除节点</el-button>
            </div>
          </el-form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { 
  ArrowLeft, Check, VideoPlay, Close, Link, Pointer, Edit, Timer, 
  Search, Switch, Monitor, Files, Camera, Finished, Aim, Connection, InfoFilled, Mouse, Key
} from '@element-plus/icons-vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'

import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

import { getWorkflow, createWorkflow, updateWorkflow, executeWorkflow, getExecutionStatus, getActiveExecutions } from '@/api'

const route = useRoute()
const router = useRouter()
const workflowId = route.params.id

const workflow = ref({
  name: '未命名流程',
  description: '',
  nodes: [],
  edges: [],
  variables: {}
})

const elements = ref([])
const selectedNode = ref(null)
const saving = ref(false)
const executing = ref(false)
const progress = ref('')
let pollInterval = null

const startPolling = (executionId) => {
  if (pollInterval) clearInterval(pollInterval)
  
  executing.value = true
  pollInterval = setInterval(async () => {
    try {
      const statusRes = await getExecutionStatus(executionId)
      if (statusRes.status === 'completed' || statusRes.status === 'failed') {
        clearInterval(pollInterval)
        pollInterval = null
        executing.value = false
        progress.value = ''
        if (statusRes.status === 'completed') {
          ElMessage.success('执行完成')
        } else {
          ElMessage.error('执行失败')
        }
      } else {
        progress.value = `${statusRes.completed_nodes}/${statusRes.total_nodes}`
      }
    } catch (err) {
      clearInterval(pollInterval)
      pollInterval = null
      executing.value = false
      progress.value = ''
    }
  }, 1000)
}

const { addNodes, addEdges, onNodeClick, onPaneClick, toObject, fromObject, onNodesInitialized } = useVueFlow()

const availableNodeTypes = [
  { type: 'start', label: '开始', icon: Finished, iconClass: 'text-success' },
  { type: 'goto', label: '页面跳转', icon: Link, iconClass: 'text-primary' },
  { type: 'click', label: '点击元素', icon: Pointer, iconClass: 'text-primary' },
  { type: 'type', label: '表单填写', icon: Edit, iconClass: 'text-primary' },
  { type: 'wait', label: '等待', icon: Timer, iconClass: 'text-warning' },
  { type: 'extract', label: '提取数据', icon: Aim, iconClass: 'text-success' },
  { type: 'get_info', label: '获取页面信息', icon: InfoFilled, iconClass: 'text-success' },
  { type: 'if', label: '条件分支', icon: Connection, iconClass: 'text-warning' },
  { type: 'tab_switch', label: '标签切换', icon: Files, iconClass: 'text-primary' },
  { type: 'iframe_switch', label: 'iFrame切换', icon: Monitor, iconClass: 'text-primary' },
  { type: 'hover', label: '鼠标悬停', icon: Mouse, iconClass: 'text-primary' },
  { type: 'keypress', label: '按键输入', icon: Key, iconClass: 'text-primary' },
  { type: 'screenshot', label: '屏幕截图', icon: Camera, iconClass: 'text-success' },
  { type: 'end', label: '结束', icon: Finished, iconClass: 'text-danger' }
]

const defaultEdgeOptions = {
  animated: true,
  style: { stroke: '#b1b1b7' }
}

const nodeTypes = {
  // 可以定义自定义节点组件，这里暂时使用默认
}

const initWorkflow = async () => {
  const id = route.params.id
  selectedNode.value = null
  
  if (id) {
    try {
      const data = await getWorkflow(id)
      workflow.value = data
      
      // Convert backend model to Vue Flow elements
      const nodes = data.nodes.map(n => ({
        id: n.id,
        type: n.type,
        label: n.label,
        position: n.position,
        data: { params: n.params }
      }))
      
      const edges = data.edges.map(e => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label,
        data: { condition_index: e.condition_index }
      }))
      
      elements.value = [...nodes, ...edges]

      // 检查当前工作流是否有活跃任务
      const activeEx = await getActiveExecutions()
      const currentActive = activeEx.find(ex => ex.workflow_id === id)
      if (currentActive) {
        startPolling(currentActive._id)
      }
    } catch (error) {
      ElMessage.error('加载流程失败')
    }
  } else {
    // Reset to default
    workflow.value = {
      name: '未命名流程',
      description: '',
      nodes: [],
      edges: [],
      variables: {}
    }
    // New workflow, add start node
    const startNode = {
      id: 'start-1',
      type: 'start',
      label: '开始',
      position: { x: 250, y: 50 },
      data: { params: {} }
    }
    elements.value = [startNode]
  }
}

onMounted(initWorkflow)

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})

// Watch for route changes to handle "New" vs "Edit" transitions
watch(() => route.params.id, (newId) => {
  initWorkflow()
})

onNodeClick(({ node }) => {
  selectedNode.value = node
})

onPaneClick(() => {
  selectedNode.value = null
})

const onDragStart = (event, type) => {
  if (event.dataTransfer) {
    event.dataTransfer.setData('application/vueflow', type)
    event.dataTransfer.effectAllowed = 'move'
  }
}

const onDrop = (event) => {
  const type = event.dataTransfer?.getData('application/vueflow')
  const position = { x: event.offsetX, y: event.offsetY }
  
  if (type) {
    const nodeType = availableNodeTypes.find(nt => nt.type === type)
    const newNode = {
      id: `${type}-${Date.now()}`,
      type: type,
      label: nodeType.label,
      position,
      data: { 
        params: {
          ...(type === 'start' ? { engine: 'playwright' } : {}),
          ...(type === 'get_info' ? { info_type: 'url' } : {}),
          ...(type === 'screenshot' ? { full_page: true } : {}),
          ...(['click', 'type', 'wait', 'extract', 'if', 'iframe_switch', 'hover'].includes(type) ? { selector_type: 'css' } : {})
        }
      }
    }
    addNodes([newNode])
  }
}

const onConnect = (params) => {
  addEdges([params])
}

const handleSave = async () => {
  saving.value = true
  try {
    const flowObj = toObject()
    
    const backendData = {
      name: workflow.value.name,
      description: workflow.value.description,
      nodes: flowObj.nodes.map(n => ({
        id: n.id,
        type: n.type,
        label: n.label,
        position: n.position,
        params: n.data.params
      })),
      edges: flowObj.edges.map((e, idx) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label,
        condition_index: e.data?.condition_index ?? (idx > 0 && flowObj.nodes.find(n => n.id === e.source)?.type === 'if' ? 1 : 0)
      })),
      variables: workflow.value.variables
    }

    if (workflowId) {
      await updateWorkflow(workflowId, backendData)
    } else {
      const res = await createWorkflow(backendData)
      router.replace({ name: 'WorkflowEditor', params: { id: res._id } })
    }
    ElMessage.success('保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const handleExecute = async (mode = 'prod') => {
  if (!workflowId) {
    ElMessage.warning('请先保存后再运行')
    return
  }
  if (executing.value) return
  
  executing.value = true
  progress.value = '准备中'
  
  try {
    const res = await executeWorkflow(workflowId, mode)
    const executionId = res.execution_id
    ElMessage.success(`${mode === 'test' ? '测试' : '正式'}执行已提交`)
    
    // 轮询进度
    startPolling(executionId)
    
  } catch (error) {
      const errorMsg = error.response?.data?.detail || '执行失败'
      ElMessage.error(errorMsg)
      executing.value = false
      progress.value = ''
    }
}

const handleDeleteNode = (id) => {
  elements.value = elements.value.filter(e => e.id !== id && e.source !== id && e.target !== id)
  selectedNode.value = null
}
</script>

<style scoped>
.workflow-editor {
  height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
  background: #f0f2f5;
  margin: -20px;
}

.editor-toolbar {
  height: 56px;
  background: #fff;
  border-bottom: 1px solid #dcdfe6;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  z-index: 10;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.name-input {
  width: 250px;
}

.editor-main {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.node-sidebar {
  width: 200px;
  background: #fff;
  border-right: 1px solid #dcdfe6;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sidebar-title {
  font-weight: bold;
  font-size: 14px;
  color: #303133;
  margin-bottom: 8px;
}

.node-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.node-item {
  padding: 10px 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  cursor: grab;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  transition: all 0.2s;
}

.node-item:hover {
  border-color: #409eff;
  background: #ecf5ff;
}

.node-item i {
  font-size: 16px;
}

.flow-container {
  flex: 1;
  position: relative;
  background: #f8f9fb;
}

.properties-panel {
  width: 300px;
  background: #fff;
  border-left: 1px solid #dcdfe6;
  display: flex;
  flex-direction: column;
}

.panel-header {
  padding: 16px;
  border-bottom: 1px solid #ebeef5;
  font-weight: bold;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-content {
  padding: 16px;
  overflow-y: auto;
}

.branch-tip {
  font-size: 12px;
  color: #909399;
  background: #f4f4f5;
  padding: 8px;
  border-radius: 4px;
  margin-top: 8px;
}

.danger-zone {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px dashed #dcdfe6;
  display: flex;
  justify-content: center;
}

.text-primary { color: #409eff; }
.text-success { color: #67c23a; }
.text-warning { color: #e6a23c; }
.text-danger { color: #f56c6c; }

:deep(.vue-flow__node) {
  border-radius: 8px;
  padding: 10px 15px;
  background: #fff;
  border: 1px solid #dcdfe6;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  font-size: 13px;
  min-width: 120px;
  text-align: center;
}

:deep(.vue-flow__node.selected) {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64,158,255,0.2);
}

:deep(.vue-flow__node-start) { border-left: 4px solid #67c23a; }
:deep(.vue-flow__node-end) { border-left: 4px solid #f56c6c; }
:deep(.vue-flow__node-if) { border-left: 4px solid #e6a23c; }
</style>
