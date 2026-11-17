<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import Chart from 'chart.js/auto'

const props = defineProps({ type: String, labels: Array, values: Array, title: String })
const canvas = ref(null)
let chart = null

function draw() {
  if (chart) chart.destroy()
  chart = new Chart(canvas.value, {
    type: props.type,
    data: {
      labels: props.labels,
      datasets: [{
        label: props.title,
        data: props.values,
        backgroundColor: ['#0d47a1', '#1976d2', '#42a5f5', '#90caf9', '#bbdefb'],
      }],
    },
    options: { responsive: true, maintainAspectRatio: false },
  })
}

onMounted(draw)
watch(() => props.values, draw)
onBeforeUnmount(() => { if (chart) chart.destroy() })
</script>

<template>
  <div style="height: 250px"><canvas ref="canvas"></canvas></div>
</template>
