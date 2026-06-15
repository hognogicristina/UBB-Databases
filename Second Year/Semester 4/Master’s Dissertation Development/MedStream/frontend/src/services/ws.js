const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws"

let socket = null
let socketState = "idle"
let subscriberId = 0
let closeTimer = null
const subscribers = new Map()

function clearCloseTimer() {
  if (closeTimer) {
    window.clearTimeout(closeTimer)
    closeTimer = null
  }
}

function cleanupSocket() {
  if (socket) {
    socket.onopen = null
    socket.onmessage = null
    socket.onerror = null
    socket.onclose = null
    socket = null
  }

  socketState = "idle"
}

function broadcastMessage(payload) {
  subscribers.forEach(({onMessage}) => {
    onMessage(payload)
  })
}

function broadcastError() {
  subscribers.forEach(({onError}) => {
    onError?.()
  })
}

function connectSocket() {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return socket
  }

  cleanupSocket()

  socketState = "connecting"
  socket = new WebSocket(WS_URL)

  socket.onopen = () => {
    socketState = "open"
  }

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      broadcastMessage(data)
    } catch {
      return
    }
  }

  socket.onerror = () => {
    socketState = "error"
    broadcastError()
  }

  socket.onclose = () => {
    cleanupSocket()
  }

  return socket
}

function scheduleSocketClose() {
  clearCloseTimer()

  closeTimer = window.setTimeout(() => {
    closeTimer = null

    if (subscribers.size > 0) {
      return
    }

    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
      socket.close()
    } else {
      cleanupSocket()
    }
  }, 250)
}

export function createWebSocket(onMessage, onError) {
  clearCloseTimer()

  const id = `${Date.now()}-${subscriberId += 1}`
  subscribers.set(id, {onMessage, onError})

  if (socketState !== "open" && socketState !== "connecting") {
    connectSocket()
  }

  return {
    close() {
      subscribers.delete(id)

      if (subscribers.size === 0) {
        scheduleSocketClose()
      }
    },
  }
}
