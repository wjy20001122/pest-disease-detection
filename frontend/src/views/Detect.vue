<template>
  <div class="detect-page">
    <PageHeader title="病虫害检测" subtitle="普通用户仅图像检测，管理员可使用视频与摄像头检测" />

    <div class="detect-tabs" v-if="isAdmin">
      <button :class="{ active: tab === 'image' }" @click="switchTab('image')">图像检测</button>
      <button :class="{ active: tab === 'video' }" @click="switchTab('video')">视频检测</button>
      <button :class="{ active: tab === 'camera' }" @click="switchTab('camera')">摄像头检测</button>
    </div>

    <el-alert
      v-else
      title="当前账号仅开放图像检测，视频与摄像头检测仅管理员可用。"
      type="info"
      :closable="false"
      show-icon
      style="margin-bottom: 12px"
    />

    <div class="detect-content" v-if="tab === 'image' && !imageResult">
      <div class="upload-section">
        <div class="upload-area" @click="triggerUpload" @dragover.prevent @drop.prevent="handleDrop">
          <input ref="fileInput" type="file" accept="image/jpeg,image/png,image/webp" @change="handleFileChange" hidden />
          <div class="upload-icon">🖼️</div>
          <div class="upload-text">
            <template v-if="!file">
              <p>点击或拖拽上传图片</p>
              <p class="hint">支持 JPG、PNG、WebP</p>
            </template>
            <template v-else>
              <p>{{ file.name }}</p>
              <p class="hint">点击更换文件</p>
            </template>
          </div>
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
            <span v-if="location.address" class="address">{{ location.address }}</span>
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

    <div class="detect-content" v-if="isAdmin && tab === 'video' && !videoResult && !videoProcessing">
      <div class="upload-section">
        <div class="upload-area" @click="triggerVideoUpload" @dragover.prevent @drop.prevent="handleVideoDrop">
          <input ref="videoFileInput" type="file" accept="video/mp4,video/avi,video/quicktime" @change="handleVideoChange" hidden />
          <div class="upload-icon">🎥</div>
          <div class="upload-text">
            <template v-if="!videoFile">
              <p>点击或拖拽上传视频</p>
              <p class="hint">支持 MP4、AVI、MOV</p>
            </template>
            <template v-else>
              <p>{{ videoFile.name }}</p>
              <p class="hint">点击更换文件</p>
            </template>
          </div>
        </div>
        <button class="detect-btn" @click="startVideoDetect" :disabled="!videoFile || loading">
          {{ loading ? '处理中...' : '开始处理视频' }}
        </button>
      </div>
    </div>

    <div class="detect-content" v-if="isAdmin && tab === 'camera'">
      <div class="upload-section">
        <div class="camera-preview">
          <video v-if="cameraRunning" ref="cameraVideo" autoplay playsinline muted></video>
          <div v-else class="video-placeholder">
            <p>摄像头未启动</p>
          </div>
        </div>

        <canvas ref="cameraCanvas" class="camera-canvas"></canvas>

        <div v-if="cameraResult" class="camera-result card-lite">
          <p><strong>检测来源：</strong>{{ cameraResult.source || '-' }}</p>
          <p><strong>是否检测到病虫害：</strong>{{ cameraResult.has_pest ? '是' : '否' }}</p>
          <p v-if="cameraResult.merged_result?.diseases?.length">
            <strong>病虫害：</strong>
            {{ cameraResult.merged_result.diseases.map(d => d.name).join('、') }}
          </p>
        </div>

        <div class="camera-actions">
          <button class="detect-btn" :disabled="loading || cameraRunning" @click="startCameraDetect">
            {{ loading ? '启动中...' : '开始摄像头检测' }}
          </button>
          <button class="btn-outline" :disabled="loading || !cameraRunning" @click="stopCameraDetect">
            停止摄像头检测
          </button>
        </div>
      </div>
    </div>

    <div class="detect-content" v-if="isAdmin && videoProcessing">
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
          <span>检测数量：{{ videoStats.total_counts ? Object.values(videoStats.total_counts).reduce((a, b) => a + b, 0) : 0 }}</span>
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

    <div class="result-section" v-if="isAdmin && tab === 'video' && videoResult">
      <div class="result-card">
        <div class="result-header">
          <span class="source-tag video">🎥 视频检测结果</span>
          <button class="btn-ghost" @click="resetVideo">重新检测</button>
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
            <div class="stats-grid">
              <div class="stat-box">
                <span class="stat-num">{{ videoResult.stats.total_counts ? Object.values(videoResult.stats.total_counts).reduce((a, b) => a + b, 0) : 0 }}</span>
                <span class="stat-desc">总检测数</span>
              </div>
              <div class="stat-box">
                <span class="stat-num">{{ videoResult.stats.total_tracks || 0 }}</span>
                <span class="stat-desc">跟踪目标数</span>
              </div>
              <div class="stat-box">
                <span class="stat-num">{{ videoResult.stats.frame_count || 0 }}</span>
                <span class="stat-desc">处理帧数</span>
              </div>
              <div class="stat-box">
                <span class="stat-num">{{ videoResult.detections?.length || 0 }}</span>
                <span class="stat-desc">检测类别</span>
              </div>
            </div>
          </div>
          <div class="detection-summary" v-if="videoResult.detections?.length">
            <h3>检测详情</h3>
            <div class="detection-list">
              <div v-for="(item, index) in videoResult.detections" :key="index" class="detection-item">
                <div class="detection-header">
                  <span class="pest-name">{{ item.class }}</span>
                  <span class="pest-count">x{{ item.count }}</span>
                </div>
                <div class="detection-info">
                  <span class="confidence">最高置信度 {{ (item.maxConfidence * 100).toFixed(1) }}%</span>
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
import PageHeader from '@/components/ui/PageHeader.vue'

