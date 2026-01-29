<template>
  <div class="home-container">
    <!-- Hero Section -->
    <div class="hero-section">
      <div class="hero-content">
        <h1 class="animate-up">Browser Cluster</h1>
        <p class="subtitle animate-up-delay-1">高性能、分布式的 Playwright 浏览器自动化集群</p>
        <div class="hero-actions animate-up-delay-2">
          <el-button type="primary" size="large" @click="$router.push('/tasks')">
            立即开始
            <el-icon class="el-icon--right"><ArrowRight /></el-icon>
          </el-button>
          <el-button size="large" @click="openDocs">
            查看文档
          </el-button>
        </div>
      </div>
      <div class="hero-visual">
        <div class="visual-card glass-effect">
          <div class="visual-header">
            <span class="dot red"></span>
            <span class="dot yellow"></span>
            <span class="dot green"></span>
          </div>
          <div class="visual-body">
            <pre><code>{
  "status": "success",
  "node": "worker-01",
  "title": "Browser Cluster",
  "load_time": "1.2s",
  "cached": true
}</code></pre>
          </div>
        </div>
      </div>
    </div>

    <!-- Features Grid -->
    <div class="section-title">
      <h2>核心特性</h2>
      <p>为现代 Web 采集与自动化而生</p>
    </div>

    <div class="features-grid">
      <div v-for="(feature, index) in features" :key="index" class="feature-card animate-up" :style="{ transitionDelay: `${index * 100}ms` }">
        <div class="feature-icon" :style="{ backgroundColor: feature.bg }">
          <el-icon :size="24" :color="feature.color">
            <component :is="feature.icon" />
          </el-icon>
        </div>
        <h3>{{ feature.title }}</h3>
        <p>{{ feature.desc }}</p>
      </div>
    </div>

    <!-- Architecture Section -->
    <div class="architecture-section">
      <div class="section-title">
        <h2>系统架构</h2>
        <p>稳定、可靠、可扩展的分布式架构</p>
      </div>
      <div class="arch-container">
        <div class="arch-step">
          <div class="step-icon"><Connection /></div>
          <h4>API Gateway</h4>
          <p>FastAPI 高性能接口，支持同步/异步任务提交</p>
        </div>
        <div class="arch-connector"><ArrowRight /></div>
        <div class="arch-step">
          <div class="step-icon"><Operation /></div>
          <h4>RabbitMQ</h4>
          <p>可靠的消息队列，实现任务分发与负载均衡</p>
        </div>
        <div class="arch-connector"><ArrowRight /></div>
        <div class="arch-step">
          <div class="step-icon"><Cpu /></div>
          <h4>Worker Nodes</h4>
          <p>多节点分布式部署，Playwright 集群渲染</p>
        </div>
        <div class="arch-connector"><ArrowRight /></div>
        <div class="arch-step">
          <div class="step-icon"><Files /></div>
          <h4>Storage & Cache</h4>
          <p>MongoDB 持久化任务，Redis 高效缓存结果</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { 
  ArrowRight, 
  Monitor, 
  Connection, 
  Operation, 
  Cpu, 
  Files, 
  Lock, 
  MagicStick, 
  Timer, 
  DataAnalysis 
} from '@element-plus/icons-vue'

const features = [
  {
    title: '分布式集群',
    desc: '支持多节点水平扩展，轻松应对高并发抓取需求。',
    icon: Connection,
    color: '#409EFF',
    bg: '#ecf5ff'
  },
  {
    title: '隐身渲染',
    desc: '内置 Stealth 插件，有效绕过反爬虫检测与人机验证。',
    icon: MagicStick,
    color: '#67C23A',
    bg: '#f0f9eb'
  },
  {
    title: '高效缓存',
    desc: '基于 Redis 的结果缓存机制，大幅降低重复抓取成本。',
    icon: Timer,
    color: '#E6A23C',
    bg: '#fdf6ec'
  },
  {
    title: 'API 拦截',
    desc: '支持在页面渲染过程中拦截并提取特定接口的数据。',
    icon: Lock,
    color: '#F56C6C',
    bg: '#fef0f0'
  },
  {
    title: '多维监控',
    desc: '实时统计成功率、加载时长、节点状态等核心指标。',
    icon: DataAnalysis,
    color: '#909399',
    bg: '#f4f4f5'
  },
  {
    title: '资源优化',
    desc: '按需拦截图片、媒体资源，显著提升渲染速度。',
    icon: Monitor,
    color: '#7232dd',
    bg: '#f2ecff'
  }
]

