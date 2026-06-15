import {BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate} from "react-router-dom"
import {lazy, Suspense, useEffect} from "react"
import AuthenticatedLayout from "./components/AuthenticatedLayout.jsx"
import {useAuth} from "./hooks/useAuth.js"
import ProtectedRoute from "./components/ProtectedRoute.jsx"
import PublicOnlyRoute from "./components/PublicOnlyRoute.jsx"
import LoadingSpinner from "./components/LoadingSpinner.jsx"
import {registerAuthFailureHandler} from "./services/api.js"
import {getPatient} from "./services/patientApi.js"
import {getResponseData} from "./services/apiMessages.js"
import {formatPatientFullName} from "./utils/patients.js"

const AddPatientPage = lazy(() => import("./pages/AddPatientPage.jsx"))
const AlertsPage = lazy(() => import("./pages/AlertsPage.jsx"))
const BatchMetricsPage = lazy(() => import("./pages/BatchMetricsPage.jsx"))
const DepartmentPage = lazy(() => import("./pages/DepartmentPage.jsx"))
const DashboardPage = lazy(() => import("./pages/DashboardPage.jsx"))
const ForgotPasswordPage = lazy(() => import("./pages/ForgotPasswordPage.jsx"))
const HowItWorksPage = lazy(() => import("./pages/HowItWorksPage.jsx"))
const LoginPage = lazy(() => import("./pages/LoginPage.jsx"))
const PatientPage = lazy(() => import("./pages/PatientPage.jsx"))
const PatientDiagnosisPage = lazy(() => import("./pages/PatientDiagnosisPage.jsx"))
const PatientAdmissionHistoryPage = lazy(() => import("./pages/PatientAdmissionHistoryPage.jsx"))
const PatientClinicalRecordsPage = lazy(() => import("./pages/PatientClinicalRecordsPage.jsx"))
const PatientPostDischargeSummaryPage = lazy(() => import("./pages/PatientPostDischargeSummaryPage.jsx"))
const PatientTreatmentAnalysisPage = lazy(() => import("./pages/PatientTreatmentAnalysisPage.jsx"))
const ProfilePage = lazy(() => import("./pages/ProfilePage.jsx"))
const RecoverAccountPage = lazy(() => import("./pages/RecoverAccountPage.jsx"))
const RecoverAccountVerifyPage = lazy(() => import("./pages/RecoverAccountVerifyPage.jsx"))
const RegisterPage = lazy(() => import("./pages/RegisterPage.jsx"))
const ResetPasswordPage = lazy(() => import("./pages/ResetPasswordPage.jsx"))
const StreamingMetricsPage = lazy(() => import("./pages/StreamingMetricsPage.jsx"))
const StreamingBatchPage = lazy(() => import("./pages/StreamingBatchPage.jsx"))
const VerifyEmailPage = lazy(() => import("./pages/VerifyEmailPage.jsx"))

function RootRoute() {
  const {isAuthenticated, isAuthResolved} = useAuth()

  if (!isAuthResolved) {
    return <LoadingSpinner/>
  }

  return <Navigate to={isAuthenticated ? "/dashboard" : "/login"} replace/>
}

function ApiAuthBridge() {
  const navigate = useNavigate()
  const location = useLocation()
  const {logout} = useAuth()
  const isAuthRoute = [
    "/login",
    "/register",
    "/forgot-password",
    "/reset-password",
    "/verify-email",
    "/recover-account",
    "/recover-account/verify",
  ].includes(location.pathname)

  useEffect(() => {
    registerAuthFailureHandler(() => {
      logout()
      if (!isAuthRoute) {
        navigate("/login", {replace: true})
      }
    })

    return () => {
      registerAuthFailureHandler(null)
    }
  }, [isAuthRoute, logout, navigate])

  return null
}

function resolveStaticTitle(pathname) {
  if (pathname === "/dashboard") {
    return "Dashboard"
  }
  if (pathname === "/metrics/streaming") {
    return "Streaming Monitoring"
  }
  if (pathname === "/metrics/batch") {
    return "Batch Analytics"
  }
  if (pathname === "/metrics/comparison") {
    return "Streaming vs Batch"
  }
  if (pathname === "/how-it-works") {
    return "How it works"
  }
  if (pathname === "/login") {
    return "Login"
  }
  if (pathname === "/register") {
    return "Register"
  }
  if (pathname === "/forgot-password" || pathname === "/recover-account") {
    return "Recover Account"
  }
  if (pathname === "/reset-password") {
    return "Reset Password"
  }
  if (pathname === "/verify-email" || pathname === "/recover-account/verify") {
    return "Verify Email"
  }
  if (pathname === "/profile") {
    return "My Profile"
  }
  if (pathname === "/alerts") {
    return "Alerting System"
  }
  if (pathname === "/departments") {
    return "All Departments"
  }
  if (pathname.startsWith("/departments/")) {
    return "Departments"
  }
  return "MedStream"
}

