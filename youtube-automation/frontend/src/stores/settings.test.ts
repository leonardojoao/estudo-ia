import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { systemApi } from '../services/system'
import { useSettingsStore } from './settings'

vi.mock('../services/system', () => ({
  systemApi: {
    getSettings: vi.fn(),
    updateSettings: vi.fn(),
  },
}))

describe('settings store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('removes sensitive values from the editable form', async () => {
    vi.mocked(systemApi.getSettings).mockResolvedValue({
      data: {
        ollama_url: 'http://localhost:11434',
        secret_key: 'never-display',
        clip_min_duration: '3',
      },
    })
    const store = useSettingsStore()

    await store.load()

    expect(store.form).toEqual({
      ollama_url: 'http://localhost:11434',
      clip_min_duration: '3',
    })
    expect(store.editableFields.some((field) => field.key === 'secret_key')).toBe(false)
  })

  it('sends the administrative key only when saving', async () => {
    vi.mocked(systemApi.getSettings).mockResolvedValue({ data: { ollama_model: 'llama3' } })
    vi.mocked(systemApi.updateSettings).mockResolvedValue({ data: { ollama_model: 'llama3' } })
    const store = useSettingsStore()
    await store.load()
    store.adminKey = 'temporary-key'

    await store.save()

    expect(systemApi.updateSettings).toHaveBeenCalledWith(
      { ollama_model: 'llama3' },
      'temporary-key',
    )
    expect(store.adminKey).toBe('')
  })
})
