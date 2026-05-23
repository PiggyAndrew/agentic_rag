import path from "node:path"
import { fileURLToPath } from "node:url"
import fsp from "node:fs/promises"
import { execSync } from "node:child_process"

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const projectDir = path.resolve(__dirname, "..")
const repoRoot = path.resolve(projectDir, "..", "..")
const setupFile = path.join(repoRoot, "setup", "setup.py")
const buildDir = path.join(repoRoot, "build")

async function exists(p) {
  try {
    await fsp.access(p)
    return true
  } catch {
    return false
  }
}

async function runCommand(cmd, cwd) {
  console.log(`Running: ${cmd}`)
  try {
    const output = execSync(cmd, {
      cwd: cwd || repoRoot,
      stdio: "inherit",
      shell: true
    })
    return output
  } catch (error) {
    console.error(`Command failed: ${cmd}`)
    throw error
  }
}

async function main() {
  console.log("Starting Python backend build process...")
  
  // 检查 setup.py 文件是否存在
  if (!(await exists(setupFile))) {
    throw new Error(`setup.py file not found: ${setupFile}`)
  }
  
  // 检查 cx_Freeze 是否已安装
  try {
    await runCommand("python -c \"import cx_Freeze; print(cx_Freeze.__version__)\"", repoRoot)
    console.log("cx_Freeze is installed")
  } catch {
    console.log("cx_Freeze not found, installing...")
    await runCommand("pip install cx_Freeze", repoRoot)
  }
  
  // 清理旧的构建目录
  if (await exists(buildDir)) {
    console.log("Cleaning old build directory...")
    await fsp.rm(buildDir, { recursive: true, force: true })
  }
  
  // 运行 cx_Freeze 构建
  console.log("Building Python backend with cx_Freeze...")
  await runCommand(`python "${setupFile}" build`, repoRoot)  
  console.log("Python backend build completed successfully!")
  console.log(`Build output: ${buildDir}`)
}

main().catch((error) => {
  console.error("Build failed:", error)
  process.exit(1)
})
