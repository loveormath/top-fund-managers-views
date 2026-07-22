import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/api'
import type { DiscussionMode, IndexStatus, Manager, Settings } from '@/types'

export const modeMeta: Record<DiscussionMode, { title: string; description: string; bullets: string[] }> = {
  single: { title: '单人总结模式', description: '与一位基金经理对话，获得基于资料的独立观点', bullets: ['深入观点分析', '个性化追问'] },
  summary: { title: '多人总结模式', description: '邀请多位基金经理独立发表观点，生成综合对比', bullets: ['多角度观点碰撞', '共识与分歧总结'] },
  meeting: { title: '会议讨论模式', description: '模拟两轮基金经理圆桌，阅读观点后交叉回应', bullets: ['两轮互动讨论', '主持人结构化报告'] },
}

export const useAppStore = defineStore('app', () => {
  const managers = ref<Manager[]>([])
  const settings = ref<Settings | null>(null)
  const index = ref<IndexStatus | null>(null)
  const loading = ref(false)
  const mode = ref<DiscussionMode>('single')
  const selectedIds = ref<string[]>([])
  const topic = ref('')

  const selectedManagers = computed(() => managers.value.filter(item => selectedIds.value.includes(item.id)))
  const selectionValid = computed(() => mode.value === 'single' ? selectedIds.value.length === 1 : selectedIds.value.length >= 2 && selectedIds.value.length <= 5)
  const ready = computed(() => Boolean(settings.value?.deepseek_configured && ['ready', 'degraded'].includes(index.value?.state ?? '')))
  const canStart = computed(() => selectionValid.value && ready.value && topic.value.trim().length >= 2)

  function setMode(value: DiscussionMode) {
    mode.value = value
    if (value === 'single' && selectedIds.value.length > 1) selectedIds.value = selectedIds.value.slice(0, 1)
  }
  function toggleManager(id: string) {
    if (selectedIds.value.includes(id)) selectedIds.value = selectedIds.value.filter(item => item !== id)
    else if (mode.value === 'single') selectedIds.value = [id]
    else if (selectedIds.value.length < 5) selectedIds.value.push(id)
  }
  async function load(refresh = false) {
    loading.value = true
    try {
      const [managerData, settingData, indexData] = await Promise.all([
        api<Manager[]>('/managers'), api<Settings>(`/settings?refresh=${refresh}`), api<IndexStatus>('/index/status'),
      ])
      managers.value = managerData
      settings.value = settingData
      index.value = indexData
      if (!selectedIds.value.length && managerData.length) selectedIds.value = [managerData[0].id]
    } finally { loading.value = false }
  }
  return { managers, settings, index, loading, mode, selectedIds, topic, selectedManagers, selectionValid, ready, canStart, setMode, toggleManager, load }
})
