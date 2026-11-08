<script setup>
import { reactive, ref, computed, watch } from 'vue'
import { api, ApiError } from '@/api/client'
import { money, days } from '@/utils/format'

const props = defineProps({ rates: { type: Array, default: () => [] } })
const form = reactive({ plan: '', weight_kg: '', quantity: 1, length_cm: '', width_cm: '', height_cm: '', containers: 1 })
// Default to the part-load plan (or the first plan) once the rate card loads.
watch(() => props.rates, (rates) => {
  if (!rates.length || rates.some((r) => r.code === form.plan)) return
  form.plan = (rates.find((r) => r.mode === 'part_load') || rates[0]).code
}, { immediate: true })
const selected = computed(() => props.rates.find((r) => r.code === form.plan))
const result = ref(null)
const error = ref('')
const loading = ref(false)
const isFcl = computed(() => selected.value?.basis === 'per_container')
const needsDims = computed(() => selected.value?.basis === 'per_cbm')

async function submit() {
  error.value = ''
  result.value = null
  loading.value = true
  const body = { plan: form.plan, weight_kg: form.weight_kg || '1', quantity: form.quantity || 1, containers: form.containers || 1 }
  for (const k of ['length_cm', 'width_cm', 'height_cm']) if (form[k] !== '') body[k] = form[k]
  try {
    result.value = await api('/rates/estimate/', { method: 'POST', body, auth: false })
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Could not calculate an estimate. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="card calc">
    <h3>Quick cost estimate</h3>
    <form @submit.prevent="submit">
      <div class="field">
        <label for="mode">Load type</label>
        <select id="mode" v-model="form.plan">
          <option v-for="r in props.rates" :key="r.code" :value="r.code">{{ r.name }}{{ r.route_display ? ` (${r.route_display})` : '' }}</option>
        </select>
      </div>
      <template v-if="isFcl">
        <div class="field">
          <label for="containers">Number of trucks / containers</label>
          <input id="containers" v-model.number="form.containers" type="number" min="1" max="50" required />
        </div>
      </template>
      <template v-else>
        <div class="row">
          <div class="field">
            <label for="w">Weight per package (kg)</label>
            <input id="w" v-model="form.weight_kg" type="number" min="0.01" step="0.01" required />
          </div>
          <div class="field">
            <label for="q">No. of packages</label>
            <input id="q" v-model.number="form.quantity" type="number" min="1" max="10000" required />
          </div>
        </div>
        <label>Package size (cm) <span class="muted small">{{ needsDims ? '— required for part loads' : '— optional, for volumetric weight' }}</span></label>
        <div class="row">
          <input v-model="form.length_cm" type="number" min="1" max="1500" placeholder="Length" :required="needsDims" aria-label="Length in cm" />
          <input v-model="form.width_cm" type="number" min="1" max="1500" placeholder="Width" :required="needsDims" aria-label="Width in cm" />
          <input v-model="form.height_cm" type="number" min="1" max="1500" placeholder="Height" :required="needsDims" aria-label="Height in cm" />
        </div>
      </template>
      <button class="btn btn-primary btn-block" style="margin-top: 16px" :disabled="loading">
        {{ loading ? 'Calculating…' : 'Estimate cost' }}
      </button>
    </form>

    <div v-if="error" class="alert alert-error" style="margin-top: 16px">{{ error }}</div>
    <div v-if="result" class="result">
      <div class="muted small">Estimated freight cost</div>
      <div class="price">{{ money(result.cost_low_usd) }} – {{ money(result.cost_high_usd) }}</div>
      <div class="small">
        Chargeable: <strong>{{ result.chargeable_quantity }} {{ result.chargeable_unit }}</strong>
        <span v-if="result.volumetric_weight_kg"> (actual {{ result.actual_weight_kg }} kg, volumetric {{ result.volumetric_weight_kg }} kg)</span>
        <span v-else-if="result.volume_cbm"> ({{ result.volume_cbm }} CBM)</span>
      </div>
      <div class="small">Transit time: <strong>{{ days(result.transit_days_min, result.transit_days_max) }}</strong> from loading</div>
      <p class="small muted" style="margin-top: 10px">{{ result.disclaimer }}</p>
    </div>
  </div>
</template>

<style scoped>
.result { margin-top: 20px; padding: 16px; border-radius: 10px; background: #fff6ec; border: 1px solid #ffd2a6; }
.price { font-size: 1.7rem; font-weight: 800; color: var(--navy); margin: 4px 0 8px; }
</style>
