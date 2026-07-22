<script setup lang="ts">
import { ref } from 'vue'
import { Sparkles, Copy, Search, Layers, ShieldCheck } from '@lucide/vue'
import { api } from '@/api'

const fundInput = ref('005827')
const selectedManager = ref('zhang-kun')

const generatedPrompt = ref('')
const fundInfo = ref({ code: '', name: '' })
const loading = ref(false)
const copySuccess = ref(false)

interface ScorePromptResponse {
  success: boolean
  prompt?: string
  fund_code?: string
  fund_name?: string
  error?: string
}

async function getScorePrompt() {
  if (!fundInput.value.trim()) {
    alert('请输入基金代码或名称')
    return
  }

  loading.value = true
  generatedPrompt.value = ''
  try {
    const result = await api<ScorePromptResponse>('/funds/generate-score-prompt', {
      method: 'POST',
      body: JSON.stringify({
        fund_input: fundInput.value.trim(),
        manager: selectedManager.value
      })
    })

    if (result.success) {
      generatedPrompt.value = result.prompt || ''
      fundInfo.value = { code: result.fund_code || '', name: result.fund_name || '' }
    } else {
      alert(result.error || '生成失败')
    }
  } catch (err) {
    alert(err instanceof Error ? err.message : '网络请求失败，请检查后端服务是否启动')
  } finally {
    loading.value = false
  }
}

async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(generatedPrompt.value)
    copySuccess.value = true
    setTimeout(() => { copySuccess.value = false }, 2000)
  } catch (err) {
    alert('复制失败')
  }
}
</script>

<template>
  <div class="page temporary-score-page">
    <section class="page-heading">
      <p class="eyebrow"><Layers :size="15" /> 智能整合面板</p>
      <h1>基金经理风格打分指引生成</h1>
    </section>

    <div class="input-dashboard-grid">
      <section class="panel input-panel">
        <div class="field-group">
          <label class="field-label">🔍 输入基金代码或名称</label>
          <div class="search-box-wrapper">
            <Search :size="16" class="search-icon" />
            <input v-model="fundInput" placeholder="支持代码或名称，如：招商中证白酒 或 005827" />
          </div>
        </div>

        <div class="field-group">
          <label class="field-label">🎯 拟对齐的评分卡经理框架</label>
          <label class="select-control">
            <select v-model="selectedManager">
              <option value="zhang-kun">张坤 评分框架</option>
              <option value="zhang-lu">张璐 评分框架</option>
              <option value="xie-zhi-yu">谢治宇 评分框架</option>
              <option value="liu-xu">刘旭 评分框架</option>
              <option value="zhao-yi">赵诣 评分框架</option>
            </select>
          </label>
        </div>

        <button class="primary-button wide-btn" :disabled="loading" @click="getScorePrompt">
          <Sparkles :size="16" /> {{ loading ? '请稍后...' : '一键生成打分提示词' }}
        </button>
      </section>


      <section v-if="generatedPrompt" class="panel result-panel animate-fade-in">
        <div class="result-header">
          <div>
            <h2>🔮 生成成功：【{{ fundInfo.name }} ({{ fundInfo.code }})】</h2>
            <small class="tip-txt"><ShieldCheck :size="12" /> 数据及 Scorecard 评分卡已就绪</small>
          </div>
          <button class="primary-button" :class="{ 'success-color': copySuccess }" @click="copyToClipboard">
            <Copy :size="14" style="margin-right: 4px; display: inline-block; vertical-align: middle;" />
            {{ copySuccess ? '✅ 已成功复制！' : '一键复制提示词' }}
          </button>
        </div>
        <pre class="prompt-preview-box">{{ generatedPrompt }}</pre>
      </section>
    </div>
  </div>
</template>

<style scoped>
.temporary-score-page { padding: 24px; }
.input-dashboard-grid { display: grid; grid-template-columns: 1fr; gap: 24px; margin-top: 20px; }
@media (min-width: 1024px) { .input-dashboard-grid { grid-template-columns: 1fr 1fr; } }
.panel { background: white; padding: 24px; border-radius: 8px; border: 1px solid #e2e8f0; }
.field-group { margin-bottom: 24px; }
.field-label { font-weight: 600; color: #334155; font-size: 14px; margin-bottom: 8px; display: block; }

.search-box-wrapper { display: flex; align-items: center; border: 1px solid #cbd5e1; border-radius: 6px; background: #f8fafc; padding: 10px 14px; gap: 8px; }
.search-box-wrapper input { border: none; background: transparent; outline: none; flex: 1; font-size: 14px; }
.select-control select { width: 100%; padding: 11px; border: 1px solid #cbd5e1; border-radius: 6px; background: #f8fafc; font-size: 14px; cursor: pointer; }

.wide-btn { width: 100%; padding: 12px; font-weight: 600; justify-content: center; display: flex; align-items: center; gap: 6px; }
.result-panel { display: flex; flex-direction: column; }
.result-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.result-header h2 { font-size: 15px; color: #1e293b; font-weight: bold; margin: 0; }
.tip-txt { color: #64748b; font-size: 12px; display: flex; align-items: center; gap: 4px; margin-top: 4px; }
.success-color { background-color: #10b981 !important; }

.prompt-preview-box { flex: 1; background: #0f172a; color: #38bdf8; padding: 18px; border-radius: 6px; font-family: monospace; font-size: 13px; white-space: pre-wrap; overflow-y: auto; max-height: 520px; border: 1px solid #1e293b; line-height: 1.6; }
.animate-fade-in { animation: fadeIn 0.3s ease-out; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
</style>