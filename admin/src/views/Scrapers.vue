<template>
  <div class="scrapers-container">
    <div class="page-header">
      <div class="header-left">
        <h2>站点采集</h2>
        <p class="subtitle">管理列表页采集任务及自动发现规则</p>
      </div>
      <el-button type="primary" @click="handleAdd">
        <el-icon><Plus /></el-icon>添加采集
      </el-button>
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
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button 
                type="success" 
                size="small" 
                @click="handleRun(row)" 
                :loading="runningScrapers.has(row._id)"
                icon="VideoPlay"
              >
                执行
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
                
                <el-form-item label="任务名称" prop="name">
                  <el-input v-model="form.name" placeholder="请输入采集任务名称，如：新闻列表抓取" clearable>
                    <template #prefix><el-icon><InfoFilled /></el-icon></template>
                  </el-input>
                </el-form-item>

                <el-form-item label="起始 URL" prop="url">
                  <el-input v-model="form.url" placeholder="请输入列表页抓取地址，如: https://news.example.com/list" clearable>
                    <template #prefix><el-icon class="icon-link"><Connection /></el-icon></template>
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
                  <div class="input-tip">
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
                  <el-button type="warning" @click="handleTest" :loading="testing" icon="VideoPlay">规则校验</el-button>
                  <el-button type="primary" @click="handleAIExtract" :loading="aiExtracting" icon="Cpu">AI智能解析</el-button>
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
                </el-form-item>

                <el-form-item label="手动代理服务器">
                  <el-input 
                    v-model="form.params.proxy.server" 
                    placeholder="http://proxy.example.com:8080" 
                    clearable 
                    :disabled="!!form.params.proxy_pool_group"
                  />
                  <div class="input-tip" v-if="form.params.proxy_pool_group">使用代理池时无法手动配置代理</div>
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
                </template>

                <div class="section-header mt-4">
                  <div class="section-title">存储设置</div>
                </div>
                <el-form-item label="存储方式">
                  <el-radio-group v-model="form.params.storage_type">
                    <el-radio label="mongo">MongoDB (默认)</el-radio>
                    <el-radio label="oss">对象存储 (OSS)</el-radio>
                  </el-radio-group>
                  <div class="input-tip">选择采集内容的存储介质。OSS 适合存储大规模网页源码。</div>
                </el-form-item>

                <div class="custom-storage-fields mt-2" v-if="form.params.storage_type === 'mongo'">
                  <el-form-item label="自定义集合名称">
                    <el-input v-model="form.params.mongo_collection" placeholder="默认使用站点名称" clearable />
                    <div class="input-tip">不填则默认使用站点英文标识作为 MongoDB 集合名。</div>
                  </el-form-item>
                </div>

                <div class="custom-storage-fields mt-2" v-if="form.params.storage_type === 'oss'">
                  <el-form-item label="OSS 存储路径">
                    <el-input v-model="form.params.oss_path" placeholder="例如: /scraped/news/" clearable />
                    <div class="input-tip">网页 HTML 将以文件形式存储在 OSS 的指定目录下。</div>
                  </el-form-item>
                </div>

                <div class="section-header mt-4">
                  <div class="section-title">重试与保存</div>
                </div>
                <el-form-item label="缓存加速">
                  <div class="switch-container">
                    <el-switch v-model="form.cache.enabled" />
                    <span class="switch-tip">{{ form.cache.enabled ? '开启 (相同 URL 在 TTL 内不再重复抓取)' : '关闭 (每次都实时抓取)' }}</span>
                  </div>
                </el-form-item>
                
                <el-form-item label="缓存有效期 (秒)" v-if="form.cache.enabled">
                  <el-input-number v-model="form.cache.ttl" :min="60" :step="60" style="width: 100%" />
                  <div class="input-tip">在有效期内，系统将直接从缓存读取该 URL 的抓取结果。</div>
                </el-form-item>

                <el-row :gutter="20">
                  <el-col :span="12">
                    <el-form-item label="失败重试">
                      <div class="switch-container">
                        <el-switch v-model="form.retry_enabled" />
                        <span class="switch-tip">{{ form.retry_enabled ? '开启 (自动重试)' : '关闭 (不重试)' }}</span>
                      </div>
                    </el-form-item>
                  </el-col>
                  <el-col :span="12" v-if="form.retry_enabled">
                    <el-form-item label="最大重试次数">
                      <el-input-number v-model="form.max_retries" :min="1" :max="10" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                </el-row>
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
      <div class="test-layout">
        <!-- 左侧：XPath 调试面板 -->
        <div class="test-sidebar">
          <div class="sidebar-header">
            <div class="header-top">
              <h3>XPath 提取调试</h3>
              <el-tag size="small" type="success">{{ testResults.items?.length || 0 }} 项匹配</el-tag>
            </div>
            <div class="url-display" v-if="form.url">
              <el-link :href="form.url" target="_blank" type="info" class="url-text">
                <el-icon><Link /></el-icon> {{ form.url }}
              </el-link>
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
                    v-model="form.list_xpath" 
                    size="small" 
                    placeholder="容器 XPath"
                    @input="updateHighlight"
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
                    v-model="form.title_xpath" 
                    size="small" 
                    placeholder="标题 XPath"
                    @input="updateHighlight"
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
                    v-model="form.link_xpath" 
                    size="small" 
                    placeholder="链接 XPath"
                    @input="updateHighlight"
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

              <el-collapse-item v-if="form.time_xpath" name="time">
                <template #title>
                  <div class="collapse-title">
                    <span class="color-dot bg-purple"></span>
                    <span>时间 (Time)</span>
                  </div>
                </template>
                <div class="xpath-expr-wrapper">
                  <el-input 
                    v-model="form.time_xpath" 
                    size="small" 
                    placeholder="时间 XPath"
                    @input="updateHighlight"
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
            </el-collapse>
          </div>

          <div class="sidebar-footer">
            <el-button type="primary" class="w-full" @click="submitForm" :loading="submitting">
              保存并更新
            </el-button>
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
               sandbox="allow-scripts"
               @load="onIframeLoad"
             ></iframe>
           </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { Plus, VideoPlay, Position, Link, Setting, Search, Delete, Refresh, InfoFilled, Operation, Monitor, Calendar, QuestionFilled, CopyDocument, Connection, Cpu } from '@element-plus/icons-vue'
