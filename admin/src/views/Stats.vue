<template>
  <div class="stats-container">
    <el-row :gutter="20">
      <el-col :span="6" v-for="item in statCards" :key="item.label">
        <el-card shadow="hover" class="stat-card" :body-style="{ padding: '20px' }">
          <div class="card-content">
            <div class="icon-box" :class="item.type">
              <el-icon><component :is="item.icon" /></el-icon>
            </div>
            <div class="text-box">
              <div class="stat-label">{{ item.label }}</div>
              <div class="stat-value">
                <span class="number">{{ item.value }}</span>
                <span class="unit" v-if="item.unit">{{ item.unit }}</span>
              </div>
            </div>
          </div>
          <div class="card-footer">
            <template v-if="item.trend !== undefined">
              <span class="trend" :class="item.trend > 0 ? (item.type === 'danger' ? 'down' : 'up') : (item.trend < 0 ? (item.type === 'danger' ? 'up' : 'down') : 'neutral')">
                {{ item.trend > 0 ? '+' : '' }}{{ item.trend }}% 
                <el-icon v-if="item.trend !== 0">
                  <CaretTop v-if="item.trend > 0" />
                  <CaretBottom v-else />
                </el-icon>
              </span>
              <span class="tip">较昨日</span>
            </template>
            <template v-else>
              <span class="trend neutral">0%</span>
              <span class="tip">较昨日</span>
            </template>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="chart-row">
      <el-col :span="16">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span>任务处理分析</span>
              <el-radio-group v-model="chartTimeRange" size="small">
                <el-radio-button label="today">今日</el-radio-button>
                <el-radio-button label="week">近一周</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="chartRef" style="height: 480px;"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" header="实时队列状态" class="queue-card-main full-height-card">
          <div class="queue-summary">
            <div class="total-queue">
              <div class="val">{{ totalQueue }}</div>
              <div class="lab">当前排队总数</div>
            </div>
          </div>
          <div class="queue-container">
            <div v-for="q in queueItems" :key="q.label" class="queue-item">
              <div class="q-info">
                <span class="q-label">
                  <span class="dot" :style="{ backgroundColor: q.color }"></span>
                  {{ q.label }}
                </span>
                <span class="q-value">{{ q.value }}</span>
              </div>
              <el-progress 
                :percentage="calculatePercentage(q.value)" 
                :color="q.color"
                :show-text="false"
                :stroke-width="6"
              />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useStatsStore } from '../stores/stats'
import * as echarts from 'echarts'
import { Timer, Checked, CircleClose, DataLine, CaretTop, CaretBottom } from '@element-plus/icons-vue'

const statsStore = useStatsStore()
const chartRef = ref(null)
const chartTimeRange = ref('today')
let chart = null

const stats = computed(() => statsStore.stats)
const totalQueue = computed(() => statsStore.totalQueue)

const statCards = computed(() => [
  { label: '今日任务总量', value: stats.value.today.total, icon: DataLine, type: 'primary', unit: '', trend: stats.value.trends.total },
  { label: '成功处理', value: stats.value.today.success, icon: Checked, type: 'success', unit: '', trend: stats.value.trends.success },
  { label: '失败记录', value: stats.value.today.failed, icon: CircleClose, type: 'danger', unit: '', trend: stats.value.trends.failed },
  { label: '平均响应时间', value: stats.value.today.avg_duration?.toFixed(2) || 0, icon: Timer, type: 'warning', unit: 's', trend: stats.value.trends.avg_duration }
])

const queueItems = computed(() => [
  { label: '等待中', value: stats.value.queue.pending, color: '#909399' },
  { label: '处理中', value: stats.value.queue.processing, color: '#e6a23c' },
  { label: '已完成', value: stats.value.queue.success, color: '#67c23a' },
  { label: '已失败', value: stats.value.queue.failed, color: '#f56c6c' }
])

const calculatePercentage = (value) => {
  const q = stats.value.queue
  const total = q.pending + q.processing + q.success + q.failed
  return total > 0 ? (value / total) * 100 : 0
}

