<template>
  <div class="login-container">
    <div class="noise-overlay"></div>
    <div class="aurora-bg">
      <div class="aurora-layer layer-1"></div>
      <div class="aurora-layer layer-2"></div>
      <div class="aurora-layer layer-3"></div>
      <div class="aurora-layer layer-4"></div>
    </div>
    <div class="animated-bg">
      <div class="bg-circle circle-1" :style="{ transform: `translate3d(${mousePosition.x * 30}px, ${mousePosition.y * 30}px, 0)` }"></div>
      <div class="bg-circle circle-2" :style="{ transform: `translate3d(${mousePosition.x * -40}px, ${mousePosition.y * -40}px, 0)` }"></div>
      <div class="bg-circle circle-3" :style="{ transform: `translate3d(${mousePosition.x * 20}px, ${mousePosition.y * -20}px, 0)` }"></div>
      
      <!-- 减少几何装饰元素数量 -->
      <div class="geo-element geo-square" :style="{ transform: `translate3d(${mousePosition.x * 15}px, ${mousePosition.y * 15}px, 0) rotate(${mousePosition.x * 20}deg)` }"></div>
      <div class="geo-element geo-triangle" :style="{ transform: `translate3d(${mousePosition.x * -25}px, ${mousePosition.y * 25}px, 0) rotate(${mousePosition.y * -30}deg)` }"></div>
      <div class="geo-element geo-circle" :style="{ transform: `translate3d(${mousePosition.x * -15}px, ${mousePosition.y * -25}px, 0)` }"></div>
      <div class="geo-element geo-line" :style="{ transform: `translate3d(${mousePosition.x * 10}px, ${mousePosition.y * -15}px, 0) rotate(-45deg)` }"></div>

      <!-- 减少流星效果数量 -->
      <div class="meteors">
        <div v-for="i in 3" :key="i" class="meteor"></div>
      </div>

      <div class="particles">
        <div v-for="i in 15" :key="i" class="particle"></div>
      </div>
    </div>
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
        <el-form-item prop="username" class="animated-input">
          <el-input v-model="loginForm.username" placeholder="用户名" :prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="password" class="animated-input">
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

const loginForm = reactive({
  username: '',
  password: ''
})

const mousePosition = reactive({
  x: 0,
  y: 0
})

let rafId = null
const handleMouseMove = (e) => {
  if (rafId) return
  
  rafId = requestAnimationFrame(() => {
    const { clientX, clientY } = e
    const { innerWidth, innerHeight } = window
    mousePosition.x = (clientX / innerWidth - 0.5) * 2
    mousePosition.y = (clientY / innerHeight - 0.5) * 2
    rafId = null
  })
}

onMounted(() => {
  window.addEventListener('mousemove', handleMouseMove, { passive: true })
})

onUnmounted(() => {
  window.removeEventListener('mousemove', handleMouseMove)
  if (rafId) cancelAnimationFrame(rafId)
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

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
  background: #f0f4f8; /* 基础浅色背景 */
  position: relative;
  overflow: hidden;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.noise-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  /* 使用静态噪声图片代替 SVG 滤镜以提升性能 */
  background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAMAAAAp4XiDAAAAUVBMVEWFhYWDg4N3d3dtbW1mzM2NjY3Pz8/T09PZ2dnMzMxubm5qampnZ2dxcXG9vb2fn5+tra2Ojo6MjIy0tLRzc3NDQ0N6enp/f39paWlkZGRhYWFnLSNIAAAAB3RSTlNDI0hJZmZzyPxjAAAAVElEQVR4Xu3XqQ4AIAwEQSgS/v/H98pS6AgT37iaZpYp9v45HS988cc8L3yx86IsfPFeFp546YpXvPAnS1/8is9uOTo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6PiaYAWcl9QnJAAAAAElFTkSuQmCC");
  background-repeat: repeat;
  opacity: 0.05;
  pointer-events: none;
  z-index: 2;
}

/* Aurora 背景层 */
.aurora-bg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  filter: blur(80px); /* 略微降低模糊半径 */
  opacity: 0.5; /* 降低透明度 */
  z-index: 0;
  will-change: transform;
}

