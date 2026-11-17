<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
import { fmtDate } from '../utils'

const notifications = ref([])

onMounted(async () => {
  const data = await api('/notifications')
  notifications.value = data.notifications
  await api('/notifications/read', { method: 'POST' })   // mark all as read
})
</script>

<template>
  <div class="container py-4" style="max-width: 700px">
    <h3 class="mb-3">Notifications</h3>
    <div v-if="!notifications.length" class="text-muted">No notifications yet.</div>
    <ul class="list-group">
      <li v-for="n in notifications" :key="n.id" class="list-group-item" :class="{ 'fw-bold': !n.is_read }">
        {{ n.message }}
        <div class="small text-muted fw-normal">{{ fmtDate(n.created_at) }}</div>
      </li>
    </ul>
  </div>
</template>
