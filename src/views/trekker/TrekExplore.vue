<script setup>
import { ref, onMounted, computed } from 'vue'
import { api } from '../../api'
import { auth } from '../../auth'
import { toast, toastError } from '../../toast'
import { fmtDate, money } from '../../utils'
import Modal from '../../components/Modal.vue'
import StatusBadge from '../../components/StatusBadge.vue'

const treks = ref([])
const locations = ref([])
const maxPeople = ref(10)
const filters = ref({ q: '', difficulty: '', location: '', min_days: '', max_days: '' })

const selected = ref(null)    // trek being booked
const people = ref([])        // details of every person in the booking

async function loadTreks() {
  try {
    const data = await api('/treks', { params: filters.value })
    treks.value = data.treks
    locations.value = data.locations
    maxPeople.value = data.max_people
  } catch (e) {
    toastError(e)
  }
}
onMounted(loadTreks)

function clearFilters() {
  filters.value = { q: '', difficulty: '', location: '', min_days: '', max_days: '' }
  loadTreks()
}

// a user can book at most 10 people, and not more than the free slots
const maxForThisTrek = computed(() => (selected.value ? Math.min(maxPeople.value, selected.value.available_slots) : 1))

function openBooking(t) {
  selected.value = t
  // first person is the user
  people.value = [{ name: auth.user.name, age: '', phone: auth.user.phone || '' }]
}

function changeCount(event) {
  const n = Number(event.target.value)
  while (people.value.length < n) people.value.push({ name: '', age: '', phone: '' })
  while (people.value.length > n) people.value.pop()
}

async function confirmBooking() {
  try {
    const data = await api('/treks/' + selected.value.id + '/book', { method: 'POST', body: { participants: people.value } })
    toast(data.message)
    selected.value = null
  } catch (e) {
    toastError(e)
  }
  loadTreks()
}
</script>

<template>
  <div class="container py-4">
    <h3 class="mb-3">Explore Treks</h3>

    <form class="card p-3 mb-4" @submit.prevent="loadTreks">
      <div class="row g-2">
        <div class="col-md-3"><input v-model="filters.q" class="form-control" placeholder="Search trek or place" /></div>
        <div class="col-md-2">
          <select v-model="filters.difficulty" class="form-select">
            <option value="">Any difficulty</option><option>Easy</option><option>Moderate</option><option>Hard</option>
          </select>
        </div>
        <div class="col-md-2">
          <select v-model="filters.location" class="form-select">
            <option value="">Any location</option>
            <option v-for="l in locations" :key="l">{{ l }}</option>
          </select>
        </div>
        <div class="col-md-2"><input v-model="filters.min_days" type="number" min="1" class="form-control" placeholder="Min days" /></div>
        <div class="col-md-2"><input v-model="filters.max_days" type="number" min="1" class="form-control" placeholder="Max days" /></div>
        <div class="col-md-1 d-flex gap-1">
          <button class="btn btn-primary">Go</button>
          <button type="button" class="btn btn-outline-secondary" @click="clearFilters">X</button>
        </div>
      </div>
    </form>

    <p v-if="!treks.length" class="text-muted">No treks found.</p>

    <div class="row g-3">
      <div v-for="t in treks" :key="t.id" class="col-md-6 col-lg-4">
        <div class="card p-3 h-100">
          <div class="d-flex justify-content-between">
            <h5>{{ t.name }}</h5><StatusBadge :value="t.difficulty" />
          </div>
          <p class="text-muted mb-1">{{ t.location }} | {{ t.duration_days }} day(s)</p>
          <p class="small flex-grow-1">{{ t.description }}</p>
          <p class="mb-1 small">Start date: <b>{{ fmtDate(t.start_date) }}</b></p>
          <p class="mb-2 small">Guide: {{ t.staff_name }} | Slots left: <b>{{ t.available_slots }}</b></p>
          <div class="d-flex justify-content-between align-items-center">
            <span class="fs-5 text-blue">{{ money(t.price) }} <small class="text-muted fs-6">/ person</small></span>
            <button class="btn btn-primary btn-sm" :disabled="t.available_slots < 1" @click="openBooking(t)">
              {{ t.available_slots < 1 ? 'Full' : 'Book' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <Modal :show="!!selected" :title="selected ? 'Book ' + selected.name : ''" large @close="selected = null">
      <form v-if="selected" id="bookForm" @submit.prevent="confirmBooking">
        <div class="row mb-3">
          <div class="col-sm-6">
            <label class="form-label">Number of people (max {{ maxForThisTrek }})</label>
            <select class="form-select" :value="people.length" @change="changeCount">
              <option v-for="n in maxForThisTrek" :key="n" :value="n">{{ n }}</option>
            </select>
          </div>
          <div class="col-sm-6 text-sm-end">
            <small class="text-muted">Total amount</small>
            <h4 class="text-blue">{{ money(selected.price * people.length) }}</h4>
          </div>
        </div>
        <p class="small text-muted">You can book up to {{ maxPeople }} people. Enter the details of everyone who is coming.</p>
        <div v-for="(p, i) in people" :key="i" class="row g-2 mb-2">
          <div class="col-sm-5"><input v-model="p.name" class="form-control" :placeholder="'Person ' + (i + 1) + ' name'" required /></div>
          <div class="col-sm-2"><input v-model="p.age" type="number" min="5" max="90" class="form-control" placeholder="Age" required /></div>
          <div class="col-sm-5"><input v-model="p.phone" class="form-control" placeholder="Phone (optional)" pattern="\+?[0-9 \-]{7,15}" title="Enter 7 to 15 digits" /></div>
        </div>
      </form>
      <template #footer>
        <button class="btn btn-secondary" @click="selected = null">Cancel</button>
        <button class="btn btn-primary" type="submit" form="bookForm">Confirm Booking</button>
      </template>
    </Modal>
  </div>
</template>
