export {}

declare global {
  interface Window {
    runtime?: {
      getApiBase?: () => string
    }
  }
}

