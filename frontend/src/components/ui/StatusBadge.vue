<template>
  <el-tag :type="mapType" size="small" effect="light" round>
    {{ label }}
  </el-tag>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: {
    type: String,
    default: 'default'
  },
  label: {
    type: String,
    default: ''
  }
})

const mapType = computed(() => {
  if (props.status === 'success' || props.status === 'completed' || props.status === 'normal') return 'success'
  if (props.status === 'warning' || props.status === 'processing' || props.status === 'warn') return 'warning'
  if (props.status === 'danger' || props.status === 'failed' || props.status === 'critical') return 'danger'
  return 'info'
})
</script>
