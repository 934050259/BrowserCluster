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
      <el-table :data="rules" v-loading="loading" style="width: 100%">
        <el-table-column prop="domain" label="域名" min-width="150" />
        <el-table-column prop="parser_type" label="解析类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getParserTypeTag(row.parser_type)">{{ row.parser_type.toUpperCase() }}</el-tag>
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

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑配置' : '添加配置'" width="700px">
      <el-form :model="form" label-width="100px" :rules="formRules" ref="formRef">
        <el-tabs v-model="activeTab" class="config-tabs">
          <el-tab-pane label="基础配置" name="basic">
            <el-form-item label="域名" prop="domain">
              <el-input v-model="form.domain" placeholder="例如: example.com" />
            </el-form-item>
            <el-form-item label="Cookies" prop="cookies">
              <el-input 
                v-model="form.cookies" 
                type="textarea" 
                :rows="6" 
                placeholder="请输入网站 Cookies (JSON 格式或 Raw 字符串)" 
              />
              <p class="form-tip">配置后任务执行时将自动携带该 Cookies</p>
            </el-form-item>
            <el-form-item label="描述">
              <el-input v-model="form.description" type="textarea" placeholder="配置说明" />
            </el-form-item>
          </el-tab-pane>

          <el-tab-pane label="解析规则" name="parser">
            <el-form-item label="解析类型" prop="parser_type">
              <el-radio-group v-model="form.parser_type">
                <el-radio-button label="gne">GNE</el-radio-button>
                <el-radio-button label="llm">LLM</el-radio-button>
                <el-radio-button label="xpath">XPath</el-radio-button>
              </el-radio-group>
            </el-form-item>
            
            <!-- GNE Config -->
            <div v-if="form.parser_type === 'gne'">
              <el-alert title="GNE (General News Extractor) 会自动提取网页的正文、标题、发布时间等通用信息，无需额外配置。" type="info" :closable="false" style="margin-bottom: 20px" />
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
            <div v-if="form.parser_type === 'xpath'">
              <el-form-item label="XPath规则">
                <div v-for="(item, index) in xpathRules" :key="index" class="xpath-rule-item">
                  <el-input v-model="item.field" placeholder="字段名" style="width: 120px" />
                  <el-input v-model="item.xpath" placeholder="XPath 表达式" style="flex: 1; margin-left: 10px" />
                  <el-button type="danger" :icon="Delete" circle @click="removeXpathRule(index)" style="margin-left: 10px" />
                </div>
                <el-button type="primary" plain :icon="Plus" @click="addXpathRule" style="margin-top: 10px">添加字段</el-button>
              </el-form-item>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, MagicStick, Connection } from '@element-plus/icons-vue'
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
  parser_config: {},
  cookies: '',
  description: '',
  is_active: true
})

const formRules = {
  domain: [{ required: true, message: '请输入域名', trigger: 'blur' }],
  parser_type: [{ required: true, message: '请选择解析类型', trigger: 'change' }]
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
    parser_config: {},
    cookies: '',
    description: '',
    is_active: true
  })
  selectedLlmFields.value = ['title', 'content']
  form.parser_config = { fields: ['title', 'content'] }
  xpathRules.value = [{ field: '', xpath: '' }]
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  activeTab.value = 'basic'
  Object.assign(form, row)
  
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

onMounted(() => {
  fetchRules()
})
</script>

<style scoped>
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
}
.xpath-rule-item {
  display: flex;
  margin-bottom: 10px;
}
.form-tip {
  font-size: 12px;
  color: #909399;
  margin: 5px 0 0;
  line-height: 1.4;
}
.config-tabs {
  margin-top: -10px;
}
:deep(.el-tabs__content) {
  padding-top: 20px;
}

/* LLM Parser Styles */
.parser-config-area {
  background: #f8fafc;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
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
.mt-4 {
  margin-top: 16px;
}
.input-tip {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
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
</style>
