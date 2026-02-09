<template>
  <div class="task-records-container">
    <el-card class="records-card" :body-style="{ padding: '0' }">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-button @click="goBack" circle :icon="ArrowLeft" class="back-btn" />
            <div class="header-breadcrumb">
              <span class="parent-title" @click="goBack">定时任务</span>
              <el-icon class="separator"><ArrowRight /></el-icon>
              <span class="current-title">采集记录</span>
              <el-tag v-if="scheduleName" size="small" effect="plain" class="schedule-badge">
                {{ scheduleName }}
              </el-tag>
            </div>
          </div>
          <div class="header-actions">
            <el-button-group>
              <el-button 
                type="danger" 
                plain
                :disabled="selectedTasks.length === 0" 
                :icon="Delete"
                @click="handleBatchDelete"
              >
                批量删除
              </el-button>
              <el-button @click="loadTasks" :loading="loading" :icon="Refresh">
                刷新
              </el-button>
            </el-button-group>
          </div>
        </div>
      </template>

      <div class="filter-section">
        <el-form :inline="true" :model="filterForm" class="modern-filter-form">
          <div class="filter-row">
            <el-form-item label="任务状态">
              <el-radio-group v-model="filterForm.status" @change="handleFilter" size="default" class="segmented-control">
                <el-radio-button label="">全部</el-radio-button>
                <el-radio-button label="pending">等待中</el-radio-button>
                <el-radio-button label="processing">处理中</el-radio-button>
                <el-radio-button label="success">成功</el-radio-button>
                <el-radio-button label="failed">失败</el-radio-button>
              </el-radio-group>
            </el-form-item>
            
            <div class="filter-right">
              <el-form-item>
                <el-input 
                  v-model="filterForm.url" 
                  placeholder="搜索任务 ID 或 URL..." 
                  clearable 
                  class="search-input"
                  @keyup.enter="handleFilter"
                >
                  <template #prefix>
                    <el-icon><Search /></el-icon>
                  </template>
                </el-input>
              </el-form-item>
              
              <el-form-item>
                <el-button type="primary" @click="handleFilter" :icon="Search">查询</el-button>
                <el-button @click="resetFilter" :icon="Delete">重置</el-button>
              </el-form-item>
            </div>
          </div>
        </el-form>
      </div>

      <el-table 
        :data="tasks" 
        v-loading="loading" 
        style="width: 100%" 
        class="modern-table" 
        border 
        stripe
        highlight-current-row
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column prop="task_id" label="任务 ID" width="250">
          <template #default="{ row }">
            <div class="task-id-cell">
              <el-icon class="id-icon"><Document /></el-icon>
              <span class="id-text">{{ row.task_id }}</span>
              <el-button 
                link 
                type="primary" 
                :icon="CopyDocument" 
                class="copy-btn-hover"
                @click.stop="copyText(row.task_id)"
              />
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="url" label="目标 URL" min-width="300">
          <template #default="{ row }">
            <div class="url-cell">
              <el-link :href="row.url" target="_blank" type="primary" :underline="false" class="url-link">
                <el-icon><Link /></el-icon>
                <span class="url-text">{{ row.url }}</span>
              </el-link>
              <el-button 
                link 
                type="primary" 
                :icon="CopyDocument" 
                class="copy-btn-hover"
                @click.stop="copyText(row.url)"
              />
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="130" align="center">
          <template #default="{ row }">
            <div class="status-cell">
              <el-tag 
                :type="getStatusColor(row.status)" 
                effect="light" 
                round 
                class="status-tag"
              >
                <el-icon class="status-icon">
                  <CircleCheck v-if="row.status === 'success'" />
                  <CircleClose v-else-if="row.status === 'failed'" />
                  <Loading v-else-if="row.status === 'processing'" />
                  <Timer v-else />
                </el-icon>
                {{ formatStatus(row.status) }}
              </el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="性能耗时" width="160" align="center">
          <template #default="{ row }">
            <div class="performance-cell" v-if="row.duration || row.result?.metadata?.load_time">
              <div class="duration-bar-container">
                <el-tooltip placement="top">
                  <template #content>
                    总耗时: {{ row.duration?.toFixed(2) }}s<br/>
                    页面加载: {{ row.result?.metadata?.load_time?.toFixed(2) }}s
                  </template>
                  <div class="duration-visual">
                    <div class="duration-label">
                      <span class="total">{{ row.duration?.toFixed(1) }}s</span>
                    </div>
                    <div class="duration-bar">
                      <div 
                        class="bar-load" 
                        :style="{ width: getLoadPercent(row) + '%' }"
                      ></div>
                    </div>
                  </div>
                </el-tooltip>
              </div>
            </div>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>

        <el-table-column label="采集时间" width="180" align="center">
          <template #default="{ row }">
            <div class="time-cell">
              <div class="date">{{ formatDate(row.created_at).split(' ')[0] }}</div>
              <div class="time">{{ formatDate(row.created_at).split(' ')[1] }}</div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="150" fixed="right" align="center">
          <template #default="{ row }">
            <el-button 
              type="primary" 
              link 
              class="action-btn"
              @click="viewTaskDetail(row)"
            >
              详情
            </el-button>
            <el-button 
              type="danger" 
              link 
              class="action-btn"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @size-change="loadTasks"
          @current-change="loadTasks"
        />
      </div>
    </el-card>

    <el-dialog 
      v-model="showDetailDialog" 
      width="1000px" 
      top="5vh"
      destroy-on-close
      class="detail-dialog"
    >
      <template #header>
        <div class="detail-dialog-header">
          <span class="title">采集记录详情</span>
          <div class="header-tags" v-if="currentTask">
            <el-tag :type="getStatusColor(currentTask.status)" effect="dark" size="small" round>
              {{ formatStatus(currentTask.status) }}
            </el-tag>
            <span class="task-id">ID: {{ currentTask.task_id }}</span>
          </div>
        </div>
      </template>
      <div v-if="currentTask" class="task-details">
        <el-tabs v-model="activeTab" class="custom-tabs">
          <el-tab-pane name="info">
            <template #label>
              <div class="tab-label-box"><el-icon><InfoFilled /></el-icon><span>基础信息</span></div>
            </template>
            <div class="info-tab-content">
              <el-descriptions :column="2" border class="modern-descriptions">
                <!-- 第一行：任务 ID 和 状态 -->
                <el-descriptions-item>
                  <template #label>
                    <div class="label-box"><el-icon><Key /></el-icon><span>任务 ID</span></div>
                  </template>
                  <div class="value-content task-id-value">
                    <code>{{ currentTask.task_id }}</code>
                    <el-button link type="primary" :icon="CopyDocument" @click="copyText(currentTask.task_id)" />
                  </div>
                </el-descriptions-item>
                <el-descriptions-item>
                  <template #label>
                    <div class="label-box"><el-icon><InfoFilled /></el-icon><span>任务状态</span></div>
                  </template>
                  <div class="value-content">
                    <el-tag :type="getStatusColor(currentTask.status)" effect="dark" round>
                      {{ formatStatus(currentTask.status) }}
                    </el-tag>
                  </div>
                </el-descriptions-item>

                <!-- 第二行：目标 URL -->
                <el-descriptions-item :span="2">
                  <template #label>
                    <div class="label-box"><el-icon><Link /></el-icon><span>目标 URL</span></div>
                  </template>
                  <div class="value-content url-value">
                    <el-link :href="currentTask.url" target="_blank" type="primary" class="url-text">{{ currentTask.url }}</el-link>
                    <el-button link type="primary" :icon="CopyDocument" @click="copyText(currentTask.url)" />
                  </div>
                </el-descriptions-item>

                <!-- 第三行：创建时间和完成时间 -->
                <el-descriptions-item>
                  <template #label>
                    <div class="label-box"><el-icon><Timer /></el-icon><span>创建时间</span></div>
                  </template>
                  <div class="value-content time-value">{{ formatDate(currentTask.created_at) }}</div>
                </el-descriptions-item>
                <el-descriptions-item>
                  <template #label>
                    <div class="label-box">
                      <el-icon v-if="currentTask.status === 'success'"><CircleCheck /></el-icon>
                      <el-icon v-else-if="currentTask.status === 'failed'"><CircleClose /></el-icon>
                      <el-icon v-else><Timer /></el-icon>
                      <span>完成时间</span>
                    </div>
                  </template>
                  <div class="value-content time-value">{{ formatDate(currentTask.completed_at) || '-' }}</div>
                </el-descriptions-item>

                <!-- 第四行：总耗时和加载耗时 -->
                <el-descriptions-item>
                  <template #label>
                    <div class="label-box"><el-icon><Watch /></el-icon><span>总耗时</span></div>
                  </template>
                  <div class="value-content" v-if="currentTask.duration">
                    <el-tag type="warning" effect="plain" class="duration-tag">{{ currentTask.duration.toFixed(2) }}s</el-tag>
                  </div>
                  <span v-else class="empty-value">-</span>
                </el-descriptions-item>
                <el-descriptions-item>
                  <template #label>
                    <div class="label-box"><el-icon><Connection /></el-icon><span>加载耗时</span></div>
                  </template>
                  <div class="value-content" v-if="currentTask.result?.metadata?.load_time">
                    <el-tag type="info" effect="plain" class="duration-tag">{{ currentTask.result.metadata.load_time.toFixed(2) }}s</el-tag>
                  </div>
                  <span v-else class="empty-value">-</span>
                </el-descriptions-item>

                <!-- 第五行：缓存状态和执行节点 -->
                <el-descriptions-item>
                  <template #label>
                    <div class="label-box"><el-icon><Files /></el-icon><span>缓存状态</span></div>
                  </template>
                  <div class="value-content">
                    <el-tag :type="currentTask.cached ? 'success' : 'info'" effect="light" size="small">
                      {{ currentTask.cached ? '已命中缓存' : '实时采集' }}
                    </el-tag>
                  </div>
                </el-descriptions-item>
                <el-descriptions-item>
                  <template #label>
                    <div class="label-box"><el-icon><Cpu /></el-icon><span>执行节点</span></div>
                  </template>
                  <div class="value-content">
                    <el-tag type="info" effect="plain" size="small" class="node-tag">
                      {{ currentTask.node_id || '自动分配' }}
                    </el-tag>
                  </div>
                </el-descriptions-item>

                <!-- 第六行：浏览器引擎和解析模式 -->
                <el-descriptions-item>
                  <template #label>
                    <div class="label-box"><el-icon><Monitor /></el-icon><span>浏览器引擎</span></div>
                  </template>
                  <div class="value-content">
                    <el-tag size="small" effect="plain" class="engine-tag">{{ currentTask.params?.engine || 'playwright' }}</el-tag>
                  </div>
                </el-descriptions-item>
                <el-descriptions-item>
                  <template #label>
                    <div class="label-box"><el-icon><MagicStick /></el-icon><span>解析模式</span></div>
                  </template>
                  <div class="value-content">
                    <el-tag type="warning" size="small" v-if="currentTask.params?.parser === 'gne'">
                      GNE - {{ currentTask.params?.parser_config?.mode === 'list' ? '列表模式' : '详情模式' }}
                    </el-tag>
                    <el-tag type="success" size="small" v-else-if="currentTask.params?.parser === 'llm'">LLM 大模型提取</el-tag>
                    <el-tag type="primary" size="small" v-else-if="currentTask.params?.parser === 'xpath'">XPath 自定义</el-tag>
                    <el-tag type="info" size="small" v-else>不解析 (仅源码)</el-tag>
                  </div>
                </el-descriptions-item>

                <!-- 第七行：存储位置 -->
                <el-descriptions-item :span="2">
                  <template #label>
                    <div class="label-box"><el-icon><Box /></el-icon><span>存储位置</span></div>
                  </template>
                  <div class="value-content storage-value" v-if="currentTask.params?.storage_type">
                    <el-tag type="success" size="small" class="storage-tag">
                      <div class="tag-flex">
                        <el-icon><Collection v-if="currentTask.params.storage_type === 'mongo'" /><FolderOpened v-else /></el-icon>
                        <span>{{ currentTask.params.storage_type === 'mongo' ? 'MongoDB' : 'Aliyun OSS' }}</span>
                      </div>
                    </el-tag>
                    <code class="storage-path">
                      <template v-if="currentTask.params.storage_type === 'mongo'">
                        集合: {{ currentTask.params.mongo_collection || 'tasks_results' }}
                      </template>
                      <template v-else>
                        路径: {{ currentTask.params.oss_path || 'tasks/' }}{{ currentTask.task_id }}/
                      </template>
                    </code>
                  </div>
                  <div class="value-content storage-value" v-else>
                    <el-tag type="info" size="small" class="storage-tag">
                      <div class="tag-flex">
                        <el-icon><Collection /></el-icon>
                        <span>MongoDB (默认)</span>
                      </div>
                    </el-tag>
                    <code class="storage-path">集合: tasks_results</code>
                  </div>
                </el-descriptions-item>

                <!-- 第七行：解析规则 (全行) -->
                <el-descriptions-item :span="2" v-if="currentTask.params?.parser">
                  <template #label>
                    <div class="label-box"><el-icon><Setting /></el-icon><span>解析规则</span></div>
                  </template>
                  <div class="value-content rule-content">
                    <template v-if="currentTask.params.parser === 'gne' && currentTask.params.parser_config?.mode === 'list'">
                      <span class="rule-label">列表 XPath:</span>
                      <code>{{ currentTask.params.parser_config.list_xpath || '-' }}</code>
                    </template>
                    <template v-else-if="currentTask.params.parser === 'xpath'">
                      <div class="rule-tags">
                        <el-tag v-for="(path, field) in currentTask.params.parser_config?.rules" :key="field" size="small" class="mr-2 mb-1">
                          <span class="field-name">{{ field }}:</span> {{ path }}
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
                    <span v-else class="empty-value">系统自动识别</span>
                  </div>
                </el-descriptions-item>

                <!-- 第八行：实际 URL (如果有重定向) -->
                <el-descriptions-item :span="2" v-if="currentTask.result?.metadata?.actual_url && currentTask.result.metadata.actual_url !== currentTask.url">
                  <template #label>
                    <div class="label-box"><el-icon><Right /></el-icon><span>实际 URL</span></div>
                  </template>
                  <div class="value-content url-value">
                    <el-link :href="currentTask.result.metadata.actual_url" target="_blank" type="warning" class="url-text">{{ currentTask.result.metadata.actual_url }}</el-link>
                    <el-button link type="primary" :icon="CopyDocument" @click="copyText(currentTask.result.metadata.actual_url)" />
                  </div>
                </el-descriptions-item>
              </el-descriptions>
            </div>
          </el-tab-pane>

          <el-tab-pane name="data">
            <template #label>
              <div class="tab-label-box"><el-icon><Files /></el-icon><span>采集数据</span></div>
            </template>
            <div class="detail-section">
              <div class="section-header">
                <div class="left">
                  <span class="section-title">解析结果</span>
                  <el-tag size="small" type="info" effect="plain" class="ml-2">JSON 格式</el-tag>
                </div>
                <div class="right">
                  <el-button size="small" :icon="CopyDocument" @click="copyJson(currentTask.result?.parsed_data)">复制内容</el-button>
                </div>
              </div>
              <div class="code-container">
                <pre v-if="currentTask.result?.parsed_data" class="pretty-json"><code>{{ JSON.stringify(currentTask.result.parsed_data, null, 2) }}</code></pre>
                <el-empty v-else description="暂无解析数据" />
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane name="screenshot" v-if="currentTask.result?.screenshot || currentTask.result?.oss_screenshot || currentTask.params?.screenshot">
            <template #label>
              <div class="tab-label-box"><el-icon><Monitor /></el-icon><span>网页截图</span></div>
            </template>
            <div class="screenshot-tab-content" v-loading="loadingScreenshot">
              <div class="screenshot-toolbar" v-if="currentTask.result?.screenshot">
                <div class="left">
                  <span class="info-item"><el-icon><InfoFilled /></el-icon> 点击图片可查看原图</span>
                </div>
              </div>
              <div class="screenshot-wrapper">
                <template v-if="currentTask.result?.screenshot">
                  <el-image 
                    :src="currentTask.result.screenshot.startsWith('http') ? currentTask.result.screenshot : `data:image/png;base64,${currentTask.result.screenshot}`" 
                    :preview-src-list="[currentTask.result.screenshot.startsWith('http') ? currentTask.result.screenshot : `data:image/png;base64,${currentTask.result.screenshot}`]"
                    fit="contain"
                    class="main-screenshot"
                  >
                    <template #error>
                      <div class="image-error">
                        <el-icon :size="40"><CircleClose /></el-icon>
                        <span>截图加载失败</span>
                      </div>
                    </template>
                  </el-image>
                </template>
                <el-empty v-else-if="loadingScreenshot" description="正在从存储节点加载截图..." />
                <el-empty v-else description="该任务未配置或未生成截图" />
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane name="html" v-if="currentTask.result?.html || currentTask.result?.oss_html || currentTask.status === 'success'">
            <template #label>
              <div class="tab-label-box"><el-icon><Connection /></el-icon><span>HTML 源码</span></div>
            </template>
            <div class="detail-section">
              <div class="section-header">
                <div class="left">
                  <span class="section-title">原始 HTML</span>
                  <el-tag size="small" type="info" effect="plain" class="ml-2" v-if="currentTask.result?.html">
                    {{ (currentTask.result.html.length / 1024).toFixed(1) }} KB
                  </el-tag>
                </div>
                <div class="right">
                  <el-button size="small" :icon="CopyDocument" @click="copyText(currentTask.result?.html)" :disabled="!currentTask.result?.html">复制源码</el-button>
                </div>
              </div>
              <div class="code-container" v-loading="loadingHtml">
                <pre v-if="currentTask.result?.html" class="pretty-code"><code>{{ currentTask.result.html }}</code></pre>
                <el-empty v-else-if="loadingHtml" description="正在从存储节点加载 HTML 源码..." />
                <el-empty v-else description="暂无 HTML 源码数据" />
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane name="error" v-if="currentTask.status === 'failed'">
            <template #label>
              <div class="tab-label-box error-label"><el-icon><CircleClose /></el-icon><span>错误详情</span></div>
            </template>
            <div class="error-tab-content">
              <div class="error-header">
                <el-icon :size="24" color="#f56c6c"><CircleClose /></el-icon>
                <span class="error-title">采集任务执行失败</span>
              </div>
              <div class="error-card">
                <div class="error-msg-box">
                  <div class="msg-label">错误信息</div>
                  <div class="msg-content">{{ currentTask.error?.message || '未知错误' }}</div>
                </div>
                <div class="error-stack-box" v-if="currentTask.error?.stack">
                  <div class="stack-label">堆栈跟踪 (Stack Trace)</div>
                  <pre class="stack-content"><code>{{ currentTask.error.stack }}</code></pre>
                </div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, ArrowRight, Refresh, Search, Link, View, CopyDocument, Timer, CircleCheck, CircleClose, Cpu, QuestionFilled, Key, InfoFilled, Watch, Connection, Files, Monitor, MagicStick, Setting, Box, Right, Delete, Document, Loading } from '@element-plus/icons-vue'