import { getScrapers, createScraper, updateScraper, deleteScraper, testScraper, getRules, runScraper, getProxyStats, aiExtractScraper } from '@/api'

const scrapers = ref([])
const rules = ref([])
const router = useRouter()
const loading = ref(false)
const runningScrapers = ref(new Set())
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
    try {
        runningScrapers.value.add(row._id)
        await runScraper(row._id)
        ElMessage.success(`任务 "${row.name}" 已提交执行`)
    } catch (error) {
        ElMessage.error(error.response?.data?.detail || '执行失败')
    } finally {
        runningScrapers.value.delete(row._id)
    }
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
const aiExtracting = ref(false)
const formRef = ref(null)
const previewIframe = ref(null)

const testResultVisible = ref(false)
const htmlViewMode = ref('render') // Default to render view
const showHighlight = ref(true)
const activeXPathField = ref(['list', 'title'])
const testResults = reactive({
    html: '',
    items: []
})

// 计算注入了高亮脚本的 HTML
const injectedHtml = computed(() => {
    if (!testResults.html) return ''
    
    const highlightScript = `
        <script>
            const COLORS = {
                list: { border: '#409eff', bg: 'rgba(64, 158, 255, 0.15)' },
                title: { border: '#67c23a', bg: 'rgba(103, 194, 58, 0.15)' },
                link: { border: '#e6a23c', bg: 'rgba(230, 162, 60, 0.15)' },
                time: { border: '#9c27b0', bg: 'rgba(156, 39, 176, 0.15)' }
            };

            function highlightElements(configs) {
                // 移除所有旧高亮，除了正在定位的
                document.querySelectorAll('.xpath-highlight:not(.locating)').forEach(el => {
                    el.classList.remove('xpath-highlight');
                    el.style.outline = '';
                    el.style.backgroundColor = '';
                    el.style.boxShadow = '';
                });

                if (!configs || configs.length === 0) return;

                configs.forEach(config => {
                    if (!config.xpath) return;
                    const color = COLORS[config.type] || COLORS.list;
                    
                    try {
                        const result = document.evaluate(config.xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                        for (let i = 0; i < result.snapshotLength; i++) {
                            const node = result.snapshotItem(i);
                            if (node.nodeType === 1) { // Element node
                                node.classList.add('xpath-highlight');
                                node.style.outline = '1px dashed ' + color.border;
                                node.style.outlineOffset = '-1px';
                                node.style.backgroundColor = color.bg;
                            }
                        }
                    } catch (e) {
                        console.error('XPath evaluation error for ' + config.type + ':', e);
                    }
                });
            }

            function locateElement(xpath, type, listXpath) {
                console.log('Locating element:', type, xpath, 'with listXpath:', listXpath);
                try {
                    let targets = [];
                    
                    if (type === 'list' || !listXpath) {
                        const result = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                        for (let i = 0; i < result.snapshotLength; i++) {
                            const node = result.snapshotItem(i);
                            const target = node.nodeType === 1 ? node : node.parentElement;
                            if (target) targets.push(target);
                        }
                    } else {
                        const containers = document.evaluate(listXpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                        for (let i = 0; i < containers.snapshotLength; i++) {
                            const container = containers.snapshotItem(i);
                            try {
                                const result = document.evaluate(xpath, container, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                                for (let j = 0; j < result.snapshotLength; j++) {
                                    const node = result.snapshotItem(j);
                                    const target = node.nodeType === 1 ? node : (node.parentElement || node.ownerElement);
                                    if (target) targets.push(target);
                                }
                            } catch (e) {
                                console.warn('Child XPath evaluation failed for container', i, e);
                            }
                        }
                    }

                    if (targets.length > 0) {
                        targets[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
                        
                        const color = COLORS[type] || COLORS.list;
                        targets.forEach(target => {
                            // 清除旧的定位状态
                            target.classList.add('locating');
                            
                            // 持久化高亮样式
                            target.style.outline = '3px solid ' + color.border;
                            target.style.outlineOffset = '2px';
                            target.style.boxShadow = '0 0 15px ' + color.border;
                            target.style.zIndex = '9999';
                            target.style.transition = 'all 0.3s ease';

                            // 柔和的背景闪烁动画
                            target.animate([
                                { backgroundColor: color.bg },
                                { backgroundColor: color.bg.replace('0.15', '0.4') },
                                { backgroundColor: color.bg }
                            ], {
                                duration: 1500,
                                iterations: 2,
                                easing: 'ease-in-out'
                            });

                            // 3秒后移除定位特有的强高亮，恢复普通高亮
                            setTimeout(() => {
                                target.classList.remove('locating');
                                target.style.outline = '1px dashed ' + color.border;
                                target.style.outlineOffset = '-1px';
                                target.style.boxShadow = '';
                                target.style.zIndex = '';
                            }, 3000);
                        });
                    }
                } catch (e) {
                    console.error('XPath locate error:', e);
                }
            }

            window.addEventListener('message', (event) => {
                if (event.data.type === 'highlight') {
                    highlightElements(event.data.configs);
                } else if (event.data.type === 'locate') {
                    locateElement(event.data.xpath, event.data.fieldType, event.data.listXpath);
                }
            });
        <\/script>
        <style>
            .xpath-highlight {
                transition: all 0.2s ease;
                position: relative !important;
                z-index: 1;
            }
            .xpath-highlight:hover {
                filter: brightness(0.9);
                z-index: 10;
            }
        </style>
    `
    // 注入到 </body> 前
    if (testResults.html.includes('</body>')) {
        return testResults.html.replace('</body>', highlightScript + '</body>')
    }
    return testResults.html + highlightScript
})

