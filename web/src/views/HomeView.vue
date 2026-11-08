<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import { date } from '@/utils/format'
import RouteMap from '@/components/RouteMap.vue'

const router = useRouter()
const number = ref('')
function track() {
  const n = number.value.trim().toUpperCase()
  if (n) router.push({ name: 'track', params: { number: n } })
}

const slides = ['/images/truck.webp', '/images/hero-port.webp', '/images/containers-aerial.webp']

const steps = [
  { n: 1, t: 'Book your load', d: 'Tell us the route, what you are moving and when it is ready: one parcel, a few pallets or a full container.' },
  { n: 2, t: 'We match a truck', d: 'We put your cargo on a truck already heading your way, often one going back to base, and confirm your price.' },
  { n: 3, t: 'A vetted driver collects', d: 'The trip is allocated to a driver in our app. Our operations team follows the truck on a live map.' },
  { n: 4, t: 'Follow every milestone', d: 'See each town, weighbridge and border post as your cargo passes it, right through to delivery.' },
]
const services = [
  { img: '/images/handover.webp', chip: '📦 From 1 box', t: 'Parcels', d: 'Small consignments ride on trucks already on your lane.' },
  { img: '/images/warehouse.webp', chip: '🧱 Pay per CBM', t: 'Part loads', d: 'Share a truck with other cargo and pay only for your space.' },
  { img: '/images/truck.webp', chip: '🚛 Door to door', t: 'Full trucks', d: 'A whole truck for your cargo, from your premises to the receiver.' },
  { img: '/images/containers-aerial.webp', chip: '🏗️ 20ft / 40ft', t: 'Containers', d: 'Port and ICD haulage to Kampala, Kigali, Goma, Juba and beyond.' },
]
const lanes = [
  { t: 'Mombasa → Kampala', v: '3–5 days', w: 45 },
  { t: 'Kampala → Goma / Beni', v: '2–4 days', w: 35 },
  { t: 'Kampala → Juba', v: '2–4 days', w: 35 },
  { t: 'Mombasa → Kigali', v: '5–8 days', w: 80 },
]

// Return trucks with space on offer (public: lane, date and space only).
const capacity = ref(null)
onMounted(async () => {
  try {
    capacity.value = await api('/capacity/', { auth: false })
  } catch {
    capacity.value = []
  }
})
function bookLane(c) {
  const mode = c.space === 'empty_container_40' ? 'container_40' : c.space === 'empty_container_20' ? 'container_20' : c.space === 'empty_truck' ? 'full_truck' : 'part_load'
  router.push({ path: '/account/shipments/new', query: { origin: c.origin, destination: c.destination, mode } })
}
</script>

