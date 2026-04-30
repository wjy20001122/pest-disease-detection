<template>
  <div class="home-page">
    <template v-if="userStore.isAdmin">
      <div class="stats-grid admin-grid">
        <div class="stat-card"><div class="stat-info"><div class="stat-value">{{ adminStats.total_users || 0 }}</div><div class="stat-label">用户总数</div></div></div>
        <div class="stat-card"><div class="stat-info"><div class="stat-value">{{ adminStats.total_detections || 0 }}</div><div class="stat-label">检测总数</div></div></div>
        <div class="stat-card"><div class="stat-info"><div class="stat-value">{{ adminStats.active_alerts || 0 }}</div><div class="stat-label">活跃预警</div></div></div>
        <div class="stat-card"><div class="stat-info"><div class="stat-value">{{ adminStats.enabled_models || 0 }}</div><div class="stat-label">可用模型</div></div></div>
      </div>
      <div class="quick-actions">
        <router-link to="/admin/overview" class="action-card primary"><div><div class="action-title">管理员概览</div><div class="action-desc">查看全局运营状态与检测结构</div></div></router-link>
        <router-link to="/admin/users" class="action-card"><div><div class="action-title">用户管理</div><div class="action-desc">角色调整、启停用户、治理账号</div></div></router-link>
        <router-link to="/admin/models" class="action-card"><div><div class="action-title">模型运维</div><div class="action-desc">管理模型可用性与云端回退策略</div></div></router-link>
      </div>
    </template>

    <template v-else>
    <div class="stats-grid">
      <div class="stat-card"><div class="stat-icon">📊</div><div class="stat-info"><div class="stat-value">{{ stats.today_count || 0 }}</div><div class="stat-label">今日检测</div></div></div>
      <div class="stat-card"><div class="stat-icon">📈</div><div class="stat-info"><div class="stat-value">{{ stats.total_count || 0 }}</div><div class="stat-label">总检测数</div></div></div>
      <div class="stat-card"><div class="stat-icon">⚠️</div><div class="stat-info"><div class="stat-value">{{ warningCount }}</div><div class="stat-label">待处理警告</div></div></div>
      <div class="stat-card"><div class="stat-icon">👤</div><div class="stat-info"><div class="stat-value">{{ trackingCount }}</div><div class="stat-label">活跃跟踪</div></div></div>
    </div>
    
    <div class="quick-actions">
      <router-link to="/detect" class="action-card primary"><div class="action-icon">🔍</div><div><div class="action-title">开始检测</div><div class="action-desc">上传图片或视频进行检测</div></div></router-link>
      <router-link to="/qna" class="action-card"><div class="action-icon">💬</div><div><div class="action-title">智能问答</div><div class="action-desc">咨询病虫害问题</div></div></router-link>
      <router-link to="/knowledge" class="action-card"><div class="action-icon">📚</div><div><div class="action-title">知识库</div><div class="action-desc">查询病虫害详情</div></div></router-link>
    </div>
    
    <div class="content-grid">
      <div class="card">
        <div class="card-header"><h3>病虫害分布</h3></div>
        <div class="card-body">
          <div v-if="stats.disease_distribution?.length" class="disease-list">
            <div v-for="item in stats.disease_distribution?.slice(0,6)" :key="item.name" class="disease-item">
              <span>{{ item.name }}</span><span>{{ item.count }}次</span>
            </div>
          </div>
          <div v-else class="empty"><span>暂无数据</span></div>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><h3>最新检测</h3><router-link to="/history" class="more">查看全部 →</router-link></div>
        <div class="card-body">
          <div v-if="recentDetections.length" class="detection-list">
            <div v-for="item in recentDetections" :key="item.id" class="detection-item">
              <div class="detection-info"><span class="tag">{{ typeMap[item.detection_type] }}</span><span>{{ item.disease_name || '未检测到' }}</span></div>
              <div class="detection-meta"><span class="source-tag" :class="item.source">{{ item.source === 'local_model' ? '本地' : '云端' }}</span></div>
            </div>
          </div>
          <div v-else class="empty"><span>暂无检测记录</span><router-link to="/detect" class="start-btn">立即检测</router-link></div>
        </div>
      </div>
    </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { detectionApi, trackingApi, adminApi } from '@/api'

const userStore = useUserStore()
const stats = ref({})
const recentDetections = ref([])
const warningCount = ref(0)
const trackingCount = ref(0)
const typeMap = { image: '图像', video: '视频', camera: '摄像头' }
const adminStats = ref({})

onMounted(async () => {
  try {
    if (userStore.isAdmin) {
      adminStats.value = await adminApi.dashboard()
      return
    }

    const [statsRes, historyRes, trackingRes] = await Promise.all([
      detectionApi.stats(),
      detectionApi.history({ page: 1, page_size: 5 }),
      trackingApi.list({ status: 'active' })
    ])
    stats.value = statsRes
    recentDetections.value = historyRes.items || []
    trackingCount.value = trackingRes.items?.length || 0
  } catch (e) { console.error(e) }
})
</script>

<style lang="scss" scoped>
.home-page { max-width: 1200px; margin: 0 auto; }
.admin-grid .stat-card { padding: 24px; }
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 24px; }
.stat-card { background: var(--bg-primary); border-radius: var(--radius-lg); padding: 20px; display: flex; align-items: center; gap: 16px; border: 1px solid var(--border-light); }
.stat-icon { font-size: 32px; }
.stat-value { font-size: 28px; font-weight: 600; }
.stat-label { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }
.quick-actions { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 24px; }
.action-card { display: flex; align-items: center; gap: 16px; padding: 24px; background: var(--bg-primary); border-radius: var(--radius-lg); border: 1px solid var(--border-light); text-decoration: none; transition: all 0.2s; &:hover { border-color: var(--primary); } &.primary { background: linear-gradient(135deg, #10b981, #059669); border: none; .action-title, .action-desc { color: white; } } }
.action-icon { font-size: 36px; }
.action-title { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.action-desc { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }
.content-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.card { background: var(--bg-primary); border-radius: var(--radius-lg); border: 1px solid var(--border-light); overflow: hidden; }
.card-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid var(--border-light); h3 { font-size: 16px; font-weight: 600; } .more { font-size: 13px; color: var(--primary); } }
.card-body { padding: 16px 20px; }
.disease-item { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid var(--border-light); &:last-child { border-bottom: none; } }
.detection-item { padding: 12px 0; border-bottom: 1px solid var(--border-light); &:last-child { border-bottom: none; } }
.detection-info { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.tag { padding: 2px 8px; background: var(--bg-secondary); border-radius: 4px; font-size: 12px; }
.source-tag { padding: 2px 8px; border-radius: 4px; font-size: 12px; &.local_model { background: #d1fae5; color: #065f46; } &.cloud_ai { background: #dbeafe; color: #1e40af; } }
.empty { text-align: center; padding: 32px; color: var(--text-muted); .start-btn { display: inline-block; margin-top: 16px; padding: 8px 20px; background: var(--primary); color: white; border-radius: var(--radius-md); text-decoration: none; } }
</style>
