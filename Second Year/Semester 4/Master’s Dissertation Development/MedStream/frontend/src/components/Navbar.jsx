import {useEffect, useMemo, useRef, useState} from "react"
import {useLocation, useNavigate} from "react-router-dom"
import {
  Button,
  ButtonDropdown,
  SideNavigation,
  TopNavigation,
} from "@cloudscape-design/components"
import {useAuth} from "../hooks/useAuth.js"
import {useTheme} from "../hooks/useTheme.js"
import {getResponseData} from "../services/apiMessages.js"
import {getDepartments} from "../services/patientApi.js"

function resolveActiveHref(pathname, search = "") {
  if (pathname === "/departments") {
    return "/departments"
  }
  if (pathname.startsWith("/departments/")) {
    return pathname
  }
  if (pathname.startsWith("/metrics/streaming")) {
    return "/metrics/streaming"
  }
  if (pathname.startsWith("/metrics/batch")) {
    return "/metrics/batch"
  }
  if (pathname.startsWith("/metrics/comparison")) {
    return "/metrics/comparison"
  }
  if (pathname.startsWith("/alerts")) {
    return "/alerts"
  }
  if (pathname.startsWith("/how-it-works")) {
    return "/how-it-works"
  }
  if (pathname.startsWith("/patients/new")) {
    return "/patients/new"
  }
  if (pathname.startsWith("/patient/") || pathname.startsWith("/patients/")) {
    const params = new URLSearchParams(search)
    const source = params.get("from")
    const department = params.get("department")

    if (source === "department" && department) {
      return `/departments/${encodeURIComponent(department)}`
    }
    if (source === "departments") {
      return "/departments"
    }
  }
  return "/dashboard"
}

const METRIC_RAIL_ITEMS = [
  {id: "/metrics/streaming", text: "Live Monitoring"},
  {id: "/metrics/batch", text: "Batch Analytics"},
  {id: "/metrics/comparison", text: "Streaming vs Batch"},
]

function VitalsHeartIcon() {
  return (
    <svg focusable="false" viewBox="0 0 16 16">
      <path d="M8 14s-5.5-3.3-5.5-7.2A3.1 3.1 0 0 1 8 4.9a3.1 3.1 0 0 1 5.5 1.9C13.5 10.7 8 14 8 14Z"/>
      <path d="M3.9 8h1.7l.8-1.8L8 10.2l1.2-2.6.7.4h2.2"/>
    </svg>
  )
}

function MetricsLinesIcon() {
  return (
    <svg focusable="false" viewBox="0 0 16 16">
      <path d="M1 14h14"/>
      <path d="M3 10.5 6.1 7.4l2.5 2.2L13 4"/>
      <path d="M3 5h2M3 8h1.2M3 2h3"/>
    </svg>
  )
}

function FolderIcon() {
  return (
    <svg focusable="false" viewBox="0 0 16 16">
      <path d="M1.8 4.2h4.5l1.2 1.5h6.7v6.7a1.4 1.4 0 0 1-1.4 1.4H3.2a1.4 1.4 0 0 1-1.4-1.4V4.2Z"/>
      <path d="M1.8 4.2V3.6a1.4 1.4 0 0 1 1.4-1.4h3l1.3 1.5h5.3a1.4 1.4 0 0 1 1.4 1.4v.6"/>
    </svg>
  )
}

function DropdownArrowIcon({direction}) {
  return <span className={`medstream-rail-caret medstream-rail-caret-${direction}`} aria-hidden="true"/>
}

function RailDropdownIcon({isActive, isOpen, fallbackIcon}) {
  if (isActive || isOpen) {
    return <DropdownArrowIcon direction={isOpen ? "up" : "down"}/>
  }

  return fallbackIcon
}

function useButtonDropdownOpenState() {
  const rootRef = useRef(null)
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    const root = rootRef.current
    if (!root) {
      return undefined
    }

    const syncOpenState = () => {
      const trigger = root.querySelector("button[aria-haspopup='true']")
      setIsOpen(trigger?.getAttribute("aria-expanded") === "true")
    }

    syncOpenState()

    const observer = new MutationObserver(syncOpenState)
    observer.observe(root, {
      attributes: true,
      attributeFilter: ["aria-expanded"],
      childList: true,
      subtree: true,
    })

    return () => {
      observer.disconnect()
    }
  }, [])

  return [rootRef, isOpen]
}

