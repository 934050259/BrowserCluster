<template>
  <div class="schedules-container">
    <el-card class="schedules-card" :body-style="{ padding: '0' }">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="title">定时任务</span>
            <span class="subtitle">配置和管理自动化调度抓取任务</span>
          </div>
          <div class="header-actions">
            <el-button type="primary" @click="openCreateDialog">
              <el-icon><Plus /></el-icon> 新建定时任务
            </el-button>
            <el-button @click="loadSchedules" :loading="loading">
              <el-icon><Refresh /></el-icon> 刷新
            </el-button>
          </div>
        </div>
      </template>

      <div class="filter-bar">
        <el-form :inline="true" :model="filterForm" class="filter-form">
          <el-form-item label="任务状态" style="width: 200px;">
            <el-select v-model="filterForm.status" placeholder="全部状态" clearable @change="handleFilter" style="width: 100%;">
              <el-option label="激活中" value="active" />
              <el-option label="已暂停" value="paused" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="名称搜索"  style="width: 300px;">
            <el-input 
              v-model="filterForm.name" 
              placeholder="搜索任务名称..." 
              clearable 
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
        :data="schedules" 
        v-loading="loading" 
        style="width: 100%" 
        class="schedules-table" 
        border 
        stripe
      >
        <el-table-column prop="name" label="任务名称" min-width="150">
          <template #default="{ row }">
            <div class="name-column">
              <span class="schedule-name">{{ row.name }}</span>
              <div class="schedule-desc" v-if="row.description">{{ row.description }}</div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="url" label="目标 URL" min-width="200">
          <template #default="{ row }">
            <el-link :href="row.url" target="_blank" type="primary" class="url-link">
              <el-icon><Link /></el-icon>
              {{ row.url }}
            </el-link>
          </template>
        </el-table-column>

        <el-table-column label="调度策略" width="200">
          <template #default="{ row }">
            <div class="schedule-policy">
              <el-tag v-if="row.schedule_type === 'interval'" type="info" size="small">
                每隔 {{ formatInterval(row.interval) }} 执行一次
              </el-tag>
              <el-tag v-else-if="row.schedule_type === 'cron'" type="warning" size="small">
                Cron: {{ row.cron }}
              </el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.status"
              active-value="active"
              inactive-value="paused"
              @change="handleToggleStatus(row)"
            />
          </template>
        </el-table-column>

        <el-table-column label="执行时间" width="200">
          <template #default="{ row }">
            <div class="execution-times">
              <div class="time-item">
                <span class="label">最近:</span>
                <span class="time">{{ formatDate(row.last_run) || '-' }}</span>
              </div>
              <div class="time-item" v-if="row.status === 'active'">
                <span class="label">下次:</span>
                <span class="time">{{ formatDate(row.next_run) || '-' }}</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip content="立即执行一次" placement="top">
                <el-button circle size="small" type="success" :icon="CaretRight" @click="handleRunNow(row)" />
              </el-tooltip>
              <el-tooltip content="采集记录" placement="top">
                <el-button circle size="small" type="info" :icon="List" @click="viewRecords(row)" />
              </el-tooltip>
              <el-tooltip content="编辑" placement="top">
                <el-button circle size="small" type="primary" :icon="Edit" @click="handleEdit(row)" />
              </el-tooltip>
              <el-tooltip content="删除" placement="top">
                <el-button circle size="small" type="danger" :icon="Delete" @click="confirmDelete(row)" />
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @size-change="loadSchedules"
          @current-change="loadSchedules"
        />
      </div>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog 
      v-model="showDialog" 
      :title="isEdit ? '编辑定时任务' : '新建定时任务'" 
      width="850px"
      destroy-on-close
      top="8vh"
      class="config-dialog"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px" label-position="top">
        <el-tabs v-model="activeTab" class="config-tabs">
          <!-- 1. 基础信息 -->
          <el-tab-pane name="basic">
            <template #label>
              <span class="tab-label">
                <el-icon class="icon-basic"><Link /></el-icon>
                <span>基础信息</span>
              </span>
            </template>
            
            <div class="tab-content">
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="任务名称" prop="name" required>
                    <el-input v-model="form.name" placeholder="请输入任务名称" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="任务优先级">
                    <el-select v-model="form.priority" style="width: 100%">
                      <el-option label="最高优先级 (10)" :value="10" />
                      <el-option label="普通优先级 (5)" :value="5" />
                      <el-option label="最低优先级 (1)" :value="1" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>

              <el-form-item label="目标 URL" prop="url" required>
                <el-input v-model="form.url" placeholder="https://example.com" clearable>
                  <template #prefix><el-icon class="icon-link"><Connection /></el-icon></template>
                </el-input>
              </el-form-item>

              <el-form-item label="任务描述" prop="description">
                <el-input v-model="form.description" type="textarea" :rows="2" placeholder="请输入任务描述" />
              </el-form-item>
              
              <el-form-item label="Cookies" v-if="form.params">
                <el-input
                  v-model="form.params.cookies"
                  type="textarea"
                  :rows="3"
                  placeholder="输入 Cookies 字符串或 JSON 格式，如：key1=value1; key2=value2"
                />
              </el-form-item>
            </div>
          </el-tab-pane>

          <!-- 2. 内容解析 -->
          <el-tab-pane name="parser">
            <template #label>
              <span class="tab-label">
                <el-icon class="icon-parser"><MagicStick /></el-icon>
                <span>内容解析</span>
              </span>
            </template>

            <div class="tab-content">
              <div class="parser-header-actions" v-if="matchedRules.length > 0">
                <el-dropdown @command="applyMatchedRule" trigger="click">
                  <el-button type="primary" plain size="small">
                    <el-icon><MagicStick /></el-icon>
                    发现 {{ matchedRules.length }} 条可用规则
                    <el-icon class="el-icon--right"><arrow-down /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item 
                        v-for="rule in matchedRules" 
                        :key="rule.id" 
                        :command="rule"
                      >
                        <div class="rule-item-dropdown">
                          <el-tag size="small" :type="getParserTypeTag(rule.parser_type)" class="mr-2">
                            {{ rule.parser_type.toUpperCase() }}
                          </el-tag>
                          <span class="rule-domain">{{ rule.domain }}</span>
                          <span class="rule-desc" v-if="rule.description">- {{ rule.description }}</span>
                        </div>
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>

              <el-form-item label="解析模式" v-if="form.params">
                <el-radio-group v-model="form.params.parser" size="default">
                  <el-radio-button label="">不解析</el-radio-button>
                  <el-radio-button label="gne">智能正文 (GNE)</el-radio-button>
                  <el-radio-button label="llm">大模型提取 (LLM)</el-radio-button>
                  <el-radio-button label="xpath">自定义规则 (XPath)</el-radio-button>
                </el-radio-group>
              </el-form-item>

              <div v-if="form.params && form.params.parser === 'gne'" class="parser-config-area">
                <el-alert title="GNE 模式" type="info" :closable="false" show-icon description="适用于新闻、博客等文章类页面，自动提取标题、作者、发布时间、正文和图片。" />
              </div>

              <div v-if="form.params && form.params.parser === 'llm'" class="parser-config-area">
                <div class="parser-presets">
                  <span class="preset-label">常用模板:</span>
                  <el-button-group>
                    <el-button size="small" plain @click="applyLlmPreset('article')">文章提取</el-button>
                    <el-button size="small" plain @click="applyLlmPreset('product')">商品详情</el-button>
                    <el-button size="small" plain @click="applyLlmPreset('contact')">联系方式</el-button>
                  </el-button-group>
                </div>
                <el-form-item label="目标提取字段" class="mt-4">
                  <el-select
                    v-model="selectedLlmFields"
                    multiple
                    filterable
                    allow-create
                    default-first-option
                    placeholder="选择或输入需要提取的字段"
                    style="width: 100%"
                  >
                    <el-option
                      v-for="item in llmFieldOptions"
                      :key="item.value"
                      :label="`${item.label} (${item.value})`"
                      :value="item.value"
                    />
                  </el-select>
                  <div class="input-tip">输入自定义字段名并按回车即可添加</div>
                </el-form-item>
              </div>

              <div v-if="form.params && form.params.parser === 'xpath'" class="parser-config-area">
                <div class="xpath-rules-header">
                  <span>XPath 规则配置</span>
                  <el-button type="primary" link :icon="Plus" @click="addXpathRule">添加规则</el-button>
                </div>
                <div v-for="(rule, index) in xpathRules" :key="index" class="xpath-rule-row">
                  <el-input v-model="rule.name" placeholder="字段名" style="width: 120px" />
                  <el-input v-model="rule.xpath" placeholder="XPath 表达式" style="flex: 1" />
                  <el-button 
                    type="danger" 
                    circle 
                    plain
                    :icon="Delete" 
                    @click="removeXpathRule(index)" 
                    :disabled="xpathRules.length <= 1"
                  />
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- 3. 浏览器特征 -->
          <el-tab-pane name="browser">
            <template #label>
              <span class="tab-label">
                <el-icon class="icon-browser"><Monitor /></el-icon>
                <span>浏览器特征</span>
              </span>
            </template>
            
            <div class="tab-content" v-if="form.params">
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="加载等待条件">
                    <el-select v-model="form.params.wait_for" style="width: 100%">
                      <el-option label="Network Idle (推荐)" value="networkidle" />
                      <el-option label="Page Load (所有资源)" value="load" />
                      <el-option label="DOM Ready (HTML解析)" value="domcontentloaded" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="截图配置">
                    <div class="switch-container">
                      <el-switch v-model="form.params.screenshot" />
                      <span class="switch-tip">{{ form.params.screenshot ? '开启' : '关闭' }}</span>
                    </div>
                  </el-form-item>
                </el-col>
              </el-row>

              <div class="feature-settings">
                <div class="feature-item">
                  <div class="feature-info">
                    <span class="feature-name">反检测模式 (Stealth)</span>
                    <span class="feature-desc">绕过大多数常见的机器人检测系统</span>
                  </div>
                  <el-switch v-model="form.params.stealth" />
                </div>
                <div class="feature-item">
                  <div class="feature-info">
                    <span class="feature-name">屏蔽图片/媒体</span>
                    <span class="feature-desc">不加载图片资源，加快抓取速度</span>
                  </div>
                  <el-switch v-model="form.params.block_images" />
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- 4. 高级设置 -->
          <el-tab-pane name="advanced">
            <template #label>
              <span class="tab-label">
                <el-icon class="icon-advanced"><Setting /></el-icon>
                <span>高级设置</span>
              </span>
            </template>
            
            <div class="tab-content">
              <div v-if="form.params">
                <div class="section-title">代理配置</div>
                <el-form-item label="代理服务器" v-if="form.params.proxy">
                  <el-input v-model="form.params.proxy.server" placeholder="http://proxy.example.com:8080" clearable />
                </el-form-item>
                <el-collapse-transition>
                  <el-row :gutter="20" v-if="form.params.proxy && form.params.proxy.server">
                    <el-col :span="12">
                      <el-form-item label="用户名">
                        <el-input v-model="form.params.proxy.username" placeholder="可选" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="密码">
                        <el-input v-model="form.params.proxy.password" show-password placeholder="可选" />
                      </el-form-item>
                    </el-col>
                  </el-row>
                </el-collapse-transition>
              </div>

              <div class="section-title mt-4">缓存策略</div>
              <el-row :gutter="20" v-if="form.cache">
                <el-col :span="12">
                  <el-form-item label="启用缓存">
                    <el-switch v-model="form.cache.enabled" />
                    <div class="input-tip" v-if="form.cache.enabled">
                      <el-icon><InfoFilled /></el-icon>
                      开启后，在 TTL 时间内重复执行将直接返回上次抓取的结果，不会触发真实浏览器访问。
                    </div>
                  </el-form-item>
                </el-col>
                <el-col :span="12" v-if="form.cache.enabled">
                  <el-form-item label="有效时长 (TTL/秒)">
                    <el-input-number v-model="form.cache.ttl" :min="60" controls-position="right" style="width: 100%" />
                  </el-form-item>
                </el-col>
              </el-row>
            </div>
          </el-tab-pane>

          <!-- 5. 调度策略 -->
          <el-tab-pane name="schedule">
            <template #label>
              <span class="tab-label">
                <el-icon class="icon-schedule"><Timer /></el-icon>
                <span>调度策略</span>
              </span>
            </template>
            
            <div class="tab-content">
              <div class="schedule-config-card">
                <el-form-item label="调度类型" prop="schedule_type">
                  <el-radio-group v-model="form.schedule_type" size="default">
                    <el-radio-button label="interval">间隔执行</el-radio-button>
                    <el-radio-button label="cron">Cron 表达式</el-radio-button>
                  </el-radio-group>
                </el-form-item>

                <div class="policy-content mt-4">
                  <el-form-item v-if="form.schedule_type === 'interval'" label="执行间隔" prop="interval">
                    <div class="interval-input">
                      <el-input-number v-model="intervalValue" :min="1" controls-position="right" />
                      <el-select v-model="intervalUnit" style="width: 100px; margin-left: 10px">
                        <el-option label="分" value="m" />
                        <el-option label="时" value="h" />
                        <el-option label="天" value="d" />
                      </el-select>
                    </div>
                    <div class="input-tip">系统将按此频率自动触发任务</div>
                  </el-form-item>

                  <el-form-item v-if="form.schedule_type === 'cron'" label="Cron 表达式" prop="cron">
                    <el-input v-model="form.cron" placeholder="*/5 * * * * (每 5 分钟执行一次)">
                      <template #append>
                        <el-button @click="openCronHelper">常用示例</el-button>
                      </template>
                    </el-input>
                    <div class="input-tip">
                      <el-icon><InfoFilled /></el-icon>
                      标准 5 位或 6 位 Cron 表达式，例如 <code>0 0 * * *</code> 表示每天凌晨执行
                    </div>
                  </el-form-item>
                </div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Search, Edit, Delete, CaretRight, Link, InfoFilled, Connection, MagicStick, Monitor, Setting, Timer, Warning, QuestionFilled, ArrowDown, CircleCheckFilled, List, View, Document, Promotion } from '@element-plus/icons-vue'
