<template>
  <div class="admin-layout">
    <div class="admin-nav">
      <router-link
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="nav-link"
        active-class="active"
      >
        {{ item.label }}
      </router-link>
    </div>
    <router-view />
  </div>
</template>

<script setup>
const navItems = [
  { to: '/admin/overview', label: '管理员概览' },
  { to: '/admin/users', label: '用户管理' },
  { to: '/admin/notifications', label: '通知治理' },
  { to: '/admin/models', label: '模型运维' }
]
</script>

<style lang="scss" scoped>
.admin-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.admin-nav {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border: 1px solid var(--border-light);
  border-radius: 8px;
  background: var(--bg-primary);
}

.nav-link {
  padding: 8px 12px;
  border-radius: 6px;
  text-decoration: none;
  color: var(--text-secondary);
  font-size: 14px;
  transition: all 0.2s;
}

.nav-link:hover {
  color: var(--text-primary);
  background: var(--bg-secondary);
}

.nav-link.active {
  background: var(--primary);
  color: #fff;
}
</style>
