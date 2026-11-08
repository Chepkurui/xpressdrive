<script setup>
import { computed } from 'vue'
import { STATUS_STEPS } from '@/utils/format'
const props = defineProps({ status: String })
const current = computed(() => STATUS_STEPS.findIndex((s) => s.key === props.status))
</script>

<template>
  <ol v-if="current >= 0" class="steps" aria-label="Booking progress">
    <li v-for="(s, i) in STATUS_STEPS" :key="s.key" :class="{ done: i < current, current: i === current }">
      <span class="dot"></span><span class="lbl">{{ s.label }}</span>
    </li>
  </ol>
</template>

<style scoped>
.steps { list-style: none; padding: 0; margin: 0 0 8px; display: grid; grid-template-columns: repeat(8, 1fr); gap: 4px; }
li { display: flex; flex-direction: column; align-items: center; text-align: center; font-size: 0.72rem; color: var(--muted); position: relative; }
li::before { content: ''; position: absolute; top: 8px; left: -50%; width: 100%; height: 3px; background: var(--border); z-index: 0; }
li:first-child::before { display: none; }
li.done::before, li.current::before { background: var(--amber); }
.dot { width: 18px; height: 18px; border-radius: 50%; background: var(--border); z-index: 1; margin-bottom: 6px; border: 3px solid #fff; box-shadow: 0 0 0 1px var(--border); }
li.done .dot { background: var(--amber); }
li.current .dot { background: var(--navy); box-shadow: 0 0 0 3px var(--amber); }
li.current { color: var(--navy); font-weight: 700; }
@media (max-width: 700px) { .lbl { display: none; } li.current .lbl { display: block; position: absolute; top: 26px; white-space: nowrap; } .steps { margin-bottom: 28px; } }
</style>
