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
            <el-button type="success" plain @click="openBatchScrapeDialog">
              <el-icon><Document /></el-icon> 批量导入
            </el-button>
            <el-button type="primary" @click="openSingleScrapeDialog">
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

        <el-table-column label="执行统计" width="150">
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

        <el-table-column label="时间轨迹" width="220">
          <template #default="{ row }">
            <div class="timeline-mini">
              <div class="time-row">
                <span class="dot create"></span>
                <span class="label">创建:</span>
                <span class="time">{{ formatDate(row.created_at) }}</span>
              </div>
              <div class="time-row" v-if="row.completed_at">
                <span class="dot complete"></span>
                <span class="label">完成:</span>
                <span class="time">{{ formatDate(row.completed_at) }}</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip content="查看详情" placement="top">
                <el-button circle size="small" :icon="View" @click="viewTask(row)" />
              </el-tooltip>
              
              <el-tooltip content="获取 API 配置" placement="top">
                <el-button 
                  circle 
                  size="small" 
                  type="info" 
                  :icon="Promotion" 
                  @click="showApiConfig(row)" 
                />
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

              <el-tooltip content="复制任务" placement="top">
                <el-button 
                  circle 
                  size="small" 
                  type="primary" 
                  :icon="CopyDocument" 
                  @click="copyTask(row)"
                  class="copy-task-btn"
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
      width="800px" 
      destroy-on-close 
      top="8vh"
      class="config-dialog"
    >
      <el-form :model="scrapeForm" label-width="100px" label-position="top">
        <el-tabs v-model="activeConfigTab" class="config-tabs">
          <!-- 1. 基础配置 -->
          <el-tab-pane name="basic">
            <template #label>
              <span class="tab-label">
                <el-icon class="icon-basic"><Link /></el-icon>
                <span>基础目标</span>
              </span>
            </template>
            
            <div class="tab-content">
              <div class="section-header">
                <div class="header-extra">
                  <el-radio-group v-model="submitMode" size="small">
                    <el-radio-button label="single">单条任务</el-radio-button>
                    <el-radio-button label="batch">批量导入</el-radio-button>
                  </el-radio-group>
                </div>
              </div>

              <div v-if="submitMode === 'single'">
                <el-form-item label="目标 URL" required>
                  <el-input v-model="scrapeForm.url" placeholder="请输入抓取地址，例如: https://example.com" clearable>
                    <template #prefix><el-icon class="icon-link"><Connection /></el-icon></template>
                  </el-input>
                </el-form-item>
                
                <el-form-item label="Cookies">
                    <div class="cookies-input-wrapper">
                      <el-input
                        v-model="scrapeForm.params.cookies"
                        type="textarea"
                        :rows="3"
                        placeholder="输入 Cookies 字符串或 JSON 格式，如：key1=value1; key2=value2"
                      />
                      <div class="cookies-tip" v-if="matchedCookies">
                        <el-icon class="success-icon"><CircleCheckFilled /></el-icon>
                        <span>已自动加载该域名的默认 Cookies 配置</span>
                      </div>
                    </div>
                </el-form-item>
              </div>
              
              <div v-else class="batch-input-area">
                <el-tabs v-model="batchMode" class="compact-tabs">
                  <el-tab-pane label="文本输入" name="text">
                    <el-form-item label="URL 列表 (每行一个)">
                      <el-input
                        v-model="batchUrlsText"
                        type="textarea"
                        :rows="6"
                        placeholder="https://example.com/1&#10;https://example.com/2"
                      />
                    </el-form-item>
                  </el-tab-pane>
                  <el-tab-pane label="文件上传" name="file">
                    <el-form-item label="上传 TXT/CSV 文件">
                      <el-upload
                        class="bento-upload"
                        drag
                        action="#"
                        :auto-upload="false"
                        :on-change="handleFileChange"
                        :on-remove="handleFileRemove"
                        :limit="1"
                        accept=".txt,.csv"
                      >
                        <el-icon class="el-icon--upload icon-upload"><UploadFilled /></el-icon>
                        <div class="el-upload__text">拖拽文件或 <em>点击上传</em></div>
                      </el-upload>
                    </el-form-item>
                  </el-tab-pane>
                </el-tabs>
                <div class="batch-count-tip" v-if="batchUrlCount > 0">
                  已识别 <span class="count">{{ batchUrlCount }}</span> 个有效 URL
                </div>
              </div>

              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="任务优先级">
                    <el-select v-model="scrapeForm.priority" style="width: 100%">
                      <el-option label="最高优先级 (10)" :value="10" />
                      <el-option label="普通优先级 (5)" :value="5" />
                      <el-option label="最低优先级 (1)" :value="1" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="数据缓存">
                    <div class="switch-container">
                      <el-switch v-model="scrapeForm.cache.enabled" />
                      <span class="switch-tip">{{ scrapeForm.cache.enabled ? '开启 (节省资源)' : '关闭 (实时抓取)' }}</span>
                    </div>
                  </el-form-item>
                </el-col>
              </el-row>
              
              <el-form-item label="缓存有效期 (TTL/秒)" v-if="scrapeForm.cache.enabled">
                <el-input-number v-model="scrapeForm.cache.ttl" :min="60" :step="60" style="width: 100%" />
              </el-form-item>
            </div>
          </el-tab-pane>

          <!-- 2. 解析配置 -->
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
                  <template #header>
                    <div class="dropdown-header">选择要应用的解析规则</div>
                  </template>
                  <template #footer>
                    <div class="dropdown-footer">点击规则可直接应用配置</div>
                  </template>
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

              <el-form-item label="解析模式">
                <el-radio-group v-model="scrapeForm.params.parser" size="default">
                  <el-radio-button label="">不解析</el-radio-button>
                  <el-radio-button label="gne">智能正文 (GNE)</el-radio-button>
                  <el-radio-button label="llm">大模型提取 (LLM)</el-radio-button>
                  <el-radio-button label="xpath">自定义规则 (XPath)</el-radio-button>
                </el-radio-group>
              </el-form-item>

              <div v-if="scrapeForm.params.parser === 'gne'" class="parser-config-area">
                <el-alert title="GNE 模式" type="info" :closable="false" show-icon description="适用于新闻、博客等文章类页面，自动提取标题、作者、发布时间、正文和图片。" />
              </div>

              <div v-if="scrapeForm.params.parser === 'llm'" class="parser-config-area">
                <div class="parser-presets">
                  <span class="preset-label">常用模板:</span>
                  <el-button-group>
                    <el-button size="small" plain @click="applyLlmPreset('article')">文章提取</el-button>
                    <el-button size="small" plain @click="applyLlmPreset('product')">商品详情</el-button>
                    <el-button size="small" plain @click="applyLlmPreset('contact')">联系方式</el-button>
                  </el-button-group>
                </div>
                <el-form-item class="mt-4">
                  <template #label>
                    <div class="label-with-help">
                      <span>目标提取字段</span>
                      <el-tooltip content="大模型将按照选定的键名生成 JSON 结果" placement="top">
                        <el-icon class="help-icon"><QuestionFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </template>
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
                      <p class="api-warning">
                        <el-icon><Warning /></el-icon>
                        注意：使用此功能前，请确保已在后端正确配置大模型 API 设置。
                      </p>
                    </div>
                  </template>
                </el-alert>
              </div>

              <div v-if="scrapeForm.params.parser === 'xpath'" class="parser-config-area">
                <div class="xpath-rules-header">
                  <span>XPath 规则配置</span>
                  <el-button type="primary" link :icon="Plus" @click="addXpathRule">添加规则</el-button>
                </div>
                <div v-for="(rule, index) in xpathRules" :key="index" class="xpath-rule-row">
                  <el-input v-model="rule.field" placeholder="字段名" style="width: 120px" />
                  <el-input v-model="rule.path" placeholder="XPath 表达式，如: //h1/text()" style="flex: 1" />
                  <el-button 
                    type="danger" 
                    circle
                    plain
                    :icon="Delete" 
                    @click="removeXpathRule(index)" 
                    :disabled="xpathRules.length <= 1"
                    class="rule-delete-btn"
                  />
                </div>
              </div>
              
              <div v-if="scrapeForm.params.parser === 'intercept_apis'" class="parser-config-area">
                <div class="xpath-rules-header">
                  <span>拦截api配置</span>
                  <el-button type="primary" link :icon="Plus" @click="addXpathRule">添加规则</el-button>
                </div>
                <div v-for="(rule, index) in xpathRules" :key="index" class="xpath-rule-row">
                  <el-input v-model="rule.path" placeholder="XPath 表达式，如: //h1/text()" style="flex: 1" />
                  <el-button 
                    type="danger" 
                    circle
                    plain
                    :icon="Delete" 
                    @click="removeXpathRule(index)" 
                    :disabled="xpathRules.length <= 1"
                    class="rule-delete-btn"
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
            
            <div class="tab-content">
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="加载等待条件">
                    <el-select v-model="scrapeForm.params.wait_for" style="width: 100%">
                      <el-option label="Network Idle (推荐)" value="networkidle" />
                      <el-option label="Page Load (所有资源)" value="load" />
                      <el-option label="DOM Ready (HTML解析)" value="domcontentloaded" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="渲染超时 (s)">
                    <el-input-number 
                      :model-value="scrapeForm.params.timeout / 1000" 
                      @update:model-value="val => scrapeForm.params.timeout = val * 1000"
                      :min="5" 
                      :step="5" 
                      style="width: 100%" 
                    />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-form-item label="视口尺寸 (分辨率)">
                <div class="viewport-input">
                  <el-input-number v-model="scrapeForm.params.viewport.width" :min="320" placeholder="宽度" controls-position="right" />
                  <span class="sep">×</span>
                  <el-input-number v-model="scrapeForm.params.viewport.height" :min="240" placeholder="高度" controls-position="right" />
                </div>
              </el-form-item>

              <div class="feature-settings">
                <div class="feature-item">
                  <div class="feature-info">
                    <span class="feature-name">反检测模式 (Stealth)</span>
                    <span class="feature-desc">绕过大多数常见的机器人检测系统</span>
                  </div>
                  <el-switch v-model="scrapeForm.params.stealth" />
                </div>
                <div class="feature-item">
                  <div class="feature-info">
                    <span class="feature-name">自动截图</span>
                    <span class="feature-desc">保存网页快照用于调试或取证</span>
                  </div>
                  <el-switch v-model="scrapeForm.params.screenshot" />
                </div>
                <div class="feature-item" v-if="scrapeForm.params.screenshot">
                  <div class="feature-info">
                    <span class="feature-name">全屏快照</span>
                    <span class="feature-desc">捕获整个页面高度而不仅是可视区域</span>
                  </div>
                  <el-switch v-model="scrapeForm.params.is_fullscreen" />
                </div>
                <div class="feature-item">
                  <div class="feature-info">
                    <span class="feature-name">屏蔽图片/媒体</span>
                    <span class="feature-desc">不加载图片和视频资源，加快抓取速度</span>
                  </div>
                  <el-switch v-model="scrapeForm.params.block_images" />
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
              <div class="section-title">接口拦截配置</div>
              <el-form-item label="拦截接口 URL 模式">
                <el-select
                v-model="scrapeForm.params.intercept_apis"
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

              <el-form-item label="拦截后继续请求">
                <div class="switch-container">
                  <el-switch v-model="scrapeForm.params.intercept_continue" />
                  <span class="switch-tip">{{ scrapeForm.params.intercept_continue ? '开启 (正常加载页面)' : '关闭 (拦截并停止, 节省流量)' }}</span>
                </div>
              </el-form-item>

              <el-divider />

              <div class="section-title">代理配置</div>
              <el-form-item label="代理服务器">
                <el-input v-model="scrapeForm.params.proxy.server" placeholder="http://proxy.example.com:8080" clearable />
              </el-form-item>
              <el-row :gutter="20" v-if="scrapeForm.params.proxy.server">
                <el-col :span="12">
                  <el-form-item label="用户名">
                    <el-input v-model="scrapeForm.params.proxy.username" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="密码">
                    <el-input v-model="scrapeForm.params.proxy.password" show-password />
                  </el-form-item>
                </el-col>
              </el-row>

              <div class="section-title">API 拦截配置</div>
              <el-form-item label="拦截 API 模式">
                <el-input
                  v-model="interceptApisText"
                  type="textarea"
                  :rows="4"
                  placeholder="输入 API 路径模式，每行一个，例如：\n/api/data\n/users/*\n/products/[0-9]+"
                />
                <div class="input-tip">支持通配符 * 和正则表达式</div>
              </el-form-item>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showScrapeDialog = false">取 消</el-button>
          <el-button type="primary" @click="submitTask" :loading="loading" class="submit-btn">
            立即开始抓取
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
                    <p><strong>Headers: </strong> {{ req.headers }}</p>
                    <div class="json-box">
                      <strong>响应内容:</strong>
                      <pre>{{ formatJSON(req.body) }}</pre>
                    </div>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </el-tab-pane>

          <el-tab-pane label="截图预览" name="screenshot" v-if="currentTask.status === 'success' && currentTask.params?.screenshot">
            <div class="screenshot-container" v-loading="!currentTask.result?.screenshot">
              <el-image 
                v-if="currentTask.result?.screenshot"
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
              <el-empty v-else description="正在加载截图..." />
            </div>
          </el-tab-pane>

          <el-tab-pane label="HTML 源码" name="html" v-if="currentTask.status === 'success'">
            <div class="html-container" v-loading="!currentTask.result?.html">
              <pre v-if="currentTask.result?.html"><code>{{ currentTask.result.html }}</code></pre>
              <el-empty v-else description="正在加载源码..." />
            </div>
          </el-tab-pane>

          <el-tab-pane label="解析数据" name="parsed" v-if="currentTask.result?.parsed_data">
            <div class="json-box">
              <pre>{{ formatJSON(currentTask.result.parsed_data) }}</pre>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>

    <!-- 编辑任务对话框 -->
    <el-dialog 
      v-model="showEditDialog" 
      title="编辑抓取任务" 
      width="800px" 
      destroy-on-close 
      top="8vh"
      class="config-dialog"
    >
      <el-form :model="editForm" label-width="100px" label-position="top">
        <el-tabs v-model="activeEditConfigTab" class="config-tabs">
          <!-- 1. 基础配置 -->
          <el-tab-pane name="basic">
            <template #label>
              <span class="tab-label">
                <el-icon class="icon-basic"><Link /></el-icon>
                <span>基础目标</span>
              </span>
            </template>
            
            <div class="tab-content">
              <div class="section-header">
                <div class="header-extra">
                  <el-radio-group v-model="editSubmitMode" size="small">
                    <el-radio-button label="single">单条任务</el-radio-button>
                  </el-radio-group>
                </div>
              </div>

              <div v-if="editSubmitMode === 'single'">
                <el-form-item label="目标 URL" required>
                  <el-input v-model="editForm.url" placeholder="请输入抓取地址，例如: https://example.com" clearable>
                    <template #prefix><el-icon class="icon-link"><Connection /></el-icon></template>
                  </el-input>
                </el-form-item>
                
                <el-form-item label="Cookies">
                    <div class="cookies-input-wrapper">
                      <el-input
                        v-model="editForm.params.cookies"
                        type="textarea"
                        :rows="3"
                        placeholder="输入 Cookies 字符串或 JSON 格式，如：key1=value1; key2=value2"
                      />
                    </div>
                </el-form-item>
              </div>
              
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="任务优先级">
                    <el-select v-model="editForm.priority" style="width: 100%">
                      <el-option label="最高优先级 (10)" :value="10" />
                      <el-option label="普通优先级 (5)" :value="5" />
                      <el-option label="最低优先级 (1)" :value="1" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="数据缓存">
                    <div class="switch-container">
                      <el-switch v-model="editForm.cache.enabled" />
                      <span class="switch-tip">{{ editForm.cache.enabled ? '开启 (节省资源)' : '关闭 (实时抓取)' }}</span>
                    </div>
                  </el-form-item>
                </el-col>
              </el-row>
              
              <el-form-item label="缓存有效期 (TTL/秒)" v-if="editForm.cache.enabled">
                <el-input-number v-model="editForm.cache.ttl" :min="60" :step="60" style="width: 100%" />
              </el-form-item>
            </div>
          </el-tab-pane>

          <!-- 2. 解析配置 -->
          <el-tab-pane name="parser">
            <template #label>
              <span class="tab-label">
                <el-icon class="icon-parser"><MagicStick /></el-icon>
                <span>内容解析</span>
              </span>
            </template>
            
            <div class="tab-content">
              <el-form-item label="解析模式">
                <el-radio-group v-model="editForm.params.parser" size="default">
                  <el-radio-button label="">不解析</el-radio-button>
                  <el-radio-button label="gne">智能正文 (GNE)</el-radio-button>
                  <el-radio-button label="llm">大模型提取 (LLM)</el-radio-button>
                  <el-radio-button label="xpath">自定义规则 (XPath)</el-radio-button>
                </el-radio-group>
              </el-form-item>

              <div v-if="editForm.params.parser === 'gne'" class="parser-config-area">
                <el-alert title="GNE 模式" type="info" :closable="false" show-icon description="适用于新闻、博客等文章类页面，自动提取标题、作者、发布时间、正文和图片。" />
              </div>

              <div v-if="editForm.params.parser === 'llm'" class="parser-config-area">
                <div class="parser-presets">
                  <span class="preset-label">常用模板:</span>
                  <el-button-group>
                    <el-button size="small" plain @click="applyEditLlmPreset('article')">文章提取</el-button>
                    <el-button size="small" plain @click="applyEditLlmPreset('product')">商品详情</el-button>
                    <el-button size="small" plain @click="applyEditLlmPreset('contact')">联系方式</el-button>
                  </el-button-group>
                </div>
                <el-form-item class="mt-4">
                  <template #label>
                    <div class="label-with-help">
                      <span>目标提取字段</span>
                      <el-tooltip content="大模型将按照选定的键名生成 JSON 结果" placement="top">
                        <el-icon class="help-icon"><QuestionFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </template>
                  <el-select
                    v-model="editSelectedLlmFields"
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
                      <p class="api-warning">
                        <el-icon><Warning /></el-icon>
                        注意：使用此功能前，请确保已在后端正确配置大模型 API 设置。
                      </p>
                    </div>
                  </template>
                </el-alert>
              </div>

              <div v-if="editForm.params.parser === 'xpath'" class="parser-config-area">
                <div class="xpath-rules-header">
                  <span>XPath 规则配置</span>
                  <el-button type="primary" link :icon="Plus" @click="addEditXpathRule">添加规则</el-button>
                </div>
                <div v-for="(rule, index) in editXpathRules" :key="index" class="xpath-rule-row">
                  <el-input v-model="rule.field" placeholder="字段名" style="width: 120px" />
                  <el-input v-model="rule.path" placeholder="XPath 表达式，如: //h1/text()" style="flex: 1" />
                  <el-button 
                    type="danger" 
                    circle
                    plain
                    :icon="Delete" 
                    @click="removeEditXpathRule(index)" 
                    :disabled="editXpathRules.length <= 1"
                    class="rule-delete-btn"
                  />
                </div>
              </div>
              
              <div v-if="editForm.params.parser === 'intercept_apis'" class="parser-config-area">
                <div class="xpath-rules-header">
                  <span>拦截api配置</span>
                  <el-button type="primary" link :icon="Plus" @click="addEditXpathRule">添加规则</el-button>
                </div>
                <div v-for="(rule, index) in editXpathRules" :key="index" class="xpath-rule-row">
                  <el-input v-model="rule.path" placeholder="XPath 表达式，如: //h1/text()" style="flex: 1" />
                  <el-button 
                    type="danger" 
                    circle
                    plain
                    :icon="Delete" 
                    @click="removeEditXpathRule(index)" 
                    :disabled="editXpathRules.length <= 1"
                    class="rule-delete-btn"
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
            
            <div class="tab-content">
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="加载等待条件">
                    <el-select v-model="editForm.params.wait_for" style="width: 100%">
                      <el-option label="Network Idle (推荐)" value="networkidle" />
                      <el-option label="Page Load (所有资源)" value="load" />
                      <el-option label="DOM Ready (HTML解析)" value="domcontentloaded" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="渲染超时 (ms)">
                    <el-input-number v-model="editForm.params.timeout" :min="5000" :step="5000" style="width: 100%" />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-form-item label="视口尺寸 (分辨率)">
                <div class="viewport-input">
                  <el-input-number v-model="editForm.params.viewport.width" :min="320" placeholder="宽度" controls-position="right" />
                  <span class="sep">×</span>
                  <el-input-number v-model="editForm.params.viewport.height" :min="240" placeholder="高度" controls-position="right" />
                </div>
              </el-form-item>

              <div class="feature-settings">
                <div class="feature-item">
                  <div class="feature-info">
                    <span class="feature-name">反检测模式 (Stealth)</span>
                    <span class="feature-desc">绕过大多数常见的机器人检测系统</span>
                  </div>
                  <el-switch v-model="editForm.params.stealth" />
                </div>
                <div class="feature-item">
                  <div class="feature-info">
                    <span class="feature-name">自动截图</span>
                    <span class="feature-desc">保存网页快照用于调试或取证</span>
                  </div>
                  <el-switch v-model="editForm.params.screenshot" />
                </div>
                <div class="feature-item" v-if="editForm.params.screenshot">
                  <div class="feature-info">
                    <span class="feature-name">全屏快照</span>
                    <span class="feature-desc">捕获整个页面高度而不仅是可视区域</span>
                  </div>
                  <el-switch v-model="editForm.params.is_fullscreen" />
                </div>
                <div class="feature-item">
                  <div class="feature-info">
                    <span class="feature-name">屏蔽图片/媒体</span>
                    <span class="feature-desc">不加载图片和视频资源，加快抓取速度</span>
                  </div>
                  <el-switch v-model="editForm.params.block_images" />
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
              <div class="section-title">代理配置</div>
              <el-form-item label="代理服务器">
                <el-input v-model="editForm.params.proxy.server" placeholder="http://proxy.example.com:8080" clearable />
              </el-form-item>
              <el-row :gutter="20" v-if="editForm.params.proxy.server">
                <el-col :span="12">
                  <el-form-item label="用户名">
                    <el-input v-model="editForm.params.proxy.username" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="密码">
                    <el-input v-model="editForm.params.proxy.password" show-password />
                  </el-form-item>
                </el-col>
              </el-row>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showEditDialog = false">取 消</el-button>
          <el-button type="primary" @click="submitEditTask" :loading="loading" class="submit-btn">
            保存任务
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- API 配置对话框 -->
    <el-dialog v-model="showApiConfigDialog" title="API 调用配置" width="700px" top="10vh">
      <div class="api-config-content">
        <el-alert
          title="使用说明"
          type="info"
          description="以下是发起该抓取任务所需的完整 API 请求体。您可以调用 /api/v1/scrape/async (异步) 或 /api/v1/scrape/ (同步) 接口。"
          show-icon
          :closable="false"
          class="api-config-alert"
          style="margin-bottom: 15px;"
        />
        
        <div class="config-actions">
          <div class="api-endpoint">
            <el-tag effect="dark">POST</el-tag>
            <code class="endpoint-path">/api/v1/scrape/async</code>
          </div>
          <el-button type="primary" :icon="CopyDocument" @click="copyToClipboard(apiConfigJson)">
            复制 JSON
          </el-button>
        </div>

        <div class="json-box api-json-box">
          <pre><code>{{ apiConfigJson }}</code></pre>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Picture, WarningFilled, DeleteFilled, Delete, Setting, Connection, Monitor, Timer, Search, CopyDocument, View, VideoPlay, Link, Lock, Promotion, QuestionFilled, Cpu, Right, Document, UploadFilled, MagicStick, Warning, ArrowDown } from '@element-plus/icons-vue'
