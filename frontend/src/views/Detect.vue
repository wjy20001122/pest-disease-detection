<template>
  <div class="detect-page">
    <div class="detect-tabs">
      <button :class="{ active: tab === 'image' }" @click="switchTab('image')">图像检测</button>
      <button :class="{ active: tab === 'video' }" @click="switchTab('video')">视频检测</button>
    </div>

    <div class="detect-content" v-if="tab === 'image' && !imageResult">
      <div class="upload-section">
        <input ref="fileInput" type="file" accept="image/jpeg,image/png,image/webp" @change="handleFileChange" hidden />
        <div v-if="!file" class="upload-area" @click="triggerUpload" @dragover.prevent @drop.prevent="handleDrop">
          <div class="upload-icon">🖼️</div>
          <div class="upload-text">
            <p>点击或拖拽上传图片</p>
            <p class="hint">支持 JPG、PNG、WebP</p>
          </div>
        </div>

        <div v-if="imagePreviewUrl" class="preview-card">
          <div class="preview-head">
            <p class="preview-title">当前图片预览（未检测）</p>
            <button class="btn-outline" @click="triggerUpload">更换图像</button>
          </div>
          <img :src="imagePreviewUrl" alt="当前上传图片预览" class="preview-image" />
        </div>

        <div class="model-section" v-if="isAdmin">
          <p class="section-label">管理员模型直连（不走AI路由）</p>
          <div class="model-cards">
            <div
              v-for="model in models"
              :key="model.modelKey"
              :class="['model-card', { active: selectedModel === model.modelKey }]"
              @click="selectedModel = model.modelKey"
            >
              <div class="model-name">{{ model.modelName }}</div>
              <div class="model-classes">
                <span v-for="(cls, idx) in (model.classes || []).slice(0, 4)" :key="idx" class="class-tag">
                  {{ cls }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div class="selection-section">
          <p class="section-label">{{ isAdmin ? '分析约束（可选）' : '选择分析约束（必填）' }}</p>
          <div class="selection-row">
            <el-select v-model="cropType" placeholder="作物类型" style="width: 180px">
              <el-option label="玉米" value="玉米" />
              <el-option label="小麦" value="小麦" />
              <el-option label="水稻" value="水稻" />
            </el-select>
            <el-select v-model="category" placeholder="病害/虫害" style="width: 180px">
              <el-option label="病害" value="病害" />
              <el-option label="虫害" value="虫害" />
            </el-select>
          </div>
          <div class="selection-tip">AI 与知识库会严格按你选择的作物与类别分析，不会越界给结论。</div>
        </div>

        <div class="location-section">
          <p class="section-label">位置信息（可选）</p>
          <div class="location-btns">
            <button class="btn-outline" @click="getLocation" :disabled="loading">
              {{ location.lat ? '已获取位置' : '获取当前位置' }}
            </button>
            <span v-if="location.county || location.address" class="address">
              {{ location.county ? `县区：${location.county}` : location.address }}
            </span>
          </div>
          <div v-if="location.address && location.county && location.address !== location.county" class="address-detail">
            {{ location.address }}
          </div>
          <div v-if="environment.weather || environment.temperature !== null || environment.humidity !== null" class="environment-card">
            <span v-if="environment.weather">{{ environment.weather }}</span>
            <span v-if="environment.temperature !== null">{{ environment.temperature }}℃</span>
            <span v-if="environment.humidity !== null">湿度 {{ environment.humidity }}%</span>
          </div>
        </div>

        <button class="detect-btn" @click="startImageDetect" :disabled="!canDetect || loading">
          {{ loading ? '检测中...' : '开始检测' }}
        </button>
      </div>
    </div>

    <div class="detect-content" v-if="tab === 'video' && !videoResult && !videoProcessing">
      <div class="upload-section">
        <input ref="videoFileInput" type="file" accept="video/mp4,video/avi,video/quicktime" @change="handleVideoChange" hidden />
        <div v-if="!videoFile" class="upload-area" @click="triggerVideoUpload" @dragover.prevent @drop.prevent="handleVideoDrop">
          <div class="upload-icon">🎥</div>
          <div class="upload-text">
            <p>点击或拖拽上传视频</p>
            <p class="hint">支持 MP4、AVI、MOV</p>
          </div>
        </div>
        <div v-if="videoPreviewUrl" class="preview-card">
          <div class="preview-head">
            <p class="preview-title">当前视频预览（未处理）</p>
            <button class="btn-outline" @click="triggerVideoUpload">更换视频</button>
          </div>
          <video :src="videoPreviewUrl" controls class="preview-video" />
        </div>
        <div class="model-section">
          <p class="section-label">本地模型选择</p>
          <div class="model-cards">
            <div
              v-for="model in models"
              :key="`video-${model.modelKey}`"
              :class="['model-card', { active: selectedVideoModel === model.modelKey }]"
              @click="selectedVideoModel = model.modelKey"
            >
              <div class="model-name">{{ model.modelName }}</div>
              <div class="model-classes">
                <span v-for="(cls, idx) in (model.classes || []).slice(0, 4)" :key="idx" class="class-tag">
                  {{ cls }}
                </span>
              </div>
            </div>
          </div>
          <div class="selection-tip">视频检测仅使用本地模型，不走云端分析。</div>
        </div>
        <button class="detect-btn" @click="startVideoDetect" :disabled="!videoFile || loading">
          {{ loading ? '处理中...' : '开始处理视频' }}
        </button>
      </div>
    </div>

    <div class="detect-content" v-if="tab === 'video' && videoProcessing">
      <div class="video-processing">
        <div class="processing-icon">🎥</div>
        <h3>视频处理中</h3>
        <p>正在分析视频中的病虫害，请稍候...</p>
        <div class="progress-section">
          <el-progress :percentage="videoProgress" :stroke-width="12" />
          <p class="progress-text">{{ videoProgressText }}</p>
        </div>
        <div class="processing-stats" v-if="videoStats">
          <span>已处理帧：{{ videoStats.frame_count || 0 }}</span>
          <span>跟踪目标：{{ videoStats.total_tracks || 0 }}</span>
        </div>
        <button class="btn-outline" @click="cancelVideoProcessing">取消</button>
      </div>
    </div>

    <div class="result-section" v-if="tab === 'image' && imageResult">
      <div class="result-card">
        <div class="result-header">
          <span class="source-tag" :class="imageResult.source || 'cloud_ai'">
            <template v-if="imageResult.source === 'local_model'">本地模型检测</template>
            <template v-else-if="imageResult.source === 'confirmed_no_pest'">AI确认无病虫害</template>
            <template v-else>AI/知识库分析</template>
          </span>
          <button class="btn-ghost" @click="resetImage">重新检测</button>
        </div>
        <div class="result-meta">
          <span>作物：{{ cropType }}</span>
          <span>类别：{{ category }}</span>
          <span v-if="imageResult.selected_model">模型：{{ imageResult.selected_model }}</span>
        </div>
        <el-alert
          v-if="imageResult.message === '与用户选择不一致'"
          title="图像特征与所选作物/类别不一致，请调整选择后重试"
          type="warning"
          :closable="false"
          show-icon
          style="margin-bottom: 12px"
        />
        <div class="image-compare" v-if="imageResult.input_image || imageResult.file_path || imageResult.output_image">
          <div class="image-panel">
            <p class="image-title">上传原图</p>
            <img :src="imageResult.input_image || imageResult.file_path" alt="上传原图" />
          </div>
          <div class="image-panel" v-if="imageResult.output_image">
            <p class="image-title">检测结果图</p>
            <img :src="imageResult.output_image" alt="检测结果图" />
          </div>
        </div>
        <div v-if="!imageResult.has_pest" class="no-pest-message">
          <div class="no-pest-icon">🌿</div>
          <h3>未检测到病虫害</h3>
          <p>{{ imageResult.message || '当前图像在所选范围内未识别到病虫害特征' }}</p>
        </div>
        <template v-else>
          <div class="detection-list" v-if="detectionItems.length">
            <div v-for="(item, index) in detectionItems" :key="index" class="detection-item">
              <div class="detection-header">
                <span class="pest-name">{{ item.name }}</span>
                <span class="pest-count">x{{ item.count }}</span>
              </div>
              <div class="detection-info">
                <span class="confidence">置信度 {{ item.confidence }}</span>
              </div>
            </div>
          </div>
          <div class="disease-list" v-if="imageResult.merged_result?.diseases?.length">
            <h3>病虫害详情</h3>
            <div v-for="(disease, index) in imageResult.merged_result.diseases" :key="index" class="disease-item">
              <div class="disease-name">{{ disease.name }}</div>
              <div class="disease-info">
                <span class="confidence">置信度 {{ ((disease.confidence || 0) * 100).toFixed(1) }}%</span>
              </div>
              <div v-if="disease.knowledge" class="disease-desc">
                <p><strong>形状：</strong>{{ disease.knowledge.shape }}</p>
                <p><strong>颜色：</strong>{{ disease.knowledge.color }}</p>
                <p><strong>大小：</strong>{{ disease.knowledge.size }}</p>
                <p><strong>症状：</strong>{{ disease.knowledge.symptoms }}</p>
                <p><strong>防治：</strong>{{ disease.knowledge.prevention }}</p>
              </div>
              <div v-else-if="disease.symptoms" class="disease-desc">
                <p><strong>症状：</strong>{{ disease.symptoms }}</p>
                <p v-if="disease.prevention"><strong>防治：</strong>{{ disease.prevention }}</p>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <div class="result-section" v-if="tab === 'video' && videoResult">
      <div class="result-card">
        <div class="result-header">
          <span class="source-tag local_model">视频检测结果</span>
          <button class="btn-ghost" @click="resetVideo">重新检测</button>
        </div>
        <div class="result-meta">
          <span>模型：{{ videoResult.selected_model || selectedVideoModel }}</span>
          <span>来源：本地模型</span>
        </div>
        <div class="video-result">
          <div class="video-player">
            <video v-if="videoResult.video_url" :src="videoResult.video_url" controls autoplay />
            <div v-else class="video-placeholder">
              <p>视频处理完成</p>
            </div>
          </div>
          <div class="video-stats" v-if="videoResult.stats">
            <h3>检测统计</h3>
            <div class="stats-grid stats-grid-compact">
              <div class="stat-box">
                <span class="stat-num">{{ totalDetectedPests }}</span>
                <span class="stat-desc">病害/虫害总数</span>
              </div>
            </div>
            <div v-if="videoResult.detections?.length" class="class-counts">
              <div v-for="(item, index) in videoResult.detections" :key="`class-count-${index}`" class="class-count-item">
                <span class="class-name">{{ item.class }}</span>
                <span class="class-value">{{ item.trackCount }} 只</span>
              </div>
            </div>
          </div>
          <div class="detection-summary" v-if="videoResult.detections?.length">
            <h3>检测详情</h3>
            <div class="detection-list">
              <div v-for="(item, index) in videoResult.detections" :key="index" class="detection-item">
                <div class="detection-header">
                  <span class="pest-name">{{ item.class }}</span>
                <span class="pest-count">目标 {{ item.trackCount }}</span>
              </div>
              <div class="detection-info">
                <span class="confidence">最高置信度 {{ (item.maxConfidence * 100).toFixed(1) }}%</span>
                <span class="confidence">检测次数 {{ item.hits }}</span>
              </div>
            </div>
          </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { detectionApi, environmentApi, mlApi } from '@/api'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const isAdmin = computed(() => userStore.user?.role === 'admin')
const tab = ref('image')
const loading = ref(false)
const models = ref([{ modelKey: 'pest', modelName: '默认模型', classes: [] }])
const selectedModel = ref('pest')
const selectedVideoModel = ref('pest')

const file = ref(null)
const fileInput = ref(null)
const cropType = ref('')
const category = ref('')
const location = ref({ lat: null, lng: null, address: '', county: '' })
const environment = ref({ weather: '', temperature: null, humidity: null })
const imageResult = ref(null)
const imagePreviewUrl = ref('')

const videoFile = ref(null)
const videoFileInput = ref(null)
const videoResult = ref(null)
const videoProcessing = ref(false)
const videoProgress = ref(0)
const videoProgressText = ref('')
const videoStats = ref(null)
const videoSessionId = ref(null)
const videoPreviewUrl = ref('')
const videoLiveDetections = ref([])
const VIDEO_TASK_STORAGE_KEY = 'detect_video_active_task'
let videoPollingActive = false
let videoPollingSessionId = ''

const canDetect = computed(() => {
  if (isAdmin.value) return Boolean(file.value && selectedModel.value)
  return Boolean(file.value && cropType.value && category.value)
})

const detectionItems = computed(() => {
  if (!imageResult.value?.labels?.length) return []
  const counts = {}
  imageResult.value.labels.forEach((label, idx) => {
    if (!counts[label]) {
      counts[label] = { name: label, count: 0, confidence: '0%' }
    }
    counts[label].count++
    const confRaw = imageResult.value.confidences?.[idx]
    if (typeof confRaw === 'number') {
      counts[label].confidence = `${Math.round(confRaw <= 1 ? confRaw * 100 : confRaw)}%`
    } else if (typeof confRaw === 'string') {
      counts[label].confidence = confRaw
    }
  })
  return Object.values(counts)
})

const totalDetectedPests = computed(() => {
  const detections = videoResult.value?.detections || []
  if (!detections.length) return 0
  return detections.reduce((sum, item) => sum + (Number(item.trackCount) || 0), 0)
})

function switchTab(next) {
  tab.value = next
}

function triggerUpload() {
  if (fileInput.value) {
    fileInput.value.value = ''
  }
  fileInput.value?.click()
}

function handleFileChange(e) {
  const selected = e.target.files?.[0]
  if (selected && selected.type.startsWith('image/')) {
    file.value = selected
  }
}

function handleDrop(e) {
  const selected = e.dataTransfer.files?.[0]
  if (selected && selected.type.startsWith('image/')) file.value = selected
}

function triggerVideoUpload() {
  videoFileInput.value?.click()
}

function handleVideoChange(e) {
  const selected = e.target.files?.[0]
  if (selected) videoFile.value = selected
}

function handleVideoDrop(e) {
  const selected = e.dataTransfer.files?.[0]
  if (selected && selected.type.startsWith('video/')) videoFile.value = selected
}

function getLocation() {
  if (!navigator.geolocation) {
    fetchEnvironmentByIp(true)
    return
  }
  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      location.value.lat = pos.coords.latitude
      location.value.lng = pos.coords.longitude
      location.value.address = `${location.value.lat.toFixed(5)},${location.value.lng.toFixed(5)}`
      location.value.county = ''
      await fetchEnvironment()
      ElMessage.success('位置已获取')
    },
    async (error) => {
      await fetchEnvironmentByIp(true)
      const messageByCode = {
        1: '定位权限被拒绝，已尝试IP定位',
        2: '无法获取当前位置，已尝试IP定位',
        3: '定位超时，已尝试IP定位'
      }
      ElMessage.warning(messageByCode[error?.code] || '获取位置失败，已尝试IP定位')
    },
    { enableHighAccuracy: true, timeout: 12000, maximumAge: 300000 }
  )
}