import { getSchedules, createSchedule, updateSchedule, deleteSchedule, toggleSchedule, runScheduleNow, getRulesByDomain, getTasks, getTask } from '../api'
import dayjs from 'dayjs'

const loading = ref(false)
const submitting = ref(false)
const schedules = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const router = useRouter()

// --- 1. 基础状态和表单定义 (置于顶部防止初始化错误) ---
const showDialog = ref(false)
const isEdit = ref(false)
const activeTab = ref('basic')
const formRef = ref(null)

// --- 采集记录相关状态 ---
const showRecordsDialog = ref(false)
const recordsLoading = ref(false)
const executionRecords = ref([])
const recordsTotal = ref(0)
const recordsPage = ref(1)
const recordsPageSize = ref(10)
const currentSchedule = ref(null)

// --- 任务详情相关状态 ---
const showTaskDialog = ref(false)
const currentTask = ref(null)
const activeDetailTab = ref('info')

const form = ref({
  name: '',
  description: '',
  url: '',
  schedule_type: 'interval',
  interval: 3600,
  cron: '',
  priority: 5,
  params: {
    screenshot: true,
    wait_for: 'networkidle',
    parser: '',
    cookies: '',
    stealth: true,
    block_images: false,
    proxy: {
      server: '',
      username: '',
      password: ''
    }
  },
  cache: {
    enabled: false,
    ttl: 3600
  }
})

