<template>
  <div class="overview-page">
    <div class="stats-grid">
      <div class="stat-card">
        <div class="label">用户总数</div>
        <div class="value">{{ dashboard.total_users || 0 }}</div>
        <div class="hint">今日新增 {{ dashboard.new_users_today || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="label">检测总数</div>
        <div class="value">{{ dashboard.total_detections || 0 }}</div>
        <div class="hint">今日检测 {{ dashboard.detections_today || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="label">活跃预警</div>
        <div class="value">{{ dashboard.active_alerts || 0 }}</div>
        <div class="hint">未读告警通知</div>
      </div>
      <div class="stat-card">
        <div class="label">可用模型</div>
        <div class="value">{{ dashboard.enabled_models || 0 }}</div>
        <div class="hint">当前启用模型数量</div>
      </div>
    </div>

    <div class="panel-grid">
      <div class="panel">
        <h3>检测类型分布</h3>
        <div class="breakdown-list">
          <div class="row">
            <span>图像检测</span>
            <strong>{{ dashboard.detection_breakdown?.image || 0 }}</strong>
          </div>
          <div class="row">
            <span>视频检测</span>
            <strong>{{ dashboard.detection_breakdown?.video || 0 }}</strong>
          </div>
          <div class="row">
            <span>摄像头检测</span>
            <strong>{{ dashboard.detection_breakdown?.camera || 0 }}</strong>
          </div>
        </div>
      </div>

      <div class="panel">
        <h3>治理快捷入口</h3>
        <div class="quick-actions">
          <router-link to="/admin/users" class="action-link">进入用户管理</router-link>
          <router-link to="/admin/notifications" class="action-link">进入通知治理</router-link>
          <router-link to="/admin/models" class="action-link">进入模型运维</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive } from 'vue'
import { adminApi } from '@/api'

const dashboard = reactive({
  total_users: 0,
  new_users_today: 0,
  total_detections: 0,
  detections_today: 0,
  active_alerts: 0,
  enabled_models: 0,
  detection_breakdown: { image: 0, video: 0, camera: 0 }
})

async function loadDashboard() {
  const data = await adminApi.dashboard()
  Object.assign(dashboard, data || {})
}

onMounted(loadDashboard)
</script>

<style lang="scss" scoped>
.overview-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.stat-card {
  padding: 16px;
  border: 1px solid var(--border-light);
  border-radius: 8px;
  background: var(--bg-primary);
}

.stat-card .label {
  font-size: 13px;
  color: var(--text-secondary);
}

.stat-card .value {
  margin-top: 6px;
  font-size: 28px;
  font-weight: 600;
  color: var(--text-primary);
}

.stat-card .hint {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-muted);
}

.panel-grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 12px;
}

.panel {
  padding: 16px;
  border: 1px solid var(--border-light);
  border-radius: 8px;
  background: var(--bg-primary);
}

.panel h3 {
  margin: 0 0 12px;
  font-size: 15px;
}

.breakdown-list .row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-light);
}

.breakdown-list .row:last-child {
  border-bottom: none;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-link {
  display: inline-block;
  text-decoration: none;
  padding: 10px 12px;
  border-radius: 6px;
  border: 1px solid var(--border-light);
  color: var(--text-primary);
}

.action-link:hover {
  background: var(--bg-secondary);
}

@media (max-width: 1024px) {
  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .panel-grid {
    grid-template-columns: 1fr;
  }
}
</style>