import { getTasks, getTask, getSchedule, deleteTask, deleteTasksBatch } from '../api'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()
const scheduleId = route.query.schedule_id
const scheduleName = ref('')

const loading = ref(false)
const loadingHtml = ref(false)
const loadingScreenshot = ref(false)
const tasks = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const selectedTasks = ref([])

const filterForm = ref({
  status: '',
  url: ''
})

const showDetailDialog = ref(false)
const currentTask = ref(null)
const activeTab = ref('data')

// 监听标签页切换，按需加载大数据字段
watch(activeTab, async (newTab) => {
  if (!currentTask.value) return
  
  const taskId = currentTask.value.task_id
  const result = currentTask.value.result || {}
  
  if (newTab === 'html') {
    if (result.html || loadingHtml.value) return
    
    loadingHtml.value = true
    try {
      // 后端 getTask API 会自动从 OSS 加载内容并返回在 result.html 中
      const data = await getTask(taskId, { include_html: true, include_screenshot: false })
      if (data.result?.html) {
        if (!currentTask.value.result) currentTask.value.result = {}
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
      const data = await getTask(taskId, { include_html: false, include_screenshot: true })
      if (data.result?.screenshot) {
        if (!currentTask.value.result) currentTask.value.result = {}
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

const loadTasks = async () => {
  if (!scheduleId) {
    ElMessage.warning('缺少定时任务 ID')
    return
  }
  
  loading.value = true
  try {
    const params = {
      schedule_id: scheduleId,
      status: filterForm.value.status || undefined,
      url: filterForm.value.url || undefined,
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value
    }
    const data = await getTasks(params)
    tasks.value = data.tasks
    total.value = data.total
  } catch (error) {
    ElMessage.error('加载记录失败')
  } finally {
    loading.value = false
  }
}

const loadScheduleInfo = async () => {
  if (!scheduleId) return
  try {
    const data = await getSchedule(scheduleId)
    scheduleName.value = data.name
  } catch (e) {
    console.error('Fetch schedule info failed:', e)
  }
}

const handleFilter = () => {
  currentPage.value = 1
  loadTasks()
}

const resetFilter = () => {
  filterForm.value = { status: '', url: '' }
  handleFilter()
}

const goBack = () => {
  router.push('/schedules')
}

const handleSelectionChange = (val) => {
  selectedTasks.value = val
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除这条采集记录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await deleteTask(row.task_id)
    ElMessage.success('删除成功')
    loadTasks()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleBatchDelete = async () => {
  if (selectedTasks.value.length === 0) return
  
  try {
    await ElMessageBox.confirm(`确定要删除选中的 ${selectedTasks.value.length} 条记录吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const taskIds = selectedTasks.value.map(task => task.task_id)
    await deleteTasksBatch(taskIds)
    ElMessage.success('批量删除成功')
    selectedTasks.value = []
    loadTasks()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量删除失败')
    }
  }
}

const viewTaskDetail = async (row) => {
  try {
    loadingHtml.value = false
    loadingScreenshot.value = false
    // 初始只获取基本信息
    const data = await getTask(row.task_id, { include_html: false, include_screenshot: false })
    currentTask.value = data
    activeTab.value = data.result?.parsed_data ? 'data' : 'info'
    showDetailDialog.value = true
  } catch (error) {
    ElMessage.error('获取详情失败')
  }
}

const getStatusColor = (status) => {
  const colors = {
    pending: 'info',
    processing: 'primary',
    success: 'success',
    failed: 'danger'
  }
  return colors[status] || 'info'
}

const getLoadPercent = (row) => {
  if (!row.duration || !row.result?.metadata?.load_time) return 0
  return Math.min(100, (row.result.metadata.load_time / row.duration) * 100)
}

const formatStatus = (status) => {
  const labels = {
    pending: '等待中',
    processing: '处理中',
    success: '成功',
    failed: '失败'
  }
  return labels[status] || status
}

const formatDate = (date) => {
  if (!date) return '-'
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

const copyJson = (data) => {
  if (!data) return
  const text = JSON.stringify(data, null, 2)
  copyText(text)
}

const copyText = (text) => {
  if (!text) return
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制到剪贴板')
  })
}

onMounted(() => {
  loadTasks()
  loadScheduleInfo()
})
</script>

<style scoped>
.task-records-container {
  padding: 24px;
  background-color: #f5f7fa;
  min-height: calc(100vh - 60px);
}

.records-card {
  border-radius: 12px;
  border: none;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

/* Header Styles */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.parent-title {
  color: #909399;
  cursor: pointer;
  transition: color 0.2s;
}

.parent-title:hover {
  color: var(--el-color-primary);
}

.separator {
  color: #c0c4cc;
  font-size: 12px;
}

.current-title {
  font-weight: 600;
  color: #303133;
  font-size: 16px;
}

.schedule-badge {
  margin-left: 4px;
  border-radius: 4px;
  background-color: #f0f2f5;
  border: none;
  color: #606266;
}

/* Filter Section */
.filter-section {
  padding: 20px 24px;
  background-color: #fff;
  border-bottom: 1px solid #f0f0f0;
}

.modern-filter-form :deep(.el-form-item) {
  margin-bottom: 0;
  margin-right: 24px;
}

.filter-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.filter-right {
  display: flex;
  align-items: center;
}

.segmented-control :deep(.el-radio-button__inner) {
  border-radius: 6px !important;
  margin: 0 4px;
  border: 1px solid transparent !important;
  background-color: #f4f4f5;
  color: #606266;
  box-shadow: none !important;
  transition: all 0.2s;
}

.segmented-control :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background-color: #fff;
  color: var(--el-color-primary);
  border-color: var(--el-color-primary) !important;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
}

.search-input {
  width: 280px;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: 8px;
  background-color: #f5f7fa;
  box-shadow: none !important;
  border: 1px solid transparent;
  transition: all 0.2s;
}

.search-input :deep(.el-input__wrapper.is-focus) {
  background-color: #fff;
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 1px var(--el-color-primary) !important;
}

/* Table Styles */
.modern-table {
  --el-table-header-bg-color: #f8faff;
  --el-table-row-hover-bg-color: #f5f8ff;
  border: none !important;
}

.modern-table :deep(th.el-table__cell) {
  font-weight: 600;
  color: #303133;
  height: 50px;
}

.task-id-cell, .url-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.id-icon {
  color: #909399;
  font-size: 14px;
}

.id-text {
  font-family: 'Fira Code', monospace;
  font-size: 13px;
  color: #606266;
}

.url-link {
  display: flex;
  align-items: center;
  gap: 4px;
  max-width: calc(100% - 30px);
}

.url-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.copy-btn-hover {
  opacity: 0;
  transition: opacity 0.2s;
  padding: 4px;
}

tr:hover .copy-btn-hover {
  opacity: 1;
}

.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0 12px;
  height: 28px;
  font-weight: 500;
}

.status-icon {
  font-size: 14px;
}

/* Performance Cell */
.performance-cell {
  width: 100%;
  padding: 0 8px;
}

.duration-visual {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.duration-label {
  display: flex;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: #606266;
}

.duration-bar {
  height: 6px;
  background-color: #ebeef5;
  border-radius: 3px;
  overflow: hidden;
  position: relative;
}

.bar-load {
  height: 100%;
  background: linear-gradient(90deg, #409eff, #36cfc9);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.time-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  line-height: 1.4;
}

.date {
  font-size: 13px;
  color: #303133;
}

.time {
  font-size: 12px;
  color: #909399;
}

.action-btn {
  font-weight: 600;
  font-size: 14px;
}

.pagination-container {
  padding: 24px;
  display: flex;
  justify-content: flex-end;
  background-color: #fff;
}

/* Detail Dialog Styles */
.detail-dialog :deep(.el-dialog) {
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
}

.detail-dialog :deep(.el-dialog__header) {
  margin: 0;
  padding: 20px 24px;
  background-color: #fff;
  border-bottom: 1px solid #f0f0f0;
}

.detail-dialog-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.detail-dialog-header .title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.header-tags {
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-id {
  font-size: 13px;
  color: #909399;
  font-family: monospace;
  background-color: #f5f7fa;
  padding: 2px 8px;
  border-radius: 4px;
}

.custom-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 0 24px;
  background-color: #f8faff;
}

.custom-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.custom-tabs :deep(.el-tabs__item) {
  height: 50px;
  font-weight: 500;
  transition: all 0.3s;
}

.custom-tabs :deep(.el-tabs__item.is-active) {
  font-weight: 600;
}

.tab-label-box {
  display: flex;
  align-items: center;
  gap: 8px;
}

.storage-info-wrapper {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.storage-detail-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
  background: #f1f5f9;
  padding: 4px 10px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  width: fit-content;
}

.storage-detail-tag code {
  background: #fff;
  padding: 1px 4px;
  border-radius: 4px;
  color: #3b82f6;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  border: 1px solid #e2e8f0;
}

.info-tab-content {
  padding: 24px;
}

.modern-descriptions :deep(.el-descriptions__label) {
  width: 140px;
  background-color: #f9fbff !important;
  color: #606266;
  font-weight: 600;
}

.modern-descriptions :deep(.el-descriptions__content) {
  padding: 12px 16px;
}

.label-box {
  display: flex;
  align-items: center;
  gap: 8px;
}

.value-content {
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-id-value code {
  background-color: #f0f2f5;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Fira Code', monospace;
  color: #409eff;
}

.url-value {
  display: flex;
  align-items: center;
  gap: 8px;
}

.url-text {
  word-break: break-all;
  line-height: 1.4;
}

.tag-flex {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.storage-value {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.storage-tag {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 8px;
  height: 24px;
}

.storage-path {
  font-family: 'Fira Code', monospace;
  font-size: 12px;
  color: #64748b;
  background-color: #f8fafc;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
}

.duration-tag {
  font-weight: 600;
  font-family: monospace;
}

.detail-section {
  padding: 24px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.code-container {
  background-color: #1e1e1e;
  border-radius: 12px;
  padding: 16px;
  max-height: 500px;
  overflow: auto;
  box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.2);
}

.pretty-json, .pretty-code {
  margin: 0;
  font-family: 'Fira Code', 'Cascadia Code', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #d4d4d4;
}

.pretty-json code, .pretty-code code {
  white-space: pre-wrap;
  word-break: break-all;
}

/* Screenshot Styles */
.screenshot-tab-content {
  padding: 24px;
}

.screenshot-toolbar {
  margin-bottom: 16px;
  padding: 12px 16px;
  background-color: #f8faff;
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #909399;
}

.screenshot-wrapper {
  background-color: #f0f2f5;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  justify-content: center;
  min-height: 300px;
}

.main-screenshot {
  max-width: 100%;
  border-radius: 4px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  cursor: zoom-in;
}

.image-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #909399;
}

/* Error Card */
.error-tab-content {
  padding: 24px;
}

.error-card {
  border-left: 4px solid var(--el-color-danger);
  background-color: #fff5f5;
}

.error-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--el-color-danger);
  font-weight: 600;
}

.error-message {
  margin-bottom: 20px;
  padding: 12px;
  background-color: #fff;
  border-radius: 4px;
  color: #303133;
  font-size: 14px;
  border: 1px solid #ffdbdb;
}

.stack-trace {
  background-color: #1e1e1e;
  border-radius: 8px;
  padding: 16px;
  overflow: auto;
  max-height: 400px;
}

.stack-trace pre {
  margin: 0;
  color: #ff8e8e;
  font-family: monospace;
  font-size: 12px;
  line-height: 1.5;
}

@media (max-width: 768px) {
  .filter-row {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .filter-right {
    width: 100%;
    justify-content: space-between;
  }
  
  .search-input {
    width: 100%;
    flex: 1;
  }
}
</style>