const rules = {
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  url: [{ required: true, message: '请输入目标 URL', trigger: 'blur' }],
  interval: [{ required: true, message: '请输入执行间隔', trigger: 'blur' }],
  cron: [{ required: true, message: '请输入 Cron 表达式', trigger: 'blur' }]
}

const intervalValue = ref(60)
const intervalUnit = ref('m')

const selectedLlmFields = ref(['title', 'content'])
const llmFieldOptions = [
  { label: '标题', value: 'title' },
  { label: '正文', value: 'content' },
  { label: '作者', value: 'author' },
  { label: '发布时间', value: 'publish_time' },
  { label: '关键词', value: 'keywords' },
  { label: '摘要', value: 'summary' },
  { label: '价格', value: 'price' },
  { label: '商品名称', value: 'product_name' },
  { label: '联系方式', value: 'contact' },
  { label: '公司名称', value: 'company_name' },
  { label: '规格参数', value: 'specifications' }
]

const xpathRules = ref([
  { name: 'title', xpath: '//h1' },
  { name: 'content', xpath: "//div[@class='article-body']" }
])

const matchedRules = ref([])
let lastCheckedDomain = ''

// --- 2. 过滤器状态 ---
const filterForm = ref({
  status: '',
  name: ''
})

const getParserTypeTag = (type) => {
  const map = {
    'gne': 'success',
    'llm': 'warning',
    'xpath': 'primary'
  }
  return map[type] || 'info'
}

