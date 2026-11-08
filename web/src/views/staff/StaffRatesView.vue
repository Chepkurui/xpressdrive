<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api, ApiError } from '@/api/client'
import { dateTime } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import StaffNav from '@/components/StaffNav.vue'
import PlaceSelect from '@/components/PlaceSelect.vue'

// Buttons follow BOTH the staff member's role and their sign-in token's scope
// (the API enforces the same rule on every request).
const auth = useAuthStore()
const canChange = computed(() => auth.can('rates', 'change'))
const canAdd = computed(() => auth.can('rates', 'add'))
const canDelete = computed(() => auth.can('rates', 'delete'))

const rates = ref(null)
const error = ref('')
const state = ref({}) // per-plan { busy, msg, err, errors }

const MODES = [
  { value: 'parcel', label: 'Parcel / small goods', basis: 'per_kg' },
  { value: 'part_load', label: 'Part load (shared truck)', basis: 'per_cbm' },
  { value: 'full_truck', label: 'Full truck load', basis: 'per_container' },
  { value: 'container_20', label: '20ft container', basis: 'per_container' },
  { value: 'container_40', label: '40ft container', basis: 'per_container' },
]
const UNIT = { per_kg: 'per kg', per_cbm: 'per CBM', per_container: 'per truck / container' }
const FIELDS = ['name', 'origin', 'destination', 'price_usd', 'min_charge_usd', 'transit_days_min', 'transit_days_max', 'summary', 'best_for', 'is_active', 'sort_order']

async function load() {
  try {
    rates.value = (await api('/staff/rates/')).map((r) => ({ ...r }))
  } catch (e) {
    error.value = e.message
  }
}
onMounted(load)

async function save(r) {
  state.value[r.code] = { busy: true }
  const body = Object.fromEntries(FIELDS.map((k) => [k, r[k]]))
  try {
    Object.assign(r, await api(`/staff/rates/${r.code}/`, { method: 'PATCH', body }))
    state.value[r.code] = { msg: 'Saved. The public pricing page now shows this.' }
  } catch (e) {
    state.value[r.code] = { errors: e instanceof ApiError ? e.data : {}, err: e.message }
  }
}

async function remove(r) {
  if (!confirm(`Delete the plan "${r.name}"? It disappears from the pricing page and estimator. Existing bookings are not affected.`)) return
  state.value[r.code] = { busy: true }
  try {
    await api(`/staff/rates/${r.code}/`, { method: 'DELETE' })
    rates.value = rates.value.filter((x) => x.code !== r.code)
  } catch (e) {
    state.value[r.code] = { err: e.message }
  }
}

// ---- add a plan
const adding = ref(false)
const blank = () => ({ name: '', code: '', mode: 'part_load', origin: '', destination: '', price_usd: '', min_charge_usd: '0', transit_days_min: '', transit_days_max: '', summary: '', best_for: '', is_active: true })
const draft = reactive(blank())
const addState = ref({})
const draftUnit = computed(() => UNIT[MODES.find((m) => m.value === draft.mode)?.basis])

async function create() {
  addState.value = { busy: true }
  const body = { ...draft }
  if (!body.code) delete body.code // server makes one from the name
  try {
    const plan = await api('/staff/rates/', { method: 'POST', body })
    rates.value.push(plan)
    Object.assign(draft, blank())
    adding.value = false
    addState.value = {}
    state.value[plan.code] = { msg: 'Plan added. It is live on the pricing page.' }
  } catch (e) {
    addState.value = { errors: e instanceof ApiError ? e.data : {}, err: e.message }
  }
}

const pick = (v) => (Array.isArray(v) ? v.join(' ') : v || '')
const err = (code, k) => pick(state.value[code]?.errors?.[k])
const addErr = (k) => pick(addState.value.errors?.[k])
</script>