.aurora-layer {
  position: absolute;
  width: 150%;
  height: 150%;
  top: -25%;
  left: -25%;
  animation: aurora-flow 20s infinite alternate ease-in-out;
  will-change: transform;
}

.layer-1 {
  background: radial-gradient(circle at 20% 30%, #4facfe 0%, transparent 50%);
  animation-duration: 25s;
}

.layer-2 {
  background: radial-gradient(circle at 80% 20%, #00f2fe 0%, transparent 50%);
  animation-duration: 18s;
  animation-delay: -5s;
}

.layer-3 {
  background: radial-gradient(circle at 40% 80%, #a8edea 0%, transparent 50%);
  animation-duration: 22s;
  animation-delay: -10s;
}

.layer-4 {
  background: radial-gradient(circle at 70% 70%, #fedfe1 0%, transparent 50%);
  animation-duration: 28s;
  animation-delay: -15s;
}

.layer-5 {
  background: radial-gradient(circle at 10% 90%, #89f7fe 0%, transparent 40%);
  animation-duration: 32s;
  animation-delay: -3s;
}

.layer-6 {
  background: radial-gradient(circle at 90% 10%, #66a6ff 0%, transparent 40%);
  animation-duration: 26s;
  animation-delay: -8s;
}

@keyframes aurora-flow {
  0% { transform: rotate3d(0, 0, 1, 0deg) translate3d(0, 0, 0) scale(1); }
  50% { transform: rotate3d(0, 0, 1, 8deg) translate3d(3%, 3%, 0) scale(1.1); }
  100% { transform: rotate3d(0, 0, 1, -8deg) translate3d(-3%, -3%, 0) scale(1); }
}

.animated-bg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
}

/* 几何装饰元素 */
.geo-element {
  position: absolute;
  border: 1px solid rgba(255, 255, 255, 0.4);
  background: rgba(255, 255, 255, 0.1);
  /* 移除 backdrop-filter 以提升性能，或显著降低模糊度 */
  backdrop-filter: blur(2px);
  z-index: 1;
  transition: transform 0.3s cubic-bezier(0.1, 0, 0.3, 1);
  will-change: transform;
}

.geo-square {
  width: 100px;
  height: 100px;
  top: 15%;
  left: 10%;
  border-radius: 20px;
  animation: float-slow 15s infinite ease-in-out;
}

.geo-triangle {
  width: 80px;
  height: 80px;
  bottom: 15%;
  right: 15%;
  clip-path: polygon(50% 0%, 0% 100%, 100% 100%);
  animation: float-slow 18s infinite ease-in-out reverse;
}

.geo-circle {
  width: 120px;
  height: 120px;
  top: 40%;
  right: 10%;
  border-radius: 50%;
  animation: float-slow 20s infinite ease-in-out;
  animation-delay: -5s;
}

.geo-line {
  width: 200px;
  height: 2px;
  top: 60%;
  left: -50px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.5), transparent);
  border: none;
  animation: scan 12s infinite linear;
}

/* 流星效果 */
.meteors {
  position: absolute;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.meteor {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 2px;
  height: 2px;
  background: #fff;
  border-radius: 50%;
  box-shadow: 0 0 10px rgba(255, 255, 255, 0.8); /* 简化阴影 */
  animation: meteor-anim 3s linear infinite;
  opacity: 0;
  will-change: transform;
}

.meteor::before {
  content: '';
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 200px; /* 缩短尾迹 */
  height: 1px;
  background: linear-gradient(90deg, #fff, transparent);
}

.meteor:nth-child(1) { top: 10%; left: 30%; animation-delay: 0s; animation-duration: 4s; }
.meteor:nth-child(2) { top: 20%; left: 60%; animation-delay: 1.5s; animation-duration: 3s; }
.meteor:nth-child(3) { top: 50%; left: 80%; animation-delay: 4s; animation-duration: 5s; }

@keyframes meteor-anim {
  0% { transform: rotate3d(0, 0, 1, -45deg) translate3d(0, 0, 0); opacity: 0; }
  10% { opacity: 1; }
  100% { transform: rotate3d(0, 0, 1, -45deg) translate3d(-1000px, 0, 0); opacity: 0; }
}

@keyframes float-slow {
  0%, 100% { transform: translate3d(0, 0, 0) rotate3d(0, 0, 1, 0deg); }
  50% { transform: translate3d(30px, -40px, 0) rotate3d(0, 0, 1, 15deg); }
}

@keyframes scan {
  0% { transform: rotate3d(0, 0, 1, -45deg) translate3d(-100%, -100%, 0); opacity: 0; }
  20% { opacity: 0.6; }
  80% { opacity: 0.6; }
  100% { transform: rotate3d(0, 0, 1, -45deg) translate3d(300%, 300%, 0); opacity: 0; }
}

.bg-circle {
  position: absolute;
  border-radius: 50%;
  filter: blur(50px); /* 降低模糊 */
  opacity: 0.5;
  animation: float 25s infinite alternate ease-in-out;
  transition: transform 0.2s cubic-bezier(0.1, 0, 0.3, 1);
  will-change: transform;
}

@media (prefers-reduced-motion: reduce) {
  .bg-circle, .particle, .login-box, .logo-wrapper::after, .aurora-layer, .geo-element, .meteor {
    animation: none !important;
    transition: none !important;
    transform: none !important;
  }
}

.circle-1 {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(64, 158, 255, 0.3) 0%, rgba(64, 158, 255, 0) 70%);
  top: -200px;
  left: -100px;
}

.circle-2 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(103, 194, 58, 0.2) 0%, rgba(103, 194, 58, 0) 70%);
  bottom: -150px;
  right: -100px;
  animation-delay: -7s;
}

.circle-3 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(255, 144, 0, 0.15) 0%, rgba(255, 144, 0, 0) 70%);
  top: 30%;
  right: 20%;
  animation-delay: -12s;
}

