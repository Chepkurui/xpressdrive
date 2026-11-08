<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api, ApiError } from '@/api/client'
import { ago, TRUCK_TYPES } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import StaffNav from '@/components/StaffNav.vue'
import PlaceSelect from '@/components/PlaceSelect.vue'

const auth = useAuthStore()
const canAddTruck = computed(() => auth.can('trucks', 'add'))
const canChangeTruck = computed(() => auth.can('trucks', 'change'))
const seeDrivers = computed(() => auth.can('users'))
const drivers = ref([])
const trucks = ref([])
const error = ref('')
const msg = ref('')
const editing = ref(null) // truck id, 'new' or null
const blank = { plate_number: '', trailer_plate: '', truck_type: 'flatbed', make_model: '', capacity_kg: '', capacity_cbm: '', home_base: '', default_driver: '', owner_name: '', owner_phone: '', is_active: true, notes: '' }
const tf = reactive({ ...blank })
const tfErr = ref({})

async function load() {
  error.value = ''
  try {
    const [d, t] = await Promise.all([
      seeDrivers.value ? api('/staff/drivers/', { query: { active: 'all' } }) : Promise.resolve([]),
      api('/staff/trucks/', { query: { page_size: 100 } }),
    ])
    drivers.value = d
    trucks.value = t.results
  } catch (e) {
    error.value = e.message
  }
}
onMounted(load)

function edit(t) {
  tfErr.value = {}
  editing.value = t ? t.id : 'new'
  Object.assign(tf, blank, t ? { ...t, default_driver: t.default_driver || '', capacity_kg: t.capacity_kg ?? '', capacity_cbm: t.capacity_cbm ?? '' } : {})
}
async function saveTruck() {
  tfErr.value = {}
  const body = Object.fromEntries(Object.keys(blank).map((k) => [k, tf[k]]))
  for (const k of ['capacity_kg', 'capacity_cbm', 'default_driver']) if (body[k] === '') body[k] = null
  try {
    if (editing.value === 'new') await api('/staff/trucks/', { method: 'POST', body })
    else await api(`/staff/trucks/${editing.value}/`, { method: 'PATCH', body })
    msg.value = `Truck ${tf.plate_number.toUpperCase()} saved.`
    editing.value = null
    await load()
  } catch (e) {
    if (e instanceof ApiError && e.status === 400) tfErr.value = Object.fromEntries(Object.keys(e.data).map((k) => [k, e.field(k)]))
    else tfErr.value = { detail: e.message }
  }
}
</script>