const onIframeLoad = () => {
    if (showHighlight.value) {
        updateHighlight()
    }
}

const updateHighlight = () => {
    if (previewIframe.value && previewIframe.value.contentWindow) {
        const configs = []
        if (showHighlight.value) {
            if (form.list_xpath) configs.push({ type: 'list', xpath: form.list_xpath })
            if (form.title_xpath) configs.push({ type: 'title', xpath: form.title_xpath })
            if (form.link_xpath) configs.push({ type: 'link', xpath: form.link_xpath })
            if (form.time_xpath) configs.push({ type: 'time', xpath: form.time_xpath })
        }
        
        previewIframe.value.contentWindow.postMessage({
            type: 'highlight',
            configs: configs
        }, '*')
    }
}

const locateElement = (type) => {
    let xpath = ''
    switch(type) {
        case 'list': xpath = form.list_xpath; break
        case 'title': xpath = form.title_xpath; break
        case 'link': xpath = form.link_xpath; break
        case 'time': xpath = form.time_xpath; break
    }
    
    if (!xpath) {
        ElMessage.warning('请先输入 XPath')
        return
    }

    // 如果当前在源码视图，先切换到渲染视图
    if (htmlViewMode.value !== 'render') {
        htmlViewMode.value = 'render'
        
        // 监听 iframe 重新挂载
        const unwatch = watch(previewIframe, (newIframe) => {
            if (newIframe) {
                // 等待 iframe 加载完成
                const onIframeReady = () => {
                    sendLocateMessage(xpath, type)
                    newIframe.removeEventListener('load', onIframeReady)
                    unwatch()
                }
                newIframe.addEventListener('load', onIframeReady)
            }
        }, { immediate: true })

        // 防御性超时，防止 watch 没触发
        setTimeout(() => {
            if (previewIframe.value) {
                sendLocateMessage(xpath, type)
                unwatch()
            }
        }, 1000)
    } else {
        if (!previewIframe.value || !previewIframe.value.contentWindow) {
            ElMessage.error('渲染引擎未就绪')
            return
        }
        sendLocateMessage(xpath, type)
    }
}

