<template>
  <div class="detect-page">
    <div class="page-header">
      <h1>病虫害检测</h1>
      <p class="subtitle">基于深度学习的玉米害虫识别系统</p>
    </div>

    <div class="detect-tabs">
      <button :class="{ active: tab === 'image' }" @click="tab = 'image'">图像检测</button>
      <button :class="{ active: tab === 'video' }" @click="tab = 'video'">视频检测</button>
      <button :class="{ active: tab === 'camera' }" @click="tab = 'camera'">摄像头检测</button>
    </div>

    <!-- 图像上传区域 -->
    <div class="detect-content" v-if="!result && tab === 'image'">
      <div class="upload-section">
        <div class="upload-area" @click="triggerUpload" @dragover.prevent @drop.prevent="handleDrop">
          <input ref="fileInput" type="file" accept="image/jpeg,image/png,image/webp" @change="handleFileChange" hidden />
          <div class="upload-icon">🖼️</div>
          <div class="upload-text">
            <template v-if="!file">
              <p>点击或拖拽上传<strong>图片</strong></p>
              <p class="hint">支持 JPG、PNG、WebP</p>
            </template>
            <template v-else>
              <p>{{ file.name }}</p>
              <p class="hint">点击更换文件</p>
            </template>
          </div>
        </div>

        <div class="model-section">
          <p class="section-label">选择检测模型</p>
          <div class="model-cards">
            <div
              v-for="model in models"
              :key="model.modelKey"
              :class="['model-card', { active: selectedModel === model.modelKey }]"
              @click="selectedModel = model.modelKey"
            >
              <div class="model-name">{{ model.modelName }}</div>
              <div class="model-classes">
                <span v-for="(cls, idx) in model.classes.slice(0, 4)" :key="idx" class="class-tag">
                  {{ cls }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div class="location-section">
          <p class="section-label">📍 位置信息（可选）</p>
          <div class="location-btns">
            <button class="btn-outline" @click="getLocation" :disabled="loading">
              {{ location.lat ? '📍 已获取位置' : '📍 获取当前位置' }}
            </button>
            <span v-if="location.address" class="address">{{ location.address }}</span>
          </div>
          <div v-if="environment.weather || environment.temperature !== null || environment.humidity !== null" class="environment-card">
            <span v-if="environment.weather">{{ environment.weather }}</span>
            <span v-if="environment.temperature !== null">{{ environment.temperature }}℃</span>
            <span v-if="environment.humidity !== null">湿度 {{ environment.humidity }}%</span>
          </div>
        </div>

        <button class="detect-btn" @click="startImageDetect" :disabled="!file || loading">
          {{ loading ? '检测中...' : '开始检测' }}
        </button>
      </div>
    </div>

    <!-- 视频上传区域 -->
    <div class="detect-content" v-if="!result && tab === 'video'">
      <div class="upload-section">
        <div class="upload-area" @click="triggerVideoUpload" @dragover.prevent @drop.prevent="handleVideoDrop">
          <input ref="videoFileInput" type="file" accept="video/mp4,video/avi,video/quicktime" @change="handleVideoChange" hidden />
          <div class="upload-icon">🎥</div>
          <div class="upload-text">
            <template v-if="!videoFile">
              <p>点击或拖拽上传<strong>视频</strong></p>
              <p class="hint">支持 MP4、AVI、MOV</p>
            </template>
            <template v-else>
              <p>{{ videoFile.name }}</p>
              <p class="hint">点击更换文件</p>
            </template>
          </div>
        </div>

        <div class="model-section">
          <p class="section-label">选择检测模型</p>
          <div class="model-cards">
            <div
              v-for="model in models"
              :key="model.modelKey"
              :class="['model-card', { active: selectedModel === model.modelKey }]"
              @click="selectedModel = model.modelKey"
            >
              <div class="model-name">{{ model.modelName }}</div>
              <div class="model-classes">
                <span v-for="(cls, idx) in model.classes.slice(0, 4)" :key="idx" class="class-tag">
                  {{ cls }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <button class="detect-btn" @click="startVideoDetect" :disabled="!videoFile || loading">
          {{ loading ? '处理中...' : '开始处理视频' }}
        </button>
      </div>
    </div>

    <!-- 摄像头检测区域 -->
    <div class="detect-content" v-if="!result && tab === 'camera'">
      <div class="upload-section">
        <div class="model-section">
          <p class="section-label">选择检测模型</p>
          <div class="model-cards">
            <div
              v-for="model in models"
              :key="model.modelKey"
              :class="['model-card', { active: selectedModel === model.modelKey }]"
              @click="selectedModel = model.modelKey"
            >
              <div class="model-name">{{ model.modelName }}</div>
              <div class="model-classes">
                <span v-for="(cls, idx) in model.classes.slice(0, 4)" :key="idx" class="class-tag">
                  {{ cls }}
                </span>
              </div>
            </div>
          </div>
        </div>

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

    <!-- 视频处理中 -->
    <div class="detect-content" v-if="videoProcessing">
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

    <!-- 图像检测结果 -->
    <div class="result-section" v-else-if="result && tab === 'image'">
      <div class="result-card">
        <div class="result-header">
          <span class="source-tag" :class="result.source">
            <template v-if="result.source === 'local_model'">🖥️ 本地模型精确检测</template>
            <template v-else-if="result.source === 'confirmed_no_pest'">✅ AI确认无病虫害</template>
            <template v-else>☁️ 云端AI分析</template>
          </span>
          <button class="btn-ghost" @click="reset">重新检测</button>
        </div>

        <div v-if="!result.has_pest" class="no-pest-message">
          <div class="no-pest-icon">🌿</div>
          <h3>未检测到病虫害</h3>
          <p>{{ result.message || '图像中不包含已知的玉米害虫特征' }}</p>
          <p v-if="result.confirmed_no_pest" class="confidence-hint">AI确认置信度：{{ ((result.confirmed_no_pest_confidence || 0) * 100).toFixed(0) }}%</p>
        </div>

        <template v-else>
          <div class="result-stats" v-if="result.stats">
            <div class="stat-item">
              <span class="stat-value">{{ result.stats.total || 0 }}</span>
              <span class="stat-label">检测到害虫</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ result.stats.unique || 0 }}</span>
              <span class="stat-label">不同目标</span>
            </div>
          </div>

          <div class="result-body">
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

            <div class="disease-list" v-if="result.merged_result?.diseases?.length">
              <h3>病虫害详情</h3>
              <div v-for="(disease, index) in result.merged_result.diseases" :key="index" class="disease-item">
                <div class="disease-name">{{ disease.name }}</div>
                <div class="disease-info">
                  <span class="confidence">置信度 {{ ((disease.confidence || 0) * 100).toFixed(1) }}%</span>
                  <span class="severity" :class="disease.severity || 'low'">{{ severityMap[disease.severity || 'low'] }}</span>
                </div>
                <div v-if="disease.knowledge" class="disease-desc">
                  <p><strong>形状：</strong>{{ disease.knowledge.shape }}</p>
                  <p><strong>颜色：</strong>{{ disease.knowledge.color }}</p>
                  <p><strong>症状：</strong>{{ disease.knowledge.symptoms }}</p>
                  <p><strong>防治：</strong>{{ disease.knowledge.prevention }}</p>
                </div>
                <div v-else-if="disease.symptoms" class="disease-desc">
                  <p><strong>症状：</strong>{{ disease.symptoms }}</p>
                  <p v-if="disease.prevention"><strong>防治：</strong>{{ disease.prevention }}</p>
                </div>
              </div>
            </div>

            <div v-if="result.ai_analysis?.diseases?.length && result.source === 'cloud_ai'" class="ai-analysis">
              <h3>AI 分析建议</h3>
              <div v-for="(disease, idx) in result.ai_analysis.diseases" :key="idx" class="ai-disease">
                <p><strong>{{ disease.name }}</strong> ({{ (disease.confidence * 100).toFixed(0) }}%)</p>
                <p v-if="disease.prevention">{{ disease.prevention }}</p>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- 视频检测结果 -->
    <div class="result-section" v-else-if="result && tab === 'video'">
      <div class="result-card">
        <div class="result-header">
          <span class="source-tag video">🎥 视频检测结果</span>
          <button class="btn-ghost" @click="reset">重新检测</button>
        </div>

        <div class="video-result">
          <div class="video-player">
            <video v-if="result.video_url" :src="result.video_url" controls autoplay />
            <div v-else class="video-placeholder">
              <p>视频处理完成</p>
            </div>
          </div>

          <div class="video-stats" v-if="result.stats">
            <h3>检测统计</h3>
            <div class="stats-grid">
              <div class="stat-box">
                <span class="stat-num">{{ result.stats.total_counts ? Object.values(result.stats.total_counts).reduce((a, b) => a + b, 0) : 0 }}</span>
                <span class="stat-desc">总检测数</span>
              </div>
              <div class="stat-box">
                <span class="stat-num">{{ result.stats.total_tracks || 0 }}</span>
                <span class="stat-desc">跟踪目标数</span>
              </div>
              <div class="stat-box">
                <span class="stat-num">{{ result.stats.frame_count || 0 }}</span>
                <span class="stat-desc">处理帧数</span>
              </div>
              <div class="stat-box">
                <span class="stat-num">{{ result.detections?.length || 0 }}</span>
                <span class="stat-desc">检测类别</span>
              </div>
            </div>
          </div>

          <div class="detection-summary" v-if="result.detections?.length">
            <h3>检测详情</h3>
            <div class="detection-list">
              <div v-for="(item, index) in result.detections" :key="index" class="detection-item">
                <div class="detection-header">
                  <span class="pest-name">{{ item.class }}</span>
                  <span class="pest-count">x{{ item.count }}</span>
                </div>
                <div class="detection-info">
                  <span class="confidence">最高置信度 {{ (item.maxConfidence * 100).toFixed(1) }}%</span>
                  <span class="tracks">跟踪ID: {{ Array.from(item.trackIds || []).join(', ') }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="timeline-section" v-if="result.timeline?.length">
            <h3>检测时间轴</h3>
            <div class="timeline">
              <div
                v-for="(item, index) in result.timeline.slice(0, 50)"
                :key="index"
                class="timeline-item"
              >
                <div class="timeline-marker" :class="'marker-' + getSeverityClass(item.confidence)"></div>
                <div class="timeline-content">
                  <span class="timeline-frame">帧 {{ item.frame }}</span>
                  <span class="timeline-class">{{ item.class }}</span>
                  <span class="timeline-conf">置信度 {{ (item.confidence * 100).toFixed(0) }}%</span>
                  <span class="timeline-track">ID: {{ item.track_id }}</span>
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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { mlApi, detectionApi, environmentApi } from '@/api'

const tab = ref('image')
const file = ref(null)
const videoFile = ref(null)
const videoFileInput = ref(null)
const fileInput = ref(null)
const loading = ref(false)
const result = ref(null)
const location = ref({ lat: null, lng: null, address: '' })
const environment = ref({ weather: '', temperature: null, humidity: null })
const models = ref([])
const selectedModel = ref('pest')

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

const severityMap = { high: '严重', medium: '中等', low: '轻微' }

function getSeverityClass(confidence) {
  if (confidence >= 0.8) return 'high'
  if (confidence >= 0.5) return 'medium'
  return 'low'
}

const detectionItems = computed(() => {
  if (!result.value?.labels?.length) return []
  const counts = {}
  result.value.labels.forEach((label, idx) => {
    if (!counts[label]) {
      counts[label] = { name: label, count: 0, confidence: '0%' }
    }
    counts[label].count++
    const conf = result.value.confidences?.[idx] || '0%'
    counts[label].confidence = conf
  })
  return Object.values(counts)
})

onMounted(async () => {
  try {
    const res = await mlApi.getModels()
    if (res.data?.models) {
      models.value = res.data.models
      if (models.value.length > 0) {
        selectedModel.value = models.value[0].modelKey
      }
    }
  } catch (e) {
    console.error('Failed to load models:', e)
  }
})

function triggerUpload() { fileInput.value?.click() }
function triggerVideoUpload() { videoFileInput.value?.click() }

function handleFileChange(e) {
  const f = e.target.files[0]
  if (f) { file.value = f }
}

function handleDrop(e) {
  const f = e.dataTransfer.files[0]
  if (f && f.type.startsWith('image/')) { file.value = f }
}

function handleVideoChange(e) {
  const f = e.target.files[0]
  if (f) { videoFile.value = f }
}

function handleVideoDrop(e) {
  const f = e.dataTransfer.files[0]
  if (f && f.type.startsWith('video/')) { videoFile.value = f }
}

function getLocation() {
  if (!navigator.geolocation) { ElMessage.warning('浏览器不支持定位'); return }
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
    const res = await environmentApi.current({
      latitude: location.value.lat,
      longitude: location.value.lng
    })
    location.value.address = res.address || `${location.value.lat.toFixed(5)},${location.value.lng.toFixed(5)}`
    environment.value = {
      weather: res.weather || '',
      temperature: res.temperature ?? null,
      humidity: res.humidity ?? null
    }
  } catch (e) {
    location.value.address = `${location.value.lat.toFixed(5)},${location.value.lng.toFixed(5)}`
    environment.value = { weather: '', temperature: null, humidity: null }
  }
}

