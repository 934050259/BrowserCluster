<template>
  <div class="rules-container">
    <div class="page-header">
      <div class="header-left">
        <h2>网站配置</h2>
        <p class="subtitle">管理网站的解析规则、Cookies 等配置</p>
      </div>
      <el-button type="primary" @click="handleAdd">
        <el-icon><Plus /></el-icon>添加配置
      </el-button>
    </div>

    <el-card shadow="never" class="table-card">
      <el-table :data="rules" v-loading="loading" style="width: 100%;">
        <el-table-column prop="domain" label="域名" min-width="150" />
        <el-table-column prop="priority" label="优先级" width="100" sortable>
          <template #default="{ row }">
            <el-tag size="small" type="warning">{{ row.priority || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="parser_type" label="解析类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getParserTypeTag(row.parser_type)">{{ row.parser_type.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="缓存时间" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.cache_config?.enabled" type="success" size="small">
              开启 ({{ formatDuration(row.cache_config.ttl) }})
            </el-tag>
            <el-tag v-else type="info" size="small">关闭</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Cookies" min-width="100">
          <template #default="{ row }">
            <el-tag v-if="row.cookies" type="success" size="small">已配置</el-tag>
            <el-tag v-else type="info" size="small">未配置</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="说明" min-width="200" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-switch v-model="row.is_active" @change="toggleStatus(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="最后修改" width="180">
          <template #default="{ row }">
            {{ formatTime(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
              <el-button type="danger" size="small" @click="handleDelete(row)">删除</el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog 
      v-model="dialogVisible" 
      :title="isEdit ? '编辑网站配置' : '添加网站配置'" 
      width="850px"
      destroy-on-close
      top="8vh"
      class="config-dialog"
    >
      <el-form :model="form" label-width="120px" :rules="formRules" ref="formRef">
        <el-tabs v-model="activeTab" class="config-tabs">
          <!-- 1. 基础配置 -->
          <el-tab-pane name="basic">
            <template #label>
              <span class="tab-label">
                <el-icon class="icon-basic"><Connection /></el-icon>
                <span>基础配置</span>
              </span>
            </template>
            
            <div class="tab-content">
              <div class="section-group">
                <div class="section-title">域名与身份验证</div>
                <el-form-item label="目标域名" prop="domain" required>
                  <el-input v-model="form.domain" placeholder="例如: example.com 或 *.example.com" clearable>
                    <template #prefix><el-icon class="icon-link"><Connection /></el-icon></template>
                  </el-input>
                  <div class="input-tip">支持相同域名配置多条规则，系统将优先匹配高优先级配置</div>
                </el-form-item>
                
                <el-form-item label="Cookies" prop="cookies">
                  <el-input 
                    v-model="form.cookies" 
                    type="textarea" 
                    :rows="4" 
                    placeholder="请输入网站 Cookies (JSON 格式或 key1=value1; key2=value2)" 
                  />
                  <div class="input-tip">配置后任务执行时将自动携带该 Cookies</div>
                </el-form-item>
              </div>

              <div class="section-group">
                <div class="section-title">规则属性</div>
                <el-row :gutter="20">
                  <el-col :span="12">
                    <el-form-item label="优先级" prop="priority">
                      <el-select v-model="form.priority" style="width: 100%">
                        <el-option label="最高优先级 (10)" :value="10" />
                        <el-option label="高优先级 (8)" :value="8" />
                        <el-option label="普通优先级 (5)" :value="5" />
                        <el-option label="低优先级 (3)" :value="3" />
                        <el-option label="最低优先级 (1)" :value="1" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="状态">
                      <div class="switch-container">
                        <el-switch v-model="form.is_active" />
                        <span class="switch-tip">{{ form.is_active ? '启用中' : '已禁用' }}</span>
                      </div>
                    </el-form-item>
                  </el-col>
                </el-row>

                <el-row :gutter="20">
                  <el-col :span="12">
                    <el-form-item label="存储位置">
                      <el-radio-group v-model="form.storage_type" size="default">
                        <el-radio-button label="mongo">MongoDB</el-radio-button>
                        <el-radio-button label="oss">OSS 存储</el-radio-button>
                      </el-radio-group>
                    </el-form-item>
                  </el-col>
                  <el-col :span="12" v-if="form.storage_type">
                    <el-form-item label="自定义存储">
                      <template v-if="form.storage_type === 'mongo'">
                        <div class="storage-input-group">
                          <div class="input-label-tip">自定义 MongoDB 集合名</div>
                          <el-input 
                            v-model="form.mongo_collection" 
                            placeholder="例如: my_collection"
                            size="small"
                            clearable
                          >
                            <template #prefix><el-icon><Collection /></el-icon></template>
                          </el-input>
                        </div>
                        <div class="storage-path-preview">
                          <el-icon><InfoFilled /></el-icon>
                          <span>实际存储集合: <code>{{ form.mongo_collection || 'tasks_results' }}</code></span>
                        </div>
                      </template>

                      <template v-if="form.storage_type === 'oss'">
                        <div class="storage-input-group">
                          <div class="input-label-tip">自定义 OSS 存储路径</div>
                          <el-input 
                            v-model="form.oss_path" 
                            placeholder="例如: custom/path/"
                            size="small"
                            clearable
                          >
                            <template #prefix><el-icon><FolderOpened /></el-icon></template>
                          </el-input>
                        </div>
                        <div class="storage-path-preview">
                          <el-icon><InfoFilled /></el-icon>
                          <span>实际存储路径: <code>{{ form.oss_path ? (form.oss_path.endsWith('/') ? form.oss_path : form.oss_path + '/') : 'tasks/' }}{任务ID}/...</code></span>
                        </div>
                      </template>
                    </el-form-item>
                  </el-col>
                </el-row>

                <el-form-item label="备注说明" style="margin-bottom: 0">
                  <el-input v-model="form.description" type="textarea" :rows="2" placeholder="配置说明，便于后续维护" />
                </el-form-item>
              </div>
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
              <div class="section-group">
                <div class="section-title">解析模式选择</div>
                <el-form-item label="解析模式">
                  <el-radio-group v-model="form.parser_type" size="default">
                    <el-radio-button label="gne">智能解析 (GNE)</el-radio-button>
                    <el-radio-button label="llm">大模型提取 (LLM)</el-radio-button>
                    <el-radio-button label="xpath">自定义规则 (XPath)</el-radio-button>
                  </el-radio-group>
                </el-form-item>
              </div>

              <div class="section-group">
                <div class="section-title">解析详细配置</div>
                <!-- GNE Config -->
                <div v-if="form.parser_type === 'gne'" class="parser-config-area">
                  <el-form-item label="提取模式">
                    <el-radio-group v-model="form.parser_config.mode" size="small">
                      <el-radio-button label="detail">详情模式</el-radio-button>
                      <el-radio-button label="list">列表模式</el-radio-button>
                    </el-radio-group>
                  </el-form-item>

                  <div v-if="form.parser_config.mode === 'list'" class="mt-4">
                    <el-form-item label="列表项 XPath">
                      <el-input 
                        v-model="form.parser_config.list_xpath" 
                        placeholder="例如: //ul/li[1]/a 或 /html/body/div/ul/li[1]/a"
                        clearable
                      >
                        <template #prefix><el-icon><Search /></el-icon></template>
                      </el-input>
                      <div class="input-tip">提示：指定列表中任意一个标题元素的 XPath，GNE 将以此为特征自动识别整个列表。</div>
                    </el-form-item>
                  </div>

                  <el-alert 
                    :title="form.parser_config.mode === 'list' ? 'GNE 列表模式' : 'GNE 详情模式'" 
                    type="info" 
                    :closable="false" 
                    show-icon
                    :description="form.parser_config.mode === 'list' ? '自动识别并提取新闻、博客列表页中的标题、链接及发布日期。' : '适用于新闻、博客等文章类页面，自动提取标题、作者、发布时间、正文和图片。'"
                  />
                </div>

                <!-- LLM Config -->
                <div v-if="form.parser_type === 'llm'" class="parser-config-area">
                  <div class="parser-presets">
                    <span class="preset-label">常用模板:</span>
                    <el-button-group>
                      <el-button size="small" plain @click="applyLlmPreset('article')">文章提取</el-button>
                      <el-button size="small" plain @click="applyLlmPreset('product')">商品详情</el-button>
                      <el-button size="small" plain @click="applyLlmPreset('contact')">联系方式</el-button>
                    </el-button-group>
                  </div>
                  <el-form-item label="提取字段" class="mt-4">
                    <el-select
                      v-model="selectedLlmFields"
                      multiple
                      filterable
                      allow-create
                      :reserve-keyword="false"
                      placeholder="选择或输入需要提取的字段"
                      style="width: 100%"
                      @change="handleLlmFieldsChange"
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
                  
                  <el-alert
                    title="配置说明"
                    type="info"
                    :closable="false"
                    show-icon
                    class="mt-4 llm-helper-alert"
                  >
                    <template #default>
                      <div class="alert-content-mini">
                        <p class="helper-text">请按 <strong>描述 (键名)</strong> 格式选择或输入字段。</p>
                        <div class="format-example-mini">
                          <span class="example-label">结果示例:</span>
                          <code>{ "title": "..." }</code>
                        </div>
                      </div>
                    </template>
                  </el-alert>
                </div>

                <!-- XPath Config -->
                <div v-if="form.parser_type === 'xpath'" class="parser-config-area">
                  <div v-for="(item, index) in xpathRules" :key="index" class="xpath-rule-item">
                    <el-input v-model="item.field" placeholder="字段名" style="width: 120px" />
                    <el-input v-model="item.xpath" placeholder="XPath 表达式" style="flex: 1; margin-left: 10px" />
                    <el-button type="danger" :icon="Delete" circle @click="removeXpathRule(index)" style="margin-left: 10px" />
                  </div>
                  <el-button type="primary" plain :icon="Plus" @click="addXpathRule" style="margin-top: 10px">添加字段规则</el-button>
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
            
            <div class="tab-content">
              <div class="section-group">
                <div class="section-title">渲染引擎配置</div>
                <el-row :gutter="20">
                  <el-col :span="12">
                    <el-form-item label="浏览器引擎">
                      <el-select v-model="form.engine" style="width: 100%">
                        <el-option label="Playwright (默认)" value="playwright" />
                        <el-option label="DrissionPage (过盾强)" value="drissionpage" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="加载等待条件">
                      <el-select v-model="form.wait_for" style="width: 100%">
                        <el-option label="Network Idle (推荐)" value="networkidle" />
                        <el-option label="Page Load (所有资源)" value="load" />
                        <el-option label="DOM Ready (HTML解析)" value="domcontentloaded" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="渲染超时 (s)">
                      <el-input-number 
                        :model-value="form.timeout / 1000" 
                        @update:model-value="val => form.timeout = val * 1000"
                        :min="5" 
                        :step="5" 
                        style="width: 100%" 
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="视口尺寸">
                      <div class="viewport-input">
                        <el-input-number v-model="form.viewport.width" :min="320" placeholder="宽" controls-position="right" style="width: 90px" />
                        <span class="sep">×</span>
                        <el-input-number v-model="form.viewport.height" :min="240" placeholder="高" controls-position="right" style="width: 90px" />
                      </div>
                    </el-form-item>
                  </el-col>
                </el-row>
              </div>

              <div class="section-group">
                <div class="section-title">特征与反检测</div>
                <div class="feature-settings">
                  <div class="feature-item">
                    <div class="feature-info">
                      <span class="feature-name">反检测模式 (Stealth)</span>
                      <span class="feature-desc">绕过大多数常见的机器人检测系统</span>
                    </div>
                    <el-switch v-model="form.stealth" />
                  </div>
                  <div class="feature-item">
                    <div class="feature-info">
                      <span class="feature-name">保存 HTML</span>
                      <span class="feature-desc">将完整的网页源码保存到数据库或 OSS</span>
                    </div>
                    <el-switch v-model="form.save_html" />
                  </div>
                  <div class="feature-item">
                    <div class="feature-info">
                      <span class="feature-name">自动截图</span>
                      <span class="feature-desc">保存网页快照用于调试或取证</span>
                    </div>
                    <el-switch v-model="form.screenshot" />
                  </div>
                  <div v-if="form.screenshot" class="feature-item">
                    <div class="feature-info">
                      <span class="feature-name">全屏快照</span>
                      <span class="feature-desc">捕获整个页面高度而不仅是可视区域</span>
                    </div>
                    <el-switch v-model="form.is_fullscreen" />
                  </div>
                  <div class="feature-item">
                    <div class="feature-info">
                      <span class="feature-name">屏蔽图片/媒体</span>
                      <span class="feature-desc">不加载图片和视频资源，加快抓取速度</span>
                    </div>
                    <el-switch v-model="form.block_images" />
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- 4. 网络与高级 -->
          <el-tab-pane name="advanced">
            <template #label>
              <span class="tab-label">
                <el-icon class="icon-advanced"><Setting /></el-icon>
                <span>高级设置</span>
              </span>
            </template>
            
            <div class="tab-content">
              <div class="section-group">
                <div class="section-title">接口拦截配置</div>
                <el-form-item label="拦截模式">
                  <el-select
                    v-model="form.intercept_apis"
                    multiple
                    filterable
                    allow-create
                    :reserve-keyword="false"
                    placeholder="输入匹配模式并按回车，例如: */api/* 或 *.json"
                    style="width: 100%"
                  >
                    <el-option label="所有 API (*api*)" value="*api*" />
                    <el-option label="JSON 数据 (*.json)" value="*.json" />
                  </el-select>
                  <div class="input-tip">使用 * 作为通配符。开启后，系统将捕获并保存匹配接口的响应内容。</div>
                </el-form-item>

                <el-form-item label="拦截后行为">
                  <div class="switch-container">
                    <el-switch v-model="form.intercept_continue" />
                    <span class="switch-tip">{{ form.intercept_continue ? '继续加载 (正常运行)' : '拦截停止 (节省资源)' }}</span>
                  </div>
                </el-form-item>
              </div>

              <div class="section-group">
                <div class="section-title">代理配置</div>
                <el-form-item label="代理服务器">
                  <el-input v-model="form.proxy.server" placeholder="http://proxy.example.com:8080" clearable />
                </el-form-item>
                
                <template v-if="form.proxy.server">
                  <el-row :gutter="20" v-if="form.engine !== 'drissionpage'">
                    <el-col :span="12">
                      <el-form-item label="用户名">
                        <el-input v-model="form.proxy.username" placeholder="可选" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="密码">
                        <el-input v-model="form.proxy.password" show-password placeholder="可选" />
                      </el-form-item>
                    </el-col>
                  </el-row>
                  
                  <el-alert
                    v-if="form.engine === 'drissionpage'"
                    title="代理说明"
                    type="info"
                    description="DrissionPage 引擎目前仅支持无账密代理（IP:Port 格式）。如需使用账密认证代理，请切换至 Playwright 引擎。"
                    show-icon
                    :closable="false"
                    class="proxy-warning"
                  />
                </template>
              </div>
            </div>
          </el-tab-pane>

          <!-- 5. 执行选项 -->
          <el-tab-pane name="cache">
            <template #label>
              <span class="tab-label">
                <el-icon class="icon-execution"><Timer /></el-icon>
                <span>执行选项</span>
              </span>
            </template>
            
            <div class="tab-content">
              <div class="section-group">
                <div class="section-title">缓存与去重配置</div>
                <el-form-item label="数据缓存">
                  <div class="switch-container">
                    <el-switch v-model="form.cache_config.enabled" />
                    <span class="switch-tip">{{ form.cache_config.enabled ? '开启 (有效期内相同 URL 不再重复抓取)' : '关闭 (每次请求都实时抓取)' }}</span>
                  </div>
                </el-form-item>

                <el-form-item label="缓存有效期" v-if="form.cache_config.enabled">
                  <div class="ttl-input">
                    <el-input-number v-model="form.cache_config.ttl" :min="60" :step="60" style="width: 150px" />
                    <span class="unit">秒</span>
                    <el-button-group class="ml-4">
                      <el-button size="small" @click="form.cache_config.ttl = 3600">1小时</el-button>
                      <el-button size="small" @click="form.cache_config.ttl = 86400">1天</el-button>
                      <el-button size="small" @click="form.cache_config.ttl = 604800">7天</el-button>
                    </el-button-group>
                  </div>
                  <div class="input-tip mt-2">在此时间内，相同的抓取请求将直接返回缓存结果。</div>
                </el-form-item>

                <el-alert
                  title="去重说明"
                  type="info"
                  :closable="false"
                  show-icon
                  class="mt-4"
                >
                  <template #default>
                    <p>去重机制基于 URL 和抓取参数生成的唯一键。如果目标网站内容更新频繁，请缩短有效期或关闭去重。</p>
                  </template>
                </el-alert>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">保存配置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, MagicStick, Connection, Search, Timer, Monitor, Setting, Warning } from '@element-plus/icons-vue'
import { getRules, createRule, updateRule, deleteRule } from '@/api'

const rules = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref(null)
const activeTab = ref('basic')

const llmFieldOptions = [
  { label: '标题', value: 'title' },
  { label: '正文', value: 'content' },
  { label: '作者', value: 'author' },
  { label: '发布时间', value: 'publish_time' },
  { label: '关键词', value: 'keywords' },
  { label: '摘要', value: 'summary' },
  { label: '价格', value: 'price' },
  { label: '商品名称', value: 'product_name' },
  { label: '商品描述', value: 'description' },
  { label: '联系方式', value: 'contact' },
  { label: '公司名称', value: 'company_name' },
  { label: '规格参数', value: 'specifications' }
]
const selectedLlmFields = ref(['title', 'content'])
const xpathRules = ref([{ field: '', xpath: '' }])

const form = reactive({
  domain: '',
  parser_type: 'gne',
  parser_config: { mode: 'detail' },
  
  // 浏览器特征配置
  engine: 'playwright',
  wait_for: 'networkidle',
  timeout: 30000,
  viewport: { width: 1280, height: 720 },
  stealth: true,
  save_html: true,
  screenshot: false,
  is_fullscreen: false,
  block_images: false,
  
  // 高级配置
  storage_type: 'mongo',
  mongo_collection: '',
  oss_path: '',
  intercept_apis: [],
  intercept_continue: true,
  proxy: { server: '', username: '', password: '' },
  
  cache_config: { enabled: true, ttl: 3600 },
  cookies: '',
  description: '',
  is_active: true,
  priority: 5
})

const formRules = {
  domain: [{ required: true, message: '请输入目标域名', trigger: 'blur' }],
  parser_type: [{ required: true, message: '请选择解析模式', trigger: 'change' }]
}

const fetchRules = async () => {
  loading.value = true
  try {
    const data = await getRules()
    rules.value = data
  } catch (error) {
    ElMessage.error('获取规则失败')
  } finally {
    loading.value = false
  }
}

const handleAdd = () => {
  isEdit.value = false
  activeTab.value = 'basic'
  Object.assign(form, {
    domain: '',
    parser_type: 'gne',
    parser_config: { mode: 'detail' },
    
    // 浏览器特征配置
    engine: 'playwright',
    wait_for: 'networkidle',
    timeout: 30000,
    viewport: { width: 1280, height: 720 },
    stealth: true,
    save_html: true,
    screenshot: false,
    is_fullscreen: false,
    block_images: false,
    
    // 高级配置
    storage_type: 'mongo',
    mongo_collection: '',
    oss_path: '',
    intercept_apis: [],
    intercept_continue: true,
    proxy: { server: '', username: '', password: '' },
    
    cache_config: { enabled: true, ttl: 3600 },
    cookies: '',
    description: '',
    is_active: true,
    priority: 5
  })
  selectedLlmFields.value = ['title', 'content']
  form.parser_config = { fields: ['title', 'content'] }
  xpathRules.value = [{ field: '', xpath: '' }]
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  activeTab.value = 'basic'
  
  // 深度克隆行数据，避免引用问题
  const rowData = JSON.parse(JSON.stringify(row))
  
  // 确保嵌套对象存在
  if (!rowData.viewport) rowData.viewport = { width: 1280, height: 720 }
  if (!rowData.proxy) rowData.proxy = { server: '', username: '', password: '' }
  if (!rowData.intercept_apis) rowData.intercept_apis = []
  if (rowData.intercept_continue === undefined) rowData.intercept_continue = true
  if (rowData.storage_type === undefined) rowData.storage_type = 'mongo'
  if (rowData.mongo_collection === undefined) rowData.mongo_collection = ''
  if (rowData.oss_path === undefined) rowData.oss_path = ''
  
  Object.assign(form, rowData)
  
  if (!form.cache_config) {
    form.cache_config = { enabled: true, ttl: 3600 }
  }

  if (form.parser_type === 'llm') {
    selectedLlmFields.value = form.parser_config.fields || []
  } else if (form.parser_type === 'xpath') {
    const rulesData = form.parser_config.rules || {}
    xpathRules.value = Object.entries(rulesData).map(([field, xpath]) => ({ field, xpath }))
    if (xpathRules.value.length === 0) {
      xpathRules.value = [{ field: '', xpath: '' }]
    }
  }
  
  dialogVisible.value = true
}

const handleDelete = (row) => {
  ElMessageBox.confirm('确定要删除这条规则吗？', '提示', {
    type: 'warning'
  }).then(async () => {
    try {
      await deleteRule(row.id)
      ElMessage.success('删除成功')
      fetchRules()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

const toggleStatus = async (row) => {
  try {
    await updateRule(row.id, { is_active: row.is_active })
    ElMessage.success('状态更新成功')
  } catch (error) {
    row.is_active = !row.is_active
    ElMessage.error('状态更新失败')
  }
}

const applyLlmPreset = (type) => {
  const presets = {
    article: ['title', 'content', 'author', 'publish_time'],
    product: ['product_name', 'price', 'description', 'specifications'],
    contact: ['company_name', 'phone', 'email', 'address']
  }
  if (presets[type]) {
    selectedLlmFields.value = [...presets[type]]
    handleLlmFieldsChange()
    ElMessage.success('已应用模板')
  }
}

const handleLlmFieldsChange = () => {
  form.parser_config = { fields: selectedLlmFields.value }
}

const addXpathRule = () => {
  xpathRules.value.push({ field: '', xpath: '' })
}

const removeXpathRule = (index) => {
  xpathRules.value.splice(index, 1)
}

const submitForm = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      if (form.parser_type === 'xpath') {
        const rulesObj = {}
        xpathRules.value.forEach(item => {
          if (item.field && item.xpath) {
            rulesObj[item.field] = item.xpath
          }
        })
        form.parser_config = { rules: rulesObj }
      }
      
      submitting.value = true
      try {
        if (isEdit.value) {
          await updateRule(form.id, form)
          ElMessage.success('更新成功')
        } else {
          await createRule(form)
          ElMessage.success('添加成功')
        }
        dialogVisible.value = false
        fetchRules()
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || '提交失败')
      } finally {
        submitting.value = false
      }
    }
  })
}

const getParserTypeTag = (type) => {
  const map = {
    'gne': 'success',
    'llm': 'warning',
    'xpath': 'primary'
  }
  return map[type] || 'info'
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString()
}

const formatDuration = (seconds) => {
  if (seconds < 60) return `${seconds}秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}小时`
  return `${Math.floor(seconds / 86400)}天`
}

onMounted(() => {
  fetchRules()
})
</script>

<style scoped>
.storage-input-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.input-label-tip {
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
}

.storage-path-preview {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
  background: #f8fafc;
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px dashed #e2e8f0;
}

.storage-path-preview code {
  background: #fff;
  padding: 2px 6px;
  border-radius: 4px;
  color: #3b82f6;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  border: 1px solid #e2e8f0;
}
.rules-container {
  padding: 20px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.subtitle {
  color: #909399;
  font-size: 14px;
  margin: 5px 0 0 0;
}
.table-card {
  margin-bottom: 20px;
  border-radius: 12px;
}

:deep(.el-table__header .el-table__cell) {
  background-color: #f8fafc;
  color: #475569;
  font-weight: 600;
  height: 50px;
}

:deep(.el-table__row) {
  transition: background-color 0.2s;
}

:deep(.el-table__row:hover > td) {
  background-color: #f1f5f9 !important;
}
/* Dialog & Tabs Styles */
.config-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.config-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 0 20px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.config-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  padding: 4px 0;
}

.tab-content {
  padding: 20px 10px;
  max-height: 500px;
  overflow-y: auto;
}

/* Icons Colors */
.icon-basic { color: #3b82f6; }
.icon-parser { color: #8b5cf6; }
.icon-browser { color: #10b981; }
.icon-advanced { color: #6366f1; }
.icon-execution { color: #f59e0b; }

.input-tip {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
  line-height: 1.4;
}

.switch-container {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 32px;
}

.switch-tip {
  font-size: 13px;
  color: #64748b;
}

/* Viewport Input */
.viewport-input {
  display: flex;
  align-items: center;
  gap: 8px;
}

.viewport-input .sep {
  color: #909399;
  font-weight: bold;
}

.ttl-input {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ttl-input .unit {
  color: #606266;
}

.ml-4 {
  margin-left: 16px;
}

.mt-2 {
  margin-top: 8px;
}

/* Feature Settings */
.feature-settings {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.feature-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  transition: all 0.2s;
}

.feature-item:hover {
  border-color: #cbd5e1;
  background: #f1f5f9;
}

.feature-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.feature-name {
  font-size: 14px;
  font-weight: 500;
  color: #1e293b;
}

.feature-desc {
  font-size: 12px;
  color: #64748b;
}

.section-group {
  background: #f8faff;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
  border: 1px solid #eef2f7;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2d3d;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-title::before {
  content: '';
  width: 4px;
  height: 14px;
  background: #409eff;
  border-radius: 2px;
}

/* Parser Styles */
.parser-config-area {
  background: #f8fafc;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  margin-top: 10px;
}

.parser-presets {
  margin-bottom: 15px;
  display: flex;
  align-items: center;
}

.preset-label {
  font-size: 13px;
  color: #64748b;
  margin-right: 10px;
}

.xpath-rule-item {
  display: flex;
  margin-bottom: 10px;
}

.mt-4 {
  margin-top: 16px;
}

.llm-helper-alert {
  margin-top: 16px;
}

.alert-content-mini {
  font-size: 13px;
}

.helper-text {
  margin: 0 0 8px 0;
}

.format-example-mini {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(0, 0, 0, 0.05);
  padding: 4px 8px;
  border-radius: 4px;
}

.example-label {
  font-weight: bold;
  color: #475569;
}

code {
  color: #e11d48;
  font-family: monospace;
}

.text-danger {
  color: #ef4444;
}
</style>
