using Microsoft.Web.WebView2.Core;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Threading;
using System.Windows;
using WPF_ArchiPlaning;

namespace BUD_Sustainable_Building_Designer
{
    class WebMessageService
    {
        private readonly string _ifcExportExeName= "ifc_exporter.exe";
        private readonly string exePath =  Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "ifc_exporter.exe");
        private readonly string _pythonCliExeName = "wind_path_cli.exe";
        private TaskCompletionSource<bool>? _exportStateTcs;

        /// <summary>
        /// 处理从网页接收到的消息
        /// </summary>
        public void CoreWebView2_WebMessageReceived(object sender, CoreWebView2WebMessageReceivedEventArgs e)
        {
            try
            {
                AppLogger.Info("CoreWebView2_WebMessageReceived: start");
                // 获取消息内容
                string message = e.WebMessageAsJson;
                AppLogger.Info($"CoreWebView2_WebMessageReceived: rawLen={message?.Length ?? 0}");

                // 解析JSON消息
                var jsonDocument = System.Text.Json.JsonDocument.Parse(message);
                var root = jsonDocument.RootElement;
                AppLogger.Info($"CoreWebView2_WebMessageReceived: rootKind={root.ValueKind}");

                // 如果root是字符串类型，需要进行二次解析
                if (root.ValueKind == System.Text.Json.JsonValueKind.String)
                {
                    string jsonString = root.GetString();
                    jsonDocument = System.Text.Json.JsonDocument.Parse(jsonString);

                    var obj = jsonDocument.RootElement;
                    if (obj.TryGetProperty("type", out var typeElem))
                    {
                        var type = typeElem.GetString();
                         AppLogger.Info($"CoreWebView2_WebMessageReceived: type={type}");
                        if (type == "python_analyze_matrix")
                        {
                            AppLogger.Info("CoreWebView2_WebMessageReceived: dispatch python_analyze_matrix");
                            HandleAnalyzeMatrix(sender as CoreWebView2, obj);
                            return;
                        }
                        else if (type == "ifc_export")
                        {
                            AppLogger.Info("CoreWebView2_WebMessageReceived: dispatch ifc_export");
                            HandleExportIFC(jsonDocument);
                            return;
                        }
                        else if (type == "export_project_state_result")
                        {
                            AppLogger.Info("CoreWebView2_WebMessageReceived: dispatch export_project_state_result");
                            HandleExportProjectStateResult(obj, sender as CoreWebView2);
                            return;
                        }
                    }
                    // 默认处理：尝试 IFC 导出
                    AppLogger.Warn("CoreWebView2_WebMessageReceived: unknown type, fallback to ifc_export");
                    HandleExportIFC(jsonDocument);
                }

            }
            catch (Exception ex)
            {
                AppLogger.Error("CoreWebView2_WebMessageReceived: exception", ex);
            }
        }

        //public void CoreWebView2_WebResourceRequested(object sender, CoreWebView2WebResourceRequestedEventArgs e)
        //{
        //    try
        //    {
        //        // 获取请求的URI
        //        var uri = new Uri(e.Request.Uri);

        //        // 如果是file协议，尝试从dist文件夹加载资源
        //        if (uri.Scheme == "file")
        //        {
        //            string filePath = uri.LocalPath;

        //            // 如果路径不在dist文件夹内，尝试从相对路径解析
        //            if (!filePath.StartsWith(_distFolderPath, StringComparison.OrdinalIgnoreCase))
        //            {
        //                string relativePath = uri.LocalPath.TrimStart('/');
        //                filePath = Path.Combine(_distFolderPath, relativePath);
        //            }

        //            if (File.Exists(filePath))
        //            {
        //                // 读取文件内容
        //                byte[] fileContent = File.ReadAllBytes(filePath);

        //                // 创建响应流
        //                var stream = new MemoryStream(fileContent);

        //                // 获取MIME类型
        //                string mimeType = GetMimeTypeFromFileName(filePath);

        //                // 创建响应对象
        //                var response = webView.CoreWebView2.Environment.CreateWebResourceResponse(
        //                    stream, 200, "OK", $"Content-Type: {mimeType}");

