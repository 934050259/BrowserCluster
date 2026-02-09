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
        element-loading-text="加载任务列表中..."
        element-loading-background="rgba(255, 255, 255, 0.7)"
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

        <el-table-column prop="status" label="状态" width="120" align="center">
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

        <el-table-column label="操作" width="220" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip content="查看详情" placement="top">
                <el-button circle size="small" :icon="View" @click="viewTask(row)" />
              </el-tooltip>

              <el-tooltip content="复制并新建" placement="top">
                <el-button 
                  circle 
                  size="small" 
                  type="success" 
                  :icon="CopyDocument" 
                  @click="handleCopyTask(row)" 
                />
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
      :title="isRetryEdit ? '编辑并重试任务' : '新建抓取任务'" 
      width="850px" 
      destroy-on-close 
      top="8vh"
      class="config-dialog"
    >
      <el-form :model="scrapeForm" label-width="120px">
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
                <div class="header-extra" v-if="!isRetryEdit">
                  <el-radio-group v-model="submitMode" size="small">
                    <el-radio-button label="single">单条任务</el-radio-button>
                    <el-radio-button label="batch">批量导入</el-radio-button>
                  </el-radio-group>
                </div>
                <div class="header-extra" v-else>
                  <el-tag type="warning" effect="dark">重试模式：仅支持单条任务编辑</el-tag>
                </div>
              </div>

              <div v-if="submitMode === 'single'">
                <el-form-item label="目标 URL" required>
                  <el-input v-model="scrapeForm.url" placeholder="请输入抓取地址，例如: https://example.com" clearable>
                    <template #prefix><el-icon class="icon-link"><Connection /></el-icon></template>
                  </el-input>
                </el-form-item>

                <!-- 匹配规则展示区 -->
                <div class="matched-rules-section" v-if="matchedRules.length > 0">
                  <div class="section-header">
                    <div class="header-title">
                      <el-icon><MagicStick /></el-icon>
                      <span>发现该域名的 {{ matchedRules.length }} 条可用规则</span>
                    </div>
                    <div class="header-tip">点击下方规则可快速切换应用配置</div>
                  </div>
                  <div class="rules-grid">
                    <div 
                      v-for="rule in matchedRules" 
                      :key="rule.id" 
                      class="rule-option-card"
                      :class="{ 'is-active': selectedRuleId === rule.id }"
                      @click="applyMatchedRule(rule)"
                    >
                      <div class="rule-card-top">
                        <el-tag size="small" :type="getParserTypeTag(rule.parser_type)">
                          {{ rule.parser_type.toUpperCase() }}
                        </el-tag>
                        <span class="rule-priority-tag" v-if="rule.priority > 0">
                          优先级: {{ rule.priority }}
                        </span>
                      </div>
                      <div class="rule-card-body">
                        <div class="rule-domain-text">{{ rule.domain }}</div>
                        <div class="rule-desc-text" v-if="rule.description">{{ rule.description }}</div>
                      </div>
                    </div>
                  </div>
                </div>
                
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
                  <el-form-item>
                    <template #label>
                      <div class="label-with-help">
                        <span>存储位置</span>
                        <el-tooltip content="指定任务结果（HTML 源码和页面截图）的存储位置" placement="top">
                          <el-icon class="help-icon"><QuestionFilled /></el-icon>
                        </el-tooltip>
                      </div>
                    </template>
                    <el-radio-group v-model="scrapeForm.params.storage_type" size="default">
                      <el-radio-button label="mongo">MongoDB</el-radio-button>
                      <el-radio-button label="oss">OSS 存储</el-radio-button>
                    </el-radio-group>

                    <div class="custom-storage-fields mt-2" v-if="scrapeForm.params.storage_type">
                      <template v-if="scrapeForm.params.storage_type === 'mongo'">
                        <div class="storage-input-group">
                          <div class="input-label-tip">自定义 MongoDB 集合名</div>
                          <el-input 
                            v-model="scrapeForm.params.mongo_collection" 
                            placeholder="例如: my_collection"
                            size="small"
                            clearable
                          >
                            <template #prefix><el-icon><Collection /></el-icon></template>
                          </el-input>
                        </div>
                        <div class="storage-path-preview">
                          <el-icon><InfoFilled /></el-icon>
                          <span>实际存储集合: <code>{{ scrapeForm.params.mongo_collection || 'tasks_results' }}</code></span>
                        </div>
                      </template>

                      <template v-if="scrapeForm.params.storage_type === 'oss'">
                        <div class="storage-input-group">
                          <div class="input-label-tip">自定义 OSS 存储路径</div>
                          <el-input 
                            v-model="scrapeForm.params.oss_path" 
                            placeholder="例如: custom/path/"
                            size="small"
                            clearable
                          >
                            <template #prefix><el-icon><FolderOpened /></el-icon></template>
                          </el-input>
                        </div>
                        <div class="storage-path-preview">
                          <el-icon><InfoFilled /></el-icon>
                          <span>实际存储路径: <code>{{ scrapeForm.params.oss_path ? (scrapeForm.params.oss_path.endsWith('/') ? scrapeForm.params.oss_path : scrapeForm.params.oss_path + '/') : 'tasks/' }}{任务ID}/...</code></span>
                        </div>
                      </template>
                    </div>

                    <div class="form-item-tip">
                      <template v-if="scrapeForm.params.storage_type === 'oss'">
                        请确保已在 <el-link type="primary" :underline="false" href="/configs">系统设置</el-link> 中配置 OSS 凭据
                      </template>
                      <template v-else>
                        结果将直接存储在 MongoDB 数据库中
                      </template>
                    </div>
                  </el-form-item>
                </el-col>
              </el-row>
              
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="数据缓存">
                    <div class="switch-container">
                      <el-switch v-model="scrapeForm.cache.enabled" />
                      <span class="switch-tip">{{ scrapeForm.cache.enabled ? '开启 (节省资源)' : '关闭 (实时抓取)' }}</span>
                    </div>
                  </el-form-item>
                </el-col>
                <el-col :span="12" v-if="scrapeForm.cache.enabled">
                  <el-form-item label="缓存有效期 (TTL/秒)">
                    <el-input-number v-model="scrapeForm.cache.ttl" :min="60" :step="60" style="width: 100%" />
                  </el-form-item>
                </el-col>
              </el-row>
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
              <!-- 匹配规则展示区已移至基础配置 -->

              <el-form-item label="解析模式">
                <el-radio-group v-model="scrapeForm.params.parser" size="default">
                  <el-radio-button label="">不解析</el-radio-button>
                  <el-radio-button label="gne">智能解析 (GNE)</el-radio-button>
                  <el-radio-button label="llm">大模型提取 (LLM)</el-radio-button>
                  <el-radio-button label="xpath">自定义规则 (XPath)</el-radio-button>
                </el-radio-group>
              </el-form-item>

              <div v-if="scrapeForm.params.parser === 'gne'" class="parser-config-area">
                <el-form-item label="提取模式">
                  <el-radio-group v-model="scrapeForm.params.parser_config.mode" size="small">
                    <el-radio-button label="detail">详情模式</el-radio-button>
                    <el-radio-button label="list">列表模式</el-radio-button>
                  </el-radio-group>
                </el-form-item>

                <div v-if="scrapeForm.params.parser_config.mode === 'list'" class="mt-4">
                  <el-form-item label="列表项 XPath" required>
            <el-input 
              v-model="scrapeForm.params.parser_config.list_xpath" 
              placeholder="例如: //ul/li[1]/a 或 /html/body/div/ul/li[1]/a"
              clearable
            >
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            <div class="input-tip text-danger">必填：指定列表中任意一个标题元素的 XPath，GNE 将以此为特征自动识别整个列表。</div>
          </el-form-item>
                </div>

                <el-alert 
                  :title="scrapeForm.params.parser_config.mode === 'list' ? 'GNE 列表模式' : 'GNE 详情模式'" 
                  type="info" 
                  :closable="false" 
                  show-icon 
                  :description="scrapeForm.params.parser_config.mode === 'list' ? '自动识别并提取新闻、博客列表页中的标题、链接及发布日期。' : '适用于新闻、博客等文章类页面，自动提取标题、作者、发布时间、正文和图片。'" 
                />
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
                  <el-form-item label="浏览器引擎">
                    <el-select v-model="scrapeForm.params.engine" style="width: 100%">
                      <el-option label="Playwright (默认)" value="playwright" />
                      <el-option label="DrissionPage (过盾强)" value="drissionpage" />
                    </el-select>
                  </el-form-item>
                </el-col>
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
                    <span class="feature-name">保存 HTML</span>
                    <span class="feature-desc">将完整的网页源码保存到数据库或 OSS</span>
                  </div>
                  <el-switch v-model="scrapeForm.params.save_html" />
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
              
              <template v-if="scrapeForm.params.proxy.server">
                <el-row :gutter="20" v-if="scrapeForm.params.engine !== 'drissionpage'">
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
                
                <el-alert
                  v-if="scrapeForm.params.engine === 'drissionpage'"
                  title="代理说明"
                  type="info"
                  description="DrissionPage 引擎目前仅支持无账密代理（IP:Port 格式）。如需使用账密认证代理，请切换至 Playwright 引擎。"
                  show-icon
                  :closable="false"
                  class="proxy-warning"
                />
              </template>
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
              <el-descriptions-item>
                <template #label>
                  <div class="label-box"><el-icon><Key /></el-icon><span>任务 ID</span></div>
                </template>
                {{ currentTask.task_id }}
              </el-descriptions-item>
              <el-descriptions-item>
                <template #label>
                  <div class="label-box"><el-icon><Watch /></el-icon><span>当前状态</span></div>
                </template>
                <el-tag :type="getStatusType(currentTask.status)" size="default">{{ getStatusText(currentTask.status) }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item :span="2">
                <template #label>
                  <div class="label-box"><el-icon><Link /></el-icon><span>目标 URL</span></div>
                </template>
                <el-link :href="currentTask.url" target="_blank" type="primary" class="detail-url-link">{{ currentTask.url }}</el-link>
              </el-descriptions-item>
              <el-descriptions-item>
                <template #label>
                  <div class="label-box"><el-icon><Timer /></el-icon><span>创建时间</span></div>
                </template>
                {{ formatDate(currentTask.created_at) }}
              </el-descriptions-item>
              <el-descriptions-item>
                <template #label>
                  <div class="label-box"><el-icon><CircleCheck /></el-icon><span>完成时间</span></div>
                </template>
                {{ formatDate(currentTask.completed_at) || '-' }}
              </el-descriptions-item>
              <el-descriptions-item>
                <template #label>
                  <div class="label-box"><el-icon><Files /></el-icon><span>缓存命中</span></div>
                </template>
                <el-tag :type="currentTask.cached ? 'success' : 'info'" size="default">
                  {{ currentTask.cached ? '命中' : '未命中' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item>
                <template #label>
                  <div class="label-box"><el-icon><Cpu /></el-icon><span>节点 ID</span></div>
                </template>
                {{ currentTask.node_id || '-' }}
              </el-descriptions-item>
              <el-descriptions-item>
                <template #label>
                  <div class="label-box"><el-icon><Monitor /></el-icon><span>浏览器引擎</span></div>
                </template>
                <el-tag size="default" type="primary" effect="plain">
                  {{ currentTask.params?.engine || 'playwright' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item>
                <template #label>
                  <div class="label-box"><el-icon><Lock /></el-icon><span>反检测</span></div>
                </template>
                <el-tag :type="currentTask.params?.stealth ? 'success' : 'info'" size="default">
                  {{ currentTask.params?.stealth ? '开启' : '关闭' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item :span="2">
                <template #label>
                  <div class="label-box"><el-icon><Box /></el-icon><span>存储位置</span></div>
                </template>
                <div class="storage-info-cell" v-if="currentTask.params?.storage_type">
                  <el-tag :type="currentTask.params?.storage_type === 'oss' ? 'warning' : 'info'" size="default">
                  <div class="tag-content-flex">
                    <el-icon><Collection v-if="currentTask.params.storage_type === 'mongo'" /><FolderOpened v-else /></el-icon>
                    <span>{{ currentTask.params?.storage_type === 'oss' ? 'Aliyun OSS' : 'MongoDB' }}</span>
                  </div>
                </el-tag>
                  <code class="storage-path-code">
                    <template v-if="currentTask.params.storage_type === 'mongo'">
                      集合: {{ currentTask.params.mongo_collection || 'tasks_results' }}
                    </template>
                    <template v-else>
                      路径: {{ currentTask.params.oss_path || 'tasks/' }}{{ currentTask.task_id }}/
                    </template>
                  </code>
                </div>
              </el-descriptions-item>
              <el-descriptions-item>
                <template #label>
                  <div class="label-box"><el-icon><Document /></el-icon><span>保存 HTML</span></div>
                </template>
                <el-tag :type="currentTask.params?.save_html !== false ? 'success' : 'info'" size="default">
                  {{ currentTask.params?.save_html !== false ? '是' : '否' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item>
                <template #label>
                  <div class="label-box"><el-icon><MagicStick /></el-icon><span>解析引擎</span></div>
                </template>
                <el-tag :type="currentTask.params?.parser ? 'success' : 'info'" size="default">
                  {{ currentTask.params?.parser || '不解析' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item>
                <template #label>
                  <div class="label-box"><el-icon><Setting /></el-icon><span>解析模式</span></div>
                </template>
                <el-tag type="warning" size="default" v-if="currentTask.params?.parser === 'gne'">
                  {{ currentTask.params?.parser_config?.mode === 'list' ? '列表模式' : '详情模式' }}
                </el-tag>
                <span v-else>-</span>
              </el-descriptions-item>

              <el-descriptions-item :span="2" v-if="currentTask.params?.parser">
                <template #label>
                  <div class="label-box"><el-icon><MagicStick /></el-icon><span>解析规则</span></div>
                </template>
                <template v-if="currentTask.params.parser === 'gne' && currentTask.params.parser_config?.mode === 'list'">
                  <span class="rule-label mr-2">列表 XPath:</span>
                  <code>{{ currentTask.params.parser_config.list_xpath || '-' }}</code>
                </template>
                <template v-else-if="currentTask.params.parser === 'xpath'">
                  <div class="rule-tags">
                    <el-tag v-for="(path, field) in currentTask.params.parser_config?.rules" :key="field" size="small" class="mr-2 mb-1">
                      {{ field }}: {{ path }}
                    </el-tag>
                  </div>
                </template>
                <template v-else-if="currentTask.params.parser === 'llm'">
                  <div class="rule-tags">
                    <el-tag v-for="field in currentTask.params.parser_config?.fields" :key="field" size="small" class="mr-2 mb-1">
                      {{ field }}
                    </el-tag>
                  </div>
                </template>
                <span v-else>自动识别</span>
              </el-descriptions-item>
              
              <el-descriptions-item :span="2" v-if="currentTask.result?.oss_html">
                <template #label>
                  <div class="label-box"><el-icon><Connection /></el-icon><span>OSS HTML 路径</span></div>
                </template>
                <div class="oss-path-info">
                  <el-link :href="currentTask.result.oss_html" target="_blank" type="primary" class="detail-url-link">
                    {{ currentTask.result.oss_html }}
                  </el-link>
                  <el-button size="small" link @click="copyToClipboard(currentTask.result.oss_html)">复制</el-button>
                </div>
              </el-descriptions-item>
              <el-descriptions-item :span="2" v-if="currentTask.result?.oss_screenshot">
                <template #label>
                  <div class="label-box"><el-icon><Picture /></el-icon><span>OSS截图路径</span></div>
                </template>
                <div class="oss-path-info">
                  <el-link :href="currentTask.result.oss_screenshot" target="_blank" type="primary" class="detail-url-link">
                    {{ currentTask.result.oss_screenshot }}
                  </el-link>
                  <el-button size="small" link @click="copyToClipboard(currentTask.result.oss_screenshot)">复制</el-button>
                </div>
              </el-descriptions-item>
            </el-descriptions>

            <div v-if="currentTask.result" class="metadata-section">
              <el-divider content-position="left">页面元数据</el-divider>
              <el-descriptions :column="2" border size="default" class="detail-descriptions">
                <el-descriptions-item :span="2" width="120px">
                  <template #label>
                    <div class="label-box"><el-icon><Document /></el-icon><span>页面标题</span></div>
                  </template>
                  {{ currentTask.result.metadata?.title || '-' }}
                </el-descriptions-item>
                <el-descriptions-item :span="2" v-if="currentTask.result.metadata?.actual_url">
                  <template #label>
                    <div class="label-box"><el-icon><Right /></el-icon><span>实际 URL</span></div>
                  </template>
                  <el-link :href="currentTask.result.metadata.actual_url" target="_blank" type="success" class="detail-url-link">
                    {{ currentTask.result.metadata.actual_url }}
                  </el-link>
                </el-descriptions-item>
                <el-descriptions-item>
                  <template #label>
                    <div class="label-box"><el-icon><Timer /></el-icon><span>加载用时</span></div>
                  </template>
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
                      <pre>{{ formatJSON(req.body) }}</pre>
                    </div>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </el-tab-pane>

          <el-tab-pane label="截图预览" name="screenshot" v-if="currentTask.status === 'success' && (currentTask.params?.screenshot || currentTask.result?.oss_screenshot)">
            <div class="screenshot-container" v-loading="loadingScreenshot">
              <template v-if="currentTask.result?.screenshot">
                <el-image 
                  :src="currentTask.result.screenshot.startsWith('http') ? currentTask.result.screenshot : 'data:image/png;base64,' + currentTask.result.screenshot" 
                  :preview-src-list="[currentTask.result.screenshot.startsWith('http') ? currentTask.result.screenshot : 'data:image/png;base64,' + currentTask.result.screenshot]"
                  fit="contain"
                >
                  <template #error>
                    <div class="image-slot">
                      <el-icon><picture /></el-icon>
                    </div>
                  </template>
                </el-image>
              </template>
              <el-empty v-else-if="loadingScreenshot" description="正在加载截图..." />
              <el-empty v-else description="暂无截图数据" />
            </div>
          </el-tab-pane>

          <el-tab-pane label="HTML 源码" name="html" v-if="currentTask.status === 'success'">
            <div class="html-container" v-loading="loadingHtml">
              <template v-if="currentTask.result?.html">
                <pre><code>{{ currentTask.result.html }}</code></pre>
              </template>
              <el-empty v-else-if="loadingHtml" description="正在加载源码..." />
              <el-empty v-else description="暂无 HTML 源码" />
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
const isRetryEdit = ref(false)
const retryTaskId = ref('')
const showTaskDialog = ref(false)
const showApiConfigDialog = ref(false)
const apiConfigJson = ref('')
const activeConfigTab = ref('basic')
const matchedRules = ref([])
const selectedRuleId = ref(null)
const matchedCookies = ref(false)
let lastCheckedDomain = ''
let debounceTimer = null
const loadingHtml = ref(false)
const loadingScreenshot = ref(false)

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
  selectedRuleId.value = rule.id
  
  // 确保 parser_config 对象存在
  if (!scrapeForm.value.params.parser_config) {
    scrapeForm.value.params.parser_config = {
      mode: 'detail',
      fields: []
    }
  }

  if (rule.cache_config) {
    scrapeForm.value.cache.enabled = rule.cache_config.enabled
    scrapeForm.value.cache.ttl = rule.cache_config.ttl
  }

  if (rule.parser_type === 'llm') {
    const fields = rule.parser_config.fields || []
    selectedLlmFields.value = [...fields]
    scrapeForm.value.params.parser_config.fields = [...fields]
    scrapeForm.value.params.parser_config.mode = rule.parser_config.mode || 'detail'
  } else if (rule.parser_type === 'xpath') {
    const rules = rule.parser_config.rules || {}
    xpathRules.value = Object.entries(rules).map(([field, path]) => ({ field, path }))
    scrapeForm.value.params.parser_config.rules = { ...rules }
  } else if (rule.parser_type === 'gne') {
    scrapeForm.value.params.parser_config.mode = rule.parser_config.mode || 'detail'
    if (rule.parser_config.mode === 'list') {
      scrapeForm.value.params.parser_config.list_xpath = rule.parser_config.list_xpath || ''
    }
  }

  // 应用浏览器特征和高级配置
  const syncFields = [
    "engine", "wait_for", "timeout", "viewport", "stealth", 
    "save_html", "screenshot", "is_fullscreen", "block_images",
    "intercept_apis", "intercept_continue", "proxy", "cookies",
    "storage_type", "mongo_collection", "oss_path"
  ]
  
  syncFields.forEach(field => {
    if (rule[field] !== undefined && rule[field] !== null) {
      if (typeof rule[field] === 'object' && rule[field] !== null) {
        scrapeForm.value.params[field] = JSON.parse(JSON.stringify(rule[field]))
      } else {
        scrapeForm.value.params[field] = rule[field]
      }
    }
  })

  if (!silent) {
    ElMessage.success(`已应用 ${rule.domain} 的解析配置`)
  }
}

// 监听标签页切换
watch(activeConfigTab, async (newTab) => {
  if (newTab === 'parser' && scrapeForm.value.url && scrapeForm.value.url.startsWith('http')) {
    // 不再在此处触发自动加载，仅在 URL 输入时触发
    // 如果没有匹配规则，尝试获取规则列表供手动选择，但不自动应用
    if (!matchedRules.value.length) {
      try {
        const urlObj = new URL(scrapeForm.value.url)
        const domain = urlObj.hostname
        const rules = await getRulesByDomain(domain)
        matchedRules.value = rules || []
        lastCheckedDomain = domain
      } catch (e) {
        console.error('Tab switch fetch rules failed:', e)
      }
    }
  }
})

// 打开对话框的便捷方法
const openSingleScrapeDialog = () => {
  submitMode.value = 'single'
  resetForm()
  showScrapeDialog.value = true
}

const openBatchScrapeDialog = () => {
  submitMode.value = 'batch'
  resetForm()
  showScrapeDialog.value = true
}

// 批量提交相关状态
const submitMode = ref('single') // 'single' | 'batch'
const batchMode = ref('text') // 'text' | 'file'
const batchUrlsText = ref('')
const batchFileUrls = ref([])

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

const handleLlmFieldsChange = (val) => {
  scrapeForm.value.params.parser_config.fields = val
}

const openUrl = (url) => {
  if (url) window.open(url, '_blank')
}

const copyToClipboard = (text) => {
  if (!text) return
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => {
    // 降级方案
    const input = document.createElement('input')
    input.value = text
    document.body.appendChild(input)
    input.select()
    document.execCommand('copy')
    document.body.removeChild(input)
    ElMessage.success('已复制到剪贴板')
  })
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
    engine: 'playwright',
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
      storage_type: 'mongo',
      mongo_collection: '',
      oss_path: '',
      save_html: true,
  parser: '',
  parser_config: {
    mode: 'detail',
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

// 监听 URL 变化，自动获取匹配规则
watch(() => scrapeForm.value.url, (newUrl) => {
  if (debounceTimer) clearTimeout(debounceTimer)
  
  debounceTimer = setTimeout(async () => {
    if (newUrl && newUrl.startsWith('http')) {
      try {
        const urlObj = new URL(newUrl)
        const domain = urlObj.hostname
        
        // 如果域名没变，且已经有匹配规则了，就不重复请求
        if (domain === lastCheckedDomain && matchedRules.value.length > 0) {
          return
        }
        
        // 如果域名变了，才请求
        if (domain && domain !== lastCheckedDomain) {
          const rules = await getRulesByDomain(domain)
          if (rules && rules.length > 0) {
            matchedRules.value = rules
            lastCheckedDomain = domain
            
            // 自动应用第一条匹配的规则
            const rule = rules[0]
            applyMatchedRule(rule, true)
            
            // 如果规则中有 cookies，提示一下
            if (rule.cookies && rule.cookies.trim()) {
              matchedCookies.value = true
              ElMessage.success(`已自动加载域名 ${domain} 的解析配置与 Cookies`)
            } else {
              ElMessage.success(`已自动加载域名 ${domain} 的解析配置`)
            }
          } else {
            // 如果没匹配到规则，重置状态
            matchedRules.value = []
            lastCheckedDomain = domain
            matchedCookies.value = false
          }
        }
      } catch (e) {
        // 忽略无效 URL 错误
      }
    } else {
      // URL 不合法或被清空时重置
      matchedRules.value = []
      lastCheckedDomain = ''
      matchedCookies.value = false
    }
  }, 500)
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
    `请选择重试方式：\nURL: ${row.url}`,
    '重试选项',
    {
      confirmButtonText: '直接重试',
      cancelButtonText: '编辑配置',
      distinguishCancelAndClose: true,
      type: 'warning',
      icon: WarningFilled,
      buttonSize: 'default'
    }
  ).then(() => {
    handleRetry(row.task_id)
  }).catch((action) => {
    if (action === 'cancel') {
      handleEditAndRetry(row)
    }
  })
}

const fillFormFromTask = (row) => {
  // 基础配置
  scrapeForm.value.url = row.url
  scrapeForm.value.priority = row.priority || 1
  
  // 深度拷贝 params 和 cache，避免引用问题
  const params = JSON.parse(JSON.stringify(row.params || {}))
  const cache = JSON.parse(JSON.stringify(row.cache || { enabled: true, ttl: 3600 }))
  
  scrapeForm.value.cache = cache
  
  // 确保所有必要的参数结构都存在，并从原任务中复制
  scrapeForm.value.params = {
    engine: params.engine || 'playwright',
    wait_for: params.wait_for || 'networkidle',
    wait_time: params.wait_time || 3000,
    timeout: params.timeout || 30000,
    selector: params.selector || '',
    screenshot: params.screenshot !== undefined ? params.screenshot : true,
    is_fullscreen: params.is_fullscreen || false,
    block_images: params.block_images || false,
    block_media: params.block_media || false,
    user_agent: params.user_agent || '',
    viewport: params.viewport || { width: 1920, height: 1080 },
    proxy: params.proxy || { server: '', username: '', password: '' },
    cookies: (function() {
      const c = params.cookies;
      if (!c) return '';
      if (typeof c === 'object') return JSON.stringify(c);
      return String(c);
    })(),
    stealth: params.stealth !== undefined ? params.stealth : true,
    storage_type: params.storage_type || 'mongo',
    mongo_collection: params.mongo_collection || '',
    oss_path: params.oss_path || '',
    save_html: params.save_html !== undefined ? params.save_html : true,
    parser: params.parser || '',
    parser_config: params.parser_config || { mode: 'detail', fields: ['title', 'content'] },
    intercept_apis: params.intercept_apis || [],
    intercept_continue: params.intercept_continue || false
  }

  // 特殊处理解析器配置的 UI 绑定
  if (scrapeForm.value.params.parser === 'llm') {
    selectedLlmFields.value = scrapeForm.value.params.parser_config.fields || []
  } else if (scrapeForm.value.params.parser === 'xpath') {
    const rules = scrapeForm.value.params.parser_config.rules || {}
    xpathRules.value = Object.entries(rules).map(([field, path]) => ({ field, path }))
  }
}

const handleEditAndRetry = (row) => {
  isRetryEdit.value = true
  retryTaskId.value = row.task_id
  submitMode.value = 'single'
  activeConfigTab.value = 'basic'
  
  fillFormFromTask(row)

  showScrapeDialog.value = true
}

const handleCopyTask = (row) => {
  isRetryEdit.value = false
  retryTaskId.value = ''
  submitMode.value = 'single'
  activeConfigTab.value = 'basic'
  
  fillFormFromTask(row)

  showScrapeDialog.value = true
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
    // 重置已加载的 HTML 状态
    loadingHtml.value = false
    
    // 默认不加载 HTML 和截图，只有切换到对应标签页时才加载（或者由用户点击加载）
    const data = await getTask(task.task_id, { include_html: false, include_screenshot: false })
    currentTask.value = data
    activeTab.value = 'info'
    showTaskDialog.value = true
  } catch (error) {
    ElMessage.error('获取任务详情失败')
  }
}

// 监听标签页切换，按需加载大数据字段
watch(activeTab, async (newTab) => {
  if (!currentTask.value) return
  
  const taskId = currentTask.value.task_id
  const result = currentTask.value.result || {}
  
  if (newTab === 'html') {
    // 如果已经有 HTML 内容或者是正在加载，则跳过
    if (result.html || loadingHtml.value) return
    
    loadingHtml.value = true
    try {
      // 后端 getTask API 会自动从 OSS 加载内容并返回在 result.html 中
      const data = await getTask(taskId, { include_html: true , include_screenshot: false})
      if (data.result?.html) {
        currentTask.value.result.html = data.result.html
      }
    } catch (e) {
      console.error('加载 HTML 失败:', e)
      ElMessage.error('加载 HTML 源码失败')
    } finally {
      loadingHtml.value = false
    }
  } else if (newTab === 'screenshot' && !result.screenshot) {
    loadingScreenshot.value = true
    try {
      // 后端 getTask API 会自动从 OSS 加载内容并返回在 result.screenshot 中
      const data = await getTask(taskId, { include_screenshot: true, include_html: false })
      if (data.result?.screenshot) {
        currentTask.value.result.screenshot = data.result.screenshot
      }
    } catch (e) {
      console.error('加载截图失败:', e)
      ElMessage.error('加载截图失败')
    } finally {
      loadingScreenshot.value = false
    }
  }
})

const submitTask = async () => {
  // 验证输入
  if (submitMode.value === 'single' && !scrapeForm.value.url) {
    ElMessage.warning('请输入目标 URL')
    return
  }
  
  // GNE 列表模式必填验证
  if (scrapeForm.value.params.parser === 'gne' && 
      scrapeForm.value.params.parser_config?.mode === 'list' && 
      !scrapeForm.value.params.parser_config?.list_xpath) {
    ElMessage.warning('GNE 列表模式下，列表项 XPath 为必填项')
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
        const mode = data.params.parser_config?.mode || 'detail'
        const list_xpath = data.params.parser_config?.list_xpath
        data.params.parser_config = { mode }
        if (mode === 'list' && list_xpath) {
          data.params.parser_config.list_xpath = list_xpath
        }
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

    if (submitMode.value === 'single') {
      const submitData = processParams(baseConfig)
      
      if (isRetryEdit.value) {
        // 编辑并重试模式
        retryTask(retryTaskId.value, submitData).then(() => {
          ElMessage.success('任务已更新并重新提交')
          loadTasks()
        }).catch(error => {
          ElMessage.error('重试失败: ' + (error.response?.data?.detail || error.message))
        })
      } else {
        // 新建异步任务模式
        scrapeAsync(submitData).then(() => {
          ElMessage.success('任务提交成功 (异步)')
          loadTasks()
        }).catch(error => {
          ElMessage.error('提交失败: ' + (error.response?.data?.detail || error.message))
        })
      }
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
  isRetryEdit.value = false
  retryTaskId.value = ''
  scrapeForm.value = {
    url: '',
    params: {
      engine: 'playwright',
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
      parser_config: { mode: 'detail', fields: ['title', 'content'] },
      stealth: true,
      storage_type: 'mongo',
      save_html: true,
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
  lastCheckedDomain = ''
  matchedRules.value = []
  activeConfigTab.value = 'basic'
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
/* 匹配规则展示区样式 */
.matched-rules-section {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 20px;
}

.matched-rules-section .section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.matched-rules-section .header-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: #0f172a;
  font-size: 14px;
}

.matched-rules-section .header-title .el-icon {
  color: #3b82f6;
  font-size: 16px;
}

.matched-rules-section .header-tip {
  font-size: 12px;
  color: #64748b;
}

.rules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.rule-option-card {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  gap: 8px;
  position: relative;
}

.rule-option-card:hover {
  border-color: #3b82f6;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
  transform: translateY(-2px);
}

.rule-option-card.is-active {
  border-color: #3b82f6;
  background-color: #eff6ff;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
}

.rule-option-card.is-active::after {
  content: '✓';
  position: absolute;
  top: -8px;
  right: -8px;
  width: 20px;
  height: 20px;
  background: #3b82f6;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
}

.rule-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.rule-priority-tag {
  font-size: 11px;
  color: #94a3b8;
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
}

.rule-card-body .rule-domain-text {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.rule-desc-text {
  font-size: 12px;
  color: #64748b;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.mr-2 {
  margin-right: 8px;
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
  display: inline-flex !important;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  vertical-align: middle;
}

:deep(.el-form-item__label) {
  display: inline-flex !important;
  align-items: center;
  white-space: nowrap;
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
  font-weight: 600;
  color: #64748b;
}

.xpath-rule-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  background-color: #fff;
}

.xpath-rule-row:last-child {
  margin-bottom: 0;
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
  gap: 4px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #64748b;
  line-height: 1;
}

.stat-item .el-icon {
  font-size: 14px;
  color: #94a3b8;
}

.stat-item .label {
  color: #94a3b8;
  font-size: 13px;
  min-width: 32px;
}

.stat-tag {
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
  border: none;
}

.timing-row {
  align-items: center;
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
  font-size: 13px !important;
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
  gap: 4px;
}

.time-row {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 13px;
  color: #64748b;
}

.time-row .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.time-row .dot.create { background-color: #3b82f6; }
.time-row .dot.complete { background-color: #22c55e; }

.time-row .label {
  color: #94a3b8;
  min-width: 32px;
}

.time-row .time {
  font-family: 'JetBrains Mono', monospace;
  color: #475569;
}

/* 原有样式保持或替换 */
.custom-storage-fields {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

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

.label-box {
  display: flex;
  align-items: center;
  gap: 8px;
}

.label-box .el-icon {
  font-size: 16px;
  color: #64748b;
}

.tag-content-flex {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.storage-info-cell {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.storage-path-code {
  font-family: 'JetBrains Mono', monospace;
  background-color: #f1f5f9;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 13px;
  color: #475569;
  border: 1px solid #e2e8f0;
}

.value-content {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 24px;
}

.detail-descriptions :deep(.el-descriptions__label) {
  width: 130px;
  background-color: #f8fafc !important;
  color: #475569;
  font-weight: 600;
}

.tasks-container {
  padding: 20px;
}

.tasks-card {
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  margin-bottom: 24px;
}

.tasks-table :deep(.el-table__cell) {
  padding: 12px 0;
}

.tasks-table :deep(.el-table__header .el-table__cell) {
  background-color: #f8fafc;
  color: #475569;
  font-weight: 600;
  height: 50px;
}

.tasks-table :deep(.el-table__row) {
  transition: background-color 0.2s;
}

.tasks-table :deep(.el-table__row:hover > td) {
  background-color: #f1f5f9 !important;
}

.tasks-card:hover {
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
}

.el-button {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  border-radius: 8px;
}

.el-button:active {
  transform: scale(0.95);
}

.el-button--primary {
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}

.el-button--primary:hover {
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.3);
  transform: translateY(-1px);
}

.el-button--success {
  box-shadow: 0 4px 12px rgba(103, 194, 58, 0.2);
}

.el-button--success:hover {
  box-shadow: 0 6px 16px rgba(103, 194, 58, 0.3);
  transform: translateY(-1px);
}

.el-button--danger {
  box-shadow: 0 4px 12px rgba(245, 108, 108, 0.2);
}

.el-button--danger:hover {
  box-shadow: 0 6px 16px rgba(245, 108, 108, 0.3);
  transform: translateY(-1px);
}

.card-header {
  padding: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 12px;
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
  padding: 16px 20px;
  background-color: #fcfdfe;
  border-bottom: 1px solid #f1f5f9;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
}

.filter-form :deep(.el-form-item) {
  margin-bottom: 0;
  margin-right: 0;
}

.filter-form :deep(.el-form-item__label) {
  font-weight: 600;
  color: #475569;
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
  white-space: normal;
  line-height: 1.4;
}

.oss-path-info {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.oss-path-info .el-link {
  flex: 1;
  word-break: break-all;
  white-space: normal;
  line-height: 1.4;
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

.storage-info-cell {
  display: flex;
  align-items: center;
  gap: 4px;
}

.help-icon, .help-icon-inline {
  font-size: 14px;
  color: #909399;
  cursor: help;
}

.help-icon-inline {
  font-size: 13px;
}
</style>
