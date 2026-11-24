<script setup lang="ts">
import { assetUrl } from '@/api/http'
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import ConsolePageHeader from '@/console/components/ConsolePageHeader.vue'
import ConsoleErrorState from '@/console/components/ConsoleErrorState.vue'
import ConsoleStatusTag from '@/console/components/ConsoleStatusTag.vue'
import {
  merchantApi,
  type Category,
  type Product,
  type ProductDraftInput,
  type ShippingTemplate,
  type Store
} from '@/console/api'
import { useConsoleAuth } from '@/console/stores/auth'
import { formatMoney } from '@/console/utils/format'
import { toErrorState } from '@/console/utils/errors'

const auth = useConsoleAuth()
const route = useRoute()
const router = useRouter()

const merchantId = computed(() => auth.merchantAccount?.id || '')
const productId = computed(() => String(route.params.id || ''))
const isEdit = computed(() => Boolean(productId.value))

interface SkuForm {
  id?: string
  spec: string
  price: string
  stock: number
  code?: string
}

interface FormState {
  title: string
  subtitle: string
  categoryId: string
  description: string
  images: string[]
  skus: SkuForm[]
  shippingTemplateId: string
  greenOrigin: string
  greenMode: string
  greenDescription: string
  aidProjectId: string
}

const form = reactive<FormState>({
  title: '',
  subtitle: '',
  categoryId: '',
  description: '',
  images: [],
  skus: [{ spec: '', price: '', stock: 0 }],
  shippingTemplateId: '',
  greenOrigin: '',
  greenMode: '',
  greenDescription: '',
  aidProjectId: ''
})

const formRef = ref<FormInstance>()
const loading = ref(true)
const error = ref('')
const requestId = ref('')
const submitting = ref(false)
const saved = ref(false)
const categories = ref<Category[]>([])
const aidProjects = ref<Array<{ id: string; title: string }>>([])
const shop = ref<Store | null>(null)
const product = ref<Product | null>(null)
const originalSignature = ref('')
const originalFullSignature = ref('')
const originalSkuSignature = ref('')
const imageDialog = ref(false)

const imageOptions = [
  assetUrl('/console-assets/images/apple.webp'),
  assetUrl('/console-assets/images/potato.webp'),
  assetUrl('/console-assets/images/melon.webp'),
  assetUrl('/console-assets/images/goji.webp'),
  assetUrl('/console-assets/images/jujube.webp'),
  assetUrl('/console-assets/images/lily.webp'),
  assetUrl('/console-assets/images/danggui.webp')
]

const rules: FormRules = {
  title: [
    { required: true, message: '请输入商品标题', trigger: 'blur' },
    { min: 2, max: 60, message: '标题长度为 2–60 个字符', trigger: 'blur' }
  ],
  categoryId: [{ required: true, message: '请选择商品分类', trigger: 'change' }],
  description: [
    { required: true, message: '请输入商品详情描述', trigger: 'blur' },
    { min: 10, message: '商品描述至少 10 个字', trigger: 'blur' }
  ],
  greenOrigin: [{ required: true, message: '请输入产地', trigger: 'blur' }],
  greenMode: [{ required: true, message: '请输入种植/养殖方式', trigger: 'blur' }]
}

const templates = computed<ShippingTemplate[]>(
  () => shop.value?.shippingTemplates.filter((item) => item.enabled) || []
)
const currentTemplate = computed(() =>
  shop.value?.shippingTemplates.find((item) => item.id === form.shippingTemplateId)
)
const approved = computed(() => product.value?.status === 'approved')

function sensitiveSignature(): string {
  return JSON.stringify({
    title: form.title,
    subtitle: form.subtitle,
    categoryId: form.categoryId,
    description: form.description,
    images: form.images,
    shippingTemplateId: form.shippingTemplateId,
    greenOrigin: form.greenOrigin,
    greenMode: form.greenMode,
    greenDescription: form.greenDescription,
    aidProjectId: form.aidProjectId,
    skus: form.skus.map((item) => ({ id: item.id || '', spec: item.spec }))
  })
}