@keyframes float {
  0% { transform: translate3d(0, 0, 0) scale(1) rotate3d(0, 0, 1, 0deg); }
  50% { transform: translate3d(60px, 40px, 0) scale(1.05) rotate3d(0, 0, 1, 5deg); }
  100% { transform: translate3d(-40px, 80px, 0) scale(0.95) rotate3d(0, 0, 1, -5deg); }
}

.particles {
  position: absolute;
  width: 100%;
  height: 100%;
}

.particle {
  position: absolute;
  width: 4px; /* 减小粒子尺寸 */
  height: 4px;
  background: rgba(255, 255, 255, 0.4);
  border-radius: 50%;
  /* 移除粒子阴影以提升性能 */
  animation: move 20s infinite linear;
  will-change: transform;
}

@keyframes move {
  0% { transform: translate3d(0, 110vh, 0) scale(0); opacity: 0; }
  20% { opacity: 0.6; }
  80% { opacity: 0.6; }
  100% { transform: translate3d(50px, -10vh, 0) scale(1); opacity: 0; }
}

/* 随机生成粒子位置和动画延迟 */
.particle:nth-child(1) { left: 12%; animation-delay: 0s; width: 4px; height: 4px; }
.particle:nth-child(2) { left: 25%; animation-delay: 3s; width: 6px; height: 6px; }
.particle:nth-child(3) { left: 38%; animation-delay: 6s; width: 3px; height: 3px; }
.particle:nth-child(4) { left: 42%; animation-delay: 9s; width: 5px; height: 5px; }
.particle:nth-child(5) { left: 55%; animation-delay: 12s; width: 4px; height: 4px; }
.particle:nth-child(6) { left: 68%; animation-delay: 1.5s; width: 7px; height: 7px; }
.particle:nth-child(7) { left: 72%; animation-delay: 4.5s; width: 3px; height: 3px; }
.particle:nth-child(8) { left: 85%; animation-delay: 7.5s; width: 5px; height: 5px; }
.particle:nth-child(9) { left: 92%; animation-delay: 10.5s; width: 4px; height: 4px; }
.particle:nth-child(10) { left: 18%; animation-delay: 13.5s; width: 6px; height: 6px; }
.particle:nth-child(11) { left: 28%; animation-delay: 0.8s; width: 4px; height: 4px; }
.particle:nth-child(12) { left: 33%; animation-delay: 3.8s; width: 5px; height: 5px; }
.particle:nth-child(13) { left: 48%; animation-delay: 6.8s; width: 3px; height: 3px; }
.particle:nth-child(14) { left: 52%; animation-delay: 9.8s; width: 6px; height: 6px; }
.particle:nth-child(15) { left: 63%; animation-delay: 12.8s; width: 4px; height: 4px; }
.particle:nth-child(16) { left: 78%; animation-delay: 2.2s; width: 5px; height: 5px; }
.particle:nth-child(17) { left: 82%; animation-delay: 5.2s; width: 4px; height: 4px; }
.particle:nth-child(18) { left: 98%; animation-delay: 8.2s; width: 3px; height: 3px; }
.particle:nth-child(19) { left: 8%; animation-delay: 11.2s; width: 6px; height: 6px; }
.particle:nth-child(20) { left: 47%; animation-delay: 14.2s; width: 4px; height: 4px; }

