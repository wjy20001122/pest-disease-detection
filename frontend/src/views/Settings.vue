<template>
  <div class="settings-page">
    <div class="settings-layout">
      <!-- 设置导航 -->
      <aside class="settings-nav">
        <div
          v-for="tab in tabs"
          :key="tab.key"
          class="nav-item"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          <span class="nav-icon">{{ tab.icon }}</span>
          <span class="nav-text">{{ tab.name }}</span>
        </div>
      </aside>

      <!-- 设置内容 -->
      <main class="settings-content">
        <!-- 个人信息 -->
        <div v-if="activeTab === 'profile'" class="settings-section">
          <h2>个人信息</h2>
          <el-form :model="profileForm" label-width="100px" class="settings-form">
            <el-form-item label="用户名">
              <el-input v-model="profileForm.username" />
            </el-form-item>
            <el-form-item label="邮箱">
              <el-input v-model="profileForm.email" type="email" />
            </el-form-item>
            <el-form-item label="手机号">
              <el-input v-model="profileForm.phone" />
            </el-form-item>
            <el-form-item label="地区">
              <el-input v-model="profileForm.region" placeholder="如：江苏省南京市" />
            </el-form-item>
            <el-form-item label="个人简介">
              <el-input v-model="profileForm.bio" type="textarea" :rows="3" placeholder="介绍一下自己" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveProfile">保存修改</el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- 账户安全 -->
        <div v-if="activeTab === 'security'" class="settings-section">
          <h2>账户安全</h2>
          
          <div class="security-item">
            <div class="security-info">
              <h4>修改密码</h4>
              <p>定期修改密码可以提高账户安全性</p>
            </div>
            <el-button @click="showPasswordDialog = true">修改</el-button>
          </div>

          <div class="security-item">
            <div class="security-info">
              <h4>双因素认证</h4>
              <p>启用后登录需要输入验证码</p>
            </div>
            <el-switch v-model="securityForm.two_factor" />
          </div>

          <div class="security-item">
            <div class="security-info">
              <h4>登录记录</h4>
              <p>查看最近的登录历史</p>
            </div>
            <el-button @click="showLoginHistory = true">查看</el-button>
          </div>
        </div>

        <!-- 通知设置 -->
        <div v-if="activeTab === 'notifications'" class="settings-section">
          <h2>通知设置</h2>

          <div class="notification-setting">
            <div class="setting-info">
              <h4>浏览器通知</h4>
              <p>接收浏览器推送通知，即使网站关闭也能收到</p>
            </div>
            <div class="push-status">
              <el-tag v-if="pushPermission === 'granted'" type="success" size="small">已开启</el-tag>
              <el-tag v-else-if="pushPermission === 'denied'" type="danger" size="small">已拒绝</el-tag>
              <el-tag v-else size="small">未开启</el-tag>
              <el-button
                v-if="pushPermission !== 'granted' && pushPermission !== 'denied'"
                size="small"
                type="primary"
                plain
                @click="requestPushPermission"
                :loading="requestingPush"
              >
                开启通知
              </el-button>
              <el-button
                v-if="pushPermission === 'granted'"
                size="small"
                @click="openPushSettings"
              >
                管理通知
              </el-button>
            </div>
          </div>

          <div class="notification-setting">
            <div class="setting-info">
              <h4>预警通知</h4>
              <p>收到区域虫害预警时发送通知</p>
            </div>
            <el-switch v-model="notificationSettings.warning" />
          </div>

          <div class="notification-setting">
            <div class="setting-info">
              <h4>检测完成通知</h4>
              <p>图像/视频检测完成后发送通知</p>
            </div>
            <el-switch v-model="notificationSettings.detection" />
          </div>

          <div class="notification-setting">
            <div class="setting-info">
              <h4>智能体报告</h4>
              <p>接收AI审查报告和智能建议</p>
            </div>
            <el-switch v-model="notificationSettings.agent" />
          </div>

          <div class="notification-setting">
            <div class="setting-info">
              <h4>邮件通知</h4>
              <p>通过邮件接收重要通知</p>
            </div>
            <el-switch v-model="notificationSettings.email" />
          </div>

          <el-button type="primary" @click="saveNotificationSettings">保存设置</el-button>
        </div>

        <!-- 检测偏好 -->
        <div v-if="activeTab === 'preferences'" class="settings-section">
          <h2>检测偏好</h2>
          
          <el-form label-width="140px">
            <el-form-item label="检测方式优先级">
              <el-select v-model="preferences.detection_priority" style="width: 300px">
                <el-option label="云端AI优先" value="cloud_first" />
                <el-option label="本地模型优先" value="local_first" />
                <el-option label="仅使用云端AI" value="cloud_only" />
                <el-option label="仅使用本地模型" value="local_only" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="自动保存检测">
              <el-switch v-model="preferences.auto_save" />
            </el-form-item>

            <el-form-item label="检测置信度阈值">
              <el-slider v-model="preferences.confidence_threshold" :min="0" :max="100" :step="5" style="width: 300px" />
              <span style="margin-left: 12px">{{ preferences.confidence_threshold }}%</span>
            </el-form-item>

            <el-form-item label="视频采样帧率">
              <el-select v-model="preferences.video_fps" style="width: 300px">
                <el-option label="1帧/秒" :value="1" />
                <el-option label="2帧/秒" :value="2" />
                <el-option label="3帧/秒" :value="3" />
              </el-select>
            </el-form-item>
          </el-form>

          <el-button type="primary" @click="savePreferences">保存偏好</el-button>
        </div>

        <!-- API密钥 -->
        <div v-if="activeTab === 'api'" class="settings-section">
          <h2>API密钥</h2>
          <p class="section-desc">使用API密钥可以访问公开API接口，实现第三方系统集成。</p>

          <div class="api-keys-list">
            <div v-for="key in apiKeys" :key="key.id" class="api-key-item">
              <div class="key-info">
                <span class="key-name">{{ key.name }}</span>
                <span class="key-value">{{ key.key }}</span>
                <span class="key-created">创建于 {{ formatTime(key.created_at) }}</span>
              </div>
              <div class="key-actions">
                <el-button size="small" @click="copyKey(key.key)">复制</el-button>
                <el-button size="small" type="danger" plain @click="deleteKey(key.id)">删除</el-button>
              </div>
            </div>
          </div>

          <el-button type="primary" @click="createApiKey">创建新密钥</el-button>
        </div>

        <!-- 数据管理 -->
        <div v-if="activeTab === 'data'" class="settings-section">
          <h2>数据管理</h2>
          
          <div class="data-item">
            <div class="data-info">
              <h4>导出数据</h4>
              <p>导出您的检测记录和个人数据</p>
            </div>
            <el-button @click="exportData">导出</el-button>
          </div>

          <div class="data-item danger">
            <div class="data-info">
              <h4>清空历史记录</h4>
              <p>删除所有检测历史，此操作不可恢复</p>
            </div>
            <el-button type="danger" @click="confirmClearHistory">清空</el-button>
          </div>

          <div class="data-item danger">
            <div class="data-info">
              <h4>注销账户</h4>
              <p>永久删除您的账户和所有数据</p>
            </div>
            <el-button type="danger" @click="confirmDeleteAccount">注销</el-button>
          </div>
        </div>
      </main>
    </div>

    <!-- 修改密码对话框 -->
    <el-dialog v-model="showPasswordDialog" title="修改密码" width="450px">
      <el-form :model="passwordForm" label-width="100px">
        <el-form-item label="当前密码">
          <el-input v-model="passwordForm.old_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="passwordForm.new_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="passwordForm.confirm_password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPasswordDialog = false">取消</el-button>
        <el-button type="primary" @click="changePassword">确认修改</el-button>
      </template>
    </el-dialog>

    <!-- 登录历史对话框 -->
    <el-dialog v-model="showLoginHistory" title="登录记录" width="600px">
      <div class="login-history">
        <div v-for="log in loginHistory" :key="log.id" class="history-item">
          <div class="history-info">
            <span class="history-device">{{ log.device }}</span>
            <span class="history-ip">{{ log.ip }}</span>
          </div>
          <span class="history-time">{{ formatTime(log.time) }}</span>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { authApi } from '@/api'