async function fetchEnvironment() {
  if (!location.value.lat || !location.value.lng) return
  try {
    const res = await environmentApi.current({ latitude: location.value.lat, longitude: location.value.lng })
    location.value.address = res.address || `${location.value.lat.toFixed(5)},${location.value.lng.toFixed(5)}`
    location.value.county = res.county || res.district || extractCountyFromAddress(res.address)
    environment.value = {
      weather: res.weather || '',
      temperature: res.temperature ?? null,
      humidity: res.humidity ?? null
    }
  } catch {
    location.value.address = `${location.value.lat.toFixed(5)},${location.value.lng.toFixed(5)}`
    location.value.county = ''
    environment.value = { weather: '', temperature: null, humidity: null }
  }
}

async function fetchEnvironmentByIp(showToast = false) {
  try {
    const res = await environmentApi.ipCurrent()
    location.value.address = res.address || 'IP定位成功'
    location.value.county = res.county || res.district || ''
    environment.value = {
      weather: res.weather || '',
      temperature: res.temperature ?? null,
      humidity: res.humidity ?? null
    }
    const hasAnyData = Boolean(location.value.county || location.value.address || environment.value.weather || environment.value.temperature !== null || environment.value.humidity !== null)
    if (showToast && hasAnyData) {
      ElMessage.success('已通过IP获取位置')
    } else if (showToast) {
      ElMessage.warning('IP定位未返回有效地址，请检查后端地图/天气配置')
    }
  } catch {
    if (showToast) {
      ElMessage.error('定位失败，请检查浏览器定位权限')
    }
  }
}

