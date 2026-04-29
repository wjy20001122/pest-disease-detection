<template>
  <div class="tracking-page">
    <div class="page-header">
      <el-button type="primary" @click="showCreateDialog = true">
        + 创建跟踪任务
      </el-button>
      <div class="filter-group">
        <el-select v-model="filter.status" placeholder="状态" clearable size="default" style="width: 120px">
          <el-option label="进行中" value="active" />
          <el-option label="已解决" value="resolved" />
          <el-option label="已归档" value="archived" />
        </el-select>
      </div>
    </div>

    <!-- 地图区域 -->
    <div class="map-container card">
      <div class="map">
        <button
          v-for="marker in mapMarkers"
          :key="marker.id"
          class="map-marker"
          :class="marker.status"
          :style="{ left: marker.x + '%', top: marker.y + '%' }"
          :title="marker.disease_name"
          @click.stop="viewDetail(marker.id)"
        >
          <span></span>
        </button>
        <div v-if="!mapMarkers.length" class="map-empty">暂无可定位的跟踪任务</div>
      </div>
      <div class="map-legend">
        <span class="legend-item active">● 进行中</span>
        <span class="legend-item resolved">● 已解决</span>
      </div>
    </div>

    <!-- 跟踪列表 -->
    <div class="tracking-list">
      <div v-for="item in list" :key="item.id" class="tracking-item card" @click="viewDetail(item.id)">
        <div class="item-header">
          <span class="disease-name">{{ item.disease_name }}</span>
          <span class="status-badge" :class="item.status">{{ statusMap[item.status] }}</span>
        </div>
        <div class="item-body">
          <div class="info-row">
            <span class="info-item">📍 {{ item.location || '未知位置' }}</span>
          </div>
          <div class="info-row">
            <span class="info-item">🕐 {{ item.update_count || 0 }} 次更新</span>
            <span class="info-item">{{ formatTime(item.last_update) }}</span>
          </div>
        </div>
        <div class="item-progress">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: getProgress(item) + '%' }"></div>
          </div>
          <span class="progress-text">{{ getProgress(item) }}%</span>
        </div>
      </div>

      <div v-if="!list.length" class="empty">
        <div class="empty-icon">📍</div>
        <p>暂无跟踪任务</p>
        <el-button type="primary" @click="showCreateDialog = true">创建第一个任务</el-button>
      </div>
    </div>

    <!-- 创建对话框 -->
    <el-dialog v-model="showCreateDialog" title="创建跟踪任务" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="关联检测">
          <el-select v-model="form.detection_id" placeholder="选择检测记录" filterable style="width: 100%">
            <el-option v-for="d in detections" :key="d.id" :label="d.disease_name || '检测 #' + d.id" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="病虫害名称">
          <el-input v-model="form.disease_name" placeholder="如：稻飞虱" />
        </el-form-item>
        <el-form-item label="严重程度">
          <el-select v-model="form.severity" placeholder="选择严重程度">
            <el-option label="轻微" value="low" />
            <el-option label="中等" value="medium" />
            <el-option label="严重" value="high" />
          </el-select>
        </el-form-item>
        <el-form-item label="位置描述">
          <div class="location-input-row">
            <el-input v-model="form.location" placeholder="如：田中部" />
            <el-button @click="fillCurrentLocation">定位</el-button>
          </div>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="3" placeholder="补充说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 详情对话框 -->
    <el-dialog v-model="showDetailDialog" title="跟踪详情" width="700px">
      <div v-if="current" class="detail-content">
        <div class="detail-header">
          <h3>{{ current.disease_name }}</h3>
          <span class="status-badge" :class="current.status">{{ statusMap[current.status] }}</span>
        </div>
        <div class="detail-info">
          <p><strong>严重程度：</strong>{{ severityMap[current.severity] }}</p>
          <p><strong>位置：</strong>{{ current.location || '未知' }}</p>
          <p><strong>创建时间：</strong>{{ formatTime(current.created_at) }}</p>
        </div>

        <div class="timeline-section">
          <h4>跟踪时间线</h4>
          <div class="timeline">
            <div v-for="update in updates" :key="update.id" class="timeline-item">
              <div class="timeline-dot"></div>
              <div class="timeline-content">
                <div class="timeline-header">
                  <span class="status">{{ update.status }}</span>
                  <span class="time">{{ formatTime(update.created_at) }}</span>
                </div>
                <p class="note">{{ update.note }}</p>
                <img v-if="update.image_url" :src="update.image_url" class="update-image" />
              </div>
            </div>
          </div>
        </div>

        <div class="detail-actions">
          <el-button type="success" @click="handleUpdateStatus('resolved')">标记已解决</el-button>
          <el-button @click="handleAddUpdate">添加更新</el-button>
          <el-button type="danger" plain @click="handleArchive">归档</el-button>
        </div>
      </div>
    </el-dialog>

    <!-- 添加更新对话框 -->
    <el-dialog v-model="showUpdateDialog" title="添加跟踪更新" width="500px">
      <el-form :model="updateForm" label-width="100px">
        <el-form-item label="状态">
          <el-select v-model="updateForm.status">
            <el-option label="监测中" value="monitoring" />
            <el-option label="恶化" value="worsening" />
            <el-option label="好转" value="improving" />
            <el-option label="已处理" value="treated" />
          </el-select>
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="updateForm.note" type="textarea" :rows="4" placeholder="描述当前状态变化" />
        </el-form-item>
        <el-form-item label="上传图片">
          <el-upload drag :auto-upload="false" :on-change="handleImageChange" accept="image/*">
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div>拖拽图片或点击上传</div>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUpdateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleAddUpdateSubmit">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref, reactive, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { trackingApi, detectionApi } from '@/api'

