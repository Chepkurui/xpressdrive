<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, ApiError } from '@/api/client'
import { CATEGORIES, MODES, MODE_HINTS } from '@/utils/format'
import AccountNav from '@/components/AccountNav.vue'
import PlaceSelect from '@/components/PlaceSelect.vue'

const route = useRoute()
const router = useRouter()
const editing = computed(() => !!route.params.number)
const form = reactive({
  origin: '', destination: '', pickup_address: '', pickup_date: '',
  description: '', category: 'general', mode: 'part_load', service_type: 'consolidated', quantity: 1,
  declared_weight_kg: '', declared_value_usd: '', is_hazardous: false, is_fragile: false,
  consignee_name: '', consignee_phone: '', delivery_option: 'pickup', delivery_address: '', customer_notes: '',
})
// Prefill a lane from the return-truck board (?origin=&destination=&mode=)
for (const k of ['origin', 'destination', 'mode']) if (typeof route.query[k] === 'string') form[k] = route.query[k]
const fullLoad = computed(() => ['full_truck', 'container_20', 'container_40'].includes(form.mode))
const errors = ref({})
const error = ref('')
const loading = ref(false)
const today = new Date().toISOString().slice(0, 10)

onMounted(async () => {
  if (!editing.value) return
  try {
    const s = await api(`/shipments/${encodeURIComponent(route.params.number)}/`)
    if (!s.is_editable) return router.replace(`/account/shipments/${s.tracking_number}`)
    for (const k of Object.keys(form)) form[k] = s[k] ?? form[k]
  } catch {
    error.value = 'Could not load this booking.'
  }
})

