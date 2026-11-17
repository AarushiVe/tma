<script setup>
defineProps({ show: Boolean, title: String, large: Boolean })
const emit = defineEmits(['close'])
</script>

<template>
  <div v-if="show">
    <div class="modal-backdrop show"></div>
    <div class="modal d-block">
      <div class="modal-dialog modal-dialog-scrollable" :class="{ 'modal-lg': large }">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ title }}</h5>
            <button type="button" class="btn-close" @click="emit('close')"></button>
          </div>
          <div class="modal-body"><slot /></div>
          <div class="modal-footer"><slot name="footer" /></div>
        </div>
      </div>
    </div>
  </div>
</template>
