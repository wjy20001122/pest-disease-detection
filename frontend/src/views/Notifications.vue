<template>
  <div class="notifications-page">
    <PageHeader title="通知中心" subtitle="查看系统消息、预警推送与智能体审查通知">
      <template #actions>
        <el-button size="small" :disabled="!unreadCount" @click="markAllRead">全部已读</el-button>
      </template>
    </PageHeader>

    <div class="page-header">
      <h2>消息中心</h2>
    </div>

    <!-- 筛选标签 -->
    <div class="filter-tabs">
      <el-radio-group v-model="filterType" @change="handleFilterChange">
        <el-radio-button label="all">全部</el-radio-button>
        <el-radio-button label="warning">预警</el-radio-button>
        <el-radio-button label="system">系统</el-radio-button>
        <el-radio-button label="agent">智能体</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 通知列表 -->
    <div class="notifications-list">
      <div v-for="item in list" :key="item.id" class="notification-item card" :class="{ unread: !item.is_read }" @click="handleRead(item)">
        <div class="item-icon" :class="item.type">
          <span v-if="item.type === 'warning'">⚠️</span>
          <span v-else-if="item.type === 'system'">🔔</span>
          <span v-else>🤖</span>
        </div>
        <div class="item-content">
          <div class="item-header">
            <span class="item-title">{{ item.title }}</span>
            <span class="item-time">{{ formatTime(item.created_at) }}</span>
          </div>
          <p class="item-message">{{ item.content }}</p>
          <div v-if="item.data?.detection_id" class="item-action">
            <el-button size="small" text @click.stop="viewDetection(item.data.detection_id)">查看检测详情 →</el-button>
          </div>
        </div>
        <div v-if="!item.is_read" class="unread-dot"></div>
      </div>

      <div v-if="!list.length" class="empty">
        <div class="empty-icon">🔕</div>
        <p>暂无通知</p>
      </div>
    </div>

    <el-pagination
      v-if="total > pageSize"
      layout="prev, pager, next"
      :total="total"
      v-model:current-page="page"
      :page-size="pageSize"
      @current-change="fetchData"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { notificationApi } from '@/api'
import { io } from 'socket.io-client'
import PageHeader from '@/components/ui/PageHeader.vue'

const router = useRouter()
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const unreadCount = ref(0)
const filterType = ref('all')
let socket = null

function formatTime(time) {
  if (!time) return ''
  const d = new Date(time)
  const now = new Date()
  const diff = now - d

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'
  if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'
  return d.toLocaleDateString('zh-CN')
}

async function fetchData() {
  try {
    const params = {
      page: page.value,
      page_size: pageSize,
      type: filterType.value === 'all' ? undefined : filterType.value
    }
    const res = await notificationApi.list(params)
    list.value = res.items || []
    total.value = res.total || 0
    unreadCount.value = res.unread_count || 0
  } catch (e) {
    list.value = [
      { id: 1, type: 'warning', title: '区域虫害预警', content: '检测到您所在区域近期稻飞虱发生率上升，建议加强田间巡查。', is_read: false, created_at: new Date(Date.now() - 3600000).toISOString(), data: { detection_id: 123 } },
      { id: 2, type: 'system', title: '检测完成通知', content: '您的图像检测已完成，发现1处轻微病虫害，已为您创建跟踪任务。', is_read: false, created_at: new Date(Date.now() - 7200000).toISOString() },
      { id: 3, type: 'agent', title: '智能体审查报告', content: '您的检测记录已通过AI审查，判断为真实虫害，无需标记为误报。', is_read: true, created_at: new Date(Date.now() - 86400000).toISOString() }
    ]
    total.value = 3
    unreadCount.value = 2
  }
}

async function handleRead(item) {
  if (item.is_read) return
  try {
    await notificationApi.markRead(item.id)
    item.is_read = true
    unreadCount.value = Math.max(0, unreadCount.value - 1)
  } catch (e) {
    item.is_read = true
    unreadCount.value = Math.max(0, unreadCount.value - 1)
  }
}

async function markAllRead() {
  try {
    await notificationApi.markAllRead()
    list.value.forEach(item => item.is_read = true)
    unreadCount.value = 0
    ElMessage.success('已全部标记为已读')
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

function handleFilterChange() {
  page.value = 1
  fetchData()
}

function viewDetection(id) {
  router.push(`/history?detection_id=${id}`)
}

function connectSocket() {
  const token = localStorage.getItem('access_token')
  if (!token) return

  socket = io('/', {
    auth: { token },
    transports: ['websocket']
  })

  socket.on('notification', (data) => {
    if (data.type === 'new_notification') {
      list.value.unshift(data.notification)
      total.value++
      if (!data.notification.is_read) {
        unreadCount.value++
      }
      ElMessage.info(`新通知：${data.notification.title}`)
    } else if (data.type === 'notification_read') {
      const item = list.value.find(n => n.id === data.notification_id)
      if (item) item.is_read = true
    } else if (data.type === 'all_notifications_read') {
      list.value.forEach(item => item.is_read = true)
      unreadCount.value = 0
    }
  })
}

onMounted(() => {
  fetchData()
  connectSocket()
})

onUnmounted(() => {
  if (socket) {
    socket.disconnect()
  }
})
</script>

<style lang="scss" scoped>
.notifications-page { max-width: 800px; margin: 0 auto; }

.page-header { display: none; }

.filter-tabs { margin-bottom: 24px; }

.notifications-list { display: flex; flex-direction: column; gap: 12px; margin-bottom: 24px; }

.notification-item {
  display: flex; align-items: flex-start; gap: 16px; padding: 16px; cursor: pointer;
  transition: all 0.2s; position: relative;
  &:hover { background: var(--bg-secondary); }
  &.unread { background: rgba(16, 185, 129, 0.05); border-left: 3px solid var(--primary); }
}

.item-icon {
  width: 44px; height: 44px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: 20px; flex-shrink: 0;
  &.warning { background: #fef3c7; }
  &.system { background: #dbeafe; }
  &.agent { background: #d1fae5; }
}

.item-content { flex: 1; min-width: 0; }
.item-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.item-title { font-size: 15px; font-weight: 600; }
.item-time { font-size: 12px; color: var(--text-muted); }
.item-message { font-size: 14px; color: var(--text-secondary); margin: 0; line-height: 1.6; }
.item-action { margin-top: 8px; }

.unread-dot { position: absolute; top: 16px; right: 16px; width: 8px; height: 8px; background: var(--primary); border-radius: 50%; }

.empty { text-align: center; padding: 64px; color: var(--text-muted); .empty-icon { font-size: 64px; margin-bottom: 16px; } }
</style>
