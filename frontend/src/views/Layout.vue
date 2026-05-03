<template>
  <AppShell :collapsed="collapsed" :mobile="isMobile" :mobile-open="mobileMenuOpen">
    <template #sidebar>
      <div class="sidebar">
        <div class="logo-row">
          <div class="logo-mark" aria-hidden="true">
            <span class="stem"></span>
            <span class="leaf leaf-a"></span>
            <span class="leaf leaf-b"></span>
          </div>
          <div v-if="!collapsed || isMobile" class="logo-text">
            <strong>Corn Detect</strong>
            <span>智能病虫害工作台</span>
          </div>
        </div>

        <nav class="nav-groups">
          <section v-for="group in groupedMenus" :key="group.key" class="group">
            <div v-if="!collapsed || isMobile" class="group-title">{{ group.label }}</div>
            <router-link
              v-for="item in group.items"
              :key="item.name"
              :to="item.path"
              :class="['nav-item', { active: isMenuActive(item) }]"
              @click="handleNavClick"
            >
              <component :is="item.icon" class="item-icon" />
              <span v-if="!collapsed || isMobile">{{ item.title }}</span>
            </router-link>
          </section>
        </nav>

        <div class="sidebar-footer">
          <el-button text @click="toggleCollapse">
            <el-icon><component :is="collapsed ? Expand : Fold" /></el-icon>
            <span v-if="!collapsed || isMobile">折叠导航</span>
          </el-button>
          <el-button text type="danger" @click="handleLogout">
            <el-icon><SwitchButton /></el-icon>
            <span v-if="!collapsed || isMobile">退出登录</span>
          </el-button>
        </div>
      </div>
    </template>

    <template #topbar>
      <div class="topbar">
        <div class="left">
          <el-button v-if="isMobile" text @click="mobileMenuOpen = !mobileMenuOpen">
            <el-icon><Menu /></el-icon>
          </el-button>
          <div class="route-meta">
            <h1>{{ pageTitle }}</h1>
            <el-breadcrumb separator="/" class="breadcrumb">
              <el-breadcrumb-item v-for="item in breadcrumbs" :key="item.path || item.title">
                <span>{{ item.title }}</span>
              </el-breadcrumb-item>
            </el-breadcrumb>
          </div>
        </div>

        <div class="right">
          <el-button text @click="toggleTheme">
            <el-icon><component :is="theme === 'light' ? Moon : Sunny" /></el-icon>
          </el-button>
          <router-link to="/notifications" class="notify-btn" @click="mobileMenuOpen = false">
            <el-icon><Bell /></el-icon>
            <span v-if="unreadCount > 0" class="badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
          </router-link>
          <el-dropdown @command="handleUserCommand">
            <span class="user-trigger">
              {{ userStore.user?.username || '用户' }}
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="settings">个人设置</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </template>

    <router-view />
  </AppShell>

  <div v-if="isMobile && mobileMenuOpen" class="mobile-mask" @click="mobileMenuOpen = false" />
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { notificationApi } from '@/api'
import AppShell from '@/components/ui/AppShell.vue'
import {
  Aim,
  ArrowDown,
  Bell,
  ChatDotSquare,
  Cpu,
  DataLine,
  Document,
  Expand,
  Fold,
  House,
  Location,
  Menu,
  MessageBox,
  Moon,
  Odometer,
  Reading,
  Setting,
  Sunny,
  SwitchButton,
  Tools,
  UserFilled,
  Warning
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const collapsed = ref(false)
const unreadCount = ref(0)
const theme = ref(localStorage.getItem('ui_theme') || 'light')
const isMobile = ref(window.innerWidth < 768)
const mobileMenuOpen = ref(false)

const iconMap = {
  House,
  Aim,
  Document,
  Location,
  Reading,
  ChatDotSquare,
  Bell,
  DataLine,
  Setting,
  Odometer,
  UserFilled,
  MessageBox,
  Cpu,
  Tools,
  Warning
}

const groupLabels = {
  workspace: '业务功能',
  admin: '管理工作区'
}

const groupOrder = ['workspace', 'admin']

const menuItems = computed(() => {
  const routes = router.getRoutes()
    .filter((item) => item.name && item.meta?.group)
    .map((item) => ({
      name: item.name,
      path: item.path,
      title: item.meta.title || item.name,
      group: item.meta.group,
      requiresAdmin: !!item.meta.requiresAdmin,
      icon: iconMap[item.meta.icon] || Document
    }))

  return routes.filter((item) => (item.requiresAdmin ? userStore.isAdmin : true))
})

const groupedMenus = computed(() => groupOrder
  .map((groupKey) => ({
    key: groupKey,
    label: groupLabels[groupKey] || groupKey,
    items: menuItems.value.filter((item) => item.group === groupKey)
  }))
  .filter((group) => group.items.length > 0))

const pageTitle = computed(() => route.meta?.title || '病虫害检测系统')

const breadcrumbs = computed(() => route.matched
  .filter((item) => item.meta?.title && item.path !== '/')
  .map((item) => ({
    title: item.meta.title,
    path: item.path
  })))

function applyTheme(value) {
  document.documentElement.setAttribute('data-theme', value)
  localStorage.setItem('ui_theme', value)
}

function toggleTheme() {
  theme.value = theme.value === 'light' ? 'dark' : 'light'
  applyTheme(theme.value)
}

function toggleCollapse() {
  if (isMobile.value) return
  collapsed.value = !collapsed.value
}

function handleNavClick() {
  if (isMobile.value) {
    mobileMenuOpen.value = false
  }
}

function isMenuActive(item) {
  if (!item?.path) return false
  if (item.name === "Home") {
    return route.path === "/"
  }
  return route.path === item.path || route.path.startsWith(`${item.path}/`)
}

function handleUserCommand(command) {
  if (command === 'settings') {
    router.push('/settings')
    return
  }
  handleLogout()
}

function handleLogout() {
  userStore.logout()
  router.push('/login')
}

function handleResize() {
  isMobile.value = window.innerWidth < 768
  if (!isMobile.value) {
    mobileMenuOpen.value = false
  }
}

async function fetchUnread() {
  try {
    const res = await notificationApi.list({ is_read: false, page_size: 1 })
    unreadCount.value = res.unread_count || 0
  } catch {
    unreadCount.value = 0
  }
}

onMounted(async () => {
  applyTheme(theme.value)
  if (!userStore.user) {
    await userStore.fetchUser()
  }
  await fetchUnread()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped lang="scss">
.sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.logo-row {
  height: var(--topbar-height);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 12px;
  border-bottom: 1px solid var(--border-light);
}

.logo-mark {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(145deg, #e8f3ff 0%, #dbeafe 100%);
  border: 1px solid #bfd9ff;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.logo-mark .stem {
  position: absolute;
  left: 50%;
  bottom: 7px;
  transform: translateX(-50%);
  width: 4px;
  height: 15px;
  border-radius: 99px;
  background: linear-gradient(180deg, #0ea5a4 0%, #1663c7 100%);
}

.logo-mark .leaf {
  position: absolute;
  width: 10px;
  height: 5px;
  border-radius: 8px 8px 8px 2px;
  background: linear-gradient(120deg, #16a34a, #0f766e);
}

.logo-mark .leaf-a {
  left: 9px;
  bottom: 9px;
  transform: rotate(-28deg);
}

.logo-mark .leaf-b {
  left: 15px;
  bottom: 13px;
  transform: rotate(26deg);
}

.logo-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.logo-text strong {
  font-size: 13px;
}

.logo-text span {
  color: var(--text-muted);
  font-size: 11px;
}

.nav-groups {
  flex: 1;
  overflow: auto;
  padding: 10px 8px;
}

.group + .group {
  margin-top: 12px;
}

.group-title {
  margin: 0 8px 6px;
  color: var(--text-muted);
  font-size: 11px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: 10px;
  color: var(--text-secondary);
  font-size: 13px;
  transition: all 0.15s ease;
}

.nav-item:hover {
  color: var(--text-primary);
  background: var(--surface-2);
}

.nav-item.active {
  color: #fff;
  background: linear-gradient(120deg, var(--primary), var(--primary-light));
}

.item-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.sidebar-footer {
  padding: 8px;
  border-top: 1px solid var(--border-light);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sidebar-footer :deep(.el-button) {
  justify-content: flex-start;
}

.topbar {
  height: 100%;
  padding: 0 12px 0 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.left,
.right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.route-meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.route-meta h1 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
}

.breadcrumb {
  font-size: 12px;
}

.notify-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  border: 1px solid var(--border-light);
  position: relative;
}

.notify-btn:hover {
  color: var(--text-primary);
  background: var(--surface-2);
}

.badge {
  position: absolute;
  top: -5px;
  right: -5px;
  min-width: 16px;
  padding: 0 4px;
  height: 16px;
  border-radius: 8px;
  color: #fff;
  font-size: 10px;
  background: var(--danger-1);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.user-trigger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-secondary);
}

.user-trigger:hover {
  background: var(--surface-2);
}

.mobile-mask {
  position: fixed;
  inset: 0;
  z-index: 30;
  background: rgba(15, 23, 42, 0.36);
}

@media (max-width: 767px) {
  .route-meta h1 {
    font-size: 14px;
  }

  .breadcrumb {
    display: none;
  }
}
</style>
