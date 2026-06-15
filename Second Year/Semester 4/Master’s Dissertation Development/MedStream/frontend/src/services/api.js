import axios from "axios"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"

export const api = axios.create({
  baseURL: API_BASE_URL
})

let authFailureHandler = null
let isHandlingUnauthorized = false

export function registerAuthFailureHandler(handler) {
  authFailureHandler = typeof handler === "function" ? handler : null
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error?.response?.status
    if (status === 401 && authFailureHandler && !isHandlingUnauthorized) {
      isHandlingUnauthorized = true
      try {
        authFailureHandler()
      } finally {
        window.setTimeout(() => {
          isHandlingUnauthorized = false
        }, 0)
      }
    }

    return Promise.reject(error)
  },
)