async function startImageDetect() {
  if (!file.value) return
  loading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file.value)
    const params = {}
    if (location.value.lat) {
      params.latitude = location.value.lat
      params.longitude = location.value.lng
      params.address = location.value.address || ''
      params.weather = environment.value.weather || ''
      if (environment.value.temperature !== null) params.temperature = environment.value.temperature
      if (environment.value.humidity !== null) params.humidity = environment.value.humidity
    }
    result.value = await detectionApi.image(formData, params)
  } catch (e) {
    console.error(e)
    ElMessage.error('检测失败，请重试')
  }
  loading.value = false
}

async function startVideoDetect() {
  if (!videoFile.value) return
  loading.value = true
  videoProcessing.value = true
  videoProgress.value = 0
  videoProgressText.value = '上传视频中...'
  videoStats.value = null

  try {
    const formData = new FormData()
    formData.append('file', videoFile.value)
    formData.append('model_key', selectedModel.value)

    const uploadRes = await detectionApi.video(formData)
    videoSessionId.value = uploadRes.session_id
    videoProgressText.value = '视频处理中...'

    let isProcessing = true
    while (isProcessing) {
      await new Promise(r => setTimeout(r, 1000))
      const statusRes = await detectionApi.videoStatus(videoSessionId.value)

      if (statusRes.is_processing === false) {
        isProcessing = false
        break
      }

      if (statusRes.progress !== undefined) {
        videoProgress.value = Math.round(statusRes.progress)
      }
      if (statusRes.frame_count !== undefined) {
        videoProgressText.value = `已处理 ${statusRes.frame_count} 帧`
      }
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
        if (!detectionsMap[key]) {
          detectionsMap[key] = { class: key, count: 0, maxConfidence: 0, trackIds: new Set() }
        }
        detectionsMap[key].count++
        detectionsMap[key].maxConfidence = Math.max(detectionsMap[key].maxConfidence, det.confidence)
        if (det.track_id !== undefined) {
          detectionsMap[key].trackIds.add(det.track_id)
        }
      })
    }

    const detections = Object.values(detectionsMap).map(item => ({
      class: item.class,
      count: item.count,
      maxConfidence: item.maxConfidence,
      uniqueTracks: item.trackIds.size
    }))

    result.value = {
      video_url: streamUrl,
      session_id: videoSessionId.value,
      source: 'video_detection',
      stats: {
        total_counts: finalStatus.total_counts || {},
        total_tracks: finalStatus.total_tracks || 0,
        frame_count: finalStatus.frame_count || 0
      },
      detections: detections,
      timeline: finalStatus.detections || []
    }

    ElMessage.success('视频处理完成')
  } catch (e) {
    console.error(e)
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
    } catch (e) {
      console.error(e)
    }
  }
  videoProcessing.value = false
  videoSessionId.value = null
}

