<!-- src/views/prediction/models/index.vue -->
<template>
  <div class="models-page">
    <!-- 基础模型卡片 -->
    <div class="page-header">
      <h2>模型管理</h2>
      <p>管理和切换神经网络模型，查看已保存的模型版本</p>
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

    <!-- 已保存模型版本 -->
    <div class="saved-section">
      <div class="saved-header">
        <div>
          <h2>已保存模型版本</h2>
          <p>每次训练完成后自动保存的模型版本，可用于继续训练</p>
        </div>
        <div class="saved-filter">
          <el-radio-group v-model="filterModelKey" size="default" @change="loadSavedModels">
            <el-radio-button value="">全部</el-radio-button>
            <el-radio-button value="lstm">LSTM</el-radio-button>
            <el-radio-button value="gru">GRU</el-radio-button>
            <el-radio-button value="transformer">Transformer</el-radio-button>
          </el-radio-group>
          <el-button @click="loadSavedModels" :loading="loadingSaved" style="margin-left: 12px">刷新</el-button>
        </div>
      </div>

      <el-table :data="filteredSavedModels" stripe v-loading="loadingSaved" empty-text="暂无保存的模型版本">
        <el-table-column prop="model_id" label="版本ID" width="100">
          <template #default="{ row }">
            <span class="model-id-badge">{{ row.model_id }}</span>
          </template>
        </el-table-column>
        <el-table-column label="名称" min-width="220">
          <template #default="{ row }">
            <div class="name-cell">
              <template v-if="editingId === row.model_id">
                <el-input v-model="editingName" size="small" style="width: 180px" @keyup.enter="confirmRename(row.model_id)"
                  @keyup.escape="cancelRename" />
                <el-button size="small" type="primary" @click="confirmRename(row.model_id)" :loading="renaming">✓</el-button>
                <el-button size="small" @click="cancelRename">✕</el-button>
              </template>
              <template v-else>
                <span class="model-name-text">{{ row.name || row.display_name }}</span>
                <el-button size="small" text type="primary" @click="startRename(row)" style="margin-left: 4px">
                  ✎
                </el-button>
              </template>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="模型类型" width="140">
          <template #default="{ row }">
            <el-tag :type="modelTagType(row.model_key)" size="small">{{ row.display_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="epochs" label="训练轮次" width="100" />
        <el-table-column label="最优Val Loss" width="130">
          <template #default="{ row }">
            <span class="loss-value">{{ row.best_val_loss }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="trained_at" label="训练时间" width="180" />
        <el-table-column prop="remark" label="备注" min-width="200" show-overflow-tooltip />
        <el-table-column prop="file_size_kb" label="大小" width="90">
          <template #default="{ row }">{{ row.file_size_kb }} KB</template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="goTrainWith(row)">继续训练</el-button>
            <el-button size="small" @click="handleLoadModel(row)">加载</el-button>
            <el-popconfirm title="确定删除此模型版本？" @confirm="handleDelete(row.model_id)">
              <template #reference>
                <el-button size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getModelList, switchModel, getSavedModels, deleteSavedModel, loadSavedModel, renameSavedModel } from '../../../api/model'

const router = useRouter()
const models = ref([])
const switching = ref(null)

const savedModels = ref([])
const loadingSaved = ref(false)
const filterModelKey = ref('')
const editingId = ref(null)
const editingName = ref('')
const renaming = ref(false)

const filteredSavedModels = computed(function () {
  if (!filterModelKey.value) return savedModels.value
  return savedModels.value.filter(function (m) { return m.model_key === filterModelKey.value })
})

onMounted(() => {
  loadModels()
  loadSavedModels()
})

async function loadModels() {
  try {
    const res = await getModelList()
    models.value = res.data || res
  } catch (e) { console.error(e) }
}

async function loadSavedModels() {
  loadingSaved.value = true
  try {
    const res = await getSavedModels()
    savedModels.value = res.data || []
  } catch (e) { console.error('加载已保存模型失败:', e) }
  finally { loadingSaved.value = false }
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

async function handleLoadModel(row) {
  try {
    await loadSavedModel(row.model_id)
    ElMessage.success(`已加载模型 ${row.model_id} (${row.display_name})`)
    await loadModels()
  } catch (e) { ElMessage.error('加载失败: ' + ((e.response && e.response.data && e.response.data.detail) || e.message)) }
}

async function handleDelete(modelId) {
  try {
    await deleteSavedModel(modelId)
    ElMessage.success('删除成功')
    await loadSavedModels()
  } catch (e) { ElMessage.error('删除失败: ' + ((e.response && e.response.data && e.response.data.detail) || e.message)) }
}

function startRename(row) {
  editingId.value = row.model_id
  editingName.value = row.name || row.display_name
}

function cancelRename() {
  editingId.value = null
  editingName.value = ''
}

async function confirmRename(modelId) {
  if (!editingName.value.trim()) { ElMessage.warning('名称不能为空'); return }
  renaming.value = true
  try {
    await renameSavedModel(modelId, editingName.value.trim())
    ElMessage.success('重命名成功')
    editingId.value = null
    editingName.value = ''
    await loadSavedModels()
  } catch (e) { ElMessage.error('重命名失败: ' + ((e.response && e.response.data && e.response.data.detail) || e.message)) }
  finally { renaming.value = false }
}

function goTrain(key) { router.push({ path: '/prediction/training', query: { model: key } }) }

function goTrainWith(row) {
  router.push({
    path: '/prediction/training',
    query: { model: row.model_key, base_model_id: row.model_id }
  })
}

function statusText(s) { return { idle: '未训练', training: '训练中', ready: '已就绪' }[s] || s }

function modelTagType(key) {
  return { lstm: '', gru: 'success', transformer: 'warning' }[key] || 'info'
}

function formatNumber(n) {
  if (!n) return '0'
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K'
  return String(n)
}
</script>

<style scoped>
.models-page {
  max-width: 1400px;
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
  margin-bottom: 32px;
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

/* ===== 已保存版本 ===== */
.saved-section {
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 16px;
  padding: 24px;
}

.saved-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 16px;
}

.saved-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.saved-header p {
  font-size: 13px;
  color: var(--text-muted);
}

.saved-filter {
  display: flex;
  align-items: center;
}

.model-id-badge {
  font-family: 'DM Mono', monospace;
  font-size: 13px;
  font-weight: 600;
  color: var(--accent);
  background: var(--accent-bg-light);
  padding: 2px 8px;
  border-radius: 6px;
}

.loss-value {
  font-family: 'DM Mono', monospace;
  font-size: 13px;
  color: var(--danger);
  font-weight: 600;
}

.name-cell {
  display: flex;
  align-items: center;
  gap: 4px;
}

.model-name-text {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}
</style>
