import {Toggle} from "@cloudscape-design/components"
import {useTheme} from "../hooks/useTheme.js"

export default function AuthThemeToggle() {
  const {theme, setTheme} = useTheme()
  const isDarkMode = theme === "dark"

  return (
    <div className="auth-theme-toggle" aria-label="Theme selector">
      <Toggle
        checked={isDarkMode}
        onChange={({detail}) => setTheme(detail.checked ? "dark" : "light")}
      >
        Dark mode
      </Toggle>
    </div>
  )
}
