<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { api, ApiError } from '@/api/client'

const route = useRoute()
const password = ref('')
const confirm = ref('')
const message = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  if (password.value !== confirm.value) return (error.value = 'Passwords do not match.')
  loading.value = true
  try {
    const res = await api('/auth/password/reset/confirm/', {
      method: 'POST',
      auth: false,
      body: { uid: String(route.query.uid || ''), token: String(route.query.token || ''), new_password: password.value },
    })
    message.value = res.detail
  } catch (e) {
    error.value = e instanceof ApiError ? e.field('new_password') || e.message : 'Something went wrong.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-wrap">
    <div class="card">
      <h1 style="font-size: 1.6rem">Choose a new password</h1>
      <div v-if="message" class="alert alert-success">{{ message }} <RouterLink to="/login">Sign in</RouterLink></div>
      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <form v-if="!message" @submit.prevent="submit">
        <div class="field"><label for="p">New password</label><input id="p" v-model="password" type="password" autocomplete="new-password" minlength="10" required /></div>
        <div class="field"><label for="c">Confirm password</label><input id="c" v-model="confirm" type="password" autocomplete="new-password" required /></div>
        <button class="btn btn-primary btn-block" :disabled="loading">Reset password</button>
      </form>
    </div>
  </div>
</template>
