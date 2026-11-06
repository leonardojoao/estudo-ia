export type SettingValue = string | number | boolean | null

export interface HealthResponse {
  status: string
}

export interface SettingsResponse {
  data: Record<string, SettingValue>
}

export type SettingsUpdate = Record<string, string | number | boolean>
