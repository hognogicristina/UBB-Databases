import {useCallback, useEffect, useMemo, useState} from "react"
import {getCurrentDoctor} from "../services/doctorApi.js"
import {getResponseData} from "../services/apiMessages.js"
import {subscribeToEmailVerified} from "../services/emailVerificationEvents.js"
import {AuthContext} from "./authContext.js"

const AUTH_STORAGE_KEY = "medstream_token"

function parseJwtExpMs(token) {
  if (!token) {
    return null
  }
  const parts = String(token).split(".")
  if (parts.length < 2) {
    return null
  }

  try {
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/")
    const payload = JSON.parse(window.atob(base64))
    const exp = Number(payload?.exp)
    if (!Number.isFinite(exp) || exp <= 0) {
      return null
    }
    return exp * 1000
  } catch {
    return null
  }
}

function isTokenExpired(token) {
  const expMs = parseJwtExpMs(token)
  if (!expMs) {
    return false
  }
  return Date.now() >= expMs
}

export function AuthProvider({children}) {
  const [token, setToken] = useState(() => {
    const storedToken = localStorage.getItem(AUTH_STORAGE_KEY)
    if (!storedToken) {
      return null
    }
    if (isTokenExpired(storedToken)) {
      localStorage.removeItem(AUTH_STORAGE_KEY)
      return null
    }
    return storedToken
  })
  const [isAuthResolved, setIsAuthResolved] = useState(() => !token)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [currentDoctor, setCurrentDoctor] = useState(null)

  const refreshCurrentDoctor = useCallback(async () => {
    if (!token) {
      setCurrentDoctor(null)
      setIsAuthenticated(false)
      setIsAuthResolved(true)
      return null
    }

    const response = await getCurrentDoctor({Authorization: `Bearer ${token}`})
    const doctorData = getResponseData(response)
    setCurrentDoctor(doctorData)
    setIsAuthenticated(true)
    setIsAuthResolved(true)
    return doctorData
  }, [token])

  const setCurrentDoctorData = useCallback((doctorData) => {
    setCurrentDoctor(doctorData)
  }, [])

  useEffect(() => {
    if (!token) {
      localStorage.removeItem(AUTH_STORAGE_KEY)
      return
    }

    localStorage.setItem(AUTH_STORAGE_KEY, token)
    let active = true

    const validateToken = async () => {
      try {
        const response = await getCurrentDoctor({Authorization: `Bearer ${token}`})
        const doctorData = getResponseData(response)
        if (!active) {
          return
        }
        setCurrentDoctor(doctorData)
        setIsAuthenticated(true)
        setIsAuthResolved(true)
      } catch {
        if (!active) {
          return
        }
        localStorage.removeItem(AUTH_STORAGE_KEY)
        setToken(null)
        setCurrentDoctor(null)
        setIsAuthenticated(false)
        setIsAuthResolved(true)
      }
    }

    validateToken()

    return () => {
      active = false
    }
  }, [token])

  useEffect(() => {
    if (!token) {
      return undefined
    }

    return subscribeToEmailVerified(() => {
      refreshCurrentDoctor().catch(() => {})
    })
  }, [refreshCurrentDoctor, token])

  const value = useMemo(
    () => ({
      token,
      currentDoctor,
      refreshCurrentDoctor,
      setCurrentDoctorData,
      isAuthenticated,
      isAuthResolved,
      login(nextToken) {
        if (isTokenExpired(nextToken)) {
          localStorage.removeItem(AUTH_STORAGE_KEY)
          setCurrentDoctor(null)
          setIsAuthenticated(false)
          setIsAuthResolved(true)
          setToken(null)
          return
        }
        setCurrentDoctor(null)
        setIsAuthenticated(false)
        setIsAuthResolved(false)
        setToken(nextToken)
      },
      logout() {
        localStorage.removeItem(AUTH_STORAGE_KEY)
        setCurrentDoctor(null)
        setIsAuthenticated(false)
        setIsAuthResolved(true)
        setToken(null)
      },
      clearToken() {
        localStorage.removeItem(AUTH_STORAGE_KEY)
        setCurrentDoctor(null)
        setIsAuthenticated(false)
        setIsAuthResolved(true)
        setToken(null)
      },
    }),
    [currentDoctor, isAuthenticated, isAuthResolved, refreshCurrentDoctor, setCurrentDoctorData, token],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
