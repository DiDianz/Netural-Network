<!-- src/components/ControlPanel.vue -->
<template>
  <div class="control-panel">
    <div class="control-row">
      <el-button type="primary" :disabled="connectionState === 'open'" @click="$emit('start')">▶ 开始预测</el-button>
      <el-button type="danger" :disabled="connectionState === 'closed'" @click="$emit('stop')">■ 停止</el-button>
      <el-button @click="$emit('clear')">清空</el-button>
    </div>
    <div class="control-row">
      <span class="slider-label">预测间隔: {{ interval.toFixed(1) }}s</span>
      <el-slider :model-value="interval" :min="0.1" :max="5" :step="0.1" @input="$emit('update:interval', $event)" style="flex: 1" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  connectionState: String,
  interval: Number
})
defineEmits(['start', 'stop', 'clear', 'update:interval'])
</script>

<style scoped>
.control-panel { background: var(--bg-card); border: 1px solid #1e1e2e; border-radius: 12px; padding: 20px; }
.control-row { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.control-row:last-child { margin-bottom: 0; }
.slider-label { font-size: 13px; color: #888; white-space: nowrap; }
</style>