async function submit() {
  errors.value = {}
  error.value = ''
  loading.value = true
  const nullable = ['declared_value_usd', 'declared_weight_kg', 'pickup_date']
  const body = { ...form, service_type: fullLoad.value ? 'dedicated' : form.service_type }
  for (const k of nullable) if (body[k] === '') body[k] = null
  try {
    const s = editing.value
      ? await api(`/shipments/${encodeURIComponent(route.params.number)}/`, { method: 'PATCH', body })
      : await api('/shipments/', { method: 'POST', body })
    router.push(`/account/shipments/${s.tracking_number}`)
  } catch (e) {
    if (e instanceof ApiError && e.status === 400) {
      errors.value = Object.fromEntries(Object.keys(e.data).map((k) => [k, e.field(k)]))
      error.value = e.data.detail || 'Please correct the highlighted fields.'
    } else error.value = 'Could not save. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="container" style="padding-top: 32px">
    <AccountNav />
    <div style="max-width: 860px">
      <h1 style="font-size: 1.8rem">{{ editing ? 'Edit booking' : 'Book a truck' }}</h1>
      <p class="muted">Tell us what you're moving and where. We'll quote you, then match your cargo with a truck heading that way, often one on its way back to base. You can change the booking until we confirm it.</p>
      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <form class="card" @submit.prevent="submit">
        <h3>Route</h3>
        <div class="row">
          <div class="field"><label for="o">From</label><PlaceSelect id="o" v-model="form.origin" required :borders="false" /><div class="error">{{ errors.origin }}</div></div>
          <div class="field"><label for="de">To</label><PlaceSelect id="de" v-model="form.destination" required :borders="false" /><div class="error">{{ errors.destination }}</div></div>
          <div class="field"><label for="pd">Ready for pickup on</label><input id="pd" v-model="form.pickup_date" type="date" :min="today" /></div>
        </div>
        <div class="field"><label for="pa">Pickup address <span class="muted small">(warehouse, shop, port or ICD)</span></label><input id="pa" v-model="form.pickup_address" maxlength="255" placeholder="e.g. Plot 12 Industrial Area, Kampala" /></div>

        <h3>Cargo</h3>
        <fieldset class="modes">
          <legend class="sr">Load type</legend>
          <label v-for="m in MODES" :key="m[0]" class="mode" :class="{ on: form.mode === m[0] }">
            <input v-model="form.mode" type="radio" name="mode" :value="m[0]" />
            <strong>{{ m[1] }}</strong>
            <span class="small muted">{{ MODE_HINTS[m[0]] }}</span>
          </label>
        </fieldset>
        <div class="field">
          <label for="d">What are you moving?</label>
          <input id="d" v-model="form.description" maxlength="255" placeholder="e.g. 200 bags of maize flour, 25 kg each" required />
          <div class="error">{{ errors.description }}</div>
        </div>
        <div class="row">
          <div class="field"><label for="c">Category</label><select id="c" v-model="form.category"><option v-for="c in CATEGORIES" :key="c[0]" :value="c[0]">{{ c[1] }}</option></select></div>
          <div class="field"><label for="q">{{ fullLoad ? 'Number of trucks / containers' : 'Packages / pallets' }}</label><input id="q" v-model.number="form.quantity" type="number" min="1" max="10000" required /><div class="error">{{ errors.quantity }}</div></div>
          <div class="field"><label for="w">Total weight (kg)</label><input id="w" v-model="form.declared_weight_kg" type="number" min="0.1" step="0.1" /><div class="error">{{ errors.declared_weight_kg }}</div></div>
          <div class="field"><label for="v">Cargo value (USD)</label><input id="v" v-model="form.declared_value_usd" type="number" min="0" step="0.01" /><div class="error">{{ errors.declared_value_usd }}</div></div>
        </div>
        <div v-if="!fullLoad" class="field">
          <label for="st">Service</label>
          <select id="st" v-model="form.service_type">
            <option value="consolidated">Shared truck: travel with other cargo (cheaper)</option>
            <option value="dedicated">Dedicated truck: only my cargo</option>
          </select>
        </div>
        <div class="field" style="display: flex; gap: 24px; flex-wrap: wrap">
          <label class="checkbox"><input v-model="form.is_fragile" type="checkbox" /> Fragile</label>
          <label class="checkbox"><input v-model="form.is_hazardous" type="checkbox" /> Hazardous (fuel, chemicals, gas, batteries)</label>
        </div>

        <h3>Receiver</h3>
        <div class="row">
          <div class="field"><label for="cn">Receiver name</label><input id="cn" v-model="form.consignee_name" maxlength="120" /></div>
          <div class="field"><label for="cp">Receiver phone</label><input id="cp" v-model="form.consignee_phone" type="tel" maxlength="30" placeholder="+243 …" /><div class="error">{{ errors.consignee_phone }}</div></div>
        </div>
        <div class="row">
          <div class="field">
            <label for="do">At the destination</label>
            <select id="do" v-model="form.delivery_option">
              <option value="pickup">Receiver collects from our depot</option>
              <option value="delivery">Deliver to the receiver's address</option>
            </select>
          </div>
          <div v-if="form.delivery_option === 'delivery'" class="field">
            <label for="da">Delivery address</label>
            <input id="da" v-model="form.delivery_address" maxlength="255" required />
            <div class="error">{{ errors.delivery_address }}</div>
          </div>
        </div>
        <div class="field"><label for="n">Notes for our team <span class="muted small">(loading equipment, opening hours, border agent…)</span></label><textarea id="n" v-model="form.customer_notes" maxlength="1000"></textarea></div>
        <button class="btn btn-primary" :disabled="loading">{{ loading ? 'Saving…' : editing ? 'Save changes' : 'Request booking' }}</button>
      </form>
    </div>
  </section>
</template>

<style scoped>
h3 { font-size: 1.05rem; margin: 8px 0 12px; }
h3:not(:first-child) { margin-top: 24px; padding-top: 20px; border-top: 1px solid var(--border); }
.modes { border: 0; padding: 0; margin: 0 0 16px; display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
.mode { display: flex; flex-direction: column; gap: 4px; padding: 12px; border: 1px solid var(--border); border-radius: 10px; cursor: pointer; font-weight: 400; margin: 0; }
.mode input { position: absolute; opacity: 0; pointer-events: none; }
.mode.on { border-color: var(--amber); box-shadow: 0 0 0 2px var(--amber) inset; }
.mode:focus-within { outline: 2px solid var(--blue); outline-offset: 2px; }
.sr { position: absolute; left: -9999px; }
</style>
