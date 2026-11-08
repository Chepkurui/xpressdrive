<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
// One tab is highlighted per page. Booking detail/edit pages count as "My bookings";
// the booking form gets its own tab.
const current = computed(() => {
  const n = route.name
  if (n === 'shipment-new') return 'new'
  if (n === 'shipments' || n === 'shipment-detail' || n === 'shipment-edit') return 'shipments'
  if (n === 'profile') return 'profile'
  return 'dashboard'
})
const tabs = [
  { key: 'dashboard', to: '/account', label: 'Dashboard' },
  { key: 'shipments', to: '/account/shipments', label: 'My bookings' },
  { key: 'new', to: '/account/shipments/new', label: '+ Book a truck' },
  { key: 'profile', to: '/account/profile', label: 'Profile' },
]
</script>

<template>
  <nav class="acct-nav" aria-label="My account">
    <RouterLink v-for="t in tabs" :key="t.key" :to="t.to" :class="{ active: current === t.key }" :aria-current="current === t.key ? 'page' : undefined">{{ t.label }}</RouterLink>
  </nav>
</template>

<style scoped>
.acct-nav { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 24px; }
a { padding: 8px 14px; border-radius: 999px; background: var(--surface); border: 1px solid var(--border); color: var(--navy); font-weight: 600; font-size: 0.9rem; text-decoration: none !important; }
a.active { background: var(--navy); color: #fff; border-color: var(--navy); }
</style>
