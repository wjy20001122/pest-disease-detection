<template>
  <div class="history-page">
    <div class="filters">
      <el-select v-model="filter.type" placeholder="检测类型" clearable size="default" style="width: 120px">
        <el-option label="图像" value="image" />
        <el-option label="视频" value="video" />
        <el-option label="摄像头" value="camera" />
      </el-select>
      <el-select v-model="filter.severity" placeholder="严重程度" clearable size="default" style="width: 120px">
        <el-option label="轻微" value="low" />
        <el-option label="中等" value="medium" />
        <el-option label="严重" value="high" />
      </el-select>
    </div>
    
    <div class="history-list" v-if="list.length">
      <div v-for="item in list" :key="item.id" class="history-item card">
        <div class="item-header">
          <span class="type-tag">{{ typeMap[item.detection_type] }}</span>
          <span class="source-tag" :class="item.source">{{ item.source === 'local_model' ? '本地模型' : '云端AI' }}</span>
        </div>
        <div class="item-body">
          <div class="disease-name">{{ item.disease_name || '未检测到病虫害' }}</div>
          <div class="item-info">
            <span v-if="item.confidence">置信度 {{ (item.confidence * 100).toFixed(1) }}%</span>
            <span v-if="item.severity" class="severity" :class="item.severity">{{ severityMap[item.severity] }}</span>
          </div>
        </div>
        <div class="item-footer">
          <span class="time">{{ formatTime(item.created_at) }}</span>
          <button class="btn-detail" @click="viewDetail(item.id)">查看详情 →</button>
        </div>
      </div>
    </div>
    
    <div v-else class="empty">
      <div class="empty-icon">📋</div>
      <p>暂无检测记录</p>
      <router-link to="/detect" class="btn-primary">开始检测</router-link>
    </div>
    
    <el-pagination v-if="total > pageSize" layout="prev, pager, next" :total="total" v-model:current-page="page" :page-size="pageSize" @current-change="fetchData" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { detectionApi } from '@/api'

const router = useRouter()
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const filter = reactive({ type: '', severity: '' })
const typeMap = { image: '图像', video: '视频', camera: '摄像头' }
const severityMap = { high: '严重', medium: '中等', low: '轻微' }

function formatTime(time) {
  if (!time) return ''
  return new Date(time).toLocaleString('zh-CN')
}

async function fetchData() {
  try {
    const params = { page: page.value, page_size: pageSize, ...filter }
    const res = await detectionApi.history(params)
    list.value = res.items || []
    total.value = res.total || 0
  } catch (e) { console.error(e) }
}

function viewDetail(id) { router.push(`/history/${id}`) }

watch(filter, () => { page.value = 1; fetchData() }, { deep: true })
onMounted(fetchData)
</script>

<style lang="scss" scoped>
.history-page { max-width: 900px; margin: 0 auto; }
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
.empty { text-align: center; padding: 64px; color: var(--text-muted); .empty-icon { font-size: 64px; margin-bottom: 16px; } p { margin-bottom: 24px; } }
.btn-primary { display: inline-block; padding: 12px 24px; background: var(--primary); color: white; text-decoration: none; border-radius: var(--radius-md); }
</style>
