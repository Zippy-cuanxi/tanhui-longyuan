<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { errorText, formatDate, toDateInput } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import AppIcon from '@/components/AppIcon.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import StateBlock from '@/components/StateBlock.vue'

const auth = useAuthStore()
const toast = useToastStore()
const loading = ref(true)
const saving = ref(false)
const avatarUploading = ref(false)
const avatarInput = ref<HTMLInputElement | null>(null)
const error = ref('')

const MAX_AVATAR_MB = 5

const form = reactive({
  nickname: '',
  gender: '',
  birthday: '',
  bio: '',
  avatar_url: ''
})

function fill(): void {
  form.nickname = auth.profile?.nickname || ''
  form.gender = auth.profile?.gender || ''
  form.birthday = toDateInput(auth.profile?.birthday)
  form.bio = auth.profile?.bio || ''
  form.avatar_url = auth.profile?.avatar_url || ''
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    if (!auth.user) await auth.fetchMe()
    fill()
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

function pickAvatar(): void {
  avatarInput.value?.click()
}

async function onAvatarChange(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    toast.show('仅支持 JPG、PNG、WebP 格式的图片', 'warning')
    return
  }
  if (file.size > MAX_AVATAR_MB * 1024 * 1024) {
    toast.show(`头像图片不能超过 ${MAX_AVATAR_MB}MB`, 'warning')
    return
  }
  avatarUploading.value = true
  try {
    const updated = await auth.uploadAvatar(file)
    form.avatar_url = updated.avatar_url || ''
    toast.show('头像已更新', 'success')
  } catch (err) {
    toast.show(errorText(err), 'error', (err as { requestId?: string }).requestId)
  } finally {
    avatarUploading.value = false
  }
}

async function removeAvatar(): Promise<void> {
  if (!form.avatar_url || avatarUploading.value) return
  avatarUploading.value = true
  try {
    await auth.updateProfile({ avatar_url: null })
    form.avatar_url = ''
    toast.show('已恢复默认头像', 'success')
  } catch (err) {
    toast.show(errorText(err), 'error', (err as { requestId?: string }).requestId)
  } finally {
    avatarUploading.value = false
  }
}

async function submit(): Promise<void> {
  error.value = ''
  if (form.nickname.length > 64) {
    error.value = '昵称不能超过 64 个字符'
    return
  }
  if (form.bio.length > 255) {
    error.value = '个人简介不能超过 255 个字符'
    return
  }
  saving.value = true
  try {
    await auth.updateProfile({
      nickname: form.nickname.trim() || null,
      gender: form.gender || null,
      birthday: form.birthday || null,
      bio: form.bio.trim() || null,
      avatar_url: form.avatar_url.trim() || null
    })
    fill()
    toast.show('个人资料已保存', 'success')
  } catch (err) {
    error.value = errorText(err)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="profile-view">
    <header class="account-page-head">
      <div>
        <span class="eyebrow">PROFILE</span>
        <h2>个人资料</h2>
        <p>维护昵称、头像与个人简介；邮箱与手机号由账号系统管理。</p>
      </div>
    </header>

    <StateBlock v-if="loading" :loading="true" />
    <StateBlock v-else-if="error && !auth.user" :error="error" @retry="load" />

    <template v-else-if="auth.user">
      <section class="profile-summary">
        <UserAvatar :url="form.avatar_url" :text="auth.avatarText" :size="58" />
        <div>
          <span class="eyebrow">ACCOUNT</span>
          <h3>{{ auth.displayName }}</h3>
          <p>{{ auth.user.email }}</p>
          <small>注册于 {{ formatDate(auth.user.created_at) }}</small>
        </div>
        <div class="profile-status">
          <span
            >账号状态 <em>{{ auth.user.is_active ? '正常' : '已禁用' }}</em></span
          >
          <span
            >邮箱验证 <em>{{ auth.user.is_email_verified ? '已验证' : '未验证' }}</em></span
          >
          <span
            >MFA <em>{{ auth.user.mfa_enabled ? '已开启' : '未开启' }}</em></span
          >
        </div>
      </section>

      <form class="profile-form" @submit.prevent="submit">
        <section class="info-card">
          <header>
            <AppIcon name="user" :size="16" />
            <h3>基本信息</h3>
          </header>
          <div class="form-grid">
            <label class="field">
              <span>昵称</span>
              <input v-model="form.nickname" maxlength="64" placeholder="如何称呼你" />
            </label>
            <label class="field">
              <span>性别</span>
              <select v-model="form.gender">
                <option value="">不填写</option>
                <option value="男">男</option>
                <option value="女">女</option>
                <option value="保密">保密</option>
              </select>
            </label>
            <label class="field">
              <span>生日</span>
              <input v-model="form.birthday" type="date" />
            </label>
            <div class="field field-wide">
              <span>头像</span>
              <div class="avatar-editor">
                <UserAvatar :url="form.avatar_url" :text="auth.avatarText" :size="72" />
                <div class="avatar-editor-copy">
                  <div class="avatar-editor-actions">
                    <button
                      type="button"
                      class="outline-button small"
                      :disabled="avatarUploading"
                      @click="pickAvatar"
                    >
                      <span v-if="avatarUploading" class="mini-spinner dark" />
                      {{ avatarUploading ? '上传中…' : '上传头像' }}
                    </button>
                    <button
                      v-if="form.avatar_url"
                      type="button"
                      class="avatar-remove"
                      :disabled="avatarUploading"
                      @click="removeAvatar"
                    >
                      移除头像
                    </button>
                  </div>
                  <small class="avatar-editor-hint">
                    支持 JPG、PNG、WebP，单张不超过 {{ MAX_AVATAR_MB }}MB；上传后立即生效。
                  </small>
                </div>
              </div>
              <input
                ref="avatarInput"
                class="avatar-file-input"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                @change="onAvatarChange"
              />
            </div>
            <label class="field field-wide">
              <span>个人简介</span>
              <textarea
                v-model="form.bio"
                maxlength="255"
                rows="3"
                placeholder="简单介绍一下自己"
              />
            </label>
          </div>
        </section>

        <p v-if="error" class="form-error">{{ error }}</p>
        <button class="primary-button" type="submit" :disabled="saving">
          <span v-if="saving" class="mini-spinner" />
          {{ saving ? '保存中…' : '保存资料' }}
        </button>
      </form>
    </template>
  </div>
</template>
