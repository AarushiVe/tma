<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { auth, logout } from '../auth'
import { api } from '../api'

const router = useRouter()
const unread = ref(0)
const open = ref(false)

const links = computed(() => {
  if (auth.user.role === 'admin') {
    return [['/admin', 'Dashboard'], ['/admin/treks', 'Treks'], ['/admin/staff', 'Staff'], ['/admin/users', 'Users'], ['/admin/bookings', 'Bookings']]
  }
  if (auth.user.role === 'staff') {
    return [['/staff', 'My Treks']]
  }
  return [['/trekker', 'Dashboard'], ['/trekker/explore', 'Explore Treks'], ['/trekker/bookings', 'My Bookings']]
})

onMounted(async () => {
  try {
    unread.value = (await api('/notifications')).unread
  } catch (e) { /* ignore */ }
})

function signOut() {
  logout()
  router.push('/login')
}
</script>

<template>
  <nav class="navbar navbar-expand-md navbar-dark navbar-trekison">
    <div class="container">
      <span class="navbar-brand fw-bold">Trekison</span>
      <button class="navbar-toggler" @click="open = !open"><span class="navbar-toggler-icon"></span></button>
      <div class="navbar-collapse" :class="{ collapse: !open }">
        <ul class="navbar-nav me-auto">
          <li v-for="l in links" :key="l[0]" class="nav-item">
            <router-link :to="l[0]" class="nav-link" @click="open = false">{{ l[1] }}</router-link>
          </li>
        </ul>
        <ul class="navbar-nav">
          <li class="nav-item">
            <router-link to="/notifications" class="nav-link">
              Notifications <span v-if="unread" class="badge bg-light text-primary">{{ unread }}</span>
            </router-link>
          </li>
          <li class="nav-item"><router-link to="/profile" class="nav-link">{{ auth.user.name }}</router-link></li>
          <li class="nav-item"><a href="#" class="nav-link" @click.prevent="signOut">Logout</a></li>
        </ul>
      </div>
    </div>
  </nav>
</template>
