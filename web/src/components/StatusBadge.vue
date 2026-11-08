<script setup>
import { computed } from 'vue'
const props = defineProps({ status: String, label: String })
const tone = computed(() => {
  if (props.status === 'delivered') return 'green'
  if (props.status === 'arrived' || props.status === 'completed' || props.status === 'accepted') return 'green'
  if (props.status === 'cancelled' || props.status === 'declined') return 'red'
  if (props.status === 'on_hold' || props.status === 'at_border' || props.status === 'allocated') return 'amber'
  if (props.status === 'booked' || props.status === 'planned') return ''
  return 'blue'
})
</script>

<template>
  <span class="badge" :class="tone">{{ label || status }}</span>
</template>
