<template>
  <div class="register-page">
    <div class="register-card">
      <div class="logo">
        <div class="logo-icon">🌾</div>
        <h1>创建账号</h1>
        <p>加入病虫害检测系统</p>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" @submit.prevent="handleRegister">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" size="large" :prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="email">
          <el-input v-model="form.email" placeholder="邮箱" type="email" size="large" :prefix-icon="Message" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码（至少6位）" size="large" :prefix-icon="Lock" show-password />
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
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Message } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref()
const loading = ref(false)
const form = reactive({ username: '', email: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }, { min: 3, message: '用户名至少3个字符', trigger: 'blur' }],
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '请输入正确的邮箱', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }, { min: 6, message: '密码至少6位', trigger: 'blur' }]
}

async function handleRegister() {
  try {
    await formRef.value.validate()
    loading.value = true
    await userStore.register(form)
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch {}
  loading.value = false
}
</script>

<style lang="scss" scoped>
.register-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #10b981 0%, #059669 100%); }
.register-card { width: 400px; padding: 48px; background: white; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.2); }
.logo { text-align: center; margin-bottom: 32px; .logo-icon { font-size: 56px; margin-bottom: 16px; } h1 { font-size: 24px; font-weight: 600; margin-bottom: 8px; } p { font-size: 14px; color: var(--text-secondary); } }
.register-btn { width: 100%; height: 44px; font-size: 16px; }
.register-footer { text-align: center; margin-top: 24px; font-size: 14px; color: var(--text-secondary); a { color: var(--primary); text-decoration: none; font-weight: 500; } }
</style>
