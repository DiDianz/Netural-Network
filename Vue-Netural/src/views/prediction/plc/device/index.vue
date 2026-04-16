<!-- src/views/prediction/plc/device/index.vue -->
<template>
  <div class="plc-device-page">
    <!-- 顶部操作栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-button type="primary" @click="handleAdd">
          <el-icon><Plus /></el-icon>新增设备
        </el-button>
        <el-button type="success" @click="handleConnectAll" :loading="connectingAll">
          一键连接全部
        </el-button>
        <el-button type="warning" @click="handleDisconnectAll">
          断开全部
        </el-button>
      </div>
      <div class="toolbar-right">
        <el-button @click="loadDevices" :icon="Refresh" circle />
      </div>
    </div>

    <!-- 设备卡片列表 -->
    <div class="device-grid">
      <div
        v-for="device in devices"
        :key="device.id"
        class="device-card"
        :class="{ 'is-connected': device.status === 'connected' }"
      >
        <div class="card-header">
          <div class="device-name">
            <el-icon class="device-icon"><Cpu /></el-icon>
            <span>{{ device.name }}</span>
          </div>
          <el-tag
            :type="statusTagType(device.status)"
            size="small"
            effect="dark"
          >
            {{ statusText(device.status) }}
          </el-tag>
        </div>

        <div class="card-body">
          <div class="info-row">
            <span class="label">IP 地址</span>
            <span class="value mono">{{ device.ip }}:{{ device.port }}</span>
          </div>
          <div class="info-row">
            <span class="label">机架 / 插槽</span>
            <span class="value">{{ device.rack }} / {{ device.slot }}</span>
          </div>
          <div class="info-row">
            <span class="label">DB 点位</span>
            <span class="value">
              <el-tag type="info" size="small">{{ device.point_count }} 个</el-tag>
            </span>
          </div>
          <div class="info-row" v-if="device.remark">
            <span class="label">备注</span>
            <span class="value remark">{{ device.remark }}</span>
          </div>
        </div>

        <div class="card-actions">
          <el-button
            v-if="device.status !== 'connected'"
            type="success"
            size="small"
            @click="handleConnect(device)"
            :loading="connectingId === device.id"
          >
            连接
          </el-button>
          <el-button
            v-else
            type="danger"
            size="small"
            @click="handleDisconnect(device)"
          >
            断开
          </el-button>
          <el-button size="small" @click="handleManagePoints(device)">
            管理点位
          </el-button>
          <el-button size="small" @click="handleEdit(device)">
            编辑
          </el-button>
          <el-popconfirm
            title="确定删除该设备及其所有点位？"
            confirm-button-text="删除"
            cancel-button-text="取消"
            @confirm="handleDelete(device)"
          >
            <template #reference>
              <el-button size="small" type="danger" plain>删除</el-button>
            </template>
          </el-popconfirm>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="devices.length === 0" class="empty-state">
        <el-empty description="暂无 PLC 设备">
          <el-button type="primary" @click="handleAdd">添加第一个设备</el-button>
        </el-empty>
      </div>
    </div>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑设备' : '新增设备'"
      width="520px"
      destroy-on-close
    >
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <el-form-item label="设备名称" prop="name">
          <el-input v-model="form.name" placeholder="如：1号产线PLC" />
        </el-form-item>
        <el-form-item label="IP 地址" prop="ip">
          <el-input v-model="form.ip" placeholder="如：192.168.1.10" />
        </el-form-item>
        <el-form-item label="端口" prop="port">
          <el-input-number v-model="form.port" :min="1" :max="65535" style="width: 100%" />
        </el-form-item>
        <el-form-item label="机架号" prop="rack">
          <el-input-number v-model="form.rack" :min="0" :max="7" style="width: 100%" />
        </el-form-item>
        <el-form-item label="插槽号" prop="slot">
          <el-input-number v-model="form.slot" :min="0" :max="31" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="可选" />
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Refresh, Cpu } from '@element-plus/icons-vue'
import {
  getPlcDeviceList, addPlcDevice, updatePlcDevice, deletePlcDevice,
  connectPlc, disconnectPlc, connectAllPlc, disconnectAllPlc
} from '../../../../api/plc'

