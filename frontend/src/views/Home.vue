<template>
  <div class="home-page">
    <PageHeader
      :title="userStore.isAdmin ? '管理运营总览' : '检测工作台'"
      :subtitle="userStore.isAdmin ? '查看全局运营状态与队列健康' : '本地检测优先，普通用户仅图像检测'"
    />

    <div class="weather-panel">
      <div class="weather-head">
        <div class="weather-item">
          <span class="label">当前位置</span>
          <strong>{{ environment.county || environment.address || '未获取' }}</strong>
        </div>
        <div class="weather-item">
          <span class="label">当前天气</span>
          <strong>{{ environment.weather || '未获取' }}</strong>
        </div>
        <div class="weather-item">
          <span class="label">温度 / 湿度</span>
          <strong>{{ formatClimate(environment.temperature, environment.humidity) }}</strong>
        </div>
      </div>
      <div class="forecast-block">
        <div class="forecast-title">
          <span>未来7天天气</span>
          <small v-if="forecastError">{{ forecastError }}</small>
        </div>
        <div class="forecast-grid" v-if="weeklyForecast.length">
          <div class="forecast-card" v-for="(item, idx) in weeklyForecast" :key="`${item.date}-${idx}`">
            <span class="day">{{ item.dayLabel }}</span>
            <span class="weather">{{ item.weatherText }}</span>
            <span class="temp">{{ formatTempRange(item.tempMin, item.tempMax) }}</span>
          </div>
        </div>
        <div class="forecast-empty" v-else>
          {{ forecastLoading ? '正在获取未来7天天气...' : '暂无未来7天天气数据' }}
        </div>
      </div>
    </div>

    <div class="metric-grid">
      <MetricCard
        v-for="item in metrics"
        :key="item.label"
        :label="item.label"
        :value="item.value"
        :hint="item.hint"
        :icon="item.icon"
      />
    </div>

    <div class="quick-actions">
      <router-link
        v-for="item in quickLinks"
        :key="item.to"
        :to="item.to"
        class="action-card"
      >
        <component :is="item.icon" class="action-icon" />
        <div>
          <div class="action-title">{{ item.title }}</div>
          <div class="action-desc">{{ item.desc }}</div>
        </div>
      </router-link>
    </div>

    <div class="panel-grid">
      <DataPanel title="病虫害分布">
        <template v-if="diseaseItems.length">
          <div class="list">
            <div v-for="item in diseaseItems" :key="item.name" class="row">
              <span>{{ item.name }}</span>
              <strong>{{ item.count }}</strong>
            </div>
          </div>
        </template>
        <EmptyState v-else title="暂无病虫害分布数据" description="完成检测后将在这里展示聚合统计" :icon="DataLine" />
      </DataPanel>

      <DataPanel title="最新检测记录">
        <template #actions>
          <router-link to="/history" class="inline-link">查看全部</router-link>
        </template>
        <template v-if="recentDetections.length">
          <div class="list">
            <div v-for="item in recentDetections" :key="item.id" class="row">
              <div class="left">
                <StatusBadge :status="item.has_pest ? 'warning' : 'success'" :label="typeMap[item.detection_type] || '未知'" />
                <span>{{ item.disease_name || '未识别到病虫害' }}</span>
              </div>
              <small>{{ item.source === 'local_model' ? '本地模型' : '云端回退' }}</small>
            </div>
          </div>
        </template>
        <EmptyState v-else title="暂无检测记录" description="可以先去检测中心上传一张图片" :icon="Document" />
      </DataPanel>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useUserStore } from '@/stores/user'
import { adminApi, detectionApi, environmentApi, trackingApi } from '@/api'
import PageHeader from '@/components/ui/PageHeader.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import DataPanel from '@/components/ui/DataPanel.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import {
  Aim,
  Bell,
  DataLine,
  Document,
  Location,
  Odometer,
  Reading,
  User
} from '@element-plus/icons-vue'

const userStore = useUserStore()

