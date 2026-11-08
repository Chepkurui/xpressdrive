<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const open = ref(false)
watch(() => route.fullPath, () => (open.value = false))

const scrolled = ref(false)
const onScroll = () => (scrolled.value = window.scrollY > 8)
onMounted(() => { onScroll(); window.addEventListener('scroll', onScroll, { passive: true }) })
onBeforeUnmount(() => window.removeEventListener('scroll', onScroll))

async function logout() {
  await auth.logout()
  router.push({ name: 'home' })
}
</script>

<template>
  <header class="header" :class="{ scrolled }">
    <div class="container bar">
      <RouterLink to="/" class="brand" aria-label="XpressDrive home">
        <span class="logo" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="22" height="22"><path d="M3 7h10v8H3zM13 10h4l3 3v2h-7z" fill="currentColor" /><circle cx="7" cy="17" r="2" fill="currentColor" /><circle cx="17" cy="17" r="2" fill="currentColor" /></svg>
        </span>
        <span class="word"><strong>Xpress</strong><em>Drive</em></span>
      </RouterLink>
      <button class="burger" :aria-expanded="open" aria-label="Toggle menu" @click="open = !open">☰</button>
      <nav :class="{ open }">
        <RouterLink to="/services">Services</RouterLink>
        <RouterLink :to="{ path: '/', hash: '#return-trucks' }">Return trucks</RouterLink>
        <RouterLink to="/pricing">Pricing</RouterLink>
        <RouterLink to="/track">Track</RouterLink>
        <RouterLink to="/about">About &amp; Contact</RouterLink>
        <template v-if="auth.isAuthenticated">
          <RouterLink v-if="auth.isStaff" to="/staff" class="btn btn-primary btn-sm">Staff Operations</RouterLink>
          <RouterLink to="/account" class="btn btn-outline btn-sm">My account</RouterLink>
          <button class="btn btn-sm btn-dark" @click="logout">Sign out</button>
        </template>
        <template v-else>
          <RouterLink to="/login">Sign in</RouterLink>
          <RouterLink to="/register" class="btn btn-primary btn-sm">Create account</RouterLink>
        </template>
      </nav>
    </div>
  </header>
</template>

<style scoped>
.header { background: var(--navy); color: #fff; position: sticky; top: 0; z-index: 20; transition: background 0.3s, box-shadow 0.3s; }
.header.scrolled { background: rgba(15, 42, 68, 0.9); backdrop-filter: saturate(160%) blur(10px); box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18); }
.logo { transition: transform 0.4s cubic-bezier(0.2, 0.7, 0.2, 1); }
.brand:hover .logo { transform: rotate(-8deg) scale(1.08); }
nav a:not(.btn) { position: relative; }
nav a:not(.btn)::after { content: ''; position: absolute; left: 0; right: 0; bottom: -6px; height: 2px; background: var(--amber); transform: scaleX(0); transform-origin: left; transition: transform 0.25s; }
nav a:not(.btn):hover { text-decoration: none; color: #fff; }
nav a:not(.btn):hover::after, nav a.router-link-active:not(.btn)::after { transform: scaleX(1); }
.bar { display: flex; align-items: center; justify-content: space-between; height: 68px; }
.brand { display: flex; align-items: center; gap: 10px; color: #fff; text-decoration: none !important; }
.word { font-size: 1.2rem; letter-spacing: -0.01em; }
.word em { font-style: normal; font-weight: 800; color: var(--amber); }
.logo { width: 36px; height: 36px; border-radius: 9px; background: var(--amber); color: var(--navy); display: grid; place-items: center; font-weight: 900; }
nav { display: flex; align-items: center; gap: 22px; }
nav a:not(.btn) { color: #d6e2ee; font-weight: 500; font-size: 0.95rem; }
nav a.router-link-active:not(.btn) { color: var(--amber); }
/* The global outline button has dark red text, which vanishes on the red header. */
nav .btn-outline { color: #fff; border-color: rgba(255, 255, 255, 0.55); }
nav .btn-outline:hover, nav .btn-outline.router-link-active { color: #fff; background: rgba(255, 255, 255, 0.12); border-color: #fff; }
.burger { display: none; background: none; border: 0; color: #fff; font-size: 1.5rem; cursor: pointer; }
@media (max-width: 860px) {
  .burger { display: block; }
  nav { display: none; position: absolute; top: 68px; left: 0; right: 0; background: var(--navy); flex-direction: column; align-items: flex-start; padding: 16px; gap: 14px; }
  nav.open { display: flex; }
}
</style>
