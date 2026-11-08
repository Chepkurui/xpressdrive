<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, ApiError } from '@/api/client'
import { money, date, dateTime, STATUSES, PAYMENT_STATUSES, MODES, CATEGORIES } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import StaffNav from '@/components/StaffNav.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import PartsNotice from '@/components/PartsNotice.vue'
import PlaceSelect from '@/components/PlaceSelect.vue'

const route = useRoute()
const auth = useAuthStore()
const canChange = computed(() => auth.can('shipments', 'change'))

const s = ref(null)
const error = ref('')
const trips = ref([])
const form = reactive({})
const fieldErrors = ref({})
const saving = ref(false)
const saved = ref('')
const st = reactive({ status: '', location: '', note: '' })
const stBusy = ref(false)

const EDITABLE = ['trip', 'weight_kg', 'volume_cbm', 'packages_received', 'charge_usd', 'payment_status', 'eta_date', 'internal_notes',
  'description', 'category', 'mode', 'service_type', 'quantity', 'declared_weight_kg', 'declared_value_usd', 'is_hazardous', 'is_fragile',
  'origin', 'destination', 'pickup_address', 'pickup_date', 'consignee_name', 'consignee_phone', 'delivery_option', 'delivery_address']

function fill(data) {
  s.value = data
  for (const k of EDITABLE) form[k] = k === 'trip' ? data.trip_code || '' : data[k] ?? ''
  st.status = data.status
}
const url = () => `/staff/shipments/${encodeURIComponent(route.params.number)}/`

async function load() {
  try {
    fill(await api(url()))
  } catch (e) {
    error.value = e instanceof ApiError && e.status === 404 ? 'Booking not found.' : e.message
  }
  if (auth.can('trips')) {
    try {
      const r = await api('/staff/trips/', { query: { state: 'open', page_size: 100 } })
      trips.value = r.results
    } catch { /* trip list is optional */ }
  }
}
onMounted(load)

async function save() {
  saving.value = true
  saved.value = ''
  fieldErrors.value = {}
  const body = {}
  for (const k of EDITABLE) {
    let v = form[k]
    if (v === '' && !['internal_notes', 'description', 'delivery_address', 'pickup_address', 'consignee_name', 'consignee_phone'].includes(k)) v = null
    body[k] = v
  }
  try {
    fill(await api(url(), { method: 'PATCH', body }))
    saved.value = 'Changes saved.'
  } catch (e) {
    if (e instanceof ApiError) fieldErrors.value = e.data
    error.value = e.message
  } finally {
    saving.value = false
  }
}

async function changeStatus() {
  if (st.status === s.value.status && !st.note) return
  stBusy.value = true
  try {
    fill(await api(`${url()}status/`, { method: 'POST', body: { ...st } }))
    st.location = ''
    st.note = ''
    saved.value = 'Status updated. The customer can see it in their timeline.'
  } catch (e) {
    error.value = e.message
  } finally {
    stBusy.value = false
  }
}
// ---- split: send some of the customer's packages on a different truck
const router = useRouter()
const canSplit = computed(() => auth.can('shipments', 'add') && auth.can('shipments', 'change') && ['confirmed', 'allocated'].includes(s.value?.status))
const sp = reactive({ open: false, packages: '', weight_kg: '', volume_cbm: '', charge_usd: '', mode: '', trip: '', busy: false, errors: {}, err: '' })
const spHave = computed(() => s.value?.packages_received || s.value?.quantity || 0)
const spTrips = computed(() => trips.value.filter((b) => b.code !== s.value?.trip_code))
async function split() {
  sp.busy = true
  sp.errors = {}
  sp.err = ''
  const body = { packages: Number(sp.packages) }
  for (const k of ['weight_kg', 'volume_cbm', 'charge_usd', 'mode', 'trip']) if (sp[k] !== '') body[k] = sp[k]
  try {
    const r = await api(`${url()}split/`, { method: 'POST', body })
    Object.assign(sp, { open: false, packages: '', weight_kg: '', volume_cbm: '', charge_usd: '', mode: '', trip: '' })
    router.push(`/staff/shipments/${r.part.tracking_number}`)
  } catch (e) {
    sp.errors = e instanceof ApiError ? e.data || {} : {}
    sp.err = e.message
  } finally {
    sp.busy = false
  }
}
const spErr = (k) => { const v = sp.errors?.[k]; return Array.isArray(v) ? v.join(' ') : v || '' }
const err = (k) => { const v = fieldErrors.value?.[k]; return Array.isArray(v) ? v.join(' ') : v || '' }
</script>

