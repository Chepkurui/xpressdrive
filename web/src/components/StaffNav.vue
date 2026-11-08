<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()

// Each tab shows only if the staff member has view permission for that section.
const tabs = computed(() =>
  [
    { key: 'overview', to: '/staff', label: 'Overview' },
    { key: 'live', to: '/staff/live', label: 'Live map', section: 'trips' },
    { key: 'trips', to: '/staff/trips', label: 'Trips', section: 'trips' },
    { key: 'shipments', to: '/staff/shipments', label: 'Bookings', section: 'shipments' },
    { key: 'emptylegs', to: '/staff/empty-legs', label: 'Empty legs', section: 'emptylegs' },
    { key: 'fleet', to: '/staff/fleet', label: 'Drivers & trucks', section: 'trucks' },
    { key: 'users', to: '/staff/users', label: 'People', section: 'users' },
    { key: 'rates', to: '/staff/rates', label: 'Pricing', section: 'rates' },
    { key: 'messages', to: '/staff/messages', label: 'Messages', section: 'messages' },
  ].filter((t) => !t.section || auth.can(t.section)),
)
const current = computed(() => {
  const n = String(route.name || '')
  if (n === 'staff-live') return 'live'
  if (n.startsWith('staff-trip')) return 'trips'
  if (n.startsWith('staff-shipment')) return 'shipments'
  if (n === 'staff-empty-legs') return 'emptylegs'
  if (n === 'staff-fleet') return 'fleet'
  if (n.startsWith('staff-user')) return 'users'
  if (n === 'staff-rates') return 'rates'
  if (n === 'staff-messages') return 'messages'
  return 'overview'
})
</script>

<template>
  <div class="staff-bar">
    <span class="tag">Staff Operations</span>
    <nav class="staff-nav" aria-label="Staff Operations">
      <RouterLink v-for="t in tabs" :key="t.key" :to="t.to" :class="{ active: current === t.key }" :aria-current="current === t.key ? 'page' : undefined">{{ t.label }}</RouterLink>
    </nav>
  </div>
</template>

<style scoped>
.staff-bar { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin: 0 0 24px; }
.tag { font-size: 0.72rem; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; color: var(--amber-dark); }
.staff-nav { display: flex; flex-wrap: wrap; gap: 8px; }
a { padding: 8px 14px; border-radius: 999px; background: var(--surface); border: 1px solid var(--border); color: var(--navy); font-weight: 600; font-size: 0.9rem; text-decoration: none !important; }
a.active { background: var(--navy); color: #fff; border-color: var(--navy); }
</style>
