import path from "node:path"
import { fileURLToPath } from "node:url"
import fsp from "node:fs/promises"

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const projectDir = path.resolve(__dirname, "..")
const repoRoot = path.resolve(projectDir, "..", "..")

const buildDir = path.join(repoRoot, "build")
const dstDir = path.join(projectDir, "resources", "python")

async function listDirs(dir) {
  const items = await fsp.readdir(dir, { withFileTypes: true })
  return items.filter((d) => d.isDirectory()).map((d) => d.name)
}

async function exists(p) {
  try {
    await fsp.access(p)
    return true
  } catch {
    return false
  }
}

if (!(await exists(buildDir))) {
  throw new Error(`python build directory not found: ${buildDir}`)
}

const candidates = (await listDirs(buildDir))
  .filter((n) => /^exe\.win-amd64-/.test(n))
  .sort()

const pick = candidates[candidates.length - 1]
if (!pick) {
  throw new Error(`python build output not found under: ${buildDir}`)
}

const srcDir = path.join(buildDir, pick)

await fsp.rm(dstDir, { recursive: true, force: true })
await fsp.mkdir(dstDir, { recursive: true })
await fsp.cp(srcDir, dstDir, { recursive: true })

const envFile = path.join(dstDir, ".env")
if (await exists(envFile)) {
  await fsp.unlink(envFile)
}

