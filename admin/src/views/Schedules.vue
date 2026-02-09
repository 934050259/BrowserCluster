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
              <el-tag v-if="row.schedule_type === 'interval'" type="info" size="small" class="policy-tag">
                每隔 {{ formatInterval(row.interval) }} 执行一次
              </el-tag>
              <el-tag v-else-if="row.schedule_type === 'cron'" type="warning" size="small" class="policy-tag">
                Cron: {{ row.cron }}
              </el-tag>
              <el-tag v-else-if="row.schedule_type === 'once'" type="success" size="small" class="policy-tag">
                定时: {{ row.once_time }}
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

        <el-table-column label="执行时间" width="250">
          <template #default="{ row }">
            <div class="execution-times">
              <div class="time-item">
                <span class="label">最近执行:</span>
                <span class="value">{{ formatDate(row.last_run) || '-' }}</span>
              </div>
              <div class="time-item" v-if="row.status === 'active'">
                <span class="label">下次执行:</span>
                <span class="value">{{ formatDate(row.next_run) || '-' }}</span>
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
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
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
              <el-form-item label="任务名称" prop="name" required>
                <el-input v-model="form.name" placeholder="请输入任务名称" />
              </el-form-item>

              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="任务优先级">
                    <el-select v-model="form.priority" style="width: 100%">
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
                    <el-radio-group v-model="form.params.storage_type" size="default">
                      <el-radio-button label="mongo">MongoDB</el-radio-button>
                      <el-radio-button label="oss">OSS 存储</el-radio-button>
                    </el-radio-group>

                    <div class="custom-storage-fields mt-2" v-if="form.params.storage_type">
                      <template v-if="form.params.storage_type === 'mongo'">
                        <div class="storage-input-group">
                          <div class="input-label-tip">自定义 MongoDB 集合名</div>
                          <el-input 
                            v-model="form.params.mongo_collection" 
                            placeholder="例如: my_collection"
                            size="small"
                            clearable
                          >
                            <template #prefix><el-icon><Collection /></el-icon></template>
                          </el-input>
                        </div>
                        <div class="storage-path-preview">
                          <el-icon><InfoFilled /></el-icon>
                          <span>实际存储集合: <code>{{ form.params.mongo_collection || 'tasks_results' }}</code></span>
                        </div>
                      </template>

                      <template v-if="form.params.storage_type === 'oss'">
                        <div class="storage-input-group">
                          <div class="input-label-tip">自定义 OSS 存储路径</div>
                          <el-input 
                            v-model="form.params.oss_path" 
                            placeholder="例如: custom/path/"
                            size="small"
                            clearable
                          >
                            <template #prefix><el-icon><FolderOpened /></el-icon></template>
                          </el-input>
                        </div>
                        <div class="storage-path-preview">
                          <el-icon><InfoFilled /></el-icon>
                          <span>实际存储路径: <code>{{ form.params.oss_path ? (form.params.oss_path.endsWith('/') ? form.params.oss_path : form.params.oss_path + '/') : 'tasks/' }}{任务ID}/...</code></span>
                        </div>
                      </template>
                    </div>

                    <div class="form-item-tip">
                      <template v-if="form.params.storage_type === 'oss'">
                        请确保已在 <el-link type="primary" :underline="false" @click="router.push('/configs')">系统设置</el-link> 中配置 OSS 凭据
                      </template>
                      <template v-else>
                        结果将直接存储在 MongoDB 数据库中
                      </template>
                    </div>
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="20" v-if="form.cache">
                <el-col :span="12">
                  <el-form-item label="数据缓存">
                    <div class="switch-container">
                      <el-switch v-model="form.cache.enabled" />
                      <span class="switch-tip">{{ form.cache.enabled ? '开启 (节省资源)' : '关闭 (实时抓取)' }}</span>
                    </div>
                  </el-form-item>
                </el-col>
                <el-col :span="12" v-if="form.cache.enabled">
                  <el-form-item label="缓存有效期 (TTL/秒)">
                    <el-input-number v-model="form.cache.ttl" :min="60" :step="60" controls-position="right" style="width: 100%" />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-form-item label="目标 URL" prop="url" required>
                <el-input v-model="form.url" placeholder="https://example.com" clearable>
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

              <el-form-item label="任务描述" prop="description">
                <el-input v-model="form.description" type="textarea" :rows="2" placeholder="请输入任务描述" />
              </el-form-item>
              
              <el-form-item label="Cookies" v-if="form.params">
                <div class="cookies-input-wrapper">
                  <el-input
                    v-model="form.params.cookies"
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
              <!-- 匹配规则展示区已移至基础配置 -->

              <el-form-item label="解析模式" v-if="form.params">
                <el-radio-group v-model="form.params.parser" size="default">
                  <el-radio-button label="">不解析</el-radio-button>
                  <el-radio-button label="gne">智能解析 (GAE)</el-radio-button>
                  <el-radio-button label="llm">大模型提取 (LLM)</el-radio-button>
                  <el-radio-button label="xpath">自定义规则 (XPath)</el-radio-button>
                </el-radio-group>
              </el-form-item>

              <div v-if="form.params && form.params.parser === 'gne'" class="parser-config-area">
                <el-form-item label="提取模式">
                  <el-radio-group v-model="form.params.parser_config.mode" size="small">
                    <el-radio-button label="detail">详情模式</el-radio-button>
                    <el-radio-button label="list">列表模式</el-radio-button>
                  </el-radio-group>
                </el-form-item>

                <el-form-item 
                  v-if="form.params.parser_config.mode === 'list'" 
                  label="列表项 XPath" 
                  prop="params.parser_config.list_xpath"
                  required
                >
                  <el-input 
                    v-model="form.params.parser_config.list_xpath" 
                    placeholder="例如: /html/body/div/div/ul/li[1]/a"
                  >
                    <template #prefix>
                      <el-icon><Search /></el-icon>
                    </template>
                  </el-input>
                  <div class="input-tip">
                    <el-icon><InfoFilled /></el-icon>
                    GNE 列表模式必须指定一个代表性的列表项标题 XPath
                  </div>
                </el-form-item>

                <el-alert 
                  :title="form.params.parser_config.mode === 'list' ? 'GAE 列表模式' : 'GAE 详情模式'" 
                  type="info" 
                  :closable="false" 
                  show-icon 
                  :description="form.params.parser_config.mode === 'list' ? '自动识别并提取新闻、博客列表页中的标题、链接及发布日期。' : '适用于新闻、博客等文章类页面，自动提取标题、作者、发布时间、正文和图片。'" 
                />
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
                  <el-form-item label="浏览器引擎">
                    <el-select v-model="form.params.engine" style="width: 100%">
                      <el-option label="Playwright (默认)" value="playwright" />
                      <el-option label="DrissionPage (过盾强)" value="drissionpage" />
                    </el-select>
                  </el-form-item>
                </el-col>
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
                  <el-form-item label="渲染超时 (s)">
                    <el-input-number 
                      :model-value="form.params.timeout / 1000" 
                      @update:model-value="val => form.params.timeout = val * 1000"
                      :min="5" 
                      :step="5" 
                      style="width: 100%" 
                    />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-form-item label="视口尺寸 (分辨率)">
                <div class="viewport-input">
                  <el-input-number v-model="form.params.viewport.width" :min="320" placeholder="宽度" controls-position="right" />
                  <span class="sep">×</span>
                  <el-input-number v-model="form.params.viewport.height" :min="240" placeholder="高度" controls-position="right" />
                </div>
              </el-form-item>

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
                    <span class="feature-name">保存 HTML</span>
                    <span class="feature-desc">将完整的网页源码保存到数据库或 OSS</span>
                  </div>
                  <el-switch v-model="form.params.save_html" />
                </div>
                <div class="feature-item">
                  <div class="feature-info">
                    <span class="feature-name">自动截图</span>
                    <span class="feature-desc">保存网页快照用于调试或取证</span>
                  </div>
                  <el-switch v-model="form.params.screenshot" />
                </div>
                <div class="feature-item" v-if="form.params.screenshot">
                  <div class="feature-info">
                    <span class="feature-name">全屏快照</span>
                    <span class="feature-desc">捕获整个页面高度而不仅是可视区域</span>
                  </div>
                  <el-switch v-model="form.params.is_fullscreen" />
                </div>
                <div class="feature-item">
                  <div class="feature-info">
                    <span class="feature-name">屏蔽图片/媒体</span>
                    <span class="feature-desc">不加载图片和视频资源，加快抓取速度</span>
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
                <div class="section-title">接口拦截配置</div>
                <el-form-item label="拦截接口 URL 模式">
                  <el-select
                  v-model="form.params.intercept_apis"
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
                    <el-switch v-model="form.params.intercept_continue" />
                    <span class="switch-tip">{{ form.params.intercept_continue ? '开启 (正常加载页面)' : '关闭 (拦截并停止, 节省流量)' }}</span>
                  </div>
                </el-form-item>

                <el-divider />

                <div class="section-title">代理配置</div>
                <el-form-item label="代理服务器" v-if="form.params.proxy">
                  <el-input v-model="form.params.proxy.server" placeholder="http://proxy.example.com:8080" clearable />
                </el-form-item>
                
                <template v-if="form.params.proxy && form.params.proxy.server">
                  <el-collapse-transition>
                    <el-row :gutter="20" v-if="form.params.engine !== 'drissionpage'">
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
                  
                  <el-alert
                    v-if="form.params.engine === 'drissionpage'"
                    title="代理说明"
                    type="info"
                    description="DrissionPage 引擎目前仅支持无账密代理（IP:Port 格式）。如需使用账密认证代理，请切换至 Playwright 引擎。"
                    show-icon
                    :closable="false"
                    style="margin-top: 10px;"
                  />
                </template>
              </div>
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
                    <el-radio-button label="once">指定时间</el-radio-button>
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

                  <el-form-item v-if="form.schedule_type === 'cron'" prop="cron">
                    <template #label>
                      <div class="label-with-help">
                        <span>Cron 表达式</span>
                        <el-tooltip content="点击右侧『常用示例』查看各字段含义" placement="top">
                          <el-icon class="help-icon"><QuestionFilled /></el-icon>
                        </el-tooltip>
                      </div>
                    </template>
                    <el-input v-model="form.cron" placeholder="*/5 * * * * (每 5 分钟执行一次)">
                      <template #append>
                        <el-button @click="openCronHelper">常用示例</el-button>
                      </template>
                    </el-input>
                    <div class="input-tip">
                      <el-icon><InfoFilled /></el-icon>
                      支持 5 位 (分 时 日 月 周) 或 6 位 (秒 分 时 日 月 周) 表达式
                    </div>
                  </el-form-item>

                  <el-form-item v-if="form.schedule_type === 'once'" label="执行时间" prop="once_time">
                    <el-date-picker
                      v-model="form.once_time"
                      type="datetime"
                      placeholder="选择具体执行时间"
                      style="width: 100%"
                      value-format="YYYY-MM-DD HH:mm:ss"
                    />
                    <div class="input-tip">任务将在设定的时间点执行一次</div>
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
  once_time: '',
  priority: 5,
  params: {
    engine: 'playwright',
    wait_for: 'networkidle',
    wait_time: 3000,
    timeout: 30000,
    screenshot: true,
    is_fullscreen: false,
    block_images: false,
    block_media: false,
    viewport: {
      width: 1920,
      height: 1080
    },
    parser: '',
    parser_config: {
      mode: 'detail',
      list_xpath: '',
      fields: ['title', 'content']
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
    intercept_apis: [],
    intercept_continue: false
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
  cron: [{ required: true, message: '请输入 Cron 表达式', trigger: 'blur' }],
  once_time: [{ required: true, message: '请选择执行时间', trigger: 'change' }]
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
const selectedRuleId = ref(null)
const matchedCookies = ref(false)
let lastCheckedDomain = ''
let debounceTimer = null

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
  selectedRuleId.value = rule.id
  
  // 确保 parser_config 对象存在
  if (!form.value.params.parser_config) {
    form.value.params.parser_config = {
      mode: 'detail',
      fields: []
    }
  }

  if (rule.cache_config) {
    form.value.cache.enabled = rule.cache_config.enabled
    form.value.cache.ttl = rule.cache_config.ttl
  }

  if (rule.parser_type === 'llm') {
    const fields = rule.parser_config.fields || []
    selectedLlmFields.value = [...fields]
    form.value.params.parser_config.fields = [...fields]
    form.value.params.parser_config.mode = rule.parser_config.mode || 'detail'
  } else if (rule.parser_type === 'xpath') {
    const rules = rule.parser_config.rules || {}
    xpathRules.value = Object.entries(rules).map(([field, path]) => ({ name: field, xpath: path }))
    form.value.params.parser_config.rules = { ...rules }
  } else if (rule.parser_type === 'gne') {
    form.value.params.parser_config.mode = rule.parser_config.mode || 'detail'
    if (rule.parser_config.mode === 'list') {
      form.value.params.parser_config.list_xpath = rule.parser_config.list_xpath || ''
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
        form.value.params[field] = JSON.parse(JSON.stringify(rule[field]))
      } else {
        form.value.params[field] = rule[field]
      }
    }
  })

  if (!silent) {
    ElMessage.success(`已应用 ${rule.domain} 的解析配置`)
  }
}