const stats = ref({})
const recentDetections = ref([])
const trackingCount = ref(0)
const adminStats = ref({})
const environment = ref({
  address: '',
  county: '',
  weather: '',
  temperature: null,
  humidity: null
})
const weeklyForecast = ref([])
const forecastLoading = ref(false)
const forecastError = ref('')
const typeMap = { image: '图像', video: '视频', camera: '摄像头' }
const weatherCodeMap = {
  0: '晴',
  1: '晴间多云',
  2: '多云',
  3: '阴',
  45: '雾',
  48: '强雾',
  51: '小毛雨',
  53: '毛雨',
  55: '大毛雨',
  61: '小雨',
  63: '中雨',
  65: '大雨',
  71: '小雪',
  73: '中雪',
  75: '大雪',
  80: '阵雨',
  81: '强阵雨',
  82: '暴雨',
  95: '雷暴'
}

const diseaseItems = computed(() => stats.value.disease_distribution?.slice(0, 8) || [])

const metrics = computed(() => {
  if (userStore.isAdmin) {
    return [
      { label: '用户总数', value: adminStats.value.total_users || 0, hint: '平台注册用户', icon: User },
      { label: '检测总数', value: adminStats.value.total_detections || 0, hint: '累计检测任务', icon: Aim },
      { label: '活跃预警', value: adminStats.value.active_alerts || 0, hint: '需要关注事件', icon: Bell },
      { label: '可用模型', value: adminStats.value.enabled_models || 0, hint: '当前启用模型', icon: Odometer }
    ]
  }
  return [
    { label: '今日检测', value: stats.value.today_count || 0, hint: '最近24小时任务', icon: Aim },
    { label: '累计检测', value: stats.value.total_count || 0, hint: '历史总量', icon: DataLine },
    { label: '活跃跟踪', value: trackingCount.value || 0, hint: '正在追踪对象', icon: Location },
    { label: '识别病害类', value: diseaseItems.value.length || 0, hint: '最近分布Top', icon: Reading }
  ]
})

const quickLinks = computed(() => {
  if (userStore.isAdmin) {
    return [
      { to: '/admin/overview', title: '管理概览', desc: '查看整体运营指标', icon: Odometer },
      { to: '/admin/users', title: '用户管理', desc: '管理用户状态与角色', icon: User },
      { to: '/admin/models', title: '模型运维', desc: '维护模型策略与开关', icon: Aim }
    ]
  }
  return [
    { to: '/detect', title: '开始检测', desc: '上传图片/视频进行识别', icon: Aim },
    { to: '/history', title: '检测历史', desc: '查看历史记录与详情', icon: Document },
    { to: '/knowledge', title: '知识库', desc: '查询病虫害知识条目', icon: Reading }
  ]
})

function formatClimate(temperature, humidity) {
  if (temperature === null && humidity === null) return '未获取'
  const tempText = temperature === null ? '--' : `${temperature}°C`
  const humText = humidity === null ? '--' : `${humidity}%`
  return `${tempText} / ${humText}`
}

function formatTempRange(min, max) {
  const minText = Number.isFinite(min) ? `${Math.round(min)}°` : '--'
  const maxText = Number.isFinite(max) ? `${Math.round(max)}°` : '--'
  return `${minText} ~ ${maxText}`
}

function resolveWeatherText(code) {
  if (code === null || code === undefined || code === '') return '未知'
  return weatherCodeMap[Number(code)] || '天气'
}

function formatDayLabel(dateText, index) {
  if (index === 0) return '今天'
  if (index === 1) return '明天'
  const date = new Date(dateText)
  if (Number.isNaN(date.getTime())) return `第${index + 1}天`
  return ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][date.getDay()]
}

async function fetchWeeklyForecast(latitude, longitude) {
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
    weeklyForecast.value = []
    return
  }
  forecastLoading.value = true
  forecastError.value = ''
  try {
    const query = new URLSearchParams({
      latitude: String(latitude),
      longitude: String(longitude),
      timezone: 'auto',
      forecast_days: '7',
      daily: 'weather_code,temperature_2m_max,temperature_2m_min'
    })
    const response = await fetch(`https://api.open-meteo.com/v1/forecast?${query.toString()}`)
    if (!response.ok) {
      throw new Error(`forecast http ${response.status}`)
    }
    const data = await response.json()
    const daily = data?.daily || {}
    const dates = daily.time || []
    const weatherCodes = daily.weather_code || []
    const maxTemps = daily.temperature_2m_max || []
    const minTemps = daily.temperature_2m_min || []

    weeklyForecast.value = dates.slice(0, 7).map((date, index) => ({
      date,
      dayLabel: formatDayLabel(date, index),
      weatherText: resolveWeatherText(weatherCodes[index]),
      tempMax: Number(maxTemps[index]),
      tempMin: Number(minTemps[index])
    }))
  } catch (error) {
    weeklyForecast.value = []
    forecastError.value = '天气服务暂不可用'
    console.error('failed to fetch weekly forecast', error)
  } finally {
    forecastLoading.value = false
  }
}

