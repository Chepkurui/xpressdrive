<script setup>
// "Part 2 of 3": a customer's cargo split across trucks. Parts always belong
// to the same customer, so this never shows anyone else's cargo.
import { date } from '@/utils/format'
import StatusBadge from '@/components/StatusBadge.vue'

defineProps({
  part: { type: Object, required: true },
  base: { type: String, required: true }, // e.g. '/account/shipments'
})
</script>

<template>
  <div class="parts card flat">
    <div class="head">
      <strong>Part {{ part.number }} of {{ part.count }}</strong>
      <span class="small muted">This cargo travels on {{ part.count }} trucks so it can move as space allows.</span>
    </div>
    <ul>
      <li v-for="p in part.siblings" :key="p.tracking_number">
        <RouterLink :to="`${base}/${p.tracking_number}`" class="mono">{{ p.tracking_number }}</RouterLink>
        <span v-if="p.tracking_number === part.original" class="small muted">original</span>
        <StatusBadge :status="p.status" :label="p.status_display" />
        <span v-if="p.eta_date" class="small muted">ETA {{ date(p.eta_date) }}</span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.parts { margin-bottom: 20px; border-left: 4px solid var(--amber); }
.head { display: flex; flex-wrap: wrap; gap: 4px 12px; align-items: baseline; margin-bottom: 8px; }
ul { list-style: none; margin: 0; padding: 0; }
li { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 6px 0; border-top: 1px solid var(--border); }
</style>
