<template>
  <div class="register-page">
    <div class="register-card">
      <div class="logo">
        <div class="logo-icon" aria-hidden="true">
          <span class="stem"></span>
          <span class="leaf leaf-a"></span>
          <span class="leaf leaf-b"></span>
          <span class="leaf leaf-c"></span>
        </div>
        <h1>创建账号</h1>
        <p>加入病虫害检测系统</p>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" @submit.prevent="handleRegister">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" size="large" :prefix-icon="User" :validate-event="false" />
        </el-form-item>
        <el-form-item prop="email">
          <el-input v-model="form.email" placeholder="邮箱" type="email" size="large" :prefix-icon="Message" :validate-event="false" />
        </el-form-item>
        <el-form-item prop="emailCode">
          <div class="code-row">
            <el-input v-model="form.emailCode" placeholder="邮箱验证码" size="large" :validate-event="false" />
            <el-button :disabled="sendingCode || codeCountdown > 0 || !form.email" @click="handleSendCode">
              {{ codeCountdown > 0 ? `${codeCountdown}s` : '发送验证码' }}
            </el-button>
          </div>
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码（至少6位）" size="large" :prefix-icon="Lock" show-password :validate-event="false" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="loading" class="register-btn" @click="handleRegister">注册</el-button>
        </el-form-item>
      </el-form>
      <div class="register-footer">已有账号？<router-link to="/login">立即登录</router-link></div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Message } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { authApi } from '@/api'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref()
const loading = ref(false)
const sendingCode = ref(false)
const codeCountdown = ref(0)
let codeTimer = null
const form = reactive({ username: '', email: '', emailCode: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }, { min: 3, message: '用户名至少3个字符', trigger: 'blur' }],
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '请输入正确的邮箱', trigger: 'blur' }],
  emailCode: [{ required: true, message: '请输入邮箱验证码', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }, { min: 6, message: '密码至少6位', trigger: 'blur' }]
}

async function handleSendCode() {
  if (!form.email) {
    ElMessage.warning('请先输入邮箱')
    return
  }
  sendingCode.value = true
  try {
    await authApi.sendEmailCode({ email: form.email, purpose: 'register' })
    ElMessage.success('验证码已发送，请查收邮箱')
    codeCountdown.value = 60
    if (codeTimer) clearInterval(codeTimer)
    codeTimer = setInterval(() => {
      codeCountdown.value = Math.max(0, codeCountdown.value - 1)
      if (codeCountdown.value === 0 && codeTimer) {
        clearInterval(codeTimer)
        codeTimer = null
      }
    }, 1000)
  } catch {}
  sendingCode.value = false
}

async function handleRegister() {
  try {
    await formRef.value.validate()
    loading.value = true
    await userStore.register({
      username: form.username,
      email: form.email,
      password: form.password,
      email_code: form.emailCode
    })
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch {}
  loading.value = false
}

onUnmounted(() => {
  if (codeTimer) clearInterval(codeTimer)
})
</script>

<style lang="scss" scoped>
.register-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #10b981 0%, #059669 100%); }
.register-card { width: 400px; padding: 48px; background: white; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.2); }
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
.register-btn { width: 100%; height: 44px; font-size: 16px; }
.register-footer { text-align: center; margin-top: 24px; font-size: 14px; color: var(--text-secondary); a { color: var(--primary); text-decoration: none; font-weight: 500; } }
.code-row { display: grid; grid-template-columns: 1fr 120px; gap: 10px; width: 100%; }
</style>
