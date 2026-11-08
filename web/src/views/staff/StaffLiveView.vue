<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api } from '@/api/client'
import { ago } from '@/utils/format'
import StaffNav from '@/components/StaffNav.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import FleetMap from '@/components/FleetMap.vue'

const REFRESH_MS = 15000
const trips = ref([])
const loaded = ref(false)
const error = ref('')
const selected = ref('')
const trail = ref([])
const filter = ref('all')
const mapRef = ref(null)
const updatedAt = ref(null)
let timer

async function load() {
  try {
    const res = await api('/staff/live/')
    trips.value = res.trips
    updatedAt.value = new Date()
    error.value = ''
    if (selected.value) await loadTrail()
  } catch (e) {
    error.value = e.message || 'Could not load live trips.'
  } finally {
    loaded.value = true
  }
}
async function loadTrail() {
  try {
    trail.value = (await api(`/staff/trips/${encodeURIComponent(selected.value)}/positions/`)).positions
  } catch {
    trail.value = []
  }
}
function select(code) {
  selected.value = selected.value === code ? '' : code
}
watch(selected, (code) => {
  trail.value = []
  if (code) {
    loadTrail()
    mapRef.value?.focus(code)
  }
})

// Pause polling while the tab is hidden; refresh as soon as it is visible again.
function onVisibility() {
  clearInterval(timer)
  if (document.visibilityState === 'visible') {
    load()
    timer = setInterval(load, REFRESH_MS)
  }
}
onMounted(() => {
  load()
  timer = setInterval(load, REFRESH_MS)
  document.addEventListener('visibilitychange', onVisibility)
})
onBeforeUnmount(() => {
  clearInterval(timer)
  document.removeEventListener('visibilitychange', onVisibility)
})

const counts = computed(() => ({
  all: trips.value.length,
  moving: trips.value.filter((t) => t.status === 'in_transit' && !t.stale).length,
  border: trips.value.filter((t) => t.status === 'at_border').length,
  stale: trips.value.filter((t) => t.stale).length,
  waiting: trips.value.filter((t) => t.status === 'allocated').length,
}))
const shown = computed(() => trips.value.filter((t) => {
  if (filter.value === 'moving') return t.status === 'in_transit' && !t.stale
  if (filter.value === 'border') return t.status === 'at_border'
  if (filter.value === 'stale') return t.stale
  if (filter.value === 'waiting') return t.status === 'allocated'
  return true
}))
const onMap = computed(() => shown.value.filter((t) => t.last_position))
</script>

<template>
  <section class="container wide" style="padding-top: 32px">
    <StaffNav />
    <div class="page-head">
      <div>
        <h1>Live trips</h1>
        <p class="small muted" style="margin: 4px 0 0">Positions come from drivers' phones while a trip is under way. Refreshes every 15 s<template v-if="updatedAt">, last at {{ updatedAt.toLocaleTimeString() }}</template>. Cargo owners never see this map, only named milestones.</p>
      </div>
      <RouterLink to="/staff/trips" class="btn btn-outline btn-sm">All trips →</RouterLink>
    </div>
    <div v-if="error" class="alert alert-error">{{ error }}</div>

    <div class="chips" role="tablist" aria-label="Filter trips">
      <button v-for="f in [['all', 'All'], ['moving', 'Moving'], ['border', 'At border'], ['stale', 'Not reporting'], ['waiting', 'Awaiting driver']]" :key="f[0]"
              role="tab" :aria-selected="filter === f[0]" :class="{ on: filter === f[0], warn: f[0] === 'stale' && counts.stale }" @click="filter = f[0]">
        {{ f[1] }} <span>{{ counts[f[0]] }}</span>
      </button>
    </div>

    <div class="live">
      <FleetMap ref="mapRef" :trips="onMap" :trail="trail" :selected="selected" height="calc(100vh - 290px)" @select="select" />
      <aside class="list card flat">
        <div v-if="!loaded" class="spinner"></div>
        <div v-else-if="!shown.length" class="empty small">No trips here right now.</div>
        <button v-for="t in shown" :key="t.code" type="button" class="trip" :class="{ sel: selected === t.code, stale: t.stale }" @click="select(t.code)">
          <div class="top">
            <span class="mono code">{{ t.code }}</span>
            <StatusBadge :status="t.status" :label="t.status_display" />
          </div>
          <div class="lane">{{ t.origin_name }} → {{ t.destination_name }}<span v-if="t.is_backhaul" class="bh">Return</span></div>
          <div class="small muted">{{ t.driver?.full_name || 'No driver' }}<template v-if="t.truck"> · {{ t.truck.plate_number }}</template></div>
          <div class="small" :class="t.stale ? 'danger' : 'muted'">
            <template v-if="t.status === 'allocated'">Waiting for the driver to accept</template>
            <template v-else-if="t.last_position">📍 {{ ago(t.last_position.at) }}<template v-if="t.last_position.speed_kmh != null"> · {{ Math.round(t.last_position.speed_kmh) }} km/h</template></template>
            <template v-else>No position yet</template>
            <template v-if="t.stale"> · not reporting</template>
          </div>
          <div class="small muted">{{ t.shipment_count }} booking(s)<template v-if="t.driver?.phone"> · <a :href="`tel:${t.driver.phone}`" @click.stop>Call driver</a></template></div>
          <RouterLink v-if="selected === t.code" :to="`/staff/trips/${t.code}`" class="small open" @click.stop>Open trip →</RouterLink>
        </button>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.wide { max-width: 1480px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.chips button { border: 1px solid var(--border); background: var(--surface); border-radius: 999px; padding: 6px 12px; font: inherit; font-size: 0.88rem; font-weight: 600; color: var(--navy); cursor: pointer; }
.chips button span { margin-left: 4px; color: var(--muted); }
.chips button.on { background: var(--navy); color: #fff; border-color: var(--navy); }
.chips button.on span { color: #d6e2ee; }
.chips button.warn:not(.on) { border-color: var(--danger); color: var(--danger); }
.live { display: grid; grid-template-columns: 1fr 340px; gap: 16px; min-height: 420px; }
.list { padding: 8px; overflow-y: auto; max-height: calc(100vh - 290px); min-height: 420px; }
.trip { display: block; width: 100%; text-align: left; background: none; border: 1px solid transparent; border-bottom-color: var(--border); border-radius: 10px; padding: 10px; font: inherit; color: inherit; cursor: pointer; }
.trip:hover { background: var(--bg); }
.trip.sel { border-color: var(--amber); background: #fff6ec; }
.trip.stale { border-left: 4px solid var(--danger); }
.top { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 4px; }
.code { font-weight: 700; color: var(--navy); }
.lane { font-weight: 600; }
.bh { margin-left: 6px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; color: var(--amber-dark); }
.danger { color: var(--danger); }
.open { display: inline-block; margin-top: 4px; font-weight: 600; }
@media (max-width: 960px) {
  .live { grid-template-columns: 1fr; }
  .list { max-height: none; }
}
</style>
