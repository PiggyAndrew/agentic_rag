import path from "node:path"
import { fileURLToPath } from "node:url"
import fsp from "node:fs/promises"

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const projectDir = path.resolve(__dirname, "..")
const repoRoot = path.resolve(projectDir, "..", "..")

const srcDir = path.join(repoRoot, "frontend", "agui-vue", "dist")
const dstDir = path.join(projectDir, "resources", "renderer")

async function exists(p) {
  try {
    await fsp.access(p)
    return true
  } catch {
    return false
  }
}

if (!(await exists(srcDir))) {
  throw new Error(`renderer dist not found: ${srcDir}`)
}

await fsp.rm(dstDir, { recursive: true, force: true })
await fsp.mkdir(dstDir, { recursive: true })
await fsp.cp(srcDir, dstDir, { recursive: true })