function skuSignature(): string {
  return JSON.stringify(
    form.skus.map((item) => ({
      id: item.id || item.spec,
      price: item.price,
      stock: item.stock
    }))
  )
}

function fullSignature(): string {
  return JSON.stringify({
    sensitive: JSON.parse(sensitiveSignature()),
    skus: form.skus.map((item) => ({
      spec: item.spec,
      price: item.price,
      stock: item.stock,
      code: item.code
    }))
  })
}

const dirty = computed(() => fullSignature() !== originalFullSignature.value)
const priceStockOnly = computed(
  () =>
    isEdit.value &&
    approved.value &&
    sensitiveSignature() === originalSignature.value &&
    skuSignature() !== originalSkuSignature.value
)
const minPrice = computed(() => {
  const prices = form.skus
    .map((item) => Number(item.price))
    .filter((value) => Number.isFinite(value) && value > 0)
  return prices.length ? Math.min(...prices) : 0
})

const pageTitle = computed(() => (isEdit.value ? '编辑商品' : '发布商品'))
const pageDescription = computed(() =>
  approved.value
    ? '已上架商品：仅调整价格 / 库存无需审核；修改标题、图片、描述、分类等将重新进入审核。'
    : '商品提交后进入平台审核，审核通过后可手动上架；价格与库存调整无需审核。'
)

function fillForm(source: Product): void {
  form.title = source.title
  form.subtitle = source.subtitle
  form.categoryId = source.categoryId
  form.description = source.description
  form.images = [...source.images]
  form.skus = source.skus.map((item) => ({
    id: item.id,
    spec: item.spec,
    price: item.price,
    stock: item.stock,
    code: item.code
  }))
  form.shippingTemplateId = source.shippingTemplateId
  form.greenOrigin = source.greenProfile.origin
  form.greenMode = source.greenProfile.plantingMode
  form.greenDescription = source.greenProfile.description
  form.aidProjectId = source.aidProjectId || ''
  originalSignature.value = sensitiveSignature()
  originalSkuSignature.value = skuSignature()
  originalFullSignature.value = fullSignature()
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  requestId.value = ''
  try {
    const [categoryResult, aidResult, shopResult] = await Promise.all([
      merchantApi.categories(),
      merchantApi.aidProjects(),
      merchantApi.shop(merchantId.value)
    ])
    categories.value = categoryResult
    aidProjects.value = aidResult
    shop.value = shopResult
    if (isEdit.value) {
      product.value = await merchantApi.product(merchantId.value, productId.value)
      fillForm(product.value)
    } else {
      form.shippingTemplateId = shopResult.shippingTemplates.find((item) => item.enabled)?.id || ''
      originalSignature.value = sensitiveSignature()
      originalSkuSignature.value = skuSignature()
      originalFullSignature.value = fullSignature()
    }
  } catch (err) {
    const state = toErrorState(err)
    error.value = state.message
    requestId.value = state.requestId
  } finally {
    loading.value = false
  }
}

function addSku(): void {
  form.skus.push({ spec: '', price: '', stock: 0 })
}

function removeSku(index: number): void {
  if (form.skus.length <= 1) {
    ElMessage.warning('至少保留一个规格')
    return
  }
  form.skus.splice(index, 1)
}

function toggleImage(src: string): void {
  const index = form.images.indexOf(src)
  if (index >= 0) {
    form.images.splice(index, 1)
    return
  }
  if (form.images.length >= 5) {
    ElMessage.warning('最多选择 5 张商品图片')
    return
  }
  form.images.push(src)
}

function validateSku(requireComplete: boolean): boolean {
  if (!form.skus.length) {
    ElMessage.warning('请至少添加一个商品规格')
    return false
  }
  for (let index = 0; index < form.skus.length; index += 1) {
    const sku = form.skus[index]
    if (requireComplete && !sku.spec.trim()) {
      ElMessage.warning(`第 ${index + 1} 个规格名称不能为空`)
      return false
    }
    if (sku.price !== '' && (!Number.isFinite(Number(sku.price)) || Number(sku.price) <= 0)) {
      ElMessage.warning(`第 ${index + 1} 个规格价格必须大于 0`)
      return false
    }
    if (sku.stock < 0 || !Number.isFinite(sku.stock)) {
      ElMessage.warning(`第 ${index + 1} 个规格库存不能为负数`)
      return false
    }
  }
  return true
}

