import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'flow',
    component: () => import('../views/FlowSelectView.vue'),
    meta: { title: '流量选型' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.afterEach((to) => {
  document.title = `${to.meta.title || '选型'} · 设备选型助手`
})

export default router
