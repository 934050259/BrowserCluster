import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Tasks from '../views/Tasks.vue'
import TaskRecords from '../views/TaskRecords.vue'
import Schedules from '../views/Schedules.vue'
import Stats from '../views/Stats.vue'
import Configs from '../views/Configs.vue'
import Rules from '../views/Rules.vue'
import Scrapers from '../views/Scrapers.vue'
import Proxies from '../views/Proxies.vue'
import Cookies from '../views/Cookies.vue'
import Nodes from '../views/Nodes.vue'
import Login from '../views/Login.vue'
import Users from '../views/Users.vue'
import Workflows from '../views/Workflows.vue'
import WorkflowEditor from '../views/WorkflowEditor.vue'
import WorkflowResults from '../views/WorkflowResults.vue'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/login', component: Login, meta: { public: true, title: '登录' } },
  { path: '/', component: Home, meta: { title: '首页概览' } },
  { path: '/tasks', component: Tasks, meta: { title: '任务管理' } },
  { path: '/task-records', component: TaskRecords, name: 'TaskRecords', meta: { title: '采集记录' } },
  { path: '/schedules', component: Schedules, meta: { title: '定时任务' } },
  { path: '/stats', component: Stats, meta: { title: '数据统计' } },
  { path: '/configs', component: Configs, meta: { adminOnly: true, title: '系统设置' } },
  { path: '/rules', component: Rules, meta: { adminOnly: true, title: '网站配置' } },
  { path: '/scrapers', component: Scrapers, meta: { adminOnly: true, title: '站点采集' } },
  { path: '/proxies', component: Proxies, meta: { adminOnly: true, title: '代理管理' } },
  { path: '/cookies', component: Cookies, meta: { adminOnly: true, title: 'Cookie 池' } },
  { path: '/nodes', component: Nodes, meta: { adminOnly: true, title: '节点管理' } },
  { path: '/users', component: Users, meta: { adminOnly: true, title: '用户管理' } },
  { path: '/workflows', component: Workflows, meta: { adminOnly: true, title: '流程编排' } },
  { path: '/workflows/edit/:id?', name: 'WorkflowEditor', component: WorkflowEditor, meta: { adminOnly: true, title: '流程编辑' } },
  { path: '/workflows/results/:id', name: 'WorkflowResults', component: WorkflowResults, meta: { adminOnly: true, title: '执行数据' } }
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
