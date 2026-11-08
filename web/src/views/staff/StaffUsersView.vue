<script setup>
import { reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import { date } from '@/utils/format'
import StaffNav from '@/components/StaffNav.vue'

const router = useRouter()
const filters = reactive({ role: useRoute().query.role || 'customers', active: '', q: '', page: 1 })
const data = ref(null)
const error = ref('')
let timer

async function load() {
  error.value = ''
  try {
    data.value = await api('/staff/users/', { query: { ...filters } })
  } catch (e) {
    error.value = e.message
  }
}
watch(() => [filters.role, filters.active, filters.page], load, { immediate: true })
watch(() => filters.q, () => { clearTimeout(timer); timer = setTimeout(() => { filters.page = 1; load() }, 350) })
</script>

<template>
  <section class="container" style="padding-top: 32px">
    <StaffNav />
    <div class="page-head"><h1>People</h1></div>
    <div class="card">
      <div class="filters">
        <select v-model="filters.role" aria-label="Account type" @change="filters.page = 1">
          <option value="customers">Cargo owners</option>
          <option value="drivers">Drivers</option>
          <option value="staff">Staff</option>
          <option value="">Everyone</option>
        </select>
        <select v-model="filters.active" aria-label="Active" @change="filters.page = 1">
          <option value="">Active &amp; deactivated</option>
          <option value="true">Active only</option>
          <option value="false">Deactivated only</option>
        </select>
        <input v-model="filters.q" placeholder="Search name, email, phone or customer code…" maxlength="80" aria-label="Search" />
      </div>
      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <div v-if="!data && !error" class="spinner"></div>
      <template v-if="data">
        <div v-if="!data.results.length" class="empty">No accounts match.</div>
        <div v-else class="table-wrap">
          <table>
            <thead><tr><th>Name</th><th>Code</th><th>Email / phone</th><th>Bookings</th><th>Joined</th><th>Last sign-in</th><th></th></tr></thead>
            <tbody>
              <tr v-for="u in data.results" :key="u.customer_code" class="clickable" @click="router.push(`/staff/users/${u.customer_code}`)">
                <td><strong>{{ u.full_name || '—' }}</strong></td>
                <td class="mono">{{ u.customer_code }}</td>
                <td>{{ u.email }}<div class="small muted">{{ u.phone }}</div></td>
                <td>{{ u.shipment_count }}<span v-if="u.active_shipment_count" class="small muted"> ({{ u.active_shipment_count }} active)</span></td>
                <td class="small">{{ date(u.date_joined) }}</td>
                <td class="small">{{ date(u.last_login) }}</td>
                <td>
                  <span v-if="!u.is_active" class="badge red">Deactivated</span>
                  <span v-else-if="u.is_superuser" class="badge amber">Admin</span>
                  <span v-else-if="u.is_staff" class="badge blue">Staff</span>
                  <span v-if="u.is_driver && u.is_active" class="badge green">Driver</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="data.count > 20" class="pager">
          <button class="btn btn-outline btn-sm" :disabled="!data.previous" @click="filters.page--">← Previous</button>
          <span class="small muted">Page {{ filters.page }} of {{ Math.ceil(data.count / 20) }} · {{ data.count }} accounts</span>
          <button class="btn btn-outline btn-sm" :disabled="!data.next" @click="filters.page++">Next →</button>
        </div>
      </template>
    </div>
  </section>
</template>

<style scoped>
.filters { display: grid; grid-template-columns: 180px 200px 1fr; gap: 12px; margin-bottom: 16px; }
.pager { display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: 16px; }
@media (max-width: 860px) { .filters { grid-template-columns: 1fr; } }
</style>
