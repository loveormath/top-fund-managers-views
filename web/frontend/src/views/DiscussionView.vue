<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { AlertCircle, ArrowUp, CheckCircle2, FileText, LoaderCircle, MessageSquareText, Sparkles, StopCircle } from '@lucide/vue'
import { api } from '@/api'
import ManagerAvatar from '@/components/ManagerAvatar.vue'
import SourceDrawer from '@/components/SourceDrawer.vue'
import { modeMeta, useAppStore } from '@/stores/app'
import { useRunStore } from '@/stores/run'
import type { Evidence, ManagerView, Run, Thread } from '@/types'

const route = useRoute()
const appStore = useAppStore()
const runStore = useRunStore()
const thread = ref<Thread | null>(null)
const activeTab = ref<'process' | 'report'>('process')
const followup = ref('')
const sending = ref(false)
const selectedEvidence = ref<Evidence | null>(null)
const pageError = ref('')

const managerMap = computed(() => new Map(appStore.managers.map(item => [item.id, item])))
const savedViews = computed(() => (thread.value?.messages || []).flatMap(message => {
  if (message.role !== 'manager') return []
  try { return [JSON.parse(message.content) as ManagerView] } catch { return [] }
}))
const views = computed(() => runStore.views.length ? runStore.views : savedViews.value)
const reportText = computed(() => runStore.report || thread.value?.runs.at(-1)?.final_report || thread.value?.last_summary || '')
const reportHtml = computed(() => DOMPurify.sanitize(marked.parse(reportText.value) as string))
const isRunning = computed(() => ['pending', 'running'].includes(runStore.status))
const currentQuestion = computed(() => thread.value?.runs.at(-1)?.question || '')

async function loadThread() {
  thread.value = await api<Thread>(`/threads/${route.params.id}`)
}
function attach(runId: string) { runStore.connect(runId, loadThread) }
async function askFollowup() {
  if (!followup.value.trim() || sending.value) return
  sending.value = true
  pageError.value = ''
  try {
    const run = await api<Run>(`/threads/${route.params.id}/runs`, { method: 'POST', body: JSON.stringify({ question: followup.value.trim() }) })
    followup.value = ''
    await loadThread()
    attach(run.id)
  } catch (reason) { pageError.value = reason instanceof Error ? reason.message : '追问失败' }
  finally { sending.value = false }
}
async function cancel() {
  if (!runStore.activeRunId) return
  await api(`/runs/${runStore.activeRunId}/cancel`, { method: 'POST' }).catch(() => undefined)
}
onMounted(async () => {
  try {
    await Promise.all([loadThread(), appStore.managers.length ? Promise.resolve() : appStore.load(false)])
    const runId = String(route.query.run || '')
    const active = thread.value?.runs.find(item => item.id === runId) || thread.value?.runs.at(-1)
    if (active && ['pending', 'running'].includes(active.status)) attach(active.id)
    else if (active) { runStore.status = active.status; runStore.report = active.final_report }
  } catch (reason) { pageError.value = reason instanceof Error ? reason.message : '加载讨论失败' }
})
onBeforeUnmount(() => runStore.close())
</script>

<template>
  <div class="page discussion-page">
    <section class="discussion-header panel">
      <div><span class="mode-badge">{{ thread ? modeMeta[thread.mode].title : '讨论' }}</span><h1>{{ thread?.title || '正在加载讨论…' }}</h1><p v-if="currentQuestion">{{ currentQuestion }}</p></div>
      <div class="participant-stack"><ManagerAvatar v-for="id in thread?.manager_ids" :key="id" :src="managerMap.get(id)?.avatar || ''" :name="managerMap.get(id)?.name || id" :color="managerMap.get(id)?.color" :size="38" /></div>
    </section>
    <div v-if="pageError" class="error-banner"><AlertCircle :size="17" />{{ pageError }}</div>
    <div class="result-tabs"><button :class="{ active: activeTab === 'process' }" @click="activeTab = 'process'"><MessageSquareText :size="17" />讨论过程</button><button :class="{ active: activeTab === 'report' }" @click="activeTab = 'report'"><FileText :size="17" />综合报告</button></div>
    <section v-if="activeTab === 'process'" class="process-layout">
      <div class="timeline panel">
        <div v-if="isRunning" class="live-status"><LoaderCircle class="spin" :size="18" /><p><strong>讨论正在进行</strong><span>{{ thread?.mode === 'meeting' ? `第 ${runStore.round || 1} 轮` : '经理正在整理观点' }}</span></p><button @click="cancel"><StopCircle :size="16" />取消</button></div>
        <div v-if="!views.length && !isRunning" class="empty-state"><Sparkles /><h2>还没有讨论内容</h2><p>在下方输入问题开始本线程的第一次讨论。</p></div>
        <article v-for="(view, index) in views" :key="`${view.manager_id}-${view.stage}-${index}`" class="speech-card">
          <div class="speech-head"><ManagerAvatar :src="managerMap.get(view.manager_id)?.avatar || ''" :name="view.manager_name" :color="managerMap.get(view.manager_id)?.color" :size="48" /><div><h3>{{ view.manager_name }}</h3><p>{{ view.stage === 'response' ? '第二轮 · 交叉回应' : view.stage === 'opening' ? '第一轮 · 独立开场' : '独立分析' }}</p></div><span class="confidence" :class="view.confidence">置信度 {{ view.confidence }}</span></div>
          <p class="position">{{ view.position }}</p>
          <div v-if="view.method_inference.length" class="inference-list"><p v-for="item in view.method_inference" :key="item">{{ item }}</p></div>
          <div v-if="[...view.direct_evidence, ...view.holdings_evidence].length" class="evidence-list"><button v-for="evidence in [...view.direct_evidence, ...view.holdings_evidence]" :key="`${evidence.chunk_id}-${evidence.quote}`" @click="selectedEvidence = evidence"><FileText :size="15" /><span>“{{ evidence.quote }}”</span><em>查看来源</em></button></div>
          <div v-if="view.missing_information.length" class="missing"><strong>资料边界</strong><span>{{ view.missing_information.join('；') }}</span></div>
        </article>
        <article v-for="(stream, key) in runStore.streams" v-show="stream && !views.some(item => `${item.manager_id}:${item.stage}` === key)" :key="key" class="speech-card streaming"><LoaderCircle class="spin" :size="17" /><p>{{ stream }}</p></article>
      </div>
      <aside class="live-report panel"><div class="section-title"><div><h2>主持摘要</h2><p>内容会随讨论实时更新</p></div></div><div v-if="reportText" class="markdown-body" v-html="reportHtml" /><div v-else class="report-placeholder"><Sparkles /><p>经理发言完成后，这里会生成综合报告。</p></div></aside>
    </section>
    <section v-else class="report-panel panel"><div class="report-title"><span><CheckCircle2 /></span><div><h2>综合研究报告</h2><p>由所选经理观点与本地资料生成</p></div></div><div v-if="reportText" class="markdown-body report-markdown" v-html="reportHtml" /><div v-else class="empty-state"><FileText /><h2>报告尚未生成</h2></div></section>
    <section class="followup-bar panel"><div><strong>继续追问</strong><span>保持当前模式与参与经理，并读取本线程历史摘要</span></div><form @submit.prevent="askFollowup"><textarea v-model="followup" :disabled="isRunning" placeholder="基于刚才的讨论继续提问…" /><button class="primary-button" :disabled="isRunning || sending || followup.trim().length < 2"><ArrowUp :size="18" /></button></form></section>
    <SourceDrawer :evidence="selectedEvidence" @close="selectedEvidence = null" />
  </div>
</template>
