<template>
  <div class="page-header-lite">
    <div class="left">
      <h2>{{ title }}</h2>
      <p v-if="subtitle">{{ subtitle }}</p>
    </div>
    <div class="right">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true
  },
  subtitle: {
    type: String,
    default: ''
  }
})
</script>

<style scoped lang="scss">
.page-header-lite {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

h2 {
  margin: 0;
  font-size: 18px;
  line-height: 1.2;
  font-weight: 600;
}

p {
  margin: 6px 0 0;
  color: var(--text-secondary);
  font-size: 13px;
}

.right {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