const router = useRouter()
const devices = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const submitting = ref(false)
const connectingId = ref(null)
const connectingAll = ref(false)

const form = ref({
  id: null, name: '', ip: '', port: 102, rack: 0, slot: 1, remark: ''
})

const rules = {
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  ip: [{ required: true, message: '请输入 IP 地址', trigger: 'blur' }],
  port: [{ required: true, message: '请输入端口号', trigger: 'blur' }],
}

onMounted(() => loadDevices())

async function loadDevices() {
  try {
    const res = await getPlcDeviceList()
    devices.value = res.data || []
  } catch (e) {
    console.error('加载设备列表失败:', e)
  }
}

function statusTagType(status) {
  return { connected: 'success', disconnected: 'info', error: 'danger' }[status] || 'info'
}

function statusText(status) {
  return { connected: '已连接', disconnected: '未连接', error: '连接异常' }[status] || '未知'
}

function handleAdd() {
  isEdit.value = false
  form.value = { id: null, name: '', ip: '', port: 102, rack: 0, slot: 1, remark: '' }
  dialogVisible.value = true
}

function handleEdit(device) {
  isEdit.value = true
  form.value = { ...device }
  dialogVisible.value = true
}

async function handleSubmit() {
  try {
    await formRef.value.validate()
    submitting.value = true
    if (isEdit.value) {
      await updatePlcDevice(form.value)
      ElMessage.success('更新成功')
    } else {
      await addPlcDevice(form.value)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    await loadDevices()
  } catch (e) {
    if (e?.message) ElMessage.error(e.message)
  } finally {
    submitting.value = false
  }
}

async function handleConnect(device) {
  connectingId.value = device.id
  try {
    await connectPlc(device.id)
    ElMessage.success(`${device.name} 连接成功`)
    await loadDevices()
  } catch (e) {
    ElMessage.error(`${device.name} 连接失败`)
  } finally {
    connectingId.value = null
  }
}

async function handleDisconnect(device) {
  try {
    await disconnectPlc(device.id)
    ElMessage.success(`${device.name} 已断开`)
    await loadDevices()
  } catch (e) {
    ElMessage.error('断开失败')
  }
}

async function handleConnectAll() {
  connectingAll.value = true
  try {
    const res = await connectAllPlc()
    const results = res.data || []
    const ok = results.filter(r => r.success).length
    ElMessage.success(`连接完成: ${ok}/${results.length} 成功`)
    await loadDevices()
  } catch (e) {
    ElMessage.error('批量连接失败')
  } finally {
    connectingAll.value = false
  }
}

async function handleDisconnectAll() {
  try {
    await disconnectAllPlc()
    ElMessage.success('已断开全部设备')
    await loadDevices()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

async function handleDelete(device) {
  try {
    await deletePlcDevice(device.id)
    ElMessage.success('删除成功')
    await loadDevices()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

function handleManagePoints(device) {
  router.push({ path: '/prediction/point', query: { device_id: device.id, device_name: device.name } })
}
</script>

<style scoped>
.plc-device-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: var(--bg-card);
  border: 1px solid #1e1e2e;
  border-radius: 12px;
}

.toolbar-left {
  display: flex;
  gap: 8px;
}

.device-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
}

.device-card {
  background: var(--bg-card);
  border: 1px solid #1e1e2e;
  border-radius: 12px;
  padding: 20px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.device-card:hover {
  border-color: #333;
}

.device-card.is-connected {
  border-color: #67c23a55;
  box-shadow: 0 0 12px rgba(103, 194, 58, 0.08);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.device-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}

.device-icon {
  font-size: 20px;
  color: #409eff;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.info-row .label {
  color: #888;
}

.info-row .value {
  color: #ccc;
}

.info-row .mono {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

.info-row .remark {
  font-size: 12px;
  color: #999;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  border-top: 1px solid #1e1e2e;
  padding-top: 14px;
}

.empty-state {
  grid-column: 1 / -1;
  display: flex;
  justify-content: center;
  padding: 60px 0;
}
</style>
