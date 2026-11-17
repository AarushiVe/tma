<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import { toast, toastError } from '../../toast'
import { fmtDate, todayISO } from '../../utils'
import Modal from '../../components/Modal.vue'
import StatusBadge from '../../components/StatusBadge.vue'

const treks = ref([])
const staff = ref([])
const search = ref('')
const statusFilter = ref('')
const showForm = ref(false)
const editId = ref(null)
const form = ref({})

function emptyForm() {
  return {
    name: '', location: '', difficulty: 'Easy', start_date: '', end_date: '',
    total_slots: 20, price: 0, staff_id: '', status: 'Pending', description: '', instructions: '',
  }
}

async function loadTreks() {
  try {
    const data = await api('/admin/treks', { params: { q: search.value, status: statusFilter.value } })
    treks.value = data.treks
  } catch (e) {
    toastError(e)
  }
}

onMounted(async () => {
  loadTreks()
  const data = await api('/admin/staff')
  staff.value = data.staff.filter((s) => s.status === 'active')
})

function newTrek() {
  editId.value = null
  form.value = emptyForm()
  showForm.value = true
}

function editTrek(t) {
  editId.value = t.id
  form.value = { ...t, staff_id: t.staff_id || '' }
  showForm.value = true
}

async function saveTrek() {
  try {
    let data
    if (editId.value) {
      data = await api('/admin/treks/' + editId.value, { method: 'PUT', body: form.value })
    } else {
      data = await api('/admin/treks', { method: 'POST', body: form.value })
    }
    toast(data.message)
    showForm.value = false
    loadTreks()
  } catch (e) {
    toastError(e)
  }
}

async function assignStaff(t, staffId) {
  try {
    const data = await api('/admin/treks/' + t.id + '/assign', { method: 'POST', body: { staff_id: staffId } })
    toast(data.message)
  } catch (e) {
    toastError(e)
  }
  loadTreks()
}

async function approve(t) {
  try {
    const data = await api('/admin/treks/' + t.id + '/approve', { method: 'POST' })
    toast(data.message)
  } catch (e) {
    toastError(e)
  }
  loadTreks()
}

async function deleteTrek(t) {
  if (!confirm('Delete ' + t.name + '?')) return
  try {
    const data = await api('/admin/treks/' + t.id, { method: 'DELETE' })
    toast(data.message)
  } catch (e) {
    toastError(e)
  }
  loadTreks()
}
</script>

<template>
  <div class="container py-4">
    <div class="d-flex flex-wrap gap-2 mb-3">
      <h3 class="me-auto">Treks</h3>
      <input v-model="search" class="form-control w-auto" placeholder="Search trek, place, staff" @input="loadTreks" />
      <select v-model="statusFilter" class="form-select w-auto" @change="loadTreks">
        <option value="">All status</option>
        <option>Pending</option><option>Approved</option><option>Open</option><option>Closed</option><option>Completed</option>
      </select>
      <button class="btn btn-primary" @click="newTrek">+ Add Trek</button>
    </div>

    <div class="table-responsive card">
      <table class="table table-hover align-middle mb-0">
        <thead>
          <tr><th>Name</th><th>Location</th><th>Difficulty</th><th>Start</th><th>Days</th><th>Slots</th><th>Staff</th><th>Status</th><th>Actions</th></tr>
        </thead>
        <tbody>
          <tr v-for="t in treks" :key="t.id">
            <td>{{ t.name }}</td>
            <td>{{ t.location }}</td>
            <td><StatusBadge :value="t.difficulty" /></td>
            <td>{{ fmtDate(t.start_date) }}</td>
            <td>{{ t.duration_days }}</td>
            <td>{{ t.available_slots }}/{{ t.total_slots }}</td>
            <td>
              <select class="form-select form-select-sm" :value="t.staff_id || ''" :disabled="t.status === 'Completed'"
                @change="assignStaff(t, $event.target.value)">
                <option value="">Not assigned</option>
                <option v-for="s in staff" :key="s.id" :value="s.id">{{ s.name }}</option>
              </select>
            </td>
            <td><StatusBadge :value="t.status" /></td>
            <td class="text-nowrap">
              <button v-if="t.status === 'Pending'" class="btn btn-sm btn-success me-1" @click="approve(t)">Approve</button>
              <button class="btn btn-sm btn-outline-primary me-1" @click="editTrek(t)">Edit</button>
              <button class="btn btn-sm btn-outline-danger" @click="deleteTrek(t)">Delete</button>
            </td>
          </tr>
          <tr v-if="!treks.length"><td colspan="9" class="text-center text-muted">No treks found</td></tr>
        </tbody>
      </table>
    </div>

    <Modal :show="showForm" :title="editId ? 'Edit Trek' : 'Add Trek'" large @close="showForm = false">
      <form id="trekForm" class="row g-3" @submit.prevent="saveTrek">
        <div class="col-md-6"><label class="form-label">Trek name</label><input v-model="form.name" class="form-control" required /></div>
        <div class="col-md-6"><label class="form-label">Location</label><input v-model="form.location" class="form-control" required /></div>
        <div class="col-md-4">
          <label class="form-label">Difficulty</label>
          <select v-model="form.difficulty" class="form-select"><option>Easy</option><option>Moderate</option><option>Hard</option></select>
        </div>
        <div class="col-md-4"><label class="form-label">Start date</label><input v-model="form.start_date" type="date" class="form-control" :min="editId ? '' : todayISO()" required /></div>
        <div class="col-md-4"><label class="form-label">End date</label><input v-model="form.end_date" type="date" class="form-control" :min="form.start_date" required /></div>
        <div class="col-md-4"><label class="form-label">Total slots</label><input v-model="form.total_slots" type="number" min="1" max="500" class="form-control" required /></div>
        <div class="col-md-4"><label class="form-label">Price per person</label><input v-model="form.price" type="number" min="0" class="form-control" required /></div>
        <div class="col-md-4">
          <label class="form-label">Assign staff</label>
          <select v-model="form.staff_id" class="form-select">
            <option value="">Not assigned</option>
            <option v-for="s in staff" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </div>
        <div v-if="editId" class="col-md-4">
          <label class="form-label">Status</label>
          <select v-model="form.status" class="form-select">
            <option>Pending</option><option>Approved</option><option>Open</option><option>Closed</option><option>Completed</option>
          </select>
        </div>
        <div class="col-12"><label class="form-label">Description</label><textarea v-model="form.description" class="form-control" rows="2"></textarea></div>
        <div class="col-12"><label class="form-label">Instructions (sent in reminders)</label><textarea v-model="form.instructions" class="form-control" rows="2"></textarea></div>
      </form>
      <template #footer>
        <button class="btn btn-secondary" @click="showForm = false">Cancel</button>
        <button class="btn btn-primary" type="submit" form="trekForm">Save</button>
      </template>
    </Modal>
  </div>
</template>
