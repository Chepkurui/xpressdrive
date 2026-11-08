<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, ApiError } from '@/api/client'
import { date, TRIP_STATUSES } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import StaffNav from '@/components/StaffNav.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import PlaceSelect from '@/components/PlaceSelect.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const canAdd = computed(() => auth.can('trips', 'add'))
const filters = reactive({ state: route.query.state || 'open', status: '', origin: '', destination: '', backhaul: '', q: '', page: 1 })
const data = ref(null)
const error = ref('')
const showNew = ref(false)
const trucks = ref([])
const nt = reactive({ origin: '', destination: '', is_backhaul: false, truck_id: '', capacity_kg: '', capacity_cbm: '', carrier_reference: '', departure_date: '', eta_date: '', notes: '' })
const ntErr = ref({})
let timer

async function load() {
  error.value = ''
  try {
    data.value = await api('/staff/trips/', { query: { ...filters } })
  } catch (e) {
    error.value = e.message
  }
}
watch(() => [filters.state, filters.status, filters.origin, filters.destination, filters.backhaul, filters.page], load, { immediate: true })
watch(() => filters.q, () => { clearTimeout(timer); timer = setTimeout(() => { filters.page = 1; load() }, 350) })

async function openNew() {
  showNew.value = !showNew.value
  if (showNew.value && !trucks.value.length && auth.can('trucks')) {
    try { trucks.value = (await api('/staff/trucks/', { query: { active: 'true', page_size: 100 } })).results } catch { /* optional */ }
  }
}
watch(() => nt.truck_id, (id) => {
  const t = trucks.value.find((x) => String(x.id) === String(id))
  if (t) { nt.capacity_kg = t.capacity_kg || ''; nt.capacity_cbm = t.capacity_cbm || '' }
})

async function create() {
  ntErr.value = {}
  const body = { ...nt }
  for (const k of ['truck_id', 'capacity_kg', 'capacity_cbm', 'departure_date', 'eta_date']) if (body[k] === '') body[k] = null
  try {
    const t = await api('/staff/trips/', { method: 'POST', body })
    router.push(`/staff/trips/${t.code}`)
  } catch (e) {
    if (e instanceof ApiError && e.status === 400) ntErr.value = Object.fromEntries(Object.keys(e.data).map((k) => [k, e.field(k)]))
    else ntErr.value = { detail: e.status === 403 ? 'You do not have permission to create trips.' : e.message }
  }
}

function fill(t) {
  if (t.capacity_cbm && Number(t.used_cbm)) return { used: Number(t.used_cbm), cap: Number(t.capacity_cbm), unit: 'CBM' }
  if (t.capacity_kg) return { used: Number(t.used_kg), cap: Number(t.capacity_kg), unit: 'kg' }
  return null
}
</script>

