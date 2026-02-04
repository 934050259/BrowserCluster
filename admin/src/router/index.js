import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Tasks from '../views/Tasks.vue'
import TaskRecords from '../views/TaskRecords.vue'
import Schedules from '../views/Schedules.vue'
import Stats from '../views/Stats.vue'
import Configs from '../views/Configs.vue'
import Rules from '../views/Rules.vue'
import Nodes from '../views/Nodes.vue'
import Login from '../views/Login.vue'
import Users from '../views/Users.vue'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/login', component: Login, meta: { public: true } },
  { path: '/', component: Home },
  { path: '/tasks', component: Tasks },
  { path: '/task-records', component: TaskRecords, name: 'TaskRecords' },
  { path: '/schedules', component: Schedules },
  { path: '/stats', component: Stats },
  { path: '/configs', component: Configs, meta: { adminOnly: true } },
  { path: '/rules', component: Rules, meta: { adminOnly: true } },
  { path: '/nodes', component: Nodes, meta: { adminOnly: true } },
  { path: '/users', component: Users, meta: { adminOnly: true } }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  }
})

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  const isAuthenticated = authStore.isAuthenticated

  // 1. 如果是访问登录页
  if (to.path === '/login') {
    if (isAuthenticated) {
      // 已登录则跳转到首页
      next('/')
    } else {
      // 未登录则允许访问
      next()
    }
    return
  }

  // 2. 如果是访问受保护页面且未登录
  if (!isAuthenticated) {
    next('/login')
    return
  }

  // 3. 已登录状态下，确保有用户信息
  if (!authStore.user) {
    try {
      await authStore.fetchCurrentUser()
    } catch (error) {
      // 获取用户信息失败（可能是 token 失效），fetchCurrentUser 内部会调用 logout
      next('/login')
      return
    }
  }

  // 4. 检查管理员权限
  if (to.meta.adminOnly && authStore.user?.role !== 'admin') {
    next('/')
    return
  }

  next()
})

export default router
