<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, ApiError } from '@/api/client'
import { ago, date, dateTime, money, LIVE_TRIP_STATUSES, TRIP_STATUSES } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import StaffNav from '@/components/StaffNav.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import PlaceSelect from '@/components/PlaceSelect.vue'
import FleetMap from '@/components/FleetMap.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const canChange = computed(() => auth.can('trips', 'change'))
const canMove = computed(() => canChange.value && auth.can('shipments', 'change'))

const t = ref(null)
const trail = ref([])
const error = ref('')
const msg = ref('')
const busy = ref(false)
const drivers = ref([])
const trucks = ref([])
const alloc = reactive({ driver: '', truck_id: '', note: '' })
const move = reactive({ status: '', place: '', place_label: '', note: '' })
const cp = reactive({ place: '', place_label: '', note: '' })
const form = reactive({})
const FIELDS = ['carrier_reference', 'capacity_cbm', 'capacity_kg', 'departure_date', 'eta_date', 'notes', 'is_backhaul']
const url = () => `/staff/trips/${encodeURIComponent(route.params.code)}/`
let timer

function fillForm(data) {
  t.value = data
  for (const k of FIELDS) form[k] = data[k] ?? ''
  alloc.truck_id = data.truck?.id || alloc.truck_id
}
async function load() {
  try {
    fillForm(await api(url()))
    if (t.value.last_position || LIVE_TRIP_STATUSES.includes(t.value.status)) {
      trail.value = (await api(`${url()}positions/`)).positions
    }
  } catch (e) {
    error.value = e instanceof ApiError && e.status === 404 ? 'Trip not found.' : e.message
  }
}
async function loadPickers() {
  if (!canChange.value) return
  try {
    const [d, tr] = await Promise.all([
      auth.can('users') ? api('/staff/drivers/') : Promise.resolve([]),
      auth.can('trucks') ? api('/staff/trucks/', { query: { active: 'true', page_size: 100 } }) : Promise.resolve({ results: [] }),
    ])
    drivers.value = d
    trucks.value = tr.results
  } catch { /* pickers are optional */ }
}
onMounted(() => {
  load()
  loadPickers()
  timer = setInterval(() => { if (t.value && LIVE_TRIP_STATUSES.includes(t.value.status) && document.visibilityState === 'visible') load() }, 30000)
})
onBeforeUnmount(() => clearInterval(timer))

