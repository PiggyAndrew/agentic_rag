# 更新日志

## [Unreleased]

### 修复 (Fixes)
- **前端构建**: 修复 Vue 3 + TypeScript 编译错误，确保项目能够成功构建

  - `ActiveConfigPanel.vue` - 修复 `$event.target` 的类型断言问题
  - `ConfigSidebar.vue` - 移除未使用的 props 变量声明
  - `ProviderLibraryPanel.vue` - 移除未使用的 props 变量声明
  - `KnowledgeBaseChat.vue` - 将 `NodeJS.Timeout` 类型改为 `ReturnType<typeof setTimeout>` 以提高兼容性
  - `LLMConfigManager.vue` - 修复 `Provider` 与 `LLMProvider` 类型不匹配问题，添加类型转换逻辑
  - `ProviderDialog.vue` - 更新 `@test` 事件签名，正确传递表单数据

### 改进 (Improvements)
- **代码质量**: 添加 ESLint 和 Prettier 配置文件
  - 新增 `.editorconfig` - 统一编辑器配置
  - 新增 `.prettierrc` - 代码格式化规则
  - 新增 `.prettierignore` - 指定不需要格式化的文件
- **构建脚本**: 在 `package.json` 中添加新的 npm 脚本
  - `npm run lint` - 运行 ESLint 检查
  - `npm run lint:fix` - 自动修复 ESLint 问题
  - `npm run format` - 使用 Prettier 格式化代码
  - `npm run format:check` - 检查代码格式

### 技术细节
- 修复了 Inno Setup 安装程序构建时的类型错误
- 解决了 Windows 桌面应用打包过程中的兼容性问题
- 确保前端代码可以成功编译并生成生产构建

---

## 版本说明

### 构建状态
- ✅ Vue 前端构建成功
- ✅ Python 后端构建成功 (cx_Freeze)
- ✅ WPF 桌面应用构建成功
- ✅ Inno Setup 安装程序生成成功

### 安装程序
- 文件名: `Agentic_RAG_Installer.exe`
- 位置: `setup/Output/`
- 大小: ~113 MB
