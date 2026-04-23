<!-- src/views/system/config/index.vue -->
<template>
  <div class="config-page">
    <div class="page-header">
      <h2>系统设置</h2>
      <p>管理系统全局配置参数</p>
    </div>

    <div class="config-list" v-loading="loading">
      <div v-for="item in configs" :key="item.config_id" class="config-item">
        <div class="config-info">
          <div class="config-name">{{ item.config_name }}</div>
          <div class="config-key">{{ item.config_key }}</div>
          <div class="config-remark" v-if="item.remark">{{ item.remark }}</div>
        </div>
        <div class="config-value">
          <!-- 布尔型开关 -->
          <el-switch
            v-if="isBoolKey(item.config_key)"
            :model-value="item.config_value === 'true'"
            @change="val => handleToggle(item, val)"
            :loading="updating === item.config_id"
            active-text="启用"
            inactive-text="禁用"
          />
          <!-- 实例类型标签编辑器 -->
          <div v-else-if="isTagListKey(item.config_key)" class="tag-list-editor">
            <div class="tag-list-items">
              <div
                v-for="(tag, idx) in parseTagList(item.config_value)"
                :key="idx"
                class="tag-list-item"
              >
                <div class="tli-row">
                  <el-tag :type="idx === 0 ? 'primary' : 'warning'" effect="dark" size="default">
                    {{ tag.name }}
                  </el-tag>
                  <el-button
                    v-if="parseTagList(item.config_value).length > 1"
                    type="danger"
                    text
                    size="small"
                    :icon="Delete"
                    @click="removeTagItem(item, idx)"
                  />
                </div>
                <div class="tli-desc">{{ tag.desc }}</div>
              </div>
            </div>
            <div class="tag-list-add">
              <el-input
                v-model="newTagKey"
                placeholder="类型标识 (如: realtime)"
                style="width: 160px"
                size="default"
              />
              <el-input
                v-model="newTagName"
                placeholder="显示名称"
                style="width: 180px"
                size="default"
              />
              <el-input
                v-model="newTagDesc"
                placeholder="描述说明"
                style="width: 260px"
                size="default"
              />
              <el-button
                type="primary"
                size="default"
                @click="addTagItem(item)"
                :disabled="!newTagKey.trim() || !newTagName.trim()"
              >
                添加
              </el-button>
            </div>
          </div>
          <!-- 文本型 -->
          <div v-else class="text-value-row">
            <el-input
              v-model="editValues[item.config_id]"
              :placeholder="item.config_value"
              style="width: 300px"
              size="default"
            />
            <el-button
              type="primary"
              size="default"
              @click="handleSaveText(item)"
              :loading="updating === item.config_id"
            >
              保存
            </el-button>
          </div>
        </div>
      </div>

      <el-empty v-if="!loading && configs.length === 0" description="暂无系统配置" />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import request from '../../../api/request'

const configs = ref([])
const loading = ref(false)
const updating = ref(null)
const editValues = reactive({})

// 实例类型新增字段
const newTagKey = ref('')
const newTagName = ref('')
const newTagDesc = ref('')

const boolKeys = ['model_delete_local_file']
const tagListKeys = ['prediction_instance_types']

function isBoolKey(key) {
  return boolKeys.includes(key)
}

function isTagListKey(key) {
  return tagListKeys.includes(key)
}

function parseTagList(val) {
  try {
    const arr = JSON.parse(val)
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
}

async function saveTagList(item, list) {
  const jsonStr = JSON.stringify(list)
  updating.value = item.config_id
  try {
    await request.put('/system/config/update', {
      config_id: item.config_id,
      config_value: jsonStr
    })
    item.config_value = jsonStr
    ElMessage.success('保存成功')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    updating.value = null
  }
}

function addTagItem(item) {
  const key = newTagKey.value.trim()
  const name = newTagName.value.trim()
  const desc = newTagDesc.value.trim()
  if (!key || !name) return

  const list = parseTagList(item.config_value)
  if (list.some(t => t.key === key)) {
    ElMessage.warning('类型标识已存在')
    return
  }
  list.push({ key, name, desc })
  saveTagList(item, list)
  newTagKey.value = ''
  newTagName.value = ''
  newTagDesc.value = ''
}

function removeTagItem(item, idx) {
  const list = parseTagList(item.config_value)
  list.splice(idx, 1)
  saveTagList(item, list)
}

onMounted(() => { loadConfigs() })

async function loadConfigs() {
  loading.value = true
  try {
    const res = await request.get('/system/config/list')
    configs.value = res.data || []
    configs.value.forEach(c => {
      editValues[c.config_id] = c.config_value
    })
  } catch (e) {
    console.error(e)
    ElMessage.error('加载配置失败')
  } finally {
    loading.value = false
  }
}

async function handleToggle(item, val) {
  updating.value = item.config_id
  try {
    await request.put('/system/config/update', {
      config_id: item.config_id,
      config_value: val ? 'true' : 'false'
    })
    item.config_value = val ? 'true' : 'false'
    ElMessage.success('修改成功')
  } catch (e) {
    ElMessage.error('修改失败')
  } finally {
    updating.value = null
  }
}

async function handleSaveText(item) {
  updating.value = item.config_id
  try {
    await request.put('/system/config/update', {
      config_id: item.config_id,
      config_value: editValues[item.config_id] || ''
    })
    item.config_value = editValues[item.config_id] || ''
    ElMessage.success('保存成功')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    updating.value = null
  }
}
</script>

<style scoped>
.config-page {
  max-width: 900px;
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

.config-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.config-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 12px;
  transition: border-color 0.3s;
}

.config-item:hover {
  border-color: var(--border-hover);
}

.config-info {
  flex: 1;
}

.config-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.config-key {
  font-size: 12px;
  color: var(--text-muted);
  font-family: 'DM Mono', monospace;
  background: var(--bg-secondary);
  padding: 2px 8px;
  border-radius: 4px;
  display: inline-block;
}

.config-remark {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 6px;
}

.config-value {
  flex-shrink: 0;
  margin-left: 24px;
}

.text-value-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 实例类型标签编辑器 */
.tag-list-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 400px;
}

.tag-list-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tag-list-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 14px;
  background: var(--bg-secondary);
  border-radius: 8px;
  border: 1px solid var(--border-secondary);
}

.tli-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tli-desc {
  font-size: 12px;
  color: var(--text-muted);
  padding-left: 2px;
}

.tag-list-add {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