function buildPayload(): ProductDraftInput {
  return {
    id: productId.value || undefined,
    title: form.title.trim(),
    subtitle: form.subtitle.trim(),
    categoryId: form.categoryId,
    description: form.description.trim(),
    images: [...form.images],
    skus: form.skus.map((item) => ({
      id: item.id,
      spec: item.spec.trim() || '默认规格',
      price: Number(item.price || 0).toFixed(2),
      stock: Number(item.stock) || 0,
      code: item.code
    })),
    shippingTemplateId: form.shippingTemplateId,
    greenProfile: {
      origin: form.greenOrigin.trim(),
      plantingMode: form.greenMode.trim(),
      description: form.greenDescription.trim()
    },
    aidProjectId: form.aidProjectId || undefined
  }
}

async function save(mode: 'draft' | 'submit' | 'price'): Promise<void> {
  if (submitting.value) return
  if (mode === 'submit') {
    const valid = await formRef.value?.validate().catch(() => false)
    if (!valid) return
    if (!form.images.length) {
      ElMessage.warning('请至少选择 1 张商品图片')
      return
    }
    if (!validateSku(true)) return
    if (!form.shippingTemplateId) {
      ElMessage.warning('请选择运费模板')
      return
    }
  } else {
    if (!form.title.trim()) {
      ElMessage.warning('请先填写商品标题')
      return
    }
    if (!validateSku(false)) return
  }

  submitting.value = true
  try {
    if (mode === 'price') {
      await merchantApi.updatePriceStock(
        merchantId.value,
        productId.value,
        form.skus
          .filter((item) => item.id)
          .map((item) => ({
            id: item.id || '',
            price: Number(item.price || 0).toFixed(2),
            stock: Number(item.stock) || 0
          }))
      )
      ElMessage.success('价格与库存已更新，无需重新审核')
    } else {
      await merchantApi.saveProduct(
        merchantId.value,
        buildPayload(),
        mode === 'submit' ? 'submit' : 'draft'
      )
      ElMessage.success(mode === 'submit' ? '已提交审核' : '草稿已保存')
    }
    saved.value = true
    await router.push('/console/merchant/products')
  } catch (err) {
    ElMessage.error(toErrorState(err, '保存失败，请稍后重试').message)
  } finally {
    submitting.value = false
  }
}

function handleBeforeUnload(event: BeforeUnloadEvent): void {
  if (!dirty.value || saved.value) return
  event.preventDefault()
  event.returnValue = ''
}

onBeforeRouteLeave(async () => {
  if (!dirty.value || saved.value) return true
  try {
    await ElMessageBox.confirm('当前商品有未保存的修改，离开后修改将丢失。', '离开页面', {
      type: 'warning',
      confirmButtonText: '放弃修改',
      cancelButtonText: '继续编辑'
    })
    return true
  } catch {
    return false
  }
})

onMounted(() => {
  window.addEventListener('beforeunload', handleBeforeUnload)
  void load()
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload)
})
</script>

