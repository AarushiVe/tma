<script setup>
import NavBar from './components/NavBar.vue'
import { auth } from './auth'
import { messages } from './toast'
</script>

<template>
  <NavBar v-if="auth.user" />
  <router-view />
  <div class="alert-box">
    <div v-for="m in messages" :key="m.id" class="alert py-2" :class="'alert-' + m.type">{{ m.text }}</div>
  </div>
</template>
