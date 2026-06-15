import {Navigate} from "react-router-dom"
import {useAuth} from "../hooks/useAuth.js"

export default function PublicOnlyRoute({children}) {
  const {isAuthenticated, isAuthResolved} = useAuth()

  if (!isAuthResolved) {
    return null
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace/>
  }

  return children
}
