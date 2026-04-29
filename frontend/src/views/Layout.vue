<template>
  <div class="layout">
    <aside class="sidebar" :class="{ collapsed }">
      <div class="logo">
        <span class="logo-icon">🌾</span>
        <span class="logo-text" v-show="!collapsed">病虫害检测</span>
      </div>
      
      <nav class="nav">
        <router-link to="/" class="nav-item" exact-active-class="active">
          <span class="icon">🏠</span>
          <span class="text" v-show="!collapsed">首页</span>
        </router-link>
        <router-link to="/detect" class="nav-item" active-class="active">
          <span class="icon">🔍</span>
          <span class="text" v-show="!collapsed">检测中心</span>
        </router-link>
        <router-link to="/history" class="nav-item" active-class="active">
          <span class="icon">📋</span>
          <span class="text" v-show="!collapsed">检测历史</span>
        </router-link>
        <router-link to="/tracking" class="nav-item" active-class="active">
          <span class="icon">📍</span>
          <span class="text" v-show="!collapsed">虫害跟踪</span>
        </router-link>
        <router-link to="/knowledge" class="nav-item" active-class="active">
          <span class="icon">📚</span>
          <span class="text" v-show="!collapsed">知识库</span>
        </router-link>
        <router-link to="/qna" class="nav-item" active-class="active">
          <span class="icon">💬</span>
          <span class="text" v-show="!collapsed">智能问答</span>
        </router-link>
        <router-link to="/stats" class="nav-item" active-class="active">
          <span class="icon">📈</span>
          <span class="text" v-show="!collapsed">数据统计</span>
        </router-link>
        <div class="nav-divider"></div>
        <router-link to="/settings" class="nav-item" active-class="active">
          <span class="icon">⚙️</span>
          <span class="text" v-show="!collapsed">设置</span>
        </router-link>
        <router-link v-if="userStore.isAdmin" to="/admin" class="nav-item" active-class="active">
          <span class="icon">📊</span>
          <span class="text" v-show="!collapsed">管理后台</span>
        </router-link>
      </nav>
      
      <div class="sidebar-footer">
        <button class="btn-ghost" @click="collapsed = !collapsed">{{ collapsed ? '→' : '←' }}</button>
        <button class="btn-ghost" @click="handleLogout">🚪</button>
      </div>
    </aside>
    
    <div class="main">
      <header class="header">
        <h1 class="page-title">{{ pageTitle }}</h1>
        <div class="header-right">
          <router-link to="/notifications" class="icon-btn">
            🔔<span v-if="unreadCount" class="badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
          </router-link>
          <span class="username">{{ userStore.user?.username }}</span>
        </div>
      </header>
      
      <main class="content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { notificationApi } from '@/api'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const collapsed = ref(false)
const unreadCount = ref(0)

const titles = { Home: '首页概览', Detect: '检测中心', History: '检测历史', Tracking: '虫害跟踪', Knowledge: '病害知识库', QnA: '智能问答', Stats: '数据统计', Notifications: '消息通知', Settings: '个人设置', Admin: '管理后台' }
const pageTitle = computed(() => titles[route.name] || '病虫害检测系统')

async function fetchUnread() {
  try {
    const res = await notificationApi.list({ is_read: false, page_size: 100 })
    unreadCount.value = res.unread_count || 0
  } catch {}
}

function handleLogout() {
  userStore.logout()
  router.push('/login')
}

onMounted(() => {
  if (!userStore.user) userStore.fetchUser()
  fetchUnread()
})
</script>

<style lang="scss" scoped>
.layout { display: flex; min-height: 100vh; }
.sidebar {
  width: 220px; background: var(--bg-primary); border-right: 1px solid var(--border-light);
  display: flex; flex-direction: column; transition: width 0.3s;
  &.collapsed { width: 64px; }
  @media (max-width: 768px) {
    position: fixed; left: -220px; z-index: 1000; height: 100vh;
    &.open { left: 0; }
  }
}
.logo { display: flex; align-items: center; gap: 12px; padding: 20px; border-bottom: 1px solid var(--border-light); }
.logo-icon { font-size: 28px; }
.logo-text { font-size: 16px; font-weight: 600; }
.nav { flex: 1; padding: 16px 12px; }
.nav-item {
  display: flex; align-items: center; gap: 12px; padding: 12px; border-radius: var(--radius-md);
  color: var(--text-secondary); text-decoration: none; margin-bottom: 4px;
  &:hover { background: var(--bg-secondary); color: var(--text-primary); }
  &.active { background: var(--primary); color: white; }
  @media (max-width: 768px) {
    padding: 10px;
  }
}
.icon { font-size: 18px; }
.nav-divider { height: 1px; background: var(--border-light); margin: 16px 0; }
.sidebar-footer { padding: 16px; display: flex; gap: 8px; border-top: 1px solid var(--border-light); }
.btn-ghost { flex: 1; padding: 10px; border: none; background: transparent; border-radius: var(--radius-md); cursor: pointer; &:hover { background: var(--bg-secondary); } }
.main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.header { display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; background: var(--bg-primary); border-bottom: 1px solid var(--border-light); }
.page-title { font-size: 18px; font-weight: 600; }
.header-right { display: flex; align-items: center; gap: 16px; }
.icon-btn { position: relative; display: flex; align-items: center; justify-content: center; width: 40px; height: 40px; border-radius: var(--radius-md); background: var(--bg-secondary); font-size: 18px; }
.badge { position: absolute; top: 2px; right: 2px; min-width: 18px; height: 18px; padding: 0 5px; background: var(--error); color: white; font-size: 11px; border-radius: 9px; display: flex; align-items: center; justify-content: center; }
.username { font-size: 14px; color: var(--text-primary); font-weight: 500; }
.content { flex: 1; padding: 24px; overflow-y: auto; }

@media (max-width: 768px) {
  .content { padding: 16px; }
  .page-title { font-size: 16px; }
  .header { padding: 12px 16px; }
}
</style>