const applyMatchedRule = (rule, silent = false) => {
  form.value.params.parser = rule.parser_type
  if (rule.parser_type === 'llm') {
    selectedLlmFields.value = rule.parser_config.fields || []
  } else if (rule.parser_type === 'xpath') {
    const rules = rule.parser_config.rules || {}
    xpathRules.value = Object.entries(rules).map(([field, path]) => ({ name: field, xpath: path }))
  }
  if (!silent) {
    ElMessage.success(`已应用 ${rule.domain} 的解析配置`)
  }
}

// 监听标签页切换
watch(activeTab, async (newTab) => {
  if (newTab === 'parser' && form.value.url && form.value.url.startsWith('http')) {
    try {
      const urlObj = new URL(form.value.url)
      const domain = urlObj.hostname
      
      if (domain === lastCheckedDomain && matchedRules.value.length > 0) {
        if (!form.value.params.parser && matchedRules.value.length > 0) {
            const rule = matchedRules.value[0]
            applyMatchedRule(rule, true)
            ElMessage.success(`已自动加载 ${domain} 的解析配置`)
        }
        return
      }
      
      const rules = await getRulesByDomain(domain)
      matchedRules.value = rules || []
      lastCheckedDomain = domain
      
      if (matchedRules.value.length > 0) {
        const rule = matchedRules.value[0]
        applyMatchedRule(rule, true)
        
        if (matchedRules.value.length > 1) {
          ElMessage({
            message: `已自动加载域名 ${domain} 的首个匹配规则，共有 ${matchedRules.value.length} 条可用，您可手动切换。`,
            type: 'success',
            duration: 5000
          })
        } else {
          ElMessage.success(`已自动加载 ${domain} 的解析配置`)
        }
      }
    } catch (e) {
      matchedRules.value = []
      lastCheckedDomain = ''
    }
  }
})

