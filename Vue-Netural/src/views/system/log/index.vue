<!-- src/views/system/log/index.vue — 增强版：支持日志类型分类筛选 -->
<template>
  <div class="log-page">
    <div class="page-header">
      <div class="header-left">
        <span class="page-title">操作日志</span>
        <span class="page-desc">覆盖 API调用 / 数据库操作 / 系统错误 / 前端操作</span>
      </div>
      <div class="header-actions">
        <el-popconfirm
          :title="`确定清理 ${clearDays} 天前的日志？`"
          @confirm="handleClear"
        >
          <template #reference>
            <el-button type="danger" plain size="default" :loading="clearing">
              清理旧日志
            </el-button>
          </template>
        </el-popconfirm>
        <el-select v-model="clearDays" size="default" style="width: 100px">
          <el-option :value="7" label="7天前" />
          <el-option :value="30" label="30天前" />
          <el-option :value="90" label="90天前" />
        </el-select>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-bar" v-if="stats">
      <div class="stat-card">
        <div class="stat-value">{{ stats.today_total || 0 }}</div>
        <div class="stat-label">今日日志</div>
      </div>
      <div class="stat-card stat-error">
        <div class="stat-value">{{ stats.today_error || 0 }}</div>
        <div class="stat-label">今日错误</div>
      </div>
      <div class="stat-card" v-for="(count, type) in stats.by_type" :key="type">
        <div class="stat-value">{{ count }}</div>
        <div class="stat-label">{{ typeLabel(type) }}</div>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-select v-model="filters.log_type" placeholder="日志类型" clearable style="width: 140px" @change="loadLogs">
        <el-option label="API调用" value="api" />
        <el-option label="数据库操作" value="db" />
        <el-option label="系统错误" value="error" />
        <el-option label="前端操作" value="frontend" />
      </el-select>
      <el-input v-model="filters.keyword" placeholder="搜索用户/模块/动作/地址" clearable style="width: 260px" @keyup.enter="loadLogs" />
      <el-select v-model="filters.module" placeholder="模块" clearable style="width: 140px" @change="loadLogs">
        <el-option v-for="m in modules" :key="m" :label="m" :value="m" />
      </el-select>
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 120px" @change="loadLogs">
        <el-option label="成功(200)" :value="200" />
        <el-option label="失败(400+)" :value="400" />
        <el-option label="未授权(401)" :value="401" />
        <el-option label="服务器错误(500)" :value="500" />
      </el-select>
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        style="width: 260px"
        @change="handleDateChange"
      />
      <el-button type="primary" @click="loadLogs" :loading="loading">查询</el-button>
      <el-button @click="resetFilters">重置</el-button>
    </div>

    <!-- 表格 -->
    <el-table :data="logs" stripe v-loading="loading" empty-text="暂无操作日志" style="width: 100%">
      <el-table-column prop="id" label="ID" width="70" align="center" />
      <el-table-column prop="log_type" label="类型" width="100" align="center">
        <template #default="{ row }">
          <el-tag size="small" :type="logTypeTag(row.log_type)">{{ typeLabel(row.log_type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="user_name" label="操作用户" width="100">
        <template #default="{ row }">
          <span>{{ row.user_name || '—' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="module" label="模块" width="110">
        <template #default="{ row }">
          <el-tag size="small" :type="moduleTagType(row.module)">{{ row.module || '其他' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="action" label="操作" width="160" show-overflow-tooltip />
      <el-table-column prop="method" label="方法" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="methodTagType(row.method)" size="small">{{ row.method }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="url" label="请求地址" min-width="220" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="mono-url">{{ row.url }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="row.status === 200 ? 'success' : 'danger'" size="small">
            {{ row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="error_msg" label="错误信息" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.error_msg" class="error-msg">{{ row.error_msg }}</span>
          <span v-else style="color: var(--text-muted)">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="cost_ms" label="耗时" width="90" align="center">
        <template #default="{ row }">
          <span :class="{ 'slow-ms': row.cost_ms > 3000 }">{{ row.cost_ms }}ms</span>
        </template>
      </el-table-column>
      <el-table-column prop="ip" label="IP" width="130" />
      <el-table-column prop="create_time" label="操作时间" width="170" />
      <el-table-column label="详情" width="70" align="center" fixed="right">
        <template #default="{ row }">
          <el-button size="small" text type="primary" @click="showDetail(row)">查看</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-bar" v-if="total > 0">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[20, 50, 100, 200]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="loadLogs"
        @current-change="loadLogs"
      />
    </div>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="操作详情" width="600px">
      <el-descriptions :column="1" border v-if="currentLog">
        <el-descriptions-item label="ID">{{ currentLog.id }}</el-descriptions-item>
        <el-descriptions-item label="日志类型">
          <el-tag :type="logTypeTag(currentLog.log_type)">{{ typeLabel(currentLog.log_type) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="操作用户">{{ currentLog.user_name || '—' }}</el-descriptions-item>
        <el-descriptions-item label="模块">{{ currentLog.module }}</el-descriptions-item>
        <el-descriptions-item label="操作">{{ currentLog.action }}</el-descriptions-item>
        <el-descriptions-item label="请求方法">{{ currentLog.method }}</el-descriptions-item>
        <el-descriptions-item label="请求地址">
          <span class="mono-url">{{ currentLog.url }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="请求参数" v-if="currentLog.params">
          <pre class="params-pre">{{ currentLog.params }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="状态码">
          <el-tag :type="currentLog.status === 200 ? 'success' : 'danger'">{{ currentLog.status }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="错误信息" v-if="currentLog.error_msg">
          <span class="error-msg">{{ currentLog.error_msg }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="操作结果">{{ currentLog.result }}</el-descriptions-item>
        <el-descriptions-item label="耗时">{{ currentLog.cost_ms }}ms</el-descriptions-item>
        <el-descriptions-item label="IP">{{ currentLog.ip }}</el-descriptions-item>
        <el-descriptions-item label="操作时间">{{ currentLog.create_time }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getLogList, getLogModules, clearLogs, getLogStats } from '../../api/log'

const logs = ref([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(50)
const modules = ref([])
const dateRange = ref(null)
const clearing = ref(false)
const clearDays = ref(30)
const stats = ref(null)

const detailVisible = ref(false)
const currentLog = ref(null)

const filters = reactive({
  log_type: '',
  keyword: '',
  module: '',
  status: null,
  start_time: '',
  end_time: '',
})

onMounted(() => {
  loadLogs()
  loadModules()
  loadStats()
})

async function loadLogs() {
  loading.value = true
  try {
    const params = {
      limit: pageSize.value,
      offset: (currentPage.value - 1) * pageSize.value,
    }
    if (filters.log_type) params.log_type = filters.log_type
    if (filters.keyword) params.keyword = filters.keyword
    if (filters.module) params.module = filters.module
    if (filters.status != null) params.status = filters.status
    if (filters.start_time) params.start_time = filters.start_time
    if (filters.end_time) params.end_time = filters.end_time

    const res = await getLogList(params)
    logs.value = res.data || []
    total.value = res.total || 0
  } catch (e) {
    console.error('加载日志失败:', e)
  } finally {
    loading.value = false
  }
}

async function loadModules() {
  try {
    const res = await getLogModules()
    modules.value = res.data || []
  } catch {}
}

async function loadStats() {
  try {
    const res = await getLogStats(7)
    stats.value = res.data || {}
  } catch {}
}

function handleDateChange(val) {
  if (val && val.length === 2) {
    filters.start_time = val[0]
    filters.end_time = val[1]
  } else {
    filters.start_time = ''
    filters.end_time = ''
  }
  loadLogs()
}

function resetFilters() {
  filters.log_type = ''
  filters.keyword = ''
  filters.module = ''
  filters.status = null
  filters.start_time = ''
  filters.end_time = ''
  dateRange.value = null
  currentPage.value = 1
  loadLogs()
}

async function handleClear() {
  clearing.value = true
  try {
    const res = await clearLogs(clearDays.value)
    ElMessage.success(res.msg || '清理成功')
    await loadLogs()
    await loadStats()
  } catch (e) {
    ElMessage.error('清理失败')
  } finally {
    clearing.value = false
  }
}

function showDetail(row) {
  currentLog.value = row
  detailVisible.value = true
}

function typeLabel(type) {
  return { api: 'API调用', db: '数据库', error: '错误', frontend: '前端操作' }[type] || type || 'API调用'
}

function logTypeTag(type) {
  return { api: '', db: 'warning', error: 'danger', frontend: 'success' }[type] || 'info'
}

function methodTagType(method) {
  return {
    GET: 'info', POST: 'success', PUT: 'warning', DELETE: 'danger',
    INSERT: 'success', UPDATE: 'warning', NAVIGATE: '',
  }[method] || 'info'
}

function moduleTagType(module) {
  const map = {
    '认证': '', '用户管理': 'success', '角色管理': 'success', '菜单管理': 'success',
    '预测': 'warning', '模型管理': 'warning', 'PLC管理': 'danger',
    '预测实例': 'warning', '烘丝机预测': 'danger', '特征方案': 'warning',
    '文件上传': 'info', '系统设置': '', '操作日志': 'info',
    '页面访问': 'success', 'Vue组件': 'danger', 'JavaScript': 'danger',
  }
  return map[module] || 'info'
}
</script>

<style scoped>
.log-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
}
.page-title {
  font-size: 20px;
  font-weight: 600;
}
.page-desc {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

/* 统计卡片 */
.stats-bar {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.stat-card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 12px 20px;
  min-width: 100px;
  text-align: center;
}
.stat-card.stat-error {
  border-color: var(--el-color-danger-light-5);
}
.stat-card.stat-error .stat-value {
  color: var(--el-color-danger);
}
.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--el-color-primary);
}
.stat-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

/* 筛选栏 */
.filter-bar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

/* 表格 */
.mono-url {
  font-family: 'Courier New', monospace;
  font-size: 12px;
}
.error-msg {
  color: var(--el-color-danger);
  font-size: 12px;
}
.slow-ms {
  color: var(--el-color-warning);
  font-weight: 600;
}
.params-pre {
  background: var(--el-fill-color-light);
  padding: 8px;
  border-radius: 4px;
  font-size: 12px;
  max-height: 200px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
.pagination-bar {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
}
</style>
