<script setup>
defineProps({
  image: { type: String, required: true },
  eyebrow: { type: String, default: '' },
  title: { type: String, required: true },
  lead: { type: String, default: '' },
  position: { type: String, default: 'center' },
})
</script>

<template>
  <section class="banner">
    <img class="bg" :src="image" alt="" :style="{ objectPosition: position }" fetchpriority="high" decoding="async" />
    <div class="shade"></div>
    <div class="container inner">
      <div v-if="eyebrow" class="eyebrow">{{ eyebrow }}</div>
      <h1>{{ title }}</h1>
      <p v-if="lead" class="lead">{{ lead }}</p>
      <slot />
    </div>
  </section>
</template>

<style scoped>
.banner { position: relative; overflow: hidden; color: #fff; padding: 88px 0 72px; background: var(--navy); isolation: isolate; }
.bg { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; z-index: -2; animation: drift 24s ease-in-out infinite alternate; }
.shade { position: absolute; inset: 0; z-index: -1; background: linear-gradient(100deg, rgba(15, 42, 68, 0.8) 0%, rgba(15, 42, 68, 0.48) 45%, rgba(15, 42, 68, 0.05) 100%); }
.inner { animation: rise 0.8s cubic-bezier(0.2, 0.7, 0.2, 1) both; }
h1 { color: #fff; max-width: 760px; }
.eyebrow { color: var(--amber); }
.lead { color: #dbe6f1; }
@keyframes drift { from { transform: scale(1.02); } to { transform: scale(1.12) translate(-1.5%, -1%); } }
@keyframes rise { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) { .bg, .inner { animation: none; } }
</style>
