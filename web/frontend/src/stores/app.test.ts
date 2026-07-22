import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAppStore } from './app'

describe('discussion selection rules', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('keeps exactly one manager in single mode', () => {
    const store = useAppStore()
    store.selectedIds = ['liu-xu']
    store.toggleManager('zhang-kun')
    expect(store.selectedIds).toEqual(['zhang-kun'])
    expect(store.selectionValid).toBe(true)
  })

  it('requires 2–5 managers in summary and meeting modes', () => {
    const store = useAppStore()
    store.setMode('meeting')
    store.selectedIds = ['liu-xu']
    expect(store.selectionValid).toBe(false)
    store.toggleManager('zhang-kun')
    expect(store.selectionValid).toBe(true)
    for (const id of ['zhang-lu', 'xie-zhi-yu', 'zhao-yi', 'ignored-sixth']) store.toggleManager(id)
    expect(store.selectedIds).toHaveLength(5)
  })

  it('disables start without key, index, topic and valid selection', () => {
    const store = useAppStore()
    store.selectedIds = ['liu-xu']
    store.topic = '分析制造业'
    expect(store.canStart).toBe(false)
  })
})
