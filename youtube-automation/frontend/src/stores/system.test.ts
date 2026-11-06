import { setActivePinia, createPinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { systemApi } from '../services/system'
import { useSystemStore } from './system'

vi.mock('../services/system', () => ({
  systemApi: {
    health: vi.fn(),
  },
}))

describe('system store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('marks the backend as healthy after a successful check', async () => {
    vi.mocked(systemApi.health).mockResolvedValue({ status: 'ok' })
    const store = useSystemStore()

    await store.checkHealth()

    expect(store.isHealthy).toBe(true)
    expect(store.error).toBeNull()
  })

  it('exposes a useful error when health check fails', async () => {
    vi.mocked(systemApi.health).mockRejectedValue(new Error('Backend indisponível'))
    const store = useSystemStore()

    await store.checkHealth()

    expect(store.isHealthy).toBe(false)
    expect(store.error).toBe('Backend indisponível')
  })
})