import { getTasks, deleteTask as deleteTaskApi, getTask, scrapeAsync, retryTask, deleteTasksBatch, scrapeBatch, getRulesByDomain } from '../api'
import { watch } from 'vue'
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
const showApiConfigDialog = ref(false)
const showEditDialog = ref(false)
const apiConfigJson = ref('')
const activeConfigTab = ref('basic')
const activeEditConfigTab = ref('basic')
const matchedRules = ref([])
const matchedCookies = ref(false)
let lastCheckedDomain = ''

// 编辑任务相关状态
const editSubmitMode = ref('single')
const editSelectedLlmFields = ref(['title', 'content'])
const editXpathRules = ref([
  { field: 'title', path: '//h1' },
  { field: 'content', path: "//div[@class='article-body']" }
])
const currentEditTaskId = ref('')

const editForm = ref({
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
      cookies: '',
      stealth: true,
  parser: '',
  parser_config: {
    fields: ['title', 'content']
  },
  intercept_apis: [],
    intercept_continue: false
  },
  cache: {
    enabled: true,
    ttl: 3600
  },
  priority: 1
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
  scrapeForm.value.params.parser = rule.parser_type
  if (rule.parser_type === 'llm') {
    selectedLlmFields.value = rule.parser_config.fields || []
  } else if (rule.parser_type === 'xpath') {
    const rules = rule.parser_config.rules || {}
    xpathRules.value = Object.entries(rules).map(([field, path]) => ({ field, path }))
  }
  if (!silent) {
    ElMessage.success(`已应用 ${rule.domain} 的解析配置`)
  }
}

