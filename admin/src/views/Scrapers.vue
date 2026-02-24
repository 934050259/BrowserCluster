<template>
  <div class="scrapers-container">
    <div class="page-header">
      <div class="header-left">
        <h2>站点采集</h2>
        <p class="subtitle">管理列表页采集任务及自动发现规则</p>
      </div>
    </div>

    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <el-input
            v-model="searchQuery"
            placeholder="搜索任务名称或 URL"
            clearable
            class="search-input"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-button type="danger" :disabled="!selectedRows.length" @click="handleBatchDelete">
            <el-icon><Delete /></el-icon>批量删除
          </el-button>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            <span>添加采集任务</span>
          </el-button>
        </div>
        <div class="toolbar-right">
          <el-button @click="fetchData">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
      </div>

      <el-table 
        :data="pagedScrapers" 
        v-loading="loading" 
        style="width: 100%;"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="name" label="任务名称" min-width="150" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-switch
              v-model="row.enabled"
              @change="(val) => handleStatusChange(row, val)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="url" label="起始 URL" min-width="250" show-overflow-tooltip>
          <template #default="{ row }">
            <el-link :href="row.url" target="_blank" type="primary" :underline="false">
              {{ row.url }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column label="关联规则" min-width="150">
           <template #default="{ row }">
             <el-tag v-if="row.rule_id" type="success">{{ getRuleName(row.rule_id) }}</el-tag>
             <span v-else class="text-gray">-</span>
           </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="最后修改" width="180">
          <template #default="{ row }">
            {{ formatTime(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="300" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button 
                type="success" 
                size="small" 
                @click="handleRun(row)" 
                :loading="runningScrapers.has(row._id)"
                icon="VideoPlay"
              >
                {{ runningScrapers.has(row._id) ? '正在测试' : '测试' }}
              </el-button>
              <el-button 
                type="info" 
                size="small" 
                @click="handleViewResults(row)"
                icon="Search"
              >
                数据
              </el-button>
              <el-button type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
              <el-button type="danger" size="small" @click="handleDelete(row)">删除</el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="filteredScrapers.length"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <el-dialog 
      v-model="dialogVisible" 
      :title="isEdit ? '编辑采集任务' : '添加采集任务'" 
      width="850px"
      destroy-on-close
      top="5vh"
      class="scraper-dialog"
    >
      <el-form :model="form" label-width="120px" :rules="formRules" ref="formRef">
        <el-tabs v-model="activeTab" class="config-tabs">
          <!-- 1. 基础设置 -->
          <el-tab-pane name="basic">
            <template #label>
              <span class="tab-label">
                <el-icon class="icon-basic"><Link /></el-icon>
                <span>基础设置</span>
              </span>
            </template>
            <div class="tab-content">
              <div class="section-group">
                <div class="section-header">
                  <div class="section-title">任务信息</div>
                </div>
                
                <el-form-item label="起始 URL" prop="url">
                  <el-input v-model="form.url" placeholder="请输入列表页抓取地址，如: https://news.example.com/list" clearable>
                    <template #prefix><el-icon class="icon-link"><Connection /></el-icon></template>
                  </el-input>
                </el-form-item>

                <el-form-item label="任务名称" prop="name">
                  <el-input v-model="form.name" placeholder="请输入采集任务名称，如：新闻列表抓取" clearable>
                    <template #prefix><el-icon><InfoFilled /></el-icon></template>
                  </el-input>
                </el-form-item>

                <el-form-item label="关联规则">
                  <div class="rule-select-container">
                    <el-select v-model="form.rule_id" placeholder="选择详情页解析规则" clearable style="flex: 1">
                      <el-option 
                        v-for="rule in filteredRules" 
                        :key="rule.id" 
                        :label="rule.domain + (rule.description ? ' (' + rule.description + ')' : '')" 
                        :value="rule.id" 
                      />
                    </el-select>
                    <el-button 
                      v-if="filteredRules.length === 0 && form.url" 
                      type="primary" 
                      link 
                      @click="goToRuleConfig"
                      class="ml-2"
                      :loading="isNavigating"
                    >
                      <el-icon v-if="!isNavigating"><Setting /></el-icon>去配置规则
                    </el-button>
                  </div>
                  <div class="input-tip" style="color: rgb(238, 118, 82);">
                    <span v-if="currentDomain">已按域名 <code>{{ currentDomain }}</code> 自动筛选。</span>
                    <span>选择用于解析详情页的网站配置规则。</span>
                  </div>
                </el-form-item>

                <el-form-item label="任务描述">
                  <el-input v-model="form.description" type="textarea" :rows="2" placeholder="可选：对该采集任务的补充说明" clearable />
                </el-form-item>

                <el-form-item label="Cookies">
                  <div class="cookies-input-wrapper">
                    <el-input
                      v-model="form.params.cookies"
                      type="textarea"
                      :rows="3"
                      placeholder="输入 Cookies 字符串或 JSON 格式，如：key1=value1; key2=value2"
                      clearable
                    />
                  </div>
                </el-form-item>

                <el-row :gutter="20">
                  <el-col :span="12">
                    <el-form-item label="存储位置">
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
                        </template>
                      </div>
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="任务状态">
                      <div class="switch-container">
                        <el-switch v-model="form.enabled" />
                        <span class="switch-tip">{{ form.enabled ? '已启用' : '已禁用' }}</span>
                      </div>
                    </el-form-item>
                  </el-col>
                </el-row>

                <div class="section-header mt-4">
                  <div class="section-title">重试与缓存</div>
                </div>
                <el-row :gutter="20">
                  <el-col :span="12">
                    <el-form-item label="数据缓存">
                      <div class="switch-container">
                        <el-switch v-model="form.cache.enabled" />
                        <el-input-number 
                          v-if="form.cache.enabled"
                          v-model="form.cache.ttl" 
                          :min="60" 
                          size="small"
                          style="width: 120px; margin-left: 10px"
                        />
                        <span class="switch-tip" v-if="form.cache.enabled">秒 (TTL)</span>
                        <span class="switch-tip" v-else>关闭缓存</span>
                      </div>
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="失败重试">
                      <div class="switch-container">
                        <el-switch v-model="form.retry_enabled" />
                        <el-input-number 
                          v-if="form.retry_enabled"
                          v-model="form.max_retries" 
                          :min="1" 
                          :max="10"
                          size="small"
                          style="width: 100px; margin-left: 10px"
                        />
                        <span class="switch-tip" v-if="form.retry_enabled">次</span>
                        <span class="switch-tip" v-else>不重试</span>
                      </div>
                    </el-form-item>
                  </el-col>
                </el-row>
              </div>
            </div>
          </el-tab-pane>

          <!-- 2. 提取规则 -->
          <el-tab-pane name="rules">
            <template #label>
              <span class="tab-label">
                <el-icon class="icon-parser"><Operation /></el-icon>
                <span>提取规则</span>
              </span>
            </template>
            <div class="tab-content">
              <div class="section-group">
                <div class="section-header">
                  <div class="section-title">列表项定位</div>
                  <el-button 
                    type="primary" 
                    size="small"
                    @click="handleAiGenerate" 
                    :loading="aiGenerating" 
                    :icon="MagicStick"
                  >
                    AI 智能生成规则
                  </el-button>
                </div>
                
                <el-form-item label="列表容器" prop="list_xpath">
                  <el-input v-model="form.list_xpath" placeholder="例如: //div[@class='news-item']" clearable>
                    <template #prefix><el-icon><Search /></el-icon></template>
                  </el-input>
                  <div class="input-tip">列表项的公共父级容器或每个列表项的 XPath 表达式</div>
                </el-form-item>
              </div>

              <div class="section-group">
                <div class="section-header">
                  <div class="section-title">字段提取 (相对容器)</div>
                </div>

                <el-row :gutter="20">
                  <el-col :span="12">
                    <el-form-item label="标题 XPath" prop="title_xpath">
                      <el-input v-model="form.title_xpath" placeholder="例如: .//a/text()" clearable />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="链接 XPath" prop="link_xpath">
                      <el-input v-model="form.link_xpath" placeholder="例如: .//a/@href" clearable />
                    </el-form-item>
                  </el-col>
                </el-row>

                <el-row :gutter="20">
                  <el-col :span="12">
                    <el-form-item label="发布时间">
                      <el-input v-model="form.time_xpath" placeholder="例如: .//span/text()" clearable />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="最大抓取页数">
                      <el-input-number v-model="form.max_pages" :min="1" :max="100" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                </el-row>

                <el-form-item label="下一页 XPath">
                  <el-input v-model="form.pagination_next_xpath" placeholder="例如: //a[contains(text(), '下一页')]" clearable />
                  <div class="input-tip">可选：用于自动翻页抓取的“下一页”按钮 XPath</div>
                </el-form-item>
                
                <div class="rules-footer mt-4">
                  <el-button type="warning" @click="handleTest(false)" :loading="testing" icon="VideoPlay">规则校验</el-button>
                  <span class="input-tip">建议在保存前校验 XPath 规则，确保能正确提取数据</span>
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
                <div class="section-header">
                  <div class="section-title">引擎与渲染</div>
                </div>

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
                </el-row>

                <el-row :gutter="20">
                  <el-col :span="12">
                    <el-form-item label="渲染超时 (s)">
                      <el-input-number 
                        :model-value="form.params.timeout / 1000" 
                        @update:model-value="val => form.params.timeout = val * 1000"
                        :min="5" 
                        :max="300" 
                        style="width: 100%" 
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="额外等待 (ms)">
                      <el-input-number v-model="form.params.wait_time" :min="0" :step="500" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                </el-row>

                <el-form-item label="等待元素">
                  <el-input v-model="form.params.wait_for_selector" placeholder="例如: .content-loaded (等待该 CSS 选择器出现)" clearable />
                </el-form-item>

                <el-form-item label="User-Agent">
                  <el-input v-model="form.params.user_agent" placeholder="自定义 User-Agent 字符串，不填则使用默认" clearable />
                </el-form-item>

                <el-form-item label="窗口尺寸">
                  <div class="viewport-input">
                    <el-input-number v-model="form.params.viewport.width" :min="320" placeholder="宽度" controls-position="right" />
                    <span class="sep">×</span>
                    <el-input-number v-model="form.params.viewport.height" :min="240" placeholder="高度" controls-position="right" />
                  </div>
                </el-form-item>

                <div class="feature-settings mt-4">
                  <div class="feature-item">
                    <div class="feature-info">
                      <span class="feature-name">启用反检测 (Stealth)</span>
                      <span class="feature-desc">使用 Stealth 插件防止被网站识别为爬虫</span>
                    </div>
                    <el-switch v-model="form.params.stealth" />
                  </div>
                  <div class="feature-item">
                    <div class="feature-info">
                      <span class="feature-name">屏蔽图片/媒体</span>
                      <span class="feature-desc">不加载图片和视频资源，加快抓取速度</span>
                    </div>
                    <el-switch v-model="form.params.block_images" />
                  </div>
                  <div class="feature-item">
                    <div class="feature-info">
                      <span class="feature-name">不加载 CSS</span>
                      <span class="feature-desc">禁止加载样式表，建议仅在 XPath 规则不受影响时开启</span>
                    </div>
                    <el-switch v-model="form.params.no_css" />
                  </div>
                  <div class="feature-item">
                    <div class="feature-info">
                      <span class="feature-name">保存页面源码</span>
                      <span class="feature-desc">在存储中保存页面的完整 HTML 源码</span>
                    </div>
                    <el-switch v-model="form.params.save_html" />
                  </div>
                  <div class="feature-item">
                    <div class="feature-info">
                      <span class="feature-name">返回 Cookies</span>
                      <span class="feature-desc">任务完成后返回当前页面的 Cookies (字符串形式)</span>
                    </div>
                    <el-switch v-model="form.params.return_cookies" />
                  </div>
                  <div class="feature-item">
                    <div class="feature-info">
                      <span class="feature-name">页面截图</span>
                      <span class="feature-desc">采集完成后自动保存页面截图</span>
                    </div>
                    <el-switch v-model="form.params.screenshot" />
                  </div>
                  <div v-if="form.params.screenshot" class="feature-item">
                    <div class="feature-info">
                      <span class="feature-name">全屏截图</span>
                      <span class="feature-desc">是否截取整个滚动页面的完整高度</span>
                    </div>
                    <el-switch v-model="form.params.is_fullscreen" />
                  </div>
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
              <div class="section-group">
                <div class="section-header">
                  <div class="section-title">接口拦截配置</div>
                </div>
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

                <div class="section-header mt-4">
                  <div class="section-title">代理配置</div>
                </div>
                <el-form-item label="代理池分组">
                  <el-select 
                    v-model="form.params.proxy_pool_group" 
                    placeholder="不使用代理池" 
                    clearable 
                    filterable
                    allow-create
                    style="width: 100%"
                    @change="val => val && (form.params.proxy.server = '')"
                  >
                    <el-option 
                      v-for="group in proxyGroups" 
                      :key="group.name || group" 
                      :label="group.name ? `${group.name} (${group.active}/${group.total})` : group" 
                      :value="group.name || group" 
                    />
                  </el-select>
                  <div class="input-tip">选择代理池分组，抓取时将自动从该组中选择随机代理。使用代理池时，手动代理设置将失效。</div>
                  <el-alert
                    v-if="form.params.engine === 'drissionpage' && form.params.proxy_pool_group"
                    title="引擎限制"
                    type="warning"
                    description="DrissionPage 引擎目前仅支持无账密代理。请确保所选代理池分组中不包含需要账密认证的代理，否则可能会导致抓取失败。"
                    show-icon
                    :closable="false"
                    class="mt-2"
                  />
                </el-form-item>

                <el-form-item label="手动代理服务器">
                  <el-input 
                    v-model="form.params.proxy.server" 
                    placeholder="http://proxy.example.com:8080" 
                    clearable 
                    :disabled="!!form.params.proxy_pool_group"
                  />
                  <div class="input-tip" v-if="form.params.proxy_pool_group">使用代理池时无法手动配置代理</div>
                  <el-alert
                    v-if="form.params.engine === 'drissionpage' && form.params.proxy.server && form.params.proxy.server.includes('@')"
                    title="格式错误"
                    type="error"
                    description="DrissionPage 引擎不支持在 URL 中包含账密的代理格式。请移除账密信息，或切换至 Playwright 引擎。"
                    show-icon
                    :closable="false"
                    class="mt-2"
                  />
                </el-form-item>
                
                <template v-if="!form.params.proxy_pool_group && form.params.proxy.server">
                  <el-row :gutter="20" v-if="form.params.engine !== 'drissionpage'">
                    <el-col :span="12">
                      <el-form-item label="用户名">
                        <el-input v-model="form.params.proxy.username" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="密码">
                        <el-input v-model="form.params.proxy.password" show-password />
                      </el-form-item>
                    </el-col>
                  </el-row>

                  <el-alert
                    v-if="form.params.engine === 'drissionpage'"
                    title="代理限制"
                    type="warning"
                    description="DrissionPage 引擎暂不支持账密认证代理。如果代理需要用户名和密码，可能会导致请求失败。建议使用无账密代理或切换至 Playwright 引擎。"
                    show-icon
                    :closable="false"
                    class="mt-2"
                  />
                </template>
              </div>
            </div>
          </el-tab-pane>

          <!-- 5. 定时采集 -->
          <el-tab-pane name="schedule">
            <template #label>
              <span class="tab-label">
                <el-icon class="icon-advanced"><Calendar /></el-icon>
                <span>定时采集</span>
              </span>
            </template>
            <div class="tab-content">
              <div class="section-group">
                <div class="section-header">
                  <div class="section-title">调度配置</div>
                </div>

                <el-form-item label="定时任务">
                  <div class="switch-container">
                    <el-switch v-model="form.enabled_schedule" />
                    <span class="switch-tip">{{ form.enabled_schedule ? '已开启自动调度计划' : '未开启自动调度计划' }}</span>
                  </div>
                </el-form-item>

                <el-form-item label="Cron 表达式" v-if="form.enabled_schedule">
                  <el-input v-model="form.cron" placeholder="例如: 0 0 * * * (每天零点执行)" clearable>
                    <template #prefix><el-icon><Timer /></el-icon></template>
                  </el-input>
                  <div class="input-tip">
                    格式：分 时 日 月 周。常用：<br/>
                    <code>*/30 * * * *</code> (每 30 分钟)<br/>
                    <code>0 9,18 * * *</code> (每天 9:00 和 18:00)
                  </div>
                </el-form-item>

                <div class="schedule-info-box" v-if="form.last_run_at || form.next_run_at">
                  <div class="info-item" v-if="form.last_run_at">
                    <el-icon><Clock /></el-icon>
                    <span class="label">上次运行：</span>
                    <span class="value">{{ formatTime(form.last_run_at) }}</span>
                  </div>
                  <div class="info-item" v-if="form.next_run_at && form.enabled_schedule">
                    <el-icon><VideoPlay /></el-icon>
                    <span class="label">预计下次：</span>
                    <span class="value">{{ formatTime(form.next_run_at) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitForm" :loading="submitting">保存配置</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- Test Result Dialog -->
    <el-dialog
      v-model="testResultVisible"
      title="规则校验与 DOM 匹配"
      width="95%"
      top="2vh"
      class="test-result-dialog"
      destroy-on-close
    >
      <div class="test-layout" v-loading="testing" element-loading-text="正在执行规则校验，请稍候...">
        <!-- 左侧：XPath 调试面板 -->
        <div class="test-sidebar">
          <div class="sidebar-header">
            <div class="header-top">
              <h3>XPath 提取调试</h3>
              <el-tag size="small" type="success">{{ testResults.items?.length || 0 }} 项匹配</el-tag>
            </div>
            <div class="input-tip mb-3" style="color: #64748b; line-height: 1.4;">
              修改下方的 XPath 表达式，右侧视图将实时同步高亮显示匹配结果。
            </div>
            <div class="url-display" v-if="form.url">
              <el-link :href="form.url" target="_blank" type="info" class="url-text">
                <el-icon><Link /></el-icon> {{ form.url }}
              </el-link>
            </div>
            <div class="name-edit-box mt-3">
              <div class="input-label mb-1" style="font-size: 12px; color: #64748b;">任务名称 (保存必填)</div>
              <el-input v-model="form.name" size="small" placeholder="请输入采集任务名称" clearable />
            </div>
          </div>
          
          <div class="xpath-debug-list">
            <el-collapse v-model="activeXPathField">
              <el-collapse-item name="list">
                <template #title>
                  <div class="collapse-title">
                    <span class="color-dot bg-blue"></span>
                    <span>列表容器 (Container)</span>
                  </div>
                </template>
                <div class="xpath-expr-wrapper">
                  <el-input 
                    v-model="testForm.list_xpath" 
                    size="small" 
                    placeholder="容器 XPath"
                    @input="debouncedUpdateHighlight"
                  >
                    <template #append>
                      <el-button @click="locateElement('list')">
                        <el-icon><Position /></el-icon>
                      </el-button>
                    </template>
                  </el-input>
                </div>
                <div class="xpath-count">{{ testResults.items?.length || 0 }} 个容器被发现</div>
              </el-collapse-item>
              
              <el-collapse-item name="title">
                <template #title>
                  <div class="collapse-title">
                    <span class="color-dot bg-green"></span>
                    <span>标题 (Title)</span>
                  </div>
                </template>
                <div class="xpath-expr-wrapper">
                  <el-input 
                    v-model="testForm.title_xpath" 
                    size="small" 
                    placeholder="标题 XPath"
                    @input="debouncedUpdateHighlight"
                  >
                    <template #append>
                      <el-button @click="locateElement('title')">
                        <el-icon><Position /></el-icon>
                      </el-button>
                    </template>
                  </el-input>
                </div>
                <div class="debug-items">
                  <div v-for="(item, idx) in testResults.items.slice(0, 5)" :key="idx" class="debug-item">
                    <span class="item-idx">#{{ idx + 1 }}</span>
                    <span class="item-val">{{ item.title || '(空)' }}</span>
                  </div>
                  <div v-if="testResults.items.length > 5" class="debug-more">... 等其余 {{ testResults.items.length - 5 }} 项</div>
                </div>
              </el-collapse-item>
              
              <el-collapse-item name="link">
                <template #title>
                  <div class="collapse-title">
                    <span class="color-dot bg-orange"></span>
                    <span>链接 (Link)</span>
                  </div>
                </template>
                <div class="xpath-expr-wrapper">
                  <el-input 
                    v-model="testForm.link_xpath" 
                    size="small" 
                    placeholder="链接 XPath"
                    @input="debouncedUpdateHighlight"
                  >
                    <template #append>
                      <el-button @click="locateElement('link')">
                        <el-icon><Position /></el-icon>
                      </el-button>
                    </template>
                  </el-input>
                </div>
                <div class="debug-items">
                  <div v-for="(item, idx) in testResults.items.slice(0, 5)" :key="idx" class="debug-item">
                    <span class="item-idx">#{{ idx + 1 }}</span>
                    <span class="item-val link-val" :title="item.link">{{ item.link || '(空)' }}</span>
                  </div>
                </div>
              </el-collapse-item>

              <el-collapse-item v-if="testForm.time_xpath || isAiPreview" name="time">
                <template #title>
                  <div class="collapse-title">
                    <span class="color-dot bg-purple"></span>
                    <span>时间 (Time)</span>
                  </div>
                </template>
                <div class="xpath-expr-wrapper">
                  <el-input 
                    v-model="testForm.time_xpath" 
                    size="small" 
                    placeholder="时间 XPath"
                    @input="debouncedUpdateHighlight"
                  >
                    <template #append>
                      <el-button @click="locateElement('time')">
                        <el-icon><Position /></el-icon>
                      </el-button>
                    </template>
                  </el-input>
                </div>
                <div class="debug-items">
                  <div v-for="(item, idx) in testResults.items.slice(0, 5)" :key="idx" class="debug-item">
                    <span class="item-idx">#{{ idx + 1 }}</span>
                    <span class="item-val">{{ item.time || '(空)' }}</span>
                  </div>
                </div>
              </el-collapse-item>

              <el-collapse-item v-if="testForm.pagination_next_xpath || isAiPreview" name="pagination">
                <template #title>
                  <div class="collapse-title">
                    <span class="color-dot bg-red"></span>
                    <span>下一页 (Next Page)</span>
                  </div>
                </template>
                <div class="xpath-expr-wrapper">
                  <el-input 
                    v-model="testForm.pagination_next_xpath" 
                    size="small" 
                    placeholder="下一页 XPath"
                    @input="debouncedUpdateHighlight"
                  >
                    <template #append>
                      <el-button @click="locateElement('pagination')">
                        <el-icon><Position /></el-icon>
                      </el-button>
                    </template>
                  </el-input>
                </div>
                <div class="input-tip mt-2">点击定位按钮查看翻页按钮是否能被正确选中</div>
              </el-collapse-item>
            </el-collapse>
          </div>

          <div class="sidebar-footer">
            <template v-if="isAiPreview">
              <div class="flex-buttons">
                <el-button type="success" class="flex-1" @click="confirmAiRules">
                  确认应用
                </el-button>
                <el-button type="warning" class="flex-1" @click="handleTest(true)" :loading="testing" icon="Refresh">
                  重新生成
                </el-button>
              </div>
              <el-button type="info" class="w-full mt-2" @click="isAiPreview = false; testResultVisible = false" plain>
                取消
              </el-button>
            </template>
            <template v-else>
              <div class="flex-buttons">
                <el-button type="primary" class="flex-1" @click="submitForm" :loading="submitting">
                  保存并关闭
                </el-button>
              </div>
              <div class="input-tip mt-3 text-center" style="color: #64748b;">
                <el-icon><InfoFilled /></el-icon> 修改 XPath 后右侧将自动同步预览
              </div>
            </template>
          </div>
        </div>

        <!-- 右侧：页面预览 -->
        <div class="test-main">
           <div class="test-header">
             <div class="header-left-group">
               <h3>视图预览</h3>
               <el-radio-group v-model="htmlViewMode" size="small" @change="handleViewModeChange">
                 <el-radio-button label="render">渲染页面</el-radio-button>
                 <el-radio-button label="source">源码</el-radio-button>
               </el-radio-group>
             </div>
             <div class="header-right-group">
                <el-checkbox v-model="showHighlight" v-if="htmlViewMode === 'render'">显示高亮</el-checkbox>
                <span class="text-sm text-gray-500" v-if="htmlViewMode === 'source'">仅展示前 50KB 内容</span>
             </div>
           </div>
           
           <div v-if="htmlViewMode === 'source'" class="viewer-container">
             <el-input 
               type="textarea" 
               v-model="testResults.html" 
               :rows="30" 
               readonly 
               resize="none"
               class="html-viewer"
             />
           </div>
           <div v-else class="viewer-container render-container">
             <iframe 
               ref="previewIframe"
               :srcdoc="injectedHtml" 
               class="render-viewer"
               sandbox="allow-scripts allow-same-origin"
               @load="onIframeLoad"
             ></iframe>
           </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive, computed, watch, onUnmounted, onActivated } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { Plus, VideoPlay, Position, Link, Setting, Search, Delete, Refresh, InfoFilled, Operation, Monitor, Calendar, QuestionFilled, CopyDocument, Connection, MagicStick } from '@element-plus/icons-vue'
import { getScrapers, createScraper, updateScraper, deleteScraper, testScraper, getRules, runScraper, getProxyStats, aiGenerateRules } from '@/api'

const scrapers = ref([])
const rules = ref([])
const router = useRouter()
const loading = ref(false)
const runningScrapers = ref(new Set(JSON.parse(localStorage.getItem('runningScrapers') || '[]')))

const saveRunningStatus = () => {
    localStorage.setItem('runningScrapers', JSON.stringify(Array.from(runningScrapers.value)))
}

const activeTab = ref('basic')
const proxyGroups = ref([])

const loadProxyGroups = async () => {
    try {
        const stats = await getProxyStats()
        proxyGroups.value = stats.groups_detail || []
    } catch (error) {
        console.error('Failed to load proxy groups:', error)
    }
}

// 筛选、分页、批量删除相关状态
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const selectedRows = ref([])

// 筛选逻辑
const filteredScrapers = computed(() => {
    if (!searchQuery.value) return scrapers.value
    const query = searchQuery.value.toLowerCase()
    return scrapers.value.filter(s => 
        (s.name && s.name.toLowerCase().includes(query)) || 
        (s.url && s.url.toLowerCase().includes(query))
    )
})

// 分页逻辑
const pagedScrapers = computed(() => {
    const start = (currentPage.value - 1) * pageSize.value
    const end = start + pageSize.value
    return filteredScrapers.value.slice(start, end)
})

// 处理搜索
const handleSearch = () => {
    currentPage.value = 1
}

// 处理多选
const handleSelectionChange = (val) => {
    selectedRows.value = val
}

// 处理分页大小变化
const handleSizeChange = (val) => {
    pageSize.value = val
    currentPage.value = 1
}

// 处理当前页变化
const handleCurrentChange = (val) => {
    currentPage.value = val
}

// 处理状态变更
const handleStatusChange = async (row, val) => {
    try {
        await updateScraper(row._id, { enabled: val })
        ElMessage.success(`站点 "${row.name}" 已${val ? '启用' : '禁用'}`)
    } catch (error) {
        row.enabled = !val // 恢复原状态
        ElMessage.error(error.response?.data?.detail || '更新状态失败')
    }
}

// 批量删除
const handleBatchDelete = () => {
    if (selectedRows.value.length === 0) return
    
    ElMessageBox.confirm(
        `确定要删除选中的 ${selectedRows.value.length} 个采集任务吗？`,
        '批量删除确认',
        { type: 'warning' }
    ).then(async () => {
        try {
            loading.value = true
            // 由于后端可能没有批量删除接口，循环调用单个删除接口
            const deletePromises = selectedRows.value.map(row => deleteScraper(row._id))
            await Promise.all(deletePromises)
            ElMessage.success('批量删除成功')
            selectedRows.value = []
            fetchData()
        } catch (error) {
            ElMessage.error('批量删除过程中出现错误')
        } finally {
            loading.value = false
        }
    })
}

// 处理执行
const handleRun = async (row) => {
    if (runningScrapers.value.has(row._id)) return
    
    ElMessageBox.confirm(
        `确定要立即对站点 "${row.name}" 执行采集测试吗？`,
        '测试确认',
        {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'info'
        }
    ).then(async () => {
        try {
            runningScrapers.value.add(row._id)
            saveRunningStatus()
            
            await runScraper(row._id)
            ElMessage.success(`测试任务 "${row.name}" 已提交`)
            
            // 提交成功后保持 5 秒的“正在测试”状态，给用户明确反馈
            setTimeout(() => {
                runningScrapers.value.delete(row._id)
                saveRunningStatus()
            }, 5000)
        } catch (error) {
            runningScrapers.value.delete(row._id)
            saveRunningStatus()
            
            const errorMsg = error.response?.data?.detail || error.message || '测试任务提交失败'
            
            ElMessageBox.alert(errorMsg, '测试失败', {
                confirmButtonText: '确定',
                type: 'error',
                customClass: 'error-message-box'
            })
        }
    }).catch(() => {
        // 取消执行，不做任何操作
    })
}

// 提取域名逻辑
const currentDomain = computed(() => {
    if (!form.url) return ''
    try {
        const url = new URL(form.url)
        return url.hostname.replace('www.', '')
    } catch (e) {
        return ''
    }
})

// 根据域名筛选规则
const filteredRules = computed(() => {
    if (!currentDomain.value) return rules.value
    const domain = currentDomain.value.toLowerCase()
    return rules.value.filter(rule => {
        const ruleDomain = rule.domain.toLowerCase()
        // 1. 完全匹配
        if (ruleDomain === domain) return true
        // 2. 子域名匹配 (例如 rule 是 example.com, domain 是 news.example.com)
        if (domain.endsWith('.' + ruleDomain)) return true
        // 3. 通配符匹配 (例如 rule 是 *.example.com)
        if (ruleDomain.startsWith('*.')) {
            const baseDomain = ruleDomain.substring(2)
            if (domain === baseDomain || domain.endsWith('.' + baseDomain)) return true
        }
        // 4. 包含匹配 (兜底)
        return domain.includes(ruleDomain) || ruleDomain.includes(domain)
    })
})

const goToRuleConfig = () => {
    isNavigating.value = true
    dialogVisible.value = false
    
    // 缩短延迟，100ms 足够关闭动画开始
    setTimeout(() => {
        router.push({
            path: '/rules',
            query: { 
                domain: currentDomain.value,
                action: 'add',
                t: Date.now()
            }
        }).finally(() => {
            isNavigating.value = false
        })
    }, 100)
}
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const isNavigating = ref(false)
const testing = ref(false)
const aiGenerating = ref(false)
const formRef = ref(null)
const previewIframe = ref(null)

const testResultVisible = ref(false)
const isAiPreview = ref(false)
const htmlViewMode = ref('render') // Default to render view
const showHighlight = ref(true)
const activeXPathField = ref(['list', 'title'])
const testResults = reactive({
    html: '',
    items: []
})
const testForm = reactive({
    list_xpath: '',
    title_xpath: '',
    link_xpath: '',
    time_xpath: '',
    pagination_next_xpath: ''
})

// 颜色配置
const COLORS = {
    list: { border: '#409eff', bg: 'rgba(64, 158, 255, 0.15)' },
    title: { border: '#67c23a', bg: 'rgba(103, 194, 58, 0.15)' },
    link: { border: '#e6a23c', bg: 'rgba(230, 162, 60, 0.15)' },
    time: { border: '#9c27b0', bg: 'rgba(156, 39, 176, 0.15)' },
    pagination: { border: '#f56c6c', bg: 'rgba(245, 108, 108, 0.15)' }
};

// 当前正在定位的目标
const locatingTarget = ref(null);

// 计算注入了高亮脚本的 HTML
const injectedHtml = computed(() => {
    if (!testResults.html) return '';

    try {
        const parser = new DOMParser();
        const doc = parser.parseFromString(testResults.html, 'text/html');

        // 1. 清理干扰项
        // 移除 xmlns 防止 XPath 命名空间问题
        if (doc.documentElement.hasAttribute('xmlns')) {
            doc.documentElement.removeAttribute('xmlns');
        }
        // 移除脚本防止执行
        doc.querySelectorAll('script').forEach(el => el.remove());
        doc.querySelectorAll('meta[http-equiv="refresh"]').forEach(el => el.remove());

        // 2. 准备配置项
        const configs = [];
        if (showHighlight.value) {
             if (testForm.list_xpath) configs.push({ type: 'list', xpath: testForm.list_xpath });
             if (testForm.title_xpath) configs.push({ type: 'title', xpath: testForm.title_xpath });
             if (testForm.link_xpath) configs.push({ type: 'link', xpath: testForm.link_xpath });
             if (testForm.time_xpath) configs.push({ type: 'time', xpath: testForm.time_xpath });
             if (testForm.pagination_next_xpath) configs.push({ type: 'pagination', xpath: testForm.pagination_next_xpath });
        }

        // 3. 执行 XPath 匹配并应用样式 (在 DOMParser 的文档对象上直接操作)
        applyHighlightsToDoc(doc, configs, testForm.list_xpath);

        // 4. 序列化回 HTML
        let safeHtml = new XMLSerializer().serializeToString(doc);

        // 5. 注入辅助 CSS
        const helperScript = `
            <style>
                .xpath-highlight {
                    position: relative !important;
                    z-index: 1;
                    cursor: help;
                    transition: all 0.3s ease;
                }
                .xpath-highlight:hover {
                    z-index: 100;
                    box-shadow: 0 0 8px rgba(0,0,0,0.5) !important;
                }
                .xpath-locating {
                    outline-width: 4px !important;
                    box-shadow: 0 0 15px rgba(0, 0, 0, 0.2) !important;
                    z-index: 1000 !important;
                    animation: pulse 1s infinite;
                }
                @keyframes pulse {
                    0% { transform: scale(1); }
                    50% { transform: scale(1.02); }
                    100% { transform: scale(1); }
                }
            </style>
        `;

        if (safeHtml.includes('</body>')) {
            return safeHtml.replace('</body>', helperScript + '</body>');
        } else {
            return safeHtml + helperScript;
        }

    } catch (e) {
        console.error('HTML processing error:', e);
        return testResults.html;
    }
})

// 在 DOMParser 创建的文档上执行高亮
function applyHighlightsToDoc(doc, configs, listXpath) {
    // 预先查找列表容器
    let containers = [];
    if (listXpath) {
        try {
            const result = doc.evaluate(listXpath, doc, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
            for(let i=0; i<result.snapshotLength; i++) containers.push(result.snapshotItem(i));
        } catch(e) {}
    }

    configs.forEach(config => {
        if (!config.xpath) return;
        const color = COLORS[config.type] || COLORS.list;
        
        // 判断是否使用相对定位
        const isRelativeField = ['title', 'link', 'time'].includes(config.type);
        const isRelativePath = config.xpath.trim().startsWith('.');
        
        let nodesToHighlight = [];

        if (isRelativeField && containers.length > 0 && isRelativePath) {
             // 相对定位
             containers.forEach(container => {
                 try {
                     const result = doc.evaluate(config.xpath, container, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                     for (let i = 0; i < result.snapshotLength; i++) {
                         nodesToHighlight.push(result.snapshotItem(i));
                     }
                 } catch(e) {}
             });
        } else {
            // 全局定位
             try {
                const result = doc.evaluate(config.xpath, doc, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                for (let i = 0; i < result.snapshotLength; i++) {
                     nodesToHighlight.push(result.snapshotItem(i));
                }
            } catch (e) {}
        }

        // 应用样式
        nodesToHighlight.forEach(node => {
            let el = node;
            if (node.nodeType === 2) el = node.ownerElement; // Attribute -> Element
            else if (node.nodeType === 3) el = node.parentElement; // Text -> Element
            
            if (el && el.style) {
                let style = `outline: 1px dashed ${color.border}; background-color: ${color.bg};`;
                el.classList.add('xpath-highlight');
                const prevTypes = (el.getAttribute('data-xpath-types') || '').trim();
                const typeSet = new Set(prevTypes ? prevTypes.split(/\s+/) : []);
                typeSet.add(config.type);
                el.setAttribute('data-xpath-types', Array.from(typeSet).join(' '));
                el.setAttribute('style', (el.getAttribute('style') || '') + '; ' + style);
            }
        });
    });
}

const onIframeLoad = () => {
    // Iframe 加载完成，无需做额外操作
}

const updateHighlight = () => {
    // 触发 injectedHtml 重新计算即可 (通过修改依赖)
}

// 提取数据的方法（纯前端实现）
const extractDataFromHtml = (html) => {
    if (!html) return [];
    
    try {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // 移除 xmlns
        if (doc.documentElement.hasAttribute('xmlns')) {
            doc.documentElement.removeAttribute('xmlns');
        }

        const items = [];
        const listXpath = testForm.list_xpath;
        
        if (!listXpath) return [];

        // 查找容器
        const containers = [];
        try {
            const result = doc.evaluate(listXpath, doc, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
            for(let i=0; i<result.snapshotLength; i++) containers.push(result.snapshotItem(i));
        } catch(e) {
            console.warn('List XPath evaluation failed:', e);
            return [];
        }

        // 遍历容器提取字段
        containers.forEach(container => {
            const item = {};
            
            // 辅助函数：提取单个字段
            const extractField = (xpath, type) => {
                if (!xpath) return null;
                try {
                    // 判断是否是相对路径
                    const isRelative = xpath.trim().startsWith('.');
                    const contextNode = isRelative ? container : doc;
                    
                    const result = doc.evaluate(xpath, contextNode, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                    if (result.snapshotLength > 0) {
                        const node = result.snapshotItem(0);
                        // 获取文本内容或属性值
                        if (node.nodeType === 2) return node.value; // Attribute
                        if (node.nodeType === 3) return node.nodeValue; // Text
                        if (node.nodeType === 1) return node.textContent.trim(); // Element
                    }
                } catch(e) {}
                return null;
            };

            item.title = extractField(testForm.title_xpath, 'title');
            item.link = extractField(testForm.link_xpath, 'link');
            item.time = extractField(testForm.time_xpath, 'time');
            
            // 只有当至少提取到一个有效字段时才添加
            if (item.title || item.link || item.time) {
                items.push(item);
            }
        });

        return items;
    } catch (e) {
        console.error('Data extraction error:', e);
        return [];
    }
}

// 防抖处理 updateHighlight
let highlightTimer = null
const debouncedUpdateHighlight = () => {
   // 输入框 v-model 直接更新了 testForm，testForm 更新触发 injectedHtml 更新
   if (highlightTimer) clearTimeout(highlightTimer)
   highlightTimer = setTimeout(() => {
        // 重新提取数据用于左侧列表展示
        if (testResults.html) {
            const extractedItems = extractDataFromHtml(testResults.html);
            testResults.items = extractedItems;
        }
   }, 300)
}

const locateElement = (type) => {
    const iframe = previewIframe.value;
    if (!iframe || !iframe.contentDocument) {
        ElMessage.warning('预览窗口未就绪');
        return;
    }
    
    const doc = iframe.contentDocument;
    
    doc.querySelectorAll('.xpath-locating').forEach(el => {
        el.classList.remove('xpath-locating');
    });
    
    let elementTargets = Array.from(doc.querySelectorAll(`[data-xpath-types~="${type}"]`));

    if (elementTargets.length === 0) {
        let xpath = '';
        if (type === 'list') xpath = testForm.list_xpath;
        else if (type === 'title') xpath = testForm.title_xpath;
        else if (type === 'link') xpath = testForm.link_xpath;
        else if (type === 'time') xpath = testForm.time_xpath;
        else if (type === 'pagination') xpath = testForm.pagination_next_xpath;

        xpath = String(xpath || '').trim();
        if (!xpath) {
            ElMessage.warning('请先输入 XPath');
            return;
        }

        const listXpath = String(testForm.list_xpath || '').trim();
        const isRelativeField = type === 'title' || type === 'link' || type === 'time';
        const isRelativePath = xpath.startsWith('.');

        const nodes = [];
        if (isRelativeField && isRelativePath && listXpath) {
            try {
                const containers = doc.evaluate(listXpath, doc, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                for (let i = 0; i < containers.snapshotLength; i++) {
                    const container = containers.snapshotItem(i);
                    try {
                        const r = doc.evaluate(xpath, container, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                        for (let j = 0; j < r.snapshotLength; j++) nodes.push(r.snapshotItem(j));
                    } catch (e) {}
                }
            } catch (e) {}
        } else {
            try {
                const r = doc.evaluate(xpath, doc, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                for (let i = 0; i < r.snapshotLength; i++) nodes.push(r.snapshotItem(i));
            } catch (e) {}
        }

        const els = [];
        const seen = new Set();
        for (const node of nodes) {
            let el = node;
            if (node && node.nodeType === 2) el = node.ownerElement;
            else if (node && node.nodeType === 3) el = node.parentElement;
            if (el && el.nodeType === 1) {
                const key = el;
                if (!seen.has(key)) {
                    seen.add(key);
                    els.push(el);
                }
            }
        }

        elementTargets = els;
    }

    if (elementTargets.length > 0) {
        elementTargets.forEach(el => {
            el.classList.add('xpath-locating');
        });
        
        const firstTarget = elementTargets[0];
        
        const style = window.getComputedStyle ? window.getComputedStyle(firstTarget) : firstTarget.currentStyle;
        if (style.display === 'none') {
             ElMessage.warning('目标元素存在，但是被隐藏了(display: none)，无法滚动可见');
        }
        
        firstTarget.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
        
        ElMessage.success(`已定位到 ${elementTargets.length} 个元素`);
        
        setTimeout(() => {
            elementTargets.forEach(el => el.classList.remove('xpath-locating'));
        }, 3000);
    } else {
        ElMessage.warning('当前视图中未找到对应元素');
    }
}


watch(showHighlight, () => {
    updateHighlight()
})

const handleViewModeChange = (val) => {
    if (val === 'render') {
        setTimeout(updateHighlight, 100)
    }
}

const form = reactive({
    name: '',
    url: '',
    rule_id: '',
    description: '',
    list_xpath: '',
    title_xpath: '',
    link_xpath: '',
    time_xpath: '',
    pagination_next_xpath: '',
    max_pages: 5,
    retry_enabled: false,
    max_retries: 0,
    params: {
        engine: 'playwright',
        wait_for: 'networkidle',
        wait_time: 3000,
        timeout: 30000,
        wait_for_selector: '',
        user_agent: '',
        viewport: { width: 1920, height: 1080 },
        stealth: true,
        no_css: true,
        block_images: true,
        block_media: false,
        proxy: { server: '', username: '', password: '' },
        proxy_pool_group: '',
        cookies: '',
        intercept_apis: [],
        intercept_continue: false,
        storage_type: 'mongo',
        mongo_collection: '',
        oss_path: '',
        save_html: true,
        screenshot: false,
        is_fullscreen: false,
    },
    cache: {
        enabled: false,
        ttl: 3600
    },
    enabled_schedule: false,
    enabled: true,
    cron: ''
})

const formRules = {
    name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
    url: [{ required: true, message: '请输入起始 URL', trigger: 'blur' }],
    list_xpath: [{ required: true, message: '请输入列表容器 XPath', trigger: 'blur' }],
    title_xpath: [{ required: true, message: '请输入标题 XPath', trigger: 'blur' }],
    link_xpath: [{ required: true, message: '请输入链接 XPath', trigger: 'blur' }]
}

const fetchData = async () => {
    loading.value = true
    try {
        const [scrapersData, rulesData] = await Promise.all([
            getScrapers(),
            getRules()
        ])
        scrapers.value = scrapersData
        rules.value = rulesData
    } catch (error) {
        ElMessage.error('获取数据失败')
    } finally {
        loading.value = false
    }
}

const getRuleName = (id) => {
    const rule = rules.value.find(r => r.id === id)
    return rule ? rule.domain : id
}

const formatTime = (time) => {
    if (!time) return '-'
    return new Date(time).toLocaleString()
}

const handleAdd = async () => {
    isEdit.value = false
    activeTab.value = 'basic'
    
    // 如果规则列表为空，则获取
    if (rules.value.length === 0) {
        await fetchRules()
    }
    
    // 初始化表单默认值
    Object.assign(form, {
        name: '',
        url: '',
        rule_id: '',
        description: '',
        list_xpath: '',
        title_xpath: '',
        link_xpath: '',
        time_xpath: '',
        pagination_next_xpath: '',
        max_pages: 5,
        retry_enabled: false,
        max_retries: 0,
        params: {
            engine: 'playwright',
            wait_for: 'networkidle',
            wait_time: 3000,
            timeout: 30000,
            wait_for_selector: '',
            user_agent: '',
            viewport: { width: 1920, height: 1080 },
            stealth: true,
            no_css: true,
            block_images: true,
            block_media: false,
            proxy: { server: '', username: '', password: '' },
            proxy_pool_group: '',
            cookies: '',
            intercept_apis: [],
            intercept_continue: false,
            storage_type: 'mongo',
            mongo_collection: '',
            oss_path: '',
            save_html: true,
            return_cookies: false,
            screenshot: false,
            is_fullscreen: false,
        },
        cache: {
            enabled: false,
            ttl: 3600
        },
        enabled_schedule: false,
        enabled: true,
        cron: ''
    })
    dialogVisible.value = true
}

const handleViewResults = (row) => {
    router.push({
        name: 'TaskRecords',
        query: { schedule_id: `scraper_${row._id}` }
    })
}

const handleEdit = async (row) => {
    isEdit.value = true
    activeTab.value = 'basic'
    
    // 基础赋值
    const rowData = JSON.parse(JSON.stringify(row))
    Object.assign(form, rowData)
    
    // 确保 params 存在且所有必要字段都有默认值
    if (!form.params) {
        form.params = {}
    }

    // 统一补齐 params 内部字段
    const defaultParams = {
        engine: 'playwright',
        wait_for: 'networkidle',
        wait_time: 3000,
        timeout: 30000,
        wait_for_selector: '',
        user_agent: '',
        viewport: { width: 1920, height: 1080 },
        stealth: true,
        no_css: true,
        block_images: true,
        block_media: false,
        proxy: { server: '', username: '', password: '' },
        proxy_pool_group: '',
        cookies: '',
        intercept_apis: [],
        intercept_continue: false,
        storage_type: 'mongo',
        mongo_collection: '',
        oss_path: '',
        save_html: true,
        return_cookies: false,
        screenshot: false,
        is_fullscreen: false,
    }

    // 合并默认参数和现有参数
    // 注意：优先使用 row 中的顶级字段（如果存在旧数据格式）
    form.params = {
        ...defaultParams,
        ...form.params,
        // 兼容旧数据格式：如果 params 中没有，但 row 中有，则使用 row 中的
        engine: form.params.engine || row.engine || defaultParams.engine,
        wait_for: form.params.wait_for || row.wait_for || defaultParams.wait_for,
        wait_time: form.params.wait_time !== undefined ? form.params.wait_time : (row.wait_time !== undefined ? row.wait_time : defaultParams.wait_time),
        timeout: form.params.timeout || row.wait_timeout || row.timeout || defaultParams.timeout,
        wait_for_selector: form.params.wait_for_selector || row.wait_for_selector || defaultParams.wait_for_selector,
        user_agent: form.params.user_agent || row.user_agent || defaultParams.user_agent,
        viewport: form.params.viewport || row.viewport || defaultParams.viewport,
        stealth: form.params.stealth !== undefined ? form.params.stealth : (row.stealth !== undefined ? row.stealth : defaultParams.stealth),
        no_css: form.params.no_css !== undefined ? form.params.no_css : (row.no_css !== undefined ? row.no_css : defaultParams.no_css),
        block_images: form.params.block_images !== undefined ? form.params.block_images : (row.block_images !== undefined ? row.block_images : (row.no_images !== undefined ? row.no_images : defaultParams.block_images)),
    }

    if (!form.cache) {
        form.cache = row.cache || { enabled: true, ttl: 3600 }
    }
    
    // 补齐缺失的顶级字段
    if (form.retry_enabled === undefined) form.retry_enabled = true
    if (form.max_retries === undefined) form.max_retries = 3
    
    // 确保在打开编辑弹窗前，规则列表是最新的
    await fetchRules()
    dialogVisible.value = true
}

const fetchRules = async () => {
    try {
        const res = await getRules()
        rules.value = res
    } catch (error) {
        console.error('Failed to fetch rules:', error)
    }
}

const handleDelete = (row) => {
    ElMessageBox.confirm('确定要删除该采集任务吗？', '提示', {
        type: 'warning'
    }).then(async () => {
        try {
            await deleteScraper(row._id)
            ElMessage.success('删除成功')
            fetchData()
        } catch (error) {
            ElMessage.error('删除失败')
        }
    })
}

const submitForm = async () => {
    // 如果是从校验弹窗点击的“保存并关闭”，需要先将 testForm 的规则同步回 form
    if (testResultVisible.value) {
        form.list_xpath = testForm.list_xpath
        form.title_xpath = testForm.title_xpath
        form.link_xpath = testForm.link_xpath
        form.time_xpath = testForm.time_xpath
        form.pagination_next_xpath = testForm.pagination_next_xpath
    }

    if (!formRef.value) return
    await formRef.value.validate(async (valid) => {
        if (valid) {
            submitting.value = true
            try {
                // Remove empty optional fields
                const data = JSON.parse(JSON.stringify(form))
                
                // 确保重试逻辑一致：如果关闭了重试开关，则重试次数强制为 0
                if (data.retry_enabled === false) {
                    data.max_retries = 0
                }
                
                if (!data.rule_id) delete data.rule_id
                if (!data.time_xpath) delete data.time_xpath
                if (!data.pagination_next_xpath) delete data.pagination_next_xpath
                if (!data.params.wait_for_selector) delete data.params.wait_for_selector
                if (!data.params.user_agent) delete data.params.user_agent

                if (isEdit.value) {
                    await updateScraper(form._id, data)
                    ElMessage.success('保存成功')
                } else {
                    const res = await createScraper(data)
                    if (res && res._id) {
                        form._id = res._id
                        isEdit.value = true
                    }
                    ElMessage.success('保存成功')
                }
                
                // 成功保存后，刷新列表
                fetchData()
                
                // 如果是从预览校验界面保存的，只关闭预览弹窗，保留主配置界面
                if (testResultVisible.value) {
                    testResultVisible.value = false
                } else {
                    // 如果是在主配置界面点击的保存，则关闭主弹窗
                    dialogVisible.value = false
                }
            } catch (error) {
                ElMessage.error(error.response?.data?.detail || '提交失败')
            } finally {
                submitting.value = false
            }
        } else {
            // 如果校验失败且校验弹窗打开着，提示用户切换回基础页签检查必填项
            if (testResultVisible.value) {
                ElMessage.error('保存失败，请检查基础配置中的必填项是否填写正确')
            }
        }
    })
}

const handleAiGenerate = async () => {
    if (!form.url) {
        ElMessage.warning('请先填写起始 URL')
        return
    }

    // 如果任务名称为空，自动根据 URL 生成一个默认名称
    if (!form.name) {
        try {
            const urlObj = new URL(form.url)
            form.name = `AI采集_${urlObj.hostname.replace('www.', '')}_${new Date().getTime().toString().slice(-4)}`
        } catch (e) {
            form.name = `AI采集任务_${new Date().getTime().toString().slice(-4)}`
        }
    }

    aiGenerating.value = true
    try {
        const res = await aiGenerateRules({
            url: form.url,
            wait_for_selector: form.params.wait_for_selector,
            wait_time: form.params.wait_time,
            timeout: form.params.timeout,
            proxy: form.params.proxy,
            proxy_pool_group: form.params.proxy_pool_group,
            cookies: form.params.cookies
        })
        
        // 存储在临时状态中，而不是直接覆盖主表单
        testForm.list_xpath = res.list_xpath || ''
        testForm.title_xpath = res.title_xpath || ''
        testForm.link_xpath = res.link_xpath || ''
        testForm.time_xpath = res.time_xpath || ''
        testForm.pagination_next_xpath = res.pagination_next_xpath || ''
        
        isAiPreview.value = true
        
        // 清空旧的校验结果，准备展示新规则的校验
        testResults.items = []
        testResults.html = ''
        
        ElMessage.success('AI 规则生成成功，正在启动预览校验...')
        
        // 生成成功后，直接调用校验，传入 true 表示来自 AI
        await handleTest(true)
    } catch (error) {
        ElMessage.error(error.response?.data?.detail || '生成失败')
    } finally {
        aiGenerating.value = false
    }
}

const handleTest = async (fromAi = false) => {
    // 兼容处理：当通过 @click="handleTest" 调用时，第一个参数是 PointerEvent (也是 truthy)
    // 我们需要确保只有显式传入 true 时才认为是 AI 模式
    const isActuallyAi = fromAi === true;
    console.log('handleTest called, isActuallyAi:', isActuallyAi);
    
    // 如果是来自主界面的点击 (不是 AI 模式 且 校验弹窗未打开)，则同步 form -> testForm
    if (!isActuallyAi && !testResultVisible.value) {
        const url = String(form.url || '').trim();
        const list_xpath = String(form.list_xpath || '').trim();
        const title_xpath = String(form.title_xpath || '').trim();
        const link_xpath = String(form.link_xpath || '').trim();

        if (!url || !list_xpath || !title_xpath || !link_xpath) {
            ElMessage.warning('请先填写完整的 URL 和基础 XPath 规则')
            return
        }
        
        testForm.list_xpath = list_xpath
        testForm.title_xpath = title_xpath
        testForm.link_xpath = link_xpath
        testForm.time_xpath = String(form.time_xpath || '').trim()
        testForm.pagination_next_xpath = String(form.pagination_next_xpath || '').trim()
        isAiPreview.value = false
    }

    // 构建 Payload，优先使用 testForm 中的当前值 (因为用户可能在侧边栏进行了修改)
    const payload = {
        url: String(form.url || '').trim(),
        list_xpath: String(testForm.list_xpath || '').trim(),
        title_xpath: String(testForm.title_xpath || '').trim(),
        link_xpath: String(testForm.link_xpath || '').trim(),
        time_xpath: String(testForm.time_xpath || '').trim(),
        pagination_next_xpath: String(testForm.pagination_next_xpath || '').trim(),
        // 规则校验强制使用 DrissionPage (dp) 以获取最佳 HTML
        engine: 'drissionpage', 
        wait_for: form.params.wait_for,
        wait_time: form.params.wait_time,
        wait_for_selector: form.params.wait_for_selector,
        wait_timeout: form.params.timeout,
        max_retries: form.max_retries,
        block_images: form.params.block_images,
        no_css: form.params.no_css,
        stealth: form.params.stealth,
        proxy: form.params.proxy,
        proxy_pool_group: form.params.proxy_pool_group,
        cookies: form.params.cookies,
        user_agent: form.params.user_agent
    }

    // 确保 testForm 与 payload 同步，这样 injectedHtml 才能使用正确的 XPath
    if (!isActuallyAi) {
         testForm.list_xpath = payload.list_xpath;
         testForm.title_xpath = payload.title_xpath;
         testForm.link_xpath = payload.link_xpath;
         testForm.time_xpath = payload.time_xpath;
         testForm.pagination_next_xpath = payload.pagination_next_xpath;
    }

    console.log('Current testForm state:', JSON.parse(JSON.stringify(testForm)));
    console.log('Sending testScraper request with payload:', payload);
    
    // 开启校验弹窗并进入加载状态
    testResultVisible.value = true
    testing.value = true
    
    try {
        const res = await testScraper(payload)
        testResults.items = res.items
        testResults.html = res.html
        htmlViewMode.value = 'render' 
        activeXPathField.value = ['list', 'title']
        ElMessage.success(`校验成功，提取到 ${res.items.length} 条数据`)
    } catch (error) {
        console.error('testScraper error:', error);
        
        const errorMsg = error.response?.data?.detail || error.message || '规则校验失败'
        
        ElMessageBox.alert(errorMsg, '测试失败', {
            confirmButtonText: '确定',
            type: 'error',
            customClass: 'error-message-box'
        })
        
        // 如果校验失败且是从 AI 生成过来的，可能需要关闭弹窗让用户重试
        if (isActuallyAi) {
            testResultVisible.value = false
        }
    } finally {
        testing.value = false
    }
}

const confirmAiRules = () => {
    form.list_xpath = testForm.list_xpath
    form.title_xpath = testForm.title_xpath
    form.link_xpath = testForm.link_xpath
    form.time_xpath = testForm.time_xpath
    form.pagination_next_xpath = testForm.pagination_next_xpath
    
    isAiPreview.value = false
    ElMessage.success('AI 规则已正式应用到配置')
}

// 监听来自 iframe 的定位结果消息
const handleIframeMessage = (event) => {
    if (event.data.type === 'locateResult') {
        if (event.data.count > 0) {
            ElMessage.success({
                message: `定位成功：找到 ${event.data.count} 个元素 (${event.data.fieldType})`,
                grouping: true
            });
        } else {
            ElMessage.warning({
                message: `未找到匹配元素：${event.data.xpath}`,
                grouping: true
            });
            if (event.data.error) {
                console.error('Locate error from iframe:', event.data.error);
            }
        }
    }
}

onMounted(() => {
    window.addEventListener('message', handleIframeMessage)
})

onActivated(() => {
    fetchData()
    loadProxyGroups()
})

onUnmounted(() => {
    window.removeEventListener('message', handleIframeMessage)
})
</script>

<style scoped>
.rule-select-container {
    display: flex;
    align-items: center;
    width: 100%;
}
.ml-2 {
    margin-left: 8px;
}
.cookies-input-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.custom-storage-fields {
  background: #f8fafc;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid #f1f5f9;
}

.scraper-dialog :deep(.el-dialog__body) {
    padding: 0;
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
  font-size: 18px;
  padding: 8px 0;
}

.tab-label .el-icon {
  font-size: 22px;
}

.icon-basic { color: #3b82f6 !important; }
.icon-parser { color: #8b5cf6 !important; }
.icon-browser { color: #10b981 !important; }
.icon-advanced { color: #f59e0b !important; }

.tab-content {
    padding: 24px;
    max-height: 65vh;
    overflow-y: auto;
    background-color: #fff;
}

.section-group {
    margin-bottom: 24px;
}

.section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
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
    line-height: 1.5;
}
.input-tip code {
    background: #f1f5f9;
    padding: 2px 4px;
    border-radius: 4px;
    color: #2b62ad;
}
.feature-settings {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-top: 16px;
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
.schedule-info-box {
    margin-top: 16px;
    padding: 16px;
    background: #f0f7ff;
    border-radius: 8px;
    border: 1px solid #d9ecff;
    display: flex;
    flex-direction: column;
    gap: 12px;
}
.info-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
}
.info-item .label {
    color: #64748b;
    min-width: 70px;
}
.info-item .value {
    color: #1e293b;
    font-weight: 600;
}
.info-item .el-icon {
    color: #3b82f6;
}
.rules-footer {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px dashed #e2e8f0;
}
.dialog-footer {
    display: flex;
    justify-content: flex-end;
    align-items: center;
}
.text-gray {
    color: #9ca3af;
}

.test-layout {
    display: flex;
    gap: 20px;
    height: 75vh;
}
.test-sidebar {
    width: 350px;
    display: flex;
    flex-direction: column;
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 16px;
    overflow-y: auto;
}
.sidebar-header {
    margin-bottom: 20px;
}
.header-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}
.url-display {
    background: #f8fafc;
    padding: 6px 10px;
    border-radius: 4px;
    border: 1px solid #f1f5f9;
}
.url-text {
    font-size: 12px;
    color: #5baaf5;
    word-break: break-all;
    line-height: 1.4;
    display: flex;
    align-items: flex-start;
    gap: 4px;
}
.url-text :deep(.el-icon) {
    margin-top: 2px;
}
.table-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
}
.toolbar-left {
    display: flex;
    gap: 12px;
    align-items: center;
}
.search-input {
    width: 280px;
}
.pagination-container {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
}
.sidebar-header h3 {
    margin: 0;
    font-size: 16px;
    color: #1e293b;
}
.xpath-debug-list :deep(.el-collapse) {
    border: none;
}
.xpath-debug-list :deep(.el-collapse-item__header) {
    font-weight: 600;
    color: #475569;
}
.xpath-expr {
    background: #f1f5f9;
    padding: 8px;
    border-radius: 4px;
    font-size: 12px;
    color: #64748b;
    word-break: break-all;
    margin-bottom: 10px;
}
.xpath-expr-wrapper {
    margin-bottom: 8px;
}
.xpath-expr-wrapper :deep(.el-input-group__append) {
    padding: 0 12px;
    cursor: pointer;
    background-color: #f8fafc;
    transition: all 0.2s;
}
.xpath-expr-wrapper :deep(.el-input-group__append:hover) {
    background-color: #f1f5f9;
    color: #409eff;
}
.xpath-count {
    font-size: 13px;
    color: #409eff;
    font-weight: 500;
}
.collapse-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
}
.color-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
}
.bg-blue { background-color: #409eff; }
.bg-green { background-color: #67c23a; }
.bg-orange { background-color: #e6a23c; }
.bg-purple { background-color: #9c27b0; }

.legend {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    padding: 12px;
    background: #f8fafc;
    border-radius: 6px;
    border: 1px solid #e2e8f0;
}
.legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: #64748b;
}
.debug-items {
    display: flex;
    flex-direction: column;
    gap: 8px;
}
.debug-item {
    display: flex;
    gap: 10px;
    font-size: 13px;
    align-items: flex-start;
}
.item-idx {
    color: #94a3b8;
    font-family: monospace;
}
.item-val {
    color: #334155;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.link-val {
    color: #409eff;
    font-size: 12px;
    cursor: help;
}
.debug-more {
    font-size: 12px;
    color: #94a3b8;
    text-align: center;
    margin-top: 5px;
}
.sidebar-footer {
    padding: 10px;
    margin-top: auto;
    padding-top: 10px;
    background: #f8fafc;
}
.highlight-box-demo {
    display: inline-block;
    padding: 0 4px;
    border: 2px solid #409eff;
    background: rgba(64, 158, 255, 0.1);
    border-radius: 2px;
    font-weight: 600;
    color: #409eff;
}

.test-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 16px;
}
.header-right-group {
    display: flex;
    align-items: center;
    gap: 15px;
}
.html-viewer {
    font-family: 'Fira Code', monospace;
    font-size: 12px;
    flex: 1;
}
.html-viewer :deep(.el-textarea__inner) {
    height: 100%;
    background-color: #0f172a;
    color: #e2e8f0;
    border: none;
    padding: 15px;
}
.test-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
}
.test-header h3 {
    margin: 0;
    font-size: 16px;
    color: #1e293b;
}
.header-left-group {
    display: flex;
    align-items: center;
    gap: 15px;
}
.viewer-container {
    flex: 1;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    overflow: hidden;
    background: #f8fafc;
}
.render-viewer {
    width: 100%;
    height: 100%;
    border: none;
}

.add-btn {
  padding: 8px 20px;
  font-weight: 500;
  letter-spacing: 0.5px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.2);
  border: none;
  background: linear-gradient(135deg, #409eff 0%, #3a8ee6 100%);
}

.add-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
  background: linear-gradient(135deg, #66b1ff 0%, #409eff 100%);
  opacity: 0.9;
}

.add-btn:active {
  transform: translateY(0);
  box-shadow: 0 2px 4px rgba(64, 158, 255, 0.3);
}

.add-btn i {
  margin-right: 6px;
  font-size: 16px;
  vertical-align: middle;
}

.add-btn span {
  vertical-align: middle;
}

.flex-buttons {
    display: flex;
    gap: 10px;
    width: 100%;
    margin-bottom: 8px;
}
.flex-1 {
    flex: 1;
}
</style>
