<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { date } from '@/utils/format'
import AccountNav from '@/components/AccountNav.vue'
import StatusBadge from '@/components/StatusBadge.vue'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const summary = ref(null)
const error = ref('')

onMounted(async () => {
  try {
    summary.value = await api('/shipments/summary/')
  } catch {
    error.value = 'Could not load your dashboard.'
  }
})
</script>

<template>
  <section class="container" style="padding-top: 32px">
    <AccountNav />
    <h1 style="font-size: 1.8rem">Hello, {{ auth.user.first_name }} 👋</h1>
    <div v-if="route.query.welcome" class="alert alert-info">Welcome to XpressDrive! Book your first load below. We'll quote it and match it with a truck heading your way.</div>
    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="!summary && !error" class="spinner"></div>

    <template v-if="summary">
      <div class="grid grid-4">
        <div class="card"><div class="small muted">Active bookings</div><div class="stat">{{ summary.active }}</div></div>
        <div class="card"><div class="small muted">Arrived</div><div class="stat">{{ summary.arrived }}</div></div>
        <div class="card"><div class="small muted">Delivered</div><div class="stat">{{ summary.delivered }}</div></div>
        <div class="card"><div class="small muted">Awaiting payment</div><div class="stat">{{ summary.awaiting_payment }}</div></div>
      </div>

      <div class="layout">
        <div class="card">
          <div class="page-head" style="margin-bottom: 8px">
            <h3 style="margin: 0">Recent bookings</h3>
            <RouterLink to="/account/shipments">View all →</RouterLink>
          </div>
          <div v-if="!summary.recent.length" class="empty">
            <p>No bookings yet.</p>
            <RouterLink to="/account/shipments/new" class="btn btn-primary">Book your first load</RouterLink>
          </div>
          <div v-else class="table-wrap">
            <table>
              <thead><tr><th>Tracking</th><th>Cargo</th><th>Route</th><th>Status</th><th>ETA</th></tr></thead>
              <tbody>
                <tr v-for="s in summary.recent" :key="s.tracking_number" class="clickable" @click="router.push(`/account/shipments/${s.tracking_number}`)">
                  <td class="mono">{{ s.tracking_number }}</td>
                  <td>{{ s.description }}</td>
                  <td class="small">{{ s.origin_name }} → {{ s.destination_name }}</td>
                  <td><StatusBadge :status="s.status" :label="s.status_display" /></td>
                  <td>{{ date(s.eta_date) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="card side">
          <div class="small muted">Your customer code</div>
          <div class="code mono">{{ auth.user.customer_code }}</div>
          <p class="small muted">Quote it when you call us or send cargo to a depot.</p>
          <RouterLink to="/account/shipments/new" class="btn btn-primary btn-block">Book a truck</RouterLink>
          <RouterLink :to="{ path: '/', hash: '#return-trucks' }" class="btn btn-outline btn-block" style="margin-top: 8px">See return trucks with space</RouterLink>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.code { font-size: 1.8rem; font-weight: 800; color: var(--amber-dark); }
.layout { display: grid; grid-template-columns: 1.7fr 1fr; gap: 20px; margin-top: 20px; align-items: start; }
@media (max-width: 960px) { .layout { grid-template-columns: 1fr; } }
</style>
