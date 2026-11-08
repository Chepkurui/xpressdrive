// Towns, ports and border posts served (from /api/places/), loaded once per page load.
import { computed, ref } from 'vue'
import { api } from '@/api/client'

const places = ref([])
let loading = null

export function usePlaces() {
  if (!loading) {
    loading = api('/places/', { auth: false })
      .then((rows) => (places.value = rows))
      .catch(() => { loading = null })
  }
  // Grouped by country for <optgroup>; border posts listed last.
  const grouped = computed(() => {
    const groups = {}
    for (const p of places.value) {
      const key = p.kind === 'border' ? 'Border posts' : p.country
      ;(groups[key] ||= []).push(p)
    }
    return Object.entries(groups).sort(([a], [b]) => (a === 'Border posts') - (b === 'Border posts'))
  })
  const name = (code) => places.value.find((p) => p.code === code)?.name || code || ''
  return { places, grouped, name }
}
