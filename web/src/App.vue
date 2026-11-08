<script setup>
import AppHeader from '@/components/AppHeader.vue'
import AppFooter from '@/components/AppFooter.vue'
</script>

<template>
  <AppHeader />
  <main>
    <RouterView :key="$route.path" />
  </main>
  <AppFooter />
</template>

<style>
#app { min-height: 100vh; display: flex; flex-direction: column; }
main { flex: 1; }
</style>
