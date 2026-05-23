import { app } from "electron"
import fs from "node:fs"
import fsp from "node:fs/promises"
import net from "node:net"
import path from "node:path"
import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process"

type PythonHandle = {
  process: ChildProcessWithoutNullStreams
  apiBase: string
}

let current: PythonHandle | null = null

function repoRootFromDistMain(distMainDir: string): string {
  return path.resolve(distMainDir, "..", "..", "..", "..")
}

async function getFreePort(host: string): Promise<number> {
  return await new Promise((resolve, reject) => {
    const server = net.createServer()
    server.on("error", reject)
    server.listen(0, host, () => {
      const addr = server.address()
      server.close(() => {
        if (addr && typeof addr === "object") resolve(addr.port)
        else reject(new Error("failed to acquire ephemeral port"))
      })
    })
  })
}

function sqliteUrlFromFile(filePath: string): string {
  const normalized = filePath.replace(/\\/g, "/")
  return `sqlite:///${normalized}`
}

async function waitForHttpOk(url: string, timeoutMs: number): Promise<void> {
  const started = Date.now()
  while (true) {
    try {
      const resp = await fetch(url, { method: "GET" })
      if (resp.ok) return
    } catch {}
    if (Date.now() - started > timeoutMs) {
      throw new Error(`backend not ready: ${url}`)
    }
    await new Promise((r) => setTimeout(r, 200))
  }
}

async function ensureDir(dirPath: string): Promise<void> {
  await fsp.mkdir(dirPath, { recursive: true })
}

function createLogStream(): fs.WriteStream {
  const userData = app.getPath("userData")
  const logsDir = path.join(userData, "logs")
  const primary = path.join(logsDir, "agent_api.log")
  try {
    fs.mkdirSync(logsDir, { recursive: true })
    return fs.createWriteStream(primary, { flags: "a" })
  } catch {}
  try {
    const root = path.join(userData, "agent_api.log")
    return fs.createWriteStream(root, { flags: "a" })
  } catch {}
  const tmp = process.env.TEMP || process.env.TMP || userData
  const tmpFile = path.join(tmp, "AgenticRAG-agent_api.log")
  return fs.createWriteStream(tmpFile, { flags: "a" })
}

function buildEnv(params: {
  host: string
  port: number
  repoRoot?: string
  pythonDir?: string
}): NodeJS.ProcessEnv {
  const userData = app.getPath("userData")
  const kbRootDir = path.join(userData, "data", "kb")
  const sqliteFile = path.join(kbRootDir, "knowledge.sqlite3")
  const env: NodeJS.ProcessEnv = {
    ...process.env,
    APP_ENV: "production",
    HOST: params.host,
    PORT: String(params.port),
    KB_ROOT_DIR: kbRootDir,
    KB_SQLITE_URL: sqliteUrlFromFile(sqliteFile),
  }

  if (params.pythonDir) {
    env.KB_SQLITE_MIGRATIONS_DIR = path.join(params.pythonDir, "backend", "database", "migrations")
  }
  if (params.repoRoot) {
    env.KB_SQLITE_MIGRATIONS_DIR = path.join(params.repoRoot, "backend", "database", "migrations")
  }
  return env
}

export async function startPythonBackend(distMainDir: string): Promise<PythonHandle> {
  if (current) return current

  const host = "127.0.0.1"
  const port = await getFreePort(host)
  const apiBase = `http://${host}:${port}`

  const userData = app.getPath("userData")
  await ensureDir(path.join(userData, "data", "kb"))

  const logStream = createLogStream()

  let proc: ChildProcessWithoutNullStreams
  if (app.isPackaged) {
    const pythonDir = path.join(process.resourcesPath, "python")
    const exePath = path.join(pythonDir, "agent_api.exe")
    try {
      logStream.write(`[info] spawn packaged exe: ${exePath} host=${host} port=${port}\n`)
    } catch {}
    proc = spawn(exePath, [], {
      cwd: userData,
      env: buildEnv({ host, port, pythonDir }),
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
    })
  } else {
    const repoRoot = repoRootFromDistMain(distMainDir)
    try {
      logStream.write(`[info] spawn dev python -m backend.entrypoints.server cwd=${repoRoot} host=${host} port=${port}\n`)
    } catch {}
    proc = spawn("python", ["-m", "backend.entrypoints.server"], {
      cwd: repoRoot,
      env: buildEnv({ host, port, repoRoot }),
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
    })
  }

  proc.stdout.on("data", (d) => logStream.write(d))
  proc.stderr.on("data", (d) => logStream.write(d))
  proc.on("error", (err) => {
    try {
      logStream.write(`[error] child_process_error ${String(err)}\n`)
    } catch {}
  })
  proc.on("exit", (code, signal) => {
    try {
      logStream.write(`[info] child_exit code=${code} signal=${signal ?? ""}\n`)
    } catch {}
    try {
      logStream.end()
    } catch {}
  })

  await waitForHttpOk(`${apiBase}/docs`, 60_000)

  current = { process: proc, apiBase }
  return current
}

export async function stopPythonBackend(): Promise<void> {
  if (!current) return
  const proc = current.process
  current = null

  try {
    if (!proc.killed) proc.kill()
  } catch {}
}
