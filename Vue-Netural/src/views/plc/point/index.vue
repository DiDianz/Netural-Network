<!-- src/views/prediction/plc/point/index.vue -->
<template>
  <div class="plc-point-page">
    <!-- 顶部信息 -->
    <div class="page-header">
      <div class="header-left">
        <el-button @click="$router.back()" :icon="ArrowLeft" text>返回设备列表</el-button>
        <el-divider direction="vertical" />
        <span class="device-label">
          <el-icon><Cpu /></el-icon>
          {{ deviceName || '所有设备' }}
        </span>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="handleAdd">
          <el-icon><Plus /></el-icon>新增点位
        </el-button>
        <el-button @click="handleReadAll" :loading="readingAll" type="success" plain>
          读取全部
        </el-button>
      </div>
    </div>

    <!-- 搜索栏 -->
    <div class="search-bar">
      <el-input
        v-model="keyword"
        placeholder="搜索点位名称 / 描述"
        clearable
        @input="handleSearch"
        style="width: 280px"
        :prefix-icon="Search"
      />
      <el-select v-model="activeFilter" placeholder="状态筛选" clearable @change="loadPoints" style="width: 120px">
        <el-option label="已启用" :value="1" />
        <el-option label="已停用" :value="0" />
      </el-select>
    </div>

    <!-- 点位表格 -->
    <el-table :data="points" stripe v-loading="loading" style="width: 100%">
      <el-table-column prop="point_name" label="点位名称" min-width="140">
        <template #default="{ row }">
          <div class="point-name-cell">
            <el-tag size="small" :type="row.is_active ? 'success' : 'info'" effect="plain">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
            <span>{{ row.point_name }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="db_number" label="DB 块号" width="90" align="center" />
      <el-table-column prop="start_address" label="起始地址" width="100" align="center" />
      <el-table-column prop="data_type" label="数据类型" width="100" align="center">
        <template #default="{ row }">
          <el-tag size="small" type="warning" effect="plain">{{ row.data_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="bit_index" label="位索引" width="80" align="center">
        <template #default="{ row }">
          <span v-if="row.data_type === 'BOOL'">{{ row.bit_index }}</span>
          <span v-else class="text-muted">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" min-width="160" show-overflow-tooltip />
      <el-table-column label="实时值" width="120" align="center">
        <template #default="{ row }">
          <span v-if="row._readValue !== undefined" class="live-value">
            {{ row._readValue }}
          </span>
          <span v-else class="text-muted">-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="handleReadOne(row)" :loading="row._reading">读取</el-button>
          <el-button size="small" @click="handleEdit(row)">编辑</el-button>
          <el-popconfirm
            title="确定删除该点位？"
            confirm-button-text="删除"
            @confirm="handleDelete(row)"
          >
            <template #reference>
              <el-button size="small" type="danger" plain>删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @change="loadPoints"
      />
    </div>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑点位' : '新增点位'"
      width="520px"
      destroy-on-close
    >
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <el-form-item label="所属设备" prop="device_id">
          <el-select v-model="form.device_id" placeholder="选择设备" style="width: 100%" filterable>
            <el-option
              v-for="d in deviceList"
              :key="d.id"
              :label="d.name"
              :value="d.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="点位名称" prop="point_name">
          <el-input v-model="form.point_name" placeholder="如：温度传感器1" />
        </el-form-item>
        <el-form-item label="DB 块号" prop="db_number">
          <el-input-number v-model="form.db_number" :min="0" :max="65535" style="width: 100%" />
        </el-form-item>
        <el-form-item label="起始地址" prop="start_address">
          <el-input-number v-model="form.start_address" :min="0" :max="65535" style="width: 100%" />
        </el-form-item>
        <el-form-item label="数据类型" prop="data_type">
          <el-select v-model="form.data_type" style="width: 100%">
            <el-option label="REAL (浮点数 4字节)" value="REAL" />
            <el-option label="INT (整数 2字节)" value="INT" />
            <el-option label="DINT (双整数 4字节)" value="DINT" />
            <el-option label="WORD (无符号字 2字节)" value="WORD" />
            <el-option label="BOOL (布尔 1位)" value="BOOL" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.data_type === 'BOOL'" label="位索引">
          <el-input-number v-model="form.bit_index" :min="0" :max="7" style="width: 100%" />
          <div class="form-tip">字节内的第几位 (0-7)</div>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="isActiveSwitch" active-text="启用" inactive-text="停用" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          {{ isEdit ? '保存' : '添加' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, ArrowLeft, Search, Cpu } from '@element-plus/icons-vue'
import {
  getPlcPointList, addPlcPoint, updatePlcPoint, deletePlcPoint,
  readPlcSingle, readPlcBatch, getPlcDeviceList
} from '../../../api/plc'

const route = useRoute()

const points = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const activeFilter = ref(null)
const readingAll = ref(false)

const deviceId = computed(() => {
  const id = route.query.device_id
  return id ? parseInt(id) : null
})
const deviceName = computed(() => route.query.device_name || '')

const deviceList = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const submitting = ref(false)

const isActiveSwitch = computed({
  get: () => form.value.is_active === 1,
  set: (v) => { form.value.is_active = v ? 1 : 0 }
})

const form = ref({
  id: null, device_id: null, point_name: '',
  db_number: 0, start_address: 0, data_type: 'REAL',
  bit_index: 0, description: '', is_active: 1
})

const rules = {
  device_id: [{ required: true, message: '请选择设备', trigger: 'change' }],
  point_name: [{ required: true, message: '请输入点位名称', trigger: 'blur' }],
  db_number: [{ required: true, message: '请输入 DB 块号', trigger: 'blur' }],
  start_address: [{ required: true, message: '请输入起始地址', trigger: 'blur' }],
  data_type: [{ required: true, message: '请选择数据类型', trigger: 'change' }],
}

let searchTimer = null

onMounted(async () => {
  await loadDeviceList()
  if (deviceId.value) {
    form.value.device_id = deviceId.value
  }
  await loadPoints()
})

function handleSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    loadPoints()
  }, 300)
}

async function loadDeviceList() {
  try {
    const res = await getPlcDeviceList()
    deviceList.value = res.data || []
  } catch (e) {
    console.error('加载设备列表失败:', e)
  }
}

async function loadPoints() {
  loading.value = true
  try {
    const res = await getPlcPointList({
      device_id: deviceId.value || undefined,
      keyword: keyword.value || undefined,
      is_active: activeFilter.value,
      limit: pageSize.value,
      offset: (page.value - 1) * pageSize.value
    })
    points.value = (res.data || []).map(p => ({ ...p, _readValue: undefined, _reading: false }))
    total.value = res.total || 0
  } catch (e) {
    console.error('加载点位列表失败:', e)
  } finally {
    loading.value = false
  }
}

function handleAdd() {
  isEdit.value = false
  form.value = {
    id: null,
    device_id: deviceId.value || (deviceList.value[0]?.id ?? null),
    point_name: '', db_number: 0, start_address: 0,
    data_type: 'REAL', bit_index: 0, description: '', is_active: 1
  }
  dialogVisible.value = true
}

function handleEdit(row) {
  isEdit.value = true
  form.value = { ...row }
  dialogVisible.value = true
}

async function handleSubmit() {
  try {
    await formRef.value.validate()
    submitting.value = true
    if (isEdit.value) {
      await updatePlcPoint(form.value)
      ElMessage.success('更新成功')
    } else {
      await addPlcPoint(form.value)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    await loadPoints()
  } catch (e) {
    if (e?.message) ElMessage.error(e.message)
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row) {
  try {
    await deletePlcPoint(row.id)
    ElMessage.success('删除成功')
    await loadPoints()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

async function handleReadOne(row) {
  row._reading = true
  try {
    const res = await readPlcSingle({
      device_id: row.device_id,
      db_number: row.db_number,
      start_address: row.start_address,
      data_type: row.data_type,
      bit_index: row.bit_index
    })
    row._readValue = res.data?.value
  } catch (e) {
    row._readValue = 'ERR'
    ElMessage.error(`读取失败: ${e.response?.data?.detail || e.message}`)
  } finally {
    row._reading = false
  }
}

async function handleReadAll() {
  if (!deviceId.value) {
    ElMessage.warning('请从设备列表进入后使用此功能')
    return
  }
  readingAll.value = true
  try {
    const res = await readPlcBatch(deviceId.value)
    const results = res.data || []
    for (const r of results) {
      const pt = points.value.find(p => p.id === r.point_id)
      if (pt) {
        pt._readValue = r.success ? r.value : 'ERR'
      }
    }
    ElMessage.success(`读取完成: ${results.filter(r => r.success).length}/${results.length} 成功`)
  } catch (e) {
    ElMessage.error('批量读取失败')
  } finally {
    readingAll.value = false
  }
}
</script>

<style scoped>
.plc-point-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: var(--bg-card);
  border: 1px solid #1e1e2e;
  border-radius: 12px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.device-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
  color: #409eff;
}

.header-right {
  display: flex;
  gap: 8px;
}

.search-bar {
  display: flex;
  gap: 12px;
  padding: 12px 20px;
  background: var(--bg-card);
  border: 1px solid #1e1e2e;
  border-radius: 12px;
}

.point-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.live-value {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-weight: 600;
  color: #67c23a;
  font-size: 14px;
}

.text-muted {
  color: #555;
}

.form-tip {
  font-size: 12px;
  color: #888;
  margin-top: 4px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  padding: 8px 0;
}

:deep(.el-table) {
  border-radius: 12px;
  border: 1px solid #1e1e2e;
}
</style>