const userStore = useUserStore()
const activeTab = ref('profile')
const showPasswordDialog = ref(false)
const showLoginHistory = ref(false)
const pushPermission = ref('default')
const requestingPush = ref(false)

const tabs = [
  { key: 'profile', name: '个人信息', icon: '👤' },
  { key: 'security', name: '账户安全', icon: '🔒' },
  { key: 'notifications', name: '通知设置', icon: '🔔' },
  { key: 'preferences', name: '检测偏好', icon: '⚙️' },
  { key: 'api', name: 'API密钥', icon: '🔑' },
  { key: 'data', name: '数据管理', icon: '📦' }
]

const profileForm = reactive({
  username: '',
  email: '',
  phone: '',
  region: '',
  bio: ''
})

const securityForm = reactive({
  two_factor: false
})

const notificationSettings = reactive({
  warning: true,
  detection: true,
  agent: true,
  email: false
})

const preferences = reactive({
  detection_priority: 'cloud_first',
  auto_save: true,
  confidence_threshold: 80,
  video_fps: 2
})

const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const apiKeys = ref([])
const loginHistory = ref([
  { id: 1, device: 'Chrome on Windows', ip: '192.168.1.100', time: new Date(Date.now() - 86400000).toISOString() },
  { id: 2, device: 'Safari on iPhone', ip: '192.168.1.101', time: new Date(Date.now() - 172800000).toISOString() }
])

