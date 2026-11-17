<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import { toast, toastError } from '../../toast'
import ChartCanvas from '../../components/ChartCanvas.vue'

const stats = ref(null)

onMounted(async () => {
  try {
    stats.value = await api('/admin/stats')
  } catch (e) {
    toastError(e)
  }
})

async function sendReport() {
  try {
    const data = await api('/admin/reports/monthly', { method: 'POST' })
    toast(data.message)
  } catch (e) {
    toastError(e)
  }
}
</script>

<template>
  <div class="container py-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h3>Admin Dashboard</h3>
      <button class="btn btn-outline-primary btn-sm" @click="sendReport">Email monthly report</button>
    </div>

    <div v-if="stats">
      <div class="row g-3 mb-4">
        <div class="col-6 col-md-4 col-lg-2" v-for="item in [
          ['Total treks', stats.totals.treks], ['Open treks', stats.totals.open_treks],
          ['Users', stats.totals.users], ['Staff', stats.totals.staff],
          ['Bookings', stats.totals.bookings], ['People booked', stats.totals.people]]" :key="item[0]">
          <div class="card text-center p-3">
            <h3 class="text-blue mb-0">{{ item[1] }}</h3>
            <small class="text-muted">{{ item[0] }}</small>
          </div>
        </div>
      </div>

      <div class="row g-3">
        <div class="col-md-7">
          <div class="card p-3">
            <h6>Popular treks (people booked)</h6>
            <ChartCanvas type="bar" :labels="stats.popular.map(p => p.name)" :values="stats.popular.map(p => p.people)" title="People" />
          </div>
        </div>
        <div class="col-md-5">
          <div class="card p-3">
            <h6>Treks by status</h6>
            <ChartCanvas type="pie" :labels="stats.by_status.map(s => s.status)" :values="stats.by_status.map(s => s.count)" title="Treks" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
