<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import { money } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import StaffNav from '@/components/StaffNav.vue'
import StatusBadge from '@/components/StatusBadge.vue'

const auth = useAuthStore()
const router = useRouter()
const d = ref(null)
const error = ref('')

onMounted(async () => {
  try {
    d.value = await api('/staff/summary/')
  } catch (e) {
    error.value = e.message || 'Could not load the overview.'
  }
})

const list = (stage) => ({ path: '/staff/shipments', query: { stage } })

// Where active bookings are right now, in journey order.
const pipeline = computed(() => {
  const s = d.value?.shipments
  if (!s) return []
  return [
    { stage: 'booked', label: 'New bookings', hint: 'To quote & confirm', n: s.booked },
    { stage: 'awaiting_truck', label: 'Awaiting truck', hint: 'Confirmed, not loaded', n: s.awaiting_truck },
    { stage: 'on_truck', label: 'On a truck', hint: 'Allocated / loaded', n: s.on_truck },
    { stage: 'transit', label: 'On the road', hint: 'In transit / at border', n: s.in_transit },
    { stage: 'arrived', label: 'Arrived', hint: 'To hand over', n: s.arrived },
  ]
})

// Things someone has to act on. Only non-zero items are shown.
const attention = computed(() => {
  const x = d.value
  if (!x) return []
  const items = []
  const s = x.shipments
  const t = x.trips
  if (t?.not_reporting) items.push({ to: '/staff/live', n: t.not_reporting, text: `truck${t.not_reporting === 1 ? '' : 's'} on the road not reporting position`, tone: 'warn' })
  if (t?.declined) items.push({ to: { path: '/staff/trips', query: { state: 'open' } }, n: t.declined, text: `trip${t.declined === 1 ? '' : 's'} declined by a driver, reallocate`, tone: 'warn' })
  if (s?.no_trip) items.push({ to: list('no_trip'), n: s.no_trip, text: `confirmed booking${s.no_trip === 1 ? '' : 's'} with no truck yet` })
  if (x.empty_legs_open) items.push({ to: '/staff/empty-legs', n: x.empty_legs_open, text: `driver offer${x.empty_legs_open === 1 ? '' : 's'} of empty return space` })
  if (s?.on_hold) items.push({ to: list('on_hold'), n: s.on_hold, text: s.on_hold === 1 ? 'booking on hold' : 'bookings on hold', tone: 'warn' })
  if (s?.awaiting_quote) items.push({ to: list('awaiting_quote'), n: s.awaiting_quote, text: 'confirmed, still need a quote' })
  if (s?.unpaid_count) items.push({ to: list('unpaid'), n: money(s.unpaid_usd), text: `unpaid across ${s.unpaid_count} booking${s.unpaid_count === 1 ? '' : 's'}` })
  if (x.unhandled_messages) items.push({ to: '/staff/messages', n: x.unhandled_messages, text: `contact message${x.unhandled_messages === 1 ? '' : 's'} waiting for a reply`, tone: 'warn' })
  return items
})
const showAttention = computed(() => d.value && (d.value.shipments || d.value.trips || d.value.unhandled_messages != null))

// Tabbed booking list. "Latest" comes with the summary; the others load on first open.
const tabs = computed(() => {
  const s = d.value?.shipments
  if (!s) return []
  return [
    { key: 'latest', label: 'Latest' },
    { key: 'awaiting_quote', label: 'Needs a quote', n: s.awaiting_quote },
    { key: 'unpaid', label: 'Unpaid', n: s.unpaid_count },
    { key: 'on_hold', label: 'On hold', n: s.on_hold },
  ]
})
const tab = ref('latest')
const tabRows = ref({})
const tabLoading = ref(false)
const rows = computed(() => (tab.value === 'latest' ? d.value?.recent_shipments : tabRows.value[tab.value]) || [])

async function openTab(key) {
  tab.value = key
  if (key === 'latest' || tabRows.value[key]) return
  tabLoading.value = true
  try {
    const res = await api('/staff/shipments/', { query: { stage: key, page_size: 8 } })
    tabRows.value = { ...tabRows.value, [key]: res.results }
  } catch (e) {
    error.value = e.message || 'Could not load bookings.'
  } finally {
    tabLoading.value = false
  }
}
</script>

