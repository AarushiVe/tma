<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import { toastError } from '../../toast'
import { fmtDate, money } from '../../utils'
import StatusBadge from '../../components/StatusBadge.vue'

const bookings = ref([])
const search = ref('')
const statusFilter = ref('')

async function loadBookings() {
  try {
    bookings.value = (await api('/admin/bookings', { params: { q: search.value, status: statusFilter.value } })).bookings
  } catch (e) {
    toastError(e)
  }
}
onMounted(loadBookings)
</script>

<template>
  <div class="container py-4">
    <div class="d-flex flex-wrap gap-2 mb-3">
      <h3 class="me-auto">All Bookings</h3>
      <input v-model="search" class="form-control w-auto" placeholder="Search user or trek" @input="loadBookings" />
      <select v-model="statusFilter" class="form-select w-auto" @change="loadBookings">
        <option value="">All status</option><option>Booked</option><option>Completed</option><option>Cancelled</option>
      </select>
    </div>

    <div class="table-responsive card">
      <table class="table table-hover align-middle mb-0">
        <thead><tr><th>ID</th><th>User</th><th>Trek</th><th>Start date</th><th>People</th><th>Amount</th><th>Status</th><th>Payment</th></tr></thead>
        <tbody>
          <tr v-for="b in bookings" :key="b.id">
            <td>{{ b.id }}</td>
            <td>{{ b.user_name }}<div class="small text-muted">{{ b.user_email }}</div></td>
            <td>{{ b.trek_name }}<div class="small text-muted">{{ b.participants.map(p => p.name).join(', ') }}</div></td>
            <td>{{ fmtDate(b.start_date) }}</td>
            <td>{{ b.people }}</td>
            <td>{{ money(b.total_amount) }}</td>
            <td><StatusBadge :value="b.status" /></td>
            <td><StatusBadge :value="b.payment_status" /></td>
          </tr>
          <tr v-if="!bookings.length"><td colspan="8" class="text-center text-muted">No bookings found</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
