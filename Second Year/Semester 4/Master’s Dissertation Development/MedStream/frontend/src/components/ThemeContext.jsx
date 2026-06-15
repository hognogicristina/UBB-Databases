import {useEffect, useMemo, useState} from "react"
import {applyMode, Mode} from "@cloudscape-design/global-styles"
import {DEFAULT_THEME, ThemeContext} from "./themeContext.js"

const THEME_STORAGE_KEY = "medstream-theme"

function normalizeTheme(value) {
  return value === "light" ? "light" : "dark"
}

export function ThemeProvider({children}) {
  const [theme, setThemeState] = useState(() => {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY)
    return normalizeTheme(stored)
  })

  useEffect(() => {
    const normalizedTheme = normalizeTheme(theme)
    document.documentElement.setAttribute("data-theme", normalizedTheme)
    document.documentElement.classList.toggle("theme-light", normalizedTheme === "light")
    document.documentElement.classList.toggle("theme-dark", normalizedTheme === "dark")
    applyMode(normalizedTheme === "light" ? Mode.Light : Mode.Dark)
    window.localStorage.setItem(THEME_STORAGE_KEY, normalizedTheme)

    const metaTheme = document.querySelector('meta[name="theme-color"]')
    if (metaTheme) {
      metaTheme.setAttribute("content", normalizedTheme === "light" ? "#F7F8FA" : "#16191f")
    }
  }, [theme])

  const setTheme = (nextTheme) => {
    setThemeState(normalizeTheme(nextTheme))
  }

  const toggleTheme = () => {
    setThemeState((currentTheme) => currentTheme === "dark" ? "light" : "dark")
  }

  const value = useMemo(() => ({
    theme,
    setTheme,
    toggleTheme,
  }), [theme])

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  )
}
