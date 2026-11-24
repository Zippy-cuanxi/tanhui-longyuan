<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import ConsolePageHeader from '@/console/components/ConsolePageHeader.vue'
import ConsoleFilterBar from '@/console/components/ConsoleFilterBar.vue'
import ConsoleDataTable from '@/console/components/ConsoleDataTable.vue'
import ConsoleStatusTag from '@/console/components/ConsoleStatusTag.vue'
import ConsoleExportButton from '@/console/components/ConsoleExportButton.vue'
import type { TableColumn } from '@/console/components/types'
import { adminApi, type AdminAccount, type AdminRole, type OperationLog } from '@/console/api'
import { ALL_ADMIN_PERMISSIONS, PERMISSION_LABELS } from '@/console/constants/permissions'
import { useConsoleAuth } from '@/console/stores/auth'
import { formatDateTime } from '@/console/utils/format'
import { toErrorState } from '@/console/utils/errors'

const auth = useConsoleAuth()
const route = useRoute()
const router = useRouter()
const canRbac = computed(() => auth.can('rbac:manage') || auth.can('*'))
const canAudit = computed(() => auth.can('audit:read') || auth.can('*'))
const canSettings = computed(() => auth.can('settings:manage') || auth.can('*'))

const allowedTabs = computed(() => {
  const tabs: Array<{ label: string; value: string }> = []
  if (canRbac.value) {
    tabs.push({ label: '管理员账号', value: 'admins' })
    tabs.push({ label: '角色权限', value: 'roles' })
  }
  if (canAudit.value) tabs.push({ label: '操作日志', value: 'logs' })
  if (canSettings.value) tabs.push({ label: '基础配置', value: 'base' })
  return tabs
})
const activeTab = ref(String(route.query.tab || ''))

watch(
  () => route.query.tab,
  (value) => {
    const next = String(value || '')
    if (allowedTabs.value.some((item) => item.value === next)) {
      activeTab.value = next
    } else {
      activeTab.value = allowedTabs.value[0]?.value || 'logs'
    }
  }
)

const admins = ref<AdminAccount[]>([])
const roles = ref<AdminRole[]>([])
const adminLoading = ref(false)
const adminError = ref('')
const adminRequestId = ref('')

const adminDialog = ref(false)
const adminFormRef = ref<FormInstance>()
const adminForm = reactive({
  username: '',
  name: '',
  roleCode: 'ops_admin' as AdminAccount['roleCode']
})
const adminSaving = ref(false)
const adminRules: FormRules = {
  username: [
    { required: true, message: '请输入登录账号', trigger: 'blur' },
    {
      pattern: /^[a-zA-Z0-9_]{3,24}$/,
      message: '账号为 3–24 位字母、数字或下划线',
      trigger: 'blur'
    }
  ],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  roleCode: [{ required: true, message: '请选择角色', trigger: 'change' }]
}

const roleDialog = ref(false)
const roleForm = ref<AdminRole | null>(null)
const rolePermissions = ref<string[]>([])
const roleSaving = ref(false)

const logs = ref<OperationLog[]>([])
const logTotal = ref(0)
const logPage = ref(1)
const logPageSize = ref(20)
const logLoading = ref(false)
const logError = ref('')
const logRequestId = ref('')
const logQuery = reactive({ keyword: '', module: 'all', risk: 'all' })
const logRange = ref<[string, string] | null>(null)

const baseForm = reactive({
  platformName: '',
  servicePhone: '',
  serviceEmail: '',
  address: '',
  icp: '',
  notice: ''
})
const baseLoading = ref(false)
const baseSaving = ref(false)
const baseError = ref('')