// 监听 URL 变化
watch(() => form.value.url, async (newUrl) => {
  matchedRules.value = []
  lastCheckedDomain = ''
  
  if (newUrl && newUrl.startsWith('http')) {
    try {
      const urlObj = new URL(newUrl)
      const domain = urlObj.hostname
      const rules = await getRulesByDomain(domain)
      if (rules && rules.length > 0) {
        const ruleWithCookies = rules.find(r => r.cookies && r.cookies.trim())
        if (ruleWithCookies) {
          form.value.params.cookies = ruleWithCookies.cookies
          ElMessage.success(`已自动加载域名 ${domain} 的默认 Cookies`)
        }
        matchedRules.value = rules
        lastCheckedDomain = domain
      }
    } catch (e) {
      console.error('Fetch rules failed:', e)
    }
  }
})

const applyLlmPreset = (type) => {
  const presets = {
    article: ['title', 'content', 'author', 'publish_time'],
    product: ['product_name', 'price', 'description', 'specifications'],
    contact: ['company_name', 'phone', 'email', 'address']
  }
  if (presets[type]) {
    selectedLlmFields.value = [...presets[type]]
    ElMessage.success('已应用模板')
  }
}

const addXpathRule = () => xpathRules.value.push({ name: '', xpath: '' })
const removeXpathRule = (index) => xpathRules.value.splice(index, 1)

