<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ src: string; name: string; color?: string; size?: number }>()
const failed = ref(false)
</script>

<template>
  <div class="manager-avatar" :style="{ width: `${size || 54}px`, height: `${size || 54}px`, background: `${color || '#2563eb'}18` }">
    <img v-if="src && !failed" :src="src" :alt="`${name}插画头像`" @error="failed = true" />
    <span v-else :style="{ color: color || '#2563eb' }">{{ name.slice(0, 1) }}</span>
  </div>
</template>
