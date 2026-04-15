<!-- src/views/system/user/index.vue -->
<template>
  <div class="user-container">
    <!-- 搜索栏 -->
    <el-card class="search-card" shadow="never">
      <el-form :model="queryParams" inline>
        <el-form-item label="账号">
          <el-input
            v-model="queryParams.user_name"
            placeholder="请输入账号"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input
            v-model="queryParams.phonenumber"
            placeholder="请输入手机号"
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
        <el-table-column prop="user_id" label="用户ID" width="80" align="center" />
        <el-table-column prop="user_name" label="账号" width="120" />
        <el-table-column prop="nick_name" label="昵称" width="120" />
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column prop="phonenumber" label="手机号" width="130" />
        <el-table-column label="角色" width="150">
          <template #default="{ row }">
            <el-tag
              v-for="name in row.role_names"
              :key="name"
              size="small"
              style="margin-right: 4px"
            >
              {{ name }}
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
        <el-table-column label="性别" width="70" align="center">
          <template #default="{ row }">
            {{ { '0': '男', '1': '女', '2': '未知' }[row.sex] || '未知' }}
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.create_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleEdit(row)">
              <el-icon><Edit /></el-icon> 修改
            </el-button>
            <el-button
              v-if="row.user_name !== 'admin'"
              link
              type="warning"
              size="small"
              @click="handleResetPwd(row)"
            >
              <el-icon><Key /></el-icon> 重置密码
            </el-button>
            <el-button
              v-if="row.user_name !== 'admin'"
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
        label-width="80px"
      >
        <el-form-item label="账号" prop="user_name">
          <el-input
            v-model="form.user_name"
            placeholder="请输入账号"
            :disabled="isEdit"
          />
        </el-form-item>
        <el-form-item v-if="!isEdit" label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="昵称" prop="nick_name">
          <el-input v-model="form.nick_name" placeholder="请输入昵称" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="手机号" prop="phonenumber">
          <el-input v-model="form.phonenumber" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="性别">
          <el-radio-group v-model="form.sex">
            <el-radio value="0">男</el-radio>
            <el-radio value="1">女</el-radio>
            <el-radio value="2">未知</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio value="0">正常</el-radio>
            <el-radio value="1">停用</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="角色" prop="role_ids">
          <el-select
            v-model="form.role_ids"
            multiple
            placeholder="请选择角色"
            style="width: 100%"
          >
            <el-option
              v-for="role in roleOptions"
              :key="role.role_id"
              :label="role.role_name"
              :value="role.role_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="form.remark"
            type="textarea"
            placeholder="请输入备注"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取 消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">
          确 定
        </el-button>
      </template>
    </el-dialog>

    <!-- 重置密码 弹窗 -->
    <el-dialog
      v-model="resetPwdVisible"
      title="重置密码"
      width="400px"
      destroy-on-close
    >
      <el-form label-width="80px">
        <el-form-item label="用户">
          <span>{{ resetPwdUser?.nick_name }} ({{ resetPwdUser?.user_name }})</span>
        </el-form-item>
        <el-form-item label="新密码" required>
          <el-input
            v-model="newPassword"
            type="password"
            placeholder="请输入新密码"
            show-password
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetPwdVisible = false">取 消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitResetPwd">
          确 定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus, Edit, Delete, Key } from '@element-plus/icons-vue'
import { getUserList, addUser, updateUser, deleteUser, resetUserPwd } from '@/api/user'
import { getRoleOptions } from '@/api/role'

// ========== 数据 ==========
const loading = ref(false)
const submitLoading = ref(false)
const tableData = ref([])
const total = ref(0)

const queryParams = reactive({
  page: 1,
  page_size: 10,
  user_name: '',
  phonenumber: '',
  status: '',
})

// 弹窗
const dialogVisible = ref(false)
const dialogTitle = ref('')
const isEdit = ref(false)
const formRef = ref(null)
const form = reactive({
  user_id: 0,
  user_name: '',
  password: '',
  nick_name: '',
  email: '',
  phonenumber: '',
  sex: '0',
  status: '0',
  remark: '',
  role_ids: [],
})

const formRules = {
  user_name: [
    { required: true, message: '请输入账号', trigger: 'blur' },
    { min: 2, max: 30, message: '长度在 2 到 30 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '长度在 6 到 20 个字符', trigger: 'blur' },
  ],
  nick_name: [
    { required: true, message: '请输入昵称', trigger: 'blur' },
  ],
  role_ids: [
    { type: 'array', required: true, message: '请选择角色', trigger: 'change' },
  ],
}

// 重置密码
const resetPwdVisible = ref(false)
const resetPwdUser = ref(null)
const newPassword = ref('')

// 角色选项
const roleOptions = ref([])

// ========== 方法 ==========
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
    const res = await getUserList(queryParams)
    tableData.value = res.rows || []
    total.value = res.total || 0
  } catch (e) {
    ElMessage.error('获取用户列表失败')
  } finally {
    loading.value = false
  }
}

async function loadRoleOptions() {
  try {
    roleOptions.value = await getRoleOptions()
  } catch (e) {
    console.error('获取角色列表失败:', e)
  }
}

function handleSearch() {
  queryParams.page = 1
  getList()
}

function handleReset() {
  queryParams.user_name = ''
  queryParams.phonenumber = ''
  queryParams.status = ''
  queryParams.page = 1
  getList()
}

function resetForm() {
  form.user_id = 0
  form.user_name = ''
  form.password = ''
  form.nick_name = ''
  form.email = ''
  form.phonenumber = ''
  form.sex = '0'
  form.status = '0'
  form.remark = ''
  form.role_ids = []
}

function handleAdd() {
  resetForm()
  isEdit.value = false
  dialogTitle.value = '新增用户'
  dialogVisible.value = true
}

function handleEdit(row) {
  resetForm()
  isEdit.value = true
  dialogTitle.value = '修改用户'
  form.user_id = row.user_id
  form.user_name = row.user_name
  form.nick_name = row.nick_name
  form.email = row.email
  form.phonenumber = row.phonenumber
  form.sex = row.sex
  form.status = row.status
  form.role_ids = [...row.role_ids]
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
    if (isEdit.value) {
      await updateUser(form)
      ElMessage.success('修改成功')
    } else {
      await addUser(form)
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
      `确认删除用户「${row.nick_name}」吗？`,
      '提示',
      { type: 'warning' }
    )
  } catch {
    return
  }

  try {
    await deleteUser(row.user_id)
    ElMessage.success('删除成功')
    getList()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

function handleResetPwd(row) {
  resetPwdUser.value = row
  newPassword.value = ''
  resetPwdVisible.value = true
}

async function submitResetPwd() {
  if (!newPassword.value || newPassword.value.length < 6) {
    ElMessage.warning('密码长度不能少于6位')
    return
  }

  submitLoading.value = true
  try {
    await resetUserPwd({
      user_id: resetPwdUser.value.user_id,
      new_password: newPassword.value,
    })
    ElMessage.success('密码重置成功')
    resetPwdVisible.value = false
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '重置失败')
  } finally {
    submitLoading.value = false
  }
}

// ========== 生命周期 ==========
onMounted(() => {
  getList()
  loadRoleOptions()
})
</script>

<style scoped>
.user-container {
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
