import {StrictMode} from "react"
import {createRoot} from "react-dom/client"
import "@cloudscape-design/global-styles/index.css"
import App from "./App.jsx"
import {AuthProvider} from "./components/AuthContext.jsx"
import {NotificationProvider} from "./components/NotificationProvider.jsx"
import {ThemeProvider} from "./components/ThemeContext.jsx"
import "./styles/index.css"

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <AuthProvider>
      <ThemeProvider>
        <NotificationProvider>
          <App/>
        </NotificationProvider>
      </ThemeProvider>
    </AuthProvider>
  </StrictMode>,
)
