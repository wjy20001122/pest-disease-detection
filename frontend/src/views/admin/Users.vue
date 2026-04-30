<template>
  <div class="admin-page">
    <div class="toolbar">
      <el-input
        v-model="filters.keyword"
        placeholder="用户名/邮箱"
        clearable
        style="width: 220px"
        @keyup.enter="loadUsers"
      />
      <el-select v-model="filters.role" clearable placeholder="角色" style="width: 120px">
        <el-option label="管理员" value="admin" />
        <el-option label="普通用户" value="user" />
      </el-select>
      <el-select v-model="filters.is_active" clearable placeholder="状态" style="width: 120px">
        <el-option label="启用" :value="true" />
        <el-option label="禁用" :value="false" />
      </el-select>
      <el-button type="primary" @click="loadUsers">查询</el-button>
    </div>

    <el-table :data="users" border stripe>
      <el-table-column prop="id" label="ID" width="72" />
      <el-table-column prop="username" label="用户名" min-width="140" />
      <el-table-column prop="email" label="邮箱" min-width="200" />
      <el-table-column prop="detections" label="检测数" width="90" />
      <el-table-column label="角色" width="150">
        <template #default="{ row }">
          <el-select
            :model-value="row.role"
            size="small"
            style="width: 110px"
            @change="(value) => updateRole(row, value)"
          >
            <el-option label="admin" value="admin" />
            <el-option label="user" value="user" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-switch
            :model-value="Boolean(row.is_active)"
            @change="(value) => updateActive(row, value)"
          />
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="注册时间" min-width="180" />
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
import { ElMessage } from 'element-plus'
import { adminApi } from '@/api'

const filters = reactive({
  keyword: '',
  role: '',
  is_active: undefined
})
const users = ref([])
const page = ref(1)
const pageSize = 20
const total = ref(0)
const loading = ref(false)

async function loadUsers() {
  if (loading.value) return
  loading.value = true
  try {
    const params = {
      page: page.value,
      page_size: pageSize,
      keyword: filters.keyword || undefined,
      role: filters.role || undefined,
      is_active: filters.is_active
    }
    const data = await adminApi.users(params)
    users.value = data.items || []
    total.value = data.total || 0
  } finally {
    loading.value = false
  }
}

async function updateRole(row, role) {
  await adminApi.updateUser(row.id, { role })
  row.role = role
  ElMessage.success('角色已更新')
}

async function updateActive(row, is_active) {
  await adminApi.updateUser(row.id, { is_active })
  row.is_active = is_active
  ElMessage.success('状态已更新')
}

function handlePageChange(nextPage) {
  page.value = nextPage
  loadUsers()
}

onMounted(loadUsers)
</script>

<style lang="scss" scoped>
.admin-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pager {
  display: flex;
  justify-content: flex-end;
}
</style>