<template>
  <section class="container" style="padding-top: 32px">
    <StaffNav />
    <div class="page-head">
      <h1>Pricing plans</h1>
      <button v-if="canAdd && !adding" class="btn btn-primary" @click="adding = true">+ Add plan</button>
    </div>
    <p class="muted">Plans power the public pricing page and the cost estimator. You can offer several plans per load type, optionally for one lane (for example "Mombasa → Kampala, 40ft" or a cheaper return-leg rate). Changes apply immediately.</p>
    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="!rates && !error" class="spinner"></div>

    <form v-if="adding" class="card new" @submit.prevent="create">
      <div class="head"><h3 style="margin: 0">New pricing plan</h3></div>
      <div class="row">
        <div class="field"><label for="n-name">Plan name</label><input id="n-name" v-model="draft.name" maxlength="80" required placeholder="e.g. 40ft — Mombasa to Kampala" /><div class="error">{{ addErr('name') }}</div></div>
        <div class="field"><label for="n-mode">Load type</label>
          <select id="n-mode" v-model="draft.mode"><option v-for="m in MODES" :key="m.value" :value="m.value">{{ m.label }}</option></select>
          <div class="error">{{ addErr('mode') }}</div>
        </div>
      </div>
      <div class="row">
        <div class="field"><label for="n-o">From <span class="muted small">(blank = any)</span></label><PlaceSelect id="n-o" v-model="draft.origin" placeholder="Any route" /></div>
        <div class="field"><label for="n-d">To <span class="muted small">(blank = any)</span></label><PlaceSelect id="n-d" v-model="draft.destination" placeholder="Any route" /></div>
      </div>
      <div class="row">
        <div class="field"><label for="n-price">Price (USD {{ draftUnit }})</label><input id="n-price" v-model="draft.price_usd" type="number" step="0.01" min="0" required /><div class="error">{{ addErr('price_usd') }}</div></div>
        <div class="field"><label for="n-min">Minimum charge (USD)</label><input id="n-min" v-model="draft.min_charge_usd" type="number" step="0.01" min="0" /></div>
      </div>
      <div class="row">
        <div class="field"><label for="n-a">Transit days (min)</label><input id="n-a" v-model.number="draft.transit_days_min" type="number" min="0" required /></div>
        <div class="field"><label for="n-b">Transit days (max)</label><input id="n-b" v-model.number="draft.transit_days_max" type="number" min="0" required /><div class="error">{{ addErr('transit_days_max') }}</div></div>
      </div>
      <div class="field"><label for="n-sum">Summary</label><input id="n-sum" v-model="draft.summary" maxlength="200" required /><div class="error">{{ addErr('summary') }}</div></div>
      <div class="field"><label for="n-best">Best for</label><input id="n-best" v-model="draft.best_for" maxlength="200" /></div>
      <div class="row">
        <div class="field"><label for="n-code">Code <span class="muted small">(optional, permanent)</span></label><input id="n-code" v-model="draft.code" class="mono" maxlength="40" pattern="[a-z0-9_-]+" placeholder="made from the name" /><div class="error">{{ addErr('code') }}</div></div>
        <div class="field"><label class="checkbox" style="margin-top: 30px"><input v-model="draft.is_active" type="checkbox" /> Offer immediately</label></div>
      </div>
      <div v-if="addState.err && !addState.errors" class="alert alert-error">{{ addState.err }}</div>
      <div class="actions">
        <button class="btn btn-primary" :disabled="addState.busy">{{ addState.busy ? 'Adding…' : 'Add plan' }}</button>
        <button type="button" class="btn btn-outline" @click="adding = false; addState = {}">Cancel</button>
      </div>
    </form>

    <div v-if="rates" class="grid grid-2">
      <form v-for="r in rates" :key="r.code" class="card" :class="{ off: !r.is_active }" @submit.prevent="save(r)">
        <div class="head">
          <span class="badge">{{ r.mode_display }}</span>
          <span v-if="r.route_display" class="badge blue">{{ r.route_display }}</span>
          <label class="checkbox small"><input v-model="r.is_active" type="checkbox" :disabled="!canChange" /> Offered</label>
        </div>
        <p class="small muted" style="margin: 8px 0 12px"><span class="mono">{{ r.code }}</span> · {{ r.basis_display }} · updated {{ dateTime(r.updated_at) }}</p>
        <fieldset :disabled="!canChange">
          <div class="field"><label :for="`n-${r.code}`">Plan name</label><input :id="`n-${r.code}`" v-model="r.name" maxlength="80" required /><div class="error">{{ err(r.code, 'name') }}</div></div>
          <div class="row">
            <div class="field"><label :for="`o-${r.code}`">From</label><PlaceSelect :id="`o-${r.code}`" v-model="r.origin" placeholder="Any route" /></div>
            <div class="field"><label :for="`d-${r.code}`">To</label><PlaceSelect :id="`d-${r.code}`" v-model="r.destination" placeholder="Any route" /></div>
          </div>
          <div class="row">
            <div class="field"><label :for="`p-${r.code}`">Price (USD {{ UNIT[r.basis] }})</label><input :id="`p-${r.code}`" v-model="r.price_usd" type="number" step="0.01" min="0" required /><div class="error">{{ err(r.code, 'price_usd') }}</div></div>
            <div class="field"><label :for="`m-${r.code}`">Minimum charge (USD)</label><input :id="`m-${r.code}`" v-model="r.min_charge_usd" type="number" step="0.01" min="0" /></div>
          </div>
          <div class="row">
            <div class="field"><label :for="`a-${r.code}`">Transit days (min)</label><input :id="`a-${r.code}`" v-model.number="r.transit_days_min" type="number" min="0" /></div>
            <div class="field"><label :for="`b-${r.code}`">Transit days (max)</label><input :id="`b-${r.code}`" v-model.number="r.transit_days_max" type="number" min="0" /><div class="error">{{ err(r.code, 'transit_days_max') }}</div></div>
          </div>
          <div class="field"><label :for="`s-${r.code}`">Summary</label><input :id="`s-${r.code}`" v-model="r.summary" maxlength="200" /></div>
          <div class="row">
            <div class="field"><label :for="`f-${r.code}`">Best for</label><input :id="`f-${r.code}`" v-model="r.best_for" maxlength="200" /></div>
            <div class="field"><label :for="`o-${r.code}`">Display order</label><input :id="`o-${r.code}`" v-model.number="r.sort_order" type="number" min="0" /></div>
          </div>
        </fieldset>
        <div v-if="state[r.code]?.msg" class="alert alert-success">{{ state[r.code].msg }}</div>
        <div v-if="state[r.code]?.err" class="alert alert-error">{{ state[r.code].err }}</div>
        <div class="actions">
          <button v-if="canChange" class="btn btn-dark" :disabled="state[r.code]?.busy">{{ state[r.code]?.busy ? 'Saving…' : 'Save' }}</button>
          <button v-if="canDelete" type="button" class="btn btn-danger" :disabled="state[r.code]?.busy" @click="remove(r)">Delete</button>
        </div>
      </form>
    </div>
  </section>
</template>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.head .checkbox { margin: 0; }
.off { opacity: 0.7; }
.new { margin-bottom: 24px; border-color: var(--amber); }
.actions { display: flex; gap: 10px; flex-wrap: wrap; }
fieldset { border: 0; padding: 0; margin: 0; min-width: 0; }
</style>
