import {useEffect, useMemo, useState} from "react"
import {useLocation, useNavigate} from "react-router-dom"
import {BreadcrumbGroup} from "@cloudscape-design/components"
import {getPatient} from "../services/patientApi.js"
import {getResponseData} from "../services/apiMessages.js"
import {formatPatientFullName} from "../utils/patients.js"

const ROUTE_LABELS = {
  "/dashboard": "Dashboard",
  "/patients/new": "Add Patient",
  "/alerts": "Alerts",
  "/profile": "My Profile",
  "/how-it-works": "How it works",
  "/metrics/streaming": "Live Monitoring",
  "/metrics/batch": "Batch Analytics",
  "/metrics/comparison": "Streaming vs Batch",
}

const DASHBOARD_BREADCRUMB = {text: "Dashboard", href: "/dashboard"}

function getPatientIdFromPathname(pathname) {
  return pathname.match(/^\/patients\/(\d+)\/(?:diagnosis|clinical-records|admission-history|analysis|post-discharge-summary)$/)?.[1]
    || pathname.match(/^\/patient\/(\d+)$/)?.[1]
    || null
}

function getSourceSearch(searchParams, sourceKey = "from") {
  const source = searchParams.get(sourceKey)
  const params = new URLSearchParams()

  if (source) {
    params.set("from", source)
  }

  const department = searchParams.get("department")
  if (department) {
    params.set("department", department)
  }

  const value = params.toString()
  return value ? `?${value}` : ""
}

function getPatientSourceBreadcrumb(searchParams, sourceKey = "from") {
  const source = searchParams.get(sourceKey)

  if (source === "department") {
    const department = searchParams.get("department") || ""
    return {
      text: department ? `Department: ${department}` : "Departments",
      href: department ? `/departments/${encodeURIComponent(department)}` : "/departments",
    }
  }

  if (source === "departments") {
    return {text: "Departments", href: "/departments"}
  }

  if (source === "alerts") {
    return {text: "Alerts", href: "/alerts"}
  }

  if (source === "profile") {
    return {text: "My Profile", href: "/profile"}
  }

  return null
}

function getPatientSourceBreadcrumbs(searchParams, sourceKey = "from") {
  const sourceBreadcrumb = getPatientSourceBreadcrumb(searchParams, sourceKey)
  return sourceBreadcrumb ? [DASHBOARD_BREADCRUMB, sourceBreadcrumb] : [DASHBOARD_BREADCRUMB]
}

function buildAlertsBreadcrumbItems(searchParams) {
  const source = searchParams.get("from")
  const patientName = searchParams.get("patient") || ""
  const sourcePatientId = searchParams.get("sourcePatientId")
  const scopedCnp = searchParams.get("cnp") || ""

  if (source === "patient" && patientName && scopedCnp) {
    const patientSourceBreadcrumbs = getPatientSourceBreadcrumbs(searchParams, "patientFrom")
    const patientSourceSearch = getSourceSearch(searchParams, "patientFrom")

    return [
      ...patientSourceBreadcrumbs,
      {
        text: `Patient: ${patientName}`,
        href: sourcePatientId ? `/patient/${sourcePatientId}${patientSourceSearch}` : undefined,
      },
      {text: `Alerts: ${patientName}`, href: "/alerts"},
    ]
  }

  return [
    DASHBOARD_BREADCRUMB,
    {text: "Alerts", href: "/alerts"},
  ]
}

function buildBreadcrumbItems(pathname, patientName, searchParams) {
  if (pathname === "/dashboard") {
    return [DASHBOARD_BREADCRUMB]
  }

  if (pathname === "/alerts") {
    return buildAlertsBreadcrumbItems(searchParams)
  }

  if (pathname === "/departments") {
    return [
      DASHBOARD_BREADCRUMB,
      {text: "Departments", href: "/departments"},
    ]
  }

  if (pathname.startsWith("/departments/")) {
    const department = decodeURIComponent(pathname.replace("/departments/", ""))
    return [
      DASHBOARD_BREADCRUMB,
      {text: `Department: ${department}`, href: pathname},
    ]
  }

  if (pathname.startsWith("/metrics/")) {
    return [
      DASHBOARD_BREADCRUMB,
      {text: ROUTE_LABELS[pathname] || "Metrics", href: pathname},
    ]
  }

  const patientSectionMatch = pathname.match(/^\/patients\/(\d+)\/(diagnosis|clinical-records|admission-history|analysis|post-discharge-summary)$/)
  if (patientSectionMatch) {
    const [, patientId, section] = patientSectionMatch
    const patientLabel = patientName ? `Patient: ${patientName}` : "Patient"
    const sourceSearch = getSourceSearch(searchParams)
    const sourceBreadcrumbs = getPatientSourceBreadcrumbs(searchParams)
    const sectionLabel = {
      diagnosis: "Clinical Records",
      "clinical-records": "Clinical Records",
      "admission-history": "Admission History",
      analysis: "Treatment Analysis",
      "post-discharge-summary": "Post-Discharge Clinical Summary",
    }[section]

    if (section === "post-discharge-summary") {
      return [
        ...sourceBreadcrumbs,
        {text: patientLabel, href: `/patient/${patientId}${sourceSearch}`},
        {text: "Treatment Analysis", href: `/patients/${patientId}/analysis${sourceSearch}`},
        {text: sectionLabel, href: pathname},
      ]
    }

    return [
      ...sourceBreadcrumbs,
      {text: patientLabel, href: `/patient/${patientId}${sourceSearch}`},
      {text: sectionLabel, href: pathname},
    ]
  }

  const patientMatch = pathname.match(/^\/patient\/(\d+)$/)
  if (patientMatch) {
    const patientLabel = patientName ? `Patient: ${patientName}` : "Patient"
    return [
      ...getPatientSourceBreadcrumbs(searchParams),
      {text: patientLabel, href: pathname},
    ]
  }

  return [
    DASHBOARD_BREADCRUMB,
    {text: ROUTE_LABELS[pathname] || "MedStream", href: pathname},
  ]
}

export default function AppBreadcrumbs({items}) {
  const location = useLocation()
  const navigate = useNavigate()
  const patientId = useMemo(() => getPatientIdFromPathname(location.pathname), [location.pathname])
  const [loadedPatientName, setLoadedPatientName] = useState({patientId: null, name: ""})

  useEffect(() => {
    if (!patientId || items) {
      return
    }

    let active = true

    const loadPatientName = async () => {
      try {
        const response = await getPatient(patientId)
        if (!active) {
          return
        }
        setLoadedPatientName({patientId, name: formatPatientFullName(getResponseData(response))})
      } catch {
        if (active) {
          setLoadedPatientName({patientId, name: ""})
        }
      }
    }

    loadPatientName()

    return () => {
      active = false
    }
  }, [items, patientId])

  const patientName = loadedPatientName.patientId === patientId ? loadedPatientName.name : ""

  const breadcrumbItems = useMemo(() => {
    const searchParams = new URLSearchParams(location.search)
    const sourceItems = items || buildBreadcrumbItems(location.pathname, patientName, searchParams)
    return sourceItems.map((item, index) => (
      index === sourceItems.length - 1 ? {...item, href: undefined} : item
    ))
  }, [items, location.pathname, location.search, patientName])

  return (
    <div className="medstream-breadcrumbs">
      <BreadcrumbGroup
        items={breadcrumbItems}
        ariaLabel="Breadcrumbs"
        onFollow={(event) => {
          event.preventDefault()
          const href = event.detail.href
          if (href) {
            navigate(href)
          }
        }}
      />
    </div>
  )
}
