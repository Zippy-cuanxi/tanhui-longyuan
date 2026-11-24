<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import ConsolePageHeader from '@/console/components/ConsolePageHeader.vue'
import ConsoleStatusTag from '@/console/components/ConsoleStatusTag.vue'
import ConsoleErrorState from '@/console/components/ConsoleErrorState.vue'
import { merchantApi, type Qualification, type ShippingTemplate, type Store } from '@/console/api'
import { useConsoleAuth } from '@/console/stores/auth'
import { formatMoney } from '@/console/utils/format'
import { toErrorState } from '@/console/utils/errors'

const auth = useConsoleAuth()
const route = useRoute()
const router = useRouter()
const merchantId = computed(() => auth.merchantAccount?.id || '')
const activeTab = ref(String(route.query.tab || 'profile'))

watch(
  () => route.query.tab,
  (value) => {
    const next = String(value || 'profile')
    activeTab.value = ['profile', 'shipping', 'qualifications'].includes(next) ? next : 'profile'
  }
)

const shop = ref<Store | null>(null)
const loading = ref(true)
const error = ref('')
const requestId = ref('')
const saving = ref(false)

const profileForm = reactive({ name: '', logo: '', region: '', description: '' })
const profileRef = ref<FormInstance>()
const profileRules: FormRules = {
  name: [
    { required: true, message: '请输入店铺名称', trigger: 'blur' },
    { min: 2, max: 30, message: '店铺名称为 2–30 个字符', trigger: 'blur' }
  ],
  region: [{ required: true, message: '请输入所在地区', trigger: 'blur' }],
  description: [
    { required: true, message: '请输入店铺简介', trigger: 'blur' },
    { min: 10, max: 200, message: '简介为 10–200 个字符', trigger: 'blur' }
  ]
}
const profileSnapshot = ref('')

const logoOptions = [
  '/console-assets/images/shop-logo-1.png',
  '/console-assets/images/shop-logo-2.png',
  '/console-assets/images/shop-logo-3.png'
]

const templates = ref<ShippingTemplate[]>([])
const templateSnapshot = ref('')
const templateDialog = ref(false)
const templateIndex = ref(-1)
const templateForm = reactive({
  name: '',
  freeThreshold: '',
  baseFee: '',
  regions: '',
  enabled: true
})
const templateFormRef = ref<FormInstance>()
const templateRules: FormRules = {
  name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  freeThreshold: [
    { required: true, message: '请输入包邮门槛', trigger: 'blur' },
    { pattern: /^\d+(\.\d{1,2})?$/, message: '请输入正确金额', trigger: 'blur' }
  ],
  baseFee: [
    { required: true, message: '请输入基础运费', trigger: 'blur' },
    { pattern: /^\d+(\.\d{1,2})?$/, message: '请输入正确金额', trigger: 'blur' }
  ],
  regions: [{ required: true, message: '请输入配送区域', trigger: 'blur' }]
}

const profileSignature = computed(() => JSON.stringify(profileForm))
const profileDirty = computed(
  () => Boolean(profileSnapshot.value) && profileSignature.value !== profileSnapshot.value
)
const templateSignature = computed(() => JSON.stringify(templates.value))
const templateDirty = computed(
  () => Boolean(templateSnapshot.value) && templateSignature.value !== templateSnapshot.value
)

const qualificationMeta: Record<
  Qualification['status'],
  { label: string; color: string; bg: string }
> = {
  approved: { label: '审核通过', color: '#2E9E5B', bg: '#E8F6ED' },
  pending: { label: '审核中', color: '#E8892B', bg: '#FFF3E4' },
  rejected: { label: '已驳回', color: '#D64545', bg: '#FDECEC' }
}

function fillProfile(source: Store): void {
  profileForm.name = source.name
  profileForm.logo = source.logo
  profileForm.region = source.region
  profileForm.description = source.description
  profileSnapshot.value = profileSignature.value
  templates.value = source.shippingTemplates.map((item) => ({ ...item }))
  templateSnapshot.value = templateSignature.value
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  requestId.value = ''
  try {
    shop.value = await merchantApi.shop(merchantId.value)
    fillProfile(shop.value)
  } catch (err) {
    const state = toErrorState(err)
    error.value = state.message
    requestId.value = state.requestId
  } finally {
    loading.value = false
  }
}

function switchTab(value: string | number): void {
  const tab = String(value)
  activeTab.value = tab
  router.replace({ query: { ...route.query, tab } })
}

