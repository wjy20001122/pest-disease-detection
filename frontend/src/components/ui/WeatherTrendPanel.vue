<template>
  <section class="weather-trend">
    <div class="weather-trend__header">
      <span class="weather-trend__location">{{ environment.county || environment.address || '当前位置' }}</span>
      <small v-if="forecastError" class="weather-trend__error">{{ forecastError }}</small>
    </div>

    <div v-if="weeklyForecast.length" class="weather-trend__chart">
      <div class="weather-trend__scroller">
        <div class="weather-trend__stage">
          <svg class="weather-trend__lines" :viewBox="`0 0 ${chartWidth} ${chartHeight}`" preserveAspectRatio="none" aria-hidden="true">
            <line
              v-for="divider in dividers"
              :key="`divider-${divider}`"
              class="weather-trend__divider"
              :x1="divider"
              :x2="divider"
              y1="0"
              :y2="chartHeight"
            />
            <polyline class="weather-trend__line weather-trend__line--max" :points="maxLinePoints" />
            <polyline class="weather-trend__line weather-trend__line--min" :points="minLinePoints" />

            <g v-for="(point, idx) in plottedPoints" :key="`point-${point.date}-${idx}`">
              <circle class="weather-trend__point-ring" :cx="point.x" :cy="point.maxY" r="8" />
              <circle class="weather-trend__point-core weather-trend__point-core--max" :cx="point.x" :cy="point.maxY" r="5" />
              <circle class="weather-trend__point-ring" :cx="point.x" :cy="point.minY" r="8" />
              <circle class="weather-trend__point-core weather-trend__point-core--min" :cx="point.x" :cy="point.minY" r="5" />
              <text class="weather-trend__value weather-trend__value--max" :x="point.x" :y="point.maxY - 24">
                {{ Number.isFinite(point.tempMax) ? `${Math.round(point.tempMax)}°` : '--' }}
              </text>
              <text class="weather-trend__value weather-trend__value--min" :x="point.x" :y="point.minY + 36">
                {{ Number.isFinite(point.tempMin) ? `${Math.round(point.tempMin)}°` : '--' }}
              </text>
            </g>
          </svg>

          <div class="weather-trend__columns">
            <article v-for="(item, idx) in weeklyForecast" :key="`${item.date}-${idx}`" class="weather-trend__column">
              <div class="weather-trend__top">
                <div class="weather-trend__day">{{ item.dayLabel }}</div>
                <div class="weather-trend__date">{{ formatDateLabel(item.date) }}</div>
                <div class="weather-trend__weather">{{ item.weatherText }}</div>
              </div>

              <div v-if="idx === 0" class="weather-trend__current">
                {{ environment.temperature ?? '--' }}<em>°C</em>
              </div>

              <div class="weather-trend__grade">{{ weatherGrade(item.weatherText) }}</div>
            </article>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="weather-trend__empty">
      {{ forecastLoading ? '正在获取未来7天天气...' : '暂无未来7天天气数据' }}
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { environmentApi } from '@/api'

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

const chartWidth = 980
const chartHeight = 460
const chartTop = 210
const chartBottom = 350
const colWidth = computed(() => chartWidth / Math.max(1, weeklyForecast.value.length))
const dividers = computed(() =>
  Array.from({ length: Math.max(0, weeklyForecast.value.length - 1) }, (_, i) => Math.round((i + 1) * colWidth.value))
)
const tempBound = computed(() => {
  const values = weeklyForecast.value.flatMap((item) => [Number(item.tempMax), Number(item.tempMin)]).filter(Number.isFinite)
  if (!values.length) return { min: 0, max: 1 }
  return { min: Math.min(...values) - 1, max: Math.max(...values) + 1 }
})

function mapTempToY(temp) {
  const span = Math.max(1, tempBound.value.max - tempBound.value.min)
  const ratio = (Number(temp) - tempBound.value.min) / span
  return chartBottom - ratio * (chartBottom - chartTop)
}

const plottedPoints = computed(() =>
  weeklyForecast.value.map((item, index) => {
    const x = colWidth.value * (index + 0.5)
    return {
      ...item,
      x,
      maxY: mapTempToY(item.tempMax),
      minY: mapTempToY(item.tempMin)
    }
  })
)

const maxLinePoints = computed(() =>
  plottedPoints.value.map((item) => `${item.x},${item.maxY}`).join(' ')
)
const minLinePoints = computed(() =>
  plottedPoints.value.map((item) => `${item.x},${item.minY}`).join(' ')
)

