<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Bot, ChartNoAxesCombined, Clock3, Home, Menu, Settings, Users, X, Sparkles } from '@lucide/vue'
import { useAppStore } from '@/stores/app'
import ManagerAvatar from '@/components/ManagerAvatar.vue'

const store = useAppStore()
const route = useRoute()
const mobileOpen = ref(false)
const title = computed(() => store.settings?.model || 'DeepSeek')
onMounted(() => store.load(false).catch(() => undefined))
</script>

<template>
  <div class="app-shell">
    <button class="mobile-menu" aria-label="打开导航" @click="mobileOpen = true"><Menu /></button>
    <div v-if="mobileOpen" class="nav-backdrop" @click="mobileOpen = false" />
    <aside class="sidebar" :class="{ open: mobileOpen }">
      <div class="brand"><span class="brand-mark"><ChartNoAxesCombined :size="22" /></span><strong>Fund Insight</strong></div>
      <button class="close-nav" aria-label="关闭导航" @click="mobileOpen = false"><X /></button>
      <nav @click="mobileOpen = false">
        <RouterLink to="/" :class="{ active: route.path === '/' }"><Home /><span>首页</span></RouterLink>
        <RouterLink to="/managers" :class="{ active: route.path.startsWith('/managers') }"><Users /><span>基金经理</span></RouterLink>
        <RouterLink to="/fund-score" :class="{ active: route.path === '/fund-score' }"><Sparkles /><span>风格打分</span></RouterLink>

        <RouterLink to="/history" :class="{ active: route.path.startsWith('/history') || route.path.startsWith('/threads') }"><Clock3 /><span>历史对话</span></RouterLink>
        <RouterLink to="/settings" :class="{ active: route.path === '/settings' }"><Settings /><span>设置</span></RouterLink>
      </nav>
      <div class="api-mini">
        <div><Bot :size="17" /><strong>DeepSeek API</strong></div>
        <span>{{ store.settings?.deepseek_configured ? '已安全配置' : '等待配置' }}</span>
        <div class="mini-track"><i :style="{ width: store.settings?.deepseek_configured ? '100%' : '12%' }" /></div>
        <small>索引：{{ store.index?.state || '加载中' }}</small>
      </div>
    </aside>
    <main class="main-area">
      <header class="topbar">
        <div class="model-pill"><Bot :size="17" /><span>模型：{{ title }}</span></div>
        <RouterLink class="icon-button" to="/settings" aria-label="设置"><Settings :size="19" /></RouterLink>
        <div class="local-user"><ManagerAvatar src="" name="研" color="#64748b" :size="30" /><strong>本地研究者</strong></div>
      </header>
      <RouterView />
    </main>
  </div>
</template>