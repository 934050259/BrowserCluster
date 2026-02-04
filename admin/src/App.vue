<template>
  <div class="app-wrapper">
    <template v-if="isLoginPage">
      <router-view />
    </template>
    <el-container v-else class="main-container">
      <!-- Sidebar -->
      <el-aside :width="isCollapse ? '64px' : '240px'" class="sidebar">
        <div class="sidebar-inner">
          <div class="logo-container">
            <div class="logo-wrapper">
              <svg class="logo-svg" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <div class="logo-glow"></div>
            </div>
            <span class="logo-text" v-if="!isCollapse">BrowserCluster</span>
          </div>
          
          <div class="menu-wrapper">
            <el-menu
              :default-active="activeMenu"
              class="el-menu-vertical"
              :collapse="isCollapse"
              @select="handleMenuSelect"
              background-color="transparent"
              text-color="#bfcbd9"
              active-text-color="#409EFF"
            >
              <el-menu-item index="">
                <el-icon><House /></el-icon>
                <template #title>首页概览</template>
              </el-menu-item>
              
              <div class="menu-group-title" v-if="!isCollapse">任务调度</div>
              <el-menu-item index="tasks">
                <el-icon><List /></el-icon>
                <template #title>任务管理</template>
              </el-menu-item>
              <el-menu-item index="schedules">
                <el-icon><Timer /></el-icon>
                <template #title>定时任务</template>
              </el-menu-item>
              <el-menu-item index="rules" v-if="isAdmin">
                <el-icon><Connection /></el-icon>
                <template #title>网站配置</template>
              </el-menu-item>

              <div class="menu-group-title" v-if="!isCollapse">分析与统计</div>
              <el-menu-item index="stats">
                <el-icon><DataLine /></el-icon>
                <template #title>数据统计</template>
              </el-menu-item>

              <div class="menu-group-title" v-if="!isCollapse">系统管理</div>
              <el-menu-item index="nodes" v-if="isAdmin">
                <el-icon><Monitor /></el-icon>
                <template #title>节点管理</template>
              </el-menu-item>
              <el-menu-item index="users" v-if="isAdmin">
                <el-icon><User /></el-icon>
                <template #title>用户管理</template>
              </el-menu-item>
              <el-menu-item index="configs" v-if="isAdmin">
                <el-icon><Setting /></el-icon>
                <template #title>系统设置</template>
              </el-menu-item>
            </el-menu>
          </div>

          <div class="sidebar-footer" v-if="!isCollapse">
            <div class="footer-card">
              <div class="footer-stats">
                <div class="stat-mini">
                  <span class="dot" :class="stats.nodes?.active > 0 ? 'success' : 'warning'"></span>
                  <span class="label">在线节点</span>
                  <span class="val">{{ stats.nodes?.active || 0 }}/{{ stats.nodes?.total || 0 }}</span>
                </div>
                <div class="stat-mini">
                  <span class="dot" :class="getLoadStatusClass(stats.system_load)"></span>
                  <span class="label">系统负载</span>
                  <span class="val">{{ stats.system_load || 0 }}%</span>
                </div>
              </div>
              <div class="version-info">v1.2.0 Stable</div>
            </div>
          </div>
        </div>
      </el-aside>

      <el-container class="content-container">
        <!-- Header -->
        <el-header class="header">
          <div class="header-left">
            <el-icon class="collapse-btn" @click="isCollapse = !isCollapse">
              <Expand v-if="isCollapse" />
              <Fold v-else />
            </el-icon>
            <el-breadcrumb separator="/">
              <el-breadcrumb-item>首页</el-breadcrumb-item>
              <el-breadcrumb-item>{{ currentRouteName }}</el-breadcrumb-item>
            </el-breadcrumb>
          </div>
          
          <div class="header-right">
            <div class="header-actions">
              <el-tooltip content="刷新统计" placement="bottom">
                <el-icon class="action-btn" @click="refreshStats"><Refresh /></el-icon>
              </el-tooltip>
              <el-tooltip content="全屏" placement="bottom">
                <el-icon class="action-btn" @click="toggleFullscreen"><FullScreen /></el-icon>
              </el-tooltip>
              <el-tooltip content="帮助文档" placement="bottom">
                <el-icon class="action-btn" @click="openDocs"><QuestionFilled /></el-icon>
              </el-tooltip>
            </div>
            
            <el-divider direction="vertical" />
            
            <div class="stats-overview">
              <el-tooltip content="今日任务统计" placement="bottom">
                <div class="stats-card-mini">
                  <div class="stat-item success">
                    <el-icon><CircleCheck /></el-icon>
                    <span class="label">Success</span>
                    <span class="value">{{ stats.today.success }}</span>
                  </div>
                  <div class="stat-divider"></div>
                  <div class="stat-item danger">
                    <el-icon><CircleClose /></el-icon>
                    <span class="label">Failed</span>
                    <span class="value">{{ stats.today.failed }}</span>
                  </div>
                  <div class="stat-progress-wrapper">
                    <el-progress 
                      type="circle" 
                      :percentage="calculateSuccessRate(stats.today.success, stats.today.total)" 
                      :width="32" 
                      :stroke-width="4"
                      :color="getStatusColor(stats.today.success, stats.today.total)"
                    >
                      <template #default="{ percentage }">
                        <span class="rate-text">{{ Math.round(percentage) }}%</span>
                      </template>
                    </el-progress>
                  </div>
                </div>
              </el-tooltip>
            </div>
            <el-divider direction="vertical" />
            <el-dropdown @command="handleCommand">
              <span class="user-info">
                <el-avatar :size="32" src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png" />
                <span class="username">{{ currentUser.username }}</span>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="logout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-header>

        <!-- Main Content -->
        <el-main class="main-content">
          <router-view v-slot="{ Component }">
            <transition name="fade-transform" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { 
  House, List, DataLine, Monitor, Setting, User,
  Expand, Fold, CircleCheck, CircleClose, Refresh,
  QuestionFilled, FullScreen
} from '@element-plus/icons-vue'
import { useStatsStore } from './stores/stats'
import { useAuthStore } from './stores/auth'