async function startCameraDetect() {
  loading.value = true
  try {
    const token = localStorage.getItem('access_token')
    if (!token) {
      ElMessage.error('请先登录')
      return
    }

    cameraMediaStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment' },
      audio: false
    })

    if (cameraVideo.value) {
      cameraVideo.value.srcObject = cameraMediaStream
    }

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host = window.location.host
    const wsUrl = `${protocol}://${host}/api/detection/camera/ws?token=${encodeURIComponent(token)}&model_key=${encodeURIComponent(selectedModel.value)}&frame_interval_ms=700`

    cameraWs = new WebSocket(wsUrl)

    cameraWs.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'detection_result') {
          cameraResult.value = msg
        } else if (msg.type === 'error') {
          ElMessage.error(msg.message || '摄像头检测异常')
        }
      } catch (err) {
        console.error(err)
      }
    }

    cameraWs.onclose = () => {
      stopCameraResources()
    }

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
  } catch (e) {
    console.error(e)
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
  } catch (e) {
    console.error(e)
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

  if (cameraVideo.value) {
    cameraVideo.value.srcObject = null
  }

  cameraRunning.value = false
}

function reset() {
  result.value = null
  file.value = null
  videoFile.value = null
  videoSessionId.value = null
  videoProcessing.value = false
  videoStats.value = null
  stopCameraResources()
  cameraResult.value = null
  environment.value = { weather: '', temperature: null, humidity: null }
}