function buildVideoDetectionSummary(statusPayload) {
  const summaryMap = {}
  const uniqueTrackCounts = statusPayload?.unique_track_counts || {}
  const totalCounts = statusPayload?.total_counts || {}
  const tailDetections = Array.isArray(statusPayload?.detections) ? statusPayload.detections : []

  const countSource = Object.keys(uniqueTrackCounts).length ? uniqueTrackCounts : totalCounts
  Object.entries(countSource).forEach(([className, countValue]) => {
    summaryMap[className] = {
      class: className,
      trackCount: Number(countValue) || 0,
      hits: 0,
      maxConfidence: 0
    }
  })

  tailDetections.forEach((det) => {
    const className = det?.class || 'unknown'
    if (!summaryMap[className]) {
      summaryMap[className] = { class: className, trackCount: 0, hits: 0, maxConfidence: 0 }
    }
    summaryMap[className].hits += 1
    summaryMap[className].maxConfidence = Math.max(summaryMap[className].maxConfidence, Number(det?.confidence) || 0)
  })

  return Object.values(summaryMap).sort((a, b) => b.trackCount - a.trackCount || b.hits - a.hits)
}

function getRequestErrorMessage(error, fallback = '操作失败，请稍后重试') {
  return error?.response?.data?.detail || error?.message || fallback
}

