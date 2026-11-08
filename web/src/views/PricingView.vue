<script setup>
import PageBanner from '@/components/PageBanner.vue'
import { onMounted, ref } from 'vue'
import { api } from '@/api/client'
import { money, days } from '@/utils/format'
import EstimateCalculator from '@/components/EstimateCalculator.vue'

const rates = ref([])
const loading = ref(true)
const error = ref('')
const unit = { per_kg: '/ kg', per_cbm: '/ CBM', per_container: '/ truck or container' }

onMounted(async () => {
  try {
    rates.value = await api('/rates/', { auth: false })
  } catch {
    error.value = 'Rates are temporarily unavailable. Please contact us for a quote.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <PageBanner
    image="/images/containers-aerial.webp"
    eyebrow="Pricing & delivery times"
    title="Transparent, indicative pricing"
    lead="Starting rates for road freight in the region. We confirm your price for the exact route when you book, and it is checked against the weight and volume at loading."
  />
  <section class="section">
    <div class="container">

      <div v-if="loading" class="spinner"></div>
      <div v-else-if="error" class="alert alert-error">{{ error }}</div>
      <div v-else class="layout">
        <div class="grid grid-2">
          <div v-for="r in rates" :key="r.code" class="card rate">
            <h3>{{ r.name }}</h3>
            <div v-if="r.name !== r.mode_display || r.route_display" class="small muted">{{ r.mode_display }}<template v-if="r.route_display"> · {{ r.route_display }}</template></div>
            <div class="price">from {{ money(r.price_usd) }} <span>{{ unit[r.basis] }}</span></div>
            <div class="small muted" v-if="Number(r.min_charge_usd) > 0">Minimum charge {{ money(r.min_charge_usd) }}</div>
            <div class="time">⏱ {{ days(r.transit_days_min, r.transit_days_max) }} on the road</div>
            <p class="small">{{ r.summary }}</p>
            <p v-if="r.best_for" class="small muted"><strong>Best for:</strong> {{ r.best_for }}</p>
          </div>
        </div>
        <EstimateCalculator :rates="rates" />
      </div>

      <div class="grid grid-2" style="margin-top: 40px">
        <div class="card flat">
          <h3>How parcels are charged</h3>
          <p class="small muted">By <strong>chargeable weight</strong>: whichever is greater of the actual weight and the volumetric weight (length × width × height in cm ÷ 3000, so 1 CBM counts as at least 333 kg). Light but bulky boxes are charged by size.</p>
        </div>
        <div class="card flat">
          <h3>Part loads, full trucks and containers</h3>
          <p class="small muted">Part loads share a truck and are charged per <strong>cubic metre (CBM)</strong>. Full trucks and containers are a fixed price per truck for the route. <strong>Return-leg (backhaul)</strong> trucks are cheaper because they're heading back to base anyway.</p>
        </div>
        <div class="card flat">
          <h3>What's not included</h3>
          <p class="small muted">Customs duties and taxes, border clearing-agent fees, cargo insurance, storage and loading or offloading labour are quoted separately. We can recommend licensed clearing agents at Malaba, Busia, Mpondwe, Katuna and Elegu.</p>
        </div>
        <div class="card flat">
          <h3>Transit times</h3>
          <p class="small muted">Times run from loading. Shared-truck cargo leaves when a truck on your lane has space, usually within a few days. Border queues, weighbridges, customs inspections and road conditions in the rainy season can add time.</p>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.layout { display: grid; grid-template-columns: 1.6fr 1fr; gap: 24px; align-items: start; margin-top: 24px; }
.price { font-size: 1.6rem; font-weight: 800; color: var(--navy); }
.price span { font-size: 0.95rem; color: var(--muted); font-weight: 500; }
.time { margin: 10px 0; font-weight: 600; }
@media (max-width: 960px) { .layout { grid-template-columns: 1fr; } }
</style>