async function fetchEnvironmentByIp() {
  try {
    const res = await environmentApi.ipCurrent()
    environment.value = {
      address: res.address || '',
      county: res.county || res.district || '',
      weather: res.weather || '',
      temperature: res.temperature ?? null,
      humidity: res.humidity ?? null
    }
    const lat = Number(res.latitude)
    const lng = Number(res.longitude)
    if (Number.isFinite(lat) && Number.isFinite(lng)) {
      fetchWeeklyForecast(lat, lng)
    } else {
      weeklyForecast.value = []
    }
  } catch {
    environment.value = { address: '', county: '', weather: '', temperature: null, humidity: null }
    weeklyForecast.value = []
  }
}

async function fetchEnvironmentByGeo(latitude, longitude) {
  try {
    const res = await environmentApi.current({ latitude, longitude })
    environment.value = {
      address: res.address || `${latitude.toFixed(5)},${longitude.toFixed(5)}`,
      county: res.county || res.district || '',
      weather: res.weather || '',
      temperature: res.temperature ?? null,
      humidity: res.humidity ?? null
    }
    fetchWeeklyForecast(latitude, longitude)
  } catch {
    await fetchEnvironmentByIp()
  }
}

function resolveEnvironment() {
  if (!navigator.geolocation) {
    fetchEnvironmentByIp()
    return
  }
  navigator.geolocation.getCurrentPosition(
    ({ coords }) => fetchEnvironmentByGeo(coords.latitude, coords.longitude),
    () => fetchEnvironmentByIp(),
    { enableHighAccuracy: true, timeout: 12000, maximumAge: 300000 }
  )
}

onMounted(async () => {
  resolveEnvironment()
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
    stats.value = statsRes || {}
    recentDetections.value = historyRes.items || []
    trackingCount.value = trackingRes.items?.length || 0
  } catch (error) {
    console.error('failed to load home data', error)
  }
})
</script>

<style scoped lang="scss">
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.weather-panel {
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  background: var(--surface-1);
  padding: 12px;
}

.weather-head {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.weather-item {
  border: 1px solid var(--border-light);
  background: var(--surface-2);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.weather-item .label {
  color: var(--text-secondary);
  font-size: 12px;
}

.weather-item strong {
  font-size: 14px;
  color: var(--text-primary);
  word-break: break-all;
}

.forecast-block {
  border: 1px dashed var(--border-light);
  border-radius: var(--radius-md);
  padding: 10px;
}

.forecast-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--text-secondary);
}

.forecast-title small {
  color: var(--warning);
}

.forecast-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 8px;
}

.forecast-card {
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  padding: 8px;
  text-align: center;
  background: var(--surface-2);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.forecast-card .day {
  font-size: 12px;
  color: var(--text-secondary);
}

.forecast-card .weather {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.forecast-card .temp {
  font-size: 12px;
  color: var(--primary);
}

.forecast-empty {
  font-size: 12px;
  color: var(--text-muted);
  padding: 8px 4px;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.action-card {
  display: flex;
  gap: 12px;
  align-items: center;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  background: var(--surface-1);
  padding: 14px;
}

.action-card:hover {
  border-color: var(--primary);
}

.action-icon {
  width: 20px;
  height: 20px;
  color: var(--primary);
}

.action-title {
  font-size: 14px;
  font-weight: 600;
}

.action-desc {
  margin-top: 3px;
  color: var(--text-secondary);
  font-size: 12px;
}

.panel-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.row strong {
  font-size: 13px;
}

.row small {
  color: var(--text-muted);
}

.inline-link {
  font-size: 12px;
  color: var(--primary);
}

@media (max-width: 1279px) {
  .weather-head,
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .forecast-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  .weather-head,
  .metric-grid,
  .quick-actions,
  .panel-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .forecast-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
