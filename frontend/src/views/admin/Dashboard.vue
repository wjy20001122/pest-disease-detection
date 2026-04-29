<template>
  <div class="admin-dashboard">
    <!-- 概览卡片 -->
    <div class="stats-grid">
      <div class="stat-card card">
        <div class="stat-icon">👥</div>
        <div class="stat-content">
          <span class="stat-value">{{ stats.total_users }}</span>
          <span class="stat-label">用户总数</span>
        </div>
        <div class="stat-trend up">+{{ stats.new_users_today }} 今日</div>
      </div>

      <div class="stat-card card">
        <div class="stat-icon">🔍</div>
        <div class="stat-content">
          <span class="stat-value">{{ formatNumber(stats.total_detections) }}</span>
          <span class="stat-label">检测总数</span>
        </div>
        <div class="stat-trend up">+{{ stats.detections_today }} 今日</div>
      </div>

      <div class="stat-card card">
        <div class="stat-icon">⚠️</div>
        <div class="stat-content">
          <span class="stat-value">{{ stats.active_alerts }}</span>
          <span class="stat-label">活跃预警</span>
        </div>
        <div class="stat-trend" :class="stats.active_alerts > 10 ? 'down' : 'normal'">{{ stats.active_alerts > 10 ? '需要关注' : '正常' }}</div>
      </div>

      <div class="stat-card card">
        <div class="stat-icon">🤖</div>
        <div class="stat-content">
          <span class="stat-value">{{ stats.ai_models }}</span>
          <span class="stat-label">AI模型</span>
        </div>
        <div class="stat-trend normal">运行中</div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts-grid">
      <div class="chart-card card">
        <h3>检测趋势</h3>
        <div ref="trendChartRef" class="chart-container"></div>
      </div>

      <div class="chart-card card">
        <h3>病虫害分布</h3>
        <div ref="pieChartRef" class="chart-container"></div>
      </div>
    </div>

    <!-- 快捷操作和数据表 -->
    <div class="bottom-grid">
      <!-- 系统状态 -->
      <div class="status-card card">
        <h3>系统状态</h3>
        <div class="status-list">
          <div class="status-item">
            <span class="status-dot online"></span>
            <span class="status-name">API服务</span>
            <span class="status-value">正常</span>
          </div>
          <div class="status-item">
            <span class="status-dot online"></span>
            <span class="status-name">数据库</span>
            <span class="status-value">正常</span>
          </div>
          <div class="status-item">
            <span class="status-dot online"></span>
            <span class="status-name">AI推理服务</span>
            <span class="status-value">正常</span>
          </div>
          <div class="status-item">
            <span class="status-dot online"></span>
            <span class="status-name">文件存储</span>
            <span class="status-value">正常</span>
          </div>
          <div class="status-item">
            <span class="status-dot warning"></span>
            <span class="status-name">响应时间</span>
            <span class="status-value">{{ systemStatus.response_time }}ms</span>
          </div>
        </div>
      </div>

      <!-- 最新检测 -->
      <div class="recent-card card">
        <h3>最新检测记录</h3>
        <el-table :data="recentDetections" size="small">
          <el-table-column prop="user" label="用户" width="100" />
          <el-table-column prop="type" label="类型" width="80">
            <template #default="{ row }">
              <el-tag size="small">{{ row.type }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="result" label="结果" />
          <el-table-column prop="time" label="时间" width="100" />
        </el-table>
      </div>

      <!-- 快捷操作 -->
      <div class="actions-card card">
        <h3>快捷操作</h3>
        <div class="action-buttons">
          <el-button @click="showUserDialog = true">用户管理</el-button>
          <el-button @click="showModelDialog = true">模型管理</el-button>
          <el-button @click="showKnowledgeDialog = true">知识库</el-button>
          <el-button @click="exportLogs">导出日志</el-button>
        </div>
      </div>
    </div>

    <!-- 用户管理对话框 -->
    <el-dialog v-model="showUserDialog" title="用户管理" width="900px">
      <div class="dialog-toolbar">
        <el-input v-model="userSearch" placeholder="搜索用户..." prefix-icon="Search" style="width: 200px" />
      </div>
      <el-table :data="filteredUsers" size="small">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="email" label="邮箱" />
        <el-table-column prop="role" label="角色" width="80">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" size="small">{{ row.role }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="detections" label="检测数" width="80" />
        <el-table-column prop="created_at" label="注册时间" width="120" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" text @click="editUser(row)">编辑</el-button>
            <el-button size="small" type="danger" text @click="deleteUser(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 模型管理对话框 -->
    <el-dialog v-model="showModelDialog" title="模型管理" width="800px">
      <div class="dialog-toolbar">
        <el-button type="primary" size="small" @click="showUploadDialog = true">上传模型</el-button>
      </div>
      <el-table :data="models" size="small">
        <el-table-column prop="name" label="模型名称" />
        <el-table-column prop="version" label="版本" width="80" />
        <el-table-column prop="pests" label="支持病虫害" />
        <el-table-column prop="accuracy" label="准确率" width="80">
          <template #default="{ row }">
            {{ (row.accuracy * 100).toFixed(1) }}%
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">{{ row.status === 'active' ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button size="small" text @click="toggleModel(row)">{{ row.status === 'active' ? '禁用' : '启用' }}</el-button>
            <el-button size="small" text @click="rollbackModel(row)">回滚</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 知识库管理对话框 -->
    <el-dialog v-model="showKnowledgeDialog" title="知识库管理" width="900px">
      <div class="dialog-toolbar">
        <el-button type="primary" size="small" @click="showAddKnowledge = true">添加条目</el-button>
        <el-button size="small" @click="batchUpdate">批量更新</el-button>
      </div>
      <el-table :data="knowledgeList" size="small">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="title" label="标题" />
        <el-table-column prop="category" label="分类" width="100" />
        <el-table-column prop="updated_at" label="更新时间" width="120" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" text @click="editKnowledge(row)">编辑</el-button>
            <el-button size="small" text @click="deleteKnowledge(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { adminApi } from '@/api'

const trendChartRef = ref(null)
const pieChartRef = ref(null)

const stats = reactive({
  total_users: 1256,
  new_users_today: 23,
  total_detections: 45890,
  detections_today: 156,
  active_alerts: 8,
  ai_models: 5
})

const systemStatus = reactive({
  response_time: 45
})

const recentDetections = ref([
  { user: '张**', type: '图像', result: '稻飞虱 (置信度 92%)', time: '10分钟前' },
  { user: '李**', type: '视频', result: '纹枯病 (置信度 88%)', time: '25分钟前' },
  { user: '王**', type: '摄像头', result: '二化螟 (置信度 95%)', time: '1小时前' }
])

const showUserDialog = ref(false)
const showModelDialog = ref(false)
const showKnowledgeDialog = ref(false)
const showUploadDialog = ref(false)
const showAddKnowledge = ref(false)
const userSearch = ref('')

const users = ref([
  { id: 1, username: '张三', email: 'zhang@example.com', role: 'user', detections: 45, created_at: '2026-04-01' },
  { id: 2, username: '李四', email: 'li@example.com', role: 'admin', detections: 128, created_at: '2026-03-15' },
  { id: 3, username: '王五', email: 'wang@example.com', role: 'user', detections: 23, created_at: '2026-04-20' }
])

const filteredUsers = computed(() => {
  if (!userSearch.value) return users.value
  return users.value.filter(u => u.username.includes(userSearch.value) || u.email.includes(userSearch.value))
})

const models = ref([
  { name: '水稻病害检测', version: 'v2.1', pests: '稻飞虱、纹枯病、稻瘟病', accuracy: 0.945, status: 'active' },
  { name: '玉米病害检测', version: 'v1.5', pests: '大斑病、小斑病', accuracy: 0.912, status: 'active' },
  { name: '通用虫害检测', version: 'v3.0', pests: '二化螟、三化螟', accuracy: 0.938, status: 'inactive' }
])

const knowledgeList = ref([
  { id: 1, title: '稻飞虱的识别与防治', category: '水稻虫害', updated_at: '2026-04-25' },
  { id: 2, title: '水稻纹枯病的发病规律', category: '水稻病害', updated_at: '2026-04-24' },
  { id: 3, title: '稻瘟病的综合防治策略', category: '水稻病害', updated_at: '2026-04-23' }
])

function formatNumber(num) {
  if (num >= 10000) return (num / 10000).toFixed(1) + 'w'
  return num.toString()
}

function initCharts() {
  // 检测趋势图
  const trendChart = echarts.init(trendChartRef.value)
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['检测次数', '预警次数'], bottom: 0 },
    xAxis: { type: 'category', data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'] },
    yAxis: [
      { type: 'value', name: '检测次数' },
      { type: 'value', name: '预警次数' }
    ],
    series: [
      { name: '检测次数', type: 'bar', data: [120, 145, 132, 168, 155, 142, 156] },
      { name: '预警次数', type: 'line', yAxisIndex: 1, data: [8, 12, 6, 15, 10, 7, 9] }
    ]
  })

  // 病虫害分布饼图
  const pieChart = echarts.init(pieChartRef.value)
  pieChart.setOption({
    tooltip: { trigger: 'item' },
    legend: { orient: 'vertical', left: 'left', bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 14 } },
      data: [
        { value: 35, name: '稻飞虱' },
        { value: 25, name: '纹枯病' },
        { value: 18, name: '稻瘟病' },
        { value: 12, name: '二化螟' },
        { value: 10, name: '其他' }
      ]
    }]
  })
}

