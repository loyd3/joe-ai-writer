import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/AuthPage.vue'),
      meta: { public: true }
    },
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'home',
          component: () => import('@/views/ProjectList.vue')
        },
        {
          path: 'project/:id',
          name: 'project',
          component: () => import('@/views/ProjectView.vue')
        },
        {
          path: 'document/:id',
          name: 'document',
          component: () => import('@/views/DocumentEditor.vue')
        },
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue')
        },
        {
          path: 'hot-topics',
          name: 'hot-topics',
          component: () => import('@/views/HotTopicsWriter.vue'),
          meta: { title: '热点写作' }
        },
        {
          path: 'ai-story-generator',
          name: 'ai-story-generator',
          component: () => import('@/views/AIStoryGenerator.vue'),
          meta: { title: 'AI故事生成器' }
        },
        {
          path: 'long-article',
          name: 'long-article',
          component: () => import('@/views/LongArticleGenerator.vue'),
          meta: { title: '长篇文章生成器' }
        }
      ]
    }
  ]
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  
  // 初始化认证状态
  if (!authStore.initialized) {
    await authStore.init()
  }
  
  // 需要登录的页面
  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    next('/login')
    return
  }
  
  // 已登录用户访问登录页，重定向到首页
  if (to.path === '/login' && authStore.isLoggedIn) {
    next('/')
    return
  }
  
  next()
})

export default router
