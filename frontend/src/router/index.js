import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { guest: true, title: '登录' }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { guest: true, title: '注册' }
  },
  {
    path: '/',
    component: () => import('@/views/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Home',
        component: () => import('@/views/Home.vue'),
        meta: { title: '工作台', group: 'workspace', icon: 'House' }
      },
      {
        path: 'detect',
        name: 'Detect',
        component: () => import('@/views/Detect.vue'),
        meta: { title: '检测中心', group: 'workspace', icon: 'Aim' }
      },
      {
        path: 'history',
        name: 'History',
        component: () => import('@/views/History.vue'),
        meta: { title: '检测历史', group: 'workspace', icon: 'Document' }
      },
      {
        path: 'tracking',
        name: 'Tracking',
        component: () => import('@/views/Tracking.vue'),
        meta: { title: '虫害跟踪', group: 'workspace', icon: 'Location' }
      },
      {
        path: 'knowledge',
        name: 'Knowledge',
        component: () => import('@/views/Knowledge.vue'),
        meta: { title: '知识库', group: 'workspace', icon: 'Reading' }
      },
      {
        path: 'qna',
        name: 'QnA',
        component: () => import('@/views/QnA.vue'),
        meta: { title: '智能问答', group: 'workspace', icon: 'ChatDotSquare' }
      },
      {
        path: 'notifications',
        name: 'Notifications',
        component: () => import('@/views/Notifications.vue'),
        meta: { title: '通知中心', group: 'workspace', icon: 'Bell' }
      },
      {
        path: 'stats',
        name: 'Stats',
        component: () => import('@/views/Stats.vue'),
        meta: { title: '统计分析', group: 'workspace', icon: 'DataLine' }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/Settings.vue'),
        meta: { title: '个人设置', group: 'workspace', icon: 'Setting' }
      },
      {
        path: 'admin',
        component: () => import('@/views/admin/AdminLayout.vue'),
        meta: { requiresAdmin: true, title: '管理后台' },
        children: [
          { path: '', redirect: '/admin/overview' },
          {
            path: 'overview',
            name: 'AdminOverview',
            component: () => import('@/views/admin/Overview.vue'),
            meta: { requiresAdmin: true, title: '管理概览', group: 'admin', icon: 'Odometer' }
          },
          {
            path: 'users',
            name: 'AdminUsers',
            component: () => import('@/views/admin/Users.vue'),
            meta: { requiresAdmin: true, title: '用户管理', group: 'admin', icon: 'UserFilled' }
          },
          {
            path: 'notifications',
            name: 'AdminNotifications',
            component: () => import('@/views/admin/Notifications.vue'),
            meta: { requiresAdmin: true, title: '通知治理', group: 'admin', icon: 'MessageBox' }
          },
          {
            path: 'models',
            name: 'AdminModels',
            component: () => import('@/views/admin/Models.vue'),
            meta: { requiresAdmin: true, title: '模型运维', group: 'admin', icon: 'Cpu' }
          },
          {
            path: 'configs',
            name: 'AdminConfigs',
            component: () => import('@/views/admin/Configs.vue'),
            meta: { requiresAdmin: true, title: '系统配置', group: 'admin', icon: 'Tools' }
          },
          {
            path: 'audit',
            name: 'AdminAudit',
            component: () => import('@/views/admin/PermissionAudit.vue'),
            meta: { requiresAdmin: true, title: '权限审计', group: 'admin', icon: 'Warning' }
          }
        ]
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  let token = localStorage.getItem('access_token')

  if (token && !userStore.user) {
    try {
      await userStore.fetchUser()
    } catch {
      // fetchUser 内部已处理 token 失效
    }
    token = localStorage.getItem('access_token')
  }

  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else if (to.meta.guest && token) {
    next('/')
  } else if (to.meta.requiresAdmin && userStore.user?.role !== 'admin') {
    next('/')
  } else {
    next()
  }
})

export default router
