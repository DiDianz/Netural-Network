<!-- src/views/login/index.vue -->
<template>
  <div class="login-container">
    <!-- 背景 -->
    <div class="login-bg">
      <div class="grid-lines"></div>
      <div class="gradient-orb orb-1"></div>
      <div class="gradient-orb orb-2"></div>
    </div>

    <div class="login-card">
      <!-- Logo -->
      <div class="login-header">
        <div class="logo-icon">
          <svg viewBox="0 0 48 48" fill="none">
            <path d="M24 4L6 14v20l18 10 18-10V14L24 4z" stroke="currentColor" stroke-width="2" fill="none"/>
            <circle cx="24" cy="24" r="6" fill="currentColor" opacity="0.8"/>
            <circle cx="14" cy="19" r="3" fill="currentColor" opacity="0.5"/>
            <circle cx="34" cy="19" r="3" fill="currentColor" opacity="0.5"/>
            <circle cx="14" cy="29" r="3" fill="currentColor" opacity="0.5"/>
            <circle cx="34" cy="29" r="3" fill="currentColor" opacity="0.5"/>
            <line x1="24" y1="24" x2="14" y2="19" stroke="currentColor" stroke-width="1" opacity="0.3"/>
            <line x1="24" y1="24" x2="34" y2="19" stroke="currentColor" stroke-width="1" opacity="0.3"/>
            <line x1="24" y1="24" x2="14" y2="29" stroke="currentColor" stroke-width="1" opacity="0.3"/>
            <line x1="24" y1="24" x2="34" y2="29" stroke="currentColor" stroke-width="1" opacity="0.3"/>
          </svg>
        </div>
        <h1 class="login-title">Neural Predict</h1>
        <p class="login-subtitle">神经网络实时预测系统</p>
      </div>

      <!-- 表单 -->
      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        class="login-form"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            size="large"
          >
            <template #prefix>
              <el-icon><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            show-password
          >
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="login-btn"
            :loading="loading"
            @click="handleLogin"
          >
            {{ loading ? '登录中...' : '登 录' }}
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-footer">
        <span>默认账号: admin / admin123</span>
      </div>
    </div>
  </div>
</template>

<!-- src/views/login/index.vue（只改 handleLogin 函数） -->
<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '../../stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const loginFormRef = ref(null)
const loading = ref(false)

const loginForm = reactive({
  username: 'admin',
  password: 'admin123'
})

const loginRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function handleLogin() {
  const valid = await loginFormRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    // 1. 登录获取 token
    await userStore.login(loginForm)

    // 2. 获取用户信息
    await userStore.fetchUserInfo()

    ElMessage.success('登录成功')

    // 3. 跳转
    const redirect = route.query.redirect || '/'
    await router.push(redirect)

    console.log('登录跳转完成, 目标:', redirect)
  } catch (error) {
    console.error('登录流程出错:', error)
    const msg = (error.response && error.response.data && error.response.data.detail) || '登录失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}
</script>


<!-- src/views/login/index.vue（只改 style 部分，template 和 script 不变） -->
<style scoped>
.login-container {
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  position: relative;
  overflow: hidden;
}

.login-bg {
  position: absolute;
  inset: 0;
}

.login-bg .grid-lines {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(var(--accent-bg-light) 1px, transparent 1px),
    linear-gradient(90deg, var(--accent-bg-light) 1px, transparent 1px);
  background-size: 60px 60px;
}

.login-bg .gradient-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  animation: float 20s ease-in-out infinite;
}

.login-bg .orb-1 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, var(--accent-glow), transparent 70%);
  top: -10%;
  right: -10%;
}

.login-bg .orb-2 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, var(--info-bg), transparent 70%);
  bottom: -10%;
  left: -5%;
  animation-delay: -10s;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  25% { transform: translate(30px, -20px); }
  50% { transform: translate(-20px, 30px); }
  75% { transform: translate(20px, 20px); }
}

.login-card {
  position: relative;
  z-index: 10;
  width: 420px;
  padding: 48px 40px;
  background: var(--bg-overlay);
  backdrop-filter: blur(20px);
  border: 1px solid var(--border-secondary);
  border-radius: 16px;
  box-shadow: var(--shadow-dropdown);
}

.login-header {
  text-align: center;
  margin-bottom: 36px;
}

.login-header .logo-icon {
  width: 56px;
  height: 56px;
  margin: 0 auto 16px;
  color: var(--accent);
  height: 100%;
}

.login-header .login-title {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.login-header .logo-icon svg {
  width:  6px;
}

.login-header .login-subtitle {
  font-size: 13px;
  color: var(--text-muted);
  letter-spacing: 0.05em;
}

.login-btn {
  width: 100%;
  height: 46px;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.1em;
  background: var(--accent) !important;
  border: none !important;
  transition: all 0.3s ease;
}

.login-btn:hover {
  background: var(--accent-hover) !important;
  box-shadow: 0 8px 24px var(--accent-glow);
}

.login-footer {
  text-align: center;
  margin-top: 24px;
  font-size: 12px;
  color: var(--text-disabled);
}
</style>
