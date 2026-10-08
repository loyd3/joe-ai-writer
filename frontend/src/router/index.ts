import { createRouter, createWebHistory, type NavigationGuardNext, type RouteLocationNormalized } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSettingsDrawerStore, type SettingsPanel } from '@/stores/settingsDrawer'

/** 旧设置页路由：打开右侧抽屉并停留在当前页 */
function openSettingsDrawer(panel: SettingsPanel) {
  return (to: RouteLocationNormalized, from: RouteLocationNormalized, next: NavigationGuardNext) => {
    useSettingsDrawerStore().show(panel)
    if (from.matched.length) next(false)
    else next({ name: 'home', replace: true })
  }
}

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
          path: 'profile',
          name: 'profile',
          component: () => import('@/views/ProjectList.vue'),
          beforeEnter: openSettingsDrawer('profile'),
        },
        {
          path: 'writing-style',
          name: 'writing-style',
          component: () => import('@/views/ProjectList.vue'),
          beforeEnter: openSettingsDrawer('writing-style'),
        },
        {
          path: 'ai-config',
          name: 'ai-config',
          component: () => import('@/views/ProjectList.vue'),
          beforeEnter: openSettingsDrawer('ai-config'),
        },
        {
          path: 'theme-settings',
          name: 'theme-settings',
          component: () => import('@/views/ProjectList.vue'),
          beforeEnter: openSettingsDrawer('theme'),
        },
        {
          path: 'project/:id/writing-style',
          redirect: '/writing-style',
        },
        {
          path: 'project/:id',
          name: 'project',
          component: () => import('@/views/ProjectView.vue')
        },
        {
          path: 'project/:id/settings',
          name: 'project-settings',
          component: () => import('@/views/ProjectSettingsView.vue'),
          meta: { title: '项目设定' }
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
          path: 'brainstorm-writing',
          name: 'brainstorm-writing',
          component: () => import('@/views/BrainstormWriting.vue'),
          meta: { title: '脑洞写作' }
        },
        {
          path: 'copywriting-writing',
          name: 'copywriting-writing',
          component: () => import('@/views/CopywritingWriter.vue'),
          meta: { title: '文案写作' }
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