async function saveProfile(): Promise<void> {
  const valid = await profileRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    shop.value = await merchantApi.saveShop(merchantId.value, { ...profileForm })
    profileSnapshot.value = profileSignature.value
    ElMessage.success('店铺资料已保存')
  } catch (err) {
    ElMessage.error(toErrorState(err, '保存失败').message)
  } finally {
    saving.value = false
  }
}

function openTemplate(index: number): void {
  templateIndex.value = index
  if (index >= 0) {
    Object.assign(templateForm, templates.value[index])
  } else {
    templateForm.name = ''
    templateForm.freeThreshold = '99.00'
    templateForm.baseFee = '8.00'
    templateForm.regions = '全国（除港澳台）'
    templateForm.enabled = true
  }
  templateDialog.value = true
}

async function submitTemplate(): Promise<void> {
  const valid = await templateFormRef.value?.validate().catch(() => false)
  if (!valid) return
  const data: ShippingTemplate = {
    id: templateIndex.value >= 0 ? templates.value[templateIndex.value].id : `ship-${Date.now()}`,
    name: templateForm.name.trim(),
    freeThreshold: Number(templateForm.freeThreshold).toFixed(2),
    baseFee: Number(templateForm.baseFee).toFixed(2),
    regions: templateForm.regions.trim(),
    enabled: templateForm.enabled
  }
  if (templateIndex.value >= 0) templates.value.splice(templateIndex.value, 1, data)
  else templates.value.push(data)
  templateDialog.value = false
}

function removeTemplate(index: number): void {
  if (templates.value.length <= 1) {
    ElMessage.warning('至少保留一个运费模板')
    return
  }
  templates.value.splice(index, 1)
}

async function saveTemplates(): Promise<void> {
  saving.value = true
  try {
    shop.value = await merchantApi.saveShippingTemplates(merchantId.value, templates.value)
    templates.value = shop.value.shippingTemplates.map((item) => ({ ...item }))
    templateSnapshot.value = templateSignature.value
    ElMessage.success('运费模板已保存')
  } catch (err) {
    ElMessage.error(toErrorState(err, '保存失败').message)
  } finally {
    saving.value = false
  }
}

function showQualification(qualification: Qualification): void {
  ElMessage.info(
    `${qualification.name}：${
      qualificationMeta[qualification.status].label
    }${qualification.reason ? `，${qualification.reason}` : ''}（演示环境不可上传）`
  )
}

onBeforeRouteLeave(async () => {
  if (!profileDirty.value && !templateDirty.value) return true
  try {
    await ElMessageBox.confirm('店铺资料或运费模板有未保存修改，确认离开？', '离开页面', {
      type: 'warning',
      confirmButtonText: '放弃修改'
    })
    return true
  } catch {
    return false
  }
})

onMounted(load)
</script>

