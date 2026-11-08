<script setup>
// Popup form for changing the signed-in user's password. The profile page only
// mounts (and lazy-loads) this when the user clicks "Change password".
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, ApiError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const emit = defineEmits(['close'])
const auth = useAuthStore()
const router = useRouter()

const dlg = ref(null)
const first = ref(null)
const pw = reactive({ current_password: '', new_password: '', confirm: '' })
const error = ref('')
const busy = ref(false)

onMounted(() => {
  dlg.value.showModal()
  first.value.focus()
})

function close() {
  if (busy.value) return
  dlg.value.close()
}

// Clicking the dimmed backdrop (outside the panel) closes the dialog.
function onBackdrop(e) {
  if (e.target === dlg.value) close()
}

async function submit() {
  error.value = ''
  if (pw.new_password !== pw.confirm) return (error.value = 'New passwords do not match.')
  busy.value = true
  try {
    await api('/auth/password/change/', { method: 'POST', body: { current_password: pw.current_password, new_password: pw.new_password } })
    auth.clearLocal()
    router.replace({ name: 'login' })
  } catch (e) {
    error.value = e instanceof ApiError ? e.field('current_password') || e.field('new_password') || e.message : 'Could not change password.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <dialog ref="dlg" aria-labelledby="cpw-title" @close="emit('close')" @cancel.prevent="close" @click="onBackdrop">
    <form class="panel" @submit.prevent="submit">
      <div class="head">
        <h3 id="cpw-title">Change password</h3>
        <button type="button" class="x" aria-label="Close" :disabled="busy" @click="close">&times;</button>
      </div>
      <p class="small muted">You'll be signed out on all devices afterwards.</p>
      <div v-if="error" class="alert alert-error" role="alert">{{ error }}</div>
      <div class="field"><label for="cp">Current password</label><input id="cp" ref="first" v-model="pw.current_password" type="password" autocomplete="current-password" required /></div>
      <div class="field"><label for="np">New password</label><input id="np" v-model="pw.new_password" type="password" autocomplete="new-password" minlength="10" required /><div class="small muted">At least 10 characters.</div></div>
      <div class="field"><label for="cf">Confirm new password</label><input id="cf" v-model="pw.confirm" type="password" autocomplete="new-password" required /></div>
      <div class="actions">
        <button type="button" class="btn btn-outline" :disabled="busy" @click="close">Cancel</button>
        <button class="btn btn-dark" :disabled="busy">{{ busy ? 'Changing…' : 'Change password' }}</button>
      </div>
    </form>
  </dialog>
</template>

<style scoped>
dialog { border: 0; padding: 0; border-radius: 14px; width: min(440px, calc(100vw - 32px)); max-height: calc(100vh - 32px); box-shadow: 0 24px 60px rgba(0, 0, 0, 0.25); background: #fff; color: inherit; }
dialog::backdrop { background: rgba(15, 23, 42, 0.55); }
dialog[open] { animation: pop 0.18s ease-out; }
.panel { padding: 24px; }
.head { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.head h3 { margin: 0; }
.x { border: 0; background: none; font-size: 1.6rem; line-height: 1; cursor: pointer; color: var(--muted); padding: 4px 8px; }
.x:hover { color: inherit; }
.actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 8px; }
@keyframes pop { from { opacity: 0; transform: translateY(8px) scale(0.98); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) { dialog[open] { animation: none; } }
</style>
