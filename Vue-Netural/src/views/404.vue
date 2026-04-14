<!-- src/views/404.vue -->
<template>
  <div class="not-found">
    <h1>404</h1>
    <p>页面不存在</p>
    <el-button type="primary" @click="router.push('/')">返回首页</el-button>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<style scoped>
.not-found {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  gap: 16px;
}

.not-found h1 {
  font-size: 80px;
  font-weight: 700;
  color: var(--accent);
}

.not-found p {
  font-size: 16px;
  color: var(--text-muted);
}
</style>
