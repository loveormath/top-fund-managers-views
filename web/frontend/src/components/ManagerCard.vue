<script setup lang="ts">
import { Check } from '@lucide/vue'
import type { Manager } from '@/types'
import ManagerAvatar from './ManagerAvatar.vue'

defineProps<{ manager: Manager; selected?: boolean; selectable?: boolean }>()
defineEmits<{ select: [] }>()
</script>

<template>
  <button class="manager-card" :class="{ selected, static: !selectable }" type="button" @click="$emit('select')">
    <ManagerAvatar :src="manager.avatar" :name="manager.name" :color="manager.color" :size="66" />
    <div class="manager-copy">
      <strong>{{ manager.name }}</strong>
      <span>{{ manager.institution }}</span>
      <div class="tag-row"><em v-for="tag in manager.tags.slice(0, 2)" :key="tag">{{ tag }}</em></div>
    </div>
    <span v-if="selectable" class="select-box" :class="{ checked: selected }"><Check v-if="selected" :size="15" /></span>
  </button>
</template>
