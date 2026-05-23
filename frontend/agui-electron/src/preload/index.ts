import { contextBridge } from "electron"

type RuntimeBridge = {
  getApiBase: () => string
}

function getArgValue(prefix: string): string {
  const hit = process.argv.find((a) => a.startsWith(prefix))
  if (!hit) return ""
  return hit.slice(prefix.length)
}

const runtime: RuntimeBridge = {
  getApiBase: () => getArgValue("--agui-api-base="),
}

contextBridge.exposeInMainWorld("runtime", runtime)
