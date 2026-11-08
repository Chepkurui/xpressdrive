<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { safeNext } from '@/router'
import { ApiError } from '@/api/client'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(email.value, password.value)
    // Staff land on the staff portal unless they were heading somewhere specific.
    router.replace(route.query.next ? safeNext(route.query.next) : auth.isStaff ? '/staff' : '/account')
  } catch (e) {
    error.value = e instanceof ApiError && e.status === 429
      ? 'Too many sign-in attempts. Please wait a minute and try again.'
      : 'Incorrect email or password.'
  } finally {
    password.value = ''
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-wrap">
    <div class="card">
      <h1 style="font-size: 1.6rem">Sign in</h1>
      <p class="muted small">Book trucks and follow your cargo across the region.</p>
      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <form @submit.prevent="submit">
        <div class="field"><label for="e">Email</label><input id="e" v-model="email" type="email" autocomplete="username" required /></div>
        <div class="field"><label for="p">Password</label><input id="p" v-model="password" type="password" autocomplete="current-password" required /></div>
        <button class="btn btn-primary btn-block" :disabled="loading">{{ loading ? 'Signing in…' : 'Sign in' }}</button>
      </form>
      <p class="small" style="margin-top: 16px"><RouterLink to="/forgot-password">Forgot your password?</RouterLink></p>
      <p class="small">New to XpressDrive? <RouterLink to="/register">Create an account</RouterLink></p>
    </div>
  </div>
</template>
