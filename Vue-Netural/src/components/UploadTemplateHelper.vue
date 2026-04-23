<!-- src/components/UploadTemplateHelper.vue -->
<!-- 上传模板下载助手 — 显示列结构说明 + 下载模板按钮 -->
<template>
  <div class="template-helper">
    <div class="template-actions">
      <el-button type="primary" plain size="small" @click="handleDownload('csv')">
        <el-icon><Download /></el-icon> 下载 CSV 模板
      </el-button>
      <el-button type="success" plain size="small" @click="handleDownload('xlsx')">
        <el-icon><Download /></el-icon> 下载 Excel 模板
      </el-button>
    </div>

    <!-- 列结构说明 -->
    <div class="column-guide" v-if="columnInfo">
      <div class="guide-title">
        <el-icon><InfoFilled /></el-icon>
        数据格式要求（共需 <b>{{ columnInfo.min_columns }}</b> 列）
      </div>
      <div class="guide-desc">
        方案「{{ columnInfo.schema_name }}」要求每行数据按以下 <b>固定顺序</b> 排列：
      </div>

      <!-- 特征列 -->
      <div class="column-section">
        <div class="section-label">📊 特征列（前 {{ columnInfo.input_dim }} 列）</div>
        <div class="column-tags">
          <el-tag v-for="(f, idx) in columnInfo.features" :key="f.name"
            type="primary" size="small" effect="plain" class="col-tag">
            <span class="col-idx">{{ idx + 1 }}</span> {{ f.name }}
            <span class="col-label" v-if="f.label">（{{ f.label }}）</span>
          </el-tag>
        </div>
      </div>

      <!-- 目标列 -->
      <div class="column-section">
        <div class="section-label">🎯 预测目标（第 {{ columnInfo.input_dim + 1 }} 列）</div>
        <el-tag type="danger" size="small" effect="dark" class="col-tag">
          <span class="col-idx">{{ columnInfo.input_dim + 1 }}</span> {{ columnInfo.target.name }}
          <span class="col-label" v-if="columnInfo.target.label">（{{ columnInfo.target.label }}）</span>
        </el-tag>
      </div>

      <!-- 品牌列 -->
      <div class="column-section">
        <div class="section-label">🏷️ 品牌列（第 {{ columnInfo.input_dim + 2 }} 列）</div>
        <el-tag type="warning" size="small" effect="dark" class="col-tag">
          <span class="col-idx">{{ columnInfo.input_dim + 2 }}</span> {{ columnInfo.brand_column.name }}
          <span class="col-label" v-if="columnInfo.brand_column.label">（{{ columnInfo.brand_column.label }}）</span>
        </el-tag>
      </div>

      <!-- CSV 表头示例 -->
      <div class="header-example">
        <div class="example-label">CSV 表头示例（可直接复制）：</div>
        <div class="example-code" @click="copyHeader">
          {{ columnInfo.csv_header_example }}
          <el-icon class="copy-icon"><CopyDocument /></el-icon>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, InfoFilled, CopyDocument } from '@element-plus/icons-vue'
import { getColumnDescription } from '@/api/feature'
import { downloadTemplate } from '@/api/model'

const props = defineProps({
  schemaId: { type: String, default: 'default' }
})

const columnInfo = ref(null)

async function loadColumnInfo() {
  try {
    const res = await getColumnDescription(props.schemaId)
    columnInfo.value = res.data
  } catch (e) {
    console.error('加载列结构失败:', e)
  }
}

watch(() => props.schemaId, loadColumnInfo)
onMounted(loadColumnInfo)

function handleDownload(format) {
  downloadTemplate(format, props.schemaId)
}

function copyHeader() {
  if (!columnInfo.value) return
  navigator.clipboard.writeText(columnInfo.value.csv_header_example).then(() => {
    ElMessage.success('表头已复制到剪贴板')
  }).catch(() => {
    ElMessage.info('请手动复制')
  })
}
</script>

<style scoped>
.template-helper {
  margin: 12px 0;
}
.template-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.column-guide {
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 8px;
  padding: 14px 16px;
  font-size: 13px;
}
.guide-title {
  font-size: 14px;
  font-weight: 600;
  color: #0369a1;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.guide-desc {
  color: #64748b;
  margin-bottom: 12px;
}
.column-section {
  margin-bottom: 10px;
}
.section-label {
  font-weight: 500;
  margin-bottom: 4px;
  color: #334155;
}
.column-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.col-tag {
  font-family: 'Courier New', monospace;
  font-size: 12px;
}
.col-idx {
  display: inline-block;
  background: rgba(0,0,0,0.15);
  border-radius: 3px;
  padding: 0 4px;
  margin-right: 3px;
  font-weight: 700;
  font-size: 11px;
}
.col-label {
  color: #94a3b8;
  font-family: system-ui, sans-serif;
}
.header-example {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed #cbd5e1;
}
.example-label {
  font-weight: 500;
  margin-bottom: 4px;
  color: #334155;
}
.example-code {
  background: #1e293b;
  color: #38bdf8;
  padding: 8px 12px;
  border-radius: 6px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  word-break: break-all;
}
.example-code:hover {
  background: #334155;
}
.copy-icon {
  flex-shrink: 0;
  margin-left: 8px;
  color: #94a3b8;
}
</style>