const userStore = useUserStore()
const isAdmin = computed(() => userStore.user?.role === 'admin')
const tab = ref('image')
const loading = ref(false)
const models = ref([{ modelKey: 'pest', modelName: '默认模型', classes: [] }])
const selectedModel = ref('pest')

const file = ref(null)
const fileInput = ref(null)
const cropType = ref('')
const category = ref('')
const location = ref({ lat: null, lng: null, address: '' })
const environment = ref({ weather: '', temperature: null, humidity: null })
const imageResult = ref(null)

const videoFile = ref(null)
const videoFileInput = ref(null)
const videoResult = ref(null)
const videoProcessing = ref(false)
const videoProgress = ref(0)
const videoProgressText = ref('')
const videoStats = ref(null)
const videoSessionId = ref(null)

const cameraRunning = ref(false)
const cameraVideo = ref(null)
const cameraCanvas = ref(null)
const cameraResult = ref(null)
let cameraMediaStream = null
let cameraWs = null
let cameraFrameTimer = null

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

function switchTab(next) {
  if (!isAdmin.value && next !== 'image') return
  tab.value = next
}

function triggerUpload() {
  fileInput.value?.click()
}

function handleFileChange(e) {
  const selected = e.target.files?.[0]
  if (selected) file.value = selected
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
    ElMessage.warning('浏览器不支持定位')
    return
  }
  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      location.value.lat = pos.coords.latitude
      location.value.lng = pos.coords.longitude
      location.value.address = '已获取位置'
      await fetchEnvironment()
      ElMessage.success('位置已获取')
    },
    () => ElMessage.error('获取位置失败')
  )
}

