<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import { toast, toastError } from '../../toast'
import Modal from '../../components/Modal.vue'
import StatusBadge from '../../components/StatusBadge.vue'

const staff = ref([])
const search = ref('')
const showForm = ref(false)
const editId = ref(null)
const form = ref({})

async function loadStaff() {
  try {
    staff.value = (await api('/admin/staff', { params: { q: search.value } })).staff
  } catch (e) {
    toastError(e)
  }
}
onMounted(loadStaff)

function newStaff() {
  editId.value = null
  form.value = { name: '', email: '', password: '', phone: '', experience_years: 0, specialization: '' }
  showForm.value = true
}

function editStaff(s) {
  editId.value = s.id
  form.value = { ...s, experience_years: s.experience_years || 0, specialization: s.specialization || '' }
  showForm.value = true
}

async function saveStaff() {
  try {
    let data
    if (editId.value) {
      data = await api('/admin/staff/' + editId.value, { method: 'PUT', body: form.value })
    } else {
      data = await api('/admin/staff', { method: 'POST', body: form.value })
    }
    toast(data.message)
    showForm.value = false
    loadStaff()
  } catch (e) {
    toastError(e)
  }
}

async function changeStatus(s, status) {
  if (status !== 'active' && !confirm('Make ' + s.name + ' ' + status + '? Their treks will be unassigned.')) return
  try {
    const data = await api('/admin/users/' + s.id + '/status', { method: 'POST', body: { status } })
    toast(data.message)
    loadStaff()
  } catch (e) {
    toastError(e)
  }
}
</script>

<template>
  <div class="container py-4">
    <div class="d-flex flex-wrap gap-2 mb-3">
      <h3 class="me-auto">Trek Staff</h3>
      <input v-model="search" class="form-control w-auto" placeholder="Search staff" @input="loadStaff" />
      <button class="btn btn-primary" @click="newStaff">+ Add Staff</button>
    </div>

    <div class="table-responsive card">
      <table class="table table-hover align-middle mb-0">
        <thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Experience</th><th>Treks</th><th>Status</th><th>Actions</th></tr></thead>
        <tbody>
          <tr v-for="s in staff" :key="s.id">
            <td>{{ s.name }}<div class="small text-muted">{{ s.specialization }}</div></td>
            <td>{{ s.email }}</td>
            <td>{{ s.phone }}</td>
            <td>{{ s.experience_years || 0 }} yrs</td>
            <td>{{ s.trek_count }}</td>
            <td><StatusBadge :value="s.status" /></td>
            <td class="text-nowrap">
              <button class="btn btn-sm btn-outline-primary me-1" @click="editStaff(s)">Edit</button>
              <button v-if="s.status !== 'active'" class="btn btn-sm btn-success me-1" @click="changeStatus(s, 'active')">Activate</button>
              <button v-if="s.status === 'active'" class="btn btn-sm btn-secondary me-1" @click="changeStatus(s, 'deactivated')">Deactivate</button>
              <button v-if="s.status !== 'blacklisted'" class="btn btn-sm btn-outline-danger" @click="changeStatus(s, 'blacklisted')">Blacklist</button>
            </td>
          </tr>
          <tr v-if="!staff.length"><td colspan="7" class="text-center text-muted">No staff added yet</td></tr>
        </tbody>
      </table>
    </div>

    <Modal :show="showForm" :title="editId ? 'Edit Staff' : 'Add Staff'" @close="showForm = false">
      <form id="staffForm" @submit.prevent="saveStaff">
        <div class="mb-3"><label class="form-label">Name</label><input v-model="form.name" class="form-control" required /></div>
        <div v-if="!editId" class="mb-3"><label class="form-label">Email (used for login)</label><input v-model="form.email" type="email" class="form-control" required /></div>
        <div v-if="!editId" class="mb-3"><label class="form-label">Password</label><input v-model="form.password" class="form-control" minlength="6" required /></div>
        <div class="mb-3"><label class="form-label">Phone</label><input v-model="form.phone" class="form-control" pattern="\+?[0-9 \-]{7,15}" title="Enter 7 to 15 digits" required /></div>
        <div class="mb-3"><label class="form-label">Experience (years)</label><input v-model="form.experience_years" type="number" min="0" max="60" class="form-control" /></div>
        <div class="mb-3"><label class="form-label">Specialization</label><input v-model="form.specialization" class="form-control" /></div>
      </form>
      <template #footer>
        <button class="btn btn-secondary" @click="showForm = false">Cancel</button>
        <button class="btn btn-primary" type="submit" form="staffForm">Save</button>
      </template>
    </Modal>
  </div>
</template>