function createNavigationItems(departments) {
  return [
    {type: "link", text: "Dashboard", href: "/dashboard"},
    {
      type: "section",
      text: "Departments",
      defaultExpanded: false,
      items: [
        {type: "link", text: "All departments", href: "/departments"},
        ...departments.map((department) => ({
          type: "link",
          text: department,
          href: `/departments/${encodeURIComponent(department)}`,
        })),
      ],
    },
    {type: "link", text: "Add Patient", href: "/patients/new"},
    {type: "link", text: "Alerts", href: "/alerts"},
    {
      type: "section",
      text: "Metrics",
      defaultExpanded: false,
      items: [
        {type: "link", text: "Live Monitoring", href: "/metrics/streaming"},
        {type: "link", text: "Batch Analytics", href: "/metrics/batch"},
        {type: "link", text: "Streaming vs Batch", href: "/metrics/comparison"},
      ],
    },
    {type: "link", text: "How it works", href: "/how-it-works"},
  ]
}

export function AppTopNavigation() {
  const navigate = useNavigate()
  const {logout} = useAuth()
  const {theme, toggleTheme} = useTheme()
  const accountMenuRef = useRef(null)
  const [isAccountMenuOpen, setIsAccountMenuOpen] = useState(false)

  useEffect(() => {
    if (!isAccountMenuOpen) {
      return undefined
    }

    const handleDocumentClick = (event) => {
      if (!accountMenuRef.current?.contains(event.target)) {
        setIsAccountMenuOpen(false)
      }
    }

    const handleDocumentKeyDown = (event) => {
      if (event.key === "Escape") {
        setIsAccountMenuOpen(false)
      }
    }

    document.addEventListener("mousedown", handleDocumentClick)
    document.addEventListener("keydown", handleDocumentKeyDown)

    return () => {
      document.removeEventListener("mousedown", handleDocumentClick)
      document.removeEventListener("keydown", handleDocumentKeyDown)
    }
  }, [isAccountMenuOpen])

  const handleAccountOption = (optionId) => {
    setIsAccountMenuOpen(false)

    if (optionId === "profile") {
      navigate("/profile")
    }
    if (optionId === "logout") {
      logout()
      navigate("/")
    }
  }

  return (
    <>
      <TopNavigation
        identity={{
          href: "/dashboard",
          title: "MedStream",
          logo: {src: "/medstream-icon-small.svg", alt: "MedStream"},
        }}
        utilities={[]}
        i18nStrings={{
          searchIconAriaLabel: "Search",
          searchDismissIconAriaLabel: "Close search",
          overflowMenuTriggerText: "More",
          overflowMenuTitleText: "All",
        }}
      />
      <div className="medstream-top-actions">
        <button className="medstream-top-action-button" onClick={toggleTheme} type="button">
          {theme === "light" ? "Dark mode" : "Light mode"}
        </button>
        <div ref={accountMenuRef} className="medstream-account-selector">
          <button
            aria-expanded={isAccountMenuOpen}
            aria-haspopup="menu"
            className="medstream-account-trigger"
            onClick={() => setIsAccountMenuOpen((current) => !current)}
            type="button"
          >
            <span>Account</span>
            <span className={`medstream-account-trigger-caret${isAccountMenuOpen ? " medstream-account-trigger-caret-open" : ""}`} aria-hidden="true"/>
          </button>
          {isAccountMenuOpen && (
            <div className="medstream-account-options" role="menu" aria-label="Account options">
              <button className="medstream-account-option" onClick={() => handleAccountOption("profile")} role="menuitem" type="button">
                <span className="medstream-account-option-text">My Profile</span>
              </button>
              <button className="medstream-account-option" onClick={() => handleAccountOption("logout")} role="menuitem" type="button">
                <span className="medstream-account-option-text">Sign out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  )
}

export function AppSideNavigation({onCollapse}) {
  const navigate = useNavigate()
  const location = useLocation()
  const [departments, setDepartments] = useState([])

  const activeHref = useMemo(() => resolveActiveHref(location.pathname, location.search), [location.pathname, location.search])
  const navItems = useMemo(() => createNavigationItems(departments), [departments])

  useEffect(() => {
    let active = true

    const loadDepartments = async () => {
      try {
        const response = await getDepartments()
        if (!active) {
          return
        }
        const data = getResponseData(response)
        setDepartments(Array.isArray(data) ? data : [])
      } catch (error) {
        void error
      }
    }

    loadDepartments()

    return () => {
      active = false
    }
  }, [])

  return (
    <div className="medstream-sidebar-panel">
      <div className="medstream-sidebar-header">
        <span className="medstream-sidebar-title">Navigation</span>
        <Button iconName="angle-left" variant="icon" ariaLabel="Collapse navigation" onClick={onCollapse}/>
      </div>
      <SideNavigation
        activeHref={activeHref}
        items={navItems}
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

export function AppIconRail({onOpen}) {
  const navigate = useNavigate()
  const location = useLocation()
  const [departments, setDepartments] = useState([])
  const [departmentsDropdownRef, isDepartmentsDropdownOpen] = useButtonDropdownOpenState()
  const [metricsDropdownRef, isMetricsDropdownOpen] = useButtonDropdownOpenState()
  const activeHref = useMemo(() => resolveActiveHref(location.pathname, location.search), [location.pathname, location.search])
  const isDepartmentsActive = activeHref.startsWith("/departments")
  const isMetricsActive = activeHref.startsWith("/metrics/")
  const departmentItems = useMemo(() => [
    {id: "/departments", text: "All departments"},
    ...departments.map((department) => ({
      id: `/departments/${encodeURIComponent(department)}`,
      text: department,
    })),
  ], [departments])

  useEffect(() => {
    let active = true

    const loadDepartments = async () => {
      try {
        const response = await getDepartments()
        if (!active) {
          return
        }
        const data = getResponseData(response)
        setDepartments(Array.isArray(data) ? data : [])
      } catch (error) {
        void error
      }
    }

    loadDepartments()

    return () => {
      active = false
    }
  }, [])

  return (
    <div className="medstream-icon-rail">
      <Button
        className="medstream-rail-button"
        variant="icon"
        iconName="angle-right"
        ariaLabel="Open navigation"
        onClick={onOpen}
      />
      <Button
        className={`medstream-rail-button${activeHref === "/dashboard" ? " medstream-rail-button-active" : ""}`}
        variant="icon"
        iconSvg={<VitalsHeartIcon/>}
        ariaLabel="Dashboard"
        onClick={() => navigate("/dashboard")}
      />
      <div ref={departmentsDropdownRef} className="medstream-rail-dropdown-wrapper">
        <ButtonDropdown
          className={`medstream-rail-dropdown${isDepartmentsActive ? " medstream-rail-dropdown-active" : ""}`}
          variant="normal"
          ariaLabel="Departments"
          expandToViewport
          items={departmentItems.length > 0 ? departmentItems : [{id: "empty", text: "No departments available", disabled: true}]}
          onItemClick={({detail}) => {
            if (detail.id && detail.id !== "empty") {
              navigate(detail.id)
            }
          }}
        >
          <span className="medstream-rail-dropdown-icon" aria-hidden="true">
            <RailDropdownIcon
              isActive={isDepartmentsActive}
              isOpen={isDepartmentsDropdownOpen}
              fallbackIcon={<FolderIcon/>}
            />
          </span>
        </ButtonDropdown>
      </div>
      <Button
        className={`medstream-rail-button${activeHref === "/patients/new" ? " medstream-rail-button-active" : ""}`}
        variant="icon"
        iconName="user-profile"
        ariaLabel="Add Patient"
        onClick={() => navigate("/patients/new")}
      />
      <Button
        className={`medstream-rail-button${activeHref === "/alerts" ? " medstream-rail-button-active" : ""}`}
        variant="icon"
        iconName="notification"
        ariaLabel="Alerts"
        onClick={() => navigate("/alerts")}
      />
      <div ref={metricsDropdownRef} className="medstream-rail-dropdown-wrapper">
        <ButtonDropdown
          className={`medstream-rail-dropdown${isMetricsActive ? " medstream-rail-dropdown-active" : ""}`}
          variant="normal"
          ariaLabel="Metrics"
          expandToViewport
          items={METRIC_RAIL_ITEMS}
          onItemClick={({detail}) => {
            if (detail.id) {
              navigate(detail.id)
            }
          }}
        >
          <span className="medstream-rail-dropdown-icon" aria-hidden="true">
            <RailDropdownIcon
              isActive={isMetricsActive}
              isOpen={isMetricsDropdownOpen}
              fallbackIcon={<MetricsLinesIcon/>}
            />
          </span>
        </ButtonDropdown>
      </div>
      <Button
        className={`medstream-rail-button${activeHref === "/how-it-works" ? " medstream-rail-button-active" : ""}`}
        variant="icon"
        iconName="status-info"
        ariaLabel="How it works"
        onClick={() => navigate("/how-it-works")}
      />
    </div>
  )
}
