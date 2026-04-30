<template>
  <section class="data-panel">
    <header v-if="title || $slots.actions" class="head">
      <h3 v-if="title">{{ title }}</h3>
      <div class="actions"><slot name="actions" /></div>
    </header>
    <div class="body"><slot /></div>
  </section>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: ''
  }
})
</script>

<style scoped lang="scss">
.data-panel {
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  background: var(--surface-1);
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-light);
}

h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.actions {
  display: flex;
  gap: 8px;
}

.body {
  padding: 14px;
}
</style>
