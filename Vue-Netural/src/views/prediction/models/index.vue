<!-- src/views/prediction/models/index.vue -->
<template>
  <div class="models-page">
    <div class="page-header">
      <h2>模型管理</h2>
      <p>管理和切换神经网络模型</p>
    </div>

    <div class="models-grid">
      <div v-for="model in models" :key="model.key" class="model-card" :class="{ active: model.is_current }">
        <div class="card-header">
          <div class="model-badge" :class="model.status">
            {{ statusText(model.status) }}
          </div>
          <el-tag v-if="model.is_current" type="success" effect="dark" size="small">当前使用</el-tag>
        </div>
        <h3 class="model-name">{{ model.display_name }}</h3>
        <p class="model-desc">{{ model.description }}</p>
        <div class="model-stats">
          <div class="stat">
            <span class="stat-label">参数量</span>
            <span class="stat-value">{{ formatNumber(model.params_count) }}</span>
          </div>
          <div class="stat">
            <span class="stat-label">预测次数</span>
            <span class="stat-value">{{ model.total_predictions }}</span>
          </div>
          <div class="stat">
            <span class="stat-label">训练时间</span>
            <span class="stat-value">{{ model.trained_at || '未训练' }}</span>
          </div>
          <div class="stat">
            <span class="stat-label">设备</span>
            <span class="stat-value">{{ model.device }}</span>
          </div>
        </div>
        <div class="card-actions">
          <el-button v-if="!model.is_current" type="primary" @click="handleSwitch(model.key)"
            :loading="switching === model.key">
            切换使用
          </el-button>
          <el-button v-else type="success" disabled>使用中</el-button>
          <el-button @click="goTrain(model.key)">去训练</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getModelList, switchModel } from '../../../api/model'

const router = useRouter()
const models = ref([])
const switching = ref(null)

onMounted(() => { loadModels() })

async function loadModels() {
  try {
    const res = await getModelList()
    models.value = res.data || res
  } catch (e) { console.error(e) }
}

async function handleSwitch(key) {
  switching.value = key
  try {
    await switchModel(key)
    ElMessage.success('切换成功')
    await loadModels()
  } catch (e) { ElMessage.error('切换失败') }
  finally { switching.value = null }
}

function goTrain(key) { router.push({ path: '/prediction/training', query: { model: key } }) }
function statusText(s) { return { idle: '未训练', training: '训练中', ready: '已就绪' }[s] || s }
function formatNumber(n) {
  if (!n) return '0'
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K'
  return String(n)
}
</script>

<style scoped>
.models-page {
  max-width: 1200px;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.page-header p {
  font-size: 13px;
  color: var(--text-muted);
}

.models-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.model-card {
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 16px;
  padding: 24px;
  transition: all 0.3s;
}

.model-card:hover {
  border-color: var(--border-hover);
  transform: translateY(-2px);
  box-shadow: var(--shadow-card);
}

.model-card.active {
  border-color: var(--border-accent);
  background: var(--accent-bg-light);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.model-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 20px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.model-badge.idle {
  background: var(--bg-input);
  color: var(--text-muted);
}

.model-badge.ready {
  background: var(--success-bg);
  color: var(--success);
}

.model-badge.training {
  background: var(--warning-bg);
  color: var(--warning);
}

.model-name {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.model-desc {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.6;
  margin-bottom: 20px;
  min-height: 42px;
}

.model-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 20px;
}

.stat {
  background: var(--bg-secondary);
  border-radius: 8px;
  padding: 10px 12px;
}

.stat-label {
  display: block;
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.card-actions {
  display: flex;
  gap: 8px;
}

.card-actions .el-button {
  flex: 1;
}
</style>