const router = useRouter()
const route = useRoute()
const statsStore = useStatsStore()
const authStore = useAuthStore()

const isCollapse = ref(false)
const stats = computed(() => statsStore.stats)
const currentUser = computed(() => authStore.user || {})
const isAdmin = computed(() => authStore.isAdmin)
const isLoginPage = computed(() => route.path === '/login')

const activeMenu = computed(() => {
  const path = route.path
  if (path === '/') return ''
  return path.substring(1)
})

const currentRouteName = computed(() => {
  const path = route.path
  if (path === '/') return '概览'
  const names = {
    '/tasks': '任务管理',
    '/task-records': '采集记录',
    '/rules': '网站配置',
    '/schedules': '定时任务',
    '/stats': '数据统计',
    '/nodes': '节点管理',
    '/configs': '系统设置',
    '/users': '用户管理'
  }
  return names[path] || '未知'
})

const refreshStats = () => {
  statsStore.fetchStats()
}

const toggleFullscreen = () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
  } else {
    if (document.exitFullscreen) {
      document.exitFullscreen()
    }
  }
}

const openDocs = () => {
  window.open('https://github.com/934050259/BrowserCluster', '_blank')
}

const handleMenuSelect = (index) => {
  router.push('/' + index)
}

const getStatusType = (success, total) => {
  const ratio = total > 0 ? success / total : 0
  if (ratio >= 0.9) return 'success'
  if (ratio >= 0.7) return 'warning'
  return 'danger'
}

const getStatusColor = (success, total) => {
  const ratio = total > 0 ? success / total : 0
  if (ratio >= 0.9) return '#67C23A'
  if (ratio >= 0.7) return '#E6A23C'
  return '#F56C6C'
}

const calculateSuccessRate = (success, total) => {
  if (!total) return 0
  return (success / total) * 100
}

const getLoadStatusClass = (load) => {
  if (load > 80) return 'danger'
  if (load > 50) return 'warning'
  return 'success'
}

