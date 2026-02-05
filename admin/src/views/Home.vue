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
          <div class="step-card">
            <div class="step-icon"><Connection /></div>
            <h4>API Gateway</h4>
            <p>鉴权、流控与请求预检，集成缓存优先策略。</p>
          </div>
        </div>
        <div class="arch-connector">
          <div class="connector-icon"><ArrowRight /></div>
        </div>
        <div class="arch-step">
          <div class="step-card">
            <div class="step-icon"><Operation /></div>
            <h4>Task Queue</h4>
            <p>RabbitMQ 异步分发，支持优先级调度与消息持久化。</p>
          </div>
        </div>
        <div class="arch-connector">
          <div class="connector-icon"><ArrowRight /></div>
        </div>
        <div class="arch-step">
          <div class="step-card">
            <div class="step-icon"><Cpu /></div>
            <h4>Smart Worker</h4>
            <p>Playwright 渲染引擎，内置 GNE/XPath/LLM 多模态解析。</p>
          </div>
        </div>
        <div class="arch-connector">
          <div class="connector-icon"><ArrowRight /></div>
        </div>
        <div class="arch-step">
          <div class="step-card">
            <div class="step-icon"><Files /></div>
            <h4>Persistence</h4>
            <p>MongoDB 结果存储与 Redis 热点数据缓存。</p>
          </div>
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
    desc: '支持多节点水平扩展，基于容器化部署，轻松应对大规模并发抓取需求。',
    icon: Connection,
    color: '#409EFF',
    bg: '#ecf5ff'
  },
  {
    title: '多模式解析',
    desc: '集成 GNE、XPath 与 LLM 大模型，支持从规则配置到语义化的结构化数据提取。',
    icon: MagicStick,
    color: '#67C23A',
    bg: '#f0f9eb'
  },
  {
    title: '云端确权存储',
    desc: '支持 HTML 源码与截图自动同步至OSS，解决海量数据存储与私有访问需求。',
    icon: Files,
    color: '#F56C6C',
    bg: '#fef0f0'
  },
  {
    title: '双引擎驱动',
    desc: '支持 Playwright 与 DrissionPage 双引擎，兼顾交互灵活性与极致的反爬避障能力。',
    icon: Cpu,
    color: '#7232dd',
    bg: '#f2ecff'
  },
  {
    title: '自动化调度',
    desc: '内置 Cron 调度引擎，支持定时周期性任务，实现全自动数据监控与采集流水线。',
    icon: Timer,
    color: '#E6A23C',
    bg: '#fdf6ec'
  },
  {
    title: 'API 实时拦截',
    desc: '支持在页面渲染过程中深度拦截并提取特定 XHR/Fetch 接口的原始响应数据。',
    icon: Connection,
    color: '#409EFF',
    bg: '#ecf5ff'
  }
]

const openDocs = () => {
  window.open('https://github.com/934050259/BrowserCluster', '_blank')
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
  margin: 20px 0 20px;
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
  padding: 20px 0;
  background: linear-gradient(180deg, #f8fafc 0%, #fff 100%);
  position: relative;
  overflow: hidden;
}

.arch-container {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 60px;
  position: relative;
  max-width: 1000px;
  margin-left: auto;
  margin-right: auto;
}

.arch-step {
  position: relative;
  z-index: 2;
  width: 220px;
}

.step-card {
  background: white;
  padding: 30px 20px;
  border-radius: 20px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  text-align: center;
}

.step-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  border-color: #bfdbfe;
}

.step-icon {
  width: 60px;
  height: 60px;
  background: #eff6ff;
  color: #3b82f6;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
  font-size: 28px;
  transition: all 0.3s ease;
}

.step-card:hover .step-icon {
  background: #3b82f6;
  color: white;
  transform: scale(1.1) rotate(5deg);
}

.arch-step h4 {
  margin: 0 0 8px;
  color: #1e293b;
  font-size: 18px;
  font-weight: 600;
}

.arch-step p {
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
  margin: 0;
}

.arch-connector {
  flex: 1;
  height: 2px;
  background: #e2e8f0;
  margin: 0 10px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.arch-connector::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  width: 100%;
  height: 2px;
  background: linear-gradient(90deg, transparent, #3b82f6, transparent);
  transform: translateY(-50%);
  background-size: 200% 100%;
  animation: flowLine 2s linear infinite;
  opacity: 0.5;
}

.connector-icon {
  width: 24px;
  height: 24px;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  font-size: 12px;
  z-index: 1;
  position: relative;
}

@keyframes flowLine {
  0% { background-position: 100% 0; }
  100% { background-position: -100% 0; }
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
  
  .arch-step {
    width: 100%;
    max-width: 320px;
  }
  
  .arch-connector {
    width: 2px;
    height: 60px;
    margin: 0;
  }
  
  .arch-connector::after {
    width: 2px;
    height: 100%;
    background: linear-gradient(180deg, transparent, #3b82f6, transparent);
    background-size: 100% 200%;
    animation: flowLineVertical 2s linear infinite;
  }
  
  @keyframes flowLineVertical {
    0% { background-position: 0 100%; }
    100% { background-position: 0 -100%; }
  }
  
  .connector-icon {
    transform: rotate(90deg);
  }
  .arch-connector {
    transform: none; /* Reset old rotation */
    padding: 0;
  }
}
</style>
