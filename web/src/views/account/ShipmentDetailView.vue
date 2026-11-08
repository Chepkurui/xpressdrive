<script setup>
import PartsNotice from '@/components/PartsNotice.vue'
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api, ApiError } from '@/api/client'
import { money, date, dateTime } from '@/utils/format'
import AccountNav from '@/components/AccountNav.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import ProgressSteps from '@/components/ProgressSteps.vue'
import TrackingTimeline from '@/components/TrackingTimeline.vue'

const route = useRoute()
const s = ref(null)
const error = ref('')
const busy = ref(false)

async function load() {
  try {
    s.value = await api(`/shipments/${encodeURIComponent(route.params.number)}/`)
  } catch (e) {
    error.value = e instanceof ApiError && e.status === 404 ? 'Booking not found.' : 'Could not load this booking.'
  }
}
async function cancel() {
  if (!confirm('Cancel this booking? This cannot be undone.')) return
  busy.value = true
  try {
    s.value = await api(`/shipments/${encodeURIComponent(s.value.tracking_number)}/cancel/`, { method: 'POST' })
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
onMounted(load)
</script>

<template>
  <section class="container" style="padding-top: 32px">
    <AccountNav />
    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="!s && !error" class="spinner"></div>
    <template v-if="s">
      <div class="page-head">
        <div>
          <div class="small muted">Tracking number</div>
          <h1 class="mono">{{ s.tracking_number }}</h1>
          <div class="muted">{{ s.description }}</div>
          <div class="lane"><strong>{{ s.origin_name }}</strong> <span aria-hidden="true">→</span><span class="sr"> to </span> <strong>{{ s.destination_name }}</strong></div>
        </div>
        <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap">
          <StatusBadge :status="s.status" :label="s.status_display" />
          <template v-if="s.is_editable">
            <RouterLink :to="`/account/shipments/${s.tracking_number}/edit`" class="btn btn-outline btn-sm">Edit</RouterLink>
            <button class="btn btn-danger btn-sm" :disabled="busy" @click="cancel">Cancel</button>
          </template>
        </div>
      </div>

      <PartsNotice v-if="s.part" :part="s.part" base="/account/shipments" />
      <div class="card"><ProgressSteps :status="s.status" /></div>

      <div class="layout">
        <div class="card">
          <h3>Milestones</h3>
          <p class="small muted" style="margin-top: -6px">We post an update when your cargo reaches each major town, weighbridge or border post. For security, we don't share the truck's live location.</p>
          <TrackingTimeline :events="s.events" />
        </div>
        <div>
          <div class="card">
            <h3>Charges</h3>
            <dl>
              <dt>Weight at loading</dt><dd>{{ s.weight_kg ? `${s.weight_kg} kg` : 'Pending' }}</dd>
              <dt>Volume</dt><dd>{{ s.volume_cbm ? `${s.volume_cbm} CBM` : '—' }}</dd>
              <dt>Packages loaded</dt><dd>{{ s.packages_received ?? '—' }}</dd>
              <dt>Freight charge</dt><dd><strong>{{ money(s.charge_usd) }}</strong></dd>
              <dt>Payment</dt><dd>{{ s.payment_status_display }}</dd>
              <dt>ETA {{ s.destination_name }}</dt><dd>{{ date(s.eta_date) }}</dd>
            </dl>
          </div>
          <div class="card" style="margin-top: 20px">
            <h3>Details</h3>
            <dl>
              <dt>Load type</dt><dd>{{ s.mode_display }}</dd>
              <dt>Service</dt><dd>{{ s.service_type_display }}</dd>
              <dt>Pickup</dt><dd>{{ s.pickup_address || s.origin_name }}<div v-if="s.pickup_date" class="small muted">Ready {{ date(s.pickup_date) }}</div></dd>
              <dt>Category</dt><dd>{{ s.category_display }}</dd>
              <dt>Quantity</dt><dd>{{ s.quantity }}</dd>
              <dt>Declared weight</dt><dd>{{ s.declared_weight_kg ? `${s.declared_weight_kg} kg` : '—' }}</dd>
              <dt>Cargo value</dt><dd>{{ money(s.declared_value_usd) }}</dd>
              <dt>Special handling</dt><dd>{{ [s.is_hazardous && 'Hazardous', s.is_fragile && 'Fragile'].filter(Boolean).join(', ') || 'None' }}</dd>
              <dt>Receiver</dt><dd>{{ s.consignee_name || '—' }}<div v-if="s.consignee_phone" class="small muted">{{ s.consignee_phone }}</div></dd>
              <dt>Delivery</dt><dd>{{ s.delivery_option_display }}<div v-if="s.delivery_address" class="small muted">{{ s.delivery_address }}</div></dd>
              <dt>Created</dt><dd>{{ dateTime(s.created_at) }}</dd>
            </dl>
            <p v-if="s.customer_notes" class="small muted" style="white-space: pre-line">{{ s.customer_notes }}</p>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.page-head h1 { font-size: 1.6rem; }
.lane { margin-top: 6px; font-size: 1.05rem; color: var(--navy); }
.lane span { color: var(--amber-dark); margin: 0 4px; }
.sr { position: absolute; left: -9999px; }
.layout { display: grid; grid-template-columns: 1.5fr 1fr; gap: 20px; margin-top: 20px; align-items: start; }
dl { display: grid; grid-template-columns: 140px 1fr; gap: 8px 12px; margin: 0; font-size: 0.93rem; }
dt { color: var(--muted); }
dd { margin: 0; }
@media (max-width: 960px) { .layout { grid-template-columns: 1fr; } }
</style>
