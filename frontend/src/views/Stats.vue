<template>
  <div class="stats-page">
    <div class="filter-section">
      <el-radio-group v-model="period" @change="fetchStats">
        <el-radio-button label="day">近7天</el-radio-button>
        <el-radio-button label="week">近4周</el-radio-button>
        <el-radio-button label="month">近90天</el-radio-button>
      </el-radio-group>
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        @change="fetchStats"
      />
    </div>

    <div class="stats-overview">
      <MetricCard label="总检测次数" :value="stats.total || 0" :icon="DataLine" />
      <MetricCard label="平均置信度" :value="stats.avg_confidence || 0" :icon="Aim" />
      <MetricCard label="高置信度检测" :value="stats.high_confidence_count || 0" :icon="WarningFilled" />
    </div>

    <div class="charts-grid">
      <div class="chart-card">
        <h3>检测趋势</h3>
        <div ref="trendChart" class="chart-container"></div>
      </div>
      <div class="chart-card">
        <h3>病虫害分布</h3>
        <div ref="pieChart" class="chart-container"></div>
      </div>
    </div>

    <div class="pest-ranking">
      <h3>病虫害排行榜</h3>
      <div class="ranking-list">
        <div
          v-for="(item, index) in stats.pest_distribution"
          :key="item.name"
          class="ranking-item"
        >
          <span class="rank">{{ index + 1 }}</span>
          <span class="pest-name">{{ item.name }}</span>
          <span class="pest-count">{{ item.count }}次</span>
          <div class="rank-bar" :style="{ width: getBarWidth(item.count) + '%' }"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import { detectionApi } from '@/api'
import MetricCard from '@/components/ui/MetricCard.vue'
import { Aim, DataLine, WarningFilled } from '@element-plus/icons-vue'

const period = ref('month')
const dateRange = ref([])
const stats = ref({})
const trendChart = ref(null)
const pieChart = ref(null)

let trendChartInstance = null
let pieChartInstance = null
let resizeHandler = null

async function fetchStats() {
  try {
    const params = { period: period.value }
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0].toISOString().split('T')[0]
      params.end_date = dateRange.value[1].toISOString().split('T')[0]
    }
    const res = await detectionApi.statsOverview(params)
    stats.value = res.data || res
    updateCharts()
  } catch (e) {
    console.error('Failed to fetch stats:', e)
  }
}

function updateCharts() {
  nextTick(() => {
    updateTrendChart()
    updatePieChart()
  })
}

function updateTrendChart() {
  if (!trendChart.value) return
  if (!trendChartInstance) {
    trendChartInstance = echarts.init(trendChart.value)
  }

  const trendData = stats.value.trend_data || []
  const dates = trendData.map((d) => d.date)
  const counts = trendData.map((d) => d.count)

  trendChartInstance.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: dates, boundaryGap: false },
    yAxis: { type: 'value', name: '检测次数' },
    series: [
      {
        name: '检测次数',
        type: 'line',
        smooth: true,
        data: counts,
        areaStyle: { color: 'rgba(34, 197, 94, 0.2)' },
        lineStyle: { color: '#22c55e' },
        itemStyle: { color: '#22c55e' }
      }
    ],
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true }
  })
}

function updatePieChart() {
  if (!pieChart.value) return
  if (!pieChartInstance) {
    pieChartInstance = echarts.init(pieChart.value)
  }

  const distribution = stats.value.pest_distribution || []
  const colors = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

  pieChartInstance.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c}次 ({d}%)' },
    legend: { orient: 'vertical', left: 'left' },
    series: [
      {
        name: '病虫害分布',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
        data: distribution.map((d, i) => ({
          value: d.count,
          name: d.name,
          itemStyle: { color: colors[i % colors.length] }
        }))
      }
    ]
  })
}

function getBarWidth(count) {
  const max = Math.max(...(stats.value.pest_distribution || []).map((d) => d.count), 1)
  return (count / max) * 100
}

onMounted(() => {
  fetchStats()
  resizeHandler = () => {
    trendChartInstance?.resize()
    pieChartInstance?.resize()
  }
  window.addEventListener('resize', resizeHandler)
})

onBeforeUnmount(() => {
  if (resizeHandler) {
    window.removeEventListener('resize', resizeHandler)
  }
  trendChartInstance?.dispose()
  pieChartInstance?.dispose()
})
</script>

<style scoped lang="scss">
.stats-page {
  max-width: 1200px;
  margin: 0 auto;
}

.filter-section {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
  align-items: center;
}

.stats-overview {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.chart-card {
  background: var(--surface-1);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-light);
  padding: 20px;
}

.chart-card h3 {
  font-size: 16px;
  margin-bottom: 16px;
}

.chart-container {
  height: 300px;
}

.pest-ranking {
  background: var(--surface-1);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-light);
  padding: 20px;
}

.pest-ranking h3 {
  font-size: 16px;
  margin-bottom: 16px;
}

.ranking-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ranking-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--surface-2);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.rank {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary);
  color: #fff;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 600;
  z-index: 1;
}

.pest-name {
  flex: 1;
  font-weight: 500;
  z-index: 1;
}

.pest-count {
  font-size: 14px;
  color: var(--text-secondary);
  z-index: 1;
}

.rank-bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  background: rgba(34, 197, 94, 0.1);
  border-radius: var(--radius-md);
}

@media (max-width: 1279px) {
  .stats-overview {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  .stats-overview,
  .charts-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .filter-section {
    flex-direction: column;
    align-items: stretch;
  }

  :deep(.el-date-editor.el-input__wrapper),
  :deep(.el-date-editor) {
    width: 100%;
  }
}
</style>
