<!-- src/views/prediction/instances/index.vue -->
<template>
  <div class="instances-page">
    <!-- 顶部操作栏 -->
    <div class="page-header">
      <div class="header-left">
        <span class="page-title">预测实例管理</span>
        <span class="page-desc">每个实例独立连接一个 PLC，独立运行预测。点击实例名称进入预测画面。</span>
      </div>
      <el-button type="primary" :icon="Plus" @click="openDialog()">新增实例</el-button>
    </div>

    <!-- 实例卡片列表 -->
    <div class="instance-grid">
      <div
        v-for="inst in instances"
        :key="inst.id"
        class="instance-card"
        @click="goToInstance(inst)"
      >
        <div class="ic-header">
          <span class="ic-name">{{ inst.name }}</span>
          <div class="ic-header-tags">
            <el-tag
              :type="inst.instance_type === 'realtime' ? 'primary' : 'warning'"
              size="small"
              effect="plain"
            >
              {{ instanceTypes.find(t => t.key === inst.instance_type)?.name || inst.instance_type }}
            </el-tag>
            <el-tag
              :type="inst.device_connected ? 'success' : 'info'"
              size="small"
              effect="dark"
            >
              {{ inst.device_connected ? 'PLC已连接' : 'PLC未连接' }}
            </el-tag>
          </div>
        </div>

        <div class="ic-body">
          <div class="ic-info-row" v-if="inst.instance_type === 'realtime'">
            <span class="ic-label">模型</span>
            <el-tag :type="modelTagType(inst.model_key)" size="small">
              {{ inst.model_key.toUpperCase() }}
            </el-tag>
            <el-tag v-if="inst.base_model_id" type="warning" size="small" effect="plain">
              已训练
            </el-tag>
            <el-tag v-else type="info" size="small" effect="plain">
              默认权重
            </el-tag>
          </div>
          <div class="ic-info-row" v-else>
            <span class="ic-label">模型</span>
            <el-tag type="warning" size="small">专用模型</el-tag>
            <el-tag type="info" size="small" effect="plain">
              {{ inst.base_model_id || '激活版本' }}
            </el-tag>
          </div>
          <div class="ic-info-row">
            <span class="ic-label">设备</span>
            <span class="ic-value">{{ inst.device_name }}</span>
          </div>
          <div class="ic-info-row">
            <span class="ic-label">间隔</span>
            <span class="ic-value mono">{{ inst.interval }}s</span>
          </div>
          <div class="ic-info-row ic-points-row">
            <span class="ic-label">点位</span>
            <div class="ic-points" v-if="inst.point_names && inst.point_names.length > 0">
              <el-tag
                v-for="(name, idx) in inst.point_names.slice(0, 4)"
                :key="idx"
                size="small"
                effect="plain"
                type="info"
              >
                {{ name }}
              </el-tag>
              <el-tag
                v-if="inst.point_names.length > 4"
                size="small"
                effect="plain"
                type="warning"
              >
                +{{ inst.point_names.length - 4 }}
              </el-tag>
            </div>
            <span v-else class="ic-value" style="color: var(--text-muted)">全部启用点位</span>
          </div>
          <div class="ic-info-row">
            <span class="ic-label">创建时间</span>
            <span class="ic-value">{{ inst.create_time }}</span>
          </div>
        </div>

        <div class="ic-footer" @click.stop>
          <el-button size="small" type="primary" text @click.stop="goToInstance(inst)">
            进入预测 →
          </el-button>
          <div class="ic-actions">
            <el-button size="small" :icon="Edit" circle @click.stop="openDialog(inst)" />
            <el-popconfirm
              title="确定删除此实例？"
              confirm-button-text="删除"
              cancel-button-text="取消"
              @confirm="handleDelete(inst)"
            >
              <template #reference>
                <el-button size="small" :icon="Delete" circle type="danger" text @click.stop />
              </template>
            </el-popconfirm>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="instances.length === 0 && !loading" class="empty-state">
        <el-icon :size="48" color="#555"><Monitor /></el-icon>
        <p>暂无预测实例</p>
        <el-button type="primary" @click="openDialog()">创建第一个实例</el-button>
      </div>
    </div>

    <!-- 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingInstance ? '编辑实例' : '新增实例'"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-form :model="formData" label-width="90px" ref="formRef">
        <el-form-item label="实例名称" required>
          <el-input v-model="formData.name" placeholder="如：1号产线预测" maxlength="50" show-word-limit />
        </el-form-item>

        <el-form-item label="实例类型" required>
          <el-radio-group v-model="formData.instance_type" size="default" @change="handleTypeChange">
            <el-radio-button
              v-for="t in instanceTypes"
              :key="t.key"
              :value="t.key"
            >
              {{ t.name }}
            </el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="PLC 设备" required>
          <div style="display: flex; gap: 8px; align-items: center; width: 100%">
            <el-select
              v-model="formData.device_id"
              placeholder="请选择 PLC 设备"
              style="flex: 1"
              filterable
              :loading="loadingDevices"
            >
              <el-option
                v-for="d in allDevices"
                :key="d.id"
                :label="d.name"
                :value="d.id"
              >
                <div class="plc-device-option">
                  <span>{{ d.name }}</span>
                  <el-tag :type="d.status === 'connected' ? 'success' : 'info'" size="small">
                    {{ d.ip }}<template v-if="d.port">:{{ d.port }}</template>
                  </el-tag>
                </div>
              </el-option>
            </el-select>
            <el-button :icon="Refresh" circle size="default" @click="loadDevices" :loading="loadingDevices" />
          </div>
        </el-form-item>

        <el-form-item label="DB 点位">
          <el-select
            v-model="formData.point_ids_array"
            multiple
            placeholder="不选则读取所有启用点位"
            style="width: 100%"
            collapse-tags
            collapse-tags-tooltip
            :loading="loadingPoints"
            :disabled="!formData.device_id"
          >
            <el-option
              v-for="p in devicePoints"
              :key="p.id"
              :label="`${p.point_name} (DB${p.db_number}.${p.start_address})`"
              :value="p.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="预测模型" required v-if="formData.instance_type === 'realtime'">
          <el-radio-group v-model="formData.model_key" size="default">
            <el-radio-button value="lstm">LSTM</el-radio-button>
            <el-radio-button value="gru">GRU</el-radio-button>
            <el-radio-button value="transformer">Transformer</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="已保存模型" v-if="formData.instance_type === 'realtime'">
          <el-select
            v-model="formData.base_model_id"
            placeholder="选择已保存的模型版本（可选，不选则使用默认权重）"
            style="width: 100%"
            filterable
            clearable
            :loading="loadingSavedModels"
          >
            <el-option
              v-for="m in filteredSavedModels"
              :key="m.model_id"
              :label="m.name || m.display_name"
              :value="m.model_id"
            >
              <div class="saved-model-option">
                <span class="smo-name">{{ m.name || m.display_name }}</span>
                <div class="smo-meta">
                  <el-tag :type="modelTagType(m.model_key)" size="small">{{ m.model_key.toUpperCase() }}</el-tag>
                  <span class="smo-loss">Loss: {{ m.best_val_loss }}</span>
                </div>
              </div>
            </el-option>
          </el-select>
          <el-button size="default" :icon="Refresh" circle style="margin-left: 8px" @click="loadSavedModels" :loading="loadingSavedModels" />
        </el-form-item>

        <el-form-item v-if="formData.instance_type === 'dryer'" label="烘丝机模型" required>
          <el-select
            v-model="formData.base_model_id"
            placeholder="选择已训练的烘丝机模型版本"
            style="width: 100%"
            filterable
            :loading="loadingDryerModels"
          >
            <el-option
              v-for="v in dryerVersions"
              :key="v.version"
              :label="v.version + (v.is_active ? ' (当前激活)' : '')"
              :value="v.version"
            >
              <div class="saved-model-option">
                <span class="smo-name">{{ v.version }} <el-tag v-if="v.is_active" type="success" size="small" effect="plain">激活</el-tag></span>
                <div class="smo-meta">
                  <span class="smo-loss">Loss: {{ v.metrics?.best_test_loss ?? '-' }}</span>
                  <span>R²: {{ v.metrics?.final_r2 ?? '-' }}</span>
                  <span>{{ v.metrics?.epochs ?? '-' }} 轮</span>
                </div>
              </div>
            </el-option>
          </el-select>
          <el-button size="default" :icon="Refresh" circle style="margin-left: 8px" @click="loadDryerVersions" :loading="loadingDryerModels" />
        </el-form-item>

        <el-form-item v-if="formData.instance_type !== 'realtime' && formData.instance_type !== 'dryer'" label="模型说明">
          <el-text type="info" size="small">
            {{ instanceTypes.find(t => t.key === formData.instance_type)?.desc || '该实例类型使用独立模型，请先完成对应模型训练。' }}
          </el-text>
        </el-form-item>

        <el-form-item label="预测间隔">
          <el-input-number v-model="formData.interval" :min="0.1" :max="30" :step="0.1" :precision="1" />
          <span style="margin-left: 8px; color: #888">秒</span>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          {{ editingInstance ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Edit, Delete, Monitor, Refresh } from '@element-plus/icons-vue'
import { getInstanceList, addInstance, updateInstance, deleteInstance } from '../../../api/instance'
import { getPlcDeviceList, getPlcPointList } from '../../../api/plc'
import { getSavedModels } from '../../../api/model'
import request from '../../../api/request'

const router = useRouter()

const instances = ref([])
const loading = ref(false)
const allDevices = ref([])
const loadingDevices = ref(false)
const devicePoints = ref([])
const loadingPoints = ref(false)
const savedModels = ref([])
const loadingSavedModels = ref(false)
const dryerVersions = ref([])
const loadingDryerModels = ref(false)
const instanceTypes = ref([
  { key: 'realtime', name: '实时预测[通用]', desc: '通用神经网络实时预测' },
  { key: 'dryer', name: '烘丝机出口水分模型', desc: '烘丝机专用预测模型' }
])

// 已保存模型按当前选中的模型类型筛选
const filteredSavedModels = computed(() => {
  return savedModels.value.filter(m => m.model_key === formData.model_key)
})

// 弹窗
const dialogVisible = ref(false)
const editingInstance = ref(null)
const submitting = ref(false)
const formData = reactive({
  name: '',
  instance_type: 'realtime',
  device_id: null,
  point_ids_array: [],
  model_key: 'lstm',
  base_model_id: '',
  interval: 1.0
})

function modelTagType(key) {
  return { lstm: '', gru: 'success', transformer: 'warning' }[key] || 'info'
}

function handleTypeChange(val) {
  // 切换类型时重置相关字段
  if (val === 'dryer') {
    formData.model_key = 'lstm'
    formData.base_model_id = ''
    loadDryerVersions()
  } else if (val === 'realtime') {
    formData.base_model_id = ''
  }
}

onMounted(async () => {
  await Promise.all([loadInstances(), loadDevices(), loadSavedModels()])
})

async function loadInstanceTypes() {
  try {
    const res = await request.get('/system/menu/instance-types')
    if (res.data && res.data.length > 0) {
      instanceTypes.value = res.data
    }
    // 如果当前编辑的实例类型不在列表中，追加进去（允许编辑已有值）
    if (editingInstance.value) {
      const currentType = editingInstance.value.instance_type || 'realtime'
      if (!instanceTypes.value.some(t => t.key === currentType)) {
        instanceTypes.value.push({
          key: currentType,
          name: currentType,
          icon: '',
          desc: '（该类型已停用）'
        })
      }
    }
  } catch (e) {
    // 使用默认值
    console.warn('加载实例类型配置失败，使用默认值')
  }
}

async function loadInstances() {
  loading.value = true
  try {
    const res = await getInstanceList()
    instances.value = res.data || []
  } catch (e) {
    console.error('加载实例列表失败:', e)
  } finally {
    loading.value = false
  }
}

async function loadDevices() {
  loadingDevices.value = true
  try {
    const res = await getPlcDeviceList()
    allDevices.value = res.data || []
  } catch (e) { /* ignore */ }
  finally { loadingDevices.value = false }
}

async function loadSavedModels() {
  loadingSavedModels.value = true
  try {
    const res = await getSavedModels()
    savedModels.value = res.data || []
  } catch (e) { /* ignore */ }
  finally { loadingSavedModels.value = false }
}

async function loadDryerVersions() {
  loadingDryerModels.value = true
  try {
    const res = await request.get('/dryer/versions')
    dryerVersions.value = res.data || []
  } catch (e) { /* ignore */ }
  finally { loadingDryerModels.value = false }
}

// 当设备变更时，加载点位
watch(() => formData.device_id, async (newId) => {
  formData.point_ids_array = []
  devicePoints.value = []
  if (!newId) return
  loadingPoints.value = true
  try {
    const res = await getPlcPointList({ device_id: newId, is_active: 1 })
    devicePoints.value = res.data || []
  } catch (e) { /* ignore */ }
  finally { loadingPoints.value = false }
})

function openDialog(inst = null) {
  editingInstance.value = inst
  if (inst) {
    formData.name = inst.name
    formData.instance_type = inst.instance_type || 'realtime'
    formData.device_id = inst.device_id
    formData.model_key = inst.model_key || 'lstm'
    formData.base_model_id = inst.base_model_id || ''
    formData.interval = inst.interval
    formData.point_ids_array = inst.point_ids
      ? inst.point_ids.split(',').map(Number).filter(n => !isNaN(n))
      : []
  } else {
    formData.name = ''
    formData.instance_type = 'realtime'
    formData.device_id = null
    formData.model_key = 'lstm'
    formData.base_model_id = ''
    formData.interval = 1.0
    formData.point_ids_array = []
  }
  // 每次打开弹窗都刷新设备列表和实例类型，确保数据同步
  loadDevices()
  loadInstanceTypes()
  // 如果是烘丝机类型，加载烘丝机模型版本
  if (formData.instance_type === 'dryer') {
    loadDryerVersions()
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formData.name.trim()) {
    ElMessage.warning('请输入实例名称')
    return
  }
  if (!formData.device_id) {
    ElMessage.warning('请选择 PLC 设备')
    return
  }
  if (formData.instance_type === 'dryer' && !formData.base_model_id) {
    ElMessage.warning('请选择烘丝机模型版本')
    return
  }

  // 如果选了已保存模型，用该模型的 model_key；否则用 radio 选的类型
  let modelKey = formData.model_key
  let baseModelId = formData.base_model_id || ''
  // 只有 realtime 类型才从 savedModels 查找 model_key
  if (baseModelId && formData.instance_type === 'realtime') {
    const saved = savedModels.value.find(m => m.model_id === baseModelId)
    if (saved) {
      modelKey = saved.model_key
    }
  }

  submitting.value = true
  try {
    const params = {
      name: formData.name.trim(),
      instance_type: formData.instance_type,
      device_id: formData.device_id,
      point_ids: formData.point_ids_array.join(','),
      model_key: modelKey,
      base_model_id: baseModelId,
      interval: formData.interval
    }

    if (editingInstance.value) {
      params.id = editingInstance.value.id
      await updateInstance(params)
      ElMessage.success('更新成功')
    } else {
      await addInstance(params)
      ElMessage.success('创建成功')
    }

    dialogVisible.value = false
    await loadInstances()
  } catch (e) {
    ElMessage.error('操作失败: ' + ((e.response && e.response.data && e.response.data.detail) || e.message))
  } finally {
    submitting.value = false
  }
}

async function handleDelete(inst) {
  try {
    await deleteInstance(inst.id)
    ElMessage.success('删除成功')
    await loadInstances()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

function goToInstance(inst) {
  router.push(`/prediction/realtime/${inst.id}`)
}
</script>

<style scoped>
.instances-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 12px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.page-desc {
  font-size: 13px;
  color: var(--text-muted);
}

.instance-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.instance-card {
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.instance-card:hover {
  border-color: var(--accent);
  box-shadow: 0 4px 20px rgba(74, 158, 255, 0.1);
}

.ic-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.ic-header-tags {
  display: flex;
  gap: 6px;
  align-items: center;
}

.ic-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.ic-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.ic-info-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ic-label {
  font-size: 12px;
  color: var(--text-muted);
  width: 60px;
  flex-shrink: 0;
}

.ic-value {
  font-size: 13px;
  color: var(--text-primary);
}

.ic-value.mono {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

.ic-points-row {
  align-items: flex-start;
}

.ic-points {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.ic-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid var(--border-secondary);
  padding-top: 12px;
}

.ic-actions {
  display: flex;
  gap: 4px;
}

.empty-state {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 60px 20px;
  color: var(--text-muted);
}

.empty-state p {
  font-size: 15px;
}

.plc-device-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

/* 已保存模型选项 */
.saved-model-option {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.smo-name {
  font-size: 13px;
  font-weight: 500;
}

.smo-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--text-secondary);
}

.smo-loss {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  color: var(--danger);
}
</style>
