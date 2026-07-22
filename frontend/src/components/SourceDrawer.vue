<script setup lang="ts">
import { ref, watch } from 'vue'
import { FileText, X } from '@lucide/vue'
import { api } from '@/api'
import type { Evidence } from '@/types'

const props = defineProps<{ evidence: Evidence | null }>()
defineEmits<{ close: [] }>()
const source = ref<Record<string, string> | null>(null)
const loading = ref(false)
watch(() => props.evidence, async evidence => {
  source.value = null
  if (!evidence?.chunk_id) return
  loading.value = true
  try { source.value = await api<Record<string, string>>(`/sources/${evidence.chunk_id}`) }
  finally { loading.value = false }
})
</script>

<template>
  <Teleport to="body">
    <div v-if="evidence" class="drawer-backdrop" @click.self="$emit('close')">
      <aside class="source-drawer">
        <header><div><FileText :size="20" /><strong>资料来源</strong></div><button @click="$emit('close')"><X /></button></header>
        <div class="drawer-body">
          <span class="source-type">{{ source?.document_type || '知识库资料' }}</span>
          <h2>{{ evidence.title || '未命名片段' }}</h2>
          <p class="source-path">{{ evidence.source_file }}</p>
          <div class="quote-card"><small>回答中的直接证据</small><blockquote>{{ evidence.quote }}</blockquote></div>
          <div class="source-content"><small>索引原文</small><p v-if="loading">正在读取…</p><pre v-else>{{ source?.content || evidence.excerpt }}</pre></div>
          <p class="exact-note">直接引语已经过后端逐字匹配校验。推演内容不会被列为直接引语。</p>
        </div>
      </aside>
    </div>
  </Teleport>
</template>
