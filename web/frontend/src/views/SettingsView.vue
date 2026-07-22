<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Bot, CheckCircle2, Database, Eye, EyeOff, KeyRound, LoaderCircle, RefreshCw, ShieldCheck, Trash2 } from '@lucide/vue'
import { api } from '@/api'
import { useAppStore } from '@/stores/app'
import type { IndexStatus, Settings } from '@/types'

const store = useAppStore()
const key = ref('')
const showKey = ref(false)
const busy = ref('')
const notice = ref('')
const error = ref('')
let timer: number | undefined
const balance = computed(() => store.settings?.balance_infos?.[0])

async function updateSettings(patch: Record<string, string>) {
  store.settings = await api<Settings>('/settings', { method: 'PATCH', body: JSON.stringify(patch) })
}
async function saveKey() {
  busy.value = 'key'; error.value = ''
  try { store.settings = await api<Settings>('/settings/deepseek-key', { method: 'PUT', body: JSON.stringify({ api_key: key.value }) }); key.value = ''; notice.value = 'API Key 已加密保存，仅后端可读取。' }
  catch (reason) { error.value = reason instanceof Error ? reason.message : '保存失败' }
  finally { busy.value = '' }
}
async function deleteKey() {
  if (!window.confirm('确认移除已保存的 DeepSeek API Key？')) return
  await api('/settings/deepseek-key', { method: 'DELETE' }); await store.load(false)
}
async function testKey() {
  busy.value = 'test'; error.value = ''
  try { store.settings = await api<Settings>('/settings/deepseek-test', { method: 'POST' }); notice.value = '连接成功，模型与余额已刷新。' }
  catch (reason) { error.value = reason instanceof Error ? reason.message : '连接失败' }
  finally { busy.value = '' }
}
async function pollIndex() {
  store.index = await api<IndexStatus>('/index/status')
  if (store.index.state === 'building') timer = window.setTimeout(pollIndex, 1800)
}
async function rebuild() {
  busy.value = 'index'; error.value = ''
  try { store.index = await api<IndexStatus>('/index/rebuild', { method: 'POST' }); notice.value = '索引构建已启动。'; await pollIndex() }
  catch (reason) { error.value = reason instanceof Error ? reason.message : '索引构建失败' }
  finally { busy.value = '' }
}
onMounted(() => store.load(true).catch(reason => { error.value = reason.message }))
onBeforeUnmount(() => window.clearTimeout(timer))
</script>

<template>
  <div class="page settings-page">
    <section class="page-heading"><p class="eyebrow"><ShieldCheck :size="15" /> 仅保存在本机</p><h1>设置</h1><p>配置模型连接、输出偏好和本地知识索引</p></section>
    <div v-if="notice" class="success-banner"><CheckCircle2 :size="17" />{{ notice }}<button @click="notice = ''">×</button></div><div v-if="error" class="error-banner">{{ error }}</div>
    <div class="settings-grid">
      <section class="settings-card panel"><div class="settings-card-head"><span><KeyRound /></span><div><h2>DeepSeek API</h2><p>密钥使用应用加密密钥后写入 SQLite，前端永不读取明文</p></div></div><div v-if="store.settings?.deepseek_configured" class="configured-key"><div><ShieldCheck /><p><strong>已配置</strong><span>{{ store.settings.deepseek_key_masked }}</span></p></div><button @click="deleteKey"><Trash2 :size="16" />移除</button></div><label class="field"><span>{{ store.settings?.deepseek_configured ? '替换 API Key' : 'DeepSeek API Key' }}</span><div class="secret-input"><input v-model="key" :type="showKey ? 'text' : 'password'" autocomplete="off" placeholder="sk-…" /><button type="button" @click="showKey = !showKey"><component :is="showKey ? EyeOff : Eye" :size="18" /></button></div><small>只会提交给本机后端，应用日志会跳过该值。</small></label><div class="button-row"><button class="primary-button" :disabled="key.length < 8 || !!busy" @click="saveKey"><LoaderCircle v-if="busy === 'key'" class="spin" :size="17" />保存密钥</button><button class="ghost-button" :disabled="!store.settings?.deepseek_configured || !!busy" @click="testKey"><Bot :size="17" />{{ busy === 'test' ? '连接中…' : '测试并刷新' }}</button></div><div v-if="store.settings?.deepseek_configured" class="account-grid"><div><small>连接状态</small><strong :class="store.settings.api_available ? 'positive' : ''">{{ store.settings.api_available === true ? '可用' : store.settings.api_available === false ? '连接异常' : '待测试' }}</strong></div><div><small>账户余额</small><strong>{{ balance ? `${balance.total_balance} ${balance.currency}` : '测试后显示' }}</strong></div></div></section>
      <section class="settings-card panel"><div class="settings-card-head"><span><Bot /></span><div><h2>模型与输出</h2><p>模型列表在连接测试后从 DeepSeek 动态读取</p></div></div><label class="field"><span>模型</span><select :value="store.settings?.model" @change="updateSettings({ model: ($event.target as HTMLSelectElement).value })"><option v-if="!store.settings?.models.length" :value="store.settings?.model || 'deepseek-v4-flash'">{{ store.settings?.model || 'deepseek-v4-flash' }}</option><option v-for="model in store.settings?.models" :key="model" :value="model">{{ model }}</option></select></label><label class="field"><span>输出语言</span><select :value="store.settings?.output_language" @change="updateSettings({ output_language: ($event.target as HTMLSelectElement).value })"><option value="zh-CN">中文</option><option value="en">English</option></select></label><label class="field"><span>总结方式</span><select :value="store.settings?.summary_format" @change="updateSettings({ summary_format: ($event.target as HTMLSelectElement).value })"><option value="structured">结构化总结</option><option value="narrative">叙事总结</option></select></label><p class="deprecation-note">默认使用 deepseek-v4-flash；系统不会写死旧的 deepseek-chat 或 deepseek-reasoner 名称。</p></section>
      <section class="settings-card panel index-card"><div class="settings-card-head"><span><Database /></span><div><h2>本地知识索引</h2><p>SQLite FTS5 + BAAI/bge-small-zh-v1.5 向量召回，按文件哈希增量更新</p></div></div><div class="index-state"><div class="index-orb" :class="store.index?.state"><RefreshCw v-if="store.index?.state === 'building'" class="spin" /><Database v-else /></div><div><strong>{{ { empty: '尚未构建', building: '正在构建', ready: '索引就绪', degraded: '关键词模式', failed: '构建失败' }[store.index?.state || 'empty'] }}</strong><span>{{ store.index?.files || 0 }} 个文件 · {{ store.index?.chunks || 0 }} 个片段</span></div></div><div class="index-details"><p><span>向量模型</span><strong>{{ store.index?.embedding_model }}</strong></p><p><span>向量召回</span><strong>{{ store.index?.vector_enabled ? '已启用' : '未启用' }}</strong></p><p><span>最近构建</span><strong>{{ store.index?.last_built_at ? new Date(store.index.last_built_at).toLocaleString('zh-CN') : '从未' }}</strong></p></div><p v-if="store.index?.error" class="index-error">{{ store.index.error }}</p><button class="primary-button" :disabled="store.index?.state === 'building' || !!busy" @click="rebuild"><RefreshCw :class="{ spin: store.index?.state === 'building' }" :size="17" />{{ store.index?.state === 'building' ? '构建中…' : '重建索引' }}</button><small class="safe-note">V1 不会联网更新基金资料；重建只读取挂载的 references 目录。</small></section>
    </div>
  </div>
</template>