const adminColumns: TableColumn[] = [
  { label: '管理员', slot: 'admin', minWidth: 200 },
  { label: '角色', slot: 'role', width: 140 },
  { label: '状态', slot: 'status', width: 100 },
  { label: '最近登录', slot: 'lastLogin', width: 150 },
  { label: '创建时间', slot: 'created', width: 150 },
  { label: '操作', slot: 'actions', width: 190, fixed: 'right' }
]
const logColumns: TableColumn[] = [
  { label: '时间', slot: 'time', width: 148 },
  { label: '操作人', slot: 'actor', minWidth: 110 },
  { label: '操作', slot: 'action', minWidth: 135 },
  { label: '模块', prop: 'module', width: 60 },
  { label: '对象', prop: 'target', minWidth: 105, showOverflowTooltip: true },
  { label: '详情', prop: 'detail', minWidth: 150, showOverflowTooltip: true },
  { label: 'IP', prop: 'ip', width: 85 },
  { label: '风险', slot: 'risk', width: 88 }
]
const logModules = ['系统', '商家', '商品', '售后', '财务', '订单', '会员', '内容', '助农']

function switchTab(value: string | number): void {
  const tab = String(value)
  activeTab.value = tab
  router.replace({ query: { ...route.query, tab } })
}

async function loadAdmins(): Promise<void> {
  adminLoading.value = true
  adminError.value = ''
  adminRequestId.value = ''
  try {
    const [adminResult, roleResult] = await Promise.all([adminApi.admins(), adminApi.roles()])
    admins.value = adminResult
    roles.value = roleResult
  } catch (err) {
    const state = toErrorState(err)
    adminError.value = state.message
    adminRequestId.value = state.requestId
  } finally {
    adminLoading.value = false
  }
}

function openCreateAdmin(): void {
  adminForm.username = ''
  adminForm.name = ''
  adminForm.roleCode = 'ops_admin'
  adminDialog.value = true
}

async function createAdmin(): Promise<void> {
  const valid = await adminFormRef.value?.validate().catch(() => false)
  if (!valid) return
  adminSaving.value = true
  try {
    await adminApi.createAdmin({ ...adminForm })
    ElMessage.success('管理员账号已创建，初始密码 Demo@123456')
    adminDialog.value = false
    await loadAdmins()
  } catch (err) {
    ElMessage.error(toErrorState(err, '创建失败').message)
  } finally {
    adminSaving.value = false
  }
}