// 监听标签页切换
watch(activeTab, async (newTab) => {
  if (newTab === 'parser' && form.value.url && form.value.url.startsWith('http')) {
    // 不再在此处触发自动加载，仅在 URL 输入时触发
    // 如果没有匹配规则，尝试获取规则列表供手动选择，但不自动应用
    if (!matchedRules.value.length) {
      try {
        const urlObj = new URL(form.value.url)
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

// 监听 URL 变化，自动获取匹配规则
watch(() => form.value.url, (newUrl) => {
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
              matchedCookies.value = false
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
    `<div class="cron-helper-content">
      <p><strong>常用示例：</strong></p>
      <ul class="mb-4">
        <li><code>0 0 * * *</code>: 每天凌晨</li>
        <li><code>*/5 * * * *</code>: 每 5 分钟</li>
        <li><code>0 9 * * 1-5</code>: 工作日早上 9 点</li>
        <li><code>0 0 1 * *</code>: 每月 1 号凌晨</li>
      </ul>
      <p><strong>字段含义：</strong></p>
      <table class="cron-table">
        <thead>
          <tr><th>位置</th><th>含义</th><th>取值范围</th></tr>
        </thead>
        <tbody>
          <tr><td>1</td><td>分钟</td><td>0-59</td></tr>
          <tr><td>2</td><td>小时</td><td>0-23</td></tr>
          <tr><td>3</td><td>日期</td><td>1-31</td></tr>
          <tr><td>4</td><td>月份</td><td>1-12</td></tr>
          <tr><td>5</td><td>星期</td><td>0-6 (周日为0)</td></tr>
        </tbody>
      </table>
      <p class="mt-2 text-xs text-gray-500">* 部分系统支持 6 位格式，第 1 位为“秒”。</p>
    </div>`,
    'Cron 表达式助手',
    { 
      dangerouslyUseHTMLString: true,
      customClass: 'cron-helper-dialog'
    }
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
    once_time: '',
    priority: 5,
    params: {
      engine: 'playwright',
      wait_for: 'networkidle',
      wait_time: 3000,
      timeout: 30000,
      screenshot: true,
      is_fullscreen: false,
      block_images: false,
      block_media: false,
      viewport: {
        width: 1920,
        height: 1080
      },
      parser: '',
      parser_config: {
        mode: 'detail',
        list_xpath: '',
        fields: ['title', 'content']
      },
      proxy: {
        server: '',
        username: '',
        password: ''
      },
      cookies: '',
      stealth: true,
      storage_type: 'mongo',
      save_html: true,
      intercept_apis: [],
      intercept_continue: false
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
  
  if (form.value.once_time === undefined) {
    form.value.once_time = ''
  }
  
  // 确保 engine 参数存在 (兼容旧数据)
  if (!form.value.params) {
    form.value.params = { engine: 'playwright' }
  } else if (!form.value.params.engine) {
    form.value.params.engine = 'playwright'
  }
  
  if (!form.value.params.storage_type) {
    form.value.params.storage_type = 'mongo'
  }
  
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
      engine: 'playwright',
      wait_for: 'networkidle',
      wait_time: 3000,
      timeout: 30000,
      screenshot: true,
      is_fullscreen: false,
      block_images: false,
      block_media: false,
      viewport: {
        width: 1920,
        height: 1080
      },
      parser: '',
      parser_config: {
        fields: ['title', 'content']
      },
      proxy: {
        server: '',
        username: '',
        password: ''
      },
      cookies: '',
      stealth: true,
      storage_type: 'mongo',
      save_html: true,
      intercept_apis: [],
      intercept_continue: false
    }
  } else {
    // 补全缺失字段
    const defaultParams = {
      engine: 'playwright',
      wait_for: 'networkidle',
      wait_time: 3000,
      timeout: 30000,
      screenshot: true,
      is_fullscreen: false,
      block_images: false,
      block_media: false,
      viewport: {
        width: 1920,
        height: 1080
      },
      parser: '',
      stealth: true,
      storage_type: 'mongo',
      save_html: true,
      intercept_apis: [],
      intercept_continue: false,
      proxy: { server: '', username: '', password: '' }
    }
    
    if (!form.value.params.parser_config) {
      form.value.params.parser_config = { mode: 'detail', list_xpath: '', fields: ['title', 'content'] }
    } else {
      if (!form.value.params.parser_config.mode) form.value.params.parser_config.mode = 'detail'
      if (form.value.params.parser_config.list_xpath === undefined) form.value.params.parser_config.list_xpath = ''
    }
    
    Object.keys(defaultParams).forEach(key => {
      if (form.value.params[key] === undefined) {
        form.value.params[key] = defaultParams[key]
      }
    })
    
    if (!form.value.params.viewport) {
      form.value.params.viewport = { width: 1920, height: 1080 }
    }
    if (!form.value.params.proxy) {
      form.value.params.proxy = { server: '', username: '', password: '' }
    }
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
        const submitData = JSON.parse(JSON.stringify(form.value))
        
        // 根据调度类型清理数据
        if (submitData.schedule_type === 'interval') {
          let totalSeconds = intervalValue.value
          if (intervalUnit.value === 'm') totalSeconds *= 60
          else if (intervalUnit.value === 'h') totalSeconds *= 3600
          else if (intervalUnit.value === 'd') totalSeconds *= 86400
          submitData.interval = totalSeconds
          submitData.cron = null
          submitData.once_time = null
        } else if (submitData.schedule_type === 'cron') {
          submitData.interval = null
          submitData.once_time = null
        } else if (submitData.schedule_type === 'once') {
          submitData.interval = null
          submitData.cron = null
        }

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
          const mode = submitData.params.parser_config?.mode || 'detail'
          const list_xpath = submitData.params.parser_config?.list_xpath || ''
          
          if (mode === 'list' && !list_xpath) {
            ElMessage.warning('GNE 列表模式下，列表项 XPath 为必填项')
            submitting.value = false
            return
          }
          
          submitData.params.parser_config = { mode, list_xpath }
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

        // 处理拦截配置
        if (!submitData.params.intercept_apis || submitData.params.intercept_apis.length === 0) {
          submitData.params.intercept_apis = null
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
.schedules-container {
  padding: 20px;
}

.schedules-card {
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.schedules-card:hover {
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background-color: #fff;
  border-bottom: 1px solid #f1f5f9;
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

.name-column {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-left: 10px;
}

.schedule-name {
  font-weight: 600;
  color: #334155;
  font-size: 14px;
}

.schedule-desc {
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.4;
}

.filter-bar {
  padding: 16px 20px;
  background-color: #fcfdfe;
  border-bottom: 1px solid #f1f5f9;
}

.filter-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.filter-form :deep(.el-form-item__label) {
  font-weight: 600;
  color: #475569;
}

.schedules-table :deep(.el-table__cell) {
  padding: 12px 0;
}

.schedules-table :deep(.el-table__header .el-table__cell) {
  background-color: #f8fafc;
  color: #475569;
  font-weight: 600;
  height: 50px;
}

.schedules-table :deep(.el-table__row) {
  transition: background-color 0.2s;
}

.schedules-table :deep(.el-table__row:hover > td) {
  background-color: #f1f5f9 !important;
}

.url-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 500;
  max-width: 100%;
}

.url-link :deep(.el-link__inner) {
  display: inline-block;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.schedule-policy {
  flex-direction: column;
  gap: 4px;
}

.policy-tag {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
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

.execution-times {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.time-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #64748b;
}

.time-item .label {
  color: #94a3b8;
}

.time-item .value {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  color: #475569;
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

.parser-config-area {
  margin-top: 20px;
  padding: 16px;
  background-color: #f8fafc;
  border-radius: 8px;
  border: 1px solid #f1f5f9;
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

/* Cron Helper Styles */
:global(.cron-helper-dialog) {
  max-width: 450px !important;
}

:global(.cron-helper-content) {
  line-height: 1.6;
}

:global(.cron-table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  font-size: 13px;
}

:global(.cron-table th),
:global(.cron-table td) {
  border: 1px solid #e2e8f0;
  padding: 8px;
  text-align: left;
}

:global(.cron-table th) {
  background-color: #f8fafc;
  font-weight: 600;
  color: #475569;
}

:global(.cron-table td) {
  color: #1e293b;
}

:global(.cron-helper-content code) {
  background-color: #f1f5f9;
  padding: 2px 4px;
  border-radius: 4px;
  font-family: monospace;
  color: #ef4444;
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

.mb-4 { margin-bottom: 1rem; }
.mt-2 { margin-top: 0.5rem; }
.text-xs { font-size: 0.75rem; }
.text-gray-500 { color: #6b7280; }
</style>