<template>
  <div>
    <ConsolePageHeader :title="pageTitle" :description="pageDescription">
      <template #actions>
        <el-button @click="router.push('/console/merchant/products')">返回列表</el-button>
      </template>
    </ConsolePageHeader>

    <ConsoleErrorState v-if="error" :message="error" :request-id="requestId" @retry="load" />
    <div v-else-if="loading" class="console-card">
      <el-skeleton :rows="12" animated />
    </div>
    <template v-else>
      <div v-if="product" class="console-alert-row">
        <ConsoleStatusTag kind="product" :value="product.status" />
        <span
          v-if="product.listed"
          class="console-status"
          style="color: #1f7a4d; background: #e7f4ec"
        >
          <i />已上架
        </span>
        <span v-if="product.auditReason" class="console-muted">
          审核说明：{{ product.auditReason }}
        </span>
        <span v-if="product.greenProfile.status === 'pending_review'" class="console-muted">
          绿色资料审核中
        </span>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        class="console-product-form"
        @submit.prevent
      >
        <section class="console-form-card">
          <h3>1. 商品基础信息</h3>
          <div class="console-form-grid">
            <el-form-item label="商品标题" prop="title" class="span-2">
              <el-input
                v-model="form.title"
                maxlength="60"
                show-word-limit
                placeholder="例如：静宁红富士苹果 5kg 精选装"
              />
            </el-form-item>
            <el-form-item label="商品卖点">
              <el-input
                v-model="form.subtitle"
                maxlength="40"
                show-word-limit
                placeholder="一句话说明产品特色"
              />
            </el-form-item>
            <el-form-item label="商品分类" prop="categoryId">
              <el-select v-model="form.categoryId" placeholder="请选择分类" style="width: 100%">
                <el-option
                  v-for="item in categories"
                  :key="item.id"
                  :label="item.name"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
          </div>
        </section>

        <section class="console-form-card">
          <h3>
            2. 商品图片
            <span class="console-muted" style="font-weight: 400">（最多 5 张，第一张为主图）</span>
          </h3>
          <div class="console-upload-row">
            <div v-for="(image, index) in form.images" :key="image" class="console-upload-item">
              <img :src="image" :alt="`商品图 ${index + 1}`" />
              <button type="button" title="移除图片" @click="form.images.splice(index, 1)">
                <el-icon><Close /></el-icon>
              </button>
              <span v-if="index === 0" class="console-cover-badge">主图</span>
            </div>
            <button
              v-if="form.images.length < 5"
              type="button"
              class="console-upload-add"
              @click="imageDialog = true"
            >
              <el-icon><Plus /></el-icon>
              <span>选择图片</span>
            </button>
          </div>
          <p class="console-muted" style="margin: 8px 0 0; font-size: 11px">
            演示环境使用本地素材库图片，不调用真实上传接口。
          </p>
        </section>

        <section class="console-form-card">
          <h3>3. 商品详情描述</h3>
          <el-form-item prop="description">
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="6"
              maxlength="1000"
              show-word-limit
              placeholder="请描述产品产地、种植方式、口感、规格、食用建议与售后说明等"
            />
          </el-form-item>
        </section>

        <section class="console-form-card">
          <h3>4. 规格、价格与库存</h3>
          <div class="console-price-stock-row console-muted" style="font-size: 11px">
            <span>规格名称</span><span>价格（元）</span><span>库存</span><span>SKU 编码</span
            ><span></span><span></span>
          </div>
          <div v-for="(sku, index) in form.skus" :key="index" class="console-price-stock-row">
            <el-input v-model="sku.spec" placeholder="例如：5kg 精选装" />
            <el-input v-model="sku.price" placeholder="0.00" inputmode="decimal" />
            <el-input-number
              v-model="sku.stock"
              :min="0"
              :max="999999"
              :controls="false"
              style="width: 100%"
            />
            <el-input
              v-model="sku.code"
              :placeholder="sku.id ? '' : '自动生成'"
              :disabled="Boolean(sku.id)"
            />
            <span class="console-mono" style="font-size: 11px; color: #7b8881">
              {{ sku.price ? `¥${formatMoney(sku.price)}` : '—' }}
            </span>
            <el-button
              link
              type="danger"
              :disabled="form.skus.length <= 1"
              @click="removeSku(index)"
            >
              删除
            </el-button>
          </div>
          <el-button plain size="small" @click="addSku">
            <el-icon><Plus /></el-icon>添加规格
          </el-button>
          <div class="console-audit-tip">
            审核规则：修改价格 /
            库存不触发审核；修改标题、主图、描述、分类、运费模板或绿色资料会重新进入审核。
            当前最低价：<strong>¥{{ formatMoney(minPrice.toFixed(2)) }}</strong
            >。
          </div>
        </section>

        <section class="console-form-card">
          <h3>5. 物流与运费模板</h3>
          <div class="console-form-grid">
            <el-form-item label="运费模板" required>
              <el-select
                v-model="form.shippingTemplateId"
                placeholder="请选择运费模板"
                style="width: 100%"
              >
                <el-option
                  v-for="item in templates"
                  :key="item.id"
                  :label="item.name"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="模板信息">
              <div
                v-if="currentTemplate"
                class="console-muted"
                style="font-size: 12px; line-height: 1.8"
              >
                满 {{ formatMoney(currentTemplate.freeThreshold) }} 元包邮；基础运费
                {{ formatMoney(currentTemplate.baseFee) }} 元；配送范围：
                {{ currentTemplate.regions }}
              </div>
              <span v-else class="console-muted">请选择运费模板</span>
            </el-form-item>
          </div>
        </section>

        <section class="console-form-card">
          <h3>6. 绿色产地信息</h3>
          <div class="console-form-grid">
            <el-form-item label="产地" prop="greenOrigin">
              <el-input v-model="form.greenOrigin" placeholder="例如：甘肃省平凉市静宁县" />
            </el-form-item>
            <el-form-item label="种植 / 养殖方式" prop="greenMode">
              <el-input v-model="form.greenMode" placeholder="例如：高原梯田果园种植" />
            </el-form-item>
            <el-form-item label="绿色资料说明" class="span-2">
              <el-input
                v-model="form.greenDescription"
                type="textarea"
                :rows="3"
                maxlength="300"
                show-word-limit
                placeholder="说明绿色种植、减碳或产地认证等信息"
              />
            </el-form-item>
          </div>
          <div class="console-audit-tip">
            绿色资料由平台审核；审核通过的商品会展示在消费者商城「绿色消费」相关场景。
          </div>
        </section>

        <section class="console-form-card">
          <h3>7. 助农项目关联</h3>
          <div class="console-form-grid">
            <el-form-item label="关联助农项目（选填）">
              <el-select
                v-model="form.aidProjectId"
                clearable
                placeholder="不关联"
                style="width: 100%"
              >
                <el-option
                  v-for="item in aidProjects"
                  :key="item.id"
                  :label="item.title"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="说明">
              <span class="console-muted" style="font-size: 12px; line-height: 1.8">
                关联后，商品成交额将按平台规则计入助农项目展示数据（演示金额）。
              </span>
            </el-form-item>
          </div>
        </section>

        <div class="console-form-footer">
          <span class="console-muted" style="margin-right: auto">
            <template v-if="priceStockOnly">仅价格 / 库存发生变化，保存后无需审核。</template>
            <template v-else-if="dirty">有未保存的修改</template>
            <template v-else>暂无未保存修改</template>
          </span>
          <el-button :disabled="submitting" @click="router.push('/console/merchant/products')">
            取消
          </el-button>
          <template v-if="priceStockOnly">
            <el-button type="primary" :loading="submitting" @click="save('price')">
              保存价格 / 库存
            </el-button>
          </template>
          <template v-else>
            <el-button :loading="submitting" @click="save('draft')">保存草稿</el-button>
            <el-button type="primary" :loading="submitting" @click="save('submit')">
              提交审核
            </el-button>
          </template>
        </div>
      </el-form>
    </template>

    <el-dialog v-model="imageDialog" title="选择商品图片" width="620px" append-to-body>
      <p class="console-muted" style="margin: 0 0 12px">
        从本地素材库选择（最多 5 张），点击切换选中状态。
      </p>
      <div class="console-image-picker">
        <button
          v-for="image in imageOptions"
          :key="image"
          type="button"
          :class="{ selected: form.images.includes(image) }"
          @click="toggleImage(image)"
        >
          <img :src="image" alt="商品图片" />
          <span>{{ form.images.includes(image) ? '已选择' : '选择' }}</span>
        </button>
      </div>
      <template #footer>
        <el-button @click="imageDialog = false">完成</el-button>
      </template>
    </el-dialog>
  </div>
</template>
