import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { guest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { guest: true }
  },
  {
    path: '/',
    component: () => import('@/views/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'Home', component: () => import('@/views/Home.vue') },
      { path: 'detect', name: 'Detect', component: () => import('@/views/Detect.vue') },
      { path: 'history', name: 'History', component: () => import('@/views/History.vue') },
      { path: 'tracking', name: 'Tracking', component: () => import('@/views/Tracking.vue') },
      { path: 'knowledge', name: 'Knowledge', component: () => import('@/views/Knowledge.vue') },
      { path: 'qna', name: 'QnA', component: () => import('@/views/QnA.vue') },
      { path: 'notifications', name: 'Notifications', component: () => import('@/views/Notifications.vue') },
      { path: 'stats', name: 'Stats', component: () => import('@/views/Stats.vue') },
      { path: 'settings', name: 'Settings', component: () => import('@/views/Settings.vue') },
      {
        path: 'admin',
        component: () => import('@/views/admin/AdminLayout.vue'),
        meta: { requiresAdmin: true },
        children: [
          { path: '', redirect: '/admin/overview' },
          { path: 'overview', name: 'AdminOverview', component: () => import('@/views/admin/Overview.vue'), meta: { requiresAdmin: true } },
          { path: 'users', name: 'AdminUsers', component: () => import('@/views/admin/Users.vue'), meta: { requiresAdmin: true } },
          { path: 'notifications', name: 'AdminNotifications', component: () => import('@/views/admin/Notifications.vue'), meta: { requiresAdmin: true } },
          { path: 'models', name: 'AdminModels', component: () => import('@/views/admin/Models.vue'), meta: { requiresAdmin: true } }
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
      // fetchUser 内部会处理失效 token
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
