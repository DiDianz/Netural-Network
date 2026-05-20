<!-- src/components/ColumnMapper.vue -->
<!-- 智能列映射组件：解析文件表头 → 自动匹配 → 用户手动调整 → 输出映射关系 -->
<template>
  <div class="column-mapper" v-if="visible">
    <div class="mapper-header">
      <div class="mapper-title">
        <el-icon><SetUp /></el-icon>
        <span>列映射配置</span>
      </div>
      <div class="mapper-subtitle">
        文件 <b>{{ fileInfo.filename }}</b>（{{ fileInfo.total_rows }} 行，{{ fileInfo.file_headers.length }} 列）
        — 请确认每列对应的角色
      </div>
    </div>

    <!-- 自动匹配结果提示 -->
    <div class="match-status" :class="autoOk ? 'match-ok' : 'match-partial'">
      <template v-if="autoOk">
        <el-icon><CircleCheckFilled /></el-icon>
        自动匹配成功！所有必需列已识别，可以直接上传。
      </template>
      <template v-else>
        <el-icon><WarningFilled /></el-icon>
        自动匹配了 {{ matchedCount }}/{{ totalNeeded }} 列，请手动补齐缺失的映射。
      </template>
    </div>

    <!-- 映射表格 -->
    <div class="mapper-table-wrap">
      <el-table :data="mappingRows" stripe size="small" border style="width: 100%">
        <el-table-column label="列序号" width="70" align="center">
          <template #default="{ row }">
            <span class="col-index">{{ row.index + 1 }}</span>
          </template>
        </el-table-column>

        <el-table-column label="文件列名" min-width="140">
          <template #default="{ row }">
            <span class="header-name">{{ row.header }}</span>
          </template>
        </el-table-column>

        <el-table-column label="映射到 →" min-width="220">
          <template #default="{ row }">
            <el-select
              v-model="row.role"
              placeholder="选择角色"
              clearable
              filterable
              size="small"
              style="width: 100%"
              @change="onMappingChange"
            >
              <el-option-group label="📊 特征列">
                <el-option
                  v-for="f in schemaReqs.features"
                  :key="'feature:' + f.name"
                  :label="`特征: ${f.name} (${f.label})`"
                  :value="`feature:${f.name}`"
                  :disabled="isRoleAssigned(`feature:${f.name}`, row.index)"
                />
              </el-option-group>
              <el-option-group label="🎯 预测目标">
                <el-option
                  :label="`目标: ${schemaReqs.target.name} (${schemaReqs.target.label})`"
                  :value="'target'"
                  :disabled="isRoleAssigned('target', row.index)"
                />
              </el-option-group>
              <el-option-group label="🏷️ 标识列">
                <el-option
                  :label="`标识: ${schemaReqs.brand.name} (${schemaReqs.brand.label})`"
                  :value="'brand'"
                  :disabled="isRoleAssigned('brand', row.index)"
                />
              </el-option-group>
              <el-option-group label="⏭️ 忽略">
                <el-option label="（跳过此列）" value="__skip__" />
              </el-option-group>
            </el-select>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.role && row.role !== '__skip__'" type="success" size="small" effect="plain">
              已映射
            </el-tag>
            <el-tag v-else-if="row.role === '__skip__'" type="info" size="small" effect="plain">
              跳过
            </el-tag>
            <el-tag v-else type="warning" size="small" effect="plain">
              未映射
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 映射摘要 -->
    <div class="mapping-summary">
      <div class="summary-item" v-for="item in summaryItems" :key="item.role"
        :class="{ 'summary-ok': item.mapped, 'summary-missing': !item.mapped }">
        <span class="summary-icon">{{ item.mapped ? '✅' : '❌' }}</span>
        <span class="summary-label">{{ item.label }}</span>
        <span class="summary-col" v-if="item.mapped">← {{ item.colName }}</span>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="mapper-actions">
      <el-button @click="$emit('cancel')">取消</el-button>
      <el-button type="info" plain @click="autoDetect">重新自动匹配</el-button>
      <el-button type="primary" :disabled="!canConfirm" @click="confirmMapping">
        {{ autoOk ? '确认上传' : '确认映射并上传' }}
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { SetUp, CircleCheckFilled, WarningFilled } from '@element-plus/icons-vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  fileInfo: {
    type: Object,
    default: () => ({
      filename: '',
      file_headers: [],
      total_rows: 0,
      schema_requirements: { features: [], target: {}, brand: {} },
      auto_mapping: {},
      matched_count: 0,
      total_needed: 0,
      auto_ok: false,
    })
  },
})

const emit = defineEmits(['confirm', 'cancel'])

// 映射行数据
const mappingRows = ref([])

// schema 需求
const schemaReqs = computed(() => props.fileInfo.schema_requirements || { features: [], target: {}, brand: {} })

