<script setup>
import { reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import { money, date, MODES } from '@/utils/format'
import AccountNav from '@/components/AccountNav.vue'
import StatusBadge from '@/components/StatusBadge.vue'

const router = useRouter()
const filters = reactive({ state: 'active', mode: '', q: '', page: 1 })
const data = ref(null)
const loading = ref(false)
const error = ref('')
let timer

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await api('/shipments/', { query: { ...filters } })
  } catch {
    error.value = 'Could not load bookings.'
  } finally {
    loading.value = false
  }
}
watch(() => [filters.state, filters.mode, filters.page], load, { immediate: true })
watch(() => filters.q, () => { clearTimeout(timer); timer = setTimeout(() => { filters.page = 1; load() }, 350) })
</script>

<template>
  <section class="container" style="padding-top: 32px">
    <AccountNav />
    <div class="page-head">
      <h1>My bookings</h1>
      <RouterLink to="/account/shipments/new" class="btn btn-primary">+ Book a truck</RouterLink>
    </div>
    <div class="card">
      <div class="filters">
        <div class="tabs">
          <button v-for="t in [['active','Active'],['closed','Delivered / cancelled'],['','All']]" :key="t[0]" class="btn btn-sm" :class="filters.state === t[0] ? 'btn-dark' : 'btn-outline'" @click="filters.state = t[0]; filters.page = 1">{{ t[1] }}</button>
        </div>
        <select v-model="filters.mode" aria-label="Load type" @change="filters.page = 1">
          <option value="">All load types</option>
          <option v-for="m in MODES" :key="m[0]" :value="m[0]">{{ m[1] }}</option>
        </select>
        <input v-model="filters.q" placeholder="Search tracking no., description, receiver…" maxlength="60" aria-label="Search" />
      </div>
      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <div v-if="loading && !data" class="spinner"></div>
      <template v-if="data">
        <div v-if="!data.results.length" class="empty">No bookings match these filters.</div>
        <div v-else class="table-wrap">
          <table>
            <thead><tr><th>Tracking</th><th>Cargo</th><th>Route</th><th>Status</th><th>Created</th><th>ETA</th><th>Charge</th></tr></thead>
            <tbody>
              <tr v-for="s in data.results" :key="s.tracking_number" class="clickable" @click="router.push(`/account/shipments/${s.tracking_number}`)">
                <td class="mono">{{ s.tracking_number }}</td>
                <td>{{ s.description }}<div class="small muted">{{ s.mode_display }}<template v-if="s.part"> · Part {{ s.part.number }} of {{ s.part.count }}</template></div></td>
                <td class="small">{{ s.origin_name }} → {{ s.destination_name }}</td>
                <td><StatusBadge :status="s.status" :label="s.status_display" /></td>
                <td class="small">{{ date(s.created_at) }}</td>
                <td class="small">{{ date(s.eta_date) }}</td>
                <td>{{ money(s.charge_usd) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="data.count > 20" class="pager">
          <button class="btn btn-outline btn-sm" :disabled="!data.previous" @click="filters.page--">← Previous</button>
          <span class="small muted">Page {{ filters.page }} of {{ Math.ceil(data.count / 20) }}</span>
          <button class="btn btn-outline btn-sm" :disabled="!data.next" @click="filters.page++">Next →</button>
        </div>
      </template>
    </div>
  </section>
</template>

<style scoped>
.filters { display: grid; grid-template-columns: auto 200px 1fr; gap: 12px; margin-bottom: 16px; align-items: center; }
.tabs { display: flex; gap: 6px; flex-wrap: wrap; }
.pager { display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: 16px; }
@media (max-width: 860px) { .filters { grid-template-columns: 1fr; } }
</style>
