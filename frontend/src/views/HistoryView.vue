<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { CalendarDays, Clock3, Search, Trash2 } from '@lucide/vue'
import { api } from '@/api'
import ManagerAvatar from '@/components/ManagerAvatar.vue'
import { modeMeta, useAppStore } from '@/stores/app'
import type { DiscussionMode, Thread } from '@/types'

const appStore = useAppStore()
const threads = ref<Thread[]>([])
const search = ref('')
const mode = ref<'all' | DiscussionMode>('all')
const managerMap = computed(() => new Map(appStore.managers.map(item => [item.id, item])))
const filtered = computed(() => threads.value.filter(item => (mode.value === 'all' || item.mode === mode.value) && `${item.title}${item.last_summary}`.includes(search.value)))
async function load() { threads.value = await api<Thread[]>('/threads') }
async function remove(id: string) {
  if (!window.confirm('确认删除这条讨论及其全部运行记录？')) return
  await api(`/threads/${id}`, { method: 'DELETE' }); await load()
}
onMounted(async () => { if (!appStore.managers.length) await appStore.load(false); await load() })
</script>

<template>
  <div class="page history-page">
    <section class="page-heading"><p class="eyebrow"><Clock3 :size="15" /> 本地持久化记录</p><h1>历史对话</h1><p>查找、打开并继续此前的基金经理讨论</p></section>
    <div class="history-toolbar panel"><label class="search-box"><Search :size="17" /><input v-model="search" placeholder="搜索问题或报告内容" /></label><div class="mode-filter"><button v-for="item in ['all', 'single', 'summary', 'meeting'] as const" :key="item" :class="{ active: mode === item }" @click="mode = item">{{ item === 'all' ? '全部' : modeMeta[item].title.replace('模式', '') }}</button></div></div>
    <div v-if="filtered.length" class="history-list"><article v-for="item in filtered" :key="item.id" class="history-card panel"><RouterLink :to="`/threads/${item.id}`"><div class="history-main"><div class="history-meta"><span>{{ modeMeta[item.mode].title }}</span><small><CalendarDays :size="14" />{{ new Date(item.updated_at).toLocaleString('zh-CN') }}</small></div><h2>{{ item.title }}</h2><p>{{ item.last_summary || '该讨论尚未生成综合报告。' }}</p><div class="history-participants"><ManagerAvatar v-for="id in item.manager_ids" :key="id" :src="managerMap.get(id)?.avatar || ''" :name="managerMap.get(id)?.name || id" :color="managerMap.get(id)?.color" :size="29" /><span>{{ item.manager_ids.map(id => managerMap.get(id)?.name || id).join('、') }}</span></div></div></RouterLink><button class="delete-button" aria-label="删除讨论" @click="remove(item.id)"><Trash2 :size="17" /></button></article></div>
    <div v-else class="empty-state panel"><Clock3 /><h2>没有找到历史讨论</h2><p>完成一次讨论后，线程、发言、报告和引用会保存在这里。</p><RouterLink class="primary-button" to="/">发起讨论</RouterLink></div>
  </div>
</template>
