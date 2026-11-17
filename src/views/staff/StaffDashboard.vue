<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import { toast, toastError } from '../../toast'
import { fmtDate } from '../../utils'
import StatusBadge from '../../components/StatusBadge.vue'

const treks = ref([])
const slots = ref({})   // slots typed in the input box, by trek id

async function loadTreks() {
  try {
    treks.value = (await api('/staff/treks')).treks
    for (const t of treks.value) {
      slots.value[t.id] = t.available_slots
    }
  } catch (e) {
    toastError(e)
  }
}
onMounted(loadTreks)

async function callApi(url, method, body) {
  try {
    const data = await api(url, { method, body })
    toast(data.message)
  } catch (e) {
    toastError(e)
  }
  loadTreks()
}

function updateSlots(t) {
  callApi('/staff/treks/' + t.id, 'PUT', { available_slots: slots.value[t.id] })
}
function setStatus(t, status) {
  callApi('/staff/treks/' + t.id, 'PUT', { status })
}
function startTrek(t) {
  if (confirm('Start ' + t.name + '? Bookings will be closed.')) callApi('/staff/treks/' + t.id + '/start', 'POST')
}
function completeTrek(t) {
  if (confirm('Mark ' + t.name + ' as completed?')) callApi('/staff/treks/' + t.id + '/complete', 'POST')
}
</script>

<template>
  <div class="container py-4">
    <h3 class="mb-3">My Assigned Treks</h3>
    <p v-if="!treks.length" class="text-muted">No treks are assigned to you yet.</p>

    <div class="row g-3">
      <div v-for="t in treks" :key="t.id" class="col-md-6">
        <div class="card p-3 h-100">
          <div class="d-flex justify-content-between">
            <h5>{{ t.name }}</h5>
            <div>
              <StatusBadge :value="t.status" />
              <span v-if="t.is_started && t.status !== 'Completed'" class="badge bg-info ms-1">Started</span>
            </div>
          </div>
          <p class="text-muted mb-2">{{ t.location }} | {{ fmtDate(t.start_date) }} to {{ fmtDate(t.end_date) }}</p>
          <p class="mb-2">
            Bookings: <b>{{ t.booking_count }}</b> |
            Registered people: <b>{{ t.registered }}</b> |
            Slots: <b>{{ t.available_slots }}/{{ t.total_slots }}</b>
          </p>

          <div v-if="t.status !== 'Completed'" class="input-group input-group-sm mb-3">
            <span class="input-group-text">Available slots</span>
            <input v-model="slots[t.id]" type="number" min="0" max="500" class="form-control" />
            <button class="btn btn-outline-primary" @click="updateSlots(t)">Update</button>
          </div>

          <div class="d-flex flex-wrap gap-2">
            <router-link :to="'/staff/treks/' + t.id" class="btn btn-sm btn-primary">View participants</router-link>
            <template v-if="t.status !== 'Completed' && !t.is_started">
              <span v-if="t.status === 'Pending'" class="text-muted small align-self-center">Waiting for admin approval</span>
              <button v-else-if="t.status === 'Open'" class="btn btn-sm btn-outline-primary" @click="setStatus(t, 'Closed')">Close bookings</button>
              <button v-else class="btn btn-sm btn-outline-primary" @click="setStatus(t, 'Open')">Open bookings</button>
              <button v-if="t.status !== 'Pending'" class="btn btn-sm btn-outline-primary" @click="startTrek(t)">Mark started</button>
            </template>
            <button v-if="t.is_started && t.status !== 'Completed'" class="btn btn-sm btn-success" @click="completeTrek(t)">Mark completed</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
