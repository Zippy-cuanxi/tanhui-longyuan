<script setup lang="ts">
import { assetUrl } from '@/api/http'
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/components/AppIcon.vue'
import { useToastStore } from '@/stores/toast'
import { useAuthStore } from '@/stores/auth'
import { merchantApi } from '@/api'
import { errorText } from '@/utils/format'

type CertKey = 'license' | 'food' | 'green'

const toast = useToastStore()
const auth = useAuthStore()
const router = useRouter()
const submitting = ref(false)

const ENTITY_TYPES = ['农民专业合作社', '涉农企业', '家庭农场', '个体工商户']

const REGIONS: Record<string, string[]> = {
  兰州市: ['城关区', '七里河区', '安宁区', '西固区', '红古区', '榆中县', '皋兰县', '永登县'],
  嘉峪关市: ['雄关区', '长城区', '镜铁区'],
  金昌市: ['金川区', '永昌县'],
  白银市: ['白银区', '平川区', '靖远县', '会宁县', '景泰县'],
  天水市: ['秦州区', '麦积区', '清水县', '秦安县', '甘谷县', '武山县', '张家川县'],
  武威市: ['凉州区', '民勤县', '古浪县', '天祝县'],
  张掖市: ['甘州区', '临泽县', '高台县', '山丹县', '民乐县', '肃南县'],
  平凉市: ['崆峒区', '泾川县', '灵台县', '崇信县', '庄浪县', '静宁县', '华亭市'],
  酒泉市: ['肃州区', '玉门市', '敦煌市', '金塔县', '瓜州县', '肃北县', '阿克塞县'],
  庆阳市: ['西峰区', '庆城县', '环县', '华池县', '合水县', '正宁县', '宁县', '镇原县'],
  定西市: ['安定区', '通渭县', '陇西县', '渭源县', '临洮县', '漳县', '岷县'],
  陇南市: ['武都区', '成县', '文县', '宕昌县', '康县', '西和县', '礼县', '徽县', '两当县'],
  临夏州: ['临夏市', '临夏县', '康乐县', '永靖县', '广河县', '和政县', '东乡县', '积石山县'],
  甘南州: ['合作市', '临潭县', '卓尼县', '舟曲县', '迭部县', '玛曲县', '碌曲县', '夏河县']
}

const STEPS = [
  { icon: assetUrl('/images/join/step-1-fill.webp'), title: '填写主体信息', hint: '约 10 分钟' },
  { icon: assetUrl('/images/join/step-2-upload.webp'), title: '上传资质证照', hint: '1-3 个工作日' },
  { icon: assetUrl('/images/join/step-3-review.webp'), title: '平台审核', hint: '审核结果短信通知' },
  { icon: assetUrl('/images/join/step-4-success.webp'), title: '入驻成功', hint: '开通店铺后台' }
]

const BENEFITS = [
  {
    icon: assetUrl('/images/join/benefit-origin.webp'),
    title: '源头直采',
    desc: '对接甘肃产地，汇聚特色农产'
  },
  {
    icon: assetUrl('/images/join/benefit-cert.webp'),
    title: '绿色认证',
    desc: '展示绿色食品认证，突出产品特色'
  },
  {
    icon: assetUrl('/images/join/benefit-settle.webp'),
    title: '结算保障',
    desc: '规范对账流程，保障商家结算'
  },
  {
    icon: assetUrl('/images/join/benefit-logistics.webp'),
    title: '物流扶持',
    desc: '整合产地物流，助力农产品外运'
  }
]

const CITIES = Object.keys(REGIONS)

const form = reactive({
  entityType: '农民专业合作社',
  entityName: '',
  creditCode: '',
  contact: '',
  phone: '',
  province: '甘肃省',
  city: '',
  district: '',
  mainProducts: '',
  agree: false
})

const certFiles = reactive<Record<CertKey, string>>({
  license: '',
  food: '',
  green: ''
})

const errors = reactive<Record<string, string>>({})
const uploadTarget = ref<CertKey | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

