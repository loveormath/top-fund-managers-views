import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { ManagerView } from '@/types'

export const useRunStore = defineStore('run', () => {
  const activeRunId = ref<string | null>(null)
  const status = ref('idle')
  const views = ref<ManagerView[]>([])
  const streams = ref<Record<string, string>>({})
  const report = ref('')
  const round = ref(0)
  const error = ref('')
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
  }
  function connect(runId: string, onDone?: () => void) {
    reset(runId)
    source = new EventSource(`/api/runs/${runId}/events`)
    source.addEventListener('run.started', () => { status.value = 'running' })
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
  return { activeRunId, status, views, streams, report, round, error, connect, close }
})