async function fetchEnvironment() {
  if (!location.value.lat || !location.value.lng) return
  try {
    const res = await environmentApi.current({ latitude: location.value.lat, longitude: location.value.lng })
    location.value.address = res.address || `${location.value.lat.toFixed(5)},${location.value.lng.toFixed(5)}`
    environment.value = {
      weather: res.weather || '',
      temperature: res.temperature ?? null,
      humidity: res.humidity ?? null
    }
  } catch {
    location.value.address = `${location.value.lat.toFixed(5)},${location.value.lng.toFixed(5)}`
    environment.value = { weather: '', temperature: null, humidity: null }
  }
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
  if (!isAdmin.value || !videoFile.value) return
  loading.value = true
  videoProcessing.value = true
  videoProgress.value = 0
  videoProgressText.value = '上传视频中...'
  videoStats.value = null
  try {
    const formData = new FormData()
    formData.append('file', videoFile.value)
    const uploadRes = await detectionApi.video(formData)
    videoSessionId.value = uploadRes.session_id
    let isProcessing = true
    while (isProcessing) {
      await new Promise(resolve => setTimeout(resolve, 1000))
      const statusRes = await detectionApi.videoStatus(videoSessionId.value)
      if (statusRes.is_processing === false) {
        isProcessing = false
        break
      }
      if (statusRes.progress !== undefined) videoProgress.value = Math.round(statusRes.progress)
      if (statusRes.frame_count !== undefined) videoProgressText.value = `已处理 ${statusRes.frame_count} 帧`
      if (statusRes.total_counts) {
        videoStats.value = {
          frame_count: statusRes.frame_count || 0,
          total_counts: statusRes.total_counts || {},
          total_tracks: statusRes.total_tracks || 0
        }
      }
    }
    const finalStatus = await detectionApi.videoStatus(videoSessionId.value)
    const streamUrl = detectionApi.videoStream(videoSessionId.value)
    const detectionsMap = {}
    if (finalStatus.detections) {
      finalStatus.detections.forEach(det => {
        const key = det.class
        if (!detectionsMap[key]) detectionsMap[key] = { class: key, count: 0, maxConfidence: 0 }
        detectionsMap[key].count++
        detectionsMap[key].maxConfidence = Math.max(detectionsMap[key].maxConfidence, det.confidence)
      })
    }
    videoResult.value = {
      video_url: streamUrl,
      stats: {
        total_counts: finalStatus.total_counts || {},
        total_tracks: finalStatus.total_tracks || 0,
        frame_count: finalStatus.frame_count || 0
      },
      detections: Object.values(detectionsMap)
    }
    ElMessage.success('视频处理完成')
  } catch {
    ElMessage.error('视频处理失败，请重试')
  } finally {
    loading.value = false
    videoProcessing.value = false
  }
}

async function cancelVideoProcessing() {
  if (videoSessionId.value) {
    try {
      await detectionApi.stopVideo(videoSessionId.value)
    } catch {}
  }
  videoProcessing.value = false
  videoSessionId.value = null
}

async function startCameraDetect() {
  if (!isAdmin.value) return
  loading.value = true
  try {
    const token = localStorage.getItem('access_token')
    if (!token) {
      ElMessage.error('请先登录')
      return
    }
    cameraMediaStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
    if (cameraVideo.value) cameraVideo.value.srcObject = cameraMediaStream
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host = window.location.host
    const wsUrl = `${protocol}://${host}/api/detection/camera/ws?token=${encodeURIComponent(token)}&model_key=pest&frame_interval_ms=700`
    cameraWs = new WebSocket(wsUrl)
    cameraWs.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'detection_result') cameraResult.value = msg
        else if (msg.type === 'error') ElMessage.error(msg.message || '摄像头检测异常')
      } catch {}
    }
    cameraWs.onclose = () => stopCameraResources()
    cameraFrameTimer = setInterval(() => {
      if (!cameraWs || cameraWs.readyState !== WebSocket.OPEN) return
      if (!cameraVideo.value || !cameraCanvas.value) return
      if (cameraVideo.value.videoWidth === 0 || cameraVideo.value.videoHeight === 0) return
      cameraCanvas.value.width = cameraVideo.value.videoWidth
      cameraCanvas.value.height = cameraVideo.value.videoHeight
      const ctx = cameraCanvas.value.getContext('2d')
      ctx.drawImage(cameraVideo.value, 0, 0)
      const imageData = cameraCanvas.value.toDataURL('image/jpeg', 0.75)
      cameraWs.send(JSON.stringify({ type: 'frame', image: imageData }))
    }, 700)
    cameraRunning.value = true
    ElMessage.success('摄像头检测已启动')
  } catch {
    ElMessage.error('启动摄像头检测失败')
  } finally {
    loading.value = false
  }
}