// 监听标签页切换
watch(activeConfigTab, async (newTab) => {
  if (newTab === 'parser' && scrapeForm.value.url && scrapeForm.value.url.startsWith('http')) {
    try {
      const urlObj = new URL(scrapeForm.value.url)
      const domain = urlObj.hostname
      
      // 如果域名没变且已经匹配过规则，则不再自动加载（防止覆盖人工修改）
      // 如果已经在 URL 监听器里加载过了，这里也不再加载
      if (domain === lastCheckedDomain && matchedRules.value.length > 0) {
        // 检查当前 parser 是否为空，如果为空则尝试应用规则
        if (!scrapeForm.value.params.parser && matchedRules.value.length > 0) {
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
        // 自动应用第一条匹配的规则，无需确认
        const rule = matchedRules.value[0]
        applyMatchedRule(rule, true) // 静默应用，由下面统一发通知
        
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

// 打开对话框的便捷方法
const openSingleScrapeDialog = () => {
  submitMode.value = 'single'
  showScrapeDialog.value = true
}

const openBatchScrapeDialog = () => {
  submitMode.value = 'batch'
  showScrapeDialog.value = true
}

// 批量提交相关状态
const submitMode = ref('single') // 'single' | 'batch'
const batchMode = ref('text') // 'text' | 'file'
const batchUrlsText = ref('')
const batchFileUrls = ref([])
const interceptApisText = ref('')

// 解析配置相关状态
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
const selectedLlmFields = ref(['title', 'content'])
const xpathRules = ref([
  { field: 'title', path: '//h1' },
  { field: 'content', path: "//div[@class='article-body']" }
])

const addXpathRule = () => {
  xpathRules.value.push({ field: '', path: '' })
}

const removeXpathRule = (index) => {
  xpathRules.value.splice(index, 1)
}

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

// 编辑模式下的LLM预设应用
const applyEditLlmPreset = (type) => {
  const presets = {
    article: ['title', 'content', 'author', 'publish_time'],
    product: ['product_name', 'price', 'description', 'specifications'],
    contact: ['company_name', 'phone', 'email', 'address']
  }
  if (presets[type]) {
    editSelectedLlmFields.value = [...presets[type]]
    ElMessage.success('已应用模板')
  }
}

// 编辑模式下的XPath规则管理
const addEditXpathRule = () => {
  editXpathRules.value.push({ field: '', path: '' })
}

const removeEditXpathRule = (index) => {
  editXpathRules.value.splice(index, 1)
}

const handleLlmFieldsChange = (val) => {
  scrapeForm.value.params.parser_config.fields = val
}

// 计算有效 URL 数量
const batchUrlCount = computed(() => {
  if (batchMode.value === 'text') {
    return batchUrlsText.value.split('\n').filter(url => url.trim().startsWith('http')).length
  }
  return batchFileUrls.value.length
})

// 处理文件读取
const handleFileChange = (file) => {
  const reader = new FileReader()
  reader.onload = (e) => {
    const content = e.target.result
    const urls = content.split(/\r?\n/)
      .map(line => line.trim())
      .filter(line => line.startsWith('http'))
    batchFileUrls.value = urls
    if (urls.length === 0) {
      ElMessage.warning('未在文件中找到有效的 URL (需以 http 开头)')
    } else {
      ElMessage.success(`成功解析 ${urls.length} 个 URL`)
    }
  }
  reader.readAsText(file.raw)
}

const handleFileRemove = () => {
  batchFileUrls.value = []
}

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
      cookies: '',
      stealth: true,
  parser: '',
  parser_config: {
    fields: ['title', 'content']
  },
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

// 监听 URL 变化，自动重置匹配规则
watch(() => scrapeForm.value.url, async (newUrl) => {
  matchedRules.value = []
  lastCheckedDomain = ''
  matchedCookies.value = false
  
  if (newUrl && newUrl.startsWith('http')) {
    try {
      const urlObj = new URL(newUrl)
      const domain = urlObj.hostname
      const rules = await getRulesByDomain(domain)
      if (rules && rules.length > 0) {
        // 查找是否有配置了 cookies 的规则
        const ruleWithCookies = rules.find(r => r.cookies && r.cookies.trim())
        if (ruleWithCookies) {
          scrapeForm.value.params.cookies = ruleWithCookies.cookies
          matchedCookies.value = true
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

const showApiConfig = (row) => {
  // 构造 API 请求体
  const config = {
    url: row.url,
    params: row.params || {},
    cache: row.cache || { enabled: true, ttl: 3600 },
    priority: row.priority || 5
  }
  
  apiConfigJson.value = JSON.stringify(config, null, 2)
  showApiConfigDialog.value = true
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
    // 默认不加载 HTML 和截图，只有切换到对应标签页时才加载（或者由用户点击加载）
    const data = await getTask(task.task_id, { include_html: false, include_screenshot: false })
    currentTask.value = data
    activeTab.value = 'info'
    showTaskDialog.value = true
  } catch (error) {
    ElMessage.error('获取任务详情失败')
  }
}

const copyTask = async (task) => {
  try {
    // 获取任务详情
    const data = await getTask(task.task_id, { include_html: false, include_screenshot: false })
    
    // 填充新建任务表单数据
    scrapeForm.value = {
      url: data.url || '',
      params: {
        wait_for: data.params?.wait_for || 'networkidle',
        wait_time: data.params?.wait_time || 3000,
        timeout: data.params?.timeout || 30000,
        selector: data.params?.selector || '',
        screenshot: data.params?.screenshot !== false,
        is_fullscreen: data.params?.is_fullscreen || false,
        block_images: data.params?.block_images || false,
        block_media: data.params?.block_media || false,
        user_agent: data.params?.user_agent || '',
        viewport: data.params?.viewport || { width: 1920, height: 1080 },
        proxy: data.params?.proxy || { server: '', username: '', password: '' },
        cookies: data.params?.cookies || '',
        stealth: data.params?.stealth !== false,
        parser: data.params?.parser || '',
        parser_config: data.params?.parser_config || { fields: ['title', 'content'] },
        intercept_apis: data.params?.intercept_apis || [],
        intercept_continue: data.params?.intercept_continue || false
      },
      cache: data.cache || { enabled: true, ttl: 3600 },
      priority: data.priority || 1
    }
    
    // 处理解析配置
    if (scrapeForm.value.params.parser === 'llm') {
      selectedLlmFields.value = scrapeForm.value.params.parser_config?.fields || ['title', 'content']
    } else if (scrapeForm.value.params.parser === 'xpath') {
      const rules = scrapeForm.value.params.parser_config?.rules || {}
      xpathRules.value = Object.entries(rules).map(([field, path]) => ({ field, path }))
    } else {
      selectedLlmFields.value = ['title', 'content']
      xpathRules.value = [
        { field: 'title', path: '//h1' },
        { field: 'content', path: "//div[@class='article-body']" }
      ]
    }
    
    // 处理API拦截配置
    if (scrapeForm.value.params.intercept_apis && Array.isArray(scrapeForm.value.params.intercept_apis)) {
      interceptApisText.value = scrapeForm.value.params.intercept_apis.join('\n')
    } else {
      interceptApisText.value = ''
    }
    
    activeConfigTab.value = 'basic'
    showScrapeDialog.value = true
    ElMessage.success('任务配置已复制到新建任务表单')
  } catch (error) {
    ElMessage.error('获取任务详情失败')
  }
}

const editTask = async (task) => {
  try {
    // 获取任务详情
    const data = await getTask(task.task_id, { include_html: false, include_screenshot: false })
    currentEditTaskId.value = task.task_id
    
    // 填充编辑表单数据
    editForm.value = {
      url: data.url || '',
      params: {
        wait_for: data.params?.wait_for || 'networkidle',
        wait_time: data.params?.wait_time || 3000,
        timeout: data.params?.timeout || 30000,
        selector: data.params?.selector || '',
        screenshot: data.params?.screenshot !== false,
        is_fullscreen: data.params?.is_fullscreen || false,
        block_images: data.params?.block_images || false,
        block_media: data.params?.block_media || false,
        user_agent: data.params?.user_agent || '',
        viewport: data.params?.viewport || { width: 1920, height: 1080 },
        proxy: data.params?.proxy || { server: '', username: '', password: '' },
        cookies: data.params?.cookies || '',
        stealth: data.params?.stealth !== false,
        parser: data.params?.parser || '',
        parser_config: data.params?.parser_config || { fields: ['title', 'content'] },
        intercept_apis: data.params?.intercept_apis || [],
        intercept_continue: data.params?.intercept_continue || false
      },
      cache: data.cache || { enabled: true, ttl: 3600 },
      priority: data.priority || 1
    }
    
    // 处理解析配置
    if (editForm.value.params.parser === 'llm') {
      editSelectedLlmFields.value = editForm.value.params.parser_config?.fields || ['title', 'content']
    } else if (editForm.value.params.parser === 'xpath') {
      const rules = editForm.value.params.parser_config?.rules || {}
      editXpathRules.value = Object.entries(rules).map(([field, path]) => ({ field, path }))
    } else {
      editSelectedLlmFields.value = ['title', 'content']
      editXpathRules.value = [
        { field: 'title', path: '//h1' },
        { field: 'content', path: "//div[@class='article-body']" }
      ]
    }
    
    activeEditConfigTab.value = 'basic'
    showEditDialog.value = true
  } catch (error) {
    ElMessage.error('获取任务详情失败')
  }
}

// 监听标签页切换，按需加载大数据字段
watch(activeTab, async (newTab) => {
  if (!currentTask.value) return
  
  const taskId = currentTask.value.task_id
  if (newTab === 'html' && !currentTask.value.result?.html) {
    try {
      const data = await getTask(taskId, { include_html: true })
      if (data.result?.html) {
        currentTask.value.result.html = data.result.html
      }
    } catch (e) {
      ElMessage.error('加载 HTML 失败')
    }
  } else if (newTab === 'screenshot' && !currentTask.value.result?.screenshot) {
    try {
      const data = await getTask(taskId, { include_screenshot: true })
      if (data.result?.screenshot) {
        currentTask.value.result.screenshot = data.result.screenshot
      }
    } catch (e) {
      ElMessage.error('加载截图失败')
    }
  }
})

const submitTask = async () => {
  // 验证输入
  if (submitMode.value === 'single' && !scrapeForm.value.url) {
    ElMessage.warning('请输入目标 URL')
    return
  }
  if (submitMode.value === 'batch' && batchUrlCount.value === 0) {
    ElMessage.warning('请提供有效的 URL 列表')
    return
  }

  loading.value = true
  try {
    // 深度克隆表单数据
    const baseConfig = JSON.parse(JSON.stringify(scrapeForm.value))
    
    // 统一处理参数格式
    const processParams = (data) => {
      if (!data.params.user_agent) data.params.user_agent = null
      if (!data.params.selector) data.params.selector = null
      
      // 处理解析配置
      if (data.params.parser === 'llm') {
        data.params.parser_config = { fields: selectedLlmFields.value }
      } else if (data.params.parser === 'xpath') {
        const rules = {}
        xpathRules.value.forEach(r => {
          if (r.field && r.path) rules[r.field] = r.path
        })
        data.params.parser_config = { rules }
      } else if (data.params.parser === 'gne') {
        data.params.parser_config = {}
      } else {
        data.params.parser_config = null
      }

      if (!data.params.proxy || !data.params.proxy.server) {
        data.params.proxy = null
      } else {
        if (!data.params.proxy.username) delete data.params.proxy.username
        if (!data.params.proxy.password) delete data.params.proxy.password
      }
      
      // 处理API拦截配置
      if (interceptApisText.value.trim()) {
        data.params.intercept_apis = interceptApisText.value
          .split('\n')
          .map(line => line.trim())
          .filter(line => line)
      } else if (!data.params.intercept_apis || data.params.intercept_apis.length === 0) {
        data.params.intercept_apis = null
      }

      if (data.params.cookies) {
        const cookieVal = data.params.cookies.trim()
        if ((cookieVal.startsWith('[') && cookieVal.endsWith(']')) || 
            (cookieVal.startsWith('{') && cookieVal.endsWith('}'))) {
          try {
            data.params.cookies = JSON.parse(cookieVal)
          } catch (e) {
            console.warn('Cookies parse failed, using as string')
          }
        }
      } else {
        data.params.cookies = null
      }
      
      if (!data.params.viewport || !data.params.viewport.width || !data.params.viewport.height) {
        data.params.viewport = null
      }
      return data
    }

    if (submitMode.value === 'single') {
      const submitData = processParams(baseConfig)
      scrapeAsync(submitData).then(() => {
        ElMessage.success('任务提交成功 (异步)')
        loadTasks()
      }).catch(error => {
        ElMessage.error('提交失败: ' + (error.response?.data?.detail || error.message))
      })
    } else {
      // 批量处理
      const urls = batchMode.value === 'text' 
        ? batchUrlsText.value.split('\n').map(u => u.trim()).filter(u => u.startsWith('http'))
        : batchFileUrls.value
      
      const batchData = {
        tasks: urls.map(url => {
          const taskConfig = JSON.parse(JSON.stringify(baseConfig))
          taskConfig.url = url
          return processParams(taskConfig)
        })
      }
      
      scrapeBatch(batchData).then(() => {
        ElMessage.success(`成功提交 ${urls.length} 个批量任务`)
        loadTasks()
      }).catch(error => {
        ElMessage.error('提交失败: ' + (error.response?.data?.detail || error.message))
      })
    }

    showScrapeDialog.value = false
    resetForm()
  } catch (error) {
    ElMessage.error('提交准备失败: ' + error.message)
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
      cookies: '',
      parser: '',
      parser_config: { fields: ['title', 'content'] },
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
  selectedLlmFields.value = ['title', 'content']
  xpathRules.value = [
    { field: 'title', path: '//h1' },
    { field: 'content', path: "//div[@class='article-body']" }
  ]
  interceptApisText.value = ''
  lastCheckedDomain = ''
  matchedRules.value = []
  activeConfigTab.value = 'basic'
}

const submitEditTask = async () => {
  // 验证输入
  if (!editForm.value.url) {
    ElMessage.warning('请输入目标 URL')
    return
  }

  loading.value = true
  try {
    // 深度克隆表单数据
    const baseConfig = JSON.parse(JSON.stringify(editForm.value))
    
    // 统一处理参数格式
    const processParams = (data) => {
      if (!data.params.user_agent) data.params.user_agent = null
      if (!data.params.selector) data.params.selector = null
      
      // 处理解析配置
      if (data.params.parser === 'llm') {
        data.params.parser_config = { fields: editSelectedLlmFields.value }
      } else if (data.params.parser === 'xpath') {
        const rules = {}
        editXpathRules.value.forEach(r => {
          if (r.field && r.path) rules[r.field] = r.path
        })
        data.params.parser_config = { rules }
      } else if (data.params.parser === 'gne') {
        data.params.parser_config = {}
      } else {
        data.params.parser_config = null
      }

      if (!data.params.proxy || !data.params.proxy.server) {
        data.params.proxy = null
      } else {
        if (!data.params.proxy.username) delete data.params.proxy.username
        if (!data.params.proxy.password) delete data.params.proxy.password
      }
      
      if (!data.params.intercept_apis || data.params.intercept_apis.length === 0) {
        data.params.intercept_apis = null
      }

      if (data.params.cookies) {
        const cookieVal = data.params.cookies.trim()
        if ((cookieVal.startsWith('[') && cookieVal.endsWith(']')) || 
            (cookieVal.startsWith('{') && cookieVal.endsWith('}'))) {
          try {
            data.params.cookies = JSON.parse(cookieVal)
          } catch (e) {
            console.warn('Cookies parse failed, using as string')
          }
        }
      } else {
        data.params.cookies = null
      }
      
      if (!data.params.viewport || !data.params.viewport.width || !data.params.viewport.height) {
        data.params.viewport = null
      }
      return data
    }

    const submitData = processParams(baseConfig)
    
    // 调用 API 更新任务
    // 这里假设后端有更新任务的 API 端点
    // 如果没有专门的更新 API，可以先删除旧任务，再创建新任务
    // 暂时使用 scrapeAsync 来创建新任务
    await scrapeAsync(submitData)
    
    ElMessage.success('任务更新成功')
    showEditDialog.value = false
    loadTasks()
  } catch (error) {
    ElMessage.error('提交失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
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

.dropdown-header {
  padding: 8px 16px;
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  border-bottom: 1px solid #f1f5f9;
}

.dropdown-footer {
  padding: 8px 16px;
  font-size: 11px;
  color: #cbd5e1;
  text-align: center;
  border-top: 1px solid #f1f5f9;
}

.mr-2 {
  margin-right: 8px;
}

.copy-task-btn {
  transition: all 0.3s ease;
  background-color: #409EFF;
  border-color: #409EFF;
}

.copy-task-btn:hover {
  background-color: #66B1FF;
  border-color: #66B1FF;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
}

.copy-task-btn:active {
  transform: translateY(0);
  box-shadow: 0 1px 4px rgba(64, 158, 255, 0.2);
}

/* 列表 UI 优化 */
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
  font-size: 18px; /* 进一步增大字体 */
  padding: 8px 0;
}

.tab-label .el-icon {
  font-size: 22px; /* 进一步增大图标 */
}

/* 彩色图标样式 - 统一类名 */
.icon-basic {
  color: #3b82f6 !important; /* 蓝色 */
}

.icon-parser {
  color: #8b5cf6 !important; /* 紫色 */
}

.icon-browser {
  color: #10b981 !important; /* 绿色 */
}

.icon-advanced {
  color: #f59e0b !important; /* 橙色 */
}

.icon-link {
  color: #3b82f6;
}

.icon-upload {
  color: #6366f1;
}

.tab-content {
  padding: 24px;
  min-height: 400px;
  background-color: #fff;
}

.section-header {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 20px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 12px;
  padding-left: 8px;
  border-left: 3px solid #3b82f6;
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

.input-tip {
  font-size: 12px;
  color: #94a3b8;
  margin: 4px 0 10px 0;
}

.cookies-input-wrapper {
  width: 100%;
}

.cookies-tip {
  margin-top: 6px;
  font-size: 12px;
  color: var(--el-color-success);
  display: flex;
  align-items: center;
  gap: 4px;
}

.cookies-tip .success-icon {
  font-size: 14px;
}

.parser-config-area {
  margin-top: 20px;
  padding: 16px;
  background-color: #f8fafc;
  border-radius: 8px;
  border: 1px solid #f1f5f9;
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
  font-weight: 600;
}

.mt-4 {
  margin-top: 16px;
}

.mb-4 {
  margin-bottom: 16px;
}

.alert-content-mini {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.helper-text {
  margin: 0;
  font-size: 13px;
  color: #475569;
}

.format-example-mini {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px;
  background-color: #f1f5f9;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
  width: fit-content;
}

.api-warning {
  margin: 4px 0 0 0;
  font-size: 12px;
  color: #e6a23c;
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 500;
}

.llm-helper-alert {
  padding: 8px 16px;
}

.llm-helper-alert :deep(.el-alert__content) {
  padding: 0 8px;
}

.llm-helper-alert :deep(.el-alert__title) {
  font-size: 13px;
  font-weight: 600;
}

.alert-content p {
  margin: 0 0 8px 0;
  font-size: 14px;
}

.format-list {
  margin: 0 0 12px 0;
  padding-left: 18px;
  list-style-type: disc;
}

.format-list li {
  font-size: 13px;
  color: #475569;
  line-height: 1.6;
}

.format-example {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background-color: #f1f5f9;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
}

.example-label {
  font-size: 12px;
  color: #64748b;
  font-weight: 600;
}

.format-example code {
  font-family: monospace;
  font-size: 12px;
  color: #0f172a;
}

.label-with-help {
  display: flex;
  align-items: center;
  gap: 6px;
}

.help-icon {
  font-size: 14px;
  color: #94a3b8;
  cursor: help;
}

.xpath-rules-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-size: 13px;
  color: #64748b;
}

.xpath-rule-row {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
  align-items: center;
}

.rule-delete-btn {
  font-size: 18px;
  padding: 0 4px;
}

.rule-delete-btn:hover {
  color: #f56c6c !important;
}

.viewport-input {
  display: flex;
  align-items: center;
  gap: 12px;
}

.viewport-input .sep {
  color: #94a3b8;
  font-weight: bold;
}

.feature-settings {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-top: 20px;
}

.feature-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background-color: #f8fafc;
  border-radius: 8px;
  border: 1px solid #f1f5f9;
}

.feature-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.feature-name {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}

.feature-desc {
  font-size: 12px;
  color: #94a3b8;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 10px;
}

.submit-btn {
  padding-left: 24px;
  padding-right: 24px;
  font-weight: 600;
}

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
.config-dialog :deep(.el-dialog__header) {
  margin-right: 0;
  padding: 20px 24px;
  border-bottom: 1px solid #f1f5f9;
}

.config-dialog :deep(.el-dialog__body) {
  padding: 20px;
  background-color: #f8fafc;
}

.header-extra {
  margin-left: auto;
  display: flex;
  align-items: center;
}

.batch-input-area {
  margin-bottom: 15px;
}

.compact-tabs :deep(.el-tabs__header) {
  margin-bottom: 10px;
}

.batch-count-tip {
  font-size: 13px;
  color: #64748b;
  margin-top: 8px;
  padding: 8px 12px;
  background-color: #f8fafc;
  border-radius: 6px;
  border-left: 4px solid #7c3aed;
}

.batch-count-tip .count {
  font-weight: bold;
  color: #7c3aed;
  font-size: 15px;
}

.bento-upload :deep(.el-upload-dragger) {
  padding: 20px 10px;
  border: 1px dashed #e2e8f0;
  background-color: #f8fafc;
}

.bento-upload :deep(.el-upload-dragger:hover) {
  border-color: #7c3aed;
}

.bento-upload .el-icon--upload {
  font-size: 40px;
  color: #94a3b8;
  margin-bottom: 8px;
}

.bento-upload .el-upload__text {
  font-size: 13px;
}

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

/* 2. 解析配置 (新增) */
.parser-card {
  grid-column: span 1;
}

.parser-tip {
  margin-top: 15px;
}

.parser-tip .el-alert {
  padding: 8px 12px;
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

.header-icon-box.parser {
  background: linear-gradient(135deg, #a855f7 0%, #7c3aed 100%);
}
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

.api-config-content {
  padding: 10px 0;
}

.api-config-alert :deep(.el-alert__title) {
  font-size: 13px;
  font-weight: 600;
}

.api-config-alert :deep(.el-alert__description) {
  font-size: 12px;
  line-height: 1.4;
}

.config-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.api-endpoint {
  display: flex;
  align-items: center;
  gap: 8px;
  background-color: #f1f5f9;
  padding: 4px 12px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.endpoint-path {
  font-family: monospace;
  color: #475569;
  font-weight: 600;
}

.api-json-box {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background-color: #f8fafc;
}

.api-json-box pre {
  margin: 0;
  padding: 16px;
  font-size: 13px;
  line-height: 1.5;
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
  gap: 5px;
}

.pagination-container {
  padding: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