<template>
  <section class="container" style="padding-top: 32px">
    <StaffNav />
    <h1 style="font-size: 1.8rem">Drivers &amp; trucks</h1>
    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="msg" class="alert alert-success">{{ msg }}</div>

    <div v-if="seeDrivers" class="card" style="margin-bottom: 20px">
      <div class="page-head" style="margin-bottom: 8px">
        <h3 style="margin: 0">Drivers</h3>
        <span class="small muted">To add a driver, have them create an account (or find them under <RouterLink :to="{ path: '/staff/users' }">People</RouterLink>) and switch on “Driver”.</span>
      </div>
      <div v-if="!drivers.length" class="empty">No drivers yet.</div>
      <div v-else class="table-wrap">
        <table>
          <thead><tr><th>Driver</th><th>Phone</th><th>Licence</th><th>Trucks</th><th>Now</th></tr></thead>
          <tbody>
            <tr v-for="d in drivers" :key="d.customer_code" :class="{ off: !d.is_active }">
              <td><RouterLink :to="`/staff/users/${d.customer_code}`">{{ d.full_name }}</RouterLink><div class="small muted">{{ d.email }}</div></td>
              <td class="small"><a v-if="d.phone" :href="`tel:${d.phone}`">{{ d.phone }}</a></td>
              <td class="small mono">{{ d.licence_number || '—' }}</td>
              <td class="small">{{ d.trucks.map((x) => x.plate_number).join(', ') || '—' }}</td>
              <td class="small">
                <template v-if="!d.is_active"><span class="badge red">Deactivated</span></template>
                <template v-else-if="d.current_trip">
                  <RouterLink :to="`/staff/trips/${d.current_trip.code}`" class="mono">{{ d.current_trip.code }}</RouterLink> · {{ d.current_trip.status_display }}
                  <div v-if="d.current_trip.last_position_at" class="muted">📍 {{ ago(d.current_trip.last_position_at) }}</div>
                </template>
                <span v-else class="badge green">Available</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="card">
      <div class="page-head" style="margin-bottom: 8px">
        <h3 style="margin: 0">Trucks</h3>
        <button v-if="canAddTruck && editing !== 'new'" class="btn btn-primary btn-sm" @click="edit(null)">+ Add truck</button>
      </div>
      <form v-if="editing" class="card flat editor" @submit.prevent="saveTruck">
        <h4>{{ editing === 'new' ? 'New truck' : `Edit ${tf.plate_number}` }}</h4>
        <div class="row">
          <div class="field"><label for="pl">Plate number</label><input id="pl" v-model="tf.plate_number" maxlength="20" required /><div class="error">{{ tfErr.plate_number }}</div></div>
          <div class="field"><label for="tp">Trailer plate</label><input id="tp" v-model="tf.trailer_plate" maxlength="20" /></div>
          <div class="field"><label for="tt">Type</label><select id="tt" v-model="tf.truck_type"><option v-for="x in TRUCK_TYPES" :key="x[0]" :value="x[0]">{{ x[1] }}</option></select></div>
          <div class="field"><label for="mm">Make / model</label><input id="mm" v-model="tf.make_model" maxlength="80" /></div>
        </div>
        <div class="row">
          <div class="field"><label for="ckg">Capacity (kg)</label><input id="ckg" v-model="tf.capacity_kg" type="number" min="0" step="0.01" /></div>
          <div class="field"><label for="ccb">Capacity (CBM)</label><input id="ccb" v-model="tf.capacity_cbm" type="number" min="0" step="0.001" /></div>
          <div class="field"><label for="hb">Home base</label><PlaceSelect id="hb" v-model="tf.home_base" :borders="false" placeholder="—" /></div>
          <div class="field"><label for="dd">Usual driver</label>
            <select id="dd" v-model="tf.default_driver"><option value="">—</option><option v-for="d in drivers.filter((x) => x.is_active)" :key="d.customer_code" :value="d.customer_code">{{ d.full_name }}</option></select>
          </div>
        </div>
        <div class="row">
          <div class="field"><label for="on">Transporter / owner</label><input id="on" v-model="tf.owner_name" maxlength="120" /></div>
          <div class="field"><label for="op">Owner phone</label><input id="op" v-model="tf.owner_phone" maxlength="30" /></div>
          <div class="field" style="align-self: end"><label class="checkbox"><input v-model="tf.is_active" type="checkbox" /> In service</label></div>
        </div>
        <div class="field"><label for="tn">Notes</label><textarea id="tn" v-model="tf.notes"></textarea></div>
        <div v-if="tfErr.detail" class="alert alert-error">{{ tfErr.detail }}</div>
        <div style="display: flex; gap: 8px"><button class="btn btn-dark">Save truck</button><button type="button" class="btn btn-outline" @click="editing = null">Cancel</button></div>
      </form>
      <div v-if="!trucks.length" class="empty">No trucks registered yet.</div>
      <div v-else class="table-wrap">
        <table>
          <thead><tr><th>Plate</th><th>Type</th><th>Capacity</th><th>Base</th><th>Usual driver</th><th>Owner</th><th></th></tr></thead>
          <tbody>
            <tr v-for="t in trucks" :key="t.id" :class="{ off: !t.is_active }">
              <td class="mono"><strong>{{ t.plate_number }}</strong><div v-if="t.trailer_plate" class="small muted">{{ t.trailer_plate }}</div></td>
              <td class="small">{{ t.truck_type_display }}<div class="muted">{{ t.make_model }}</div></td>
              <td class="small">{{ t.capacity_kg ? `${Number(t.capacity_kg).toLocaleString()} kg` : '—' }}<div v-if="t.capacity_cbm" class="muted">{{ t.capacity_cbm }} CBM</div></td>
              <td class="small">{{ t.home_base_name || '—' }}</td>
              <td class="small">{{ t.default_driver_detail?.full_name || '—' }}</td>
              <td class="small">{{ t.owner_name || '—' }}</td>
              <td><button v-if="canChangeTruck" class="btn btn-outline btn-sm" @click="edit(t)">Edit</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

<style scoped>
.editor { margin: 12px 0 20px; background: var(--bg); }
.editor h4 { margin: 0 0 12px; }
tr.off td { opacity: 0.55; }
</style>
