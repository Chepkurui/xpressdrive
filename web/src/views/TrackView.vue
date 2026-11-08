<script setup>
import PageBanner from '@/components/PageBanner.vue'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, ApiError } from '@/api/client'
import { date } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import StatusBadge from '@/components/StatusBadge.vue'
import ProgressSteps from '@/components/ProgressSteps.vue'
import TrackingTimeline from '@/components/TrackingTimeline.vue'
import RouteMap from '@/components/RouteMap.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
// Full details are only for the owner or staff. Signed-out visitors get a sign-in
// prompt; signed-in users get a link only if they may open the booking.
const isStaffViewer = computed(() => auth.isStaff && auth.can('shipments'))
const isOwner = ref(false)
const number = ref(route.params.number || '')
const result = ref(null)
const error = ref('')
const loading = ref(false)

async function load(n) {
  result.value = null
  error.value = ''
  isOwner.value = false
  if (!n) return
  if (!/^(XD|WD)[A-Z0-9]{10}$/.test(n)) {
    error.value = 'Tracking numbers start with XD followed by 10 letters/numbers.'
    return
  }
  loading.value = true
  try {
    result.value = await api(`/track/${encodeURIComponent(n)}/`, { auth: false })
    if (auth.isAuthenticated && !isStaffViewer.value) {
      // The customer endpoint only returns the user's own bookings; anything else is a 404.
      isOwner.value = await api(`/shipments/${encodeURIComponent(n)}/`).then(() => true, () => false)
    }
  } catch (e) {
    error.value = e instanceof ApiError && e.status === 429 ? 'Too many lookups. Please wait a minute and try again.' : 'No booking found with that tracking number.'
  } finally {
    loading.value = false
  }
}

function submit() {
  const n = number.value.trim().toUpperCase()
  router.replace({ name: 'track', params: { number: n } })
}

watch(() => route.params.number, (n) => { number.value = n || ''; load((n || '').toUpperCase()) }, { immediate: true })
</script>

<template>
  <PageBanner image="/images/truck.webp" eyebrow="Milestone tracking" title="Track a booking" lead="See each town, weighbridge and border post your cargo has passed, from pickup to delivery." position="center 60%" />
  <section class="section">
    <div class="container" style="max-width: 860px">
      <form class="search" @submit.prevent="submit">
        <input v-model="number" class="mono" placeholder="Enter tracking number, e.g. XD7KQ2M9XP4A" maxlength="12" aria-label="Tracking number" autocomplete="off" />
        <button class="btn btn-dark" :disabled="loading">Track</button>
      </form>

      <div v-if="loading" class="spinner"></div>
      <div v-if="error" class="alert alert-error">{{ error }}</div>

      <div v-if="result" class="card">
        <div class="page-head" style="margin-bottom: 12px">
          <div>
            <div class="small muted">Tracking number</div>
            <div class="mono" style="font-size: 1.3rem; font-weight: 700">{{ result.tracking_number }}</div>
          </div>
          <StatusBadge :status="result.status" :label="result.status_display" />
        </div>
        <p class="lane"><strong>{{ result.origin_name }}</strong> → <strong>{{ result.destination_name }}</strong></p>
        <p class="small muted">{{ result.mode_display }} · ETA: <strong>{{ date(result.eta_date) }}</strong></p>
        <ProgressSteps :status="result.status" />
        <h3 style="margin-top: 24px">Milestones</h3>
        <TrackingTimeline :events="result.events" />
        <p v-if="!auth.isAuthenticated" class="small muted" style="margin-top: 16px">Is this your booking? <RouterLink :to="{ name: 'login', query: { next: route.fullPath } }">Sign in</RouterLink> to see charges, measurements and full details.</p>
        <p v-else-if="isStaffViewer" style="margin-top: 16px"><RouterLink :to="`/staff/shipments/${result.tracking_number}`" class="btn btn-outline btn-sm">Open in Staff Operations →</RouterLink></p>
        <p v-else-if="isOwner" style="margin-top: 16px"><RouterLink :to="`/account/shipments/${result.tracking_number}`" class="btn btn-outline btn-sm">View charges &amp; full details →</RouterLink></p>
      </div>
    </div>
  </section>
  <section class="route-band">
    <div class="container">
      <div class="center" v-reveal>
        <div class="eyebrow">Our route</div>
        <h2>From the coast to the Great Lakes, and back</h2>
      </div>
      <div v-reveal="150"><RouteMap /></div>
    </div>
  </section>
</template>

<style scoped>
.route-band { color: #fff; padding: 56px 0 40px; background: linear-gradient(rgba(15, 42, 68, 0.72), rgba(15, 42, 68, 0.8)), url('/images/containers-aerial.webp') center / cover fixed; }
.route-band h2 { color: #fff; }
.lane { font-size: 1.1rem; color: var(--navy); margin: 0 0 4px; }
.search { display: flex; gap: 12px; margin: 16px 0 24px; }
.search input { flex: 1; }
</style>
