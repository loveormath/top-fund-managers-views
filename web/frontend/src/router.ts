import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView },
    { path: '/managers', component: () => import('@/views/ManagersView.vue') },
    { path: '/managers/:id', component: () => import('@/views/ManagerDetailView.vue') },
    { path: '/fund-score', component: () => import('@/views/FundScoreView.vue') },

    { path: '/history', component: () => import('@/views/HistoryView.vue') },
    { path: '/threads/:id', component: () => import('@/views/DiscussionView.vue') },
    { path: '/settings', component: () => import('@/views/SettingsView.vue') },
  ],
  scrollBehavior: () => ({ top: 0 }),
})