const sendLocateMessage = (xpath, type) => {
    if (previewIframe.value && previewIframe.value.contentWindow) {
        previewIframe.value.contentWindow.postMessage({
            type: 'locate',
            xpath: xpath,
            fieldType: type,
            listXpath: form.list_xpath // 传递容器 XPath 用于相对定位
        }, '*')
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
    retry_enabled: true,
    max_retries: 3,
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
        enabled: true,
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

const handleAdd = () => {
    isEdit.value = false
    activeTab.value = 'basic'
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
        retry_enabled: true,
        max_retries: 3,
        params: {
            engine: 'playwright',
            wait_for: 'networkidle',
            wait_time: 3000,
            timeout: 30000,
            wait_for_selector: '',
            user_agent: '',
            viewport: { width: 1920, height: 1080 },
            stealth: true,
            no_images: true,
            no_css: true,
            block_images: false,
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
            enabled: true,
            ttl: 3600
        },
        enabled_schedule: false,
        enabled: true,
        cron: ''
    })
    dialogVisible.value = true
}

const handleEdit = async (row) => {
    isEdit.value = true
    activeTab.value = 'basic'
    
    // 基础赋值
    Object.assign(form, JSON.parse(JSON.stringify(row)))
    
    // 确保嵌套对象存在且有默认值
    if (!form.params) {
        form.params = {
            engine: row.engine || 'playwright',
            wait_for: row.wait_for || 'networkidle',
            wait_time: row.wait_time !== undefined ? row.wait_time : 3000,
            timeout: row.wait_timeout || 30000,
            wait_for_selector: row.wait_for_selector || '',
            user_agent: row.user_agent || '',
            viewport: row.viewport || { width: 1920, height: 1080 },
            stealth: row.stealth !== undefined ? row.stealth : true,
            no_css: row.no_css !== undefined ? row.no_css : true,
            block_images: row.block_images !== undefined ? row.block_images : (row.no_images !== undefined ? row.no_images : true),
            block_media: row.block_media || false,
            proxy: row.proxy || { server: '', username: '', password: '' },
            proxy_pool_group: row.proxy_pool_group || '',
            cookies: row.cookies || '',
            intercept_apis: row.intercept_apis || [],
            intercept_continue: row.intercept_continue || false,
            storage_type: row.storage_type || 'mongo',
            mongo_collection: row.mongo_collection || '',
            oss_path: row.oss_path || '',
            save_html: row.save_html !== undefined ? row.save_html : true,
            screenshot: row.screenshot || false,
            is_fullscreen: row.is_fullscreen || false,
        }
    }

    if (!form.cache) {
        form.cache = row.cache || { enabled: true, ttl: 3600 }
    }
    
    // 补齐缺失的字段
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
    if (!formRef.value) return
    await formRef.value.validate(async (valid) => {
        if (valid) {
            submitting.value = true
            try {
                // Remove empty optional fields
                const data = JSON.parse(JSON.stringify(form))
                if (!data.rule_id) delete data.rule_id
                if (!data.time_xpath) delete data.time_xpath
                if (!data.pagination_next_xpath) delete data.pagination_next_xpath
                if (!data.params.wait_for_selector) delete data.params.wait_for_selector
                if (!data.params.user_agent) delete data.params.user_agent

                if (isEdit.value) {
                    await updateScraper(form._id, data)
                    ElMessage.success('保存成功')
                } else {
                    await createScraper(data)
                    ElMessage.success('保存成功')
                }
                
                // 如果当前正在校验规则，只关闭校验弹窗，保留主弹窗
                if (testResultVisible.value) {
                    testResultVisible.value = false
                } else {
                    // 如果是在主弹窗点击保存，则关闭主弹窗
                    dialogVisible.value = false
                }
                
                fetchData()
            } catch (error) {
                ElMessage.error(error.response?.data?.detail || '提交失败')
            } finally {
                submitting.value = false
            }
        }
    })
}