function editUser(user) { ElMessage.info('编辑用户: ' + user.username) }
function deleteUser(user) { ElMessage.info('删除用户: ' + user.username) }
function toggleModel(model) { ElMessage.info('切换模型: ' + model.name) }
function rollbackModel(model) { ElMessage.info('回滚模型: ' + model.name) }
function editKnowledge(item) { ElMessage.info('编辑知识: ' + item.title) }
function deleteKnowledge(item) { ElMessage.info('删除知识: ' + item.title) }
function batchUpdate() { ElMessage.info('批量更新') }
function exportLogs() { ElMessage.info('导出日志') }

onMounted(async () => {
  try {
    const res = await adminApi.dashboard()
    Object.assign(stats, res.stats || {})
  } catch (e) {
    // 使用模拟数据
  }

  nextTick(() => {
    initCharts()
  })
})
</script>

<style lang="scss" scoped>
.admin-dashboard { max-width: 1400px; margin: 0 auto; }

.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
.stat-card { display: flex; align-items: center; gap: 16px; padding: 20px; }
.stat-icon { font-size: 32px; }
.stat-content { flex: 1; }
.stat-value { display: block; font-size: 28px; font-weight: 700; }
.stat-label { font-size: 14px; color: var(--text-secondary); }
.stat-trend { font-size: 12px; padding: 2px 8px; border-radius: 4px; &.up { background: #d1fae5; color: #065f46; } &.down { background: #fee2e2; color: #dc2626; } &.normal { background: var(--bg-secondary); color: var(--text-secondary); } }

.charts-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }
.chart-card { padding: 20px; h3 { margin: 0 0 16px; font-size: 16px; } }
.chart-container { height: 280px; }

.bottom-grid { display: grid; grid-template-columns: 1fr 1.5fr 1fr; gap: 16px; }
.status-card, .recent-card, .actions-card { padding: 20px; h3 { margin: 0 0 16px; font-size: 16px; } }

.status-list { display: flex; flex-direction: column; gap: 12px; }
.status-item { display: flex; align-items: center; gap: 12px; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; &.online { background: var(--success); } &.warning { background: #f59e0b; } &.error { background: var(--error); } }
.status-name { flex: 1; font-size: 14px; }
.status-value { font-size: 13px; color: var(--text-secondary); }

.action-buttons { display: flex; flex-direction: column; gap: 8px; }

.dialog-toolbar { margin-bottom: 16px; display: flex; gap: 12px; }
</style>