// 匹配状态
const matchedCount = ref(0)
const totalNeeded = ref(0)
const autoOk = ref(false)

// 初始化映射行
function initRows() {
  const fi = props.fileInfo
  if (!fi || !fi.file_headers) return

  const headers = fi.file_headers
  const auto = fi.auto_mapping || {}

  mappingRows.value = headers.map((h, idx) => ({
    index: idx,
    header: h,
    role: auto[String(idx)] || auto[idx] || '',
  }))

  matchedCount.value = fi.matched_count || 0
  totalNeeded.value = fi.total_needed || 0
  autoOk.value = fi.auto_ok || false
}

watch(() => props.visible, (v) => { if (v) initRows() })
watch(() => props.fileInfo, () => { if (props.visible) initRows() }, { deep: true })
onMounted(() => { if (props.visible) initRows() })

// 某角色是否已被其他行占用
function isRoleAssigned(role, currentIndex) {
  if (!role || role === '__skip__') return false
  return mappingRows.value.some(r => r.index !== currentIndex && r.role === role)
}

// 映射变化时更新状态
function onMappingChange() {
  updateMatchStatus()
}

function updateMatchStatus() {
  const reqs = schemaReqs.value
  const roles = mappingRows.value.map(r => r.role).filter(Boolean)

  let matched = 0
  const featureNames = (reqs.features || []).map(f => f.name)
  for (const fn of featureNames) {
    if (roles.includes(`feature:${fn}`)) matched++
  }
  if (roles.includes('target')) matched++
  if (roles.includes('brand')) matched++

  matchedCount.value = matched
  totalNeeded.value = featureNames.length + 2
  autoOk.value = matched === totalNeeded.value
}

// 是否可以确认
const canConfirm = computed(() => autoOk.value)

// 自动检测
function autoDetect() {
  const fi = props.fileInfo
  if (!fi) return
  const auto = fi.auto_mapping || {}
  mappingRows.value.forEach(row => {
    row.role = auto[String(row.index)] || auto[row.index] || ''
  })
  updateMatchStatus()
}

// 确认映射
function confirmMapping() {
  const mapping = {}
  mappingRows.value.forEach(row => {
    if (row.role && row.role !== '__skip__') {
      mapping[String(row.index)] = row.role
    }
  })
  emit('confirm', mapping)
}

// 映射摘要
const summaryItems = computed(() => {
  const reqs = schemaReqs.value
  const items = []
  const roles = {}

  mappingRows.value.forEach(r => {
    if (r.role && r.role !== '__skip__') {
      roles[r.role] = r.header
    }
  })

  // 特征列
  for (const f of (reqs.features || [])) {
    const role = `feature:${f.name}`
    items.push({
      role,
      label: `${f.name} (${f.label || '特征'})`,
      mapped: !!roles[role],
      colName: roles[role] || '',
    })
  }

  // 目标列
  items.push({
    role: 'target',
    label: `${reqs.target?.name || 'target'} (${reqs.target?.label || '预测目标'})`,
    mapped: !!roles['target'],
    colName: roles['target'] || '',
  })

  // 品牌列
  items.push({
    role: 'brand',
    label: `${reqs.brand?.name || 'brand'} (${reqs.brand?.label || '标识'})`,
    mapped: !!roles['brand'],
    colName: roles['brand'] || '',
  })

  return items
})
</script>

<style scoped>
.column-mapper {
  background: var(--bg-card, #fff);
  border: 2px solid var(--accent, #409eff);
  border-radius: 12px;
  padding: 20px;
  margin: 16px 0;
}

.mapper-header {
  margin-bottom: 16px;
}

.mapper-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #303133);
}

.mapper-subtitle {
  font-size: 13px;
  color: var(--text-muted, #909399);
  margin-top: 6px;
}

.match-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
  margin-bottom: 16px;
}

.match-ok {
  background: #f0f9ff;
  color: #059669;
  border: 1px solid #a7f3d0;
}

.match-partial {
  background: #fffbeb;
  color: #d97706;
  border: 1px solid #fde68a;
}

.mapper-table-wrap {
  max-height: 400px;
  overflow-y: auto;
  margin-bottom: 16px;
}

.col-index {
  font-weight: 700;
  color: var(--accent, #409eff);
  font-family: 'DM Mono', monospace;
}

.header-name {
  font-family: 'Courier New', monospace;
  font-size: 13px;
  color: var(--text-primary, #303133);
}

.mapping-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
  padding: 12px;
  background: var(--bg-secondary, #f5f7fa);
  border-radius: 8px;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 6px;
}

.summary-ok {
  background: #f0f9ff;
  color: #059669;
}

.summary-missing {
  background: #fef2f2;
  color: #dc2626;
}

.summary-icon {
  font-size: 12px;
}

.summary-label {
  font-weight: 500;
}

.summary-col {
  color: var(--text-muted, #909399);
  font-family: monospace;
}

.mapper-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