function formatTime(time) {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

async function fetchUserProfile() {
  try {
    const res = await authApi.getProfile()
    Object.assign(profileForm, res)
  } catch (e) {
    // 使用默认数据
    Object.assign(profileForm, {
      username: userStore.user?.username || 'User',
      email: 'user@example.com',
      phone: '138****8888',
      region: '江苏省南京市',
      bio: '专注农业生产'
    })
  }
}

async function saveProfile() {
  try {
    await authApi.updateProfile(profileForm)
    ElMessage.success('保存成功')
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

async function changePassword() {
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    ElMessage.error('两次输入的密码不一致')
    return
  }
  // 调用API
  ElMessage.success('密码修改成功')
  showPasswordDialog.value = false
  Object.assign(passwordForm, { old_password: '', new_password: '', confirm_password: '' })
}

function saveNotificationSettings() {
  ElMessage.success('设置已保存')
}

async function requestPushPermission() {
  requestingPush.value = true
  try {
    if (typeof window.requestWebPushPermission === 'function') {
      const granted = await window.requestWebPushPermission()
      if (granted) {
        ElMessage.success('浏览器通知已开启')
        pushPermission.value = 'granted'
      } else {
        ElMessage.warning('通知权限被拒绝，请在浏览器设置中开启')
        pushPermission.value = 'denied'
      }
    } else {
      const permission = await Notification.requestPermission()
      if (permission === 'granted') {
        ElMessage.success('浏览器通知已开启')
        pushPermission.value = 'granted'
      } else {
        pushPermission.value = 'denied'
      }
    }
  } catch (e) {
    ElMessage.error('请求通知权限失败')
    pushPermission.value = 'denied'
  } finally {
    requestingPush.value = false
  }
}

function openPushSettings() {
  if (pushPermission.value === 'denied') {
    ElMessage.info('请在浏览器设置中修改通知权限')
  }
}

function checkPushPermission() {
  if (typeof window.checkPushPermission === 'function') {
    pushPermission.value = window.checkPushPermission()
  } else if ('Notification' in window) {
    pushPermission.value = Notification.permission
  } else {
    pushPermission.value = 'unsupported'
  }
}

function savePreferences() {
  ElMessage.success('偏好已保存')
}

function createApiKey() {
  ElMessage.info('功能开发中')
}

function copyKey(key) {
  navigator.clipboard.writeText(key)
  ElMessage.success('已复制到剪贴板')
}

function deleteKey(id) {
  ElMessageBox.confirm('确定要删除这个API密钥吗？', '提示', { type: 'warning' })
    .then(() => {
      apiKeys.value = apiKeys.value.filter(k => k.id !== id)
      ElMessage.success('已删除')
    })
    .catch(() => {})
}

function exportData() {
  ElMessage.info('正在生成导出文件...')
}

function confirmClearHistory() {
  ElMessageBox.confirm('确定要清空所有检测历史吗？此操作不可恢复。', '警告', { type: 'warning' })
    .then(() => {
      ElMessage.success('历史记录已清空')
    })
    .catch(() => {})
}

function confirmDeleteAccount() {
  ElMessageBox.confirm('确定要注销账户吗？所有数据将被永久删除。', '危险操作', { type: 'error' })
    .then(() => {
      ElMessage.success('账户已注销')
    })
    .catch(() => {})
}

onMounted(() => {
  fetchUserProfile()
  checkPushPermission()
})
</script>

<style lang="scss" scoped>
.settings-page { max-width: 1000px; margin: 0 auto; }

.settings-layout { display: flex; gap: 32px; }

.settings-nav {
  width: 200px; flex-shrink: 0;
  background: var(--bg-primary); border-radius: var(--radius-lg); padding: 16px;
}
.nav-item {
  display: flex; align-items: center; gap: 12px; padding: 12px; border-radius: var(--radius-md);
  cursor: pointer; transition: all 0.2s; margin-bottom: 4px;
  &:hover { background: var(--bg-secondary); }
  &.active { background: var(--primary); color: white; }
  .nav-icon { font-size: 18px; }
}

.settings-content { flex: 1; }
.settings-section {
  background: var(--bg-primary); border-radius: var(--radius-lg); padding: 24px;
  h2 { margin: 0 0 24px; font-size: 20px; } 
}
.section-desc { color: var(--text-secondary); margin-bottom: 24px; }

.settings-form { max-width: 500px; }

.security-item, .notification-setting { display: flex; justify-content: space-between; align-items: center; padding: 16px 0; border-bottom: 1px solid var(--border-light); }
.notification-setting .push-status { display: flex; align-items: center; gap: 12px; }
.security-info h4, .setting-info h4 { margin: 0 0 4px; font-size: 15px; }
.security-info p, .setting-info p { margin: 0; font-size: 13px; color: var(--text-secondary); }

.data-item { display: flex; justify-content: space-between; align-items: center; padding: 16px 0; border-bottom: 1px solid var(--border-light); &.danger .data-info h4 { color: var(--error); } }
.data-info h4 { margin: 0 0 4px; font-size: 15px; } .data-info p { margin: 0; font-size: 13px; color: var(--text-secondary); }

.api-keys-list { margin-bottom: 24px; }
.api-key-item { display: flex; justify-content: space-between; align-items: center; padding: 16px; background: var(--bg-secondary); border-radius: var(--radius-md); margin-bottom: 12px; }
.key-info { display: flex; flex-direction: column; gap: 4px; }
.key-name { font-weight: 600; }
.key-value { font-family: monospace; font-size: 13px; color: var(--text-secondary); }
.key-created { font-size: 12px; color: var(--text-muted); }
.key-actions { display: flex; gap: 8px; }

.login-history { max-height: 400px; overflow-y: auto; }
.history-item { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid var(--border-light); }
.history-device { font-weight: 500; }
.history-ip { font-size: 13px; color: var(--text-secondary); margin-left: 12px; }
.history-time { font-size: 13px; color: var(--text-muted); }
</style>