function useDocumentTitle() {
  const location = useLocation()

  useEffect(() => {
    let active = true
    const {pathname} = location
    const staticTitle = resolveStaticTitle(pathname)
    document.title = staticTitle

    const match = pathname.match(/^\/patients\/(\d+)\/(diagnosis|clinical-records|admission-history|analysis|post-discharge-summary)$/)
      || pathname.match(/^\/patient\/(\d+)$/)

    if (!match) {
      return () => {
        active = false
      }
    }

    const patientId = match[1]
    const section = match[2] || ""
    const sectionTitle = section === "diagnosis"
      ? "Clinical Records"
      : section === "clinical-records"
        ? "Clinical Records"
        : section === "admission-history"
          ? "Admission History"
          : section === "analysis"
            ? "Treatment Analysis"
            : section === "post-discharge-summary"
              ? "Post-Discharge Clinical Summary"
              : ""

    const fallbackPatientTitle = sectionTitle ? `Patient ID: ${patientId} - ${sectionTitle}` : `Patient ID: ${patientId}`
    document.title = fallbackPatientTitle

    const setPatientTitle = async () => {
      try {
        const response = await getPatient(patientId)
        if (!active) {
          return
        }
        const patientName = formatPatientFullName(getResponseData(response))
        document.title = sectionTitle ? `Patient: ${patientName} - ${sectionTitle}` : `Patient: ${patientName}`
      } catch (error) {
        void error
      }
    }

    setPatientTitle()

    return () => {
      active = false
    }
  }, [location])
}

function TitleManager() {
  useDocumentTitle()
  return null
}

function App() {
  return (
    <BrowserRouter>
      <TitleManager/>
      <ApiAuthBridge/>
      <Suspense fallback={<LoadingSpinner/>}>
        <Routes>
          <Route path="/" element={<RootRoute/>}/>

          <Route
            path="/login"
            element={
              <PublicOnlyRoute>
                <LoginPage/>
              </PublicOnlyRoute>
            }
          />

          <Route
            path="/register"
            element={
              <PublicOnlyRoute>
                <RegisterPage/>
              </PublicOnlyRoute>
            }
          />

          <Route
            path="/forgot-password"
            element={
              <PublicOnlyRoute>
                <ForgotPasswordPage/>
              </PublicOnlyRoute>
            }
          />

          <Route
            path="/reset-password"
            element={
              <PublicOnlyRoute>
                <ResetPasswordPage/>
              </PublicOnlyRoute>
            }
          />

          <Route
            path="/verify-email"
            element={<VerifyEmailPage/>}
          />

          <Route
            path="/recover-account"
            element={
              <PublicOnlyRoute>
                <RecoverAccountPage/>
              </PublicOnlyRoute>
            }
          />

          <Route
            path="/recover-account/verify"
            element={<RecoverAccountVerifyPage/>}
          />

          <Route
            element={
              <ProtectedRoute>
                <AuthenticatedLayout/>
              </ProtectedRoute>
            }
          >
            <Route path="/dashboard" element={<DashboardPage/>}/>
            <Route path="/departments" element={<DepartmentPage/>}/>
            <Route path="/departments/:name" element={<DepartmentPage/>}/>
            <Route path="/patient/:id" element={<PatientPage/>}/>
            <Route path="/patients/:id/diagnosis" element={<PatientDiagnosisPage/>}/>
            <Route path="/patients/:id/clinical-records" element={<PatientClinicalRecordsPage/>}/>
            <Route path="/patients/:id/admission-history" element={<PatientAdmissionHistoryPage/>}/>
            <Route path="/patients/:id/analysis" element={<PatientTreatmentAnalysisPage/>}/>
            <Route path="/patients/:id/post-discharge-summary" element={<PatientPostDischargeSummaryPage/>}/>
            <Route path="/alerts" element={<AlertsPage/>}/>
            <Route path="/metrics/streaming" element={<StreamingMetricsPage/>}/>
            <Route path="/metrics/batch" element={<BatchMetricsPage/>}/>
            <Route path="/metrics/comparison" element={<StreamingBatchPage/>}/>
            <Route path="/how-it-works" element={<HowItWorksPage/>}/>
            <Route path="/patients/new" element={<AddPatientPage/>}/>
            <Route path="/profile" element={<ProfilePage/>}/>
          </Route>
          <Route path="*" element={<RootRoute/>}/>
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}

export default App
