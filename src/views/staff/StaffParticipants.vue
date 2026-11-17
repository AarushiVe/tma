<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../../api'
import { toast, toastError } from '../../toast'
import StatusBadge from '../../components/StatusBadge.vue'

const route = useRoute()
const trek = ref(null)
const bookings = ref([])

async function load() {
  try {
    const data = await api('/staff/treks/' + route.params.id + '/participants')
    trek.value = data.trek
    bookings.value = data.bookings
  } catch (e) {
    toastError(e)
  }
}
onMounted(load)

async function removeBooking(b) {
  if (!confirm('Remove ' + b.user_name + "'s booking? Slots will be given back.")) return
  try {
    const data = await api('/staff/bookings/' + b.id + '/cancel', { method: 'POST' })
    toast(data.message)
    load()
  } catch (e) {
    toastError(e)
  }
}
</script>

<template>
  <div class="container py-4">
    <router-link to="/staff">&larr; Back</router-link>
    <h3 v-if="trek" class="mt-2">{{ trek.name }} - Participants</h3>
    <p v-if="trek" class="text-muted">{{ trek.registered }} people registered, {{ trek.available_slots }} slots left</p>

    <div class="table-responsive card">
      <table class="table align-middle mb-0">
        <thead><tr><th>Booked by</th><th>People</th><th>Names (age)</th><th>Payment</th><th>Status</th><th></th></tr></thead>
        <tbody>
          <tr v-for="b in bookings" :key="b.id">
            <td>{{ b.user_name }}<div class="small text-muted">{{ b.user_email }}</div></td>
            <td>{{ b.people }}</td>
            <td>{{ b.participants.map(p => p.name + ' (' + p.age + ')').join(', ') }}</td>
            <td><StatusBadge :value="b.payment_status" /></td>
            <td><StatusBadge :value="b.status" /></td>
            <td>
              <button v-if="b.status === 'Booked' && !trek.is_started" class="btn btn-sm btn-outline-danger" @click="removeBooking(b)">Remove</button>
            </td>
          </tr>
          <tr v-if="!bookings.length"><td colspan="6" class="text-center text-muted">Nobody has booked this trek yet</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
