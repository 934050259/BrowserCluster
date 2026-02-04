<template>
  <div class="login-container">
    <!-- 浅色动态网格背景 -->
    <div class="mesh-background">
      <div class="mesh-blob blob-1"></div>
      <div class="mesh-blob blob-2"></div>
      <div class="mesh-blob blob-3"></div>
    </div>
    
    <!-- 粒子 Canvas -->
    <canvas ref="particleCanvas" class="particle-canvas"></canvas>

    <div class="login-box">
      <div class="login-header">
        <div class="logo-wrapper">
          <svg class="logo-svg" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <h1>BrowserCluster</h1>
        <p>分布式浏览器集群管理系统</p>
      </div>

      <el-form :model="loginForm" :rules="rules" ref="loginFormRef" class="login-form" @keyup.enter="handleLogin">
        <el-form-item prop="username">
          <el-input v-model="loginForm.username" placeholder="用户名" :prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="loginForm.password" type="password" placeholder="密码" :prefix-icon="Lock" show-password />
        </el-form-item>
        <el-form-item>
          <el-button :loading="loading" type="primary" class="login-button" @click="handleLogin">
            <span v-if="!loading">登 录</span>
            <span v-else>正在登录...</span>
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="login-footer">
        <p>&copy; 2026 BrowserCluster. All rights reserved.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()

const loginFormRef = ref(null)
const loading = ref(false)
const particleCanvas = ref(null)

const loginForm = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

// 粒子系统逻辑
let animationId = null
onMounted(() => {
  const canvas = particleCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  let particles = []
  
  const resize = () => {
    canvas.width = window.innerWidth
    canvas.height = window.innerHeight
  }
  
  class Particle {
    constructor() {
      this.init()
    }
    init() {
      this.x = Math.random() * canvas.width
      this.y = Math.random() * canvas.height
      this.size = Math.random() * 2 + 1
      this.speedX = Math.random() * 0.5 - 0.25
      this.speedY = Math.random() * 0.5 - 0.25
      this.opacity = Math.random() * 0.5 + 0.2
    }
    update() {
      this.x += this.speedX
      this.y += this.speedY
      if (this.x > canvas.width || this.x < 0 || this.y > canvas.height || this.y < 0) {
        this.init()
      }
    }
    draw() {
      ctx.fillStyle = `rgba(59, 130, 246, ${this.opacity})`
      ctx.beginPath()
      ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
      ctx.fill()
    }
  }

  const initParticles = () => {
    particles = []
    const count = Math.floor((canvas.width * canvas.height) / 15000)
    for (let i = 0; i < count; i++) {
      particles.push(new Particle())
    }
  }

  const animate = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    particles.forEach(p => {
      p.update()
      p.draw()
    })
    animationId = requestAnimationFrame(animate)
  }

  window.addEventListener('resize', () => {
    resize()
    initParticles()
  })
  
  resize()
  initParticles()
  animate()
})

onUnmounted(() => {
  if (animationId) cancelAnimationFrame(animationId)
})

const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        await authStore.login(loginForm.username, loginForm.password)
        ElMessage.success('登录成功')
        router.push('/')
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || '用户名或密码错误')
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #f8fafc; /* 浅色背景 */
  position: relative;
  overflow: hidden;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

/* 浅色网格背景 */
.mesh-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  background-color: #f8fafc;
  background-image: 
    radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.05) 0, transparent 50%), 
    radial-gradient(at 100% 0%, rgba(139, 92, 246, 0.05) 0, transparent 50%),
    radial-gradient(at 100% 100%, rgba(37, 99, 235, 0.03) 0, transparent 50%),
    radial-gradient(at 0% 100%, rgba(29, 78, 216, 0.03) 0, transparent 50%);
}

.mesh-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.5;
  animation: blob-float 20s infinite alternate ease-in-out;
  will-change: transform;
  transform: translate3d(0, 0, 0);
}

.blob-1 {
  width: 600px;
  height: 600px;
  background: rgba(59, 130, 246, 0.08);
  top: -100px;
  left: -100px;
}

.blob-2 {
  width: 500px;
  height: 500px;
  background: rgba(139, 92, 246, 0.08);
  bottom: -50px;
  right: -50px;
  animation-duration: 25s;
  animation-delay: -5s;
}

.blob-3 {
  width: 400px;
  height: 400px;
  background: rgba(30, 64, 175, 0.05);
  top: 40%;
  left: 30%;
  animation-duration: 30s;
  animation-delay: -10s;
}

@keyframes blob-float {
  0% { transform: translate3d(0, 0, 0) scale(1); }
  100% { transform: translate3d(5%, 5%, 0) scale(1.05); }
}

.particle-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
  pointer-events: none;
}

.login-box {
  width: 420px;
  padding: 40px;
  background: rgb(232, 243, 248); /* 亮色玻璃拟态 */
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 24px;
  box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.05);
  z-index: 10;
  position: relative;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.login-box:hover {
  transform: translateY(-4px);
  box-shadow: 0 30px 60px -12px rgba(0, 0, 0, 0.08);
}

.login-header {
  text-align: center;
  margin-bottom: 40px;
}

.logo-wrapper {
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  border-radius: 18px;
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 0 auto 20px;
  box-shadow: 0 10px 20px -5px rgba(59, 130, 246, 0.3);
}

.logo-svg {
  width: 32px;
  height: 32px;
  color: white;
}

.login-header h1 {
  font-size: 28px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 8px;
  letter-spacing: -0.5px;
}

.login-header p {
  color: #64748b;
  font-size: 14px;
}

.login-form :deep(.el-input__wrapper) {
  background: #ffffff !important;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02) !important;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 8px 15px;
  transition: all 0.3s;
}

.login-form :deep(.el-input__wrapper:hover) {
  border-color: #cbd5e1;
}

.login-form :deep(.el-input__wrapper.is-focus) {
  border-color: #3b82f6;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1) !important;
}

.login-form :deep(.el-input__inner) {
  color: #1e293b !important;
  height: 40px;
}

.login-form :deep(.el-input__prefix-icon) {
  color: #94a3b8;
}

.login-button {
  width: 100%;
  height: 48px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  border: none;
  margin-top: 10px;
  transition: all 0.3s;
}

.login-button:hover {
  transform: translateY(-1px);
  filter: brightness(1.05);
  box-shadow: 0 10px 20px -5px rgba(59, 130, 246, 0.4);
}

.login-footer {
  text-align: center;
  margin-top: 30px;
}

.login-footer p {
  color: #94a3b8;
  font-size: 12px;
}

@media (max-width: 480px) {
  .login-box {
    width: 90%;
    padding: 30px 20px;
  }
}
</style>
