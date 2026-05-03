<template>
  <div class="login-page">
    <div class="login-card">
      <div class="logo">
        <div class="logo-icon" aria-hidden="true">
          <span class="stem"></span>
          <span class="leaf leaf-a"></span>
          <span class="leaf leaf-b"></span>
          <span class="leaf leaf-c"></span>
        </div>
        <h1>病虫害检测系统</h1>
        <p>智能农业 · 精准检测</p>
      </div>
      
      <el-form ref="formRef" :model="form" :rules="rules" @submit.prevent="handleLogin">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" size="large" :prefix-icon="User" :validate-event="false" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码" size="large" :prefix-icon="Lock" show-password :validate-event="false" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="loading" class="login-btn" @click="handleLogin">登录</el-button>
        </el-form-item>
      </el-form>
      <div class="forgot-row">
        <el-link type="primary" :underline="false" @click="resetDialogVisible = true">忘记密码？</el-link>
      </div>
      
      <div class="login-footer">
        还没有账号？<router-link to="/register">立即注册</router-link>
      </div>
    </div>

    <el-dialog v-model="resetDialogVisible" title="找回密码" width="420px">
      <el-form :model="resetForm" :rules="resetRules" ref="resetFormRef" label-position="top">
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="resetForm.email" placeholder="请输入注册邮箱" />
        </el-form-item>
        <el-form-item label="验证码" prop="code">
          <div class="code-row">
            <el-input v-model="resetForm.code" placeholder="请输入验证码" />
            <el-button :disabled="sendingResetCode || resetCountdown > 0 || !resetForm.email" @click="sendResetCode">
              {{ resetCountdown > 0 ? `${resetCountdown}s` : '发送验证码' }}
            </el-button>
          </div>
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="resetForm.newPassword" type="password" show-password placeholder="至少6位" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="resettingPassword" @click="handleResetPassword">重置密码</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { authApi } from '@/api'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref()
const loading = ref(false)
const form = reactive({ username: '', password: '' })
const resetDialogVisible = ref(false)
const resetFormRef = ref()
const sendingResetCode = ref(false)
const resetCountdown = ref(0)
const resettingPassword = ref(false)
let resetTimer = null
const resetForm = reactive({
  email: '',
  code: '',
  newPassword: ''
})
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}
const resetRules = {
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '请输入正确的邮箱', trigger: 'blur' }],
  code: [{ required: true, message: '请输入验证码', trigger: 'blur' }],
  newPassword: [{ required: true, message: '请输入新密码', trigger: 'blur' }, { min: 6, message: '密码至少6位', trigger: 'blur' }]
}

async function handleLogin() {
  try {
    await formRef.value.validate()
    loading.value = true
    await userStore.login(form.username, form.password)
    ElMessage.success('登录成功')
    router.push('/')
  } catch {}
  loading.value = false
}

async function sendResetCode() {
  if (!resetForm.email) {
    ElMessage.warning('请先输入邮箱')
    return
  }
  sendingResetCode.value = true
  try {
    await authApi.sendResetCode({ email: resetForm.email })
    ElMessage.success('验证码已发送，请查收邮箱')
    resetCountdown.value = 60
    if (resetTimer) clearInterval(resetTimer)
    resetTimer = setInterval(() => {
      resetCountdown.value = Math.max(0, resetCountdown.value - 1)
      if (resetCountdown.value === 0 && resetTimer) {
        clearInterval(resetTimer)
        resetTimer = null
      }
    }, 1000)
  } catch {}
  sendingResetCode.value = false
}

async function handleResetPassword() {
  try {
    await resetFormRef.value.validate()
    resettingPassword.value = true
    await authApi.resetPassword({
      email: resetForm.email,
      code: resetForm.code,
      new_password: resetForm.newPassword
    })
    ElMessage.success('密码重置成功，请使用新密码登录')
    resetDialogVisible.value = false
    resetForm.email = ''
    resetForm.code = ''
    resetForm.newPassword = ''
  } catch {}
  resettingPassword.value = false
}

onUnmounted(() => {
  if (resetTimer) clearInterval(resetTimer)
})
</script>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.login-card {
  width: 400px;
  padding: 48px;
  background: #ffffff;
  border-radius: 16px;
  border: 1px solid #e6edf4;
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.1);
}

.logo {
  text-align: center;
  margin-bottom: 32px;

  .logo-icon {
    width: 68px;
    height: 68px;
    margin: 0 auto 16px;
    border-radius: 18px;
    background: linear-gradient(145deg, #eef7ff 0%, #dceeff 100%);
    border: 1px solid #bfd9ff;
    position: relative;
  }

  .stem {
    position: absolute;
    left: 50%;
    bottom: 14px;
    transform: translateX(-50%);
    width: 6px;
    height: 34px;
    border-radius: 999px;
    background: linear-gradient(180deg, #0ea5a4 0%, #1663c7 100%);
  }

  .leaf {
    position: absolute;
    width: 18px;
    height: 9px;
    border-radius: 10px 10px 10px 2px;
    background: linear-gradient(120deg, #16a34a, #0f766e);
  }

  .leaf-a { left: 22px; bottom: 18px; transform: rotate(-32deg); }
  .leaf-b { left: 34px; bottom: 26px; transform: rotate(28deg); }
  .leaf-c { left: 18px; bottom: 30px; transform: rotate(-18deg); }

  h1 { font-size: 24px; font-weight: 600; margin-bottom: 8px; }
  p { font-size: 14px; color: var(--text-secondary); }
}

.login-btn { width: 100%; height: 44px; font-size: 16px; }
.forgot-row { margin-top: 4px; text-align: right; }
.login-footer { text-align: center; margin-top: 24px; font-size: 14px; color: var(--text-secondary); a { color: var(--primary); text-decoration: none; font-weight: 500; } }
.code-row { display: grid; grid-template-columns: 1fr 120px; gap: 10px; width: 100%; }
</style>
