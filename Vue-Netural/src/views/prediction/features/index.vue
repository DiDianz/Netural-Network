<!-- src/views/prediction/features/index.vue -->
<template>
  <div class="feature-schema-page">
    <div class="page-header">
      <h2>特征方案管理</h2>
      <el-button type="primary" @click="openCreate">+ 新建方案</el-button>
    </div>

    <div class="page-hint">
      特征方案定义了训练数据的列结构和各特征的权重。不同工艺设备可创建不同方案，训练时选择对应方案即可。
    </div>

    <!-- 方案列表 -->
    <el-table :data="schemaList" stripe v-loading="loading" style="width: 100%">
      <el-table-column prop="name" label="方案名称" min-width="160" />
      <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
      <el-table-column prop="feature_count" label="特征数" width="80" align="center" />
      <el-table-column label="特征列" min-width="280" show-overflow-tooltip>
        <template #default="{ row }">
          <el-tag v-for="name in row.feature_names" :key="name" size="small" style="margin: 2px">
            {{ name }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="target" label="预测目标" width="110" />
      <el-table-column label="内置" width="70" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.is_builtin" type="info" size="small">内置</el-tag>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column prop="updated_at" label="更新时间" width="160" />
      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" @click="openWeightEdit(row)">调权重</el-button>
          <el-button size="small" @click="handleCopy(row)">复制</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)" :disabled="row.is_builtin">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新建/编辑方案对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEditing ? '编辑特征方案' : '新建特征方案'" width="720px"
      :close-on-click-modal="false">
      <el-form :model="form" label-width="100px" :rules="formRules" ref="formRef">
        <el-form-item label="方案名称" prop="name">
          <el-input v-model="form.name" placeholder="如：烘丝机方案、回潮机方案" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" placeholder="方案用途说明" />
        </el-form-item>
        <el-form-item label="预测目标" prop="target_name">
          <el-input v-model="form.target_name" placeholder="目标列名，如 out_moist" style="width: 200px" />
          <el-input v-model="form.target_label" placeholder="中文名称" style="width: 200px; margin-left: 8px" />
        </el-form-item>
        <el-form-item label="品牌列">
          <el-input v-model="form.brand_name" placeholder="品牌列名，如 brandID" style="width: 200px" />
          <el-input v-model="form.brand_label" placeholder="中文名称" style="width: 200px; margin-left: 8px" />
        </el-form-item>

        <el-divider content-position="left">特征列配置</el-divider>

        <div class="feature-list-editor">
          <div v-for="(feat, idx) in form.features" :key="idx" class="feature-row">
            <el-input v-model="feat.name" placeholder="列名（英文）" style="width: 180px" />
            <el-input v-model="feat.label" placeholder="中文名称" style="width: 180px" />
            <el-input-number v-model="feat.weight" :min="0" :max="10" :step="0.1" :precision="1"
              controls-position="right" style="width: 130px" />
            <span class="weight-label">权重</span>
            <el-button type="danger" circle size="small" @click="form.features.splice(idx, 1)"
              :disabled="form.features.length <= 1">
              ✕
            </el-button>
          </div>
          <el-button type="primary" plain size="small" @click="addFeature" style="margin-top: 8px">
            + 添加特征列
          </el-button>
        </div>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          {{ isEditing ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 权重快速调整对话框 -->
    <el-dialog v-model="weightDialogVisible" title="调整特征权重" width="600px">
      <div class="weight-editor" v-if="weightSchema">
        <div class="weight-header">
          <span>方案：{{ weightSchema.name }}</span>
          <el-button size="small" @click="resetWeights">重置为 1.0</el-button>
        </div>
        <div v-for="feat in weightFeatures" :key="feat.name" class="weight-row">
          <span class="weight-name">{{ feat.label || feat.name }}</span>
          <span class="weight-key">{{ feat.name }}</span>
          <el-slider v-model="feat.weight" :min="0" :max="10" :step="0.1" style="flex: 1; margin: 0 16px" />
          <el-input-number v-model="feat.weight" :min="0" :max="10" :step="0.1" :precision="1"
            controls-position="right" size="small" style="width: 100px" />
        </div>
      </div>
      <template #footer>
        <el-button @click="weightDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveWeights" :loading="savingWeights">保存权重</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listSchemas, getSchema, createSchema, updateSchema,
  deleteSchema, copySchema, updateWeights
} from '@/api/feature'

const loading = ref(false)
const schemaList = ref([])

// ===== 列表 =====
async function loadList() {
  loading.value = true
  try {
    const res = await listSchemas()
    schemaList.value = res.data || []
  } catch (e) {
    ElMessage.error('加载失败: ' + (e.message || e))
  } finally {
    loading.value = false
  }
}
onMounted(loadList)

// ===== 新建/编辑 =====
const dialogVisible = ref(false)
const isEditing = ref(false)
const editingId = ref(null)
const submitting = ref(false)
const formRef = ref(null)

const form = reactive({
  name: '',
  description: '',
  target_name: 'out_moist',
  target_label: '出口水分',
  brand_name: 'brandID',
  brand_label: '品牌标识',
  features: [{ name: '', label: '', weight: 1.0 }],
})

const formRules = {
  name: [{ required: true, message: '请输入方案名称', trigger: 'blur' }],
  target_name: [{ required: true, message: '请输入目标列名', trigger: 'blur' }],
}

function resetForm() {
  form.name = ''
  form.description = ''
  form.target_name = 'out_moist'
  form.target_label = '出口水分'
  form.brand_name = 'brandID'
  form.brand_label = '品牌标识'
  form.features = [{ name: '', label: '', weight: 1.0 }]
}

function addFeature() {
  form.features.push({ name: '', label: '', weight: 1.0 })
}

function openCreate() {
  resetForm()
  isEditing.value = false
  editingId.value = null
  dialogVisible.value = true
}

async function openEdit(row) {
  if (row.is_builtin) {
    ElMessage.warning('内置方案不可编辑，可复制后修改')
    return
  }
  try {
    const res = await getSchema(row.id)
    const schema = res.data
    form.name = schema.name
    form.description = schema.description || ''
    form.target_name = schema.target?.name || 'out_moist'
    form.target_label = schema.target?.label || '出口水分'
    form.brand_name = schema.brand_column?.name || 'brandID'
    form.brand_label = schema.brand_column?.label || '品牌标识'
    form.features = (schema.features || []).map(f => ({
      name: f.name, label: f.label || '', weight: f.weight ?? 1.0
    }))
    isEditing.value = true
    editingId.value = row.id
    dialogVisible.value = true
  } catch (e) {
    ElMessage.error('加载方案详情失败')
  }
}

async function handleSubmit() {
  try {
    await formRef.value.validate()
  } catch { return }

  // 校验特征名
  const validFeatures = form.features.filter(f => f.name.trim())
  if (validFeatures.length === 0) {
    ElMessage.warning('至少添加一个特征列')
    return
  }
  const names = validFeatures.map(f => f.name.trim())
  if (new Set(names).size !== names.length) {
    ElMessage.warning('特征列名不能重复')
    return
  }

  submitting.value = true
  try {
    const payload = {
      name: form.name,
      description: form.description,
      features: validFeatures.map(f => ({
        name: f.name.trim(),
        label: f.label.trim(),
        weight: f.weight,
      })),
      target: { name: form.target_name.trim(), label: form.target_label.trim() },
      brand_column: { name: form.brand_name.trim(), label: form.brand_label.trim() },
    }

    if (isEditing.value) {
      await updateSchema(editingId.value, payload)
      ElMessage.success('方案已更新')
    } else {
      await createSchema(payload)
      ElMessage.success('方案已创建')
    }
    dialogVisible.value = false
    loadList()
  } catch (e) {
    ElMessage.error((e.response?.data?.detail || e.message || '操作失败'))
  } finally {
    submitting.value = false
  }
}

// ===== 复制 =====
async function handleCopy(row) {
  try {
    await copySchema(row.id, `${row.name} (副本)`)
    ElMessage.success('复制成功')
    loadList()
  } catch (e) {
    ElMessage.error('复制失败')
  }
}

// ===== 删除 =====
async function handleDelete(row) {
  if (row.is_builtin) {
    ElMessage.warning('内置方案不可删除')
    return
  }
  try {
    await ElMessageBox.confirm(`确定删除方案「${row.name}」？`, '确认', { type: 'warning' })
    await deleteSchema(row.id)
    ElMessage.success('已删除')
    loadList()
  } catch { /* cancelled */ }
}

// ===== 权重快速调整 =====
const weightDialogVisible = ref(false)
const weightSchema = ref(null)
const weightFeatures = ref([])
const savingWeights = ref(false)

async function openWeightEdit(row) {
  try {
    const res = await getSchema(row.id)
    weightSchema.value = res.data
    weightFeatures.value = (res.data.features || []).map(f => ({ ...f }))
    weightDialogVisible.value = true
  } catch {
    ElMessage.error('加载方案失败')
  }
}

function resetWeights() {
  weightFeatures.value.forEach(f => { f.weight = 1.0 })
}

async function handleSaveWeights() {
  if (!weightSchema.value) return
  savingWeights.value = true
  try {
    const weights = {}
    weightFeatures.value.forEach(f => { weights[f.name] = f.weight })
    await updateWeights(weightSchema.value.id, weights)
    ElMessage.success('权重已保存')
    weightDialogVisible.value = false
    loadList()
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    savingWeights.value = false
  }
}
</script>

<style scoped>
.feature-schema-page {
  padding: 20px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.page-header h2 {
  margin: 0;
}
.page-hint {
  color: #909399;
  font-size: 13px;
  margin-bottom: 16px;
}
.feature-list-editor {
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 12px;
  background: #fafafa;
}
.feature-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.weight-label {
  color: #909399;
  font-size: 12px;
  width: 30px;
}
.weight-editor {
  max-height: 480px;
  overflow-y: auto;
}
.weight-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  font-weight: 500;
}
.weight-row {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}
.weight-name {
  width: 120px;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.weight-key {
  width: 130px;
  color: #909399;
  font-size: 12px;
  font-family: monospace;
}
</style>
