<script setup>
import { ref } from 'vue'
import { api } from '../api'
import { auth, updateUser } from '../auth'
import { toast, toastError } from '../toast'

const form = ref({
  name: auth.user.name, email: auth.user.email, phone: auth.user.phone || '',
  current_password: '', new_password: '',
})

async function save() {
  try {
    const data = await api('/auth/me', { method: 'PUT', body: form.value })
    updateUser(data.user)
    form.value.current_password = ''
    form.value.new_password = ''
    toast('Profile updated')
  } catch (e) {
    toastError(e)
  }
}
</script>

<template>
  <div class="container py-4" style="max-width: 600px">
    <h3 class="mb-3">My Profile</h3>
    <form class="card p-4" @submit.prevent="save">
      <div class="mb-3">
        <label class="form-label">Name</label>
        <input v-model="form.name" class="form-control" required />
      </div>
      <div class="mb-3">
        <label class="form-label">Email</label>
        <input v-model="form.email" type="email" class="form-control" required />
      </div>
      <div class="mb-3">
        <label class="form-label">Phone</label>
        <input v-model="form.phone" class="form-control" pattern="\+?[0-9 \-]{7,15}" title="Enter 7 to 15 digits" />
      </div>
      <hr />
      <p class="text-muted small">To change password fill these two fields, otherwise leave them empty.</p>
      <div class="mb-3">
        <label class="form-label">Current password</label>
        <input v-model="form.current_password" type="password" class="form-control" />
      </div>
      <div class="mb-3">
        <label class="form-label">New password</label>
        <input v-model="form.new_password" type="password" class="form-control" minlength="6" />
      </div>
      <button class="btn btn-primary">Save</button>
    </form>
  </div>
</template>
