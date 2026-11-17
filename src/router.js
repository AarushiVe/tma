import { createRouter, createWebHistory } from 'vue-router'
import { auth, homePath } from './auth'

const routes = [
  { path: '/', redirect: () => (auth.user ? homePath() : '/login') },
  { path: '/login', component: () => import('./views/LoginView.vue') },
  { path: '/register', component: () => import('./views/RegisterView.vue') },

  { path: '/admin', component: () => import('./views/admin/AdminDashboard.vue'), meta: { role: 'admin' } },
  { path: '/admin/treks', component: () => import('./views/admin/AdminTreks.vue'), meta: { role: 'admin' } },
  { path: '/admin/staff', component: () => import('./views/admin/AdminStaff.vue'), meta: { role: 'admin' } },
  { path: '/admin/users', component: () => import('./views/admin/AdminUsers.vue'), meta: { role: 'admin' } },
  { path: '/admin/bookings', component: () => import('./views/admin/AdminBookings.vue'), meta: { role: 'admin' } },

  { path: '/staff', component: () => import('./views/staff/StaffDashboard.vue'), meta: { role: 'staff' } },
  { path: '/staff/treks/:id', component: () => import('./views/staff/StaffParticipants.vue'), meta: { role: 'staff' } },

  { path: '/trekker', component: () => import('./views/trekker/TrekkerDashboard.vue'), meta: { role: 'trekker' } },
  { path: '/trekker/explore', component: () => import('./views/trekker/TrekExplore.vue'), meta: { role: 'trekker' } },
  { path: '/trekker/bookings', component: () => import('./views/trekker/MyBookings.vue'), meta: { role: 'trekker' } },

  { path: '/profile', component: () => import('./views/ProfileView.vue'), meta: { role: 'any' } },
  { path: '/notifications', component: () => import('./views/NotificationsView.vue'), meta: { role: 'any' } },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({ history: createWebHistory(), routes })

// protect pages by login and role
router.beforeEach((to) => {
  const role = auth.user?.role
  const needed = to.meta.role
  if (!needed) {
    if (role) return homePath()   // logged in users don't need login/register pages
    return true
  }
  if (!role) return '/login'
  if (needed !== 'any' && needed !== role) return homePath()
})

export default router
