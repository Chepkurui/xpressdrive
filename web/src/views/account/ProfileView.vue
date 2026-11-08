<script setup>
import { defineAsyncComponent, reactive, ref } from 'vue'
import { ApiError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import AccountNav from '@/components/AccountNav.vue'

// Loaded only when the user chooses to change their password.
const ChangePasswordDialog = defineAsyncComponent(() => import('@/components/ChangePasswordDialog.vue'))

const auth = useAuthStore()
const showPw = ref(false)
const profile = reactive({ first_name: auth.user.first_name, last_name: auth.user.last_name, phone: auth.user.phone })
const msg = ref('')
const err = ref('')

async function saveProfile() {
  msg.value = err.value = ''
  try {
    await auth.updateProfile({ ...profile })
    msg.value = 'Profile updated.'
  } catch (e) {
    err.value = e instanceof ApiError ? e.message : 'Could not update profile.'
  }
}

</script>

<template>
  <section class="container" style="padding-top: 32px">
    <AccountNav />
    <h1 style="font-size: 1.8rem">Profile</h1>
    <div class="grid grid-2" style="align-items: start">
      <div>
        <form class="card" @submit.prevent="saveProfile">
          <h3>Your details</h3>
          <div v-if="msg" class="alert alert-success">{{ msg }}</div>
          <div v-if="err" class="alert alert-error">{{ err }}</div>
          <div class="field"><label>Email</label><input :value="auth.user.email" disabled /></div>
          <div class="row">
            <div class="field"><label for="fn">First name</label><input id="fn" v-model="profile.first_name" maxlength="80" required /></div>
            <div class="field"><label for="ln">Last name</label><input id="ln" v-model="profile.last_name" maxlength="80" required /></div>
          </div>
          <div class="field"><label for="ph">Phone</label><input id="ph" v-model="profile.phone" type="tel" /></div>
          <button class="btn btn-dark">Save</button>
        </form>

        <div class="card pw" style="margin-top: 20px">
          <div>
            <h3>Password</h3>
            <p class="small muted" style="margin: 0">Changing it signs you out on all devices.</p>
          </div>
          <button type="button" class="btn btn-outline" @click="showPw = true">Change password</button>
        </div>
      </div>
      <div class="card">
        <div class="small muted">Your customer code</div>
        <div class="code mono">{{ auth.user.customer_code }}</div>
        <p class="small muted">Quote this code when you call us, drop cargo at a depot or pay an invoice.</p>
        <p v-if="auth.user.is_driver" class="alert alert-info small" style="margin: 0">You're registered as a driver. Use the XpressDrive mobile app to get trip allocations and share your location while you drive.</p>
      </div>
    </div>
    <ChangePasswordDialog v-if="showPw" @close="showPw = false" />
  </section>
</template>

<style scoped>
.code { font-size: 1.8rem; font-weight: 800; color: var(--amber-dark); }
.pw { display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap; }
.pw h3 { margin: 0 0 4px; }
</style>
