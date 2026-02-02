<template>
  <div class="app-wrapper">
    <template v-if="isLoginPage">
      <router-view />
    </template>
    <el-container v-else class="main-container">
      <!-- Sidebar -->
      <el-aside :width="isCollapse ? '64px' : '240px'" class="sidebar">
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
        
        <el-menu
          :default-active="activeMenu"
          class="el-menu-vertical"
          :collapse="isCollapse"
          @select="handleMenuSelect"
          background-color="#304156"
          text-color="#bfcbd9"
          active-text-color="#409EFF"
        >
          <el-menu-item index="">
            <el-icon><House /></el-icon>
            <template #title>首页</template>
          </el-menu-item>
          <el-menu-item index="tasks">
            <el-icon><List /></el-icon>
            <template #title>任务管理</template>
          </el-menu-item>
          <el-menu-item index="rules" v-if="isAdmin">
            <el-icon><Connection /></el-icon>
            <template #title>网站配置</template>
          </el-menu-item>
          <el-menu-item index="stats">
            <el-icon><DataLine /></el-icon>
            <template #title>数据统计</template>
          </el-menu-item>
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
  Expand, Fold, CircleCheck, CircleClose 
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
    '/stats': '数据统计',
    '/nodes': '节点管理',
    '/configs': '系统设置',
    '/users': '用户管理'
  }
  return names[path] || '未知'
})

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
  height: 100%;
  transition: width 0.3s;
  overflow: hidden;
  box-shadow: 2px 0 6px rgba(0, 21, 41, 0.35);
  z-index: 1001;
}

.logo-container {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  background-color: #2b2f3a;
  color: white;
  padding: 0 16px;
  overflow: hidden;
  gap: 12px;
}

.logo-wrapper {
  position: relative;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.logo-svg {
  width: 28px;
  height: 28px;
  color: #409EFF;
  z-index: 2;
  filter: drop-shadow(0 0 8px rgba(64, 158, 255, 0.4));
  animation: logo-float 3s ease-in-out infinite;
}

.logo-glow {
  position: absolute;
  width: 20px;
  height: 20px;
  background: #409EFF;
  filter: blur(15px);
  opacity: 0.5;
  z-index: 1;
}

@keyframes logo-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  white-space: nowrap;
  background: linear-gradient(135deg, #fff 0%, #409EFF 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: 0.5px;
}

.el-menu-vertical {
  border: none !important;
}

.el-menu-vertical:not(.el-menu--collapse) {
  width: 240px;
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
