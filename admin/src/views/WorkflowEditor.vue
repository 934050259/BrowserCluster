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
          <el-collapse v-model="activeCollapseNames">
            <el-collapse-item v-for="category in nodeCategories" :key="category.name" :title="category.name" :name="category.name">
              <div class="node-item-container">
                <div 
                  v-for="type in category.types" 
                  :key="type"
                  class="node-item" 
                  :draggable="true" 
                  @dragstart="onDragStart($event, type)"
                >
                  <el-icon :class="availableNodeTypes[type].iconClass"><component :is="availableNodeTypes[type].icon" /></el-icon>
                  <span>{{ availableNodeTypes[type].label }}</span>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>

      <!-- Flow Canvas -->
      <div class="flow-container" @drop="onDrop" @dragover.prevent>
        <VueFlow
          v-model="elements"
          :node-types="nodeTypes"
          :default-edge-options="defaultEdgeOptions"
          @connect="onConnect"
        >
          <Background />
          <Controls />
          <MiniMap />
        </VueFlow>
      </div>

      <!-- Properties Panel -->
      <div class="properties-panel" v-if="selectedNode && selectedNode.type">
        <div class="panel-header">
          <span>{{ selectedNode.label }} 配置</span>
          <el-button link @click="selectedNode = null"><el-icon><Close /></el-icon></el-button>
        </div>
        <div class="panel-content" v-if="selectedNode.data">
          <el-form :model="selectedNode.data.params" label-position="top">
            <el-form-item label="节点名称">
              <el-input v-model="selectedNode.label" placeholder="请输入节点名称" />
            </el-form-item>
            
            <!-- Dynamic Form based on Node Type -->
            <template v-if="selectedNode.type === 'start'">
              <el-form-item label="执行引擎">
                <el-select v-model="selectedNode.data.params.engine" placeholder="请选择引擎">
                  <el-option label="Playwright (推荐)" value="playwright" />
                  <el-option label="DrissionPage" value="drission" />
                </el-select>
              </el-form-item>
              <el-form-item label="代理服务器 (可选)">
                <el-input v-model="selectedNode.data.params.proxy" placeholder="http://user:pass@host:port" />
                <div class="branch-tip">支持 http/https/socks5 代理</div>
                <el-alert
                  v-if="selectedNode.data.params.engine === 'drission' && selectedNode.data.params.proxy?.includes('@')"
                  title="注意：DrissionPage 引擎暂不支持带账号密码的代理，建议使用 Playwright 或不带认证的代理。"
                  type="warning"
                  :closable="false"
                  show-icon
                  style="margin-top: 8px"
                />
              </el-form-item>
              <el-form-item label="自定义请求头 (JSON)">
                <el-input 
                  v-model="selectedNode.data.params.headers" 
                  type="textarea" 
                  :rows="3" 
                  placeholder='{"User-Agent": "Mozilla/5.0...", "Referer": "https://google.com"}' 
                />
                <div class="branch-tip">请输入合法的 JSON 格式</div>
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

            <template v-if="selectedNode.type === 'reload'">
              <div class="branch-tip">刷新当前页面并等待网络空闲。</div>
            </template>

            <template v-if="selectedNode.type === 'back'">
              <div class="branch-tip">返回上一页。</div>
            </template>

            <template v-if="selectedNode.type === 'forward'">
              <div class="branch-tip">前进到下一页。</div>
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

            <template v-if="selectedNode.type === 'clear'">
              <el-form-item label="选择器模式">
                <el-radio-group v-model="selectedNode.data.params.selector_type" size="small">
                  <el-radio-button label="css">CSS</el-radio-button>
                  <el-radio-button label="xpath">XPath</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="选择器 (Selector)">
                <el-input v-model="selectedNode.data.params.selector" placeholder="#input-id" />
              </el-form-item>
            </template>

            <template v-if="selectedNode.type === 'select'">
              <el-form-item label="选择器模式">
                <el-radio-group v-model="selectedNode.data.params.selector_type" size="small">
                  <el-radio-button label="css">CSS</el-radio-button>
                  <el-radio-button label="xpath">XPath</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="下拉框选择器 (Selector)">
                <el-input v-model="selectedNode.data.params.selector" placeholder="select#id" />
              </el-form-item>
              <el-form-item label="选择值 (Value/Label/Index)">
                <el-input v-model="selectedNode.data.params.value" placeholder="Option Value" />
              </el-form-item>
            </template>

            <template v-if="selectedNode.type === 'scroll'">
              <el-form-item label="选择器模式">
                <el-radio-group v-model="selectedNode.data.params.selector_type" size="small">
                  <el-radio-button label="css">CSS</el-radio-button>
                  <el-radio-button label="xpath">XPath</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="目标元素 (可选)">
                <el-input v-model="selectedNode.data.params.selector" placeholder="不填则滚动整个窗口" />
              </el-form-item>
              <el-form-item label="滚动方向">
                <el-select v-model="selectedNode.data.params.direction">
                  <el-option label="向下 (Down)" value="down" />
                  <el-option label="向上 (Up)" value="up" />
                  <el-option label="滚动到顶部" value="top" />
                  <el-option label="滚动到底部" value="bottom" />
                </el-select>
              </el-form-item>
              <el-form-item label="滚动距离 (px)" v-if="['down', 'up'].includes(selectedNode.data.params.direction)">
                <el-input-number v-model="selectedNode.data.params.delta" :min="0" :step="100" />
              </el-form-item>
            </template>

            <template v-if="selectedNode.type === 'drag_drop'">
              <el-form-item label="选择器模式">
                <el-radio-group v-model="selectedNode.data.params.selector_type" size="small">
                  <el-radio-button label="css">CSS</el-radio-button>
                  <el-radio-button label="xpath">XPath</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="源元素 (Source Selector)">
                <el-input v-model="selectedNode.data.params.selector" placeholder="拖拽的起始元素" />
              </el-form-item>
              <el-form-item label="目标元素 (Target Selector)">
                <el-input v-model="selectedNode.data.params.target_selector" placeholder="拖拽到的目标位置" />
              </el-form-item>
            </template>

            <template v-if="selectedNode.type === 'upload'">
              <el-form-item label="选择器模式">
                <el-radio-group v-model="selectedNode.data.params.selector_type" size="small">
                  <el-radio-button label="css">CSS</el-radio-button>
                  <el-radio-button label="xpath">XPath</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="文件输入框选择器">
                <el-input v-model="selectedNode.data.params.selector" placeholder="input[type='file']" />
              </el-form-item>
              <el-form-item label="文件路径">
                <el-input v-model="selectedNode.data.params.file_paths" placeholder="C:/path/to/file1.png, C:/path/to/file2.txt" />
                <div class="branch-tip">多个文件请用逗号分隔。注意后端执行环境的文件路径。</div>
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
                <el-input v-model="selectedNode.data.params.selector" placeholder="等待该元素 appear" />
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

            <template v-if="selectedNode.type === 'js_execute'">
              <el-form-item label="JavaScript 脚本">
                <el-input 
                  v-model="selectedNode.data.params.script" 
                  type="textarea" 
                  :rows="5" 
                  placeholder="return document.querySelector('.price').innerText;" 
                />
                <div class="branch-tip">脚本执行结果将保存到变量中。</div>
              </el-form-item>
              <el-form-item label="保存结果至变量名">
                <el-input v-model="selectedNode.data.params.variable_name" placeholder="js_result" />
              </el-form-item>
            </template>

            <template v-if="selectedNode.type === 'set_variable'">
              <el-form-item label="变量名">
                <el-input v-model="selectedNode.data.params.variable_name" placeholder="my_var" />
              </el-form-item>
              <el-form-item label="变量值">
                <el-input v-model="selectedNode.data.params.value" placeholder="123 or hello" />
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

            <template v-if="selectedNode.type === 'loop'">
              <el-form-item label="循环次数">
                <el-input-number v-model="selectedNode.data.params.loop_count" :min="1" :max="100" />
              </el-form-item>
              <div class="branch-tip">注意：目前循环仅支持简单的顺序连接，复杂循环逻辑正在开发中。</div>
            </template>

            <template v-if="selectedNode.type === 'wait_request'">
              <el-form-item label="URL 匹配模式 (正则/字符串)">
                <el-input v-model="selectedNode.data.params.url_pattern" placeholder="例如 **/api/v1/user" />
              </el-form-item>
              <el-form-item label="超时时间 (ms)">
                <el-input-number v-model="selectedNode.data.params.timeout" :min="0" :step="1000" />
              </el-form-item>
            </template>

            <template v-if="selectedNode.type === 'wait_response'">
              <el-form-item label="URL 匹配模式 (正则/字符串)">
                <el-input v-model="selectedNode.data.params.url_pattern" placeholder="例如 **/api/v1/user" />
              </el-form-item>
              <el-form-item label="超时时间 (ms)">
                <el-input-number v-model="selectedNode.data.params.timeout" :min="0" :step="1000" />
              </el-form-item>
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
import { ref, onMounted, watch, onUnmounted, computed, nextTick, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { 
  ArrowLeft, Check, VideoPlay, Close, Link, Pointer, Edit, Timer, 
  Search, Switch, Monitor, Files, Camera, Finished, Aim, Connection, InfoFilled, Mouse, Key, Bottom, Delete, Select,
  Rank, Upload, Refresh, Back, Right, Cpu, Operation, Connection as LinkIcon
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
const workflowId = computed(() => route.params.id)

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

onNodesInitialized((nodes) => {
  console.log('Nodes initialized:', nodes.length)
})

const nodeCategories = [
  {
    name: '基础控制',
    types: ['start', 'end', 'goto', 'wait', 'screenshot', 'reload', 'back', 'forward']
  },
  {
    name: '页面交互',
    types: ['click', 'type', 'clear', 'select', 'hover', 'keypress', 'scroll', 'drag_drop', 'upload']
  },
  {
    name: '数据处理',
    types: ['extract', 'get_info', 'js_execute', 'set_variable']
  },
  {
    name: '流程控制',
    types: ['if', 'loop', 'tab_switch', 'iframe_switch', 'wait_request', 'wait_response']
  }
]

const availableNodeTypes = {
  start: { type: 'start', label: '开始', icon: Finished, iconClass: 'text-success' },
  end: { type: 'end', label: '结束', icon: Finished, iconClass: 'text-danger' },
  goto: { type: 'goto', label: '页面跳转', icon: Link, iconClass: 'text-primary' },
  wait: { type: 'wait', label: '等待', icon: Timer, iconClass: 'text-warning' },
  screenshot: { type: 'screenshot', label: '屏幕截图', icon: Camera, iconClass: 'text-success' },
  click: { type: 'click', label: '点击元素', icon: Pointer, iconClass: 'text-primary' },
  type: { type: 'type', label: '表单填写', icon: Edit, iconClass: 'text-primary' },
  clear: { type: 'clear', label: '清空输入', icon: Delete, iconClass: 'text-primary' },
  select: { type: 'select', label: '下拉选择', icon: Select, iconClass: 'text-primary' },
  hover: { type: 'hover', label: '鼠标悬停', icon: Mouse, iconClass: 'text-primary' },
  keypress: { type: 'keypress', label: '按键输入', icon: Key, iconClass: 'text-primary' },
  scroll: { type: 'scroll', label: '页面滚动', icon: Bottom, iconClass: 'text-primary' },
  drag_drop: { type: 'drag_drop', label: '拖拽元素', icon: Rank, iconClass: 'text-primary' },
  upload: { type: 'upload', label: '上传文件', icon: Upload, iconClass: 'text-primary' },
  reload: { type: 'reload', label: '刷新页面', icon: Refresh, iconClass: 'text-primary' },
  back: { type: 'back', label: '后退', icon: Back, iconClass: 'text-primary' },
  forward: { type: 'forward', label: '前进', icon: Right, iconClass: 'text-primary' },
  extract: { type: 'extract', label: '提取数据', icon: Aim, iconClass: 'text-success' },
  get_info: { type: 'get_info', label: '获取页面信息', icon: InfoFilled, iconClass: 'text-success' },
  js_execute: { type: 'js_execute', label: '执行 JS', icon: Cpu, iconClass: 'text-success' },
  set_variable: { type: 'set_variable', label: '设置变量', icon: Operation, iconClass: 'text-success' },
  if: { type: 'if', label: '条件分支', icon: Connection, iconClass: 'text-warning' },
  loop: { type: 'loop', label: '循环', icon: Refresh, iconClass: 'text-warning' },
  tab_switch: { type: 'tab_switch', label: '标签切换', icon: Files, iconClass: 'text-primary' },
  iframe_switch: { type: 'iframe_switch', label: 'iFrame切换', icon: Monitor, iconClass: 'text-primary' },
  wait_request: { type: 'wait_request', label: '等待请求', icon: LinkIcon, iconClass: 'text-warning' },
  wait_response: { type: 'wait_response', label: '等待响应', icon: LinkIcon, iconClass: 'text-warning' }
}

const activeCollapseNames = ref(['基础控制', '页面交互', '数据提取', '流程控制'])


const defaultEdgeOptions = {
  animated: true,
  style: { stroke: '#b1b1b7' }
}

const nodeTypes = {
  // 可以定义自定义节点组件，这里暂时使用默认
}

const initWorkflow = async () => {
  const id = workflowId.value
  selectedNode.value = null
  
  // 确保 Vue Flow 实例在切换时处于干净状态
  elements.value = []
  await nextTick()
  
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
    const nodeTypeData = availableNodeTypes[type]
    const newNode = {
      id: `${type}-${Date.now()}`,
      type: type,
      label: nodeTypeData.label,
      position,

      data: { 
        params: {
          ...(type === 'start' ? { engine: 'playwright' } : {}),
          ...(type === 'get_info' ? { info_type: 'url' } : {}),
          ...(type === 'screenshot' ? { full_page: true } : {}),
          ...(type === 'scroll' ? { direction: 'down', delta: 500 } : {}),
          ...(['click', 'type', 'wait', 'extract', 'if', 'iframe_switch', 'hover', 'clear', 'select', 'scroll', 'drag_drop', 'upload'].includes(type) ? { selector_type: 'css' } : {}),
          ...(type === 'js_execute' ? { script: 'return document.title;', variable_name: 'js_result' } : {}),
          ...(type === 'set_variable' ? { variable_name: 'my_var', value: '' } : {}),
          ...(type === 'wait_request' || type === 'wait_response' ? { url_pattern: '', timeout: 30000 } : {}),
          ...(type === 'loop' ? { loop_count: 5 } : {})
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
        params: n.data?.params || {}
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

    if (workflowId.value) {
      await updateWorkflow(workflowId.value, backendData)
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
  if (!workflowId.value) {
    ElMessage.warning('请先保存后再运行')
    return
  }
  if (executing.value) return
  
  executing.value = true
  progress.value = '准备中'
  
  try {
    const res = await executeWorkflow(workflowId.value, mode)
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
  overflow-y: auto;
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

.node-item-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.node-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  background-color: #f8f9fa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  cursor: grab;
  transition: all 0.3s ease;
}

.node-item:hover {
  background-color: #ecf5ff;
  border-color: #c6e2ff;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.node-item:active {
  cursor: grabbing;
}

.node-item .el-icon {
  margin-right: 8px;
  font-size: 16px;
}

/* 覆盖 el-collapse 默认样式，使其更紧凑 */
:deep(.el-collapse) {
  border-top: none;
}
:deep(.el-collapse-item__header) {
  font-weight: bold;
  color: #606266;
  background-color: transparent;
  border-bottom: 1px solid #ebeef5;
}
:deep(.el-collapse-item__wrap) {
  border-bottom: none;
  background-color: transparent;
}
:deep(.el-collapse-item__content) {
  padding-bottom: 10px;
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
