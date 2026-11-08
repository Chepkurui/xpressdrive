<script setup>
import { reactive, ref } from 'vue'
import { api, ApiError } from '@/api/client'
import PageBanner from '@/components/PageBanner.vue'

const form = reactive({ name: '', email: '', phone: '', subject: '', message: '', website: '' })
const sent = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    const res = await api('/contact/', { method: 'POST', body: { ...form }, auth: false })
    sent.value = res.detail
    Object.assign(form, { name: '', email: '', phone: '', subject: '', message: '' })
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Something went wrong. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <PageBanner
    image="/images/warehouse-aisle.webp"
    eyebrow="About us"
    title="XpressDrive"
    lead="We keep East Africa's trucks full, and your freight costs down."
  />
  <section class="section">
    <div class="container grid grid-2" style="align-items: start">
      <div v-reveal>
        <div class="collage">
          <img src="/images/warehouse.webp" alt="Cargo sorted at our depot" loading="lazy" decoding="async" />
          <img src="/images/handover.webp" alt="Parcel handed over to a customer" loading="lazy" decoding="async" />
        </div>
        <p>Every day, trucks and containers drive back to base empty after a delivery: Mombasa to Kampala, Goma to Kampala, Juba to Gulu. XpressDrive connects cargo owners with those trucks, and with scheduled trucks on the same lanes, so goods move for less and drivers earn on both legs.</p>
        <p>You book anything from a parcel to a full container. Our operations team matches it to a truck, allocates the trip to a vetted driver, and follows the truck on our live dashboard until your cargo is delivered.</p>
        <h3>Why customers choose us</h3>
        <ul>
          <li>Parcels, part loads, full trucks and 20ft/40ft containers</li>
          <li>Lower prices on return-leg (backhaul) trucks</li>
          <li>Milestone updates at every major town and border post</li>
          <li>Vetted drivers, tracked by our operations team on every trip</li>
        </ul>
        <h3>Offices</h3>
        <p class="muted">Kampala, Uganda — head office &amp; depot<br />Mombasa &amp; Nairobi, Kenya — port and city desks</p>
      </div>

      <div class="card contact" v-reveal="150">
        <h3>Contact us</h3>
        <div v-if="sent" class="alert alert-success">{{ sent }}</div>
        <div v-if="error" class="alert alert-error">{{ error }}</div>
        <form @submit.prevent="submit">
          <div class="hp" aria-hidden="true"><label>Website<input v-model="form.website" tabindex="-1" autocomplete="off" /></label></div>
          <div class="field"><label for="cn">Name</label><input id="cn" v-model="form.name" maxlength="120" required /></div>
          <div class="row">
            <div class="field"><label for="ce">Email</label><input id="ce" v-model="form.email" type="email" required /></div>
            <div class="field"><label for="cp">Phone</label><input id="cp" v-model="form.phone" type="tel" placeholder="+256…" /></div>
          </div>
          <div class="field"><label for="cs">Subject</label><input id="cs" v-model="form.subject" maxlength="150" required /></div>
          <div class="field"><label for="cm">Message</label><textarea id="cm" v-model="form.message" maxlength="3000" required></textarea></div>
          <button class="btn btn-primary btn-block" :disabled="loading">{{ loading ? 'Sending…' : 'Send message' }}</button>
        </form>
      </div>
    </div>
  </section>
</template>

<style scoped>
.collage { display: grid; grid-template-columns: 1.5fr 1fr; gap: 12px; margin-bottom: 24px; }
.collage img { width: 100%; height: 220px; object-fit: cover; border-radius: 14px; display: block; box-shadow: var(--shadow); transition: transform 0.5s cubic-bezier(0.2, 0.7, 0.2, 1); }
.collage img:hover { transform: scale(1.03) rotate(-0.5deg); }
.contact { position: sticky; top: 92px; }
@media (max-width: 640px) { .collage img { height: 160px; } .contact { position: static; } }
@media (prefers-reduced-motion: reduce) { .collage img { transition: none; } .collage img:hover { transform: none; } }
</style>