<template>
  <div>
    <ConsolePageHeader
      title="店铺管理"
      description="维护店铺资料、运费模板与资质认证；资质文件仅展示审核状态。"
    >
      <template #actions>
        <el-button @click="router.push('/console/merchant/analytics')">查看经营数据</el-button>
      </template>
    </ConsolePageHeader>

    <ConsoleErrorState v-if="error" :message="error" :request-id="requestId" @retry="load" />
    <div v-else-if="loading" class="console-card">
      <el-skeleton :rows="10" animated />
    </div>
    <div v-else-if="shop" class="console-card">
      <div class="console-shop-head">
        <img :src="shop.logo" :alt="shop.name" class="console-shop-logo" />
        <div>
          <h2>{{ shop.name }}</h2>
          <p>
            <ConsoleStatusTag kind="store" :value="shop.status" />
            <span class="console-muted" style="margin-left: 8px">评分 {{ shop.rating }}</span>
            <span class="console-muted" style="margin-left: 8px">{{ shop.region }}</span>
          </p>
        </div>
      </div>

      <el-tabs :model-value="activeTab" @tab-change="switchTab">
        <el-tab-pane label="店铺信息" name="profile" />
        <el-tab-pane label="运费模板" name="shipping" />
        <el-tab-pane label="资质认证" name="qualifications" />
      </el-tabs>

      <div v-if="activeTab === 'profile'" style="max-width: 860px">
        <el-form
          ref="profileRef"
          :model="profileForm"
          :rules="profileRules"
          label-position="top"
          @submit.prevent="saveProfile"
        >
          <div class="console-form-grid">
            <el-form-item label="店铺名称" prop="name">
              <el-input v-model="profileForm.name" maxlength="30" show-word-limit />
            </el-form-item>
            <el-form-item label="所在地区" prop="region">
              <el-input v-model="profileForm.region" maxlength="40" />
            </el-form-item>
            <el-form-item label="店铺 Logo" class="span-2">
              <div class="console-logo-picker">
                <button
                  v-for="logo in logoOptions"
                  :key="logo"
                  type="button"
                  :class="{ selected: profileForm.logo === logo }"
                  @click="profileForm.logo = logo"
                >
                  <img :src="logo" alt="店铺 Logo" />
                </button>
              </div>
              <p class="console-muted" style="font-size: 11px; margin: 6px 0 0">
                演示环境从本地素材库选择 Logo，不调用真实上传。
              </p>
            </el-form-item>
            <el-form-item label="店铺简介" prop="description" class="span-2">
              <el-input
                v-model="profileForm.description"
                type="textarea"
                :rows="4"
                maxlength="200"
                show-word-limit
              />
            </el-form-item>
          </div>
          <div class="console-inline-actions">
            <el-button type="primary" :loading="saving" @click="saveProfile"
              >保存店铺资料</el-button
            >
            <span v-if="profileDirty" class="console-muted">有未保存修改</span>
          </div>
        </el-form>
      </div>

      <div v-else-if="activeTab === 'shipping'">
        <div
          class="console-inline-actions"
          style="justify-content: space-between; margin-bottom: 12px"
        >
          <span class="console-muted"
            >共 {{ templates.length }} 个运费模板；商品发布时选择其一。</span
          >
          <div class="console-inline-actions">
            <el-button plain @click="openTemplate(-1)">
              <el-icon><Plus /></el-icon>新增模板
            </el-button>
            <el-button type="primary" :loading="saving" @click="saveTemplates">
              保存运费模板
            </el-button>
          </div>
        </div>
        <el-table :data="templates">
          <el-table-column prop="name" label="模板名称" min-width="160" />
          <el-table-column label="包邮门槛" width="130">
            <template #default="{ row }">满 ¥{{ formatMoney(row.freeThreshold) }}</template>
          </el-table-column>
          <el-table-column label="基础运费" width="120">
            <template #default="{ row }">¥{{ formatMoney(row.baseFee) }}</template>
          </el-table-column>
          <el-table-column prop="regions" label="配送区域" min-width="190" show-overflow-tooltip />
          <el-table-column label="启用" width="90">
            <template #default="{ row }">
              <el-switch v-model="row.enabled" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ $index }">
              <el-button link type="primary" size="small" @click="openTemplate($index)">
                编辑
              </el-button>
              <el-button link type="danger" size="small" @click="removeTemplate($index)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="templateDirty" class="console-audit-tip">
          运费模板有未保存修改，保存后对后续商品生效。
        </div>
      </div>

      <div v-else>
        <div class="console-qualification-grid">
          <article
            v-for="item in shop.qualifications"
            :key="item.id"
            class="console-qualification-card"
          >
            <img :src="item.image" :alt="item.name" />
            <div>
              <h4>{{ item.name }}</h4>
              <span
                class="console-status"
                :style="{
                  color: qualificationMeta[item.status].color,
                  background: qualificationMeta[item.status].bg
                }"
              >
                <i />{{ qualificationMeta[item.status].label }}
              </span>
              <p v-if="item.reason" class="console-amount" style="font-size: 11px">
                {{ item.reason }}
              </p>
              <el-button link type="primary" size="small" @click="showQualification(item)">
                查看说明
              </el-button>
            </div>
          </article>
        </div>
        <p class="console-muted" style="font-size: 11px; margin-top: 12px">
          资质文件由平台审核；当前为演示环境，不提供真实上传与替换入口。
        </p>
      </div>
    </div>

    <el-dialog
      v-model="templateDialog"
      :title="templateIndex >= 0 ? '编辑运费模板' : '新增运费模板'"
      width="520px"
    >
      <el-form
        ref="templateFormRef"
        :model="templateForm"
        :rules="templateRules"
        label-position="top"
      >
        <el-form-item label="模板名称" prop="name">
          <el-input v-model="templateForm.name" maxlength="30" placeholder="例如：全国满 99 包邮" />
        </el-form-item>
        <div class="console-form-grid">
          <el-form-item label="包邮门槛（元）" prop="freeThreshold">
            <el-input v-model="templateForm.freeThreshold" inputmode="decimal" />
          </el-form-item>
          <el-form-item label="基础运费（元）" prop="baseFee">
            <el-input v-model="templateForm.baseFee" inputmode="decimal" />
          </el-form-item>
        </div>
        <el-form-item label="配送区域" prop="regions">
          <el-input v-model="templateForm.regions" maxlength="80" />
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="templateForm.enabled" active-text="启用" inactive-text="停用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="templateDialog = false">取消</el-button>
        <el-button type="primary" @click="submitTemplate">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>