async function run(fn, ok) {
  busy.value = true
  msg.value = error.value = ''
  try {
    await fn()
    msg.value = ok
    await load()
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
const allocate = () => run(async () => {
  await api(`${url()}allocate/`, { method: 'POST', body: { driver: alloc.driver, truck_id: alloc.truck_id || null, note: alloc.note } })
  alloc.note = ''
}, 'Trip offered to the driver. It is now in their app, waiting for them to accept.')
function doMove() {
  if (!move.status) return
  const label = TRIP_STATUSES.find((s) => s[0] === move.status)?.[1]
  if (!confirm(`Move this trip to "${label}"? Open bookings on it will be updated and cargo owners will see the milestone.`)) return
  run(async () => {
    const r = await api(`${url()}move/`, { method: 'POST', body: { ...move } })
    Object.assign(move, { status: '', place: '', place_label: '', note: '' })
    msg.value = `Moved. ${r.moved} booking(s) updated.`
  }, '')
}
const checkpoint = () => run(async () => {
  const r = await api(`${url()}checkpoint/`, { method: 'POST', body: { ...cp } })
  Object.assign(cp, { place: '', place_label: '', note: '' })
  msg.value = `Checkpoint posted to ${r.updated} booking(s).`
}, '')
const save = () => run(async () => {
  const body = Object.fromEntries(FIELDS.map((k) => [k, form[k] === '' && !['notes', 'carrier_reference'].includes(k) ? null : form[k]]))
  fillForm(await api(url(), { method: 'PATCH', body }))
}, 'Trip saved.')

const fill = computed(() => {
  if (!t.value) return null
  if (t.value.capacity_cbm && Number(t.value.used_cbm)) return { used: Number(t.value.used_cbm), cap: Number(t.value.capacity_cbm), unit: 'CBM' }
  if (t.value.capacity_kg) return { used: Number(t.value.used_kg), cap: Number(t.value.capacity_kg), unit: 'kg' }
  return null
})
const canAllocate = computed(() => t.value && ['planned', 'allocated', 'accepted'].includes(t.value.status))
const isClosed = computed(() => t.value && ['completed', 'cancelled'].includes(t.value.status))
const mapTrips = computed(() => (t.value?.last_position ? [{ ...t.value, stale: false }] : []))
</script>

<template>
  <section class="container" style="padding-top: 32px">
    <StaffNav />
    <RouterLink to="/staff/trips" class="small">← All trips</RouterLink>
    <div v-if="error" class="alert alert-error" style="margin-top: 12px">{{ error }}</div>
    <div v-if="!t && !error" class="spinner"></div>

    <template v-if="t">
      <div class="page-head" style="margin-top: 12px">
        <div>
          <div class="small muted">Trip <span v-if="t.is_backhaul" class="bh">· Return / backhaul leg</span></div>
          <h1 class="mono">{{ t.code }}</h1>
          <div class="lane">{{ t.origin_name }} → {{ t.destination_name }}</div>
          <div class="muted small">
            {{ t.driver?.full_name || 'No driver' }}<template v-if="t.driver?.phone"> · <a :href="`tel:${t.driver.phone}`">{{ t.driver.phone }}</a></template>
            · {{ t.truck ? `${t.truck.plate_number} (${t.truck.truck_type_display})` : 'No truck' }}
          </div>
        </div>
        <div style="text-align: right">
          <StatusBadge :status="t.status" :label="t.status_display" />
          <div v-if="t.driver_response" class="small muted" style="margin-top: 6px">Driver: {{ t.driver_response_display }}<template v-if="t.decline_reason"> ({{ t.decline_reason }})</template></div>
          <div v-if="t.last_position" class="small muted">📍 {{ ago(t.last_position.at) }}</div>
        </div>
      </div>
      <div v-if="msg" class="alert alert-success">{{ msg }}</div>

      <FleetMap v-if="mapTrips.length || trail.length" :trips="mapTrips" :trail="trail" :selected="t.code" height="380px" fit-on-change />
      <p v-else-if="!isClosed" class="card flat small muted">No GPS positions yet. The truck appears here once the driver accepts the trip and their phone starts sharing its location.</p>

      <div class="grid grid-2" style="align-items: start; margin-top: 20px">
        <div>
          <div v-if="canChange && canAllocate" class="card">
            <h3>{{ t.driver ? 'Reallocate' : 'Allocate to a driver' }}</h3>
            <form @submit.prevent="allocate">
              <div class="field">
                <label for="dr">Driver</label>
                <select id="dr" v-model="alloc.driver" required>
                  <option value="">Choose a driver</option>
                  <option v-for="d in drivers" :key="d.customer_code" :value="d.customer_code" :disabled="!!d.current_trip && d.current_trip.code !== t.code && d.current_trip.status !== 'allocated'">
                    {{ d.full_name }}{{ d.current_trip ? ` — on ${d.current_trip.code} (${d.current_trip.status_display})` : ' — available' }}
                  </option>
                </select>
                <div v-if="!drivers.length" class="small muted">No drivers yet. Mark an account as a driver under People.</div>
              </div>
              <div class="field">
                <label for="tk">Truck</label>
                <select id="tk" v-model="alloc.truck_id"><option value="">Keep current / none</option><option v-for="x in trucks" :key="x.id" :value="x.id">{{ x.plate_number }} · {{ x.truck_type_display }}</option></select>
              </div>
              <div class="field"><label for="an">Message to the driver <span class="muted small">(optional)</span></label><input id="an" v-model="alloc.note" maxlength="255" placeholder="e.g. Load at Gate 3, ask for Mr. Bahati" /></div>
              <button class="btn btn-primary" :disabled="busy">Send to driver's app</button>
            </form>
          </div>

          <div v-if="canMove && !isClosed" class="card" style="margin-top: 20px">
            <h3>Move this trip</h3>
            <p class="small muted">Drivers normally do this from the app. Use it when a driver has no signal, or to cancel. Open bookings get the matching milestone.</p>
            <form @submit.prevent="doMove">
              <div class="row">
                <div class="field"><label for="ms">New stage</label>
                  <select id="ms" v-model="move.status" required><option value="">Choose…</option><option v-for="s in TRIP_STATUSES" :key="s[0]" :value="s[0]" :disabled="s[0] === t.status">{{ s[1] }}</option></select>
                </div>
                <div class="field"><label for="mp">At</label><PlaceSelect id="mp" v-model="move.place" placeholder="(optional)" /></div>
              </div>
              <div class="field"><label for="mn">Note cargo owners will see <span class="muted small">(optional)</span></label><input id="mn" v-model="move.note" maxlength="255" /></div>
              <button class="btn btn-dark" :disabled="busy || !move.status">Move trip</button>
            </form>
          </div>

          <div v-if="canChange && !isClosed && !['planned', 'allocated'].includes(t.status)" class="card" style="margin-top: 20px">
            <h3>Post a checkpoint</h3>
            <p class="small muted">Tell cargo owners the truck has reached a major point, without changing its stage.</p>
            <form @submit.prevent="checkpoint">
              <div class="row">
                <div class="field"><label for="cpp">Place</label><PlaceSelect id="cpp" v-model="cp.place" placeholder="Choose…" /></div>
                <div class="field"><label for="cpl">…or type it</label><input id="cpl" v-model="cp.place_label" maxlength="120" placeholder="e.g. Lukaya weighbridge" /></div>
              </div>
              <div class="field"><label for="cpn">Note <span class="muted small">(optional)</span></label><input id="cpn" v-model="cp.note" maxlength="255" /></div>
              <button class="btn btn-outline" :disabled="busy || (!cp.place && !cp.place_label)">Post checkpoint</button>
            </form>
          </div>
        </div>

        <div>
          <form class="card" @submit.prevent="save">
            <h3>Details</h3>
            <div v-if="fill" style="margin-bottom: 16px">
              <div class="bar"><span :style="{ width: Math.min(100, (fill.used / fill.cap) * 100) + '%' }"></span></div>
              <div class="small muted">{{ fill.used }} of {{ fill.cap }} {{ fill.unit }} loaded ({{ Math.round((fill.used / fill.cap) * 100) }}%) · {{ t.shipment_count }} booking(s)</div>
            </div>
            <fieldset :disabled="!canChange">
              <div class="field"><label for="ref">Container no. / reference</label><input id="ref" v-model="form.carrier_reference" maxlength="80" /></div>
              <div class="row">
                <div class="field"><label for="cc">Capacity (CBM)</label><input id="cc" v-model="form.capacity_cbm" type="number" step="0.001" min="0" /></div>
                <div class="field"><label for="ck">Capacity (kg)</label><input id="ck" v-model="form.capacity_kg" type="number" step="0.01" min="0" /></div>
              </div>
              <div class="row">
                <div class="field"><label for="dd">Departure</label><input id="dd" v-model="form.departure_date" type="date" /></div>
                <div class="field"><label for="eta">ETA</label><input id="eta" v-model="form.eta_date" type="date" /></div>
              </div>
              <div class="field"><label class="checkbox"><input v-model="form.is_backhaul" type="checkbox" /> Return / backhaul leg <span class="muted small">(listed on the public return-truck board while planned)</span></label></div>
              <div class="field"><label for="no">Notes for the team and driver</label><textarea id="no" v-model="form.notes"></textarea></div>
            </fieldset>
            <button v-if="canChange" class="btn btn-dark" :disabled="busy">Save</button>
          </form>

          <div class="card" style="margin-top: 20px">
            <h3>Trip log</h3>
            <ul class="log">
              <li v-for="e in t.events" :key="e.id">
                <div class="small muted">{{ dateTime(e.created_at) }} · {{ e.created_by_name || 'System' }}</div>
                <div><strong>{{ e.kind === 'checkpoint' ? '📍 ' + (e.place_label || e.place) : e.status_display || e.kind_display }}</strong><template v-if="e.kind === 'status' && e.place_label"> at {{ e.place_label }}</template></div>
                <div v-if="e.note" class="small">{{ e.note }}</div>
              </li>
              <li v-if="!t.events.length" class="muted">Nothing yet.</li>
            </ul>
          </div>
        </div>
      </div>

      <h2 style="font-size: 1.2rem; margin: 28px 0 12px">Bookings on this trip</h2>
      <div class="card">
        <div v-if="!t.shipments.length" class="empty">No bookings yet. Open a booking and choose this trip to load it here, or <RouterLink :to="{ path: '/staff/shipments', query: { stage: 'no_trip', origin: t.origin } }">see cargo waiting for a truck from {{ t.origin_name }}</RouterLink>.</div>
        <div v-else class="table-wrap">
          <table>
            <thead><tr><th>Tracking</th><th>Customer</th><th>Cargo</th><th>Route</th><th>Status</th><th>Weight / CBM</th><th>Charge</th></tr></thead>
            <tbody>
              <tr v-for="s in t.shipments" :key="s.tracking_number" class="clickable" @click="router.push(`/staff/shipments/${s.tracking_number}`)">
                <td class="mono">{{ s.tracking_number }}</td>
                <td>{{ s.owner.full_name }}<div class="small muted mono">{{ s.owner.customer_code }}</div></td>
                <td>{{ s.description }}<div class="small muted">{{ s.mode_display }}</div></td>
                <td class="small">{{ s.origin_name }} → {{ s.destination_name }}</td>
                <td><StatusBadge :status="s.status" :label="s.status_display" /></td>
                <td class="small">{{ s.weight_kg ? `${s.weight_kg} kg` : s.declared_weight_kg ? `~${s.declared_weight_kg} kg` : '—' }}<div v-if="s.volume_cbm" class="muted">{{ s.volume_cbm }} CBM</div></td>
                <td>{{ money(s.charge_usd) }}<div class="small muted">{{ s.payment_status_display }}</div></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <p class="small muted" style="margin-top: 12px">Created {{ date(t.created_at) }}<template v-if="t.allocated_at"> · allocated {{ dateTime(t.allocated_at) }}</template><template v-if="t.started_at"> · departed {{ dateTime(t.started_at) }}</template><template v-if="t.completed_at"> · finished {{ dateTime(t.completed_at) }}</template></p>
    </template>
  </section>
</template>

<style scoped>
.page-head h1 { font-size: 1.6rem; }
.lane { font-size: 1.15rem; font-weight: 700; color: var(--navy); }
.bh { color: var(--amber-dark); font-weight: 700; }
fieldset { border: 0; padding: 0; margin: 0; min-width: 0; }
.bar { height: 10px; border-radius: 99px; background: var(--border); overflow: hidden; margin-bottom: 6px; }
.bar span { display: block; height: 100%; background: var(--amber-dark); }
.log { list-style: none; padding: 0; margin: 0; max-height: 420px; overflow-y: auto; }
.log li { padding: 8px 0; border-bottom: 1px solid var(--border); }
</style>