<template>
  <section class="container" style="padding-top: 32px">
    <StaffNav />
    <h1 style="font-size: 1.8rem">Good day, {{ auth.user.first_name || 'team' }}</h1>
    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="!d && !error" class="spinner"></div>

    <template v-if="d">
      <div v-if="!Object.keys(d).length" class="card empty">
        Your staff account has no sections assigned yet. Ask an administrator to give you permissions.
      </div>

      <!-- 1. Pipeline -->
      <div v-if="d.shipments" class="card pipeline">
        <div class="pipe-head">
          <h2 class="sec">Booking pipeline</h2>
          <RouterLink class="small" :to="{ path: '/staff/shipments', query: { state: 'active' } }">
            {{ d.shipments.active }} active<template v-if="d.shipments.on_hold"> · {{ d.shipments.on_hold }} on hold</template> →
          </RouterLink>
        </div>
        <ol class="stages">
          <li v-for="p in pipeline" :key="p.stage">
            <RouterLink :to="list(p.stage)" class="stage" :class="{ zero: !p.n }">
              <span class="n">{{ p.n }}</span>
              <span class="lbl">{{ p.label }}</span>
              <span class="hint">{{ p.hint }}</span>
            </RouterLink>
          </li>
        </ol>
      </div>

      <div class="split">
        <!-- 2. Needs attention -->
        <div v-if="showAttention" class="card">
          <h2 class="sec">Needs attention</h2>
          <ul v-if="attention.length" class="todo">
            <li v-for="a in attention" :key="a.text">
              <RouterLink :to="a.to" :class="a.tone">
                <strong>{{ a.n }}</strong> <span>{{ a.text }}</span> <span class="go">→</span>
              </RouterLink>
            </li>
          </ul>
          <p v-else class="muted clear">✓ All clear. Nothing is waiting on the team.</p>
        </div>

        <!-- 3. Operations -->
        <div v-if="d.trips || d.customers" class="card ops">
          <h2 class="sec">Operations</h2>
          <RouterLink v-if="d.trips" to="/staff/live" class="op">
            <span class="small muted">Trips</span>
            <span><strong>{{ d.trips.live }}</strong> under way</span>
            <span class="small muted">{{ d.trips.planned }} planned · {{ d.trips.awaiting_driver }} awaiting a driver</span>
          </RouterLink>
          <RouterLink v-if="d.drivers != null" to="/staff/fleet" class="op">
            <span class="small muted">Drivers</span>
            <span><strong>{{ d.drivers }}</strong> active</span>
          </RouterLink>
          <RouterLink v-if="d.customers" to="/staff/users" class="op">
            <span class="small muted">Customers</span>
            <span><strong>{{ d.customers.total }}</strong> total</span>
            <span class="small muted">{{ d.customers.active }} active</span>
          </RouterLink>
        </div>
      </div>

      <!-- 4. Tabbed parcel list -->
      <div v-if="tabs.length" class="card list">
        <div class="tabs" role="tablist">
          <button
            v-for="t in tabs" :key="t.key" role="tab" :aria-selected="tab === t.key"
            :class="{ active: tab === t.key }" @click="openTab(t.key)"
          >
            {{ t.label }}<span v-if="t.n" class="count">{{ t.n }}</span>
          </button>
          <RouterLink class="small all" :to="tab === 'latest' ? '/staff/shipments' : list(tab)">View all →</RouterLink>
        </div>
        <div v-if="tabLoading" class="spinner"></div>
        <div v-else-if="!rows.length" class="empty">Nothing here.</div>
        <div v-else class="table-wrap">
          <table>
            <thead><tr><th>Tracking</th><th>Customer</th><th>Cargo</th><th>Route</th><th>Status</th><th>Charge</th></tr></thead>
            <tbody>
              <tr v-for="s in rows" :key="s.tracking_number" class="clickable" @click="router.push(`/staff/shipments/${s.tracking_number}`)">
                <td class="mono">{{ s.tracking_number }}</td>
                <td>{{ s.owner.full_name }}<div class="small muted mono">{{ s.owner.customer_code }}</div></td>
                <td>{{ s.description }}<div v-if="s.part" class="small muted">Part {{ s.part.number }} of {{ s.part.count }}</div></td>
                <td class="small">{{ s.origin_name }} → {{ s.destination_name }}</td>
                <td><StatusBadge :status="s.status" :label="s.status_display" /></td>
                <td>{{ money(s.charge_usd) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.sec { font-size: 1.1rem; margin: 0 0 12px; }
a { color: inherit; text-decoration: none !important; }

.pipeline { margin-bottom: 20px; }
.pipe-head { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; flex-wrap: wrap; }
.pipe-head a { color: var(--blue); }
.stages { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(5, 1fr); }
.stages li { position: relative; }
.stages li + li::before { content: '›'; position: absolute; left: -6px; top: 50%; transform: translateY(-50%); color: var(--muted); font-size: 1.4rem; }
.stage { display: flex; flex-direction: column; padding: 8px 20px; border-radius: 10px; }
.stage:hover { background: var(--bg); }
.stage .n { font-size: 2rem; font-weight: 800; color: var(--navy); line-height: 1.1; }
.stage .lbl { font-weight: 600; }
.stage .hint { font-size: 0.8rem; color: var(--muted); }
.stage.zero .n { color: var(--muted); opacity: 0.5; }

.split { display: grid; grid-template-columns: 1.4fr 1fr; gap: 20px; margin-bottom: 20px; align-items: stretch; }
.todo { list-style: none; margin: 0; padding: 0; }
.todo li + li { border-top: 1px solid var(--border); }
.todo a { display: flex; align-items: baseline; gap: 8px; padding: 10px 4px; }
.todo a:hover { background: var(--bg); }
.todo strong { font-size: 1.15rem; color: var(--navy); min-width: 2ch; }
.todo .warn strong { color: var(--warning); }
.todo .go { margin-left: auto; color: var(--muted); }
.clear { margin: 0; }

.ops { display: flex; flex-direction: column; }
.op { display: grid; grid-template-columns: 90px 1fr; column-gap: 12px; padding: 10px 4px; align-items: baseline; }
.op + .op { border-top: 1px solid var(--border); }
.op:hover { background: var(--bg); }
.op > span:last-child { grid-column: 2; }
.op strong { font-size: 1.15rem; color: var(--navy); }

.tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--border); margin-bottom: 8px; flex-wrap: wrap; align-items: center; }
.tabs button { background: none; border: 0; border-bottom: 2px solid transparent; padding: 10px 14px; font: inherit; font-weight: 600; color: var(--muted); cursor: pointer; margin-bottom: -1px; }
.tabs button.active { color: var(--navy); border-bottom-color: var(--amber); }
.tabs .count { margin-left: 6px; background: var(--bg); border-radius: 999px; padding: 1px 8px; font-size: 0.78rem; }
.tabs .all { margin-left: auto; color: var(--blue); }

@media (max-width: 860px) {
  .stages { grid-template-columns: repeat(2, 1fr); row-gap: 8px; }
  .stages li:nth-child(odd)::before { display: none; }
  .split { grid-template-columns: 1fr; }
}
</style>