<template>
  <section class="hero">
    <div class="slides" aria-hidden="true">
      <img v-for="(s, i) in slides" :key="s" :src="s" alt="" :style="{ animationDelay: `${i * 6}s` }" :fetchpriority="i === 0 ? 'high' : 'auto'" decoding="async" />
    </div>
    <div class="shade"></div>
    <div class="container hero-inner">
      <div class="intro">
        <div class="eyebrow"><span class="live-dot"></span> Trucks on the road across East Africa, every day</div>
        <h1>Move anything by road, from one parcel to a full container.</h1>
        <p class="lead">
          XpressDrive puts your cargo on trucks already heading your way, including trucks and empty containers returning to base.
          Uganda, Kenya, Rwanda, Tanzania, South Sudan and DR Congo.
        </p>
        <div class="cta">
          <RouterLink to="/account/shipments/new" class="btn btn-primary">Book a truck</RouterLink>
          <a href="#return-trucks" class="btn btn-outline light">See return trucks with space</a>
        </div>
      </div>
      <form class="card track" @submit.prevent="track">
        <h3>Track a booking</h3>
        <label for="tn">Tracking number</label>
        <input id="tn" v-model="number" class="mono" placeholder="e.g. XD7KQ2M9XP4A" maxlength="12" autocomplete="off" />
        <button class="btn btn-dark btn-block" style="margin-top: 12px">Track</button>
        <p class="small muted" style="margin: 12px 0 0">Signed-in customers see charges, receiver details and every milestone in <RouterLink to="/account">My account</RouterLink>.</p>
      </form>
    </div>
  </section>

  <section id="return-trucks" class="section alt">
    <div class="container">
      <div class="board-head" v-reveal>
        <div>
          <div class="eyebrow">Return trucks</div>
          <h2>Space going your way</h2>
          <p class="muted" style="margin: 0">These trucks and containers have delivered and are heading back to base. Fill them at a lower price.</p>
        </div>
        <RouterLink to="/pricing" class="small">Backhaul prices →</RouterLink>
      </div>
      <div v-if="capacity === null" class="spinner"></div>
      <div v-else-if="!capacity.length" class="card flat empty-board">No open return trips right now. Book anyway and we'll match you with the next truck on your lane.</div>
      <ul v-else class="board">
        <li v-for="(c, i) in capacity.slice(0, 8)" :key="i" v-reveal="i * 60" class="card flat lane-card">
          <div class="lane-route"><strong>{{ c.origin_name }}</strong><span aria-hidden="true">→</span><span class="sr"> to </span><strong>{{ c.destination_name }}</strong></div>
          <div class="small muted">{{ c.date_from ? `From ${date(c.date_from)}` : 'Dates to be confirmed' }}<template v-if="c.date_to"> · until {{ date(c.date_to) }}</template></div>
          <div class="lane-foot">
            <span class="badge green">{{ c.space_display }}</span>
            <button type="button" class="btn btn-sm btn-outline" @click="bookLane(c)">Book this lane</button>
          </div>
        </li>
      </ul>
    </div>
  </section>

  <section class="route-band">
    <div class="container">
      <div class="center" v-reveal>
        <div class="eyebrow">Our network</div>
        <h2>From the coast to the Great Lakes, and back</h2>
      </div>
      <div v-reveal="150"><RouteMap /></div>
    </div>
  </section>

  <section class="section">
    <div class="container">
      <div v-reveal>
        <div class="eyebrow">How it works</div>
        <h2>Four simple steps</h2>
      </div>
      <div class="grid grid-4 steps" style="margin-top: 24px">
        <div v-for="(s, i) in steps" :key="s.n" v-reveal="i * 120" class="card flat lift">
          <div class="num">{{ s.n }}</div>
          <h3>{{ s.t }}</h3>
          <p class="muted small">{{ s.d }}</p>
        </div>
      </div>
    </div>
  </section>

  <section class="section alt">
    <div class="container">
      <div v-reveal>
        <div class="eyebrow">Load sizes</div>
        <h2>From one box to a full container</h2>
      </div>
      <div class="grid grid-4" style="margin-top: 24px">
        <RouterLink v-for="(s, i) in services" :key="s.t" v-reveal="i * 120" to="/services" class="card photo-card lift svc">
          <div class="ph">
            <img :src="s.img" :alt="s.t" loading="lazy" decoding="async" />
            <span class="chip">{{ s.chip }}</span>
          </div>
          <div class="body">
            <h3>{{ s.t }}</h3>
            <p class="muted small">{{ s.d }}</p>
            <span class="more">Learn more →</span>
          </div>
        </RouterLink>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="container grid grid-2 delivery">
      <div class="photo" v-reveal>
        <img src="/images/hero-port.webp" alt="Containers waiting at the port" loading="lazy" decoding="async" />
        <div class="float-badge">📍 Milestones at every town &amp; border post</div>
      </div>
      <div>
        <div v-reveal>
          <div class="eyebrow">Transit times</div>
          <h2>How long will it take?</h2>
          <p class="muted">Typical road times from loading, on our busiest lanes.</p>
        </div>
        <ul class="times">
          <li v-for="(t, i) in lanes" :key="t.t" v-reveal="i * 100" :style="{ '--w': t.w + '%' }">
            <span>🚚 {{ t.t }}</span><strong>{{ t.v }}</strong>
            <i class="bar"></i>
          </li>
        </ul>
      </div>
    </div>
  </section>

  <section class="cta-band center">
    <div class="container" v-reveal>
      <h2>Ready to move your cargo?</h2>
      <p class="lead" style="margin: 0 auto 24px">Create a free account, book your first load in a couple of minutes and follow it all the way to the receiver.</p>
      <RouterLink to="/register" class="btn btn-primary">Create free account</RouterLink>
    </div>
  </section>
</template>

