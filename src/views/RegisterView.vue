<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { toast } from '../toast'

const router = useRouter()
const form = ref({ name: '', email: '', phone: '', password: '', confirm: '' })
const error = ref('')

async function register() {
  error.value = ''
  if (form.value.password !== form.value.confirm) {
    error.value = 'Passwords do not match'
    return
  }
  try {
    await api('/auth/register', {
      method: 'POST',
      body: { name: form.value.name, email: form.value.email, phone: form.value.phone, password: form.value.password },
    })
    toast('Registered! Please login.')
    router.push('/login')
  } catch (e) {
    error.value = e.message
  }
}
</script>

<template>
  <div class="auth-box">
    <h2 class="text-center text-blue mb-3">Trekison</h2>
    <div class="card p-4">
      <h4 class="mb-3">Register</h4>
      <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
      <form @submit.prevent="register">
        <div class="mb-3">
          <label class="form-label">Name</label>
          <input v-model="form.name" class="form-control" required />
        </div>
        <div class="mb-3">
          <label class="form-label">Email</label>
          <input v-model="form.email" type="email" class="form-control" required />
        </div>
        <div class="mb-3">
          <label class="form-label">Phone (optional)</label>
          <input v-model="form.phone" class="form-control" pattern="\+?[0-9 \-]{7,15}" title="Enter 7 to 15 digits" />
        </div>
        <div class="mb-3">
          <label class="form-label">Password</label>
          <input v-model="form.password" type="password" class="form-control" minlength="6" required />
        </div>
        <div class="mb-3">
          <label class="form-label">Confirm password</label>
          <input v-model="form.confirm" type="password" class="form-control" required />
        </div>
        <button class="btn btn-primary w-100">Register</button>
      </form>
      <p class="mt-3 mb-0 text-center">Already have an account? <router-link to="/login">Login</router-link></p>
    </div>
  </div>
</template>