const list = ref([])
const filter = reactive({ status: '' })
const showCreateDialog = ref(false)
const showDetailDialog = ref(false)
const showUpdateDialog = ref(false)
const current = ref(null)
const updates = ref([])
const detections = ref([])
const statusMap = {
  active: '进行中',
  monitoring: '监测中',
  worsening: '恶化',
  improving: '好转',
  treated: '已处理',
  resolved: '已解决',
  archived: '已归档'
}
const severityMap = { high: '严重', medium: '中等', low: '轻微' }

const form = reactive({
  detection_id: null,
  disease_name: '',
  severity: 'medium',
  location: '',
  latitude: null,
  longitude: null,
  notes: ''
})

const updateForm = reactive({
  status: 'monitoring',
  note: '',
  image: null
})

const mapMarkers = computed(() => {
  const located = list.value.filter(item => item.latitude !== null && item.latitude !== undefined && item.longitude !== null && item.longitude !== undefined)
  if (!located.length) return []

  const lats = located.map(item => Number(item.latitude))
  const lngs = located.map(item => Number(item.longitude))
  const minLat = Math.min(...lats)
  const maxLat = Math.max(...lats)
  const minLng = Math.min(...lngs)
  const maxLng = Math.max(...lngs)
  const latSpan = Math.max(maxLat - minLat, 0.001)
  const lngSpan = Math.max(maxLng - minLng, 0.001)

  return located.map(item => ({
    ...item,
    x: 8 + ((Number(item.longitude) - minLng) / lngSpan) * 84,
    y: 92 - ((Number(item.latitude) - minLat) / latSpan) * 84
  }))
})

function formatTime(time) {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

function getProgress(item) {
  if (item.status === 'resolved') return 100
  if (item.status === 'archived') return 100
  const days = item.days_active || 1
  return Math.min(90, days * 5)
}

async function fetchList() {
  try {
    const params = { page: 1, page_size: 50, ...filter }
    const res = await trackingApi.list(params)
    list.value = res.items || []
  } catch (e) { console.error(e) }
}

async function fetchDetections() {
  try {
    const res = await detectionApi.history({ page_size: 100 })
    detections.value = res.items || []
  } catch (e) { console.error(e) }
}

async function handleCreate() {
  try {
    await trackingApi.create(form)
    ElMessage.success('创建成功')
    showCreateDialog.value = false
    Object.assign(form, { detection_id: null, disease_name: '', severity: 'medium', location: '', latitude: null, longitude: null, notes: '' })
    fetchList()
  } catch (e) { ElMessage.error('创建失败') }
}

function fillCurrentLocation() {
  if (!navigator.geolocation) {
    ElMessage.warning('浏览器不支持定位')
    return
  }
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      form.latitude = pos.coords.latitude
      form.longitude = pos.coords.longitude
      if (!form.location) {
        form.location = `${form.latitude.toFixed(5)},${form.longitude.toFixed(5)}`
      }
      ElMessage.success('位置已填充')
    },
    () => ElMessage.error('定位失败')
  )
}

async function viewDetail(id) {
  try {
    const res = await trackingApi.detail(id)
    current.value = res
    updates.value = res.updates || []
    showDetailDialog.value = true
  } catch (e) { ElMessage.error('获取详情失败') }
}

async function handleUpdateStatus(status) {
  if (!current.value) return
  try {
    await trackingApi.update(current.value.id, { status })
    ElMessage.success('更新成功')
    showDetailDialog.value = false
    fetchList()
  } catch (e) { ElMessage.error('更新失败') }
}

function handleAddUpdate() {
  showDetailDialog.value = false
  showUpdateDialog.value = true
}

