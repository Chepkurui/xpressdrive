<script setup>
import { ref } from 'vue'
import { api, ApiError } from '@/api/client'

const email = ref('')
const message = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    message.value = (await api('/auth/password/reset/', { method: 'POST', body: { email: email.value }, auth: false })).detail
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Something went wrong.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-wrap">
    <div class="card">
      <h1 style="font-size: 1.6rem">Reset your password</h1>
      <div v-if="message" class="alert alert-success">{{ message }}</div>
      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <form v-if="!message" @submit.prevent="submit">
        <div class="field"><label for="e">Email</label><input id="e" v-model="email" type="email" required /></div>
        <button class="btn btn-primary btn-block" :disabled="loading">Send reset link</button>
      </form>
      <p class="small" style="margin-top: 16px"><RouterLink to="/login">Back to sign in</RouterLink></p>
    </div>
  </div>
</template>
