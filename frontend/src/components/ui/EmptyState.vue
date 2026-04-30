<template>
  <div class="empty-state-lite">
    <component :is="icon" class="icon" v-if="icon" />
    <h4>{{ title }}</h4>
    <p v-if="description">{{ description }}</p>
    <div v-if="$slots.actions" class="actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: '暂无数据'
  },
  description: {
    type: String,
    default: ''
  },
  icon: {
    type: Object,
    default: null
  }
})
</script>

<style scoped lang="scss">
.empty-state-lite {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 26px 16px;
  border: 1px dashed var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-2);
  color: var(--text-muted);
}

.icon {
  width: 20px;
  height: 20px;
}

h4 {
  margin: 0;
  color: var(--text-secondary);
  font-size: 14px;
}

p {
  margin: 0;
  font-size: 12px;
}

.actions {
  margin-top: 6px;
}
</style>
