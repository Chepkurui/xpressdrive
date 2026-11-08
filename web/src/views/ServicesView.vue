<script setup>
import PageBanner from '@/components/PageBanner.vue'
const services = [
  {
    t: 'Parcels & small goods', icon: '📦', img: '/images/handover.webp',
    d: 'Boxes, spare parts and shop restocks ride with other cargo on trucks already heading your way. Charged by chargeable weight.',
    points: ['1–4 days within the region', 'Depot drop-off or pickup', 'Milestone updates at every major town'],
  },
  {
    t: 'Part loads (shared truck)', icon: '🧱', img: '/images/warehouse.webp',
    d: 'Pallets and bulk that don\'t fill a truck. We combine your cargo with others on the same lane and you pay only for the cubic metres you use.',
    points: ['2–6 days within the region', 'Charged per CBM, small minimum', 'Business stock, produce, furniture'],
  },
  {
    t: 'Full truck loads', icon: '🚛', img: '/images/truck.webp',
    d: 'A whole flatbed, box or curtain-side trailer for your cargo, loaded at your premises and driven straight to the receiver.',
    points: ['Door to door', 'Up to about 30 tonnes', 'Cement, iron sheets, produce, machinery'],
  },
  {
    t: 'Container haulage (20ft / 40ft)', icon: '🏗️', img: '/images/containers-aerial.webp',
    d: 'Port and ICD pickups at Mombasa, Naivasha and Dar es Salaam, delivered to Kampala, Kigali, Goma, Juba and beyond. Empty boxes returned for you.',
    points: ['Mombasa → Kampala in 3–7 days', 'Transit to DR Congo & South Sudan', 'Empty-container return included on request'],
  },
  {
    t: 'Return-leg (backhaul) space', icon: '↩️', img: '/images/hero-port.webp',
    d: 'Trucks and empty containers that have delivered and are going back to base. We fill them with your cargo at a lower price, so you pay less and trucks don\'t travel empty.',
    points: ['Lower prices than a dedicated truck', 'See current space on the home page', 'Dates follow the truck'],
  },
  {
    t: 'Border & delivery support', icon: '🧾', img: '/images/port-cranes.webp',
    d: 'We work with licensed clearing agents at the main border posts and tell you when your cargo reaches each one. Collect from our depot or have it delivered.',
    points: ['Malaba, Busia, Mpondwe, Katuna, Elegu', 'Clearing-agent introductions', 'Last-mile delivery on request'],
  },
]
</script>

<template>
  <PageBanner
    image="/images/port-cranes.webp"
    eyebrow="Our services"
    title="Road freight for every load size"
    lead="From one box to a convoy of containers, across Uganda, Kenya, Rwanda, Tanzania, South Sudan and DR Congo. We match your cargo with trucks on your lane, including those returning to base, so you pay less."
  />
  <section class="section">
    <div class="container">
      <div class="grid grid-2">
        <div v-for="(s, i) in services" :key="s.t" v-reveal="(i % 2) * 120" class="card photo-card lift">
          <div class="ph">
            <img :src="s.img" :alt="s.t" loading="lazy" decoding="async" />
            <span class="chip">{{ s.icon }} {{ s.points[0] }}</span>
          </div>
          <div class="body">
            <h3>{{ s.t }}</h3>
            <p class="muted">{{ s.d }}</p>
            <ul><li v-for="p in s.points.slice(1)" :key="p">{{ p }}</li></ul>
          </div>
        </div>
      </div>

      <div class="card" style="margin-top: 32px" v-reveal>
        <h3>What we cannot ship</h3>
        <p class="muted">For safety and legal reasons we do not carry weapons, explosives, drugs, counterfeit goods, live animals or anything prohibited in the origin, transit or destination country. Fuel, gas, chemicals and batteries need hazardous-goods handling and permits, so tick "Hazardous" when you book.</p>
      </div>
      <div class="center" style="margin-top: 32px">
        <RouterLink to="/pricing" class="btn btn-primary">Get a price estimate</RouterLink>
      </div>
    </div>
  </section>
</template>

<style scoped>
ul { padding-left: 18px; margin: 0; }
li { margin-bottom: 4px; }
</style>
