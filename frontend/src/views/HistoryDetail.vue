<template>
  <div class="history-detail-page">
    <PageHeader title="检测详情" :subtitle="`记录 #${recordId}`">
      <template #actions>
        <button class="btn-outline" @click="goBack">返回历史</button>
      </template>
    </PageHeader>

    <div v-if="loading" class="state-card">正在加载详情...</div>
    <div v-else-if="error" class="state-card error">{{ error }}</div>
    <div v-else-if="detail" class="detail-card">
      <div class="meta-row">
        <span class="type-tag">{{ typeLabel }}</span>
        <span class="time">{{ formatTime(detail.created_at) }}</span>
      </div>

      <template v-if="isImageType">
        <div class="image-grid">
          <div class="panel">
            <p class="panel-title">原图</p>
            <img v-if="detail.input" :src="detail.input" alt="原图" class="image-view" />
            <div v-else class="placeholder">原图不可用</div>
          </div>
          <div class="panel">
            <p class="panel-title">检测结果图</p>
            <img v-if="detail.output" :src="detail.output" alt="结果图" class="image-view" />
            <div v-else class="placeholder">暂无标注结果图</div>
          </div>
        </div>

        <div class="stats-card">
          <h3>图像检测统计</h3>
          <div v-if="imageItems.length" class="item-grid">
            <div v-for="item in imageItems" :key="item.name" class="item-card">
              <div class="name">{{ item.name }}</div>
              <div class="meta">数量 {{ item.count }} · 最高置信度 {{ item.confidence }}</div>
            </div>
          </div>
          <div v-else class="placeholder small">未检测到病虫害</div>
        </div>
      </template>

      <template v-else>
        <div class="panel">
          <p class="panel-title">检测视频</p>
          <video v-if="videoUrl" :src="videoUrl" class="video-view" controls autoplay />
          <div v-else class="placeholder">视频资源不可用</div>
        </div>

        <div class="stats-card">
          <h3>视频/摄像头检测统计</h3>
          <div class="quick-stats">
            <span>总帧数 {{ videoStats.frame_count || 0 }}</span>
            <span>跟踪目标 {{ videoStats.total_tracks || 0 }}</span>
            <span>检测总数 {{ totalDetectionCount }}</span>
          </div>
          <div v-if="totalCountEntries.length" class="item-grid">
            <div v-for="entry in totalCountEntries" :key="entry.name" class="item-card">
              <div class="name">{{ entry.name }}</div>
              <div class="meta">累计 {{ entry.count }} 次</div>
            </div>
          </div>
          <div v-else class="placeholder small">未检测到病虫害</div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { detectionApi } from '@/api'
import PageHeader from '@/components/ui/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const error = ref('')
const detail = ref(null)

const recordId = computed(() => route.params.id)
const detectionType = computed(() => {
  const type = String(route.query.type || 'image').toLowerCase()
  return ['image', 'video', 'camera'].includes(type) ? type : 'image'
})

const typeLabel = computed(() => ({ image: '图像', video: '视频', camera: '摄像头' }[detectionType.value]))
const isImageType = computed(() => detectionType.value === 'image')

const imageItems = computed(() => {
  if (!detail.value || !isImageType.value) return []
  const labels = parseJsonField(detail.value.label, [])
  const confidences = parseJsonField(detail.value.confidence, [])
  if (!Array.isArray(labels) || !labels.length) return []

  const grouped = {}
  labels.forEach((label, idx) => {
    const key = String(label)
    if (!grouped[key]) grouped[key] = { name: key, count: 0, maxConfidence: 0 }
    grouped[key].count += 1
    const confidence = Number(confidences[idx])
    if (Number.isFinite(confidence)) grouped[key].maxConfidence = Math.max(grouped[key].maxConfidence, confidence)
  })

  return Object.values(grouped)
    .map((item) => {
      const normalized = item.maxConfidence <= 1 ? item.maxConfidence * 100 : item.maxConfidence
      return { name: item.name, count: item.count, confidence: `${normalized.toFixed(1)}%` }
    })
    .sort((a, b) => b.count - a.count)
})

const videoStats = computed(() => {
  if (!detail.value || isImageType.value) return {}
  const stats = parseJsonField(detail.value.track_stats, {})
  return {
    frame_count: Number(stats?.frame_count || 0),
    total_tracks: Number(stats?.total_tracks || 0),
    total_counts: stats?.total_counts && typeof stats.total_counts === 'object' ? stats.total_counts : {}
  }
})

const totalCountEntries = computed(() => {
  const totalCounts = videoStats.value.total_counts || {}
  return Object.entries(totalCounts)
    .map(([name, count]) => ({ name, count: Number(count) || 0 }))
    .filter((entry) => entry.count > 0)
    .sort((a, b) => b.count - a.count)
})

const totalDetectionCount = computed(() => totalCountEntries.value.reduce((sum, entry) => sum + entry.count, 0))

const videoUrl = computed(() => detail.value?.output || detail.value?.input || '')

function parseJsonField(value, fallback) {
  if (!value) return fallback
  if (typeof value === 'object') return value
  try {
    return JSON.parse(value)
  } catch {
    return fallback
  }
}

function formatTime(time) {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

function goBack() {
  router.push('/history')
}

async function fetchDetail() {
  loading.value = true
  error.value = ''
  try {
    detail.value = await detectionApi.detail(recordId.value, detectionType.value)
  } catch (err) {
    error.value = err?.response?.data?.detail || '加载检测详情失败'
  } finally {
    loading.value = false
  }
}

onMounted(fetchDetail)
</script>

<style scoped lang="scss">
.history-detail-page { max-width: 1200px; margin: 0 auto; }
.state-card { background: var(--bg-primary); border: 1px solid var(--border-light); border-radius: var(--radius-md); padding: 20px; color: var(--text-secondary); }
.state-card.error { color: #dc2626; }
.detail-card { background: var(--bg-primary); border: 1px solid var(--border-light); border-radius: var(--radius-md); padding: 16px; display: grid; gap: 14px; }
.meta-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.type-tag { padding: 4px 10px; border-radius: 999px; background: var(--bg-secondary); font-size: 12px; color: var(--text-secondary); }
.time { color: var(--text-muted); font-size: 13px; }
.image-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.panel { border: 1px solid var(--border-light); border-radius: var(--radius-md); overflow: hidden; background: var(--bg-secondary); }
.panel-title { margin: 0; padding: 10px 12px; border-bottom: 1px solid var(--border-light); font-size: 13px; color: var(--text-secondary); }
.image-view, .video-view { display: block; width: 100%; max-height: 520px; object-fit: contain; background: #000; }
.placeholder { padding: 28px 16px; color: var(--text-muted); text-align: center; }
.placeholder.small { padding: 14px; text-align: left; }
.stats-card { border: 1px solid var(--border-light); border-radius: var(--radius-md); padding: 12px; }
.stats-card h3 { margin: 0 0 10px; font-size: 15px; }
.quick-stats { display: flex; flex-wrap: wrap; gap: 16px; margin-bottom: 10px; color: var(--text-secondary); font-size: 13px; }
.item-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; }
.item-card { border: 1px solid var(--border-light); border-radius: var(--radius-sm); padding: 10px; background: var(--bg-secondary); }
.item-card .name { font-weight: 600; font-size: 14px; margin-bottom: 4px; }
.item-card .meta { color: var(--text-secondary); font-size: 12px; }
.btn-outline { padding: 8px 14px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: transparent; cursor: pointer; }
@media (max-width: 900px) {
  .image-grid { grid-template-columns: 1fr; }
}
</style>
