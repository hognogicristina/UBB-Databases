import {useContext} from "react"
import {NotificationContext} from "../components/notificationContext.js"

export function useNotifications() {
  const context = useContext(NotificationContext)

  if (!context) {
    throw new Error("useNotifications must be used within a NotificationProvider")
  }

  return context
}