<style scoped>
/* Hero with cross-fading, slowly zooming photos */
.hero { position: relative; overflow: hidden; color: #fff; padding: 96px 0 104px; background: var(--navy); isolation: isolate; }
.slides { position: absolute; inset: 0; z-index: -2; }
.slides img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0; animation: slide 18s linear infinite; }
.shade { position: absolute; inset: 0; z-index: -1; background: linear-gradient(100deg, rgba(15, 42, 68, 0.8) 0%, rgba(15, 42, 68, 0.45) 50%, rgba(23, 61, 98, 0.05) 100%); }
@keyframes slide {
  0% { opacity: 0; transform: scale(1); }
  6% { opacity: 1; }
  33% { opacity: 1; }
  40% { opacity: 0; transform: scale(1.14); }
  100% { opacity: 0; transform: scale(1.14); }
}
.hero h1 { color: #fff; }
.hero .lead { color: #dbe6f1; }
.hero .eyebrow { color: var(--amber); display: inline-flex; align-items: center; gap: 8px; }
.live-dot { width: 8px; height: 8px; border-radius: 50%; background: #4ade80; box-shadow: 0 0 0 0 rgba(74, 222, 128, 0.7); animation: ping 1.8s ease-out infinite; }
@keyframes ping { to { box-shadow: 0 0 0 10px rgba(74, 222, 128, 0); } }
.hero-inner { display: grid; grid-template-columns: 1.4fr 1fr; gap: 48px; align-items: center; }
.intro { animation: rise 0.9s cubic-bezier(0.2, 0.7, 0.2, 1) both; }
.track { color: var(--text); animation: rise 0.9s 0.2s cubic-bezier(0.2, 0.7, 0.2, 1) both; backdrop-filter: blur(6px); }
@keyframes rise { from { opacity: 0; transform: translateY(24px); } to { opacity: 1; transform: none; } }
.cta { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 24px; }
.btn-outline.light { color: #fff; border-color: rgba(255, 255, 255, 0.5); backdrop-filter: blur(4px); }
.btn-outline.light:hover { background: rgba(255, 255, 255, 0.1); border-color: #fff; }

/* Route band */
.route-band { position: relative; isolation: isolate; overflow: hidden; color: #fff; padding: 56px 0 40px; background: #0b1f33; }
/* Blurred sea photo: keeps the mood without detail competing with the route map. */
.route-band::before { content: ''; position: absolute; inset: -24px; z-index: -2; background: url('/images/containers-aerial.webp') center 60% / cover; filter: blur(10px) saturate(0.7); }
.route-band::after { content: ''; position: absolute; inset: 0; z-index: -1; background: linear-gradient(rgba(15, 42, 68, 0.35), rgba(15, 42, 68, 0.45)); }
.route-band h2 { color: #fff; }
.route-band .eyebrow { color: var(--amber); }

/* Return-truck board */
.board-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; flex-wrap: wrap; margin-bottom: 20px; }
.board { list-style: none; padding: 0; margin: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 14px; }
.lane-card { padding: 18px; display: flex; flex-direction: column; gap: 6px; }
.lane-route { font-size: 1.1rem; color: var(--navy); display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; }
.lane-route span[aria-hidden] { color: var(--amber-dark); }
.lane-foot { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-top: 6px; flex-wrap: wrap; }
.empty-board { color: var(--muted); }
.sr { position: absolute; left: -9999px; }

/* Steps */
.num { width: 40px; height: 40px; border-radius: 50%; background: var(--amber); color: var(--navy); font-weight: 800; display: grid; place-items: center; margin-bottom: 12px; transition: transform 0.3s; }
.steps .card:hover .num { transform: rotate(-10deg) scale(1.12); }

/* Service photo cards */
.svc { color: inherit; text-decoration: none !important; }
.more { font-weight: 600; font-size: 0.9rem; color: var(--blue); display: inline-block; transition: transform 0.2s; }
.svc:hover .more { transform: translateX(4px); }

/* Delivery times */
.delivery { align-items: center; gap: 48px; }
.photo { position: relative; }
.photo img { width: 100%; aspect-ratio: 4 / 3; object-fit: cover; border-radius: 18px; display: block; box-shadow: var(--shadow); }
.float-badge { position: absolute; right: -8px; bottom: 24px; background: var(--surface); color: var(--navy); font-weight: 700; font-size: 0.9rem; padding: 12px 16px; border-radius: 12px; box-shadow: 0 12px 30px rgba(15, 42, 68, 0.2); animation: bob 4s ease-in-out infinite; max-width: 80%; }
@keyframes bob { 50% { transform: translateY(-8px); } }
.times { list-style: none; padding: 0; margin: 16px 0 0; }
.times li { position: relative; overflow: hidden; display: flex; justify-content: space-between; padding: 16px 20px; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; margin-bottom: 10px; }
.times .bar { position: absolute; left: 0; bottom: 0; height: 3px; width: 0; background: linear-gradient(90deg, var(--amber), var(--amber-dark)); transition: width 1.2s cubic-bezier(0.2, 0.7, 0.2, 1) calc(var(--reveal-delay, 0ms) + 300ms); }
.times li.in .bar { width: var(--w); }

/* Closing CTA with parallax photo */
.cta-band { color: #fff; padding: 88px 0; background: linear-gradient(rgba(15, 42, 68, 0.58), rgba(15, 42, 68, 0.68)), url('/images/truck.webp') center / cover fixed; }
.cta-band h2 { color: #fff; }
.cta-band .lead { color: #dbe6f1; }

@media (max-width: 860px) {
  .hero { padding: 64px 0 72px; }
  .hero-inner { grid-template-columns: 1fr; }
  .float-badge { right: 12px; }
  /* fixed backgrounds are janky / unsupported on mobile */
  .cta-band { background-attachment: scroll; }
}
@media (prefers-reduced-motion: reduce) {
  .slides img { animation: none; }
  .slides img:first-child { opacity: 1; }
  .intro, .track, .float-badge, .live-dot { animation: none; }
  .times .bar { transition: none; }
}
</style>
