import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { systemApi } from '../services/system'

export const useSystemStore = defineStore('system', () => {
  const loading = ref(false)
  const status = ref<string | null>(null)
  const error = ref<string | null>(null)

  const isHealthy = computed(() => status.value === 'ok')

  async function checkHealth() {
    loading.value = true
    error.value = null
    try {
      const response = await systemApi.health()
      status.value = response.status
    } catch (reason) {
      status.value = null
      error.value =
        reason instanceof Error ? reason.message : 'Não foi possível conectar ao backend.'
    } finally {
      loading.value = false
    }
  }

  return { loading, status, error, isHealthy, checkHealth }
})
