<script setup>
import { computed } from 'vue'
const props = defineProps({ value: String })

const colors = {
  Open: 'success', Booked: 'success', active: 'success', Paid: 'success', Done: 'success',
  Approved: 'primary', Easy: 'primary', Moderate: 'info', Hard: 'dark',
  Pending: 'secondary', Refunded: 'info', Closed: 'secondary', deactivated: 'secondary',
  Completed: 'dark', Cancelled: 'danger', blacklisted: 'danger', Failed: 'danger',
}
const color = computed(() => colors[props.value] || 'secondary')
</script>

<template><span class="badge" :class="'bg-' + color">{{ value }}</span></template>
