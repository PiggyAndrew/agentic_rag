# Agentic RAG Electron 桌面应用构建文档

## 目录

- [项目概述](#项目概述)
- [技术架构](#技术架构)
- [开发环境设置](#开发环境设置)
- [开发模式运行](#开发模式运行)
- [生产环境构建](#生产环境构建)
- [跨平台打包](#跨平台打包)
- [Content Security Policy (CSP) 配置](#content-security-policy-csp-配置)
- [常见问题](#常见问题)

---

## 项目概述

Agentic RAG 是一个基于 Electron 的桌面应用，整合了 Vue 前端和 Python 后端，提供完整的 RAG（检索增强生成）功能。

### 主要特性

- **前端**：Vue 3 + Vite + Element Plus
- **后端**：Python + FastAPI + LangChain
- **桌面容器**：Electron
- **数据库**：SQLite
- **向量存储**：ChromaDB

---

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Electron 主进程                          │
│  - 窗口管理                                            │
│  - Python 后端进程管理                                   │
│  - 文件系统访问                                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ├────────────────────────────────┐
                            │                            │
                            ▼                            ▼
┌─────────────────────────┐    ┌─────────────────────────┐
│   Vue 渲染进程          │    │   Python 后端进程       │
│  - Vue 3 应用            │    │  - FastAPI 服务         │
│  - Element Plus UI       │    │  - LangChain 集成       │
│  - 前端路由             │    │  - 数据库操作           │
│  - 状态管理 (Pinia)     │    │  - 向量检索             │
└─────────────────────────┘    └─────────────────────────┘
                            │
                            ▼
                    ┌──────────────────┐
                    │   SQLite 数据库  │
                    │   ChromaDB 向量库│
                    └──────────────────┘
```

---

## 开发环境设置

### 前置要求

- Node.js >= 18
- Python >= 3.11
- npm 或 yarn

### 安装依赖

#### 1. 安装 Electron 依赖

```bash
cd frontend/agui-electron
npm install
```

#### 2. 安装 Vue 依赖

```bash
cd frontend/agui-vue
npm install
```

#### 3. 安装 Python 依赖

```bash
# 在项目根目录
pip install -r requirements.txt
# 或者使用 pyproject.toml
pip install -e .
```

#### 4. 安装 PyInstaller（用于打包 Python）

```bash
pip install pyinstaller
```

---

## 开发模式运行

开发模式需要同时运行两个服务：Vue 开发服务器和 Electron 应用。

### 方式一：使用 npm scripts（推荐）

#### 终端 1：启动 Vue 开发服务器

```bash
cd frontend/agui-vue
npm run dev
```

Vue 开发服务器将在 `http://localhost:5173` 启动。

#### 终端 2：启动 Electron 开发模式

```bash
cd frontend/agui-electron
npm run dev
```

这将自动设置 `ELECTRON_DEV=1` 环境变量并启动 Electron。

### 方式二：手动设置环境变量

```bash
# Windows PowerShell
$env:ELECTRON_DEV="1"; npm start

# Windows CMD
set ELECTRON_DEV=1 && npm start

# Linux/macOS
ELECTRON_DEV=1 npm start
```

### 开发模式特点

- 自动打开开发者工具
- 支持热重载（HMR）
- 显示详细的日志输出
- 连接到本地 Vite 开发服务器

---

## 生产环境构建

生产环境构建包括以下步骤：

### 1. 构建 Vue 前端

```bash
cd frontend/agui-vue
npm run build
```

这将生成 `frontend/agui-vue/dist` 目录，包含静态资源文件。

### 2. 打包 Python 后端

```bash
cd frontend/agui-electron
npm run build:python
```

这将使用 PyInstaller 将 Python 后端打包为单一可执行文件 `agent_api.exe`。

**注意**：首次运行时会自动安装 PyInstaller。

### 3. 构建 Electron 主进程

```bash
cd frontend/agui-electron
npm run build
```

这将使用 tsup 将 TypeScript 代码编译为 CommonJS 格式。

### 4. 准备资源文件

```bash
cd frontend/agui-electron
npm run prepare:all
```

这将：
- 复制 Vue 构建产物到 `resources/renderer`
- 复制 Python 打包产物到 `resources/python`

### 5. 一键构建所有

```bash
cd frontend/agui-electron
npm run build:all
```

这将依次执行上述所有步骤。

---

## 跨平台打包

### Windows 打包

```bash
cd frontend/agui-electron
npm run dist:win
```

生成的文件位于 `release/` 目录：
- `Agentic RAG Setup x.x.x.exe` - NSIS 安装程序
- `Agentic RAG x.x.x.exe` - 便携版可执行文件

### macOS 打包

```bash
cd frontend/agui-electron
npm run dist:mac
```

生成的文件位于 `release/` 目录：
- `Agentic RAG-x.x.x.dmg` - DMG 镜像文件
- `Agentic RAG-x.x.x-arm64.dmg` - ARM64 版本（Apple Silicon）

### Linux 打包

```bash
cd frontend/agui-electron
npm run dist:linux
```

生成的文件位于 `release/` 目录：
- `Agentic RAG-x.x.x.AppImage` - AppImage 格式
- `agentic-rag_x.x.x_amd64.deb` - DEB 包
- `agentic-rag-x.x.x-1.x86_64.rpm` - RPM 包

### 所有平台打包

```bash
cd frontend/agui-electron
npm run dist
```

这将根据当前操作系统打包对应平台的安装包。

---

## Content Security Policy (CSP) 配置

### 为什么需要 CSP？

Electron 默认会显示安全警告，如果没有正确配置 Content Security Policy。CSP 是一个安全层，帮助防止跨站脚本攻击（XSS）和数据注入攻击。

### 当前 CSP 配置

在 `frontend/agui-vue/index.html` 中添加了以下 CSP 策略：

```html
<meta http-equiv="Content-Security-Policy" 
      content="default-src 'self'; 
               script-src 'self' 'unsafe-inline' 'unsafe-eval'; 
               style-src 'self' 'unsafe-inline'; 
               img-src 'self' data: blob:; 
               font-src 'self' data:; 
               connect-src 'self' http://127.0.0.1:* ws://127.0.0.1:*; 
               worker-src 'self' blob:;">
```

### 策略说明

- `default-src 'self'` - 默认只允许加载同源资源
- `script-src 'self' 'unsafe-inline' 'unsafe-eval'` - 允许内联脚本和 eval（Vue 需要）
- `style-src 'self' 'unsafe-inline'` - 允许内联样式
- `img-src 'self' data: blob:` - 允许加载图片、data URL 和 blob URL
- `font-src 'self' data:` - 允许加载字体和 data URL
- `connect-src 'self' http://127.0.0.1:* ws://127.0.0.1:*` - 允许连接本地后端
- `worker-src 'self' blob:` - 允许使用 Web Workers

### 安全最佳实践

1. **最小权限原则**：只允许必要的资源类型
2. **避免 `unsafe-eval`**：虽然当前需要，但应尽量减少使用
3. **限制连接源**：只允许连接本地后端（127.0.0.1）
4. **定期审查**：根据实际需求调整策略

---

## 常见问题

### 1. Electron 启动时显示 CSP 警告

**问题**：看到 "Electron Security Warning (Insecure Content-Security-Policy)" 警告

**解决方案**：
- 确保 `frontend/agui-vue/index.html` 中包含 CSP meta 标签
- 重新构建 Vue 前端：`cd frontend/agui-vue && npm run build`
- 重新准备资源：`cd frontend/agui-electron && npm run prepare:renderer`

### 2. Python 后端启动失败

**问题**：应用启动时显示 "后端服务未就绪" 错误

**解决方案**：
- 检查 Python 依赖是否完整安装
- 查看日志文件：`%APPDATA%/agui-electron/logs/agent_api.log`
- 确保端口未被占用
- 在开发模式下手动测试 Python 服务：`python -m backend.entrypoints.server`

### 3. Vue 前端无法连接后端

**问题**：前端显示网络错误或无法加载数据

**解决方案**：
- 检查 CSP 策略中的 `connect-src` 是否包含 `http://127.0.0.1:*`
- 确保后端服务正在运行
- 检查防火墙设置
- 查看浏览器控制台错误信息

### 4. 打包后的应用无法启动

**问题**：双击安装后的应用无反应

**解决方案**：
- 检查是否正确打包了 Python 可执行文件
- 查看应用日志：`%APPDATA%/agui-electron/logs/main.log`
- 尝试以管理员身份运行
- 检查杀毒软件是否拦截

### 5. 构建时 PyInstaller 失败

**问题**：运行 `npm run build:python` 时出错

**解决方案**：
- 确保 PyInstaller 已安装：`pip install pyinstaller`
- 检查 `backend/entrypoints/server.spec` 文件是否存在
- 清理旧的构建目录：删除 `build/` 文件夹
- 检查 Python 依赖是否完整

### 6. 开发模式下热重载不工作

**问题**：修改 Vue 代码后页面不自动刷新

**解决方案**：
- 确保 Vite 开发服务器正在运行
- 检查浏览器控制台是否有错误
- 尝试手动刷新页面
- 重启 Vite 开发服务器

### 7. 打包体积过大

**问题**：生成的安装包文件很大

**解决方案**：
- 在 `backend/entrypoints/server.spec` 中排除不需要的模块
- 使用 UPX 压缩（已启用）
- 清理 Python 依赖中的测试文件和文档
- 考虑使用虚拟环境隔离依赖

### 8. macOS 签名问题

**问题**：macOS 上应用无法打开，提示"已损坏"

**解决方案**：
- 在系统设置中允许运行未签名的应用
- 使用 `xattr -cr /Applications/Agentic\ RAG.app` 移除隔离属性
- 配置代码签名（需要 Apple 开发者账号）

---

## 文件结构

```
agentic_rag/
├── frontend/
│   ├── agui-electron/          # Electron 主项目
│   │   ├── dist/               # 编译后的 Electron 代码
│   │   ├── resources/          # 资源文件
│   │   │   ├── renderer/      # Vue 构建产物
│   │   │   └── python/       # Python 打包产物
│   │   ├── scripts/           # 构建脚本
│   │   │   ├── build-python.mjs
│   │   │   ├── prepare-python.mjs
│   │   │   └── prepare-renderer.mjs
│   │   ├── src/               # 源代码
│   │   │   ├── main/         # 主进程
│   │   │   └── preload/      # 预加载脚本
│   │   ├── package.json
│   │   ├── electron-builder.json
│   │   └── tsconfig.json
│   └── agui-vue/            # Vue 前端项目
│       ├── dist/               # 构建产物
│       ├── src/               # 源代码
│       ├── package.json
│       └── vite.config.ts
├── backend/                  # Python 后端
│   ├── entrypoints/
│   │   └── server.py        # FastAPI 入口
│   ├── entrypoints/
│   │   └── server.spec      # PyInstaller 配置
│   └── ...                 # 其他后端代码
├── build/                    # PyInstaller 构建输出
│   └── exe.win-amd64-3.12/
│       ├── agent_api.exe      # 打包后的 Python 可执行文件
│       └── lib/             # Python 库文件
└── release/                 # Electron 打包输出
    ├── Agentic RAG Setup x.x.x.exe
    └── win-unpacked/
```

---

## 环境变量

### Electron 主进程

- `ELECTRON_DEV` - 设置为 "1" 启用开发模式
- `VITE_DEV_SERVER_URL` - 自定义 Vite 开发服务器 URL

### Python 后端

- `APP_ENV` - 应用环境（development/production）
- `HOST` - 服务监听地址
- `PORT` - 服务监听端口
- `KB_SQLITE_URL` - SQLite 数据库连接字符串
- `KB_SQLITE_MIGRATIONS_DIR` - 数据库迁移文件目录

---

## 日志文件

### Windows

- 主进程日志：`%APPDATA%\agui-electron\logs\main.log`
- Python 后端日志：`%APPDATA%\agui-electron\logs\agent_api.log`

### macOS

- 主进程日志：`~/Library/Logs/agui-electron/main.log`
- Python 后端日志：`~/Library/Logs/agui-electron/agent_api.log`

### Linux

- 主进程日志：`~/.config/agui-electron/logs/main.log`
- Python 后端日志：`~/.config/agui-electron/logs/agent_api.log`

---

## 贡献指南

如需贡献代码，请遵循以下步骤：

1. Fork 项目仓库
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m 'Add some feature'`
4. 推送到分支：`git push origin feature/your-feature`
5. 提交 Pull Request

---

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

---

## 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 Issue
- 发送邮件至项目维护者
- 加入社区讨论组

---

**最后更新**：2026-02-06