const handleCommand = (command) => {
  if (command === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}

onMounted(() => {
  if (!isLoginPage.value) {
    statsStore.fetchStats()
    // 取消自动刷新：删除了每 30 秒更新统计数据的定时器
  }
})
</script>

<style>
body {
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  background-color: #f0f2f5;
}

.app-wrapper {
  height: 100vh;
  width: 100%;
}

.main-container {
  height: 100%;
}

/* Sidebar Styles */
.sidebar {
  background-color: #304156;
  color: #fff;
  transition: width 0.3s;
  overflow: hidden;
  box-shadow: 2px 0 6px rgba(0, 21, 41, 0.35);
  z-index: 1001;
}

.sidebar-inner {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.menu-wrapper {
  flex: 1;
  overflow-y: auto;
  scrollbar-width: none; /* Firefox */
}

.menu-wrapper::-webkit-scrollbar {
  display: none; /* Chrome/Safari */
}

.logo-container {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  background: #2b3b4d;
  overflow: hidden;
  white-space: nowrap;
}

.logo-wrapper {
  position: relative;
  width: 32px;
  height: 32px;
  margin-right: 12px;
  flex-shrink: 0;
}

.logo-svg {
  width: 100%;
  height: 100%;
  color: #409EFF;
}

.logo-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 20px;
  height: 20px;
  background: rgba(64, 158, 255, 0.4);
  filter: blur(10px);
  border-radius: 50%;
  z-index: -1;
}

.logo-text {
  font-size: 18px;
  font-weight: bold;
  background: linear-gradient(120deg, #fff, #409EFF);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.menu-group-title {
  padding: 16px 12px 8px;
  font-size: 12px;
  color: #e2ebf0;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  font-weight: 300;
  opacity: 0.8;
}

.el-menu-vertical {
  border-right: none;
}

.el-menu-item {
  height: 50px;
  line-height: 50px;
}

.el-menu-item:hover {
  background-color: #263445 !important;
}

.el-menu-item.is-active {
  background-color: #1f2d3d !important;
}

.sidebar-footer {
  padding: 16px;
  background: #2b3b4d;
}

.footer-card {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 12px;
}

.footer-stats {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 8px;
}

.stat-mini {
  display: flex;
  align-items: center;
  font-size: 12px;
  color: #bfcbd9;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-right: 8px;
}

.dot.success { background: #67C23A; box-shadow: 0 0 5px #67C23A; }
.dot.warning { background: #E6A23C; box-shadow: 0 0 5px #E6A23C; }
.dot.danger { background: #F56C6C; box-shadow: 0 0 5px #F56C6C; }

.label { flex: 1; }
.val { color: #fff; font-family: monospace; }

.version-info {
  font-size: 10px;
  color: #c6cdd6;
  text-align: center;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding-top: 8px;
}

/* Header Styles */
.header {
  background-color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  z-index: 1000;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  transition: color 0.3s;
}

.collapse-btn:hover {
  color: #409EFF;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 15px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.action-btn {
  font-size: 18px;
  color: #606266;
  cursor: pointer;
  padding: 8px;
  border-radius: 4px;
  transition: all 0.3s;
}

.action-btn:hover {
  background-color: #f5f7fa;
  color: #409EFF;
}

.stats-overview {
  display: flex;
  align-items: center;
}

.stats-card-mini {
  display: flex;
  align-items: center;
  background: #f8f9fb;
  border: 1px solid #ebeef5;
  border-radius: 20px;
  padding: 4px 12px;
  gap: 12px;
  transition: all 0.3s;
}

.stats-card-mini:hover {
  background: #fff;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
  border-color: #409eff;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.stat-item .el-icon {
  font-size: 14px;
}

.stat-item.success { color: #67c23a; }
.stat-item.danger { color: #f56c6c; }

.stat-item .label {
  color: #909399;
  font-size: 12px;
}

.stat-item .value {
  font-weight: 600;
  font-family: 'Inter', sans-serif;
}

.stat-divider {
  width: 1px;
  height: 14px;
  background: #dcdfe6;
}

.stat-progress-wrapper {
  display: flex;
  align-items: center;
  margin-left: 4px;
}

.rate-text {
  font-size: 10px;
  font-weight: 700;
  padding-right: 15px;
  display: inline-block;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 0 8px;
  height: 40px;
  transition: background 0.3s;
  border-radius: 4px;
}

.user-info:hover {
  background-color: rgba(0, 0, 0, 0.025);
}

.username {
  font-size: 14px;
  color: #606266;
}

/* Main Content Styles */
.content-container {
  background-color: #f0f2f5;
}

.main-content {
  padding: 20px;
}

/* Transitions */
.fade-transform-enter-active,
.fade-transform-leave-active {
  transition: all 0.5s;
}

.fade-transform-enter-from {
  opacity: 0;
  transform: translateX(-30px);
}

.fade-transform-leave-to {
  opacity: 0;
  transform: translateX(30px);
}
</style>