const openCronHelper = () => {
  ElMessageBox.alert(
    `<ul>
      <li><code>0 0 * * *</code>: 每天凌晨</li>
      <li><code>*/5 * * * *</code>: 每 5 分钟</li>
      <li><code>0 9 * * 1-5</code>: 工作日早上 9 点</li>
      <li><code>0 0 1 * *</code>: 每月 1 号凌晨</li>
    </ul>`,
    '常用 Cron 示例',
    { dangerouslyUseHTMLString: true }
  )
}

const loadSchedules = async () => {
  loading.value = true
  try {
    const params = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value
    }
    
    if (filterForm.value.status) params.status = filterForm.value.status
    if (filterForm.value.name) params.name = filterForm.value.name
    
    const data = await getSchedules(params)
    schedules.value = data.schedules
    total.value = data.total
  } catch (error) {
    ElMessage.error('获取定时任务失败')
  } finally {
    loading.value = false
  }
}

const handleFilter = () => {
  currentPage.value = 1
  loadSchedules()
}

const resetFilter = () => {
  filterForm.value = { status: '', name: '' }
  handleFilter()
}

const openCreateDialog = () => {
  isEdit.value = false
  form.value = {
    name: '',
    description: '',
    url: '',
    schedule_type: 'interval',
    interval: 3600,
    cron: '',
    priority: 5,
    params: {
      screenshot: true,
      wait_for: 'networkidle',
      parser: '',
      cookies: '',
      stealth: true,
      block_images: false,
      proxy: {
        server: '',
        username: '',
        password: ''
      }
    },
    cache: {
      enabled: false,
      ttl: 3600
    }
  }
  matchedRules.value = []
  lastCheckedDomain = ''
  selectedLlmFields.value = ['title', 'content']
  xpathRules.value = [
    { name: 'title', xpath: '//h1' },
    { name: 'content', xpath: "//div[@class='article-body']" }
  ]
  intervalValue.value = 60
  intervalUnit.value = 'm'
  activeTab.value = 'basic'
  showDialog.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  form.value = JSON.parse(JSON.stringify(row))
  
  // 处理间隔回显
  if (row.interval) {
    if (row.interval % 86400 === 0) {
      intervalValue.value = row.interval / 86400
      intervalUnit.value = 'd'
    } else if (row.interval % 3600 === 0) {
      intervalValue.value = row.interval / 3600
      intervalUnit.value = 'h'
    } else if (row.interval % 60 === 0) {
      intervalValue.value = row.interval / 60
      intervalUnit.value = 'm'
    } else {
      // 默认按分钟处理
      intervalValue.value = Math.max(1, Math.floor(row.interval / 60))
      intervalUnit.value = 'm'
    }
  }

  // 确保基础结构完整
  if (!form.value.params) {
    form.value.params = {
      screenshot: true,
      wait_for: 'networkidle',
      parser: '',
      cookies: '',
      stealth: true,
      block_images: false,
      proxy: { server: '', username: '', password: '' }
    }
  }
  if (!form.value.cache) {
    form.value.cache = { enabled: false, ttl: 3600 }
  }
  if (!form.value.params.proxy) {
    form.value.params.proxy = { server: '', username: '', password: '' }
  }

  // 处理解析配置回显
  if (form.value.params.parser === 'llm' && form.value.params.parser_config) {
    selectedLlmFields.value = form.value.params.parser_config.fields || []
  } else if (form.value.params.parser === 'xpath' && form.value.params.parser_config) {
    const rules = form.value.params.parser_config.rules || {}
    xpathRules.value = Object.entries(rules).map(([name, xpath]) => ({ name, xpath }))
  } else {
    selectedLlmFields.value = []
    xpathRules.value = [
      { name: 'title', xpath: '//h1' },
      { name: 'content', xpath: "//div[@class='article-body']" }
    ]
  }

  // 确保代理对象存在
  if (!form.value.params.proxy) {
    form.value.params.proxy = { server: '', username: '', password: '' }
  }

  // 处理 Cookies 回显
  if (form.value.params.cookies && typeof form.value.params.cookies !== 'string') {
    form.value.params.cookies = JSON.stringify(form.value.params.cookies, null, 2)
  }

  activeTab.value = 'basic'
  showDialog.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      try {
        // 计算间隔秒数
        let totalSeconds = intervalValue.value
        if (intervalUnit.value === 'm') totalSeconds *= 60
        else if (intervalUnit.value === 'h') totalSeconds *= 3600
        else if (intervalUnit.value === 'd') totalSeconds *= 86400
        
        const submitData = JSON.parse(JSON.stringify(form.value))
        submitData.interval = totalSeconds

        // 处理解析配置
        if (submitData.params.parser === 'llm') {
          submitData.params.parser_config = { fields: selectedLlmFields.value }
        } else if (submitData.params.parser === 'xpath') {
          const rules = {}
          xpathRules.value.forEach(r => {
            if (r.name && r.xpath) rules[r.name] = r.xpath
          })
          submitData.params.parser_config = { rules }
        } else if (submitData.params.parser === 'gne') {
          submitData.params.parser_config = {}
        } else {
          submitData.params.parser_config = null
        }

        // 处理代理
        if (!submitData.params.proxy || !submitData.params.proxy.server) {
          submitData.params.proxy = null
        } else {
          if (!submitData.params.proxy.username) delete submitData.params.proxy.username
          if (!submitData.params.proxy.password) delete submitData.params.proxy.password
        }

        // 处理 Cookies
        if (submitData.params.cookies) {
          const cookieVal = submitData.params.cookies.trim()
          if ((cookieVal.startsWith('[') && cookieVal.endsWith(']')) || 
              (cookieVal.startsWith('{') && cookieVal.endsWith('}'))) {
            try {
              submitData.params.cookies = JSON.parse(cookieVal)
            } catch (e) {
              console.warn('Cookies parse failed, using as string')
            }
          }
        } else {
          submitData.params.cookies = null
        }

        if (isEdit.value) {
          await updateSchedule(submitData.schedule_id, submitData)
          ElMessage.success('更新成功')
        } else {
          await createSchedule(submitData)
          ElMessage.success('创建成功')
        }
        showDialog.value = false
        loadSchedules()
      } catch (error) {
        ElMessage.error((isEdit.value ? '更新' : '创建') + '失败: ' + (error.response?.data?.detail || error.message))
      } finally {
        submitting.value = false
      }
    }
  })
}

