import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { systemApi } from '../services/system'
import type { SettingValue } from '../types'

const hiddenKeys = new Set(['secret_key', 'oauth_credentials', 'credentials'])

const fieldLabels: Record<string, string> = {
  ollama_url: 'URL do Ollama',
  ollama_model: 'Modelo do Ollama',
  tts_voice: 'Voz de narração',
  default_dimension: 'Dimensão padrão',
  clip_min_duration: 'Duração mínima do clipe',
  clip_max_duration: 'Duração máxima do clipe',
}

export const useSettingsStore = defineStore('settings', () => {
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)
  const message = ref<string | null>(null)
  const adminKey = ref('')
  const values = ref<Record<string, SettingValue>>({})
  const form = ref<Record<string, string | number>>({})

  const editableFields = computed(() =>
    Object.keys(form.value)
      .filter((key) => !hiddenKeys.has(key))
      .map((key) => ({
        key,
        label: fieldLabels[key] ?? key.split('_').join(' '),
        type: typeof form.value[key] === 'number' ? 'number' : 'text',
      })),
  )

  async function load() {
    loading.value = true
    error.value = null
    message.value = null
    try {
      const response = await systemApi.getSettings()
      values.value = Object.fromEntries(
        Object.entries(response.data).filter(([key]) => !hiddenKeys.has(key)),
      )
      form.value = Object.fromEntries(
        Object.entries(values.value).filter(
          (entry): entry is [string, string | number] =>
            typeof entry[1] === 'string' || typeof entry[1] === 'number',
        ),
      )
    } catch (reason) {
      error.value =
        reason instanceof Error ? reason.message : 'Não foi possível carregar as configurações.'
    } finally {
      loading.value = false
    }
  }

  async function save() {
    saving.value = true
    error.value = null
    message.value = null
    try {
      await systemApi.updateSettings(form.value, adminKey.value)
      adminKey.value = ''
      message.value = 'Configurações atualizadas com sucesso.'
      await load()
    } catch (reason) {
      error.value =
        reason instanceof Error ? reason.message : 'Não foi possível salvar as configurações.'
    } finally {
      saving.value = false
    }
  }

  return {
    loading,
    saving,
    error,
    message,
    adminKey,
    values,
    form,
    editableFields,
    load,
    save,
  }
})
