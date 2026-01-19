import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import KnowledgeBaseChat from '@/components/KnowledgeBaseChat.vue'
import KnowledgeBaseManager from '@/pages/KnowledgeBaseManager.vue'
import AboutAuthor from '@/pages/AboutAuthor.vue'
import LLMConfigManager from '@/pages/LLMConfigManager.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Chat',
    component: KnowledgeBaseChat,
  },
  {
    path: '/kb',
    name: 'KnowledgeBaseManager',
    component: KnowledgeBaseManager,
  },
  {
    path: '/about',
    name: 'AboutAuthor',
    component: AboutAuthor,
  },
  {
    path: '/settings',
    name: 'Settings',
    component: LLMConfigManager,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
