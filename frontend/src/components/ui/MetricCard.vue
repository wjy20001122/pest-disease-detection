<template>
  <section class="metric-card">
    <div class="meta">
      <span class="label">{{ label }}</span>
      <el-tag v-if="status" size="small" :type="statusType">{{ status }}</el-tag>
    </div>
    <div class="value-row">
      <component :is="icon" v-if="icon" class="icon" />
      <strong>{{ value }}</strong>
    </div>
    <p v-if="hint">{{ hint }}</p>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  hint: { type: String, default: '' },
  status: { type: String, default: '' },
  statusType: { type: String, default: 'info' },
  icon: { type: Object, default: null }
})

const value = computed(() => props.value ?? '--')
</script>

<style scoped lang="scss">
.metric-card {
  padding: 14px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  background: var(--surface-1);
}

.meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.label {
  color: var(--text-secondary);
  font-size: 12px;
}

.value-row {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.icon {
  width: 18px;
  height: 18px;
  color: var(--primary);
}

strong {
  font-size: 26px;
  line-height: 1.1;
}

p {
  margin: 8px 0 0;
  color: var(--text-muted);
  font-size: 12px;
}
</style>
