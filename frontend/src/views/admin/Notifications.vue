<template>
  <div class="admin-page">
    <div class="toolbar">
      <el-select v-model="filters.type" clearable placeholder="通知类型" style="width: 140px">
        <el-option label="system" value="system" />
        <el-option label="warning" value="warning" />
        <el-option label="regional_alert" value="regional_alert" />
        <el-option label="agent_push" value="agent_push" />
      </el-select>
      <el-select v-model="filters.is_read" clearable placeholder="读取状态" style="width: 120px">
        <el-option label="未读" :value="false" />
        <el-option label="已读" :value="true" />
      </el-select>
      <el-input v-model="filters.user_id" clearable placeholder="用户ID" style="width: 120px" />
      <el-button type="primary" @click="loadNotifications">查询</el-button>
      <el-button @click="markAllRead">全部标记已读</el-button>
      <el-button type="success" @click="showBroadcast = true">广播通知</el-button>
    </div>

    <el-table :data="items" border stripe>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="user_id" label="用户ID" width="90" />
      <el-table-column prop="type" label="类型" width="140" />
      <el-table-column prop="title" label="标题" min-width="180" />
      <el-table-column prop="content" label="内容" min-width="260" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_read ? 'info' : 'danger'" size="small">
            {{ row.is_read ? '已读' : '未读' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" min-width="180" />
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

    <el-dialog v-model="showBroadcast" title="广播通知" width="520px">
      <el-form label-width="88px">
        <el-form-item label="类型">
          <el-select v-model="broadcast.type" style="width: 100%">
            <el-option label="system" value="system" />
            <el-option label="warning" value="warning" />
            <el-option label="regional_alert" value="regional_alert" />
            <el-option label="agent_push" value="agent_push" />
          </el-select>
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="broadcast.title" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="broadcast.content" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showBroadcast = false">取消</el-button>
        <el-button type="primary" @click="sendBroadcast">发送</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { adminApi } from '@/api'

const filters = reactive({
  type: '',
  is_read: undefined,
  user_id: ''
})

const items = ref([])
const page = ref(1)
const pageSize = 20
const total = ref(0)
const showBroadcast = ref(false)
const broadcast = reactive({
  type: 'system',
  title: '',
  content: ''
})

async function loadNotifications() {
  const params = {
    page: page.value,
    page_size: pageSize,
    type: filters.type || undefined,
    is_read: filters.is_read,
    user_id: filters.user_id ? Number(filters.user_id) : undefined
  }
  const data = await adminApi.notifications(params)
  items.value = data.items || []
  total.value = data.total || 0
}

async function markAllRead() {
  const params = {
    type: filters.type || undefined,
    user_id: filters.user_id ? Number(filters.user_id) : undefined
  }
  const data = await adminApi.markAllNotificationsRead(params)
  ElMessage.success(data.message || '已更新')
  loadNotifications()
}

async function sendBroadcast() {
  if (!broadcast.title || !broadcast.content) {
    ElMessage.warning('请填写标题和内容')
    return
  }
  const data = await adminApi.broadcastNotification({
    type: broadcast.type,
    title: broadcast.title,
    content: broadcast.content
  })
  ElMessage.success(`已发送 ${data.created_count || 0} 条通知`)
  showBroadcast.value = false
  broadcast.title = ''
  broadcast.content = ''
  loadNotifications()
}

function handlePageChange(nextPage) {
  page.value = nextPage
  loadNotifications()
}

onMounted(loadNotifications)
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
  flex-wrap: wrap;
}

.pager {
  display: flex;
  justify-content: flex-end;
}
</style>
