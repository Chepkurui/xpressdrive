<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import { money, date, MODES, STATUSES, PAYMENT_STATUSES } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import StaffNav from '@/components/StaffNav.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import PlaceSelect from '@/components/PlaceSelect.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const canChange = computed(() => auth.can('shipments', 'change'))

// Filters start from the URL so overview tiles can link straight to a filtered list.
const q0 = route.query
// Dashboard groupings (backend SHIPMENT_STAGES); shown as a removable chip.
const STAGE_LABELS = {
  booked: 'New bookings',
  awaiting_truck: 'Confirmed, awaiting a truck',
  on_truck: 'Truck allocated / loaded',
  transit: 'On the road',
  arrived: 'Arrived',
  on_hold: 'On hold',
  no_trip: 'Needs a truck (no trip yet)',
  awaiting_quote: 'Confirmed, needs a quote',
  unpaid: 'Unpaid',
}
const filters = reactive({
  stage: STAGE_LABELS[q0.stage] ? q0.stage : '',
  state: q0.state ?? (q0.status || q0.payment_status || q0.stage ? '' : 'active'),
  status: q0.status || '',
  payment_status: q0.payment_status || '',
  mode: q0.mode || '',
  origin: q0.origin || '',
  destination: q0.destination || '',
  q: q0.q || '',
  page: 1,
})
const data = ref(null)
const loading = ref(false)
const error = ref('')
const selected = ref(new Set())
const bulk = reactive({ status: '', note: '' })
const bulkMsg = ref('')
let timer

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await api('/staff/shipments/', { query: { ...filters } })
    selected.value = new Set()
  } catch (e) {
    error.value = e.message || 'Could not load bookings.'
  } finally {
    loading.value = false
  }
}
watch(() => [filters.stage, filters.state, filters.status, filters.payment_status, filters.mode, filters.origin, filters.destination, filters.page], load, { immediate: true })

function clearStage() {
  filters.stage = ''
  filters.page = 1
  router.replace({ query: { ...route.query, stage: undefined } })
}
watch(() => filters.q, () => { clearTimeout(timer); timer = setTimeout(() => { filters.page = 1; load() }, 350) })

function resetPage() { filters.page = 1 }
function toggle(tn) {
  const s = new Set(selected.value)
  s.has(tn) ? s.delete(tn) : s.add(tn)
  selected.value = s
}
const allSelected = computed(() => data.value?.results.length && data.value.results.every((s) => selected.value.has(s.tracking_number)))
function toggleAll() {
  selected.value = allSelected.value ? new Set() : new Set(data.value.results.map((s) => s.tracking_number))
}

async function applyBulk() {
  if (!bulk.status || !selected.value.size) return
  const label = STATUSES.find((s) => s[0] === bulk.status)?.[1]
  if (!confirm(`Set ${selected.value.size} booking(s) to "${label}"? Customers will see this update.`)) return
  try {
    const r = await api('/staff/shipments/bulk-status/', { method: 'POST', body: { tracking_numbers: [...selected.value], status: bulk.status, note: bulk.note } })
    bulkMsg.value = `${r.updated} booking(s) updated.`
    bulk.status = ''
    bulk.note = ''
    await load()
  } catch (e) {
    error.value = e.message
  }
}
</script>