async function toggleAdmin(row: AdminAccount): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确认${row.status === 'active' ? '禁用' : '启用'}管理员「${row.name}」？`,
      '账号状态变更',
      { type: 'warning' }
    )
  } catch {
    return
  }
  try {
    await adminApi.toggleAdmin(row.id)
    ElMessage.success('账号状态已更新，已记录日志')
    await loadAdmins()
  } catch (err) {
    ElMessage.error(toErrorState(err, '操作失败').message)
  }
}

async function resetPassword(row: AdminAccount): Promise<void> {
  try {
    await ElMessageBox.confirm(`确认重置「${row.name}」的密码为 Demo@123456？`, '重置密码', {
      type: 'warning',
      confirmButtonText: '重置'
    })
  } catch {
    return
  }
  try {
    await adminApi.resetAdminPassword(row.id)
    ElMessage.success('密码已重置为 Demo@123456（演示）')
  } catch (err) {
    ElMessage.error(toErrorState(err, '操作失败').message)
  }
}

function openRole(role: AdminRole): void {
  roleForm.value = role
  rolePermissions.value = [...role.permissions]
  roleDialog.value = true
}

async function saveRole(): Promise<void> {
  if (!roleForm.value) return
  if (roleForm.value.code === 'super_admin') {
    ElMessage.warning('超级管理员权限不可修改')
    return
  }
  roleSaving.value = true
  try {
    const updated = await adminApi.updateRolePermissions(roleForm.value.code, rolePermissions.value)
    roleDialog.value = false
    ElMessage.success(`角色「${updated.name}」权限已更新，已记录高风险日志`)
    await loadAdmins()
  } catch (err) {
    ElMessage.error(toErrorState(err, '保存失败').message)
  } finally {
    roleSaving.value = false
  }
}

async function loadLogs(): Promise<void> {
  logLoading.value = true
  logError.value = ''
  logRequestId.value = ''
  try {
    const result = await adminApi.logs({
      page: logPage.value,
      page_size: logPageSize.value,
      keyword: logQuery.keyword,
      module: logQuery.module,
      risk: logQuery.risk,
      date_from: logRange.value?.[0],
      date_to: logRange.value?.[1]
    })
    logs.value = result.items
    logTotal.value = result.pagination.total
  } catch (err) {
    const state = toErrorState(err)
    logError.value = state.message
    logRequestId.value = state.requestId
  } finally {
    logLoading.value = false
  }
}

function searchLogs(): void {
  logPage.value = 1
  loadLogs()
}

function resetLogs(): void {
  logQuery.keyword = ''
  logQuery.module = 'all'
  logQuery.risk = 'all'
  logRange.value = null
  logPage.value = 1
  loadLogs()
}

async function loadBase(): Promise<void> {
  baseLoading.value = true
  baseError.value = ''
  try {
    const settings = await adminApi.settings()
    baseForm.platformName = settings.platformName || ''
    baseForm.servicePhone = settings.servicePhone || ''
    baseForm.serviceEmail = settings.serviceEmail || ''
    baseForm.address = settings.address || ''
    baseForm.icp = settings.icp || ''
    baseForm.notice = settings.notice || ''
  } catch (err) {
    baseError.value = toErrorState(err, '加载失败').message
  } finally {
    baseLoading.value = false
  }
}

async function saveBase(): Promise<void> {
  baseSaving.value = true
  try {
    await adminApi.saveSettings({ ...baseForm })
    ElMessage.success('基础配置已保存，已记录高风险日志')
  } catch (err) {
    ElMessage.error(toErrorState(err, '保存失败').message)
  } finally {
    baseSaving.value = false
  }
}

const logExportRows = computed(() =>
  logs.value.map((item) => ({
    createdAt: formatDateTime(item.createdAt),
    actor: `${item.actorName}（${item.actor}）`,
    action: item.action,
    module: item.module,
    target: item.target,
    detail: item.detail,
    ip: item.ip,
    risk: item.risk === 'high' ? '高风险' : '常规'
  }))
)

onMounted(async () => {
  if (!allowedTabs.value.some((item) => item.value === activeTab.value)) {
    activeTab.value = allowedTabs.value[0]?.value || 'logs'
  }
  if (String(route.query.tab || '') !== activeTab.value && activeTab.value) {
    await router.replace({ query: { ...route.query, tab: activeTab.value } })
  }
  if (canRbac.value) await loadAdmins()
  if (canAudit.value) await loadLogs()
  if (canSettings.value) await loadBase()
})
</script>

<template>
  <div>
    <ConsolePageHeader
      title="系统设置"
      description="管理员账号、角色权限、操作日志与平台基础配置；敏感操作均写入高风险日志。"
    >
      <template #actions>
        <el-tag type="info" effect="plain">当前角色：{{ auth.adminRoleName || '—' }}</el-tag>
      </template>
    </ConsolePageHeader>

    <el-tabs :model-value="activeTab" @tab-change="switchTab">
      <el-tab-pane
        v-for="tab in allowedTabs"
        :key="tab.value"
        :label="tab.label"
        :name="tab.value"
      />
    </el-tabs>

    <template v-if="activeTab === 'admins'">
      <div class="console-card">
        <div class="console-card-title">
          <span>管理员账号</span>
          <el-button type="primary" size="small" @click="openCreateAdmin">
            <el-icon><Plus /></el-icon>新增管理员
          </el-button>
        </div>
        <ConsoleDataTable
          :columns="adminColumns"
          :rows="admins"
          :loading="adminLoading"
          :error="adminError"
          :error-request-id="adminRequestId"
          :total="admins.length"
          :page="1"
          :page-size="20"
          empty-text="暂无管理员"
          @retry="loadAdmins"
        >
          <template #admin="{ row }">
            <div class="console-two-line">
              <strong>{{ row.name }}</strong>
              <span>{{ row.username }} · {{ row.id }}</span>
            </div>
          </template>
          <template #role="{ row }">{{ row.roleName }}</template>
          <template #status="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? '启用' : '已禁用' }}
            </el-tag>
          </template>
          <template #lastLogin="{ row }">{{ formatDateTime(row.lastLoginAt) }}</template>
          <template #created="{ row }">{{ formatDateTime(row.createdAt) }}</template>
          <template #actions="{ row }">
            <div class="console-inline-actions">
              <el-button link type="primary" size="small" @click="toggleAdmin(row)">
                {{ row.status === 'active' ? '禁用' : '启用' }}
              </el-button>
              <el-button link type="warning" size="small" @click="resetPassword(row)">
                重置密码
              </el-button>
            </div>
          </template>
        </ConsoleDataTable>
      </div>
    </template>

    <template v-else-if="activeTab === 'roles'">
      <div class="console-role-grid">
        <article v-for="role in roles" :key="role.code" class="console-role-card">
          <div class="console-role-head">
            <h3>{{ role.name }}</h3>
            <span v-if="role.code === 'super_admin'" class="console-tag-soft">内置 · 全部权限</span>
            <span v-else class="console-tag-soft">{{ role.permissions.length }} 项权限</span>
          </div>
          <p>{{ role.description }}</p>
          <div class="console-role-perms">
            <span v-for="code in role.permissions.slice(0, 6)" :key="code" class="console-code">
              {{ code }}
            </span>
            <span v-if="role.permissions.length > 6" class="console-muted">
              +{{ role.permissions.length - 6 }}
            </span>
          </div>
          <el-button
            plain
            size="small"
            :disabled="role.code === 'super_admin'"
            @click="openRole(role)"
          >
            编辑权限
          </el-button>
        </article>
      </div>
      <div class="console-audit-tip" style="margin-top: 14px">
        角色权限修改只影响后续登录 / 刷新后的会话；修改角色权限会写入高风险操作日志。
      </div>
    </template>

    <template v-else-if="activeTab === 'logs'">
      <div class="console-card">
        <ConsoleFilterBar :loading="logLoading" @search="searchLogs" @reset="resetLogs">
          <el-form-item label="关键词">
            <el-input
              v-model="logQuery.keyword"
              clearable
              placeholder="操作人 / 动作 / 对象"
              style="width: 210px"
              @keyup.enter="searchLogs"
            />
          </el-form-item>
          <el-form-item label="模块">
            <el-select v-model="logQuery.module" style="width: 120px">
              <el-option label="全部模块" value="all" />
              <el-option v-for="item in logModules" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="风险">
            <el-select v-model="logQuery.risk" style="width: 110px">
              <el-option label="全部" value="all" />
              <el-option label="高风险" value="high" />
              <el-option label="常规" value="normal" />
            </el-select>
          </el-form-item>
          <el-form-item label="日期">
            <el-date-picker
              v-model="logRange"
              type="daterange"
              value-format="YYYY-MM-DD"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              style="width: 240px"
            />
          </el-form-item>
        </ConsoleFilterBar>
        <div style="display: flex; justify-content: flex-end; margin-bottom: 10px">
          <ConsoleExportButton
            filename="操作日志.csv"
            :rows="logExportRows"
            :headers="[
              { key: 'createdAt', label: '时间' },
              { key: 'actor', label: '操作人' },
              { key: 'action', label: '操作' },
              { key: 'module', label: '模块' },
              { key: 'target', label: '对象' },
              { key: 'detail', label: '详情' },
              { key: 'ip', label: 'IP' },
              { key: 'risk', label: '风险' }
            ]"
          />
        </div>
        <ConsoleDataTable
          :columns="logColumns"
          :rows="logs"
          :loading="logLoading"
          :error="logError"
          :error-request-id="logRequestId"
          :total="logTotal"
          :page="logPage"
          :page-size="logPageSize"
          empty-text="暂无操作日志"
          @update:page="
            (value: number) => {
              logPage = value
              loadLogs()
            }
          "
          @update:page-size="
            (value: number) => {
              logPageSize = value
              logPage = 1
              loadLogs()
            }
          "
          @retry="loadLogs"
        >
          <template #time="{ row }">{{ formatDateTime(row.createdAt) }}</template>
          <template #actor="{ row }">
            <div class="console-two-line">
              <strong>{{ row.actorName }}</strong>
              <span>{{ row.actor }}</span>
            </div>
          </template>
          <template #action="{ row }">
            <span class="console-code" :title="row.action">{{ row.action }}</span>
          </template>
          <template #risk="{ row }">
            <ConsoleStatusTag kind="risk" :value="row.risk" />
          </template>
        </ConsoleDataTable>
      </div>
    </template>

    <template v-else-if="activeTab === 'base'">
      <div class="console-card">
        <div class="console-card-title">
          <span>平台基础配置</span>
          <span class="console-muted">演示环境，保存仅影响本地 mock</span>
        </div>
        <div v-if="baseError" class="console-login-error">{{ baseError }}</div>
        <div v-loading="baseLoading" style="max-width: 760px">
          <el-form label-position="top" @submit.prevent="saveBase">
            <div class="console-form-grid">
              <el-form-item label="平台名称">
                <el-input v-model="baseForm.platformName" maxlength="30" />
              </el-form-item>
              <el-form-item label="客服电话">
                <el-input v-model="baseForm.servicePhone" maxlength="30" />
              </el-form-item>
              <el-form-item label="客服邮箱">
                <el-input v-model="baseForm.serviceEmail" maxlength="60" />
              </el-form-item>
              <el-form-item label="平台地址">
                <el-input v-model="baseForm.address" maxlength="60" />
              </el-form-item>
              <el-form-item label="ICP 备案号">
                <el-input v-model="baseForm.icp" maxlength="40" />
              </el-form-item>
              <el-form-item label="演示提示">
                <el-input v-model="baseForm.notice" maxlength="120" />
              </el-form-item>
            </div>
            <el-alert
              type="warning"
              :closable="false"
              show-icon
              title="基础配置变更属于高风险操作，会写入平台操作日志。"
              style="margin-bottom: 14px"
            />
            <el-button type="primary" :loading="baseSaving" @click="saveBase">
              保存基础配置
            </el-button>
          </el-form>
        </div>
      </div>
    </template>

    <div v-if="!allowedTabs.length" class="console-card">
      <p class="console-muted">当前账号没有系统设置相关权限。</p>
    </div>

    <el-dialog v-model="adminDialog" title="新增管理员" width="480px">
      <el-form ref="adminFormRef" :model="adminForm" :rules="adminRules" label-position="top">
        <el-form-item label="登录账号" prop="username">
          <el-input v-model="adminForm.username" maxlength="24" placeholder="字母、数字或下划线" />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="adminForm.name" maxlength="20" />
        </el-form-item>
        <el-form-item label="角色" prop="roleCode">
          <el-select v-model="adminForm.roleCode" style="width: 100%">
            <el-option
              v-for="role in roles"
              :key="role.code"
              :label="role.name"
              :value="role.code"
            />
          </el-select>
        </el-form-item>
        <p class="console-muted" style="font-size: 11px; margin: 0">
          初始密码统一为 Demo@123456；创建账号属于高风险操作，会写入日志。
        </p>
      </el-form>
      <template #footer>
        <el-button @click="adminDialog = false">取消</el-button>
        <el-button type="primary" :loading="adminSaving" @click="createAdmin">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="roleDialog" :title="`编辑角色权限 · ${roleForm?.name || ''}`" width="680px">
      <el-checkbox-group v-model="rolePermissions" class="console-permission-grid">
        <el-checkbox v-for="code in ALL_ADMIN_PERMISSIONS" :key="code" :value="code">
          <span>{{ PERMISSION_LABELS[code] || code }}</span>
          <span class="console-code" style="margin-left: 4px">{{ code }}</span>
        </el-checkbox>
      </el-checkbox-group>
      <p class="console-muted" style="font-size: 11px; margin-top: 10px">
        取消权限后，该角色管理员刷新页面即生效；前端路由与按钮均按权限控制。
      </p>
      <template #footer>
        <el-button @click="roleDialog = false">取消</el-button>
        <el-button type="primary" :loading="roleSaving" @click="saveRole">保存权限</el-button>
      </template>
    </el-dialog>
  </div>
</template>