function saveActiveVideoTask() {
  if (!videoSessionId.value) return
  localStorage.setItem(
    VIDEO_TASK_STORAGE_KEY,
    JSON.stringify({
      session_id: videoSessionId.value,
      selected_model: selectedVideoModel.value,
      updated_at: Date.now()
    })
  )
}

function clearActiveVideoTask() {
  localStorage.removeItem(VIDEO_TASK_STORAGE_KEY)
}

async function pollVideoTask(sessionId, modelKey, notifyOnComplete = true) {
  if (!sessionId) return
  if (videoPollingActive && videoPollingSessionId === sessionId) return
  videoPollingActive = true
  videoPollingSessionId = sessionId

  videoProcessing.value = true
  videoSessionId.value = sessionId
  videoProgressText.value = '任务排队中，等待 worker 处理...'
  saveActiveVideoTask()

  try {
    let pollCount = 0
    let stalledRounds = 0
    let stallWarningShown = false
    let lastFrameCount = -1
    let terminalReached = false

    while (videoPollingActive && videoPollingSessionId === sessionId) {
      await new Promise(resolve => setTimeout(resolve, 1000))
      const statusRes = await detectionApi.videoStatus(sessionId)
      const status = statusRes.status

      if (status === 'queued') {
        videoProgressText.value = '任务排队中，等待 worker 处理...'
      }
      if (statusRes.progress !== undefined) videoProgress.value = Math.round(statusRes.progress)
      if (statusRes.frame_count !== undefined && status !== 'queued') {
        videoProgressText.value = `已处理 ${statusRes.frame_count} 帧`
      }
      videoStats.value = {
        frame_count: statusRes.frame_count || 0,
        total_counts: statusRes.total_counts || {},
        total_tracks: statusRes.total_tracks || 0,
        unique_track_counts: statusRes.unique_track_counts || {}
      }
      videoLiveDetections.value = Array.isArray(statusRes.detections) ? statusRes.detections : []
      saveActiveVideoTask()

      if (statusRes.frame_count === lastFrameCount && status === 'processing') {
        stalledRounds += 1
      } else {
        stalledRounds = 0
        lastFrameCount = statusRes.frame_count
      }

      if (!stallWarningShown && stalledRounds >= 8) {
        stallWarningShown = true
        ElMessage.warning('视频处理进度暂未变化，请稍候或检查 Celery worker 状态')
      }

      if (status === 'failed') {
        terminalReached = true
        clearActiveVideoTask()
        throw new Error(statusRes.error_message || '视频处理失败')
      }
      if (status === 'stopped') {
        terminalReached = true
        clearActiveVideoTask()
        ElMessage.info('视频处理已停止')
        return
      }
      if (statusRes.is_processing === false || status === 'completed') {
        terminalReached = true
        break
      }

      pollCount += 1
      if (pollCount >= 180) {
        throw new Error('视频任务轮询超时，请稍后重试')
      }
    }

    if (!videoPollingActive || videoPollingSessionId !== sessionId) {
      return
    }

    if (!terminalReached) {
      return
    }

    const finalStatus = await detectionApi.videoStatus(sessionId)
    if (finalStatus.status === 'failed') {
      clearActiveVideoTask()
      throw new Error(finalStatus.error_message || '视频处理失败')
    }
    if (finalStatus.status === 'stopped') {
      clearActiveVideoTask()
      ElMessage.info('视频处理已停止')
      return
    }
    if (finalStatus.is_processing === true && finalStatus.status !== 'completed') {
      return
    }

    const streamUrl = detectionApi.videoStream(sessionId)
    videoLiveDetections.value = Array.isArray(finalStatus.detections) ? finalStatus.detections : []
    videoResult.value = {
      video_url: streamUrl,
      selected_model: finalStatus.selected_model || modelKey || selectedVideoModel.value,
      stats: {
        total_counts: finalStatus.total_counts || {},
        total_tracks: finalStatus.total_tracks || 0,
        frame_count: finalStatus.frame_count || 0,
        unique_track_counts: finalStatus.unique_track_counts || {}
      },
      detections: buildVideoDetectionSummary(finalStatus)
    }
    clearActiveVideoTask()
    if (notifyOnComplete) ElMessage.success('视频处理完成')
  } finally {
    if (videoPollingSessionId === sessionId) {
      videoPollingActive = false
      videoPollingSessionId = ''
      videoProcessing.value = false
      loading.value = false
    }
  }
}

