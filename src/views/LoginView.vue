<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { setSession, homePath } from '../auth'

const router = useRouter()
const email = ref('')
const password = ref('')
const error = ref('')

async function login() {
  error.value = ''
  try {
    const data = await api('/auth/login', { method: 'POST', body: { email: email.value, password: password.value } })
    setSession(data.token, data.user)
    router.push(homePath(data.user.role))
  } catch (e) {
    error.value = e.message
  }
}
</script>

<template>
  <div class="auth-box">
    <h2 class="text-center text-blue mb-1">Trekison</h2>
    <p class="text-center text-muted">Trekking Management Application</p>
    <div class="card p-4">
      <h4 class="mb-3">Login</h4>
      <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
      <form @submit.prevent="login">
        <div class="mb-3">
          <label class="form-label">Email</label>
          <input v-model="email" type="email" class="form-control" required />
        </div>
        <div class="mb-3">
          <label class="form-label">Password</label>
          <input v-model="password" type="password" class="form-control" required />
        </div>
        <button class="btn btn-primary w-100">Login</button>
      </form>
      <p class="mt-3 mb-0 text-center">New user? <router-link to="/register">Register here</router-link></p>
    </div>
  </div>
</template>
