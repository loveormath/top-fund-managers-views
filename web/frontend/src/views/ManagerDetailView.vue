<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft, BookOpen, BriefcaseBusiness, Database } from '@lucide/vue'
import { api } from '@/api'
import ManagerAvatar from '@/components/ManagerAvatar.vue'
import type { Manager } from '@/types'

const route = useRoute()
const manager = ref<Manager | null>(null)
onMounted(async () => { manager.value = await api<Manager>(`/managers/${route.params.id}`) })
</script>

<template>
  <div class="page detail-page">
    <RouterLink class="back-link" to="/managers"><ArrowLeft :size="16" />返回经理列表</RouterLink>
    <section v-if="manager" class="manager-hero panel"><ManagerAvatar :src="manager.avatar" :name="manager.name" :color="manager.color" :size="112" /><div><span>{{ manager.institution }}</span><h1>{{ manager.name }}</h1><p>{{ manager.role }}</p><div class="tag-row"><em v-for="tag in manager.tags" :key="tag">{{ tag }}</em></div></div><RouterLink class="primary-button" :to="{ path: '/', query: { manager: manager.id } }">邀请参与讨论</RouterLink></section>
    <div v-if="manager" class="detail-grid"><section class="panel rich-card"><h2><BookOpen />经理简介</h2><pre>{{ manager.profile_excerpt }}</pre></section><section class="panel rich-card"><h2><BriefcaseBusiness />投资方法</h2><pre>{{ manager.method_excerpt }}</pre></section><aside><section class="panel mini-info"><h2><Database />资料统计</h2><p><span>语料文件</span><strong>{{ manager.corpus_files }}</strong></p><p><span>基金数据</span><strong>{{ manager.fund_files }}</strong></p></section><section class="panel mini-info"><h2>代表基金</h2><p v-for="fund in manager.representative_funds" :key="fund.code"><span>{{ fund.name }}</span><em>{{ fund.code }}</em></p></section></aside></div>
  </div>
</template>
