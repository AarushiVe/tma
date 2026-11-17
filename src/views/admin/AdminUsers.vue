<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import { toast, toastError } from '../../toast'
import { fmtDate } from '../../utils'
import StatusBadge from '../../components/StatusBadge.vue'

const users = ref([])
const search = ref('')
const statusFilter = ref('')

async function loadUsers() {
  try {
    users.value = (await api('/admin/users', { params: { q: search.value, status: statusFilter.value } })).users
  } catch (e) {
    toastError(e)
  }
}
onMounted(loadUsers)

async function changeStatus(u, status) {
  if (status !== 'active' && !confirm('Make ' + u.name + ' ' + status + '?')) return
  try {
    const data = await api('/admin/users/' + u.id + '/status', { method: 'POST', body: { status } })
    toast(data.message)
    loadUsers()
  } catch (e) {
    toastError(e)
  }
}
</script>

<template>
  <div class="container py-4">
    <div class="d-flex flex-wrap gap-2 mb-3">
      <h3 class="me-auto">Users (Trekkers)</h3>
      <input v-model="search" class="form-control w-auto" placeholder="Search users" @input="loadUsers" />
      <select v-model="statusFilter" class="form-select w-auto" @change="loadUsers">
        <option value="">All</option><option value="active">Active</option>
        <option value="deactivated">Deactivated</option><option value="blacklisted">Blacklisted</option>
      </select>
    </div>

    <div class="table-responsive card">
      <table class="table table-hover align-middle mb-0">
        <thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Joined</th><th>Bookings</th><th>Status</th><th>Actions</th></tr></thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>{{ u.name }}</td>
            <td>{{ u.email }}</td>
            <td>{{ u.phone || '-' }}</td>
            <td>{{ fmtDate(u.created_at) }}</td>
            <td>{{ u.booking_count }}</td>
            <td><StatusBadge :value="u.status" /></td>
            <td class="text-nowrap">
              <button v-if="u.status !== 'active'" class="btn btn-sm btn-success me-1" @click="changeStatus(u, 'active')">Activate</button>
              <button v-if="u.status === 'active'" class="btn btn-sm btn-secondary me-1" @click="changeStatus(u, 'deactivated')">Deactivate</button>
              <button v-if="u.status !== 'blacklisted'" class="btn btn-sm btn-outline-danger" @click="changeStatus(u, 'blacklisted')">Blacklist</button>
            </td>
          </tr>
          <tr v-if="!users.length"><td colspan="7" class="text-center text-muted">No users found</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
