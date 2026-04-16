<template>
  <div class="menu-container">
    <!-- 操作栏 -->
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <el-button type="primary" @click="handleAdd(null)">
            <el-icon><Plus /></el-icon> 新增
          </el-button>
          <el-button @click="toggleExpand">
            <el-icon><Sort /></el-icon> {{ isExpand ? '折叠' : '展开' }}
          </el-button>
        </div>
      </template>

      <el-table
        v-loading="loading"
        :data="menuTree"
        row-key="menu_id"
        :default-expand-all="isExpand"
        :tree-props="{ children: 'children' }"
        border
        stripe
      >
        <el-table-column prop="menu_name" label="菜单名称" min-width="180" />
        <el-table-column prop="icon" label="图标" width="80" align="center">
          <template #default="{ row }">
            <el-icon v-if="row.icon && row.icon !== '#'">
              <component :is="row.icon" />
            </el-icon>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="order_num" label="排序" width="80" align="center" />
        <el-table-column prop="path" label="路由地址" min-width="150" />
        <el-table-column prop="component" label="组件路径" min-width="180" />
        <el-table-column label="类型" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.menu_type === 'M'" type="warning" size="small">目录</el-tag>
            <el-tag v-else-if="row.menu_type === 'C'" type="success" size="small">菜单</el-tag>
            <el-tag v-else-if="row.menu_type === 'F'" type="info" size="small">按钮</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="可见" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.visible === '0' ? 'success' : 'info'" size="small">
              {{ row.visible === '0' ? '显示' : '隐藏' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === '0' ? 'success' : 'danger'" size="small">
              {{ row.status === '0' ? '正常' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleAdd(row)">
              <el-icon><Plus /></el-icon> 新增
            </el-button>
            <el-button link type="primary" size="small" @click="handleEdit(row)">
              <el-icon><Edit /></el-icon> 修改
            </el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">
              <el-icon><Delete /></el-icon> 删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑 弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="680px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-width="100px"
      >
        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item label="上级菜单">
              <el-tree-select
                v-model="form.parent_id"
                :data="menuTreeOptions"
                :props="{ label: 'menu_name', value: 'menu_id', children: 'children' }"
                check-strictly
                clearable
                placeholder="选择上级菜单（不选则为顶级）"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="菜单类型" prop="menu_type">
              <el-radio-group v-model="form.menu_type">
                <el-radio value="M">目录</el-radio>
                <el-radio value="C">菜单</el-radio>
                <el-radio value="F">按钮</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="菜单名称" prop="menu_name">
              <el-input v-model="form.menu_name" placeholder="请输入菜单名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="排序" prop="order_num">
              <el-input-number v-model="form.order_num" :min="0" :max="999" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12" v-if="form.menu_type !== 'F'">
            <el-form-item label="路由地址" prop="path">
              <el-input v-model="form.path" placeholder="请输入路由地址" />
            </el-form-item>
          </el-col>
          <el-col :span="12" v-if="form.menu_type === 'C'">
            <el-form-item label="组件路径">
              <el-input v-model="form.component" placeholder="如：system/user/index" />
            </el-form-item>
          </el-col>
          <el-col :span="12" v-if="form.menu_type !== 'F'">
            <el-form-item label="菜单图标">
              <el-input v-model="form.icon" placeholder="请输入图标名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12" v-if="form.menu_type !== 'F'">
            <el-form-item label="是否显示">
              <el-radio-group v-model="form.visible">
                <el-radio value="0">显示</el-radio>
                <el-radio value="1">隐藏</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="菜单状态">
              <el-radio-group v-model="form.status">
                <el-radio value="0">正常</el-radio>
                <el-radio value="1">停用</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="备注">
              <el-input v-model="form.remark" type="textarea" placeholder="请输入备注" />
            </el-form-item>
          </el-col>
        </el-row>
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
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Sort } from '@element-plus/icons-vue'
import { getMenuTree, addMenu, updateMenu, deleteMenu } from '@/api/menu'

const loading = ref(false)
const submitLoading = ref(false)
const menuTree = ref([])
const isExpand = ref(true)

// 弹窗
const dialogVisible = ref(false)
const dialogTitle = ref('')
const isEdit = ref(false)
const formRef = ref(null)
const menuTreeOptions = ref([])

const form = reactive({
  menu_id: 0,
  menu_name: '',
  parent_id: null,
  order_num: 0,
  path: '',
  component: '',
  menu_type: 'C',
  visible: '0',
  status: '0',
  icon: '#',
  remark: '',
})

const formRules = {
  menu_name: [{ required: true, message: '请输入菜单名称', trigger: 'blur' }],
  menu_type: [{ required: true, message: '请选择菜单类型', trigger: 'change' }],
  order_num: [{ required: true, message: '请输入排序', trigger: 'blur' }],
}

async function loadMenuTree() {
  loading.value = true
  try {
    menuTree.value = await getMenuTree()
  } catch (e) {
    ElMessage.error('获取菜单列表失败')
  } finally {
    loading.value = false
  }
}

async function loadMenuTreeOptions() {
  try {
    // 构建带"顶级菜单"选项的树
    const tree = await getMenuTree()
    menuTreeOptions.value = [
      { menu_id: 0, menu_name: '顶级菜单', children: tree }
    ]
  } catch (e) {
    console.error('获取菜单树失败:', e)
  }
}

function toggleExpand() {
  isExpand.value = !isExpand.value
  // 重新加载表格以应用展开状态
  loadMenuTree()
}

function resetForm() {
  form.menu_id = 0
  form.menu_name = ''
  form.parent_id = null
  form.order_num = 0
  form.path = ''
  form.component = ''
  form.menu_type = 'C'
  form.visible = '0'
  form.status = '0'
  form.icon = '#'
  form.remark = ''
}

function handleAdd(parentRow) {
  resetForm()
  isEdit.value = false
  dialogTitle.value = parentRow ? `新增「${parentRow.menu_name}」的子菜单` : '新增菜单'
  if (parentRow) {
    form.parent_id = parentRow.menu_id
  }
  loadMenuTreeOptions()
  dialogVisible.value = true
}

function handleEdit(row) {
  resetForm()
  isEdit.value = true
  dialogTitle.value = '修改菜单'
  form.menu_id = row.menu_id
  form.menu_name = row.menu_name
  form.parent_id = row.parent_id || null
  form.order_num = row.order_num
  form.path = row.path
  form.component = row.component
  form.menu_type = row.menu_type
  form.visible = row.visible
  form.status = row.status
  form.icon = row.icon
  form.remark = row.remark
  loadMenuTreeOptions()
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  submitLoading.value = true
  try {
    const data = { ...form }
    if (!data.parent_id) data.parent_id = 0

    if (isEdit.value) {
      await updateMenu(data)
      ElMessage.success('修改成功')
    } else {
      await addMenu(data)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    loadMenuTree()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  } finally {
    submitLoading.value = false
  }
}

async function handleDelete(row) {
  if (row.children && row.children.length > 0) {
    ElMessage.warning('该菜单下存在子菜单，请先删除子菜单')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确认删除菜单「${row.menu_name}」吗？`,
      '提示',
      { type: 'warning' }
    )
  } catch {
    return
  }

  try {
    await deleteMenu(row.menu_id)
    ElMessage.success('删除成功')
    loadMenuTree()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

onMounted(() => {
  loadMenuTree()
})
</script>

<style scoped>
.menu-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: flex-start;
  gap: 8px;
}
</style>
