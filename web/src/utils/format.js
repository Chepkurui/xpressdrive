export const money = (v) =>
  v == null || v === '' ? '—' : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Number(v))

export const date = (v) => (v ? new Date(v).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : '—')

export const dateTime = (v) =>
  v ? new Date(v).toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'

export const days = (min, max) => (min === max ? `${min} days` : `${min}–${max} days`)

export const weeks = (min, max) => {
  const a = Math.round(min / 7)
  const b = Math.round(max / 7)
  return a === b ? `~${a} weeks` : `${a}–${b} weeks`
}

export const STATUS_STEPS = [
  { key: 'booked', label: 'Booked' },
  { key: 'confirmed', label: 'Confirmed' },
  { key: 'allocated', label: 'Truck allocated' },
  { key: 'loaded', label: 'Loaded' },
  { key: 'in_transit', label: 'In transit' },
  { key: 'at_border', label: 'Border / customs' },
  { key: 'arrived', label: 'Arrived' },
  { key: 'delivered', label: 'Delivered' },
]

export const CATEGORIES = [
  ['general', 'General goods'],
  ['fmcg', 'Food, drinks & FMCG'],
  ['agriculture', 'Agricultural produce'],
  ['electronics', 'Electronics & phones'],
  ['clothing', 'Clothing, shoes & bags'],
  ['home', 'Home, kitchen & furniture'],
  ['machinery', 'Machinery & spare parts'],
  ['building', 'Building & hardware'],
  ['other', 'Other'],
]

// Load types, from one parcel up to a full container.
export const MODES = [
  ['parcel', 'Parcel / small goods'],
  ['part_load', 'Part load (shared truck)'],
  ['full_truck', 'Full truck load'],
  ['container_20', '20ft container'],
  ['container_40', '40ft container'],
]
export const MODE_HINTS = {
  parcel: 'Boxes and small consignments, charged by weight.',
  part_load: 'Pallets or bulk that share a truck, charged by volume (CBM).',
  full_truck: 'A whole truck for your cargo, door to door.',
  container_20: 'A 20ft container from the port, ICD or your premises.',
  container_40: 'A 40ft container from the port, ICD or your premises.',
}

// Every booking status, in journey order (used by the staff portal).
export const STATUSES = [
  ...STATUS_STEPS.map((s) => [s.key, s.label]),
  ['on_hold', 'On hold'],
  ['cancelled', 'Cancelled'],
]

export const PAYMENT_STATUSES = [
  ['pending', 'Awaiting quote'],
  ['unpaid', 'Unpaid'],
  ['paid', 'Paid'],
  ['waived', 'Waived'],
]

export const TRIP_STATUSES = [
  ['planned', 'Planned — accepting cargo'],
  ['allocated', 'Allocated — awaiting driver'],
  ['accepted', 'Accepted by driver'],
  ['loading', 'Loading at origin'],
  ['in_transit', 'In transit'],
  ['at_border', 'At border / customs'],
  ['arrived', 'Arrived'],
  ['completed', 'Completed'],
  ['cancelled', 'Cancelled'],
]
export const LIVE_TRIP_STATUSES = ['accepted', 'loading', 'in_transit', 'at_border', 'arrived']

export const TRUCK_TYPES = [
  ['van', 'Van / pickup (up to 3 t)'],
  ['rigid', 'Rigid truck (5–15 t)'],
  ['flatbed', 'Trailer — flatbed / skeletal'],
  ['box_trailer', 'Trailer — box / curtain-side'],
  ['container_20', 'Container carrier — 20ft'],
  ['container_40', 'Container carrier — 40ft'],
]

export const SPACE_TYPES = [
  ['empty_truck', 'Empty truck'],
  ['empty_container_20', 'Empty 20ft container'],
  ['empty_container_40', 'Empty 40ft container'],
  ['partial', 'Part space available'],
]

export const ago = (v) => {
  if (!v) return 'never'
  const s = Math.max(0, (Date.now() - new Date(v).getTime()) / 1000)
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.round(s / 60)} min ago`
  if (s < 86400) return `${Math.round(s / 3600)} h ago`
  return `${Math.round(s / 86400)} d ago`
}
