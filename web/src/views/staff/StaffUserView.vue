<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, ApiError } from '@/api/client'
import { money, date, dateTime } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import StaffNav from '@/components/StaffNav.vue'
import StatusBadge from '@/components/StatusBadge.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const u = ref(null)
const shipments = ref(null)
const error = ref('')
const msg = ref('')
const fieldErrors = ref({})
const busy = ref(false)
const form = reactive({ first_name: '', last_name: '', email: '', phone: '', is_driver: false, licence_number: '' })
const url = () => `/staff/users/${encodeURIComponent(route.params.code)}/`

// Other rules (e.g. only superusers may edit other staff) are enforced by the API.
const isSelf = computed(() => u.value?.email === auth.user?.email)

function fill(data) {
  u.value = data
  for (const k of Object.keys(form)) form[k] = data[k] ?? ''
}
async function load() {
  try {
    fill(await api(url()))
  } catch (e) {
    error.value = e instanceof ApiError && e.status === 404 ? 'Account not found.' : e.message
    return
  }
  if (auth.can('shipments')) {
    try {
      shipments.value = await api('/staff/shipments/', { query: { owner: route.params.code, page_size: 100 } })
    } catch { /* optional */ }
  }
}
onMounted(load)

async function patch(body, okMsg) {
  busy.value = true
  msg.value = ''
  error.value = ''
  fieldErrors.value = {}
  try {
    fill(await api(url(), { method: 'PATCH', body }))
    msg.value = okMsg
  } catch (e) {
    if (e instanceof ApiError) fieldErrors.value = e.data
    error.value = e.message
  } finally {
    busy.value = false
  }
}
const save = () => patch({ ...form }, 'Details saved.')
function toggleActive() {
  const off = u.value.is_active
  if (off && !confirm(`Deactivate ${u.value.full_name || u.value.email}? They will not be able to sign in. Their bookings are kept.`)) return
  patch({ is_active: !off }, off ? 'Account deactivated.' : 'Account reactivated.')
}
async function sendReset() {
  if (!confirm(`Email a password reset link to ${u.value.email}?`)) return
  busy.value = true
  try {
    msg.value = (await api(`${url()}password-reset/`, { method: 'POST' })).detail
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
const err = (k) => { const v = fieldErrors.value?.[k]; return Array.isArray(v) ? v.join(' ') : v || '' }
</script>

<template>
  <section class="container" style="padding-top: 32px">
    <StaffNav />
    <RouterLink to="/staff/users" class="small">← All people</RouterLink>
    <div v-if="error" class="alert alert-error" style="margin-top: 12px">{{ error }}</div>
    <div v-if="!u && !error" class="spinner"></div>

    <template v-if="u">
      <div class="page-head" style="margin-top: 12px">
        <div>
          <h1>{{ u.full_name || u.email }}</h1>
          <div class="muted"><span class="mono">{{ u.customer_code }}</span> · joined {{ date(u.date_joined) }} · last sign-in {{ dateTime(u.last_login) }}</div>
        </div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap">
          <span v-if="!u.is_active" class="badge red">Deactivated</span>
          <span v-if="u.is_superuser" class="badge amber">Admin</span>
          <span v-else-if="u.is_staff" class="badge blue">Staff</span>
          <span v-if="u.is_driver" class="badge green">Driver</span>
        </div>
      </div>
      <div v-if="msg" class="alert alert-success">{{ msg }}</div>

      <div class="grid grid-2" style="align-items: start">
        <form class="card" @submit.prevent="save">
          <h3>Details</h3>
          <fieldset :disabled="!auth.can('users', 'change')">
            <div class="row">
              <div class="field"><label for="fn">First name</label><input id="fn" v-model="form.first_name" maxlength="80" required /><div class="error">{{ err('first_name') }}</div></div>
              <div class="field"><label for="ln">Last name</label><input id="ln" v-model="form.last_name" maxlength="80" required /><div class="error">{{ err('last_name') }}</div></div>
            </div>
            <div class="field"><label for="em">Email (used to sign in)</label><input id="em" v-model="form.email" type="email" required /><div class="error">{{ err('email') }}</div></div>
            <div class="field"><label for="ph">Phone</label><input id="ph" v-model="form.phone" /><div class="error">{{ err('phone') }}</div></div>
            <div class="driver-box">
              <label class="checkbox"><input v-model="form.is_driver" type="checkbox" /> Driver: can sign in to the driver app, receive trip allocations and share location</label>
              <div v-if="form.is_driver" class="field" style="margin: 10px 0 0"><label for="lic">Driving licence no.</label><input id="lic" v-model="form.licence_number" maxlength="40" /><div class="error">{{ err('licence_number') }}</div></div>
            </div>
          </fieldset>
          <button v-if="auth.can('users', 'change')" class="btn btn-dark" :disabled="busy">Save</button>
        </form>

        <div v-if="auth.can('users', 'change')" class="card">
          <h3>Account</h3>
          <p class="small muted">Staff can't see passwords. Send a reset link and the customer chooses a new one.</p>
          <button class="btn btn-outline" :disabled="busy || !u.is_active" @click="sendReset">Email password reset link</button>
          <hr />
          <p class="small muted">{{ u.is_active ? 'Deactivating blocks sign-in but keeps all bookings and history.' : 'This account cannot sign in.' }}</p>
          <button v-if="!isSelf" class="btn" :class="u.is_active ? 'btn-danger' : 'btn-dark'" :disabled="busy" @click="toggleActive">{{ u.is_active ? 'Deactivate account' : 'Reactivate account' }}</button>
          <p v-if="u.is_staff" class="small muted" style="margin-top: 12px">Staff roles and permissions are managed in the Django admin.</p>
        </div>
      </div>

      <template v-if="shipments">
        <h2 style="font-size: 1.2rem; margin: 28px 0 12px">Bookings ({{ shipments.count }})</h2>
        <div class="card">
          <div v-if="!shipments.results.length" class="empty">No bookings yet.</div>
          <div v-else class="table-wrap">
            <table>
              <thead><tr><th>Tracking</th><th>Cargo</th><th>Route</th><th>Status</th><th>Charge</th><th>Created</th></tr></thead>
              <tbody>
                <tr v-for="s in shipments.results" :key="s.tracking_number" class="clickable" @click="router.push(`/staff/shipments/${s.tracking_number}`)">
                  <td class="mono">{{ s.tracking_number }}<div class="small muted">{{ s.mode_display }}</div></td>
                  <td>{{ s.description }}</td>
                  <td class="small">{{ s.origin_name }} → {{ s.destination_name }}</td>
                  <td><StatusBadge :status="s.status" :label="s.status_display" /></td>
                  <td>{{ money(s.charge_usd) }}<div class="small muted">{{ s.payment_status_display }}</div></td>
                  <td class="small">{{ date(s.created_at) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </template>
  </section>
</template>

<style scoped>
.driver-box { margin-top: 8px; padding: 12px; border-radius: 10px; background: var(--bg); }
.page-head h1 { font-size: 1.6rem; }
fieldset { border: 0; padding: 0; margin: 0; min-width: 0; }
hr { border: 0; border-top: 1px solid var(--border); margin: 20px 0; }
</style>
