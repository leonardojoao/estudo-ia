import { api } from './api'
import type { HealthResponse, SettingsResponse, SettingsUpdate } from '../types'

export const systemApi = {
  async health(): Promise<HealthResponse> {
    const response = await api.get<HealthResponse>('/health')
    return response.data
  },
  async getSettings(): Promise<SettingsResponse> {
    const response = await api.get<SettingsResponse>('/api/settings')
    return response.data
  },
  async updateSettings(payload: SettingsUpdate): Promise<SettingsResponse> {
    const response = await api.put<SettingsResponse>('/api/settings', payload)
    return response.data
  },
}