const handleAIExtract = async () => {
    if (!form.url) {
        ElMessage.warning('请先填写起始 URL')
        return
    }

    aiExtracting.value = true
    try {
        const res = await aiExtractScraper({
            url: form.url,
            // 同步浏览器配置到 AI 接口以确保能正确抓取页面
            engine: form.params.engine,
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
        })

        if (res.status === 'success' && res.data) {
            const data = res.data
            if (data.list_xpath) form.list_xpath = data.list_xpath
            if (data.title_xpath) form.title_xpath = data.title_xpath
            if (data.link_xpath) form.link_xpath = data.link_xpath
            if (data.time_xpath) form.time_xpath = data.time_xpath
            
            ElMessage.success('AI 智能解析完成，已自动填充 XPath 规则')
            
            // 自动跳转到规则校验（可选，或者提示用户手动校验）
            ElMessageBox.confirm('AI 已生成初步规则，是否立即进行规则校验以验证准确性？', '解析成功', {
                confirmButtonText: '立即校验',
                cancelButtonText: '稍后手动校验',
                type: 'success'
            }).then(() => {
                handleTest()
            }).catch(() => {})
        } else {
            ElMessage.warning('AI 未能识别出有效的 XPath 规则，请尝试手动配置')
        }
    } catch (error) {
        ElMessage.error(error.response?.data?.detail || 'AI 智能解析失败')
    } finally {
        aiExtracting.value = false
    }
}

const handleTest = async () => {
    if (!form.url || !form.list_xpath || !form.title_xpath || !form.link_xpath) {
        ElMessage.warning('请先填写完整的 URL 和基础 XPath 规则')
        return
    }

    testing.value = true
    try {
        const res = await testScraper({
            url: form.url,
            list_xpath: form.list_xpath,
            title_xpath: form.title_xpath,
            link_xpath: form.link_xpath,
            time_xpath: form.time_xpath,
            // 同步浏览器配置到测试接口
            engine: form.params.engine,
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
        })
        testResults.items = res.items
        testResults.html = res.html
        testResultVisible.value = true
        htmlViewMode.value = 'render' 
        activeXPathField.value = ['list', 'title']
        ElMessage.success(`校验成功，提取到 ${res.items.length} 条数据`)
    } catch (error) {
        ElMessage.error(error.response?.data?.detail || '校验失败')
    } finally {
        testing.value = false
    }
}

onMounted(() => {
    fetchData()
    loadProxyGroups()
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
    color: #475569;
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
</style>
