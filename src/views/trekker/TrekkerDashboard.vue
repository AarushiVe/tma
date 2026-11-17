<script setup>
import { ref, onMounted, computed } from 'vue'
import { api, downloadFile } from '../../api'
import { auth } from '../../auth'
import { toast, toastError } from '../../toast'
import { fmtDate } from '../../utils'
import StatusBadge from '../../components/StatusBadge.vue'

const treks = ref([])
const bookings = ref([])
const exporting = ref(false)

onMounted(async () => {
  try {
    treks.value = (await api('/treks')).treks
    bookings.value = (await api('/bookings')).bookings
  } catch (e) {
    toastError(e)
  }
})

// export booking history as csv: start the job, then wait until the file is ready
async function exportCsv() {
  exporting.value = true
  try {
    const data = await api('/exports', { method: 'POST' })
    toast(data.message)
    for (let i = 0; i < 30; i++) {
      await new Promise((resolve) => setTimeout(resolve, 2000))
      const list = (await api('/exports')).exports
      const mine = list.find((e) => e.id === data.export_id)
      if (mine && mine.status === 'Done') {
        await downloadFile('/exports/' + mine.id + '/download', 'my_trekking_history.csv')
        break
      }
      if (mine && mine.status === 'Failed') {
        toast('Export failed, please try again', 'danger')
        break
      }
    }
  } catch (e) {
    toastError(e)
  }
  exporting.value = false
}

const booked = computed(() => bookings.value.filter((b) => b.status === 'Booked'))
const completed = computed(() => bookings.value.filter((b) => b.status === 'Completed'))
</script>

<template>
  <div class="container py-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h3 class="mb-0">Welcome, {{ auth.user.name }}</h3>
      <button class="btn btn-outline-primary btn-sm" :disabled="exporting" @click="exportCsv">
        {{ exporting ? 'Preparing CSV...' : 'Export booking history (CSV)' }}
      </button>
    </div>

    <div class="row g-3 mb-4">
      <div class="col-4"><div class="card text-center p-3"><h3 class="text-blue mb-0">{{ treks.length }}</h3><small class="text-muted">Available treks</small></div></div>
      <div class="col-4"><div class="card text-center p-3"><h3 class="text-blue mb-0">{{ booked.length }}</h3><small class="text-muted">Booked treks</small></div></div>
      <div class="col-4"><div class="card text-center p-3"><h3 class="text-blue mb-0">{{ completed.length }}</h3><small class="text-muted">Completed</small></div></div>
    </div>

    <div class="row g-4">
      <div class="col-md-6">
        <h5>My booked treks</h5>
        <p v-if="!booked.length" class="text-muted">You have no active bookings. <router-link to="/trekker/explore">Explore treks</router-link></p>
        <div v-for="b in booked" :key="b.id" class="card p-3 mb-2">
          <div class="d-flex justify-content-between">
            <b>{{ b.trek_name }}</b>
            <span><StatusBadge :value="b.status" /> <StatusBadge :value="b.trek_status" /></span>
          </div>
          <small class="text-muted">{{ b.location }} | {{ fmtDate(b.start_date) }} | {{ b.people }} people</small>
        </div>
      </div>

      <div class="col-md-6">
        <h5>Available treks</h5>
        <p v-if="!treks.length" class="text-muted">No treks are open right now.</p>
        <div v-for="t in treks.slice(0, 4)" :key="t.id" class="card p-3 mb-2">
          <div class="d-flex justify-content-between">
            <b>{{ t.name }}</b><StatusBadge :value="t.difficulty" />
          </div>
          <small class="text-muted">{{ t.location }} | {{ fmtDate(t.start_date) }} | {{ t.available_slots }} slots left</small>
        </div>
        <router-link to="/trekker/explore">See all treks</router-link>
      </div>
    </div>
  </div>
</template>
