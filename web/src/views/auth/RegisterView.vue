<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ApiError } from '@/api/client'

const auth = useAuthStore()
const router = useRouter()
const form = reactive({ first_name: '', last_name: '', email: '', phone: '', password: '', confirm: '' })
const errors = ref({})
const error = ref('')
const loading = ref(false)

async function submit() {
  errors.value = {}
  error.value = ''
  if (form.password !== form.confirm) {
    errors.value = { confirm: 'Passwords do not match.' }
    return
  }
  loading.value = true
  try {
    const { confirm, ...payload } = form
    await auth.register(payload)
    router.replace({ name: 'dashboard', query: { welcome: '1' } })
  } catch (e) {
    if (e instanceof ApiError && e.status === 400) {
      errors.value = Object.fromEntries(Object.keys(e.data).map((k) => [k, e.field(k)]))
      if (!Object.keys(errors.value).some((k) => k in form)) error.value = e.message
    } else {
      error.value = e instanceof ApiError && e.status === 429 ? 'Too many attempts. Please try again later.' : 'Registration failed. Please try again.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-wrap" style="max-width: 560px">
    <div class="card">
      <h1 style="font-size: 1.6rem">Create your account</h1>
      <p class="muted small">Free. Book anything from a parcel to a full container, and follow every milestone.</p>
      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <form novalidate @submit.prevent="submit">
        <div class="row">
          <div class="field"><label for="fn">First name</label><input id="fn" v-model="form.first_name" autocomplete="given-name" maxlength="80" required /><div class="error">{{ errors.first_name }}</div></div>
          <div class="field"><label for="ln">Last name</label><input id="ln" v-model="form.last_name" autocomplete="family-name" maxlength="80" required /><div class="error">{{ errors.last_name }}</div></div>
        </div>
        <div class="field"><label for="em">Email</label><input id="em" v-model="form.email" type="email" autocomplete="email" required /><div class="error">{{ errors.email }}</div></div>
        <div class="field"><label for="ph">Phone (WhatsApp preferred)</label><input id="ph" v-model="form.phone" type="tel" autocomplete="tel" placeholder="+256 7XX XXX XXX" required /><div class="error">{{ errors.phone }}</div></div>
        <div class="field">
          <label for="pw">Password</label>
          <input id="pw" v-model="form.password" type="password" autocomplete="new-password" minlength="10" required />
          <div class="small muted">At least 10 characters. Avoid common or all-numeric passwords.</div>
          <div class="error">{{ errors.password }}</div>
        </div>
        <div class="field"><label for="pc">Confirm password</label><input id="pc" v-model="form.confirm" type="password" autocomplete="new-password" required /><div class="error">{{ errors.confirm }}</div></div>
        <button class="btn btn-primary btn-block" :disabled="loading">{{ loading ? 'Creating account…' : 'Create account' }}</button>
      </form>
      <p class="small" style="margin-top: 16px">Already have an account? <RouterLink to="/login">Sign in</RouterLink></p>
    </div>
  </div>
</template>