        //                e.Response = response;
        //            }
        //        }
        //    }
        //    catch (Exception ex)
        //    {
        //        // 记录异常但不中断执行
        //        Console.WriteLine($"处理资源请求时出错: {ex.Message}");
        //    }
        //}

        /// <summary>
        /// 处理IFC导出请求
        /// </summary>
        public void HandleExportIFC(System.Text.Json.JsonDocument jsonDoc)
        {
            try
            {
                // 在UI线程中显示文件保存对话框
                string outputFile = null;
                bool userCancelled = false;

                // 创建保存文件对话框
                Microsoft.Win32.SaveFileDialog saveFileDialog = new Microsoft.Win32.SaveFileDialog
                {
                    Title = "选择IFC文件保存位置",
                    Filter = "IFC文件 (*.ifc)|*.ifc|所有文件 (*.*)|*.*",
                    DefaultExt = ".ifc",
                    FileName = $"ArchiPlaning_Export_{DateTime.Now:yyyyMMdd_HHmmss}.ifc",
                    InitialDirectory = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments)
                };

                // 显示对话框
                if (saveFileDialog.ShowDialog() == true)
                {
                    outputFile = saveFileDialog.FileName;
                }

                // 如果用户取消了操作，直接返回
                if (userCancelled || string.IsNullOrEmpty(outputFile))
                {
                    return;
                }

                // 在后台线程中执行导出操作
                Task.Run(() =>
                {
                    try
                    {

                        var root = jsonDoc.RootElement;
                        if (!root.TryGetProperty("buildings", out var _))
                        {
                            throw new Exception("数据格式错误：缺少buildings字段");
                        }

                        // 创建临时JSON文件
                        string tempDir = Path.GetTempPath();
                        string tempJsonFile = Path.Combine(tempDir, $"ifc_export_{Guid.NewGuid()}.json");

                        // 将数据写入临时文件 - 使用不带BOM的UTF-8编码
                        File.WriteAllText(tempJsonFile, root.GetString(), new UTF8Encoding(false));

                      

                        // 检查文件是否存在
                        if (!File.Exists(exePath))
                        {
                            return;
                        }

                        // 创建进程启动信息
                        ProcessStartInfo startInfo = new ProcessStartInfo
                        {
                            FileName = exePath,
                            Arguments = $"--input \"{tempJsonFile}\" --output \"{outputFile}\"",
                            UseShellExecute = false,
                            RedirectStandardOutput = true,
                            RedirectStandardError = true,
                            CreateNoWindow = true,
                            StandardOutputEncoding = Encoding.UTF8,
                            StandardErrorEncoding = Encoding.UTF8
                        };

                        // 创建输出缓冲区
                        StringBuilder outputBuilder = new StringBuilder();
                        StringBuilder errorBuilder = new StringBuilder();

                        // 启动进程
                        using (Process process = new Process())
                        {
                            process.StartInfo = startInfo;

                            // 设置输出处理
                            process.OutputDataReceived += (sender, e) =>
                            {
                                if (!string.IsNullOrEmpty(e.Data))
                                    outputBuilder.AppendLine(e.Data);
                            };

                            process.ErrorDataReceived += (sender, e) =>
                            {
                                if (!string.IsNullOrEmpty(e.Data))
                                    errorBuilder.AppendLine(e.Data);
                            };

                            // 启动进程
                            process.Start();

                            // 开始异步读取
                            process.BeginOutputReadLine();
                            process.BeginErrorReadLine();

                            // 等待进程结束
                            process.WaitForExit();

                            // 检查进程退出代码
                            if (process.ExitCode != 0)
                            {
                                // 导出失败
                                string errorMessage = errorBuilder.ToString();
                                string outputMessage = outputBuilder.ToString();

                                // 保存错误日志到文件
                                string logFile = Path.Combine(
                                    Environment.GetFolderPath(Environment.SpecialFolder.Desktop),
                                    $"ArchiPlaning_Error_{DateTime.Now:yyyyMMdd_HHmmss}.log");

                                File.WriteAllText(logFile,
                                    $"=== 导出失败 ===\n时间: {DateTime.Now}\n" +
                                    $"退出代码: {process.ExitCode}\n\n" +
                                    $"错误信息:\n{errorMessage}\n\n" +
                                    $"标准输出:\n{outputMessage}");

                                if (string.IsNullOrEmpty(errorMessage))
                                {
                                    errorMessage = $"导出失败，退出代码: {process.ExitCode}";
                                }

                            }
                        }

                        // 清理临时文件
                        try
                        {
                            if (File.Exists(tempJsonFile))
                                File.Delete(tempJsonFile);
                        }
                        catch { 
                        }
                    }
                    catch (Exception ex)
                    {
                        MessageBox.Show($"导出过程中发生错误:\n{ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
                    }
                });
            }
            catch (Exception ex)
            {
                MessageBox.Show($"启动导出过程时发生错误:\n{ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        /// <summary>
        /// 处理风分析矩阵的桥接请求：写入临时JSON，调用打包的CLI或Python脚本，返回结果到前端
        /// </summary>
        private void HandleAnalyzeMatrix(CoreWebView2 core, System.Text.Json.JsonElement obj)
        {
            try
            {
                if (!obj.TryGetProperty("payload", out var payload))
                {
                    PostBridgeError(core, "Invalid payload: missing 'payload'");
                    return;
                }
                var filename = payload.TryGetProperty("filename", out var f) ? f.GetString() ?? "uploaded_file" : "uploaded_file";
                var zone = payload.TryGetProperty("zone", out var z) ? z.GetString() ?? "" : "";
                if (string.IsNullOrWhiteSpace(zone))
                {
                    PostBridgeError(core, "Missing required field: zone");
                    return;
                }
                if (!payload.TryGetProperty("matrix", out var matrixElem))
                {
                    PostBridgeError(core, "Missing required field: matrix");
                    return;
                }

                // 将矩阵写入临时文件
                var tmpDir = Path.GetTempPath();
                var tmpFolder = Path.Combine(tmpDir, "wind-analysis", Guid.NewGuid().ToString());
                Directory.CreateDirectory(tmpFolder);
                var matrixPath = Path.Combine(tmpFolder, "matrix.json");
                var outputPath = Path.Combine(tmpFolder, "result.json");
                var matrixWrapper = new
                {
                    matrix = System.Text.Json.JsonSerializer.Deserialize<object>(matrixElem.GetRawText())
                };
                File.WriteAllText(matrixPath, System.Text.Json.JsonSerializer.Serialize(matrixWrapper), new UTF8Encoding(false));

                // 选择调用方式：仅使用打包的 CLI exe（不回退到 python 解释器）
                var cliExePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, _pythonCliExeName);
                if (!File.Exists(cliExePath))
                {
                    PostBridgeError(core, $"CLI not found: {cliExePath}");
                    return;
                }
                var startInfo = new ProcessStartInfo
                {
                    FileName = cliExePath,
                    Arguments = $"--matrix \"{matrixPath}\" --json-key matrix --zone \"{zone}\" --filename \"{filename}\" --output \"{outputPath}\" --print-summary",
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true,
                    StandardOutputEncoding = Encoding.UTF8,
                    StandardErrorEncoding = Encoding.UTF8
                };

                var outputBuilder = new StringBuilder();
                var errorBuilder = new StringBuilder();

                using (var process = new Process())
                {
                    process.StartInfo = startInfo;
                    process.OutputDataReceived += (_, args) => { if (!string.IsNullOrWhiteSpace(args.Data)) outputBuilder.AppendLine(args.Data); };
                    process.ErrorDataReceived += (_, args) => { if (!string.IsNullOrWhiteSpace(args.Data)) errorBuilder.AppendLine(args.Data); };
                    process.Start();
                    process.BeginOutputReadLine();
                    process.BeginErrorReadLine();
                    process.WaitForExit();

                    if (process.ExitCode != 0)
                    {
                        var err = errorBuilder.ToString();
                        PostBridgeError(core, string.IsNullOrWhiteSpace(err) ? $"CLI exited with {process.ExitCode}" : err);
                        return;
                    }
                }

                // 读取输出并返回给前端
                if (!File.Exists(outputPath))
                {
                    PostBridgeError(core, "Output file not found");
                    return;
                }
                var content = File.ReadAllText(outputPath, new UTF8Encoding(false));
                var resp = new
                {
                    type = "python_analyze_matrix_result",
                    success = true,
                    data = System.Text.Json.JsonSerializer.Deserialize<object>(content)
                };
                core?.PostWebMessageAsJson(System.Text.Json.JsonSerializer.Serialize(resp));

                // 清理临时文件夹
                try { Directory.Delete(tmpFolder, true); } catch { }
            }
            catch (Exception ex)
            {
                PostBridgeError(core, ex.Message);
            }
        }

        /// <summary>
        /// 将错误消息通过 WebView2 回发到前端
        /// </summary>
        private void PostBridgeError(CoreWebView2 core, string message)
        {
            var err = new { type = "python_analyze_matrix_result", success = false, error = message };
            core?.PostWebMessageAsJson(System.Text.Json.JsonSerializer.Serialize(err));
        }

        /// <summary>
        /// 触发前端导出项目状态并保存到本地文件
        /// </summary>
        public async Task<bool> RequestExportProjectStateAndSave(CoreWebView2 core)
        {
            try
            {
                if (core == null) return false;
                AppLogger.Info("RequestExportProjectStateAndSave: start");
                _exportStateTcs = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
                var msg = new { type = "export_project_state" };
                core.PostWebMessageAsJson(System.Text.Json.JsonSerializer.Serialize(msg));
                var completed = await Task.WhenAny(_exportStateTcs.Task, Task.Delay(2000));
                var ok = completed == _exportStateTcs.Task && _exportStateTcs.Task.Result;
                AppLogger.Info($"RequestExportProjectStateAndSave: done ok={ok}");
                return ok;
            }
            catch (Exception ex)
            {
                AppLogger.Error("RequestExportProjectStateAndSave: exception", ex);
                return false;
            }
        }

        /// <summary>
        /// 处理导出状态结果消息并写入磁盘
        /// </summary>
        private void HandleExportProjectStateResult(System.Text.Json.JsonElement obj, CoreWebView2 core)
        {
            try
            {
                if (!obj.TryGetProperty("payload", out var payload))
                {
                    AppLogger.Warn("HandleExportProjectStateResult: missing payload");
                    _exportStateTcs?.TrySetResult(false);
                    return;
                }
                var path = GetStateFilePath();
                var dir = Path.GetDirectoryName(path);
                if (!string.IsNullOrEmpty(dir))
                {
                    Directory.CreateDirectory(dir);
                }
                var json = payload.GetRawText();
                File.WriteAllText(path, json, new UTF8Encoding(false));
                AppLogger.Info($"HandleExportProjectStateResult: saved {path} (bytes={json?.Length ?? 0})");
                _exportStateTcs?.TrySetResult(true);
            }
            catch (Exception ex)
            {
                AppLogger.Error("HandleExportProjectStateResult: exception", ex);
                _exportStateTcs?.TrySetResult(false);
            }
        }

        /// <summary>
        /// 在页面加载完成后，从本地文件读取项目状态并发送到前端进行恢复
        /// </summary>
        public void ImportProjectState(CoreWebView2 core)
        {
            try
            {
                if (core == null) return;
                var path = GetStateFilePath();
                if (!File.Exists(path))
                {
                    AppLogger.Info("ImportProjectState: no state file found");
                    return;
                }
                var text = File.ReadAllText(path, new UTF8Encoding(false));
                var resp = new
                {
                    type = "import_project_state",
                    payload = System.Text.Json.JsonSerializer.Deserialize<object>(text)
                };
                core.PostWebMessageAsJson(System.Text.Json.JsonSerializer.Serialize(resp));
                AppLogger.Info($"ImportProjectState: posted to web (bytes={text?.Length ?? 0})");
            }
            catch (Exception ex)
            {
                AppLogger.Error("ImportProjectState: exception", ex);
            }
        }

        /// <summary>
        /// 获取项目状态持久化文件路径（位于 LocalAppData 下）
        /// </summary>
        private string GetStateFilePath()
        {
            try
            {
                var appName = System.Reflection.Assembly.GetEntryAssembly()?.GetName().Name ?? "BUD Sustainable Building Designer";
                var localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                var dir = Path.Combine(localAppData, appName, "state");
                return Path.Combine(dir, "wind_analysis_state.json");
            }
            catch
            {
                return Path.Combine(Path.GetTempPath(), "wind_analysis_state.json");
            }
        }
    }
}
