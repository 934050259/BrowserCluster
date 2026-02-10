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
        <el-table-column prop="url" label="起始 URL" min-width="250" show-overflow-tooltip>
          <template #default="{ row }">
            <el-link :href="row.url" target="_blank" type="primary" :underline="false">
              {{ row.url }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column label="关联规则" min-width="150">
           <template #default="{ row }">
             <el-tag v-if="row.rule_id" type="info">{{ getRuleName(row.rule_id) }}</el-tag>
             <span v-else class="text-gray">-</span>
           </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="最后修改" width="180">
          <template #default="{ row }">
            {{ formatTime(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button-group>
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

    <!-- Config Dialog -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="isEdit ? '编辑采集任务' : '添加采集任务'" 
      width="850px"
      destroy-on-close
      top="5vh"
    >
      <el-form :model="form" label-width="120px" :rules="formRules" ref="formRef">
        <div class="section-group">
            <div class="section-title">基础信息</div>
            <el-form-item label="任务名称" prop="name">
                <el-input v-model="form.name" placeholder="请输入任务名称" />
            </el-form-item>
            <el-form-item label="起始 URL" prop="url">
                <el-input v-model="form.url" placeholder="列表页起始地址" />
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
                    <span v-if="currentDomain">已按域名 {{ currentDomain }} 自动筛选</span>
                    <span v-else>选择用于解析详情页的网站配置规则</span>
                </div>
            </el-form-item>
            <el-form-item label="描述">
                <el-input v-model="form.description" type="textarea" :rows="2" />
            </el-form-item>
        </div>

        <div class="section-group">
            <div class="section-title">列表提取规则 (XPath)</div>
            <el-form-item label="列表容器" prop="list_xpath">
                <el-input v-model="form.list_xpath" placeholder="//div[@class='list-item']" />
                <div class="input-tip">列表项的公共父级容器或每个列表项的 XPath</div>
            </el-form-item>
            <el-row :gutter="20">
                <el-col :span="12">
                    <el-form-item label="标题 XPath" prop="title_xpath">
                        <el-input v-model="form.title_xpath" placeholder=".//a/text()" />
                        <div class="input-tip">相对于列表容器</div>
                    </el-form-item>
                </el-col>
                <el-col :span="12">
                    <el-form-item label="链接 XPath" prop="link_xpath">
                        <el-input v-model="form.link_xpath" placeholder=".//a/@href" />
                        <div class="input-tip">相对于列表容器</div>
                    </el-form-item>
                </el-col>
            </el-row>
            <el-form-item label="时间 XPath">
                <el-input v-model="form.time_xpath" placeholder=".//span[@class='date']/text()" />
                <div class="input-tip">相对于列表容器 (可选)</div>
            </el-form-item>
        </div>

        <div class="section-group">
            <div class="section-title">翻页设置</div>
            <el-row :gutter="20">
                <el-col :span="12">
                    <el-form-item label="下一页 XPath">
                        <el-input v-model="form.pagination_next_xpath" placeholder="//a[@class='next']" />
                    </el-form-item>
                </el-col>
                <el-col :span="12">
                    <el-form-item label="最大页数">
                        <el-input-number v-model="form.max_pages" :min="1" :max="100" />
                    </el-form-item>
                </el-col>
            </el-row>
        </div>

        <div class="section-group">
            <div class="section-title">浏览器设置</div>
            <el-form-item label="等待元素" prop="wait_for_selector">
                <el-input v-model="form.wait_for_selector" placeholder=".content-loaded (等待该元素加载完成后再抓取)" />
            </el-form-item>
            <el-form-item label="超时时间(ms)">
                <el-input-number v-model="form.wait_timeout" :min="1000" :step="5000" :max="60000" />
                <div class="input-tip">页面加载及等待元素出现的总超时时间</div>
            </el-form-item>
            <el-form-item label="资源拦截">
                <el-checkbox v-model="form.no_images">不加载图片</el-checkbox>
                <el-checkbox v-model="form.no_css">不加载 CSS</el-checkbox>
                <div class="input-tip">不加载图片和 CSS 可极大提升抓取速度，但可能导致页面结构解析异常</div>
            </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
           <el-button type="warning" @click="handleTest" :loading="testing" icon="VideoPlay">校验规则</el-button>
           <div>
             <el-button @click="dialogVisible = false">取消</el-button>
             <el-button type="primary" @click="submitForm" :loading="submitting">保存</el-button>
           </div>
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
import { Plus, VideoPlay, Position, Link, Setting, Search, Delete, Refresh } from '@element-plus/icons-vue'
import { getScrapers, createScraper, updateScraper, deleteScraper, testScraper, getRules } from '@/api'

const scrapers = ref([])
const rules = ref([])
const router = useRouter()
const loading = ref(false)

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
    return rules.value.filter(rule => 
        rule.domain.includes(currentDomain.value) || 
        currentDomain.value.includes(rule.domain)
    )
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
    wait_for_selector: '',
    wait_timeout: 30000,
    no_images: true,
    no_css: true
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
        wait_for_selector: '',
        wait_timeout: 30000,
        no_images: true,
        no_css: true
    })
    dialogVisible.value = true
}

const handleEdit = (row) => {
    isEdit.value = true
    Object.assign(form, row)
    // Fix undefined fields
    if (!form.max_pages) form.max_pages = 5
    if (!form.wait_timeout) form.wait_timeout = 30000
    if (form.no_images === undefined) form.no_images = true
    if (form.no_css === undefined) form.no_css = true
    dialogVisible.value = true
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
                const data = { ...form }
                if (!data.rule_id) delete data.rule_id
                if (!data.time_xpath) delete data.time_xpath
                if (!data.pagination_next_xpath) delete data.pagination_next_xpath
                if (!data.wait_for_selector) delete data.wait_for_selector

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
            wait_for_selector: form.wait_for_selector,
            wait_timeout: form.wait_timeout,
            no_images: form.no_images,
            no_css: form.no_css
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
.scrapers-container {
    padding: 20px;
}
.page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}
.subtitle {
    color: #64748b;
    margin-top: 4px;
}
.section-group {
    background: #f8faff;
    border-radius: 8px;
    padding: 8px;
    margin-bottom: 20px;
    border: 1px solid #eef2f7;
}
.section-title {
    font-size: 14px;
    font-weight: 600;
    color: #1f2d3d;
    margin-bottom: 10px;
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
.input-tip {
    font-size: 12px;
    color: #94a3b8;
    margin-left: 10px;
    line-height: 1.4;
}
.dialog-footer {
    display: flex;
    justify-content: space-between;
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
