<script setup lang="ts">
import { computed, ref } from 'vue'
import { Search, Users } from '@lucide/vue'
import ManagerCard from '@/components/ManagerCard.vue'
import { useAppStore } from '@/stores/app'

const store = useAppStore()
const query = ref('')
const list = computed(() => store.managers.filter(item => `${item.name}${item.institution}${item.tags.join('')}`.includes(query.value)))
</script>

<template>
  <div class="page directory-page">
    <section class="page-heading"><p class="eyebrow"><Users :size="15" /> 经理知识库</p><h1>基金经理</h1><p>浏览五位基金经理的资料范围、投资方法与代表基金</p></section>
    <label class="search-box directory-search"><Search :size="17" /><input v-model="query" placeholder="搜索姓名、公司或投资标签" /></label>
    <div class="directory-grid"><RouterLink v-for="manager in list" :key="manager.id" :to="`/managers/${manager.id}`"><ManagerCard :manager="manager" /><div class="manager-stats"><span><strong>{{ manager.corpus_files }}</strong>份语料</span><span><strong>{{ manager.fund_files }}</strong>份基金数据</span></div><p>{{ manager.profile_excerpt }}</p><button>查看经理档案 →</button></RouterLink></div>
  </div>
</template>
