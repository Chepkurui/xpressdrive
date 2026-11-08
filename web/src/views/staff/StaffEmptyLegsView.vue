<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import { date, dateTime } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import StaffNav from '@/components/StaffNav.vue'
import PlaceSelect from '@/components/PlaceSelect.vue'

const router = useRouter()
const auth = useAuthStore()
const canMatch = computed(() => auth.can('trips', 'add') && auth.can('emptylegs', 'change'))
const canChange = computed(() => auth.can('emptylegs', 'change'))
const filters = reactive({ status: 'open', current: 'true', origin: '', destination: '', page: 1 })
const data = ref(null)
const error = ref('')
const busy = ref(0)

async function load() {
  error.value = ''
  try {
    data.value = await api('/staff/empty-legs/', { query: { ...filters } })
  } catch (e) {
    error.value = e.message
  }
}
watch(() => ({ ...filters }), load, { immediate: true, deep: true })

async function createTrip(leg) {
  if (!confirm(`Create a backhaul trip ${leg.origin_name} → ${leg.destination_name} and offer it to ${leg.driver.full_name}?`)) return
  busy.value = leg.id
  try {
    const trip = await api(`/staff/empty-legs/${leg.id}/create-trip/`, { method: 'POST', body: { allocate: true } })
    router.push(`/staff/trips/${trip.code}`)
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = 0
  }
}
async function setStatus(leg, status) {
  busy.value = leg.id
  try {
    await api(`/staff/empty-legs/${leg.id}/`, { method: 'PATCH', body: { status } })
    await load()
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = 0
  }
}
</script>

<template>
  <section class="container" style="padding-top: 32px">
    <StaffNav />
    <div class="page-head">
      <div>
        <h1>Empty legs</h1>
        <p class="small muted" style="margin: 4px 0 0">Drivers post these from the app when their truck or container is going back empty. Turn one into a backhaul trip, then load bookings going that way. Open offers also appear (without driver details) on the public return-truck board.</p>
      </div>
    </div>
    <div class="card">
      <div class="filters">
        <div class="tabs">
          <button v-for="t in [['open', 'Open'], ['matched', 'Matched'], ['withdrawn', 'Withdrawn'], ['expired', 'Expired'], ['', 'All']]" :key="t[0]" class="btn btn-sm" :class="filters.status === t[0] ? 'btn-dark' : 'btn-outline'" @click="filters.status = t[0]; filters.page = 1">{{ t[1] }}</button>
        </div>
        <PlaceSelect v-model="filters.origin" placeholder="Any origin" aria-label="Origin" />
        <PlaceSelect v-model="filters.destination" placeholder="Any destination" aria-label="Destination" />
        <label class="checkbox small"><input v-model="filters.current" type="checkbox" true-value="true" false-value="" /> Hide past dates</label>
      </div>
      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <div v-if="!data && !error" class="spinner"></div>
      <template v-if="data">
        <div v-if="!data.results.length" class="empty">No empty legs here.</div>
        <div v-else class="table-wrap">
          <table>
            <thead><tr><th>Lane</th><th>Available</th><th>Space</th><th>Driver &amp; truck</th><th>Status</th><th></th></tr></thead>
            <tbody>
              <tr v-for="l in data.results" :key="l.id">
                <td><strong>{{ l.origin_name }} → {{ l.destination_name }}</strong><div v-if="l.notes" class="small muted">{{ l.notes }}</div></td>
                <td class="small">{{ date(l.available_from) }}<template v-if="l.available_until"> – {{ date(l.available_until) }}</template><div class="muted">posted {{ dateTime(l.created_at) }}</div></td>
                <td class="small">{{ l.space_display }}<div v-if="l.capacity_kg || l.capacity_cbm" class="muted">{{ l.capacity_kg ? `${l.capacity_kg} kg` : '' }} {{ l.capacity_cbm ? `${l.capacity_cbm} CBM` : '' }}</div></td>
                <td>{{ l.driver.full_name }}<div class="small muted"><a v-if="l.driver.phone" :href="`tel:${l.driver.phone}`">{{ l.driver.phone }}</a> · {{ l.truck?.plate_number || l.vehicle_description || 'truck not set' }}</div></td>
                <td><span class="badge" :class="{ green: l.status === 'open', blue: l.status === 'matched' }">{{ l.status_display }}</span>
                  <div v-if="l.trip_code" class="small"><RouterLink :to="`/staff/trips/${l.trip_code}`" class="mono">{{ l.trip_code }}</RouterLink></div></td>
                <td class="actions">
                  <button v-if="l.status === 'open' && canMatch" class="btn btn-primary btn-sm" :disabled="busy === l.id" @click="createTrip(l)">Create trip</button>
                  <button v-if="l.status === 'open' && canChange" class="btn btn-outline btn-sm" :disabled="busy === l.id" @click="setStatus(l, 'expired')">Expire</button>
                  <button v-if="l.status === 'expired' && canChange" class="btn btn-outline btn-sm" :disabled="busy === l.id" @click="setStatus(l, 'open')">Reopen</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="data.count > 20" class="pager">
          <button class="btn btn-outline btn-sm" :disabled="!data.previous" @click="filters.page--">← Previous</button>
          <span class="small muted">Page {{ filters.page }}</span>
          <button class="btn btn-outline btn-sm" :disabled="!data.next" @click="filters.page++">Next →</button>
        </div>
      </template>
    </div>
  </section>
</template>

<style scoped>
.filters { display: grid; grid-template-columns: auto 180px 180px auto; gap: 10px; margin-bottom: 16px; align-items: center; }
.tabs { display: flex; gap: 6px; flex-wrap: wrap; }
.actions { display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }
.pager { display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: 16px; }
@media (max-width: 900px) { .filters { grid-template-columns: 1fr 1fr; } .tabs { grid-column: 1 / -1; } }
</style>
