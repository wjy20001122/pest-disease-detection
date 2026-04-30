<template>
  <div class="app-shell" :class="{ 'is-collapsed': collapsed }">
    <aside class="shell-sidebar" :class="{ mobile: mobile, open: mobileOpen }">
      <slot name="sidebar" />
    </aside>
    <div class="shell-main">
      <header class="shell-topbar">
        <slot name="topbar" />
      </header>
      <main class="workspace-content">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup>
defineProps({
  collapsed: {
    type: Boolean,
    default: false
  },
  mobile: {
    type: Boolean,
    default: false
  },
  mobileOpen: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped lang="scss">
.app-shell {
  display: flex;
  min-height: 100vh;
  background: var(--surface-0);
}

.shell-sidebar {
  width: var(--sidebar-width);
  border-right: 1px solid var(--border-light);
  background: var(--surface-1);
  transition: width 0.2s ease;
}

.app-shell.is-collapsed .shell-sidebar {
  width: var(--sidebar-collapsed);
}

.shell-sidebar.mobile {
  position: fixed;
  left: -100%;
  top: 0;
  bottom: 0;
  width: min(85vw, var(--sidebar-width));
  z-index: 40;
  box-shadow: var(--shadow-md);
}

.shell-sidebar.mobile.open {
  left: 0;
}

.shell-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.shell-topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  height: var(--topbar-height);
  border-bottom: 1px solid var(--border-light);
  background: color-mix(in srgb, var(--surface-1) 92%, transparent);
  backdrop-filter: blur(8px);
}

.workspace-content {
  flex: 1;
  padding: 16px 20px 20px;
  overflow: auto;
}

@media (max-width: 767px) {
  .workspace-content {
    padding: 12px;
  }
}
</style>
