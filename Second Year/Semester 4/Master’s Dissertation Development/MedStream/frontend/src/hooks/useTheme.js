import {useContext} from "react"
import {ThemeContext} from "../components/themeContext.js"

export function useTheme() {
  return useContext(ThemeContext)
}
