import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: MainLayout,
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
        }
      ]
    }
  ]
})

export default router