const updateChart = () => {
  if (!chart && chartRef.value) {
    chart = echarts.init(chartRef.value)
  }
  if (!chart) return
  
  let option = {}
  
  if (chartTimeRange.value === 'today') {
    // 今日数据展示为柱状图 (支持分时或总量)
    const hourly = stats.value.today_hourly || []
    const today = stats.value.today
    
    if (hourly.length > 0) {
      // 如果有分时数据，展示分时柱状图
      const hours = hourly.map(item => item._id)
      const successData = hourly.map(item => item.success)
      const failedData = hourly.map(item => item.failed)
      const totalData = hourly.map(item => item.total)

      option = {
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' }
        },
        legend: {
          data: ['成功', '失败', '总计'],
          bottom: 0
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '10%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: hours,
          axisTick: { alignWithLabel: true }
        },
        yAxis: { type: 'value' },
        series: [
          {
            name: '成功',
            type: 'bar',
            stack: 'status',
            data: successData,
            itemStyle: { color: '#67C23A' }
          },
          {
            name: '失败',
            type: 'bar',
            stack: 'status',
            data: failedData,
            itemStyle: { color: '#F56C6C' }
          },
          {
            name: '总计',
            type: 'line',
            data: totalData,
            itemStyle: { color: '#409EFF' },
            smooth: true
          }
        ]
      }
    } else {
      // 降级为总量柱状图
      option = {
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' }
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '10%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: ['任务总量', '成功处理', '失败记录'],
          axisTick: { alignWithLabel: true }
        },
        yAxis: { type: 'value' },
        series: [
          {
            name: '数量',
            type: 'bar',
            barWidth: '40%',
            data: [
              { value: today.total, itemStyle: { color: '#409EFF' } },
              { value: today.success, itemStyle: { color: '#67C23A' } },
              { value: today.failed, itemStyle: { color: '#F56C6C' } }
            ],
            label: {
              show: true,
              position: 'top'
            }
          }
        ]
      }
    }
  } else {
    // 近一周数据展示为折线图
    const history = stats.value.history || []
    const dates = history.map(item => item._id)
    const successData = history.map(item => item.success)
    const failedData = history.map(item => item.failed)
    const totalData = history.map(item => item.total)

    option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' }
      },
      legend: {
        data: ['成功', '失败', '总计'],
        bottom: 0
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '10%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: dates.length > 0 ? dates : ['无数据'],
        axisTick: { alignWithLabel: true }
      },
      yAxis: { type: 'value' },
      series: [
        {
          name: '成功',
          type: 'line',
          smooth: true,
          data: successData,
          itemStyle: { color: '#67C23A' },
          areaStyle: { opacity: 0.1 }
        },
        {
          name: '失败',
          type: 'line',
          smooth: true,
          data: failedData,
          itemStyle: { color: '#F56C6C' },
          areaStyle: { opacity: 0.1 }
        },
        {
          name: '总计',
          type: 'line',
          smooth: true,
          data: totalData,
          itemStyle: { color: '#409EFF' }
        }
      ]
    }
  }
  
  chart.setOption(option, true)
}

onMounted(() => {
  statsStore.fetchStats().then(() => updateChart())
  window.addEventListener('resize', () => chart?.resize())
})

// 监听时间范围变化
watch(chartTimeRange, () => {
  updateChart()
})

watch(() => statsStore.stats, () => {
  updateChart()
}, { deep: true })

onUnmounted(() => {
  window.removeEventListener('resize', () => chart?.resize())
  chart?.dispose()
})
</script>

<style scoped>
.stats-container {
  padding: 0;
}

.stat-card {
  border-radius: 12px;
  border: none;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.stat-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}

.card-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.icon-box {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.icon-box.primary { background-color: rgba(64, 158, 255, 0.1); color: #409eff; }
.icon-box.success { background-color: rgba(103, 194, 58, 0.1); color: #67c23a; }
.icon-box.danger { background-color: rgba(245, 108, 108, 0.1); color: #f56c6c; }
.icon-box.warning { background-color: rgba(230, 162, 60, 0.1); color: #e6a23c; }

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 4px;
}

.stat-value {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.stat-value .number {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.stat-value .unit {
  font-size: 14px;
  color: #909399;
}

.card-footer {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #f0f2f5;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.trend {
  display: flex;
  align-items: center;
  font-weight: 500;
}

.trend.up { color: #67c23a; }
.trend.down { color: #f56c6c; }
.trend.neutral { color: #909399; }

.tip { color: #c0c4cc; }

.chart-row {
  margin-top: 20px;
}

.chart-card, .queue-card-main {
  border-radius: 12px;
  border: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.full-height-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.full-height-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-around;
  padding: 30px 20px !important;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.queue-summary {
  background: linear-gradient(135deg, #409eff 0%, #3a8ee6 100%);
  border-radius: 8px;
  padding: 20px;
  color: #fff;
  text-align: center;
  margin-bottom: 20px;
}

.total-queue .val {
  font-size: 32px;
  font-weight: bold;
}

.total-queue .lab {
  font-size: 13px;
  opacity: 0.8;
  margin-top: 4px;
}

.queue-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.queue-item .q-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.q-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #606266;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.q-value {
  font-size: 14px;
  font-weight: bold;
  color: #303133;
}
</style>