.login-box {
  width: 420px;
  padding: 50px 40px;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(15px) saturate(160%); /* 降低模糊半径以提升性能 */
  -webkit-backdrop-filter: blur(15px) saturate(160%);
  border-radius: 32px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.05);
  z-index: 10;
  border: 1px solid rgba(255, 255, 255, 0.8);
  transition: transform 0.2s cubic-bezier(0.1, 0, 0.3, 1), box-shadow 0.4s ease;
  will-change: transform;
}

.login-box:hover {
  box-shadow: 0 30px 60px rgba(0, 0, 0, 0.08);
}

.login-header {
  text-align: center;
  margin-bottom: 40px;
}

.logo-wrapper {
  width: 80px;
  height: 80px;
  margin: 0 auto 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 22px;
  display: flex;
  justify-content: center;
  align-items: center;
  color: white;
  box-shadow: 0 12px 24px rgba(118, 75, 162, 0.25);
  position: relative;
  overflow: hidden;
  transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  cursor: pointer;
}

.logo-wrapper:hover {
  transform: scale(1.1) rotate(5deg);
  box-shadow: 0 15px 30px rgba(118, 75, 162, 0.4);
}

.logo-wrapper::after {
  content: '';
  position: absolute;
  top: -100%;
  left: -100%;
  width: 300%;
  height: 300%;
  background: linear-gradient(45deg, transparent, rgba(255,255,255,0.4), transparent);
  transform: rotate(45deg);
  animation: shine 4s infinite;
}

@keyframes shine {
  0% { transform: translate(-50%, -50%) rotate(45deg); }
  100% { transform: translate(50%, 50%) rotate(45deg); }
}

.logo-svg {
  width: 40px;
  height: 40px;
}

.login-header h1 {
  font-size: 34px;
  font-weight: 800;
  background: linear-gradient(135deg, #1a1a1a 0%, #4a4a4a 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0 0 10px;
  letter-spacing: -1px;
}

.login-header p {
  color: #64748b;
  font-size: 15px;
  margin: 0;
  font-weight: 500;
}

.login-form :deep(.el-input__wrapper) {
  background-color: rgba(248, 250, 252, 0.8);
  box-shadow: 0 0 0 1px #e2e8f0 inset;
  border-radius: 12px;
  padding: 8px 15px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.login-form :deep(.el-input__wrapper.is-focus) {
  background-color: #ffffff;
  box-shadow: 0 0 0 2px #3b82f6 inset;
  transform: translateY(-2px);
}

.login-form :deep(.el-input__prefix) {
  transition: all 0.3s ease;
}

.login-form :deep(.el-input__wrapper.is-focus .el-input__prefix) {
  color: #3b82f6;
  transform: scale(1.2);
}

.login-button {
  width: 100%;
  height: 50px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  border: none;
  box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.3);
  margin-top: 10px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.login-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 20px 25px -5px rgba(59, 130, 246, 0.4);
  filter: brightness(1.05);
}

.login-button:active {
  transform: translateY(1px) scale(0.98);
  box-shadow: 0 5px 10px -3px rgba(59, 130, 246, 0.3);
}

.login-button::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.2),
    transparent
  );
  transition: 0.5s;
}

.login-button:hover::before {
  left: 100%;
}

.login-footer {
  text-align: center;
  margin-top: 30px;
  color: #94a3b8;
  font-size: 13px;
}

@media (max-width: 480px) {
  .login-box {
    width: 90%;
    padding: 40px 25px;
  }
}
</style>
