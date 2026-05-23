import { app, BrowserWindow, dialog, Menu } from "electron";
import path from "node:path";
import fs from "node:fs";
import { startPythonBackend, stopPythonBackend } from "./python";

const WINDOW_TITLE = "Agentic RAG";

function isDev(): boolean {
  return (
    String(process.env.ELECTRON_DEV ?? "").toLowerCase() === "1" ||
    Boolean(process.env.VITE_DEV_SERVER_URL)
  );
}

function preloadPath(): string {
  return path.join(__dirname, "..", "preload", "index.cjs");
}

function rendererIndexHtml(): string {
  return path.join(process.resourcesPath, "renderer", "index.html");
}

async function createMainWindow(apiBase: string): Promise<BrowserWindow> {
  const win = new BrowserWindow({
    width: 1280,
    height: 860,
    title: WINDOW_TITLE,
    webPreferences: {
      preload: preloadPath(),
      contextIsolation: true,
      nodeIntegration: false,
      additionalArguments: [`--agui-api-base=${apiBase}`],
    },
  });
  win.on("page-title-updated", (e) => {
    e.preventDefault();
  });
  win.setTitle(WINDOW_TITLE);
  if (isDev()) {
    const url = process.env.VITE_DEV_SERVER_URL || "http://localhost:5173";
    await win.loadURL(url);
    win.webContents.openDevTools({ mode: "detach" });
  } else {
    Menu.setApplicationMenu(null);
    await win.loadFile(rendererIndexHtml());
  }

  return win;
}

function ensureLogStream(): fs.WriteStream {
  const userData = app.getPath("userData");
  const primaryDir = path.join(userData, "logs");
  const primaryFile = path.join(primaryDir, "main.log");
  try {
    fs.mkdirSync(primaryDir, { recursive: true });
    return fs.createWriteStream(primaryFile, { flags: "a" });
  } catch {}
  // fallback to root of userData
  try {
    const rootFile = path.join(userData, "main.log");
    return fs.createWriteStream(rootFile, { flags: "a" });
  } catch {}
  // fallback to temp directory
  const tmp = process.env.TEMP || process.env.TMP || userData;
  const tmpFile = path.join(tmp, "AgenticRAG-main.log");
  return fs.createWriteStream(tmpFile, { flags: "a" });
}

const logStream = ensureLogStream();
function log(msg: string) {
  const line = `[${new Date().toISOString()}] ${msg}\n`;
  try {
    logStream.write(line);
  } catch {}
}

app.whenReady().then(async () => {
  log("app_ready");
  let apiBase = "";
  try {
    const handle = await startPythonBackend(__dirname);
    apiBase = handle.apiBase;
    log(`backend_started ${apiBase}`);
  } catch (e) {
    log(`backend_failed ${String(e)}`);
    dialog.showErrorBox("启动失败", "后端服务未就绪，请查看日志");
  }
  try {
    await createMainWindow(apiBase);
    log("window_created");
  } catch (e) {
    log(`window_failed ${String(e)}`);
  }
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", async () => {
  await stopPythonBackend();
});

process.on("uncaughtException", (err) => {
  log(`uncaught_exception ${String(err)}`);
});
process.on("unhandledRejection", (reason) => {
  log(`unhandled_rejection ${String(reason)}`);
});
