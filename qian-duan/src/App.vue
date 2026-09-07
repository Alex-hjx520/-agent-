<template>
  <!-- 启动动画页：点击「进入选型系统」后才进入使用页面 -->
  <div v-if="!entered" class="splash">
    <div class="splash-inner">
      <div class="splash-logo">
        <el-icon :size="56"><Cpu /></el-icon>
      </div>
      <h1 class="splash-title">制冷设备流量选型系统</h1>
      <p class="splash-sub">CoolProp 物性计算 · 全类型候选 · 质量流量窗口达标</p>
      <div class="splash-badges">
        <el-tag size="small" effect="plain">R410A / R32 / R134a …</el-tag>
        <el-tag size="small" effect="plain">表单 / 对话</el-tag>
        <el-tag size="small" effect="plain">报告导出</el-tag>
      </div>
      <el-button type="primary" size="large" class="splash-btn" @click="entered = true">
        进入选型系统
      </el-button>
      <p class="splash-foot">
        <span :class="online ? 'dot on' : 'dot'"></span>
        {{ online ? '后端在线' : '后端未连接' }}
      </p>
    </div>
  </div>

  <!-- 使用页面 -->
  <el-container v-else class="app-shell">
    <el-header class="app-header">
      <div class="brand">
        <el-icon :size="20"><Cpu /></el-icon>
        <span>制冷设备流量选型系统</span>
        <el-tag v-if="online" size="small" type="success" style="margin-left: 8px">后端在线</el-tag>
        <el-tag v-else size="small" type="danger" style="margin-left: 8px">后端未连接</el-tag>
      </div>
      <div class="header-right">
        <el-button size="small" text @click="entered = false">返回启动页</el-button>
      </div>
    </el-header>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const entered = ref(false)
const online = ref(false)

onMounted(async () => {
  try {
    await fetch('/health')
    online.value = true
  } catch {
    online.value = false
  }
})
</script>

<style scoped>
/* ---------- 启动动画页 ---------- */
.splash {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(1100px 600px at 20% -10%, rgba(58, 160, 255, 0.18), transparent 60%),
    radial-gradient(900px 500px at 90% 110%, rgba(47, 195, 161, 0.12), transparent 60%),
    var(--el-bg-color-page);
}
.splash-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18px;
  padding: 40px;
  text-align: center;
}
.splash-logo {
  width: 120px;
  height: 120px;
  border-radius: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: linear-gradient(135deg, #3aa0ff, #2fc3a1);
  box-shadow: 0 18px 46px rgba(58, 160, 255, 0.35);
  animation: logoFloat 2.4s ease-in-out infinite;
}
@keyframes logoFloat {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-12px) scale(1.04); }
}
.splash-title {
  font-size: 30px;
  margin: 0;
  color: var(--el-text-color-primary);
  animation: fadeUp 0.8s ease both;
}
.splash-sub {
  color: var(--el-text-color-secondary);
  font-size: 14px;
  margin: 0;
  animation: fadeUp 0.8s 0.15s ease both;
}
.splash-badges {
  display: flex;
  gap: 8px;
  animation: fadeUp 0.8s 0.3s ease both;
}
.splash-btn {
  margin-top: 10px;
  min-width: 220px;
  animation: fadeUp 0.8s 0.45s ease both;
}
.splash-foot {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  display: flex;
  align-items: center;
  gap: 6px;
  animation: fadeUp 0.8s 0.6s ease both;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--el-color-danger);
}
.dot.on {
  background: var(--el-color-success);
}
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ---------- 使用页 ---------- */
.app-shell { height: 100vh; }
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  border-bottom: 1px solid var(--el-border-color-light);
  background: var(--el-bg-color);
}
.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 16px;
}
.header-right { display: flex; align-items: center; }
.app-main {
  padding: 12px 16px;
  background: var(--el-fill-color-light);
  overflow: hidden;
}
</style>
