<!-- src/views/system/config/index.vue -->
<template>
  <div class="config-page">
    <div class="page-header">
      <h2>系统设置</h2>
      <p>管理系统全局配置参数</p>
    </div>

    <div class="config-collapse" v-loading="loading">
      <!-- 实例类型配置 -->
      <div class="collapse-item" :class="{ open: expandedKeys.includes('instance_types') }">
        <div class="collapse-header" @click="toggle('instance_types')">
          <div class="ch-left">
            <el-icon class="ch-arrow"><ArrowRight /></el-icon>
            <span class="ch-title">预测实例类型</span>
            <el-tag size="small" type="success" effect="plain">
              已启用 {{ allMenus.filter(m => m.as_instance_type === 'Y').length }} 项
            </el-tag>
          </div>
          <span class="ch-hint">从菜单中选取可用作预测实例类型的菜单项</span>
        </div>
        <div class="collapse-body" v-show="expandedKeys.includes('instance_types')">
          <div class="instance-type-list">
            <div
              v-for="m in allMenus"
              :key="m.menu_id"
              class="instance-type-row"
            >
              <div class="itr-info">
                <el-icon v-if="m.icon && m.icon !== '#'" style="margin-right: 6px">
                  <component :is="m.icon" />
                </el-icon>
                <span class="itr-name">{{ m.menu_name }}</span>
                <el-tag size="small" type="info" effect="plain">{{ m.path }}</el-tag>
              </div>
              <el-switch
                :model-value="m.as_instance_type === 'Y'"
                @change="val => handleInstanceFlagChange(m, val)"
                :loading="flagUpdating === m.menu_id"
                active-text="可用"
                inactive-text="不可用"
              />
            </div>
            <el-empty v-if="allMenus.length === 0" description="暂无菜单数据" :image-size="48" />
          </div>
        </div>
      </div>

      <!-- 其他配置项 -->
      <div
        v-for="item in otherConfigs"
        :key="item.config_id"
        class="collapse-item"
        :class="{ open: expandedKeys.includes(item.config_key) }"
      >
        <div class="collapse-header" @click="toggle(item.config_key)">
          <div class="ch-left">
            <el-icon class="ch-arrow"><ArrowRight /></el-icon>
            <span class="ch-title">{{ item.config_name }}</span>
            <!-- 布尔型显示当前状态 -->
            <el-tag
              v-if="isBoolKey(item.config_key)"
              size="small"
              :type="item.config_value === 'true' ? 'success' : 'info'"
              effect="plain"
            >
              {{ item.config_value === 'true' ? '已启用' : '已禁用' }}
            </el-tag>
          </div>
          <span class="ch-hint">{{ item.remark || item.config_key }}</span>
        </div>
        <div class="collapse-body" v-show="expandedKeys.includes(item.config_key)">
          <!-- 布尔型开关 -->
          <div v-if="isBoolKey(item.config_key)" class="collapse-value">
            <el-switch
              :model-value="item.config_value === 'true'"
              @change="val => handleToggle(item, val)"
              :loading="updating === item.config_id"
              active-text="启用"
              inactive-text="禁用"
            />
          </div>
          <!-- 文本型 -->
          <div v-else class="collapse-value text-value-row">
            <el-input
              v-model="editValues[item.config_id]"
              :placeholder="item.config_value"
              style="width: 360px"
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
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowRight } from '@element-plus/icons-vue'
import request from '../../../api/request'

const configs = ref([])
const loading = ref(false)
const updating = ref(null)
const editValues = reactive({})

// 展开控制
const expandedKeys = ref([])

function toggle(key) {
  const idx = expandedKeys.value.indexOf(key)
  if (idx >= 0) {
    expandedKeys.value.splice(idx, 1)
  } else {
    expandedKeys.value.push(key)
  }
}

// 菜单列表（用于实例类型配置）
const allMenus = ref([])
const flagUpdating = ref(null)

const otherConfigs = computed(() => {
  return configs.value.filter(c => c.config_key !== 'prediction_instance_types')
})

const boolKeys = ['model_delete_local_file']

function isBoolKey(key) {
  return boolKeys.includes(key)
}

onMounted(() => {
  loadConfigs()
  loadAllMenus()
})

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

async function loadAllMenus() {
  try {
    const res = await request.get('/system/menu/tree')
    const flat = []
    function walk(nodes) {
      for (const n of nodes) {
        if (n.menu_type === 'C' && n.component) {
          flat.push(n)
        }
        if (n.children && n.children.length) walk(n.children)
      }
    }
    walk(res)
    allMenus.value = flat
  } catch (e) {
    console.error('加载菜单失败:', e)
  }
}

async function handleInstanceFlagChange(menu, val) {
  flagUpdating.value = menu.menu_id
  try {
    await request.put('/system/menu/update', {
      ...menu,
      as_instance_type: val ? 'Y' : 'N',
      parent_id: menu.parent_id || 0,
    })
    menu.as_instance_type = val ? 'Y' : 'N'
    ElMessage.success(`${menu.menu_name} 已${val ? '启用' : '禁用'}作为实例类型（下次新建实例时生效）`)
  } catch (e) {
    ElMessage.error('修改失败')
  } finally {
    flagUpdating.value = null
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
  margin-bottom: 20px;
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

/* 折叠面板 */
.config-collapse {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.collapse-item {
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 10px;
  overflow: hidden;
  transition: border-color 0.2s;
}

.collapse-item:hover {
  border-color: var(--border-hover);
}

.collapse-item.open {
  border-color: var(--accent);
}

/* 折叠头 */
.collapse-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
}

.collapse-header:hover {
  background: var(--bg-secondary);
}

.ch-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ch-arrow {
  font-size: 14px;
  color: var(--text-muted);
  transition: transform 0.25s ease;
  flex-shrink: 0;
}

.collapse-item.open .ch-arrow {
  transform: rotate(90deg);
}

.ch-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.ch-hint {
  font-size: 12px;
  color: var(--text-muted);
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 折叠内容 */
.collapse-body {
  border-top: 1px solid var(--border-secondary);
  padding: 20px;
  animation: slideDown 0.2s ease;
}

@keyframes slideDown {
  from { opacity: 0; transform: translateY(-6px); }
  to   { opacity: 1; transform: translateY(0); }
}

.collapse-value {
  display: flex;
  align-items: center;
  gap: 12px;
}

.text-value-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 实例类型列表 */
.instance-type-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.instance-type-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border-radius: 8px;
  border: 1px solid var(--border-secondary);
}

.itr-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.itr-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}
</style>