function resolveWeatherText(code) {
  if (code === null || code === undefined || code === '') return '未知'
  return weatherCodeMap[Number(code)] || '天气'
}

function weatherGrade(text) {
  if (!text) return '优'
  if (text.includes('晴')) return '优'
  if (text.includes('云') || text.includes('阴')) return '良'
  return '一般'
}

function formatDayLabel(dateText, index) {
  if (index === 0) return '今天'
  if (index === 1) return '明天'
  const date = new Date(dateText)
  if (Number.isNaN(date.getTime())) return `第${index + 1}天`
  return ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][date.getDay()]
}

function formatDateLabel(dateText) {
  const date = new Date(dateText)
  if (Number.isNaN(date.getTime())) return dateText || '--'
  return `${date.getMonth() + 1}月${date.getDate()}日`
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

onMounted(() => {
  resolveEnvironment()
})
</script>

<style scoped lang="scss">
.weather-trend {
  background: #ffffff;
  border: 1px solid #e6eaf0;
  border-radius: 14px;
  overflow: hidden;
}

.weather-trend__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px 10px;
  color: #111827;
  font-size: 14px;
}

.weather-trend__location {
  font-weight: 600;
}

.weather-trend__error {
  color: #d97706;
}

.weather-trend__chart {
  position: relative;
  min-height: 460px;
}

.weather-trend__scroller {
  overflow-x: auto;
  overflow-y: hidden;
}

.weather-trend__stage {
  position: relative;
  min-width: 980px;
  min-height: 460px;
}

.weather-trend__lines {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  width: 100%;
  height: 460px;
  z-index: 1;
  pointer-events: none;
}

.weather-trend__divider {
  stroke: rgba(215, 221, 230, 0.85);
  stroke-width: 1;
}

.weather-trend__line {
  fill: none;
  stroke-width: 5;
  stroke-linecap: round;
  stroke-linejoin: round;
  shape-rendering: geometricPrecision;
}

.weather-trend__line--max {
  stroke: #ff7a00;
}

.weather-trend__line--min {
  stroke: #5f97ea;
}

.weather-trend__columns {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  min-height: 460px;
  background: #fff;
}

.weather-trend__column {
  position: relative;
  z-index: 2;
  min-height: 460px;
  padding: 18px 8px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.weather-trend__top {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-height: 120px;
}

.weather-trend__day {
  font-size: 22px;
  line-height: 1.1;
  font-weight: 700;
  color: #0f172a;
}

.weather-trend__date {
  margin-top: 8px;
  font-size: 13px;
  color: #6b7280;
}

.weather-trend__weather {
  margin-top: 16px;
  font-size: 20px;
  line-height: 1.2;
  font-weight: 600;
  color: #334155;
}

.weather-trend__current {
  margin-top: 14px;
  margin-bottom: 140px;
  font-size: 48px;
  line-height: 1;
  font-weight: 700;
  color: #0f172a;
}

.weather-trend__current em {
  font-style: normal;
  font-size: 20px;
  margin-left: 2px;
}

.weather-trend__point-ring {
  fill: #ffffff;
}

.weather-trend__point-core--max {
  fill: #ff7a00;
}

.weather-trend__point-core--min {
  fill: #5f97ea;
}

.weather-trend__value {
  font-weight: 700;
  font-size: 30px;
  text-anchor: middle;
  font-variant-numeric: tabular-nums;
}

.weather-trend__value--max {
  fill: #c57229;
}

.weather-trend__value--min {
  fill: #4686df;
}

.weather-trend__grade {
  margin-top: auto;
  padding-bottom: 8px;
  font-size: 20px;
  font-weight: 600;
  color: #8a6b00;
}

.weather-trend__empty {
  padding: 20px;
  color: #6b7280;
  font-size: 13px;
}

@media (max-width: 1279px) {
  .weather-trend__stage {
    min-width: 900px;
  }

  .weather-trend__temp {
    font-size: 36px;
  }
}

@media (max-width: 767px) {
  .weather-trend__header {
    padding: 14px 16px 8px;
  }

  .weather-trend__column {
    min-height: 320px;
    padding: 14px 6px 18px;
  }

  .weather-trend__day {
    font-size: 18px;
  }

  .weather-trend__date {
    font-size: 12px;
  }

  .weather-trend__weather {
    font-size: 14px;
  }

  .weather-trend__current {
    font-size: 30px;
    margin-bottom: 100px;
  }

  .weather-trend__value {
    font-size: 24px;
  }

  .weather-trend__stage {
    min-width: 840px;
  }
}
</style>