function extractCountyFromAddress(addressText = '') {
  const value = String(addressText || '')
  if (!value) return ''
  const match = value.match(/([\u4e00-\u9fa5A-Za-z]+(?:县|区|旗))/)
  return match ? match[1] : ''
}

async function startImageDetect() {
  if (!canDetect.value) {
    ElMessage.warning(isAdmin.value ? '请先上传图片并选择模型' : '请先上传图片并选择作物与病虫害类别')
    return
  }
  loading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file.value)
    const params = {}
    if (cropType.value) params.crop_type = cropType.value
    if (category.value) params.category = category.value
    if (isAdmin.value) params.model_key = selectedModel.value
    if (location.value.lat) {
      params.latitude = location.value.lat
      params.longitude = location.value.lng
      params.address = location.value.address || ''
      params.weather = environment.value.weather || ''
      if (environment.value.temperature !== null) params.temperature = environment.value.temperature
      if (environment.value.humidity !== null) params.humidity = environment.value.humidity
    }
    imageResult.value = await detectionApi.image(formData, params)
  } catch {
    ElMessage.error('检测失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

async function startVideoDetect() {
  if (!videoFile.value || !selectedVideoModel.value) {
    ElMessage.warning('请先上传视频并选择本地模型')
    return
  }
  loading.value = true
  videoProcessing.value = true
  videoProgress.value = 0
  videoProgressText.value = '上传视频中...'
  videoStats.value = null
  try {
    const formData = new FormData()
    formData.append('file', videoFile.value)
    const uploadRes = await detectionApi.video(formData, { model_key: selectedVideoModel.value })
    await pollVideoTask(uploadRes.session_id, selectedVideoModel.value, true)
  } catch (error) {
    ElMessage.error(getRequestErrorMessage(error, '视频处理失败，请重试'))
  } finally {
    loading.value = false
  }
}

async function cancelVideoProcessing() {
  if (videoSessionId.value) {
    try {
      await detectionApi.stopVideo(videoSessionId.value)
    } catch {}
  }
  videoProcessing.value = false
  videoPollingActive = false
  videoPollingSessionId = ''
  videoSessionId.value = null
  videoLiveDetections.value = []
  videoStats.value = null
  clearActiveVideoTask()
}

function resetImage() {
  imageResult.value = null
  file.value = null
  if (fileInput.value) fileInput.value.value = ''
}

function resetVideo() {
  videoResult.value = null
  videoFile.value = null
  videoSessionId.value = null
  videoLiveDetections.value = []
  clearActiveVideoTask()
}

async function loadModelsForAdmin() {
  try {
    const res = await mlApi.getModels()
    if (res?.data?.models?.length) {
      models.value = res.data.models
      if (!models.value.some((item) => item.modelKey === selectedModel.value)) {
        selectedModel.value = res.data.models[0].modelKey
      }
      if (!models.value.some((item) => item.modelKey === selectedVideoModel.value)) {
        selectedVideoModel.value = res.data.models[0].modelKey
      }
    }
  } catch {
    models.value = [{ modelKey: 'pest', modelName: '默认模型', classes: [] }]
    selectedModel.value = 'pest'
    selectedVideoModel.value = 'pest'
  }
}

onMounted(() => {
  loadModelsForAdmin()
  const raw = localStorage.getItem(VIDEO_TASK_STORAGE_KEY)
  if (!raw) return
  try {
    const saved = JSON.parse(raw)
    const savedSessionId = saved?.session_id
    if (!savedSessionId) return
    if (saved?.selected_model) selectedVideoModel.value = saved.selected_model
    tab.value = 'video'
    pollVideoTask(savedSessionId, saved?.selected_model || selectedVideoModel.value, false).catch(() => {})
  } catch {}
})

watch(isAdmin, (value) => {
  if (value) loadModelsForAdmin()
})

watch(file, (next, prev) => {
  if (imagePreviewUrl.value) {
    URL.revokeObjectURL(imagePreviewUrl.value)
    imagePreviewUrl.value = ''
  }
  if (next) imagePreviewUrl.value = URL.createObjectURL(next)
  if (prev && !next && fileInput.value) fileInput.value.value = ''
})

watch(videoFile, (next, prev) => {
  if (videoPreviewUrl.value) {
    URL.revokeObjectURL(videoPreviewUrl.value)
    videoPreviewUrl.value = ''
  }
  if (next) videoPreviewUrl.value = URL.createObjectURL(next)
  if (prev && !next && videoFileInput.value) videoFileInput.value.value = ''
})

watch(videoProcessing, (processing) => {
  if (!processing) {
    return
  }
})

onUnmounted(() => {
  videoPollingActive = false
  if (imagePreviewUrl.value) URL.revokeObjectURL(imagePreviewUrl.value)
  if (videoPreviewUrl.value) URL.revokeObjectURL(videoPreviewUrl.value)
})
</script>

<style scoped lang="scss">
.detect-page { max-width: 1200px; margin: 0 auto; }
.detect-tabs { display: flex; gap: 8px; margin-bottom: 12px; padding: 8px; border-radius: var(--radius-md); border: 1px solid var(--border-light); background: var(--bg-primary);
  button { flex: 1; padding: 10px 12px; border: 1px solid transparent; background: transparent; border-radius: var(--radius-sm); cursor: pointer; font-size: 13px; color: var(--text-secondary); transition: all 0.2s; &.active { background: color-mix(in srgb, var(--primary) 12%, transparent); color: var(--text-primary); border-color: color-mix(in srgb, var(--primary) 40%, transparent); } }
}
.detect-content { background: var(--bg-primary); border-radius: var(--radius-md); border: 1px solid var(--border-light); padding: 14px; }
.upload-section { display: grid; gap: 14px; }
.upload-area { border: 1px dashed var(--border); border-radius: var(--radius-md); padding: 24px; text-align: center; cursor: pointer; transition: all 0.2s; &:hover { border-color: var(--primary); background: var(--bg-secondary); } }
.upload-icon { font-size: 48px; margin-bottom: 16px; }
.upload-text { color: var(--text-secondary); p { margin: 8px 0; } .hint { font-size: 13px; color: var(--text-muted); } }
.preview-card { border: 1px solid var(--border-light); border-radius: var(--radius-md); background: var(--bg-secondary); overflow: hidden; }
.preview-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 12px; border-bottom: 1px solid var(--border-light); }
.preview-title { margin: 0; font-size: 13px; color: var(--text-secondary); }
.preview-image { display: block; width: 100%; max-height: 380px; object-fit: contain; background: #111827; }
.preview-video { display: block; width: 100%; max-height: 420px; background: #000; }
.model-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.model-card { padding: 16px; background: var(--bg-secondary); border: 2px solid transparent; border-radius: var(--radius-md); cursor: pointer; transition: all 0.2s;
  &:hover { border-color: var(--primary-light); }
  &.active { border-color: var(--primary); background: var(--primary-light); }
}
.model-name { font-weight: 600; margin-bottom: 8px; }
.model-classes { display: flex; flex-wrap: wrap; gap: 4px; }
.class-tag { font-size: 11px; padding: 2px 8px; background: var(--bg-primary); border-radius: 4px; color: var(--text-secondary); }
.selection-row { display: flex; gap: 12px; flex-wrap: wrap; }
.selection-tip { margin-top: 8px; font-size: 12px; color: var(--text-muted); }
.section-label { font-size: 14px; color: var(--text-secondary); margin-bottom: 12px; }
.location-btns { display: flex; align-items: center; gap: 12px; }
.address { font-size: 13px; color: var(--text-secondary); }
.address-detail { margin-top: 8px; font-size: 12px; color: var(--text-muted); }
.environment-card { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; font-size: 13px; color: var(--text-secondary); span { padding: 4px 8px; border-radius: var(--radius-sm); background: var(--bg-secondary); } }
.detect-btn { width: 100%; margin-top: 4px; padding: 12px; background: var(--primary); color: white; border: none; border-radius: var(--radius-sm); font-size: 14px; font-weight: 500; cursor: pointer; &:disabled { opacity: 0.6; cursor: not-allowed; } &:hover:not(:disabled) { background: var(--primary-dark); } }
.btn-outline { padding: 8px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: transparent; cursor: pointer; }
.result-card { background: var(--bg-primary); border-radius: var(--radius-lg); border: 1px solid var(--border-light); padding: 24px; }
.result-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.source-tag { padding: 6px 16px; border-radius: 20px; font-size: 14px; font-weight: 500; &.local_model { background: #d1fae5; color: #065f46; } &.cloud_ai, &.hybrid, &.no_pest, &.confirmed_no_pest, &.video { background: #dbeafe; color: #1e40af; } }
.result-meta { display: flex; gap: 16px; margin-bottom: 12px; font-size: 13px; color: var(--text-secondary); flex-wrap: wrap; }
.image-compare { margin-bottom: 16px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.image-panel { background: var(--bg-secondary); border: 1px solid var(--border-light); border-radius: var(--radius-md); overflow: hidden; }
.image-title { margin: 0; padding: 10px 12px; font-size: 13px; color: var(--text-secondary); border-bottom: 1px solid var(--border-light); }
.image-panel img { display: block; width: 100%; max-height: 360px; object-fit: contain; background: #111827; }
.btn-ghost { padding: 8px 16px; background: transparent; border: 1px solid var(--border); border-radius: var(--radius-md); cursor: pointer; &:hover { background: var(--bg-secondary); } }
.detection-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; margin-bottom: 20px; }
.detection-item { padding: 16px; background: var(--bg-secondary); border-radius: var(--radius-md); }
.detection-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.pest-name { font-weight: 600; }
.pest-count { background: var(--primary); color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px; }
.detection-info { display: flex; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.confidence { color: var(--primary); font-weight: 500; font-size: 13px; }
.disease-list, .ai-analysis { margin-top: 16px; h3 { font-size: 16px; margin-bottom: 12px; } }
.disease-item { padding: 16px; background: var(--bg-secondary); border-radius: var(--radius-md); margin-bottom: 12px; }
.disease-name { font-size: 16px; font-weight: 600; margin-bottom: 8px; }
.disease-desc { font-size: 14px; color: var(--text-secondary); p { margin: 6px 0; } }
.no-pest-message { text-align: center; padding: 48px 24px; .no-pest-icon { font-size: 64px; margin-bottom: 16px; } h3 { font-size: 20px; margin-bottom: 8px; } p { color: var(--text-secondary); margin-bottom: 8px; } }
.video-processing { text-align: center; padding: 24px; .processing-icon { font-size: 64px; margin-bottom: 16px; } h3 { font-size: 20px; margin-bottom: 8px; } p { color: var(--text-secondary); margin-bottom: 24px; } }
.progress-section { max-width: 400px; margin: 0 auto 24px; .progress-text { font-size: 13px; color: var(--text-muted); margin-top: 8px; } }
.processing-stats { display: flex; justify-content: center; gap: 24px; margin-bottom: 24px; font-size: 14px; color: var(--text-secondary); }
.video-player { background: #000; border-radius: var(--radius-lg); overflow: hidden; margin-bottom: 20px; video { width: 100%; display: block; max-height: 500px; } .video-placeholder { padding: 48px; text-align: center; color: var(--text-muted); } }
.video-stats { padding: 16px; background: var(--bg-secondary); border-radius: var(--radius-md); margin-bottom: 16px; h3 { font-size: 16px; margin-bottom: 12px; } .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; } .stats-grid-compact { grid-template-columns: 1fr; max-width: 280px; } .stat-box { text-align: center; .stat-num { font-size: 28px; font-weight: 700; color: var(--primary); display: block; } .stat-desc { font-size: 13px; color: var(--text-muted); } } }
.class-counts { margin-top: 12px; display: grid; gap: 8px; }
.class-count-item { display: flex; justify-content: space-between; align-items: center; background: var(--bg-primary); border: 1px solid var(--border-light); border-radius: var(--radius-sm); padding: 8px 12px; }
.class-name { font-size: 14px; color: var(--text-primary); font-weight: 600; }
.class-value { font-size: 14px; color: var(--primary); font-weight: 700; }
@media (max-width: 768px) {
  .image-compare { grid-template-columns: 1fr; }
}
</style>
