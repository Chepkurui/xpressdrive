<script setup>
import { dateTime } from '@/utils/format'
defineProps({ events: { type: Array, default: () => [] } })
</script>

<template>
  <ul class="timeline">
    <li v-for="(e, i) in events" :key="i" :class="{ latest: i === 0 }">
      <div class="when small muted">{{ dateTime(e.created_at) }}</div>
      <div class="what">
        <strong>{{ e.status_display }}</strong>
        <div v-if="e.location" class="small muted">📍 {{ e.location }}</div>
        <div v-if="e.note" class="small">{{ e.note }}</div>
      </div>
    </li>
    <li v-if="!events.length" class="muted">No tracking events yet.</li>
  </ul>
</template>

<style scoped>
.timeline { list-style: none; margin: 0; padding: 0; }
li { display: grid; grid-template-columns: 170px 1fr; gap: 16px; padding: 14px 0 14px 20px; border-left: 2px solid var(--border); position: relative; }
li::before { content: ''; position: absolute; left: -7px; top: 18px; width: 12px; height: 12px; border-radius: 50%; background: var(--border); }
li.latest::before { background: var(--amber); box-shadow: 0 0 0 4px #fff1e3; }
@media (max-width: 600px) { li { grid-template-columns: 1fr; gap: 2px; } }
</style>
