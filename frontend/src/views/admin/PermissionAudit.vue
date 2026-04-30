<template>
  <div class="admin-page">
    <PageHeader title="权限审计" subtitle="查看 401/403 拒绝访问事件与来源信息" />

    <div class="toolbar">
      <el-select v-model="filters.status_code" clearable placeholder="状态码" style="width: 120px">
        <el-option :value="401" label="401" />
        <el-option :value="403" label="403" />
      </el-select>
      <el-date-picker v-model="filters.start_date" type="date" placeholder="开始日期" value-format="YYYY-MM-DD" />
      <el-date-picker v-model="filters.end_date" type="date" placeholder="结束日期" value-format="YYYY-MM-DD" />
      <el-button type="primary" @click="loadAuditLogs">查询</el-button>
    </div>

    <el-table :data="items" border stripe>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="status_code" label="状态码" width="90" />
      <el-table-column prop="method" label="方法" width="90" />
      <el-table-column prop="path" label="路径" min-width="220" />
      <el-table-column prop="user_id" label="用户ID" width="90" />
      <el-table-column prop="client_ip" label="IP" width="140" />
      <el-table-column prop="reason" label="原因" min-width="180" />
      <el-table-column prop="created_at" label="时间" min-width="180" />
    </el-table>

    <div class="pager">
      <el-pagination
        background
        layout="prev, pager, next, total"
        :current-page="page"
        :page-size="pageSize"
        :total="total"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { adminApi } from '@/api'
import PageHeader from '@/components/ui/PageHeader.vue'

const filters = reactive({
  status_code: undefined,
  start_date: '',
  end_date: ''
})
const items = ref([])
const page = ref(1)
const pageSize = 20
const total = ref(0)

async function loadAuditLogs() {
  const params = {
    page: page.value,
    page_size: pageSize,
    status_code: filters.status_code,
    start_date: filters.start_date || undefined,
    end_date: filters.end_date || undefined
  }
  const data = await adminApi.permissionAudit(params)
  items.value = data.items || []
  total.value = data.total || 0
}

function handlePageChange(nextPage) {
  page.value = nextPage
  loadAuditLogs()
}

onMounted(loadAuditLogs)
</script>

<style lang="scss" scoped>
.admin-page { display: flex; flex-direction: column; gap: 12px; }
.toolbar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.pager { display: flex; justify-content: flex-end; }
</style>
