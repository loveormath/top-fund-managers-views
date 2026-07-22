<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Bot, Check, ChevronDown, Filter, Search, Sparkles, UserRound, UsersRound } from '@lucide/vue'
import { api } from '@/api'
import ManagerAvatar from '@/components/ManagerAvatar.vue'
import ManagerCard from '@/components/ManagerCard.vue'
import { modeMeta, useAppStore } from '@/stores/app'
import type { DiscussionMode, Run, Thread } from '@/types'

const store = useAppStore()
const router = useRouter()
const query = ref('')
const company = ref('全部公司')
const previewOpen = ref(false)
const error = ref('')
const starting = ref(false)
const modes: DiscussionMode[] = ['single', 'summary', 'meeting']
const modeIcons = { single: UserRound, summary: UsersRound, meeting: Sparkles }
const filtered = computed(() => store.managers.filter(manager => {
  const matches = `${manager.name}${manager.institution}${manager.tags.join('')}`.includes(query.value.trim())
  return matches && (company.value === '全部公司' || manager.institution === company.value)
}))
const companies = computed(() => ['全部公司', ...new Set(store.managers.map(item => item.institution))])
const readinessHint = computed(() => {
  if (!store.settings?.deepseek_configured) return '请先在设置中配置 DeepSeek API Key'
  if (!['ready', 'degraded'].includes(store.index?.state || '')) return '知识索引尚未就绪，请前往设置构建'
  if (!store.selectionValid) return store.mode === 'single' ? '请选择 1 位基金经理' : '请选择 2–5 位基金经理'
  if (store.topic.trim().length < 2) return '请输入讨论主题'
  return ''
})

async function start() {
  if (!store.canStart) return
  error.value = ''
  starting.value = true
  try {
    const thread = await api<Thread>('/threads', { method: 'POST', body: JSON.stringify({ mode: store.mode, manager_ids: store.selectedIds }) })
    const run = await api<Run>(`/threads/${thread.id}/runs`, { method: 'POST', body: JSON.stringify({ question: store.topic.trim() }) })
    await router.push({ path: `/threads/${thread.id}`, query: { run: run.id } })
  } catch (reason) { error.value = reason instanceof Error ? reason.message : '启动失败' }
  finally { starting.value = false }
}
</script>

<template>
  <div class="page home-page">
    <section class="page-heading">
      <p class="eyebrow"><Bot :size="15" /> Fund Insight 研究工作台</p>
      <h1>选择讨论模式</h1>
      <p>选择合适的讨论模式，邀请基金经理参与对话，获取有来源的专业洞察</p>
    </section>
    <section class="mode-grid">
      <button v-for="item in modes" :key="item" class="mode-card" :class="[item, { selected: store.mode === item }]" @click="store.setMode(item)">
        <span class="mode-icon"><component :is="modeIcons[item]" :size="31" /></span>
        <div><h2>{{ modeMeta[item].title }}</h2><p>{{ modeMeta[item].description }}</p></div>
        <span v-if="store.mode === item" class="mode-check"><Check :size="14" /></span>
        <ul><li v-for="bullet in modeMeta[item].bullets" :key="bullet"><Check :size="15" />{{ bullet }}</li></ul>
      </button>
    </section>
    <div class="home-workspace">
      <section class="manager-panel panel">
        <div class="section-title"><div><h2>选择参与讨论的基金经理</h2><p>{{ store.mode === 'single' ? '选择 1 位' : '可选择 2–5 位' }}</p></div></div>
        <div class="manager-toolbar">
          <label class="search-box"><Search :size="17" /><input v-model="query" placeholder="搜索基金经理姓名、公司或标签" /></label>
          <label class="select-control"><select v-model="company"><option v-for="item in companies" :key="item">{{ item }}</option></select><ChevronDown :size="15" /></label>
          <button class="filter-button"><Filter :size="16" />筛选</button>
        </div>
        <div class="manager-grid">
          <ManagerCard v-for="manager in filtered" :key="manager.id" :manager="manager" selectable :selected="store.selectedIds.includes(manager.id)" @select="store.toggleManager(manager.id)" />
        </div>
        <div class="selection-footer">
          <div class="chosen"><strong>已选择 {{ store.selectedIds.length }} 人</strong><span v-for="manager in store.selectedManagers" :key="manager.id"><ManagerAvatar :src="manager.avatar" :name="manager.name" :color="manager.color" :size="24" />{{ manager.name }}<button @click="store.toggleManager(manager.id)">×</button></span></div>
          <button class="ghost-button preview-toggle" @click="previewOpen = true">设置预览</button>
          <button class="ghost-button" @click="store.selectedIds = []">清空</button>
          <button class="primary-button" :disabled="!store.canStart || starting" :title="readinessHint" @click="start"><Sparkles :size="18" />{{ starting ? '正在创建…' : '开始讨论' }}</button>
        </div>
      </section>
      <div v-if="previewOpen" class="preview-backdrop" @click="previewOpen = false" />
      <aside class="preview-panel panel" :class="{ open: previewOpen }">
        <div class="preview-heading"><h2>讨论设置预览</h2><button @click="previewOpen = false">×</button></div>
        <div class="preview-mode"><small>当前模式</small><div><span class="mini-mode-icon"><component :is="modeIcons[store.mode]" :size="19" /></span><p><strong>{{ modeMeta[store.mode].title }}</strong><span>{{ modeMeta[store.mode].description }}</span></p></div></div>
        <div class="preview-section"><div class="preview-label"><strong>参与人员（{{ store.selectedIds.length }}/{{ store.mode === 'single' ? 1 : 5 }}）</strong><button @click="store.selectedIds = []">清空</button></div><div class="preview-people"><div v-for="manager in store.selectedManagers" :key="manager.id"><ManagerAvatar :src="manager.avatar" :name="manager.name" :color="manager.color" :size="34" /><p><strong>{{ manager.name }}</strong><span>{{ manager.institution }}</span></p><button @click="store.toggleManager(manager.id)">×</button></div><p v-if="!store.selectedIds.length" class="empty-copy">尚未选择基金经理</p></div></div>
        <div class="preview-section"><div class="preview-label"><strong>讨论主题</strong><span>必填</span></div><textarea v-model="store.topic" maxlength="4000" placeholder="例如：请分析当前市场环境下，AI 产业链的投资机会与风险？" /><small class="counter">{{ store.topic.length }}/4000</small></div>
        <div class="preview-section other-settings"><strong>其他设置</strong><p><span>输出语言</span><em>{{ store.settings?.output_language === 'en' ? 'English' : '中文' }}</em></p><p><span>总结方式</span><em>{{ store.settings?.summary_format === 'narrative' ? '叙事总结' : '结构化总结' }}</em></p><p><span>知识索引</span><em :class="store.index?.state">{{ store.index?.state || '加载中' }}</em></p></div>
        <RouterLink v-if="readinessHint && (!store.ready)" class="setup-hint" to="/settings">{{ readinessHint }} →</RouterLink>
        <p v-if="error" class="error-banner">{{ error }}</p>
      </aside>
    </div>
  </div>
</template>
