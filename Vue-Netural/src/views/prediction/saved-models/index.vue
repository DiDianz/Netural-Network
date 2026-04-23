<!-- src/views/prediction/saved-models/index.vue -->
<template>
  <div class="saved-models-page">
    <div class="page-header">
      <h2>已保存模型</h2>
      <p>每次训练完成后自动保存的模型版本，可用于继续训练、加载使用或删除</p>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-radio-group v-model="filterModelKey" size="default" @change="loadSavedModels">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="lstm">LSTM</el-radio-button>
        <el-radio-button value="gru">GRU</el-radio-button>
        <el-radio-button value="transformer">Transformer</el-radio-button>
        <el-radio-button value="dryer">烘丝机</el-radio-button>
      </el-radio-group>
      <el-input v-model="searchKeyword" placeholder="搜索名称/备注" clearable style="width: 240px; margin-left: 16px" />
      <el-button @click="loadSavedModels" :loading="loading" style="margin-left: 12px">刷新</el-button>
    </div>

    <!-- 表格 -->
    <el-table :data="displayList" stripe v-loading="loading" empty-text="暂无保存的模型版本">
      <el-table-column prop="model_id" label="版本ID" width="100">
        <template #default="{ row }">
          <span class="model-id-badge">{{ row.model_id }}</span>
          <el-tag v-if="row.is_active" type="success" size="small" style="margin-left: 4px;">激活</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="名称" min-width="240">
        <template #default="{ row }">
          <div class="name-cell">
            <template v-if="editingId === row.model_id">
              <el-input v-model="editingName" size="small" style="width: 200px" @keyup.enter="confirmRename(row.model_id)"
                @keyup.escape="cancelRename" ref="renameInputRef" />
              <el-button size="small" type="primary" @click="confirmRename(row.model_id)" :loading="renaming">✓</el-button>
              <el-button size="small" @click="cancelRename">✕</el-button>
            </template>
            <template v-else>
              <span class="model-name-text">{{ row.name || row.display_name }}</span>
              <el-button size="small" text type="primary" @click="startRename(row)" style="margin-left: 4px">✎</el-button>
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
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="goTrainWith(row)">继续训练</el-button>
          <el-button size="small" @click="handleLoadModel(row)">加载</el-button>
          <el-popconfirm title="确定删除此模型版本？" @confirm="handleDelete(row)">
            <template #reference>
              <el-button size="small" type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 统计 -->
    <div class="stats-bar" v-if="savedModels.length > 0">
      <span>共 {{ savedModels.length }} 个版本</span>
      <span v-if="filterModelKey">，当前筛选 {{ displayList.length }} 个</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getSavedModels, deleteSavedModel, loadSavedModel, renameSavedModel } from '../../../api/model'
import { deleteVersion as deleteDryerVersion, activateVersion as activateDryerVersion } from '../../../api/dryer'

const router = useRouter()

const savedModels = ref([])
const loading = ref(false)
const filterModelKey = ref('')
const searchKeyword = ref('')
const editingId = ref(null)
const editingName = ref('')
const renaming = ref(false)

const displayList = computed(function () {
  var list = savedModels.value
  if (filterModelKey.value) {
    list = list.filter(function (m) { return m.model_key === filterModelKey.value })
  }
  if (searchKeyword.value.trim()) {
    var kw = searchKeyword.value.trim().toLowerCase()
    list = list.filter(function (m) {
      return (m.name || '').toLowerCase().includes(kw) ||
        (m.remark || '').toLowerCase().includes(kw) ||
        (m.display_name || '').toLowerCase().includes(kw) ||
        (m.model_id || '').toLowerCase().includes(kw)
    })
  }
  return list
})

onMounted(() => { loadSavedModels() })

async function loadSavedModels() {
  loading.value = true
  try {
    // 从统一接口加载所有模型（通用模型 + 烘丝机模型）
    const res = await getSavedModels()
    savedModels.value = (res.data || []).map(m => ({ ...m }))
  } catch (e) { console.error('加载已保存模型失败:', e) }
  finally { loading.value = false }
}

async function handleLoadModel(row) {
  try {
    if (row.model_type === 'dryer' || row.model_key === 'dryer') {
      await activateDryerVersion(row.model_id)
      ElMessage.success(`已激活烘丝机模型: ${row.model_id}`)
    } else {
      await loadSavedModel(row.model_id)
      ElMessage.success(`已加载模型: ${row.name || row.display_name}`)
    }
    await loadSavedModels()
  } catch (e) { ElMessage.error('加载失败: ' + ((e.response && e.response.data && e.response.data.detail) || e.message)) }
}

async function handleDelete(row) {
  try {
    if (row.model_type === 'dryer' || row.model_key === 'dryer') {
      await deleteDryerVersion(row.model_id)
    } else {
      await deleteSavedModel(row.model_id)
    }
    ElMessage.success('删除成功')
    await loadSavedModels()
  } catch (e) { ElMessage.error('删除失败: ' + ((e.response && e.response.data && e.response.data.detail) || e.message)) }
}

function goTrainWith(row) {
  if (row.model_type === 'dryer' || row.model_key === 'dryer') {
    router.push({ path: '/prediction/dryer' })
  } else {
    router.push({
      path: '/prediction/training',
      query: { model: row.model_key, base_model_id: row.model_id }
    })
  }
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

function modelTagType(key) {
  return { lstm: '', gru: 'success', transformer: 'warning', dryer: 'danger' }[key] || 'info'
}
</script>

<style scoped>
.saved-models-page {
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

.filter-bar {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  padding: 16px 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 12px;
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

.stats-bar {
  margin-top: 12px;
  padding: 8px 16px;
  font-size: 13px;
  color: var(--text-muted);
  background: var(--bg-secondary);
  border-radius: 8px;
}
</style>