<template>
  <section class="container" style="padding-top: 32px">
    <StaffNav />
    <RouterLink to="/staff/shipments" class="small">← All bookings</RouterLink>
    <div v-if="error" class="alert alert-error" style="margin-top: 12px">{{ error }}</div>
    <div v-if="!s && !error" class="spinner"></div>

    <template v-if="s">
      <div class="page-head" style="margin-top: 12px">
        <div>
          <div class="small muted">Tracking number</div>
          <h1 class="mono">{{ s.tracking_number }}</h1>
          <div class="muted">{{ s.description }} · {{ s.mode_display }}</div>
          <div class="lane">{{ s.origin_name }} → {{ s.destination_name }}</div>
        </div>
        <div class="head-right">
          <StatusBadge :status="s.status" :label="s.status_display" />
          <span class="badge" :class="{ green: s.payment_status === 'paid', amber: s.payment_status === 'unpaid' }">{{ s.payment_status_display }}</span>
          <strong>{{ money(s.charge_usd) }}</strong>
        </div>
      </div>
      <div v-if="saved" class="alert alert-success">{{ saved }}</div>
      <PartsNotice v-if="s.part" :part="s.part" base="/staff/shipments" />

      <div class="layout">
        <div>
          <form class="card" @submit.prevent="save">
            <h3>Loading &amp; billing</h3>
            <fieldset :disabled="!canChange">
              <div class="row">
                <div class="field"><label for="w">Weight (kg)</label><input id="w" v-model="form.weight_kg" type="number" step="0.01" min="0" /><div class="error">{{ err('weight_kg') }}</div></div>
                <div class="field"><label for="v">Volume (CBM)</label><input id="v" v-model="form.volume_cbm" type="number" step="0.001" min="0" /><div class="error">{{ err('volume_cbm') }}</div></div>
                <div class="field"><label for="pk">Packages loaded</label><input id="pk" v-model="form.packages_received" type="number" min="0" /></div>
              </div>
              <div class="row">
                <div class="field"><label for="c">Charge (USD)</label><input id="c" v-model="form.charge_usd" type="number" step="0.01" min="0" /><div class="error">{{ err('charge_usd') }}</div></div>
                <div class="field"><label for="ps">Payment</label><select id="ps" v-model="form.payment_status"><option v-for="p in PAYMENT_STATUSES" :key="p[0]" :value="p[0]">{{ p[1] }}</option></select></div>
                <div class="field"><label for="eta">ETA destination</label><input id="eta" v-model="form.eta_date" type="date" /></div>
              </div>
              <div class="field">
                <label for="b">Trip (truck)</label>
                <select v-if="auth.can('trips')" id="b" v-model="form.trip">
                  <option value="">Not on a truck yet</option>
                  <option v-if="form.trip && !trips.some((b) => b.code === form.trip)" :value="form.trip">{{ form.trip }}</option>
                  <option v-for="b in trips" :key="b.code" :value="b.code">{{ b.code }} · {{ b.origin_name }} → {{ b.destination_name }} · {{ b.status_display }}{{ b.is_backhaul ? ' · return leg' : '' }}{{ b.origin === s.origin && b.destination === s.destination ? ' ★ same lane' : '' }}</option>
                </select>
                <input v-else id="b" v-model="form.trip" placeholder="Trip code" />
                <div class="error">{{ err('trip') }}</div>
                <RouterLink v-if="s.trip_code" :to="`/staff/trips/${s.trip_code}`" class="small">Open trip {{ s.trip_code }} →</RouterLink>
              </div>
              <div class="field"><label for="n">Internal notes <span class="muted small">(staff only, never shown to the customer)</span></label><textarea id="n" v-model="form.internal_notes" maxlength="2000"></textarea></div>

              <details>
                <summary>Customer's declaration</summary>
                <div class="field" style="margin-top: 12px"><label for="d">Description</label><input id="d" v-model="form.description" maxlength="255" /></div>
                <div class="row">
                  <div class="field"><label for="cat">Category</label><select id="cat" v-model="form.category"><option v-for="c in CATEGORIES" :key="c[0]" :value="c[0]">{{ c[1] }}</option></select></div>
                  <div class="field"><label for="m">Load type</label><select id="m" v-model="form.mode"><option v-for="m in MODES" :key="m[0]" :value="m[0]">{{ m[1] }}</option></select></div>
                  <div class="field"><label for="q">Quantity</label><input id="q" v-model="form.quantity" type="number" min="1" /></div>
                </div>
                <div class="row">
                  <div class="field"><label for="st">Service</label><select id="st" v-model="form.service_type"><option value="consolidated">Shared truck</option><option value="dedicated">Dedicated truck</option></select></div>
                  <div class="field"><label for="dw">Declared weight (kg)</label><input id="dw" v-model="form.declared_weight_kg" type="number" step="0.1" min="0" /></div>
                  <div class="field"><label for="dv">Cargo value (USD)</label><input id="dv" v-model="form.declared_value_usd" type="number" step="0.01" min="0" /></div>
                </div>
                <div class="row">
                  <div class="field"><label for="or">From</label><PlaceSelect id="or" v-model="form.origin" :borders="false" /><div class="error">{{ err('origin') }}</div></div>
                  <div class="field"><label for="ds">To</label><PlaceSelect id="ds" v-model="form.destination" :borders="false" /><div class="error">{{ err('destination') }}</div></div>
                  <div class="field"><label for="pd">Pickup date</label><input id="pd" v-model="form.pickup_date" type="date" /></div>
                </div>
                <div class="field"><label for="pa">Pickup address</label><input id="pa" v-model="form.pickup_address" maxlength="255" /></div>
                <div class="row">
                  <div class="field"><label for="cn">Receiver</label><input id="cn" v-model="form.consignee_name" maxlength="120" /></div>
                  <div class="field"><label for="cp">Receiver phone</label><input id="cp" v-model="form.consignee_phone" maxlength="30" /></div>
                  <div class="field"><label for="do">Delivery</label><select id="do" v-model="form.delivery_option"><option value="pickup">Collect at depot</option><option value="delivery">Door delivery</option></select></div>
                </div>
                <div v-if="form.delivery_option === 'delivery'" class="field"><label for="da">Delivery address</label><input id="da" v-model="form.delivery_address" maxlength="255" /></div>
                <label class="checkbox"><input v-model="form.is_hazardous" type="checkbox" /> Hazardous</label>
                <label class="checkbox"><input v-model="form.is_fragile" type="checkbox" /> Fragile</label>
                <p v-if="s.customer_notes" class="small muted" style="margin-top: 12px">Customer notes: {{ s.customer_notes }}</p>
              </details>
            </fieldset>
            <button v-if="canChange" class="btn btn-dark" :disabled="saving" style="margin-top: 16px">{{ saving ? 'Saving…' : 'Save changes' }}</button>
          </form>
        </div>

        <div>
          <div class="card">
            <h3>Customer</h3>
            <p style="margin: 0">
              <strong>{{ s.owner.full_name }}</strong> · <span class="mono">{{ s.owner.customer_code }}</span><br />
              <a :href="`mailto:${s.owner.email}`">{{ s.owner.email }}</a><br />
              <a v-if="s.owner.phone" :href="`tel:${s.owner.phone}`">{{ s.owner.phone }}</a>
            </p>
            <RouterLink v-if="auth.can('users')" :to="`/staff/users/${s.owner.customer_code}`" class="small">View customer →</RouterLink>
          </div>

          <div v-if="canSplit" class="card" style="margin-top: 20px">
            <h3>Split across trucks</h3>
            <p class="small muted">Send some of these {{ spHave }} packages on a different truck, e.g. when this one is full. Weight, volume and charge you enter move to the new part. The customer sees it as "Part 2 of 2"; they never see other customers' cargo.</p>
            <button v-if="!sp.open" class="btn btn-outline btn-block" @click="sp.open = true">Split booking…</button>
            <form v-else @submit.prevent="split">
              <div class="row">
                <div class="field"><label for="sp-p">Packages to move</label><input id="sp-p" v-model="sp.packages" type="number" min="1" :max="spHave - 1" required /><div class="error">{{ spErr('packages') }}</div></div>
                <div class="field"><label for="sp-m">Load type</label>
                  <select id="sp-m" v-model="sp.mode"><option value="">Same ({{ s.mode_display }})</option><option v-for="m in MODES" :key="m[0]" :value="m[0]">{{ m[1] }}</option></select>
                </div>
              </div>
              <div class="row">
                <div class="field"><label for="sp-w">Weight kg</label><input id="sp-w" v-model="sp.weight_kg" type="number" step="0.01" min="0" :max="s.weight_kg" /><div class="error">{{ spErr('weight_kg') }}</div></div>
                <div class="field"><label for="sp-v">Volume CBM</label><input id="sp-v" v-model="sp.volume_cbm" type="number" step="0.001" min="0" :max="s.volume_cbm" /><div class="error">{{ spErr('volume_cbm') }}</div></div>
                <div class="field"><label for="sp-c">Charge USD</label><input id="sp-c" v-model="sp.charge_usd" type="number" step="0.01" min="0" :max="s.charge_usd" /><div class="error">{{ spErr('charge_usd') }}</div></div>
              </div>
              <div class="field"><label for="sp-b">Put on trip <span class="muted small">(optional)</span></label>
                <select id="sp-b" v-model="sp.trip"><option value="">Decide later</option><option v-for="b in spTrips" :key="b.code" :value="b.code">{{ b.code }} · {{ b.origin_name }} → {{ b.destination_name }}</option></select>
                <div class="error">{{ spErr('trip') }}</div>
              </div>
              <div v-if="sp.err && !Object.keys(sp.errors).length" class="alert alert-error">{{ sp.err }}</div>
              <div v-else-if="spErr('detail') || spErr('non_field_errors')" class="alert alert-error">{{ spErr('detail') || spErr('non_field_errors') }}</div>
              <div style="display: flex; gap: 8px">
                <button class="btn btn-primary" :disabled="sp.busy">{{ sp.busy ? 'Splitting…' : 'Create part' }}</button>
                <button type="button" class="btn btn-outline" @click="sp.open = false">Cancel</button>
              </div>
            </form>
          </div>

          <form v-if="canChange" class="card" style="margin-top: 20px" @submit.prevent="changeStatus">
            <h3>Update status</h3>
            <div class="field"><label for="ns">New status</label><select id="ns" v-model="st.status"><option v-for="x in STATUSES" :key="x[0]" :value="x[0]">{{ x[1] }}</option></select></div>
            <div class="field"><label for="loc">Location <span class="muted small">(optional; a default is used)</span></label><input id="loc" v-model="st.location" maxlength="120" placeholder="e.g. Malaba border" /></div>
            <div class="field"><label for="note">Note for the customer <span class="muted small">(optional)</span></label><input id="note" v-model="st.note" maxlength="255" placeholder="e.g. Quote accepted, loading Thursday" /></div>
            <button class="btn btn-primary btn-block" :disabled="stBusy || (st.status === s.status && !st.note)">{{ stBusy ? 'Updating…' : 'Add update' }}</button>
          </form>

          <div class="card" style="margin-top: 20px">
            <h3>Timeline</h3>
            <ol class="timeline">
              <li v-for="e in s.events" :key="e.id">
                <strong>{{ e.status_display }}</strong>
                <div class="small muted">{{ dateTime(e.created_at) }}<template v-if="e.location"> · {{ e.location }}</template></div>
                <div v-if="e.note" class="small">{{ e.note }}</div>
                <div v-if="e.created_by_name" class="small muted">by {{ e.created_by_name }}</div>
              </li>
            </ol>
            <p class="small muted" style="margin: 8px 0 0">Created {{ date(s.created_at) }}<template v-if="s.received_at"> · loaded {{ date(s.received_at) }}</template><template v-if="s.delivered_at"> · delivered {{ date(s.delivered_at) }}</template></p>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.page-head h1 { font-size: 1.6rem; }
.lane { font-weight: 700; color: var(--navy); margin-top: 4px; }
.head-right { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.layout { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr); gap: 20px; align-items: start; }
fieldset { border: 0; padding: 0; margin: 0; min-width: 0; }
details summary { cursor: pointer; font-weight: 600; color: var(--navy); }
.timeline { list-style: none; padding: 0; margin: 0; }
.timeline li { padding: 10px 0 10px 16px; border-left: 2px solid var(--border); position: relative; }
.timeline li::before { content: ''; position: absolute; left: -6px; top: 15px; width: 10px; height: 10px; border-radius: 50%; background: var(--border); }
.timeline li:first-child::before { background: var(--amber); }
@media (max-width: 900px) { .layout { grid-template-columns: 1fr; } }
</style>
