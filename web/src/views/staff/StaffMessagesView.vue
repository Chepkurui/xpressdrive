<script setup>
import { computed, ref, watch } from 'vue'
import { api } from '@/api/client'
import { dateTime } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import StaffNav from '@/components/StaffNav.vue'

const auth = useAuthStore()
const canChange = computed(() => auth.can('messages', 'change'))
const handled = ref('false')
const page = ref(1)
const data = ref(null)
const error = ref('')

async function load() {
  error.value = ''
  try {
    data.value = await api('/staff/messages/', { query: { handled: handled.value, page: page.value } })
  } catch (e) {
    error.value = e.message
  }
}
watch([handled, page], load, { immediate: true })

async function toggle(m) {
  try {
    const r = await api(`/staff/messages/${m.id}/`, { method: 'PATCH', body: { handled: !m.handled } })
    m.handled = r.handled
  } catch (e) {
    error.value = e.message
  }
}
</script>

<template>
  <section class="container" style="padding-top: 32px">
    <StaffNav />
    <div class="page-head">
      <h1>Contact messages</h1>
      <select v-model="handled" style="width: auto" aria-label="Show" @change="page = 1">
        <option value="false">Waiting for a reply</option>
        <option value="true">Handled</option>
        <option value="">All</option>
      </select>
    </div>
    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="!data && !error" class="spinner"></div>
    <template v-if="data">
      <div v-if="!data.results.length" class="card empty">Nothing here. 🎉</div>
      <div v-for="m in data.results" :key="m.id" class="card msg" :class="{ done: m.handled }">
        <div class="head">
          <div>
            <h3 style="margin: 0">{{ m.subject }}</h3>
            <div class="small muted">
              {{ m.name }} · <a :href="`mailto:${m.email}?subject=Re: ${encodeURIComponent(m.subject)}`">{{ m.email }}</a>
              <template v-if="m.phone"> · <a :href="`tel:${m.phone}`">{{ m.phone }}</a></template>
              · {{ dateTime(m.created_at) }}
            </div>
          </div>
          <button v-if="canChange" class="btn btn-sm" :class="m.handled ? 'btn-outline' : 'btn-dark'" @click="toggle(m)">{{ m.handled ? 'Mark as not handled' : 'Mark as handled' }}</button>
        </div>
        <p class="body">{{ m.message }}</p>
      </div>
      <div v-if="data.count > 20" class="pager">
        <button class="btn btn-outline btn-sm" :disabled="!data.previous" @click="page--">← Previous</button>
        <span class="small muted">Page {{ page }}</span>
        <button class="btn btn-outline btn-sm" :disabled="!data.next" @click="page++">Next →</button>
      </div>
    </template>
  </section>
</template>

<style scoped>
.msg { margin-bottom: 16px; }
.msg.done { opacity: 0.65; }
.head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; }
.body { white-space: pre-wrap; margin: 12px 0 0; }
.pager { display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: 16px; }
</style>
