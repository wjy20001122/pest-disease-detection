<template>
  <div class="overview-page">
    <div class="metric-grid">
      <MetricCard label="用户总数" :value="dashboard.total_users || 0" :icon="UserFilled" />
      <MetricCard label="检测总数" :value="dashboard.total_detections || 0" :icon="DataLine" />
      <MetricCard label="活跃预警" :value="dashboard.active_alerts || 0" :icon="Warning" />
      <MetricCard label="可用模型" :value="dashboard.enabled_models || 0" :icon="Cpu" />
    </div>

    <div class="panel-grid">
      <DataPanel title="检测类型分布">
        <div class="rows">
          <div class="row"><span>图像检测</span><strong>{{ dashboard.detection_breakdown?.image || 0 }}</strong></div>
          <div class="row"><span>视频检测</span><strong>{{ dashboard.detection_breakdown?.video || 0 }}</strong></div>
          <div class="row"><span>摄像头检测</span><strong>{{ dashboard.detection_breakdown?.camera || 0 }}</strong></div>
        </div>
      </DataPanel>

      <DataPanel title="治理快捷入口">
        <div class="links">
          <router-link to="/admin/users">用户管理</router-link>
          <router-link to="/admin/notifications">通知治理</router-link>
          <router-link to="/admin/models">模型运维</router-link>
          <router-link to="/admin/configs">系统配置</router-link>
          <router-link to="/admin/audit">权限审计</router-link>
        </div>
      </DataPanel>
    </div>

    <DataPanel title="队列健康">
      <div class="rows">
        <div class="row"><span>队列长度</span><strong>{{ queueMetrics.queue_length }}</strong></div>
        <div class="row"><span>排队任务</span><strong>{{ queueMetrics.queued_count }}</strong></div>
        <div class="row"><span>处理中任务</span><strong>{{ queueMetrics.processing_count }}</strong></div>
        <div class="row"><span>失败任务</span><strong>{{ queueMetrics.failed_count }}</strong></div>
        <div class="row"><span>停止任务</span><strong>{{ queueMetrics.stopped_count }}</strong></div>
        <div class="row">
          <span>健康等级</span>
          <StatusBadge :status="queueMetrics.level" :label="queueMetrics.level" />
        </div>
      </div>
    </DataPanel>
  </div>
</template>

<script setup>
import { onMounted, reactive } from 'vue'
import { adminApi } from '@/api'
import MetricCard from '@/components/ui/MetricCard.vue'
import DataPanel from '@/components/ui/DataPanel.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { Cpu, DataLine, UserFilled, Warning } from '@element-plus/icons-vue'

const dashboard = reactive({
  total_users: 0,
  total_detections: 0,
  active_alerts: 0,
  enabled_models: 0,
  detection_breakdown: { image: 0, video: 0, camera: 0 }
})

const queueMetrics = reactive({
  queue_length: 0,
  queued_count: 0,
  processing_count: 0,
  failed_count: 0,
  stopped_count: 0,
  level: 'normal'
})

onMounted(async () => {
  const [dashboardData, queueData] = await Promise.all([
    adminApi.dashboard(),
    adminApi.queueMetrics()
  ])
  Object.assign(dashboard, dashboardData || {})
  Object.assign(queueMetrics, queueData || {})
})
</script>

<style scoped lang="scss">
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.panel-grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 12px;
}

.rows {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.links {
  display: grid;
  gap: 8px;
}

.links a {
  border: 1px solid var(--border-light);
  border-radius: 8px;
  padding: 8px 10px;
  color: var(--text-secondary);
}

.links a:hover {
  border-color: var(--primary);
  color: var(--text-primary);
}

@media (max-width: 1279px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .panel-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 767px) {
  .metric-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
