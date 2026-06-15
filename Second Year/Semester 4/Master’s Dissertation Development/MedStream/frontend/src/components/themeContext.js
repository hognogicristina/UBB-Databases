import {createContext} from "react"

export const DEFAULT_THEME = "light"

export const ThemeContext = createContext({
  theme: DEFAULT_THEME,
  setTheme: () => {},
  toggleTheme: () => {},
})
