<template>
  <div class="admin-page">
    <PageHeader title="模型运维" subtitle="配置模型启停、默认策略与回退提示" />

    <el-table :data="models" border stripe>
      <el-table-column prop="model_key" label="模型Key" min-width="130" />
      <el-table-column prop="display_name" label="模型名称" min-width="180">
        <template #default="{ row }">
          <el-input
            :model-value="row.display_name"
            size="small"
            @change="(value) => updateModel(row, { display_name: value })"
          />
        </template>
      </el-table-column>
      <el-table-column label="启用" width="90">
        <template #default="{ row }">
          <el-switch
            :model-value="Boolean(row.enabled)"
            @change="(value) => updateModel(row, { enabled: value })"
          />
        </template>
      </el-table-column>
      <el-table-column label="默认模型" width="110">
        <template #default="{ row }">
          <el-radio
            :model-value="defaultModelKey"
            :value="row.model_key"
            @change="setDefaultModel(row.model_key)"
          >
            默认
          </el-radio>
        </template>
      </el-table-column>
      <el-table-column label="云端回退" width="100">
        <template #default="{ row }">
          <el-switch
            :model-value="Boolean(row.fallback_to_cloud)"
            @change="(value) => updateModel(row, { fallback_to_cloud: value })"
          />
        </template>
      </el-table-column>
      <el-table-column label="回退提示语" min-width="300">
        <template #default="{ row }">
          <el-input
            :model-value="row.fallback_notice"
            size="small"
            @change="(value) => updateModel(row, { fallback_notice: value })"
          />
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { adminApi } from '@/api'
import PageHeader from '@/components/ui/PageHeader.vue'

const models = ref([])

const defaultModelKey = computed(() => {
  const current = models.value.find((item) => item.is_default)
  return current?.model_key || ''
})

async function loadModels() {
  const data = await adminApi.models()
  models.value = data.items || []
}

async function updateModel(row, payload) {
  const next = await adminApi.updateModel(row.model_key, payload)
  Object.assign(row, next)
  if (payload.is_default || payload.enabled !== undefined) {
    await loadModels()
  }
  ElMessage.success('模型策略已更新')
}

async function setDefaultModel(modelKey) {
  await adminApi.updateModel(modelKey, { is_default: true })
  await loadModels()
  ElMessage.success('默认模型已更新')
}

onMounted(loadModels)
</script>

<style lang="scss" scoped>
.admin-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
</style>
