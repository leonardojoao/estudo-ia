import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 8000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error)) {
      const detail = error.response?.data?.detail
      const message =
        typeof detail === 'string' ? detail : 'Não foi possível concluir a solicitação.'
      return Promise.reject(new Error(message))
    }
    return Promise.reject(error)
  },
)
