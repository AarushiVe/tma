<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { api, downloadFile } from '../../api'
import { toast, toastError } from '../../toast'
import { fmtDate, money } from '../../utils'
import StatusBadge from '../../components/StatusBadge.vue'

const bookings = ref([])
const exportsList = ref([])
const tab = ref('upcoming')
let timer = null
let waitingIds = []   // exports we were waiting for, to download them automatically

const upcoming = computed(() => bookings.value.filter((b) => b.status === 'Booked'))
const history = computed(() => bookings.value.filter((b) => b.status !== 'Booked'))
const shown = computed(() => (tab.value === 'upcoming' ? upcoming.value : history.value))

async function load() {
  try {
    bookings.value = (await api('/bookings')).bookings
    exportsList.value = (await api('/exports')).exports
    // keep checking while an export is still being prepared
    for (const e of exportsList.value) {
      if (e.status === 'Done' && waitingIds.includes(e.id)) {
        waitingIds = waitingIds.filter((id) => id !== e.id)
        download(e)     // the file was being prepared, so download it now
      }
    }
    const waiting = exportsList.value.some((e) => e.status === 'Pending')
    if (waiting && !timer) timer = setInterval(load, 2500)
    if (!waiting && timer) {
      clearInterval(timer)
      timer = null
    }
  } catch (e) {
    toastError(e)
  }
}
onMounted(load)
onBeforeUnmount(() => clearInterval(timer))

async function post(url) {
  try {
    const data = await api(url, { method: 'POST' })
    toast(data.message)
  } catch (e) {
    toastError(e)
  }
  load()
}

async function startExport() {
  try {
    const data = await api('/exports', { method: 'POST' })
    waitingIds.push(data.export_id)
    toast('Preparing your CSV, it will download automatically')
  } catch (e) {
    toastError(e)
  }
  load()
}

function cancelBooking(b) {
  if (confirm('Cancel your booking for ' + b.trek_name + '?')) post('/bookings/' + b.id + '/cancel')
}

async function download(e) {
  try {
    await downloadFile('/exports/' + e.id + '/download', 'my_trekking_history.csv')
  } catch (err) {
    toastError(err)
  }
}
</script>

<template>
  <div class="container py-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h3>My Bookings</h3>
      <button class="btn btn-outline-primary" @click="startExport">Export history (CSV)</button>
    </div>

    <div v-if="exportsList.length" class="card p-3 mb-3">
      <b class="small mb-1">Your exports</b>
      <div v-for="e in exportsList.slice(0, 3)" :key="e.id" class="small mb-1">
        Export #{{ e.id }} <StatusBadge :value="e.status" />
        <span v-if="e.status === 'Pending'" class="text-muted">preparing file...</span>
        <button v-if="e.status === 'Done'" class="btn btn-sm btn-primary py-0 ms-1" @click="download(e)">Download</button>
      </div>
    </div>

    <div class="mb-3">
      <button class="btn me-2" :class="tab === 'upcoming' ? 'btn-primary' : 'btn-outline-primary'" @click="tab = 'upcoming'">Booked ({{ upcoming.length }})</button>
      <button class="btn" :class="tab === 'history' ? 'btn-primary' : 'btn-outline-primary'" @click="tab = 'history'">Trekking history ({{ history.length }})</button>
    </div>

    <p v-if="!shown.length" class="text-muted">Nothing to show here.</p>

    <div v-for="b in shown" :key="b.id" class="card p-3 mb-3">
      <div class="d-flex flex-wrap justify-content-between gap-2">
        <div>
          <h5 class="mb-1">{{ b.trek_name }}</h5>
          <div class="text-muted">{{ b.location }} | {{ fmtDate(b.start_date) }} to {{ fmtDate(b.end_date) }}</div>
          <div>{{ b.people }} people | {{ money(b.total_amount) }} | booked on {{ fmtDate(b.booking_date) }}</div>
          <div class="small mt-1">People: {{ b.participants.map(p => p.name + ' (' + p.age + ')').join(', ') }}</div>
        </div>
        <div class="text-end">
          <div>Booking: <StatusBadge :value="b.status" /></div>
          <div>Trek: <StatusBadge :value="b.trek_status" /></div>
          <div v-if="b.status !== 'Cancelled' || b.payment_status === 'Refunded'">Payment: <StatusBadge :value="b.payment_status" /></div>
          <div v-if="b.payment_status === 'Refunded'" class="small text-success">Refund processed: {{ money(b.total_amount) }}</div>
        </div>
      </div>
      <div v-if="b.status === 'Booked'" class="mt-3">
        <button v-if="b.payment_status === 'Pending'" class="btn btn-sm btn-primary me-2" @click="post('/bookings/' + b.id + '/pay')">Pay now (demo)</button>
        <button class="btn btn-sm btn-outline-danger" @click="cancelBooking(b)">Cancel booking</button>
      </div>
    </div>
  </div>
</template>
