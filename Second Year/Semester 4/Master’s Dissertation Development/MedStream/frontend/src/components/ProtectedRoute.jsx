import {Navigate} from "react-router-dom"
import {useAuth} from "../hooks/useAuth.js"
import LoadingSpinner from "./LoadingSpinner.jsx"

export default function ProtectedRoute({children}) {
  const {isAuthenticated, isAuthResolved, token} = useAuth()

  if (!isAuthResolved) {
    return <LoadingSpinner text="Loading..."/>
  }

  if (!token || !isAuthenticated) {
    return <Navigate to="/login" replace/>
  }

  return children
}
