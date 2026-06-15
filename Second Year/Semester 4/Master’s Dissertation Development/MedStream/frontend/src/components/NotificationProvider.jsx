import {useCallback, useEffect, useMemo, useRef, useState} from "react"
import {NotificationContext} from "./notificationContext.js"

const DEFAULT_NOTIFICATION_DURATION = 5000
const MAX_NOTIFICATIONS = 4

function resolveDurationOptions(durationOrOptions) {
  if (typeof durationOrOptions === "number") {
    return {duration: durationOrOptions}
  }
  if (durationOrOptions && typeof durationOrOptions === "object") {
    return durationOrOptions
  }
  return {}
}

export function NotificationProvider({children}) {
  const [notifications, setNotifications] = useState([])
  const notificationsRef = useRef([])
  const timeoutIdsRef = useRef(new Map())
  const nextIdRef = useRef(0)

  useEffect(() => {
    notificationsRef.current = notifications
  }, [notifications])

  useEffect(() => () => {
    timeoutIdsRef.current.forEach((timeoutId) => window.clearTimeout(timeoutId))
    timeoutIdsRef.current.clear()
  }, [])

  const dismissNotification = useCallback((id) => {
    const timeoutId = timeoutIdsRef.current.get(id)

    if (timeoutId) {
      window.clearTimeout(timeoutId)
      timeoutIdsRef.current.delete(id)
    }

    setNotifications((current) => current.filter((notification) => notification.id !== id))
  }, [])

  const dismissNotificationByDedupeKey = useCallback((dedupeKey) => {
    if (!dedupeKey) {
      return
    }

    setNotifications((current) => current.filter((notification) => {
      if (notification.dedupeKey !== dedupeKey) {
        return true
      }

      const timeoutId = timeoutIdsRef.current.get(notification.id)
      if (timeoutId) {
        window.clearTimeout(timeoutId)
        timeoutIdsRef.current.delete(notification.id)
      }

      return false
    }))
  }, [])

  const showNotification = useCallback(({
                                          message,
                                          type = "success",
                                          duration = DEFAULT_NOTIFICATION_DURATION,
                                          actionLabel = "",
                                          onAction = null,
                                          dedupeKey = "",
                                        }) => {
    if (!message) {
      return
    }

    const nextDedupeKey = dedupeKey || `${type}:${message}`
    const existingNotification = notificationsRef.current.find((notification) => notification.dedupeKey === nextDedupeKey)

    if (existingNotification) {
      const existingTimeoutId = timeoutIdsRef.current.get(existingNotification.id)
      if (existingTimeoutId) {
        window.clearTimeout(existingTimeoutId)
        timeoutIdsRef.current.delete(existingNotification.id)
      }
    }

    const id = `notification-${nextIdRef.current += 1}`
    setNotifications((current) => {
      const filtered = current.filter((notification) => notification.dedupeKey !== nextDedupeKey)
      return [...filtered, {
        id,
        message,
        type,
        actionLabel,
        onAction,
        dedupeKey: nextDedupeKey,
      }].slice(-MAX_NOTIFICATIONS)
    })

    if (duration > 0) {
      const timeoutId = window.setTimeout(() => {
        dismissNotification(id)
      }, duration)

      timeoutIdsRef.current.set(id, timeoutId)
    }
  }, [dismissNotification])

  const contextValue = useMemo(() => ({
    notify: showNotification,
    notifySuccess(message, options) {
      showNotification({message, type: "success", ...resolveDurationOptions(options), duration: 5000})
    },
    notifyError(message, options) {
      showNotification({message, type: "error", ...resolveDurationOptions(options), duration: 5000})
    },
    notifyWarning(message, options = {}) {
      showNotification({message, type: "warning", ...resolveDurationOptions(options), duration: 5000})
    },
    dismissNotification,
    dismissNotificationByDedupeKey,
  }), [dismissNotification, dismissNotificationByDedupeKey, showNotification])

  return (
    <NotificationContext.Provider value={contextValue}>
      {children}
      <div className="notification-stack" aria-live="polite" aria-atomic="true">
        {notifications.map((notification) => (
          <div
            key={notification.id}
            className={`notification-toast notification-toast-${notification.type}`}
            role="status"
          >
            <div>
              <p className="notification-toast-label">
                {notification.type === "error" ? "Error" : notification.type === "warning" ? "Warning" : "Success"}
              </p>
              <p className="notification-toast-message">{notification.message}</p>
              {notification.actionLabel && typeof notification.onAction === "function" && (
                <button
                  type="button"
                  className="notification-toast-action-link"
                  onClick={notification.onAction}
                >
                  {notification.actionLabel}
                </button>
              )}
            </div>
            <button
              type="button"
              onClick={() => dismissNotification(notification.id)}
              className="notification-toast-dismiss"
              aria-label="Dismiss notification"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </NotificationContext.Provider>
  )
}