onUnmounted(async () => {
  if (cameraRunning.value) {
    await stopCameraDetect()
  }
})
</script>

<style lang="scss" scoped>
.video-processing { text-align: center; padding: 48px;
  .processing-icon { font-size: 64px; margin-bottom: 16px; }
  h3 { font-size: 20px; margin-bottom: 8px; }
  p { color: var(--text-secondary); margin-bottom: 24px; }
}
.progress-section { max-width: 400px; margin: 0 auto 24px;
  .progress-text { font-size: 13px; color: var(--text-muted); margin-top: 8px; }
}
.processing-stats { display: flex; justify-content: center; gap: 24px; margin-bottom: 24px; font-size: 14px; color: var(--text-secondary); }

.video-result { margin-top: 20px; }
.video-player { background: #000; border-radius: var(--radius-lg); overflow: hidden; margin-bottom: 20px;
  video { width: 100%; display: block; max-height: 500px; }
  .video-placeholder { padding: 48px; text-align: center; color: var(--text-muted); }
}
.camera-preview {
  margin-top: 20px;
  background: #000;
  border-radius: var(--radius-lg);
  overflow: hidden;

  video {
    width: 100%;
    display: block;
    max-height: 500px;
    object-fit: contain;
  }

  .video-placeholder {
    padding: 48px;
    text-align: center;
    color: var(--text-muted);
    background: var(--bg-secondary);
  }
}
.camera-canvas {
  display: none;
}
.camera-result {
  margin-top: 12px;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);

  p {
    margin: 4px 0;
    font-size: 13px;
  }
}
.camera-actions {
  margin-top: 16px;
  display: flex;
  gap: 12px;

  .detect-btn,
  .btn-outline {
    margin-top: 0;
    flex: 1;
  }
}
.video-stats { padding: 16px; background: var(--bg-secondary); border-radius: var(--radius-md); margin-bottom: 16px;
  h3 { font-size: 16px; margin-bottom: 12px; }
  .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
  .stat-box { text-align: center; .stat-num { font-size: 28px; font-weight: 700; color: var(--primary); display: block; } .stat-desc { font-size: 13px; color: var(--text-muted); } }
}
.detection-summary { h3 { font-size: 16px; margin-bottom: 12px; } }
.timeline-section { margin-top: 20px;
  h3 { font-size: 16px; margin-bottom: 12px; }
}
.timeline { max-height: 400px; overflow-y: auto; padding: 12px; background: var(--bg-secondary); border-radius: var(--radius-md); }
.timeline-item { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--border-light);
  &:last-child { border-bottom: none; }
}
.timeline-marker { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0;
  &.marker-high { background: #dc2626; }
  &.marker-medium { background: #d97706; }
  &.marker-low { background: #059669; }
}
.timeline-content { display: flex; gap: 16px; font-size: 13px; flex-wrap: wrap;
  .timeline-frame { color: var(--text-muted); min-width: 60px; }
  .timeline-class { font-weight: 600; min-width: 80px; }
  .timeline-conf { color: var(--primary); }
  .timeline-track { color: var(--text-secondary); }
}
.detect-page { max-width: 900px; margin: 0 auto; padding: 20px; }
.page-header { text-align: center; margin-bottom: 24px; h1 { font-size: 28px; color: var(--text-primary); } .subtitle { color: var(--text-secondary); margin-top: 8px; } }
.detect-tabs { display: flex; gap: 8px; margin-bottom: 20px; background: var(--bg-primary); padding: 8px; border-radius: var(--radius-lg); border: 1px solid var(--border-light);
  button { flex: 1; padding: 12px; border: none; background: transparent; border-radius: var(--radius-md); cursor: pointer; font-size: 14px; transition: all 0.2s; &.active { background: var(--primary); color: white; } }
}
.detect-content { background: var(--bg-primary); border-radius: var(--radius-lg); border: 1px solid var(--border-light); padding: 24px; }
.upload-area { border: 2px dashed var(--border); border-radius: var(--radius-lg); padding: 40px; text-align: center; cursor: pointer; transition: all 0.2s; &:hover { border-color: var(--primary); background: var(--bg-secondary); } }
.upload-icon { font-size: 48px; margin-bottom: 16px; }
.upload-text { color: var(--text-secondary); p { margin: 8px 0; } .hint { font-size: 13px; color: var(--text-muted); } }
.model-section { margin-top: 20px; .section-label { font-size: 14px; color: var(--text-secondary); margin-bottom: 12px; } }
.model-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.model-card { padding: 16px; background: var(--bg-secondary); border: 2px solid transparent; border-radius: var(--radius-md); cursor: pointer; transition: all 0.2s;
  &:hover { border-color: var(--primary-light); }
  &.active { border-color: var(--primary); background: var(--primary-light); }
  .model-name { font-weight: 600; margin-bottom: 8px; }
  .model-classes { display: flex; flex-wrap: wrap; gap: 4px; }
  .class-tag { font-size: 11px; padding: 2px 8px; background: var(--bg-primary); border-radius: 4px; color: var(--text-secondary); }
}
.location-section { margin-top: 20px; .section-label { font-size: 14px; color: var(--text-secondary); margin-bottom: 12px; } }
.location-btns { display: flex; align-items: center; gap: 12px; }
.address { font-size: 13px; color: var(--text-secondary); }
.environment-card { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; font-size: 13px; color: var(--text-secondary);
  span { padding: 4px 8px; border-radius: var(--radius-sm); background: var(--bg-secondary); }
}
.detect-btn { width: 100%; margin-top: 20px; padding: 14px; background: var(--primary); color: white; border: none; border-radius: var(--radius-md); font-size: 16px; font-weight: 500; cursor: pointer; &:disabled { opacity: 0.6; cursor: not-allowed; } &:hover:not(:disabled) { background: var(--primary-dark); } }
.result-card { background: var(--bg-primary); border-radius: var(--radius-lg); border: 1px solid var(--border-light); padding: 24px; }
.result-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.source-tag { padding: 6px 16px; border-radius: 20px; font-size: 14px; font-weight: 500; &.local_model { background: #d1fae5; color: #065f46; } &.cloud_ai { background: #dbeafe; color: #1e40af; } &.confirmed_no_pest { background: #d1fae5; color: #065f46; } }
.btn-ghost { padding: 8px 16px; background: transparent; border: 1px solid var(--border); border-radius: var(--radius-md); cursor: pointer; &:hover { background: var(--bg-secondary); } }
.result-stats { display: flex; gap: 24px; margin-bottom: 20px; padding: 16px; background: var(--bg-secondary); border-radius: var(--radius-md); }
.stat-item { text-align: center; .stat-value { font-size: 32px; font-weight: 700; color: var(--primary); } .stat-label { font-size: 13px; color: var(--text-secondary); } }
.detection-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; margin-bottom: 20px; }
.detection-item { padding: 16px; background: var(--bg-secondary); border-radius: var(--radius-md); }
.detection-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.pest-name { font-weight: 600; }
.pest-count { background: var(--primary); color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px; }
.confidence { color: var(--primary); font-weight: 500; font-size: 13px; }
.disease-list, .ai-analysis { margin-top: 16px; h3 { font-size: 16px; margin-bottom: 12px; } }
.disease-item { padding: 16px; background: var(--bg-secondary); border-radius: var(--radius-md); margin-bottom: 12px; }
.disease-name { font-size: 16px; font-weight: 600; margin-bottom: 8px; }
.disease-info { display: flex; gap: 12px; margin-bottom: 8px; .severity { padding: 2px 10px; border-radius: 4px; font-size: 13px; &.high { background: #fee2e2; color: #dc2626; } &.medium { background: #fef3c7; color: #d97706; } &.low { background: #d1fae5; color: #065f46; } } }
.disease-desc { font-size: 14px; color: var(--text-secondary); p { margin: 6px 0; } }
.no-pest-message { text-align: center; padding: 48px 24px;
  .no-pest-icon { font-size: 64px; margin-bottom: 16px; }
  h3 { font-size: 20px; margin-bottom: 8px; }
  p { color: var(--text-secondary); margin-bottom: 8px; }
  .confidence-hint { font-size: 13px; color: var(--text-muted); }
}
.ai-disease { padding: 12px; background: var(--bg-secondary); border-radius: var(--radius-md); margin-bottom: 8px; p { margin: 4px 0; } }
.disease-desc { font-size: 13px; color: var(--text-secondary); p { margin: 4px 0; } }
</style>
