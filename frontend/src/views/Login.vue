<template>
  <div class="login-page">
    <div class="login-card">
      <div class="logo">
        <div class="logo-icon">🌾</div>
        <h1>病虫害检测系统</h1>
        <p>智能农业 · 精准检测</p>
      </div>
      
      <el-form ref="formRef" :model="form" :rules="rules" @submit.prevent="handleLogin">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" size="large" :prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码" size="large" :prefix-icon="Lock" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="loading" class="login-btn" @click="handleLogin">登录</el-button>
        </el-form-item>
      </el-form>
      
      <div class="login-footer">
        还没有账号？<router-link to="/register">立即注册</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref()
const loading = ref(false)
const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
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
</script>

<style lang="scss" scoped>
.login-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #10b981 0%, #059669 100%); }
.login-card { width: 400px; padding: 48px; background: white; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.2); }
.logo { text-align: center; margin-bottom: 32px; .logo-icon { font-size: 56px; margin-bottom: 16px; } h1 { font-size: 24px; font-weight: 600; margin-bottom: 8px; } p { font-size: 14px; color: var(--text-secondary); } }
.login-btn { width: 100%; height: 44px; font-size: 16px; }
.login-footer { text-align: center; margin-top: 24px; font-size: 14px; color: var(--text-secondary); a { color: var(--primary); text-decoration: none; font-weight: 500; } }
</style>