async function handleAddUpdateSubmit() {
  if (!current.value) return
  try {
    const data = new FormData()
    data.append('status', updateForm.status)
    data.append('note', updateForm.note)
    if (updateForm.image) data.append('image', updateForm.image)
    
    await fetch(`/api/v1/tracking/${current.value.id}/updates`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
      body: data
    })
    
    ElMessage.success('更新已提交')
    showUpdateDialog.value = false
    Object.assign(updateForm, { status: 'monitoring', note: '', image: null })
  } catch (e) { ElMessage.error('提交失败') }
}

function handleImageChange(file) {
  updateForm.image = file.raw
}

function handleArchive() {
  handleUpdateStatus('archived')
}

watch(filter, () => fetchList(), { deep: true })
onMounted(() => {
  fetchList()
  fetchDetections()
})
</script>

<style lang="scss" scoped>
.tracking-page { max-width: 1200px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.filter-group { display: flex; gap: 12px; }

.map-container { padding: 0; overflow: hidden; margin-bottom: 24px; position: relative; }
.map { height: 300px; background: linear-gradient(135deg, #ecfdf5, #eef2ff); position: relative; overflow: hidden; }
.map::before { content: ''; position: absolute; inset: 24px; border: 1px solid rgba(15, 23, 42, 0.08); background-image: linear-gradient(rgba(15, 23, 42, 0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(15, 23, 42, 0.06) 1px, transparent 1px); background-size: 40px 40px; border-radius: var(--radius-md); }
.map-empty { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: var(--text-muted); }
.map-marker { position: absolute; width: 24px; height: 24px; transform: translate(-50%, -50%); border: 0; background: transparent; cursor: pointer; z-index: 2; }
.map-marker span { display: block; width: 14px; height: 14px; margin: 5px; border-radius: 50%; background: var(--primary); box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.2); }
.map-marker.resolved span { background: #6b7280; box-shadow: 0 0 0 4px rgba(107, 114, 128, 0.18); }
.map-marker.archived span { background: #9ca3af; box-shadow: 0 0 0 4px rgba(156, 163, 175, 0.16); }
.map-marker.worsening span { background: #dc2626; box-shadow: 0 0 0 4px rgba(220, 38, 38, 0.18); }
.map-legend { position: absolute; bottom: 12px; right: 12px; background: white; padding: 8px 12px; border-radius: var(--radius-sm); box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.legend-item { margin-right: 16px; font-size: 13px; &.active { color: var(--primary); } &.resolved { color: var(--text-muted); } }

.tracking-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.tracking-item { cursor: pointer; transition: box-shadow 0.2s; &:hover { box-shadow: var(--shadow-md); } }
.item-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.disease-name { font-size: 16px; font-weight: 600; }
.status-badge { padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 500; &.active, &.monitoring, &.improving, &.treated { background: #d1fae5; color: #065f46; } &.worsening { background: #fee2e2; color: #991b1b; } &.resolved { background: #e5e7eb; color: #374151; } &.archived { background: #f3f4f6; color: #9ca3af; } }

.item-body { margin-bottom: 16px; }
.info-row { display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px; color: var(--text-secondary); }

.item-progress { display: flex; align-items: center; gap: 8px; }
.progress-bar { flex: 1; height: 6px; background: var(--bg-secondary); border-radius: 3px; overflow: hidden; }
.progress-fill { height: 100%; background: var(--primary); border-radius: 3px; transition: width 0.3s; }
.progress-text { font-size: 12px; color: var(--text-muted); min-width: 40px; text-align: right; }

.empty { text-align: center; padding: 64px; color: var(--text-muted); .empty-icon { font-size: 64px; margin-bottom: 16px; } p { margin-bottom: 24px; } }

.detail-content { padding: 0 8px; }
.detail-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; h3 { margin: 0; } }
.detail-info { margin-bottom: 24px; p { margin: 8px 0; } }

.timeline-section { margin-bottom: 24px; h4 { margin-bottom: 16px; } }
.timeline { position: relative; padding-left: 24px; &::before { content: ''; position: absolute; left: 6px; top: 0; bottom: 0; width: 2px; background: var(--border-light); } }
.timeline-item { position: relative; margin-bottom: 24px; }
.timeline-dot { position: absolute; left: -22px; top: 4px; width: 12px; height: 12px; background: var(--primary); border-radius: 50%; border: 2px solid white; }
.timeline-content { background: var(--bg-secondary); padding: 12px 16px; border-radius: var(--radius-md); }
.timeline-header { display: flex; justify-content: space-between; margin-bottom: 8px; .status { font-weight: 500; font-size: 14px; } .time { font-size: 12px; color: var(--text-muted); } }
.note { font-size: 14px; color: var(--text-secondary); margin: 0; }
.update-image { max-width: 200px; margin-top: 8px; border-radius: var(--radius-sm); }

.detail-actions { display: flex; gap: 12px; margin-top: 24px; }
.location-input-row { display: flex; gap: 8px; width: 100%; }
</style>