<template>
  <section class="container" style="padding-top: 32px">
    <StaffNav />
    <div class="page-head"><h1>Bookings</h1></div>

    <div class="card">
      <div v-if="filters.stage" class="stage-chip">
        Showing: <strong>{{ STAGE_LABELS[filters.stage] }}</strong>
        <button type="button" aria-label="Clear stage filter" @click="clearStage">✕</button>
      </div>
      <div class="filters">
        <select v-model="filters.state" aria-label="Active or closed" @change="resetPage">
          <option value="active">Active</option>
          <option value="closed">Delivered / cancelled</option>
          <option value="">All</option>
        </select>
        <select v-model="filters.status" aria-label="Status" @change="resetPage">
          <option value="">Any status</option>
          <option v-for="s in STATUSES" :key="s[0]" :value="s[0]">{{ s[1] }}</option>
        </select>
        <select v-model="filters.payment_status" aria-label="Payment" @change="resetPage">
          <option value="">Any payment</option>
          <option v-for="s in PAYMENT_STATUSES" :key="s[0]" :value="s[0]">{{ s[1] }}</option>
        </select>
        <select v-model="filters.mode" aria-label="Load type" @change="resetPage">
          <option value="">All load types</option>
          <option v-for="m in MODES" :key="m[0]" :value="m[0]">{{ m[1] }}</option>
        </select>
        <PlaceSelect v-model="filters.origin" placeholder="Any origin" aria-label="Origin" @update:model-value="resetPage" />
        <PlaceSelect v-model="filters.destination" placeholder="Any destination" aria-label="Destination" @update:model-value="resetPage" />
        <input v-model="filters.q" class="search" placeholder="Search tracking no., customer name/email/code/phone, receiver…" maxlength="80" aria-label="Search" />
      </div>

      <div v-if="canChange && selected.size" class="bulk">
        <strong>{{ selected.size }} selected</strong>
        <select v-model="bulk.status" aria-label="New status">
          <option value="">Set status to…</option>
          <option v-for="s in STATUSES" :key="s[0]" :value="s[0]">{{ s[1] }}</option>
        </select>
        <input v-model="bulk.note" placeholder="Note for customers (optional)" maxlength="255" />
        <button class="btn btn-dark btn-sm" :disabled="!bulk.status" @click="applyBulk">Apply</button>
      </div>
      <div v-if="bulkMsg" class="alert alert-success">{{ bulkMsg }}</div>
      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <div v-if="loading && !data" class="spinner"></div>

      <template v-if="data">
        <div v-if="!data.results.length" class="empty">No bookings match these filters.</div>
        <div v-else class="table-wrap">
          <table>
            <thead>
              <tr>
                <th v-if="canChange"><input type="checkbox" :checked="allSelected" aria-label="Select all" @change="toggleAll" /></th>
                <th>Tracking</th><th>Customer</th><th>Cargo</th><th>Route</th><th>Status</th><th>Weight / CBM</th><th>Charge</th><th>Pickup</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in data.results" :key="s.tracking_number" class="clickable" @click="router.push(`/staff/shipments/${s.tracking_number}`)">
                <td v-if="canChange" @click.stop><input type="checkbox" :checked="selected.has(s.tracking_number)" :aria-label="`Select ${s.tracking_number}`" @change="toggle(s.tracking_number)" /></td>
                <td class="mono">{{ s.tracking_number }}<div class="small muted">{{ s.mode_display }}</div></td>
                <td>{{ s.owner.full_name }}<div class="small muted mono">{{ s.owner.customer_code }}</div></td>
                <td>{{ s.description }}<div v-if="s.part || s.trip_code" class="small muted"><span v-if="s.part" class="part">Part {{ s.part.number }} of {{ s.part.count }}</span><template v-if="s.trip_code">Trip {{ s.trip_code }}</template></div></td>
                <td class="small">{{ s.origin_name }} → {{ s.destination_name }}</td>
                <td><StatusBadge :status="s.status" :label="s.status_display" /></td>
                <td class="small">{{ s.weight_kg ? `${s.weight_kg} kg` : s.declared_weight_kg ? `~${s.declared_weight_kg} kg` : '—' }}<div v-if="s.volume_cbm" class="muted">{{ s.volume_cbm }} CBM</div></td>
                <td>{{ money(s.charge_usd) }}<div class="small muted">{{ s.payment_status_display }}</div></td>
                <td class="small">{{ s.pickup_date ? date(s.pickup_date) : '—' }}<div class="muted">booked {{ date(s.created_at) }}</div></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="data.count > 20" class="pager">
          <button class="btn btn-outline btn-sm" :disabled="!data.previous" @click="filters.page--">← Previous</button>
          <span class="small muted">Page {{ filters.page }} of {{ Math.ceil(data.count / 20) }} · {{ data.count }} bookings</span>
          <button class="btn btn-outline btn-sm" :disabled="!data.next" @click="filters.page++">Next →</button>
        </div>
      </template>
    </div>
  </section>
</template>

<style scoped>
.part { margin-right: 8px; padding: 0 6px; border-radius: 6px; background: var(--bg); border: 1px solid var(--border); }
.stage-chip { display: inline-flex; align-items: center; gap: 8px; background: var(--bg); border: 1px solid var(--border); border-radius: 999px; padding: 4px 6px 4px 14px; margin-bottom: 12px; font-size: 0.9rem; }
.stage-chip button { background: none; border: 0; cursor: pointer; color: var(--muted); font-size: 0.9rem; padding: 2px 6px; border-radius: 999px; }
.stage-chip button:hover { background: var(--border); color: var(--text); }
.filters { display: grid; grid-template-columns: repeat(4, minmax(140px, 1fr)); gap: 12px; margin-bottom: 16px; }
.filters .search { grid-column: 1 / -1; }
.bulk { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; padding: 12px; margin-bottom: 16px; border-radius: 10px; background: #fff9e8; border: 1px solid #f3dd9e; }
.bulk select { width: auto; }
.bulk input { flex: 1; min-width: 200px; }
td input[type='checkbox'], th input[type='checkbox'] { width: auto; }
.pager { display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: 16px; }
@media (max-width: 860px) { .filters { grid-template-columns: 1fr 1fr; } }
</style>
