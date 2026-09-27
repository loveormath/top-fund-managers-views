import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { AgentTrace, ManagerView } from '@/types'

export const useRunStore = defineStore('run', () => {
  const activeRunId = ref<string | null>(null)
  const status = ref('idle')
  const views = ref<ManagerView[]>([])
  const streams = ref<Record<string, string>>({})
  const report = ref('')
  const round = ref(0)
  const error = ref('')
  const agentTrace = ref<AgentTrace[]>([])
  let source: EventSource | null = null

  function reset(runId: string) {
    source?.close()
    activeRunId.value = runId
    status.value = 'pending'
    views.value = []
    streams.value = {}
    report.value = ''
    round.value = 0
    error.value = ''
    agentTrace.value = []
  }
  function connect(runId: string, onDone?: () => void) {
    reset(runId)
    source = new EventSource(`/api/runs/${runId}/events`)
    source.addEventListener('run.started', () => { status.value = 'running' })
    source.addEventListener('agent.plan.created', event => {
      const data = JSON.parse((event as MessageEvent).data)
      const managerText = data.manager_ids?.length ? `；经理：${data.manager_ids.join('、')}` : ''
      agentTrace.value.push({ id: `plan-${data.step}`, kind: 'plan', title: `第 ${data.step} 步·规划`, detail: `${data.reason}${managerText}`, status: 'completed', step: data.step })
    })
    source.addEventListener('agent.tool.started', event => {
      const data = JSON.parse((event as MessageEvent).data)
      const title = data.tool === 'search_corpus' ? '检索本地资料' : `调用${data.mode === 'meeting' ? '两轮会议' : data.mode === 'single' ? '单人分析' : '多人综合'}`
      agentTrace.value.push({ id: `tool-${data.step}`, kind: 'tool', title, detail: `目标经理：${data.manager_ids.join('、')}`, status: 'running', step: data.step })
    })
    source.addEventListener('agent.tool.completed', event => {
      const data = JSON.parse((event as MessageEvent).data)
      const item = agentTrace.value.find(entry => entry.id === `tool-${data.step}`)
      if (item) {
        item.status = 'completed'
        item.detail += data.failed ? `；执行失败：${data.error}` : `；已返回 ${data.result_count ?? data.view_count ?? 0} 项结果`
      }
    })
    source.addEventListener('agent.critique.completed', event => {
      const data = JSON.parse((event as MessageEvent).data)
      agentTrace.value.push({ id: `critique-${data.step}`, kind: 'critique', title: data.sufficient ? '质检通过' : '需要继续补证', detail: data.reason || data.gaps?.join('；') || '已完成评审', status: 'completed', step: data.step })
    })
    source.addEventListener('round.started', event => { round.value = JSON.parse((event as MessageEvent).data).round })
    source.addEventListener('manager.started', event => {
      const data = JSON.parse((event as MessageEvent).data)
      streams.value[`${data.manager_id}:${data.stage}`] = ''
    })
    source.addEventListener('manager.delta', event => {
      const data = JSON.parse((event as MessageEvent).data)
      const key = `${data.manager_id}:${data.stage}`
      streams.value[key] = (streams.value[key] || '') + data.delta
    })
    source.addEventListener('manager.completed', event => {
      const data = JSON.parse((event as MessageEvent).data)
      if (data.view) views.value.push(data.view)
    })
    source.addEventListener('moderator.delta', event => { report.value += JSON.parse((event as MessageEvent).data).delta })
    source.addEventListener('run.completed', event => {
      const data = JSON.parse((event as MessageEvent).data)
      report.value = data.final_report
      status.value = 'completed'
      source?.close()
      onDone?.()
    })
    source.addEventListener('run.failed', event => {
      const data = JSON.parse((event as MessageEvent).data)
      status.value = data.cancelled ? 'cancelled' : 'failed'
      error.value = data.error || '运行已取消'
      source?.close()
      onDone?.()
    })
    source.onerror = () => {
      if (status.value === 'running' || status.value === 'pending') error.value = '事件连接暂时中断，浏览器会自动重连。'
    }
  }
  function close() { source?.close() }
  return { activeRunId, status, views, streams, report, round, error, agentTrace, connect, close }
})