<template>
  <section class="container" style="padding-top: 32px">
    <StaffNav />
    <div class="page-head">
      <h1>Trips</h1>
      <div style="display: flex; gap: 8px">
        <RouterLink to="/staff/live" class="btn btn-outline">Live map</RouterLink>
        <button v-if="canAdd" class="btn btn-primary" @click="openNew">{{ showNew ? 'Close' : '+ New trip' }}</button>
      </div>
    </div>

    <form v-if="showNew" class="card" style="margin-bottom: 20px" @submit.prevent="create">
      <h3>New trip</h3>
      <p class="small muted" style="margin-top: -6px">Plan a truck journey, add bookings to it, then allocate it to a driver. Tip: open driver offers under <RouterLink to="/staff/empty-legs">Empty legs</RouterLink> become backhaul trips in one click.</p>
      <div class="row">
        <div class="field"><label for="o">From</label><PlaceSelect id="o" v-model="nt.origin" required /><div class="error">{{ ntErr.origin }}</div></div>
        <div class="field"><label for="d">To</label><PlaceSelect id="d" v-model="nt.destination" required /><div class="error">{{ ntErr.destination }}</div></div>
        <div class="field"><label for="tr">Truck</label>
          <select id="tr" v-model="nt.truck_id"><option value="">Decide later</option><option v-for="t in trucks" :key="t.id" :value="t.id">{{ t.plate_number }} · {{ t.truck_type_display }}</option></select>
        </div>
      </div>
      <div class="row">
        <div class="field"><label for="ck">Capacity (kg)</label><input id="ck" v-model="nt.capacity_kg" type="number" min="0" step="0.01" /></div>
        <div class="field"><label for="cc">Capacity (CBM)</label><input id="cc" v-model="nt.capacity_cbm" type="number" min="0" step="0.001" /></div>
        <div class="field"><label for="ref">Container no. / reference</label><input id="ref" v-model="nt.carrier_reference" maxlength="80" /></div>
      </div>
      <div class="row">
        <div class="field"><label for="dd">Departure</label><input id="dd" v-model="nt.departure_date" type="date" /></div>
        <div class="field"><label for="eta">ETA</label><input id="eta" v-model="nt.eta_date" type="date" /></div>
        <div class="field" style="align-self: end"><label class="checkbox"><input v-model="nt.is_backhaul" type="checkbox" /> Return / backhaul leg</label></div>
      </div>
      <div class="field"><label for="no">Notes for the team and driver</label><textarea id="no" v-model="nt.notes"></textarea></div>
      <div v-if="ntErr.detail || ntErr.non_field_errors" class="alert alert-error">{{ ntErr.detail || ntErr.non_field_errors }}</div>
      <button class="btn btn-dark">Create trip</button>
    </form>

    <div class="card">
      <div class="filters">
        <div class="tabs">
          <button v-for="t in [['open', 'Open'], ['live', 'Under way'], ['closed', 'Finished'], ['', 'All']]" :key="t[0]" class="btn btn-sm" :class="filters.state === t[0] ? 'btn-dark' : 'btn-outline'" @click="filters.state = t[0]; filters.status = ''; filters.page = 1">{{ t[1] }}</button>
        </div>
        <select v-model="filters.status" aria-label="Status" @change="filters.page = 1">
          <option value="">Any status</option>
          <option v-for="s in TRIP_STATUSES" :key="s[0]" :value="s[0]">{{ s[1] }}</option>
        </select>
        <PlaceSelect v-model="filters.origin" placeholder="Any origin" aria-label="Origin" @update:model-value="filters.page = 1" />
        <PlaceSelect v-model="filters.destination" placeholder="Any destination" aria-label="Destination" @update:model-value="filters.page = 1" />
        <label class="checkbox small"><input v-model="filters.backhaul" type="checkbox" true-value="true" false-value="" /> Backhaul only</label>
        <input v-model="filters.q" placeholder="Search code, plate, driver…" maxlength="80" aria-label="Search" />
      </div>
      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <div v-if="!data && !error" class="spinner"></div>
      <template v-if="data">
        <div v-if="!data.results.length" class="empty">No trips match.</div>
        <div v-else class="table-wrap">
          <table>
            <thead><tr><th>Trip</th><th>Route</th><th>Status</th><th>Driver / truck</th><th>Load</th><th>Departs</th><th>ETA</th></tr></thead>
            <tbody>
              <tr v-for="t in data.results" :key="t.code" class="clickable" @click="router.push(`/staff/trips/${t.code}`)">
                <td class="mono">{{ t.code }}<div v-if="t.is_backhaul" class="small bh">Return leg</div></td>
                <td>{{ t.origin_name }} → {{ t.destination_name }}</td>
                <td><StatusBadge :status="t.status" :label="t.status_display" /><div v-if="t.driver_response === 'declined' && t.status === 'planned'" class="small danger">Last driver declined</div></td>
                <td>{{ t.driver?.full_name || '—' }}<div class="small muted">{{ t.truck?.plate_number || 'No truck' }}</div></td>
                <td style="min-width: 130px">
                  <div class="small">{{ t.shipment_count }} booking(s)</div>
                  <template v-if="fill(t)">
                    <div class="bar"><span :style="{ width: Math.min(100, (fill(t).used / fill(t).cap) * 100) + '%' }"></span></div>
                    <div class="small muted">{{ fill(t).used }} / {{ fill(t).cap }} {{ fill(t).unit }}</div>
                  </template>
                </td>
                <td class="small">{{ date(t.departure_date) }}</td>
                <td class="small">{{ date(t.eta_date) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="data.count > 20" class="pager">
          <button class="btn btn-outline btn-sm" :disabled="!data.previous" @click="filters.page--">← Previous</button>
          <span class="small muted">Page {{ filters.page }}</span>
          <button class="btn btn-outline btn-sm" :disabled="!data.next" @click="filters.page++">Next →</button>
        </div>
      </template>
    </div>
  </section>
</template>

<style scoped>
.filters { display: grid; grid-template-columns: auto 190px 170px 170px auto 1fr; gap: 10px; margin-bottom: 16px; align-items: center; }
.tabs { display: flex; gap: 6px; flex-wrap: wrap; }
.bar { height: 8px; border-radius: 99px; background: var(--border); overflow: hidden; margin: 4px 0; }
.bar span { display: block; height: 100%; background: var(--amber-dark); }
.bh { color: var(--amber-dark); font-weight: 700; font-family: inherit; }
.danger { color: var(--danger); }
.pager { display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: 16px; }
@media (max-width: 1100px) { .filters { grid-template-columns: 1fr 1fr; } .tabs { grid-column: 1 / -1; } }
@media (max-width: 600px) { .filters { grid-template-columns: 1fr; } }
</style>
