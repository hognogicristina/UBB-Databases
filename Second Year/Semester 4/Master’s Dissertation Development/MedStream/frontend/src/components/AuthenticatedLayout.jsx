import {Outlet, useLocation} from "react-router-dom"
import {useCallback, useEffect, useMemo, useState} from "react"
import {AppIconRail, AppSideNavigation, AppTopNavigation} from "./Navbar.jsx"
import {useAuth} from "../hooks/useAuth.js"
import {resendVerificationEmail} from "../services/authApi.js"
import {getErrorMessage, getResponseMessage} from "../services/apiMessages.js"
import {useNotifications} from "../hooks/useNotifications.js"

const EMAIL_NOT_VERIFIED_WARNING = "Your email is not verified. Please verify your email."
const EMAIL_NOT_VERIFIED_WARNING_KEY = "email-not-verified-warning"
const EMAIL_WARNING_INTERVAL_MS = 15000
const EMAIL_WARNING_DURATION_MS = 5000
const EMAIL_STATUS_REFRESH_MS = 30000

export default function AuthenticatedLayout() {
  const location = useLocation()
  const {currentDoctor: doctor, refreshCurrentDoctor, token} = useAuth()
  const {dismissNotificationByDedupeKey, notifyError, notifySuccess, notifyWarning} = useNotifications()
  const [isResending, setIsResending] = useState(false)
  const [navigationOpen, setNavigationOpen] = useState(true)

  const authHeaders = useMemo(() => token ? {Authorization: `Bearer ${token}`} : undefined, [token])
  const currentDoctorId = doctor?.id
  const isEmailConfirmed = doctor?.email_confirmed

  useEffect(() => {
    if (!authHeaders) {
      return
    }

    const loadDoctor = async () => {
      try {
        await refreshCurrentDoctor()
      } catch (error) {
        void error
      }
    }

    loadDoctor()
  }, [authHeaders, location.pathname, refreshCurrentDoctor])

  useEffect(() => {
    if (!authHeaders || !currentDoctorId || isEmailConfirmed) {
      return
    }

    const refreshId = window.setInterval(async () => {
      try {
        await refreshCurrentDoctor()
      } catch (error) {
        void error
      }
    }, EMAIL_STATUS_REFRESH_MS)

    return () => {
      window.clearInterval(refreshId)
    }
  }, [authHeaders, currentDoctorId, isEmailConfirmed, refreshCurrentDoctor])

  useEffect(() => {
    if (!authHeaders || !currentDoctorId || isEmailConfirmed) {
      return
    }

    const refreshEmailStatus = () => {
      refreshCurrentDoctor().catch(() => {})
    }
    const refreshWhenVisible = () => {
      if (document.visibilityState === "visible") {
        refreshEmailStatus()
      }
    }

    window.addEventListener("focus", refreshEmailStatus)
    document.addEventListener("visibilitychange", refreshWhenVisible)

    return () => {
      window.removeEventListener("focus", refreshEmailStatus)
      document.removeEventListener("visibilitychange", refreshWhenVisible)
    }
  }, [authHeaders, currentDoctorId, isEmailConfirmed, refreshCurrentDoctor])

  useEffect(() => {
    if (isEmailConfirmed) {
      dismissNotificationByDedupeKey(EMAIL_NOT_VERIFIED_WARNING_KEY)
    }
  }, [dismissNotificationByDedupeKey, isEmailConfirmed])

  const showResend = Boolean(doctor?.email_confirmed === false && doctor?.email_verification_expired)

  const handleResend = useCallback(async () => {
    if (!authHeaders || isResending || !showResend) {
      return
    }

    setIsResending(true)
    try {
      const response = await resendVerificationEmail({headers: authHeaders})
      notifySuccess(getResponseMessage(response))
      await refreshCurrentDoctor()
    } catch (error) {
      notifyError(getErrorMessage(error))
    } finally {
      setIsResending(false)
    }
  }, [authHeaders, isResending, notifyError, notifySuccess, refreshCurrentDoctor, showResend])

  useEffect(() => {
    if (!doctor || doctor.email_confirmed) {
      return
    }

    const intervalId = window.setInterval(() => {
      notifyWarning(EMAIL_NOT_VERIFIED_WARNING, {
        duration: EMAIL_WARNING_DURATION_MS,
        dedupeKey: EMAIL_NOT_VERIFIED_WARNING_KEY,
        actionLabel: showResend ? (isResending ? "Sending..." : "Resend email") : "",
        onAction: showResend && !isResending ? handleResend : null,
      })
    }, EMAIL_WARNING_INTERVAL_MS)

    return () => {
      window.clearInterval(intervalId)
    }
  }, [doctor, handleResend, isResending, notifyWarning, showResend])

  return (
    <div className="medstream-shell">
      <div id="top-nav">
        <AppTopNavigation/>
      </div>
      <div className={`medstream-main-frame${navigationOpen ? "" : " medstream-main-frame-collapsed"}`}>
        {navigationOpen ? (
          <aside className="medstream-sidebar">
            <AppSideNavigation onCollapse={() => setNavigationOpen(false)}/>
          </aside>
        ) : (
          <aside className="medstream-sidebar medstream-sidebar-collapsed">
            <AppIconRail onOpen={() => setNavigationOpen(true)}/>
          </aside>
        )}
        <main className="medstream-content-inner">
          <Outlet/>
        </main>
      </div>
    </div>
  )
}
