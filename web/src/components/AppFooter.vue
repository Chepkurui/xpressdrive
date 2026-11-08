<template>
  <footer class="footer">
    <div class="container grid grid-4">
      <div>
        <h4>XpressDrive</h4>
        <p class="small">Road freight across East Africa and DR Congo. We match your cargo with trucks and containers already heading your way, often on their trip back to base.</p>
      </div>
      <div>
        <h4>Services</h4>
        <RouterLink to="/services">Parcels &amp; part loads</RouterLink>
        <RouterLink to="/services">Full trucks</RouterLink>
        <RouterLink to="/services">Container haulage</RouterLink>
        <RouterLink :to="{ path: '/', hash: '#return-trucks' }">Return-truck space</RouterLink>
      </div>
      <div>
        <h4>Customers</h4>
        <RouterLink to="/pricing">Pricing &amp; delivery times</RouterLink>
        <RouterLink to="/track">Track a booking</RouterLink>
        <RouterLink to="/register">Create account</RouterLink>
      </div>
      <div>
        <h4>Contact</h4>
        <p class="small">Kampala, Uganda<br />Nairobi &amp; Mombasa, Kenya<br />info@xpressdrive.co.ug</p>
      </div>
    </div>
    <div class="container copy small">© {{ new Date().getFullYear() }} XpressDrive. All rights reserved.</div>
  </footer>
</template>

<style scoped>
.footer { background: var(--navy); color: #b9c8d8; padding: 48px 0 24px; margin-top: 64px; }
h4 { color: #fff; margin: 0 0 12px; }
a { display: block; color: #b9c8d8; margin-bottom: 6px; font-size: 0.9rem; }
.copy { border-top: 1px solid rgba(255, 255, 255, 0.1); margin-top: 32px; padding-top: 16px; }
</style>