const confirmDelete = (row) => {
  ElMessageBox.confirm(`确定要删除定时任务 "${row.name}" 吗？`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await deleteSchedule(row.schedule_id)
      ElMessage.success('删除成功')
      loadSchedules()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

const handleToggleStatus = async (row) => {
  try {
    await toggleSchedule(row.schedule_id)
    ElMessage.success(row.status === 'active' ? '已激活' : '已暂停')
    loadSchedules()
  } catch (error) {
    ElMessage.error('状态切换失败')
    row.status = row.status === 'active' ? 'paused' : 'active'
  }
}

const handleRunNow = async (row) => {
  try {
    await runScheduleNow(row.schedule_id)
    ElMessage.success('执行请求已提交')
    loadSchedules()
  } catch (error) {
    ElMessage.error('执行失败')
  }
}

// --- 采集记录逻辑 ---
const viewRecords = (row) => {
  router.push({
    name: 'TaskRecords',
    query: { schedule_id: row.schedule_id }
  })
}

const loadExecutionRecords = async () => {
  if (!currentSchedule.value) return
  
  recordsLoading.value = true
  try {
    const res = await getTasks({
      schedule_id: currentSchedule.value.schedule_id,
      skip: (recordsPage.value - 1) * recordsPageSize.value,
      limit: recordsPageSize.value
    })
    executionRecords.value = res.tasks
    recordsTotal.value = res.total
  } catch (error) {
    console.error('加载记录失败:', error)
    ElMessage.error('加载采集记录失败')
  } finally {
    recordsLoading.value = false
  }
}

const viewTaskDetail = async (row) => {
  try {
    const res = await getTask(row.task_id)
    currentTask.value = res
    activeDetailTab.value = 'info'
    showTaskDialog.value = true
  } catch (error) {
    ElMessage.error('获取任务详情失败')
  }
}

const formatStatus = (status) => {
  const map = {
    'pending': '等待中',
    'processing': '抓取中',
    'success': '成功',
    'failed': '失败'
  }
  return map[status] || status
}

const getStatusColor = (status) => {
  const map = {
    'pending': 'info',
    'processing': 'primary',
    'success': 'success',
    'failed': 'danger'
  }
  return map[status] || 'info'
}

const formatDate = (date) => {
  if (!date) return ''
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

const formatInterval = (seconds) => {
  if (!seconds) return '-'
  if (seconds % 86400 === 0) return `${seconds / 86400} 天`
  if (seconds % 3600 === 0) return `${seconds / 3600} 小时`
  if (seconds % 60 === 0) return `${seconds / 60} 分钟`
  // 如果有余秒，尝试展示更友好的格式
  if (seconds > 60) {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m} 分 ${s} 秒`
  }
  return `${seconds} 秒`
}

onMounted(() => {
  loadSchedules()
})
</script>

<style scoped>
.schedules-container {
  padding: 24px;
  background-color: #f0f2f5;
  min-height: calc(100vh - 64px);
}

.schedules-card {
  border-radius: 8px;
  border: none;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
}

.header-left .title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2f3d;
}

.header-left .subtitle {
  font-size: 13px;
  color: #909399;
  margin-left: 12px;
}

.name-column {
  display: flex;
  flex-direction: column;
  line-height: 1.4;
}

.schedule-name {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
}

.schedule-desc {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.filter-bar {
  padding: 16px 20px;
  background-color: #fff;
  border-bottom: 1px solid #ebeef5;
}

.filter-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.url-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  max-width: 100%;
}

.url-link :deep(.el-link--inner) {
  display: inline-block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.schedule-policy {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.execution-times {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.time-item {
  font-size: 12px;
  color: #606266;
}

.time-item .label {
  color: #909399;
  margin-right: 4px;
}

.pagination-container {
  padding: 16px 20px;
  display: flex;
  justify-content: flex-end;
}

/* 对话框配置样式 */
.config-tabs {
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  border: 1px solid #f1f5f9;
  background: #fff;
}

.config-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 8px 16px;
  background-color: #f8fafc;
  border-bottom: 1px solid #f1f5f9;
}

.config-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.config-tabs :deep(.el-tabs__active-bar) {
  height: 3px;
  border-radius: 3px;
}

.config-tabs :deep(.el-tabs__item) {
  height: auto;
  padding: 8px 20px;
}

.config-tabs :deep(.el-tabs__content) {
  padding: 0;
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: 600;
  font-size: 16px;
  padding: 8px 0;
}

.tab-label .el-icon {
  font-size: 20px;
}

.icon-basic { color: #3b82f6 !important; }
.icon-parser { color: #10b981 !important; }
.icon-browser { color: #f59e0b !important; }
.icon-advanced { color: #8b5cf6 !important; }
.icon-schedule { color: #ef4444 !important; }

.tab-content {
  padding: 24px;
  max-height: 60vh;
  overflow-y: auto;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 16px;
  padding-left: 10px;
  border-left: 4px solid #3b82f6;
}

.parser-header-actions {
  margin-bottom: 16px;
  display: flex;
  justify-content: flex-end;
}

.rule-item-dropdown {
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: 400px;
}

.rule-domain {
  font-weight: 600;
  color: #1e293b;
}

.rule-desc {
  font-size: 12px;
  color: #94a3b8;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.parser-config-area {
  background-color: #f8fafc;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  margin-top: 16px;
}

.parser-presets {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.preset-label {
  font-size: 13px;
  color: #64748b;
}

.xpath-rules-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-weight: 600;
  color: #475569;
}

.xpath-rule-row {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}

.feature-settings {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 20px;
}

.feature-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.feature-info {
  display: flex;
  flex-direction: column;
}

.feature-name {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.feature-desc {
  font-size: 12px;
  color: #64748b;
  margin-top: 2px;
}

.schedule-config-card {
  background: #fff;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.policy-content {
  background-color: #f8fafc;
  padding: 20px;
  border-radius: 8px;
  border: 1px dashed #cbd5e1;
}

.interval-input {
  display: flex;
  align-items: center;
}

.input-tip {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.mt-4 { margin-top: 16px; }
.mr-2 { margin-right: 8px; }
</style>
