<script setup>
// Staff-only map of trucks (last known positions) and, optionally, one trip's GPS trail.
// Coordinates never reach cargo owners; this component is only used in Staff Operations.
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const props = defineProps({
  trips: { type: Array, default: () => [] }, // [{ code, status, stale, last_position: {lat,lng,...}, ... }]
  trail: { type: Array, default: () => [] }, // [{ lat, lng, recorded_at }]
  selected: { type: String, default: '' },
  height: { type: String, default: '520px' },
  fitOnChange: { type: Boolean, default: false },
})
const emit = defineEmits(['select'])

const el = ref(null)
let map
let markers
let trailLayer
let fitted = false
const EAST_AFRICA = [[-5.2, 28.6], [5.2, 40.2]]

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]))

function icon(t) {
  const tone = t.stale ? 'stale' : t.status === 'at_border' ? 'border' : t.status === 'in_transit' ? 'moving' : 'idle'
  const sel = t.code === props.selected ? ' sel' : ''
  return L.divIcon({
    className: '',
    html: `<div class="truck-pin ${tone}${sel}"><span>🚚</span><b>${esc(t.truck?.plate_number || t.code)}</b></div>`,
    iconSize: null,
    iconAnchor: [14, 14],
  })
}

function draw() {
  if (!map) return
  markers.clearLayers()
  const pts = []
  for (const t of props.trips) {
    const p = t.last_position
    if (!p) continue
    const m = L.marker([p.lat, p.lng], { icon: icon(t), keyboard: true, title: `${t.code} ${t.origin_name} → ${t.destination_name}` })
    m.on('click', () => emit('select', t.code))
    m.bindTooltip(`<strong>${esc(t.code)}</strong> · ${esc(t.status_display)}<br>${esc(t.origin_name)} → ${esc(t.destination_name)}<br>${esc(t.driver?.full_name || 'No driver')}`, { direction: 'top', offset: [0, -12] })
    m.addTo(markers)
    pts.push([p.lat, p.lng])
  }
  trailLayer.clearLayers()
  if (props.trail.length > 1) {
    const line = props.trail.map((p) => [p.lat, p.lng])
    L.polyline(line, { color: '#ff8a1f', weight: 4, opacity: 0.85 }).addTo(trailLayer)
    L.circleMarker(line[0], { radius: 6, color: '#0f2a44', fillColor: '#fff', fillOpacity: 1, weight: 3 }).bindTooltip('Start of trail').addTo(trailLayer)
    pts.push(...line)
  }
  if (pts.length && (!fitted || props.fitOnChange)) {
    map.fitBounds(L.latLngBounds(pts).pad(0.25), { maxZoom: 11 })
    fitted = true
  }
}

onMounted(() => {
  map = L.map(el.value, { scrollWheelZoom: false, worldCopyJump: true }).fitBounds(EAST_AFRICA)
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map)
  markers = L.layerGroup().addTo(map)
  trailLayer = L.layerGroup().addTo(map)
  map.on('focus', () => map.scrollWheelZoom.enable())
  map.on('blur', () => map.scrollWheelZoom.disable())
  draw()
})
onBeforeUnmount(() => map?.remove())
watch(() => [props.trips, props.trail, props.selected], draw, { deep: true })

defineExpose({
  focus(code) {
    const t = props.trips.find((x) => x.code === code)
    if (t?.last_position && map) map.setView([t.last_position.lat, t.last_position.lng], Math.max(map.getZoom(), 9))
  },
})
</script>

<template>
  <div ref="el" class="fleet-map" :style="{ height }" role="application" aria-label="Map of trucks under way"></div>
</template>

<style>
.fleet-map { width: 100%; min-height: 360px; border-radius: var(--radius); border: 1px solid var(--border); z-index: 0; }
.truck-pin { display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px 3px 4px; border-radius: 999px; background: #fff; border: 2px solid var(--navy); box-shadow: 0 4px 10px rgba(15, 42, 68, 0.3); white-space: nowrap; font: 700 11px/1.2 Inter, system-ui, sans-serif; color: var(--navy); transform: translate(-4px, -4px); }
.truck-pin span { font-size: 15px; }
.truck-pin.moving { border-color: #1f9d55; }
.truck-pin.border { border-color: var(--amber); }
.truck-pin.stale { border-color: var(--danger); background: #fdecea; }
.truck-pin.idle { border-color: var(--muted); }
.truck-pin.sel { background: var(--navy); color: #fff; }
</style>