const districts = computed(() => (form.city ? REGIONS[form.city] || [] : []))

watch(
  () => form.city,
  () => {
    form.district = ''
    clearError('city')
    clearError('district')
  }
)

function clearError(key: string): void {
  delete errors[key]
}

function scrollToForm(): void {
  document.getElementById('join-form')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function pickFile(key: CertKey): void {
  uploadTarget.value = key
  fileInput.value?.click()
}

function onFileChange(event: Event): void {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  const key = uploadTarget.value
  input.value = ''
  if (!file || !key) return
  if (!/\.(jpe?g|png)$/i.test(file.name)) {
    toast.show('仅支持 JPG、PNG 格式的证照图片', 'warning')
    return
  }
  if (file.size > 10 * 1024 * 1024) {
    toast.show('单个证照文件不能超过 10M', 'warning')
    return
  }
  certFiles[key] = file.name
  clearError(key)
}

function certHint(key: CertKey): string {
  return certFiles[key] ? `已选择：${certFiles[key]}` : '支持 JPG、PNG 格式，单个文件不超过10M'
}

function validate(): boolean {
  Object.keys(errors).forEach((key) => delete errors[key])
  if (!form.entityName.trim()) errors.entityName = '请填写营业执照上的主体名称'
  if (!/^[0-9A-Za-z]{18}$/.test(form.creditCode.trim())) {
    errors.creditCode = '请填写 18 位统一社会信用代码'
  }
  if (!form.contact.trim()) errors.contact = '请填写联系人姓名'
  if (!/^1\d{10}$/.test(form.phone.trim())) errors.phone = '请填写 11 位手机号'
  if (!form.city) errors.city = '请选择所在城市'
  if (!form.district) errors.district = '请选择所在区县'
  if (!certFiles.license) errors.license = '请上传营业执照'
  if (!certFiles.food) errors.food = '请上传食品经营许可证'
  return Object.keys(errors).length === 0
}

async function submit(): Promise<void> {
  if (!form.agree) {
    toast.show('请先阅读并同意《商家入驻协议》与《绿色产品承诺》', 'warning')
    return
  }
  if (!validate()) {
    toast.show('请完善带 * 的必填信息', 'warning')
    return
  }
  if (!auth.isAuthenticated) {
    toast.show('请先登录后再提交入驻申请', 'warning')
    router.push({ name: 'login', query: { redirect: '/join' } })
    return
  }
  submitting.value = true
  try {
    const storeName = `${form.entityName.trim()}旗舰店`.slice(0, 64)
    await merchantApi.apply({
      company_name: form.entityName.trim(),
      license_no: form.creditCode.trim(),
      legal_person: form.contact.trim(),
      contact_phone: form.phone.trim(),
      region: `${form.province}${form.city}${form.district}`,
      store_name: storeName
    })
    toast.show('入驻申请已提交，请等待管理员审核', 'success')
  } catch (err) {
    toast.show(errorText(err), 'error')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="page-main join-page">
    <section class="join-hero">
      <img class="join-hero-img" :src="assetUrl('/images/join/join-hero.webp')" alt="" aria-hidden="true" />
      <div class="join-hero-inner">
        <h1>商家入驻</h1>
        <p>加入碳惠陇原 · 把甘肃好物卖向万家餐桌</p>
        <button class="join-apply" type="button" @click="scrollToForm">
          立即申请
          <AppIcon name="arrow-right" :size="15" />
        </button>
      </div>
    </section>

    <div class="join-body">
      <div class="join-container">
        <h2 class="join-section-title">入驻流程</h2>
        <div class="join-steps">
          <article v-for="step in STEPS" :key="step.title" class="join-step">
            <img :src="step.icon" :alt="step.title" loading="lazy" />
            <strong>{{ step.title }}</strong>
            <span>{{ step.hint }}</span>
          </article>
        </div>

        <div class="join-layout">
          <div class="join-main">
            <section id="join-form" class="join-card">
              <h2>主体信息</h2>
              <div class="join-form">
                <div class="join-row">
                  <label for="join-entity-type">主体类型</label>
                  <div class="join-control">
                    <select id="join-entity-type" v-model="form.entityType" class="join-select">
                      <option v-for="type in ENTITY_TYPES" :key="type" :value="type">
                        {{ type }}
                      </option>
                    </select>
                  </div>
                </div>

                <div class="join-row">
                  <label for="join-entity-name">主体名称</label>
                  <div class="join-control">
                    <input
                      id="join-entity-name"
                      v-model="form.entityName"
                      class="join-input"
                      :class="{ invalid: errors.entityName }"
                      type="text"
                      maxlength="60"
                      placeholder="请输入营业执照名称"
                      @input="clearError('entityName')"
                    />
                    <p v-if="errors.entityName" class="join-field-error">{{ errors.entityName }}</p>
                  </div>
                </div>

                <div class="join-row">
                  <label for="join-credit-code">统一社会信用代码</label>
                  <div class="join-control">
                    <input
                      id="join-credit-code"
                      v-model="form.creditCode"
                      class="join-input"
                      :class="{ invalid: errors.creditCode }"
                      type="text"
                      maxlength="18"
                      placeholder="请输入18位代码"
                      @input="clearError('creditCode')"
                    />
                    <p v-if="errors.creditCode" class="join-field-error">{{ errors.creditCode }}</p>
                  </div>
                </div>

                <div class="join-row">
                  <label for="join-contact">联系人</label>
                  <div class="join-control">
                    <input
                      id="join-contact"
                      v-model="form.contact"
                      class="join-input"
                      :class="{ invalid: errors.contact }"
                      type="text"
                      maxlength="20"
                      placeholder="请输入姓名"
                      @input="clearError('contact')"
                    />
                    <p v-if="errors.contact" class="join-field-error">{{ errors.contact }}</p>
                  </div>
                </div>

                <div class="join-row">
                  <label for="join-phone">联系手机</label>
                  <div class="join-control">
                    <input
                      id="join-phone"
                      v-model="form.phone"
                      class="join-input"
                      :class="{ invalid: errors.phone }"
                      type="tel"
                      maxlength="11"
                      placeholder="请输入11位手机号"
                      @input="clearError('phone')"
                    />
                    <p v-if="errors.phone" class="join-field-error">{{ errors.phone }}</p>
                  </div>
                </div>

                <div class="join-row">
                  <label for="join-city">所在地区</label>
                  <div class="join-control">
                    <div class="join-region">
                      <select id="join-province" v-model="form.province" class="join-select">
                        <option value="甘肃省">甘肃省</option>
                      </select>
                      <select
                        id="join-city"
                        v-model="form.city"
                        class="join-select"
                        :class="{ invalid: errors.city }"
                      >
                        <option value="" disabled>市</option>
                        <option v-for="city in CITIES" :key="city" :value="city">{{ city }}</option>
                      </select>
                      <select
                        id="join-district"
                        v-model="form.district"
                        class="join-select"
                        :class="{ invalid: errors.district }"
                        :disabled="!form.city"
                      >
                        <option value="" disabled>区县</option>
                        <option v-for="district in districts" :key="district" :value="district">
                          {{ district }}
                        </option>
                      </select>
                    </div>
                    <p v-if="errors.city || errors.district" class="join-field-error">
                      {{ errors.city || errors.district }}
                    </p>
                  </div>
                </div>

                <div class="join-row">
                  <label for="join-products">主打产品</label>
                  <div class="join-control">
                    <input
                      id="join-products"
                      v-model="form.mainProducts"
                      class="join-input"
                      type="text"
                      maxlength="60"
                      placeholder="请输入主打农产品"
                    />
                  </div>
                </div>
              </div>
            </section>

            <section class="join-card">
              <h2>资质证照</h2>
              <div class="join-certs">
                <div class="join-cert" :class="{ invalid: errors.license }">
                  <span class="join-cert-icon">
                    <AppIcon name="upload-cloud" :size="22" />
                  </span>
                  <div class="join-cert-copy">
                    <strong>营业执照 <em>*</em></strong>
                    <small>{{ certHint('license') }}</small>
                  </div>
                  <button
                    class="join-upload"
                    type="button"
                    :aria-label="certFiles.license ? '重新上传营业执照' : '上传营业执照'"
                    @click="pickFile('license')"
                  >
                    {{ certFiles.license ? '重新上传' : '上传' }}
                  </button>
                </div>

                <div class="join-cert" :class="{ invalid: errors.food }">
                  <span class="join-cert-icon">
                    <AppIcon name="upload-cloud" :size="22" />
                  </span>
                  <div class="join-cert-copy">
                    <strong>食品经营许可证 <em>*</em></strong>
                    <small>{{ certHint('food') }}</small>
                  </div>
                  <button
                    class="join-upload"
                    type="button"
                    :aria-label="certFiles.food ? '重新上传食品经营许可证' : '上传食品经营许可证'"
                    @click="pickFile('food')"
                  >
                    {{ certFiles.food ? '重新上传' : '上传' }}
                  </button>
                </div>

                <div class="join-cert optional">
                  <span class="join-cert-icon">
                    <AppIcon name="upload-cloud" :size="22" />
                  </span>
                  <div class="join-cert-copy">
                    <strong>绿色食品认证（选填）</strong>
                    <small>{{ certHint('green') }}</small>
                  </div>
                  <button
                    class="join-upload"
                    type="button"
                    :aria-label="certFiles.green ? '重新上传绿色食品认证' : '上传绿色食品认证'"
                    @click="pickFile('green')"
                  >
                    {{ certFiles.green ? '重新上传' : '上传' }}
                  </button>
                </div>
              </div>

              <input
                ref="fileInput"
                class="join-file-input"
                type="file"
                accept=".jpg,.jpeg,.png,image/jpeg,image/png"
                @change="onFileChange"
              />

              <label class="join-agree">
                <input v-model="form.agree" type="checkbox" />
                <span>我已阅读并同意《商家入驻协议》与《绿色产品承诺》</span>
              </label>

              <button class="join-submit" type="button" :disabled="submitting" @click="submit">{{ submitting ? '提交中…' : '提交入驻申请' }}</button>
            </section>
          </div>

          <aside class="join-side">
            <section class="join-side-card">
              <h2>入驻须知</h2>
              <ol class="join-notice-list">
                <li>
                  <span class="join-notice-num">1</span>
                  <span>证照需清晰完整且在有效期内</span>
                </li>
                <li>
                  <span class="join-notice-num">2</span>
                  <span>主体需为甘肃产地合作社或涉农企业</span>
                </li>
                <li>
                  <span class="join-notice-num">3</span>
                  <span>审核通过后短信通知并开通后台</span>
                </li>
              </ol>
            </section>

            <RouterLink to="/help" class="join-help">
              <span class="join-help-icon"><AppIcon name="headset" :size="30" /></span>
              <div>
                <strong>帮助中心</strong>
                <span>入驻问题请联系平台客服</span>
              </div>
            </RouterLink>

            <RouterLink
              class="join-help join-console-entry"
              :to="{
                path: '/console/login',
                query: { redirect: '/console/admin/products/review' }
              }"
            >
              <span class="join-help-icon"><AppIcon name="shield" :size="30" /></span>
              <div>
                <strong>商品审核后台</strong>
                <span>管理员登录后进入待审商品列表</span>
              </div>
            </RouterLink>
          </aside>
        </div>

        <div class="join-benefits">
          <article v-for="benefit in BENEFITS" :key="benefit.title" class="join-benefit">
            <img :src="benefit.icon" :alt="benefit.title" loading="lazy" />
            <div>
              <strong>{{ benefit.title }}</strong>
              <span>{{ benefit.desc }}</span>
            </div>
          </article>
        </div>
      </div>
    </div>
  </main>
</template>
