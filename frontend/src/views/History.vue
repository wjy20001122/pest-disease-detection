<template>
  <div class="history-page">
    <PageHeader title="检测历史" subtitle="按类型、日期和关键词筛选历史检测记录" />

    <div class="filters">
      <el-select v-model="filter.type" placeholder="检测类型" clearable size="default" style="width: 120px">
        <el-option label="图像" value="image" />
        <el-option label="视频" value="video" />
        <el-option label="摄像头" value="camera" />
      </el-select>
      <el-date-picker v-model="filter.date_from" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" />
      <el-date-picker v-model="filter.date_to" type="date" value-format="YYYY-MM-DD" placeholder="结束日期" />
      <el-input v-model="filter.keyword" clearable placeholder="关键词(模型/crop)" style="width: 200px" />
    </div>
    
    <div class="history-list" v-if="list.length">
      <div v-for="item in list" :key="item.id" class="history-item card">
        <div class="item-header">
          <span class="type-tag">{{ typeMap[item.detection_type || item.type] }}</span>
          <span class="source-tag" :class="resolveSource(item)">{{ resolveSourceLabel(item) }}</span>
        </div>
        <div class="item-body">
          <div class="disease-name">{{ resolveDiseaseName(item) }}</div>
          <div class="item-info">
            <span v-if="resolveConfidence(item) !== null">置信度 {{ resolveConfidence(item) }}</span>
            <span v-if="item.severity" class="severity" :class="item.severity">{{ severityMap[item.severity] }}</span>
            <span v-if="resolveDetectionCount(item) > 0">检测数量 {{ resolveDetectionCount(item) }}</span>
          </div>
        </div>
        <div class="item-footer">
          <span class="time">{{ formatTime(item.created_at) }}</span>
          <button class="btn-detail" @click="viewDetail(item.id, item.detection_type || item.type)">查看详情 →</button>
        </div>
      </div>
    </div>
    
    <EmptyState v-else title="暂无检测记录" description="可以前往检测中心开始一次新检测" :icon="Document">
      <template #actions>
        <router-link to="/detect" class="btn-primary">开始检测</router-link>
      </template>
    </EmptyState>
    
    <el-pagination v-if="total > pageSize" layout="prev, pager, next" :total="total" v-model:current-page="page" :page-size="pageSize" @current-change="fetchData" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { detectionApi } from '@/api'
import PageHeader from '@/components/ui/PageHeader.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { Document } from '@element-plus/icons-vue'

const router = useRouter()
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const filter = reactive({ type: '', date_from: '', date_to: '', keyword: '' })
const typeMap = { image: '图像', video: '视频', camera: '摄像头' }
const severityMap = { high: '严重', medium: '中等', low: '轻微' }

function parseJsonField(value, fallback) {
  if (!value) return fallback
  if (typeof value === 'object') return value
  try {
    return JSON.parse(value)
  } catch {
    return fallback
  }
}

function resolveSource(item) {
  const source = item?.source || item?.model_key || item?.modelKey || ''
  return source === 'local_model' ? 'local_model' : 'cloud_ai'
}

function resolveSourceLabel(item) {
  return resolveSource(item) === 'local_model' ? '本地模型' : '云端AI'
}

function resolveDetectionCount(item) {
  const detectionType = item?.detection_type || item?.type
  if (detectionType === 'image') {
    const labels = parseJsonField(item?.label, [])
    return Array.isArray(labels) ? labels.length : 0
  }
  const stats = parseJsonField(item?.track_stats, {})
  const totalCounts = stats?.total_counts || stats?.totalCounts || {}
  if (!totalCounts || typeof totalCounts !== 'object') return 0
  return Object.values(totalCounts).reduce((sum, count) => sum + (Number(count) || 0), 0)
}

function resolveDiseaseName(item) {
  if (item?.disease_name) return item.disease_name
  const detectionType = item?.detection_type || item?.type
  if (detectionType === 'image') {
    const labels = parseJsonField(item?.label, [])
    if (Array.isArray(labels) && labels.length > 0) {
      const first = String(labels[0])
      return labels.length > 1 ? `${first} 等${labels.length}项` : first
    }
    return '未检测到病虫害'
  }

  const stats = parseJsonField(item?.track_stats, {})
  const totalCounts = stats?.total_counts || stats?.totalCounts || {}
  const entries = Object.entries(totalCounts || {}).filter(([, count]) => Number(count) > 0)
  if (!entries.length) return '未检测到病虫害'

  entries.sort((a, b) => Number(b[1]) - Number(a[1]))
  const [topName, topCount] = entries[0]
  const total = entries.reduce((sum, [, count]) => sum + (Number(count) || 0), 0)
  return `${topName}（${topCount}次，合计${total}次）`
}

function resolveConfidence(item) {
  const detectionType = item?.detection_type || item?.type
  if (detectionType !== 'image') return null

  if (typeof item?.confidence === 'number') {
    return `${(item.confidence * 100).toFixed(1)}%`
  }

  const confidenceList = parseJsonField(item?.confidence, [])
  if (!Array.isArray(confidenceList) || !confidenceList.length) return null
  const numericList = confidenceList
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value))

  if (!numericList.length) return null
  const max = Math.max(...numericList)
  const normalized = max <= 1 ? max * 100 : max
  return `${normalized.toFixed(1)}%`
}

function formatTime(time) {
  if (!time) return ''
  return new Date(time).toLocaleString('zh-CN')
}

async function fetchData() {
  try {
    const params = {
      page: page.value,
      page_size: pageSize,
      type: filter.type || undefined,
      date_from: filter.date_from || undefined,
      date_to: filter.date_to || undefined,
      keyword: filter.keyword || undefined
    }
    const res = await detectionApi.history(params)
    list.value = res.items || []
    total.value = res.total || 0
  } catch (e) { console.error(e) }
}

function viewDetail(id, detectionType) {
  router.push({
    path: `/history/${id}`,
    query: { type: detectionType || 'image' }
  })
}

watch(filter, () => { page.value = 1; fetchData() }, { deep: true })
onMounted(fetchData)
</script>

<style lang="scss" scoped>
.history-page { max-width: 1200px; margin: 0 auto; }
.filters { display: flex; gap: 12px; margin-bottom: 24px; }
.history-list { display: flex; flex-direction: column; gap: 16px; }
.history-item { padding: 20px; }
.item-header { display: flex; gap: 8px; margin-bottom: 12px; }
.type-tag { padding: 4px 12px; background: var(--bg-secondary); border-radius: 4px; font-size: 13px; }
.source-tag { padding: 4px 12px; border-radius: 4px; font-size: 13px; &.local_model { background: #d1fae5; color: #065f46; } &.cloud_ai { background: #dbeafe; color: #1e40af; } }
.disease-name { font-size: 16px; font-weight: 600; margin-bottom: 8px; }
.item-info { display: flex; gap: 16px; font-size: 14px; color: var(--text-secondary); }
.severity { padding: 2px 8px; border-radius: 4px; font-size: 12px; &.high { background: #fee2e2; color: #dc2626; } &.medium { background: #fef3c7; color: #d97706; } &.low { background: #d1fae5; color: #065f46; } }
.item-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border-light); }
.time { font-size: 13px; color: var(--text-muted); }
.btn-detail { background: none; border: none; color: var(--primary); cursor: pointer; font-size: 14px; }
.btn-primary { display: inline-block; padding: 12px 24px; background: var(--primary); color: white; text-decoration: none; border-radius: var(--radius-md); }
</style>
