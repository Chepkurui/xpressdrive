import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/', name: 'home', component: () => import('@/views/HomeView.vue') },
  { path: '/services', name: 'services', component: () => import('@/views/ServicesView.vue'), meta: { title: 'Services' } },
  { path: '/pricing', name: 'pricing', component: () => import('@/views/PricingView.vue'), meta: { title: 'Pricing & delivery times' } },
  { path: '/track/:number?', name: 'track', component: () => import('@/views/TrackView.vue'), meta: { title: 'Track a booking' } },
  { path: '/about', name: 'about', component: () => import('@/views/AboutView.vue'), meta: { title: 'About & contact' } },

  { path: '/login', name: 'login', component: () => import('@/views/auth/LoginView.vue'), meta: { guestOnly: true, title: 'Sign in' } },
  { path: '/register', name: 'register', component: () => import('@/views/auth/RegisterView.vue'), meta: { guestOnly: true, title: 'Create account' } },
  { path: '/forgot-password', name: 'forgot', component: () => import('@/views/auth/ForgotPasswordView.vue'), meta: { guestOnly: true, title: 'Forgot password' } },
  { path: '/reset-password', name: 'reset', component: () => import('@/views/auth/ResetPasswordView.vue'), meta: { title: 'Reset password' } },

  { path: '/account', name: 'dashboard', component: () => import('@/views/account/DashboardView.vue'), meta: { requiresAuth: true, title: 'My dashboard' } },
  { path: '/account/shipments', name: 'shipments', component: () => import('@/views/account/ShipmentsView.vue'), meta: { requiresAuth: true, title: 'My bookings' } },
  { path: '/account/shipments/new', name: 'shipment-new', component: () => import('@/views/account/ShipmentFormView.vue'), meta: { requiresAuth: true, title: 'Book a truck' } },
  { path: '/account/shipments/:number', name: 'shipment-detail', component: () => import('@/views/account/ShipmentDetailView.vue'), meta: { requiresAuth: true, title: 'Booking details' } },
  { path: '/account/shipments/:number/edit', name: 'shipment-edit', component: () => import('@/views/account/ShipmentFormView.vue'), meta: { requiresAuth: true, title: 'Edit booking' } },
  { path: '/account/profile', name: 'profile', component: () => import('@/views/account/ProfileView.vue'), meta: { requiresAuth: true, title: 'My profile' } },

  { path: '/staff', name: 'staff', component: () => import('@/views/staff/StaffDashboardView.vue'), meta: { requiresStaff: true, title: 'Staff Operations' } },
  { path: '/staff/shipments', name: 'staff-shipments', component: () => import('@/views/staff/StaffShipmentsView.vue'), meta: { requiresStaff: true, title: 'Bookings · Staff Operations' } },
  { path: '/staff/shipments/:number', name: 'staff-shipment', component: () => import('@/views/staff/StaffShipmentView.vue'), meta: { requiresStaff: true, title: 'Booking · Staff Operations' } },
  { path: '/staff/live', name: 'staff-live', component: () => import('@/views/staff/StaffLiveView.vue'), meta: { requiresStaff: true, title: 'Live trips · Staff Operations' } },
  { path: '/staff/trips', name: 'staff-trips', component: () => import('@/views/staff/StaffTripsView.vue'), meta: { requiresStaff: true, title: 'Trips · Staff Operations' } },
  { path: '/staff/trips/:code', name: 'staff-trip', component: () => import('@/views/staff/StaffTripView.vue'), meta: { requiresStaff: true, title: 'Trip · Staff Operations' } },
  { path: '/staff/empty-legs', name: 'staff-empty-legs', component: () => import('@/views/staff/StaffEmptyLegsView.vue'), meta: { requiresStaff: true, title: 'Empty legs · Staff Operations' } },
  { path: '/staff/fleet', name: 'staff-fleet', component: () => import('@/views/staff/StaffFleetView.vue'), meta: { requiresStaff: true, title: 'Drivers & trucks · Staff Operations' } },
  // Old links from the China-batch era
  { path: '/staff/batches/:code?', redirect: '/staff/trips' },
  { path: '/staff/users', name: 'staff-users', component: () => import('@/views/staff/StaffUsersView.vue'), meta: { requiresStaff: true, title: 'People · Staff Operations' } },
  { path: '/staff/users/:code', name: 'staff-user', component: () => import('@/views/staff/StaffUserView.vue'), meta: { requiresStaff: true, title: 'Account · Staff Operations' } },
  { path: '/staff/rates', name: 'staff-rates', component: () => import('@/views/staff/StaffRatesView.vue'), meta: { requiresStaff: true, title: 'Pricing plans · Staff Operations' } },
  { path: '/staff/messages', name: 'staff-messages', component: () => import('@/views/staff/StaffMessagesView.vue'), meta: { requiresStaff: true, title: 'Messages · Staff Operations' } },

  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/views/NotFoundView.vue'), meta: { title: 'Page not found' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: (to) => (to.hash ? { el: to.hash, top: 80 } : { top: 0 }),
})

// Only allow same-app relative redirects (prevents open redirects via ?next=).
export function safeNext(next) {
  return typeof next === 'string' && next.startsWith('/') && !next.startsWith('//') && !next.includes('\\') ? next : '/account'
}

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.init()
  if ((to.meta.requiresAuth || to.meta.requiresStaff) && !auth.isAuthenticated) {
    return { name: 'login', query: { next: to.fullPath } }
  }
  // UI convenience only: the API enforces staff permissions on every request.
  if (to.meta.requiresStaff && !auth.isStaff) return { name: 'dashboard' }
  if (to.meta.guestOnly && auth.isAuthenticated) return { name: auth.isStaff ? 'staff' : 'dashboard' }
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · XpressDrive` : 'XpressDrive — Regional road freight'
})

export default router
