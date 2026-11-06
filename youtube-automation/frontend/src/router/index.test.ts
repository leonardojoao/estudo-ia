import { createRouter, createWebHistory } from 'vue-router'
import { describe, expect, it } from 'vitest'

import router from './index'

describe('router', () => {
  it('navigates to the settings page', async () => {
    await router.push('/settings')
    await router.isReady()

    expect(router.currentRoute.value.name).toBe('settings')
  })

  it('redirects unknown routes to dashboard', async () => {
    const isolatedRouter = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', name: 'dashboard', component: { template: '<div />' } },
        { path: '/:pathMatch(.*)*', redirect: '/' },
      ],
    })

    await isolatedRouter.push('/unknown')
    expect(isolatedRouter.currentRoute.value.name).toBe('dashboard')
  })
})