const openDocs = () => {
  window.open('https://github.com/your-repo/browser-cluster', '_blank')
}
</script>

<style scoped>
.home-container {
  max-width: 1200px;
  margin: 0 auto;
}

/* Hero Section */
.hero-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 30px 0;
  gap: 20px;
}

.hero-content {
  flex: 1;
}

.hero-content h1 {
  font-size: 56px;
  font-weight: 800;
  margin: 0;
  background: linear-gradient(135deg, #409EFF 0%, #7232dd 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-content .subtitle {
  font-size: 20px;
  color: #606266;
  margin: 24px 0 40px;
  line-height: 1.6;
}

.hero-visual {
  flex: 1;
  display: flex;
  justify-content: flex-end;
}

.visual-card {
  width: 100%;
  max-width: 450px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.glass-effect {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(10px);
}

.visual-header {
  background: rgba(0, 0, 0, 0.05);
  padding: 12px;
  display: flex;
  gap: 8px;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.dot.red { background: #ff5f56; }
.dot.yellow { background: #ffbd2e; }
.dot.green { background: #27c93f; }

.visual-body {
  padding: 24px;
  background: #1e1e1e;
  color: #d4d4d4;
  font-family: 'Fira Code', monospace;
}

/* Section Titles */
.section-title {
  text-align: center;
  margin: 80px 0 40px;
}

.section-title h2 {
  font-size: 32px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 12px;
}

.section-title p {
  font-size: 16px;
  color: #909399;
}

/* Features Grid */
.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 24px;
}

.feature-card {
  padding: 32px;
  background: white;
  border-radius: 16px;
  border: 1px solid #ebeef5;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
}

.feature-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.05);
  border-color: #409EFF;
}

.feature-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
}

.feature-card h3 {
  font-size: 20px;
  margin-bottom: 12px;
  color: #303133;
}

.feature-card p {
  color: #606266;
  line-height: 1.6;
  margin: 0;
}

/* Architecture Section */
.architecture-section {
  margin-top: 100px;
  padding: 60px 40px;
  background: white;
  border-radius: 24px;
  border: 1px solid #ebeef5;
}

.arch-container {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-top: 40px;
}

.arch-step {
  flex: 1;
  text-align: center;
  padding: 0 20px;
}

.step-icon {
  width: 64px;
  height: 64px;
  background: #f0f7ff;
  color: #409EFF;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
  font-size: 28px;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}

.arch-step h4 {
  margin-bottom: 12px;
  color: #303133;
}

.arch-step p {
  font-size: 14px;
  color: #606266;
  line-height: 1.4;
}

.arch-connector {
  padding-top: 24px;
  color: #dcdfe6;
  font-size: 24px;
}

/* Animations */
.animate-up {
  animation: slideUp 0.8s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

.animate-up-delay-1 {
  animation: slideUp 0.8s cubic-bezier(0.4, 0, 0.2, 1) 0.2s forwards;
  opacity: 0;
}

.animate-up-delay-2 {
  animation: slideUp 0.8s cubic-bezier(0.4, 0, 0.2, 1) 0.4s forwards;
  opacity: 0;
}

@keyframes slideUp {
  from {
    transform: translateY(30px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

/* Responsive */
@media (max-width: 1024px) {
  .hero-section {
    flex-direction: column;
    text-align: center;
  }
  .hero-visual {
    justify-content: center;
    width: 100%;
  }
  .arch-container {
    flex-direction: column;
    gap: 40px;
  }
  .arch-connector {
    transform: rotate(90deg);
    padding: 0;
    margin: -20px auto;
  }
}
</style>
