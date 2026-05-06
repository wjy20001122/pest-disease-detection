<template>
  <div class="admin-page">
    <el-form label-width="260px" class="config-form">
      <el-form-item v-for="item in configFields" :key="item.key" :label="item.label">
        <el-input-number
          v-if="item.type === 'int'"
          v-model="form[item.key]"
          :min="item.min ?? 0"
          :step="item.step ?? 1"
          style="width: 220px"
        />
        <el-input-number
          v-else
          v-model="form[item.key]"
          :min="item.min ?? 0"
          :max="item.max ?? 1"
          :step="item.step ?? 0.05"
          style="width: 220px"
        />
      </el-form-item>
    </el-form>
    <div class="actions">
      <el-button type="primary" @click="saveConfigs">保存配置</el-button>
      <el-button @click="loadConfigs">刷新</el-button>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { adminApi } from '@/api'

const configFields = [
  { key: 'review_trigger_confidence', label: '审查触发置信度阈值', type: 'float', min: 0, max: 1, step: 0.05 },
  { key: 'regional_alert_threshold', label: '区域预警触发数量阈值', type: 'int', min: 1 },
  { key: 'regional_alert_days', label: '区域预警统计天数', type: 'int', min: 1 },
  { key: 'video_task_soft_time_limit_sec', label: '视频任务 Soft 超时(秒)', type: 'int', min: 60, step: 60 },
  { key: 'video_task_hard_time_limit_sec', label: '视频任务 Hard 超时(秒)', type: 'int', min: 60, step: 60 },
  { key: 'video_task_max_retries', label: '视频任务最大重试次数', type: 'int', min: 0 },
  { key: 'video_task_retry_backoff_sec', label: '视频任务重试退避(秒)', type: 'int', min: 1 },
  { key: 'queue_backlog_warn_threshold', label: '队列积压 Warn 阈值', type: 'int', min: 1 },
  { key: 'queue_backlog_critical_threshold', label: '队列积压 Critical 阈值', type: 'int', min: 1 }
]

const form = reactive({})

async function loadConfigs() {
  const data = await adminApi.configs()
  const values = data.items || {}
  configFields.forEach((field) => {
    form[field.key] = values[field.key]
  })
}

async function saveConfigs() {
  const values = {}
  configFields.forEach((field) => {
    values[field.key] = form[field.key]
  })
  await adminApi.updateConfigs(values)
  ElMessage.success('系统配置已更新')
  await loadConfigs()
}

onMounted(loadConfigs)
</script>

<style lang="scss" scoped>
.admin-page { display: flex; flex-direction: column; gap: 12px; }
.config-form {
  padding: 16px;
  border: 1px solid var(--border-light);
  border-radius: 8px;
  background: var(--bg-primary);
}
.actions { display: flex; gap: 8px; }
</style>
