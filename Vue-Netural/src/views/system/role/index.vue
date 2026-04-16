<template>
  <div class="role-container">
    <!-- 搜索栏 -->
    <el-card class="search-card" shadow="never">
      <el-form :model="queryParams" inline>
        <el-form-item label="角色名称">
          <el-input
            v-model="queryParams.role_name"
            placeholder="请输入角色名称"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="queryParams.status" placeholder="全部" clearable style="width: 120px">
            <el-option label="正常" value="0" />
            <el-option label="停用" value="1" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon> 搜索
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon> 重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 操作栏 + 表格 -->
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon> 新增
          </el-button>
        </div>
      </template>

      <el-table
        v-loading="loading"
        :data="tableData"
        border
        stripe
        style="width: 100%"
      >
        <el-table-column prop="role_id" label="角色ID" width="80" align="center" />
        <el-table-column prop="role_name" label="角色名称" width="150" />
        <el-table-column prop="role_key" label="权限标识" width="150" />
        <el-table-column prop="sort" label="排序" width="80" align="center" />
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === '0' ? 'success' : 'danger'" size="small">
              {{ row.status === '0' ? '正常' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.create_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="180" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              size="small"
              @click="handleEdit(row)"
            >
              <el-icon><Edit /></el-icon> 修改
            </el-button>
            <el-button
              v-if="row.role_key !== 'admin'"
              link
              type="danger"
              size="small"
              @click="handleDelete(row)"
            >
              <el-icon><Delete /></el-icon> 删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.page_size"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="getList"
          @current-change="getList"
        />
      </div>
    </el-card>

    <!-- 新增/编辑 弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="角色名称" prop="role_name">
          <el-input v-model="form.role_name" placeholder="请输入角色名称" />
        </el-form-item>
        <el-form-item label="权限标识" prop="role_key">
          <el-input
            v-model="form.role_key"
            placeholder="请输入权限标识"
            :disabled="isEdit && form.role_key === 'admin'"
          />
        </el-form-item>
        <el-form-item label="排序" prop="sort">
          <el-input-number v-model="form.sort" :min="0" :max="999" style="width: 100%" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio value="0">正常</el-radio>
            <el-radio value="1">停用</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="菜单权限">
          <el-tree
            ref="menuTreeRef"
            :data="menuTreeData"
            :props="{ label: 'menu_name', children: 'children' }"
            show-checkbox
            node-key="menu_id"
            check-strictly
            default-expand-all
            style="max-height: 300px; overflow-y: auto; width: 100%; border: 1px solid #dcdfe6; border-radius: 4px; padding: 8px"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" placeholder="请输入备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取 消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">
          确 定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus, Edit, Delete } from '@element-plus/icons-vue'
import { getRoleList, addRole, updateRole, deleteRole } from '@/api/role'
import { getMenuTreeSelect } from '@/api/menu'

const loading = ref(false)
const submitLoading = ref(false)
const tableData = ref([])
const total = ref(0)

const queryParams = reactive({
  page: 1,
  page_size: 10,
  role_name: '',
  status: '',
})

// 弹窗
const dialogVisible = ref(false)
const dialogTitle = ref('')
const isEdit = ref(false)
const formRef = ref(null)
const menuTreeRef = ref(null)
const menuTreeData = ref([])

const form = reactive({
  role_id: 0,
  role_name: '',
  role_key: '',
  sort: 0,
  status: '0',
  remark: '',
  menu_ids: [],
})

const formRules = {
  role_name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
  role_key: [{ required: true, message: '请输入权限标识', trigger: 'blur' }],
  sort: [{ required: true, message: '请输入排序', trigger: 'blur' }],
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

async function getList() {
  loading.value = true
  try {
    const res = await getRoleList(queryParams)
    tableData.value = res.rows || []
    total.value = res.total || 0
  } catch (e) {
    ElMessage.error('获取角色列表失败')
  } finally {
    loading.value = false
  }
}

async function loadMenuTree() {
  try {
    menuTreeData.value = await getMenuTreeSelect()
  } catch (e) {
    console.error('获取菜单树失败:', e)
  }
}

// 收集所有叶子节点 menu_id（非目录类型的菜单/按钮）
function collectLeafIds(nodes) {
  const ids = []
  function walk(list) {
    for (const n of list) {
      if (n.children && n.children.length > 0) {
        walk(n.children)
      } else {
        ids.push(n.menu_id)
      }
    }
  }
  walk(nodes)
  return ids
}

// 收集所有节点 menu_id
function collectAllIds(nodes) {
  const ids = []
  function walk(list) {
    for (const n of list) {
      ids.push(n.menu_id)
      if (n.children && n.children.length > 0) {
        walk(n.children)
      }
    }
  }
  walk(nodes)
  return ids
}

function handleSearch() {
  queryParams.page = 1
  getList()
}

function handleReset() {
  queryParams.role_name = ''
  queryParams.status = ''
  queryParams.page = 1
  getList()
}

function resetForm() {
  form.role_id = 0
  form.role_name = ''
  form.role_key = ''
  form.sort = 0
  form.status = '0'
  form.remark = ''
  form.menu_ids = []
}

async function handleAdd() {
  resetForm()
  isEdit.value = false
  dialogTitle.value = '新增角色'
  dialogVisible.value = true
  await nextTick()
  await loadMenuTree()
  await nextTick()
  menuTreeRef.value?.setCheckedKeys([])
}

async function handleEdit(row) {
  resetForm()
  isEdit.value = true
  dialogTitle.value = '修改角色'

  try {
    const detail = await (await import('@/api/role')).getRoleDetail(row.role_id)
    form.role_id = detail.role_id
    form.role_name = detail.role_name
    form.role_key = detail.role_key
    form.sort = detail.sort
    form.status = detail.status
    form.remark = detail.remark
    form.menu_ids = detail.menu_ids || []

    dialogVisible.value = true
    await nextTick()
    await loadMenuTree()
    await nextTick()
    // 设置已选中的菜单
    menuTreeRef.value?.setCheckedKeys(form.menu_ids)
  } catch (e) {
    ElMessage.error('获取角色详情失败')
  }
}

async function handleSubmit() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  // 获取选中的菜单 ID
  const checkedKeys = menuTreeRef.value?.getCheckedKeys() || []
  const halfCheckedKeys = menuTreeRef.value?.getHalfCheckedKeys() || []
  form.menu_ids = [...checkedKeys, ...halfCheckedKeys]

  submitLoading.value = true
  try {
    if (isEdit.value) {
      await updateRole(form)
      ElMessage.success('修改成功')
    } else {
      await addRole(form)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    getList()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  } finally {
    submitLoading.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除角色「${row.role_name}」吗？`,
      '提示',
      { type: 'warning' }
    )
  } catch {
    return
  }

  try {
    await deleteRole(row.role_id)
    ElMessage.success('删除成功')
    getList()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

onMounted(() => {
  getList()
})
</script>

<style scoped>
.role-container {
  padding: 20px;
}

.search-card {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  justify-content: flex-start;
}

.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