async function stopCameraDetect() {
  loading.value = true
  try {
    if (cameraWs && cameraWs.readyState === WebSocket.OPEN) {
      cameraWs.send(JSON.stringify({ type: 'stop' }))
      cameraWs.close()
    }
  } finally {
    stopCameraResources()
    loading.value = false
  }
}

function stopCameraResources() {
  if (cameraFrameTimer) {
    clearInterval(cameraFrameTimer)
    cameraFrameTimer = null
  }
  if (cameraWs) {
    cameraWs.onmessage = null
    cameraWs.onclose = null
    cameraWs = null
  }
  if (cameraMediaStream) {
    cameraMediaStream.getTracks().forEach(track => track.stop())
    cameraMediaStream = null
  }
  if (cameraVideo.value) cameraVideo.value.srcObject = null
  cameraRunning.value = false
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
}

onUnmounted(async () => {
  if (cameraRunning.value) await stopCameraDetect()
})

async function loadModelsForAdmin() {
  if (!isAdmin.value) return
  try {
    const res = await mlApi.getModels()
    if (res?.data?.models?.length) {
      models.value = res.data.models
      selectedModel.value = res.data.models[0].modelKey
    }
  } catch {
    models.value = [{ modelKey: 'pest', modelName: '默认模型', classes: [] }]
    selectedModel.value = 'pest'
  }
}

onMounted(() => {
  loadModelsForAdmin()
})

watch(isAdmin, (value) => {
  if (value) loadModelsForAdmin()
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
.confidence { color: var(--primary); font-weight: 500; font-size: 13px; }
.disease-list, .ai-analysis { margin-top: 16px; h3 { font-size: 16px; margin-bottom: 12px; } }
.disease-item { padding: 16px; background: var(--bg-secondary); border-radius: var(--radius-md); margin-bottom: 12px; }
.disease-name { font-size: 16px; font-weight: 600; margin-bottom: 8px; }
.disease-desc { font-size: 14px; color: var(--text-secondary); p { margin: 6px 0; } }
.no-pest-message { text-align: center; padding: 48px 24px; .no-pest-icon { font-size: 64px; margin-bottom: 16px; } h3 { font-size: 20px; margin-bottom: 8px; } p { color: var(--text-secondary); margin-bottom: 8px; } }
.video-processing { text-align: center; padding: 48px; .processing-icon { font-size: 64px; margin-bottom: 16px; } h3 { font-size: 20px; margin-bottom: 8px; } p { color: var(--text-secondary); margin-bottom: 24px; } }
.progress-section { max-width: 400px; margin: 0 auto 24px; .progress-text { font-size: 13px; color: var(--text-muted); margin-top: 8px; } }
.processing-stats { display: flex; justify-content: center; gap: 24px; margin-bottom: 24px; font-size: 14px; color: var(--text-secondary); }
.video-player { background: #000; border-radius: var(--radius-lg); overflow: hidden; margin-bottom: 20px; video { width: 100%; display: block; max-height: 500px; } .video-placeholder { padding: 48px; text-align: center; color: var(--text-muted); } }
.camera-preview { background: #000; border-radius: var(--radius-lg); overflow: hidden; video { width: 100%; display: block; max-height: 500px; object-fit: contain; } .video-placeholder { padding: 48px; text-align: center; color: var(--text-muted); background: var(--bg-secondary); } }
.camera-canvas { display: none; }
.camera-result { margin-top: 12px; padding: 12px; background: var(--bg-secondary); border-radius: var(--radius-md); p { margin: 4px 0; font-size: 13px; } }
.camera-actions { margin-top: 16px; display: flex; gap: 12px; .detect-btn, .btn-outline { margin-top: 0; flex: 1; } }
.video-stats { padding: 16px; background: var(--bg-secondary); border-radius: var(--radius-md); margin-bottom: 16px; h3 { font-size: 16px; margin-bottom: 12px; } .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; } .stat-box { text-align: center; .stat-num { font-size: 28px; font-weight: 700; color: var(--primary); display: block; } .stat-desc { font-size: 13px; color: var(--text-muted); } } }
@media (max-width: 768px) {
  .image-compare { grid-template-columns: 1fr; }
}
</style>
