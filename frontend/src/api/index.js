import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const request = axios.create({
  baseURL: '/api',
  timeout: 60000
})

request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      switch (status) {
        case 401:
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          router.push('/login')
          ElMessage.error(data.detail || '请先登录')
          break
        case 403:
          ElMessage.error('权限不足')
          break
        case 404:
          ElMessage.error('资源不存在')
          break
        default:
          ElMessage.error(data.detail || '请求失败')
      }
    } else {
      ElMessage.error('网络错误')
    }
    return Promise.reject(error)
  }
)

export default request

// 认证相关 API
export const authApi = {
  register: (data) => request.post('/auth/register', null, { params: data }),
  sendEmailCode: (params) => request.post('/auth/email/send-code', null, { params }),
  login: (data) => {
    const form = new URLSearchParams()
    form.append('username', data.username)
    form.append('password', data.password)
    return request.post('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
  },
  sendResetCode: (params) => request.post('/auth/password/send-code', null, { params }),
  resetPassword: (params) => request.post('/auth/password/reset', null, { params }),
  logout: () => request.post('/auth/logout'),
  getProfile: () => request.get('/auth/profile'),
  updateProfile: (data) => request.put('/auth/profile', null, { params: data })
}

// 检测相关 API (自定义病虫害检测)
export const detectionApi = {
  image: (formData, params = {}) => request.post('/detection/image', formData, {
    params,
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  video: (formData) => request.post('/detection/video', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  videoStatus: (sessionId) => request.get(`/detection/video/${sessionId}/status`),
  videoStream: (sessionId) => `${request.defaults.baseURL}/detection/video/${sessionId}/stream`,
  stopVideo: (sessionId) => request.post(`/detection/video/${sessionId}/stop`),
  cameraStart: (modelKey) => request.post('/detection/camera/start', null, { params: { model_key: modelKey } }),
  cameraStream: () => `${request.defaults.baseURL}/detection/camera/stream`,
  cameraStop: () => request.post('/detection/camera/stop'),
  history: (params) => request.get('/detection/history', { params }),
  detail: (id, detectionType) => request.get(`/detection/${id}`, { params: { detection_type: detectionType } }),
  stats: (params) => request.get('/detection/stats/overview', { params }),
  statsOverview: (params) => request.get('/detection/stats/overview', { params })
}

// ML模型检测 API (基于现有Fastapi项目)
export const mlApi = {
  getModels: () => request.get('/get_models'),
  fileNames: (modelKey) => request.get('/file_names', { params: { modelKey } }),
  predictImage: (payload) => request.post('/predictImg', payload),
  predictVideo: (params) => request.get('/predictVideo', { params }),
  stopVideo: (sessionId) => request.get('/stopVideo', { params: { sessionId } }),
  predictCamera: (params) => request.get('/predictCamera', { params }),
  stopCamera: () => request.get('/stopCamera'),
  startRecording: () => request.get('/startRecording'),
  stopRecording: (params) => request.get('/stopRecording', { params }),
  uploadFile: (file, category) => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/upload', formData, {
      params: { category },
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  }
}

// 跟踪任务 API
export const trackingApi = {
  create: (data) => request.post('/tracking', data),
  list: (params) => request.get('/tracking', { params }),
  detail: (id) => request.get(`/tracking/${id}`),
  update: (id, data) => request.put(`/tracking/${id}`, data),
  addUpdate: (id, data) => request.post(`/tracking/${id}/updates`, data)
}

// 环境数据 API
export const environmentApi = {
  current: (params) => request.get('/environment/current', { params }),
  ipCurrent: () => request.get('/environment/ip-current'),
  weather: (params) => request.get('/environment/weather', { params }),
  manual: (params) => request.post('/environment/manual', null, { params })
}

// 知识库 API
export const knowledgeApi = {
  search: (params) => request.get('/knowledge/search', { params }),
  recent: (params) => request.get('/knowledge/recent', { params }),
  detail: (id) => request.get(`/knowledge/${id}`),
  shapes: () => request.get('/knowledge/shapes'),
  colors: () => request.get('/knowledge/colors')
}

// 问答 API
export const qnaApi = {
  ask: (data) => request.post('/qna/ask', data),
  conversations: (params) => request.get('/qna/conversations', { params }),
  conversationDetail: (id) => request.get(`/qna/conversations/${id}`)
}

// 通知 API
export const notificationApi = {
  list: (params) => request.get('/notifications', { params }),
  markRead: (id) => request.put(`/notifications/${id}/read`),
  markAllRead: () => request.put('/notifications/read-all')
}

// 管理后台 API
export const adminApi = {
  dashboard: () => request.get('/admin/dashboard'),
  users: (params) => request.get('/admin/users', { params }),
  updateUser: (id, data) => request.patch(`/admin/users/${id}`, data),
  stats: (params) => request.get('/admin/stats', { params }),
  models: () => request.get('/admin/models'),
  updateModel: (modelKey, data) => request.put(`/admin/models/${modelKey}`, data),
  notifications: (params) => request.get('/admin/notifications', { params }),
  broadcastNotification: (data) => request.post('/admin/notifications/broadcast', data),
  markAllNotificationsRead: (params) => request.put('/admin/notifications/read-all', null, { params }),
  knowledge: (params) => request.get('/admin/knowledge', { params }),
  queueMetrics: () => request.get('/admin/queue/metrics'),
  configs: () => request.get('/admin/configs'),
  updateConfigs: (values) => request.put('/admin/configs', { values }),
  permissionAudit: (params) => request.get('/admin/audit/permissions', { params })
}

// 记录相关 API (与现有Fastapi兼容)
export const recordsApi = {
  getImgRecords: (params) => request.get('/records/img', { params }),
  getVideoRecords: (params) => request.get('/records/video', { params }),
  getCameraRecords: (params) => request.get('/records/camera', { params }),
  getDataCollectionRecords: (params) => request.get('/records/datacollection', { params })
}
