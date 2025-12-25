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
using System.Net.Http;
using System.Text.Json;

namespace BUD_Sustainable_Building_Designer
{
    class WebMessageService
    {
        private const string DEFAULT_REPO = "PiggyAndrew/agentic_rag";
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
                        if (type == "app_update_install")
                        {
                            AppLogger.Info("CoreWebView2_WebMessageReceived: dispatch app_update_install");
                            HandleAppUpdateInstall(obj, sender as CoreWebView2);
                            return;
                        }
                        else if (type == "app_update_execute")
                        {
                            AppLogger.Info("CoreWebView2_WebMessageReceived: dispatch app_update_execute");
                            HandleAppUpdateExecute(obj, sender as CoreWebView2);
                            return;
                        }
                    }
                    // 默认处理：尝试 IFC 导出
                    AppLogger.Warn("CoreWebView2_WebMessageReceived: unknown type, fallback to ifc_export");
                    HandleAppUpdateInstall(obj, sender as CoreWebView2);
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
        /// 将错误消息通过 WebView2 回发到前端
        /// </summary>
        private void PostBridgeError(CoreWebView2 core, string message)
        {
            var err = new { type = "python_analyze_matrix_result", success = false, error = message };
            core?.PostWebMessageAsJson(System.Text.Json.JsonSerializer.Serialize(err));
        }

        /// <summary>
        /// 处理应用更新安装请求：从 GitHub Releases 下载 .exe 并启动安装程序
        /// </summary>
        private async void HandleAppUpdateInstall(System.Text.Json.JsonElement obj, CoreWebView2 core)
        {
            try
            {
                if (!obj.TryGetProperty("payload", out var payload))
                {
                    PostUpdateResult(core, false, error: "missing payload");
                    return;
                }
                var repo = DEFAULT_REPO;
                var assetMatch = payload.TryGetProperty("assetMatch", out var am) ? am.GetString() ?? ".exe" : ".exe";
                var token = payload.TryGetProperty("token", out var t) ? t.GetString() ?? string.Empty : string.Empty;
                if (string.IsNullOrWhiteSpace(token))
                {
                    token = Environment.GetEnvironmentVariable("GITHUB_TOKEN")
                        ?? Environment.GetEnvironmentVariable("AGUI_GH_TOKEN")
                        ?? string.Empty;
                }
                var args = payload.TryGetProperty("args", out var a) ? a.GetString() ?? string.Empty : string.Empty;
                if (string.IsNullOrWhiteSpace(repo) || !repo.Contains('/'))
                {
                    PostUpdateResult(core, false, error: "invalid repo (expect owner/repo)");
                    return;
                }

                PostUpdateProgress(core, $"开始检查更新: {repo}");

                using var http = new HttpClient();
                http.DefaultRequestHeaders.UserAgent.ParseAdd("AGUI.WPF/1.0.0");
                http.DefaultRequestHeaders.Accept.ParseAdd("application/vnd.github+json");
                if (!string.IsNullOrWhiteSpace(token))
                {
                    http.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", token);
                }

                var owner = repo.Split('/')[0];
                var name = repo.Split('/')[1];
                var apiUrl = $"https://api.github.com/repos/{owner}/{name}/releases/latest";

                using var resp = await http.GetAsync(apiUrl);
                string? downloadUrl = null;
                if (resp.IsSuccessStatusCode)
                {
                    var json = await resp.Content.ReadAsStringAsync();
                    using var doc = JsonDocument.Parse(json);
                    if (doc.RootElement.TryGetProperty("assets", out var assets) && assets.ValueKind == JsonValueKind.Array)
                    {
                        foreach (var asset in assets.EnumerateArray())
                        {
                            var nameProp = asset.TryGetProperty("name", out var n) ? n.GetString() ?? string.Empty : string.Empty;
                            var urlProp = asset.TryGetProperty("browser_download_url", out var u) ? u.GetString() ?? string.Empty : string.Empty;
                            if (!string.IsNullOrEmpty(nameProp) && !string.IsNullOrEmpty(urlProp))
                            {
                                if (!string.IsNullOrEmpty(assetMatch))
                                {
                                    if (nameProp.IndexOf(assetMatch, StringComparison.OrdinalIgnoreCase) >= 0)
                                    {
                                        downloadUrl = urlProp;
                                        break;
                                    }
                                }
                                else if (nameProp.EndsWith(".exe", StringComparison.OrdinalIgnoreCase))
                                {
                                    downloadUrl = urlProp;
                                    break;
                                }
                            }
                        }
                    }
                }
                else
                {
                    var listUrl = $"https://api.github.com/repos/{owner}/{name}/releases";
                    using var respList = await http.GetAsync(listUrl);
                    if (!respList.IsSuccessStatusCode)
                    {
                        PostUpdateResult(core, false, error: $"GitHub API failed: latest={(int)resp.StatusCode}, list={(int)respList.StatusCode}");
                        return;
                    }
                    var listJson = await respList.Content.ReadAsStringAsync();
                    using var listDoc = JsonDocument.Parse(listJson);
                    if (listDoc.RootElement.ValueKind != JsonValueKind.Array || listDoc.RootElement.GetArrayLength() == 0)
                    {
                        PostUpdateResult(core, false, error: "no releases available");
                        return;
                    }
                    foreach (var rel in listDoc.RootElement.EnumerateArray())
                    {
                        var isDraft = rel.TryGetProperty("draft", out var d) && d.GetBoolean();
                        var isPre = rel.TryGetProperty("prerelease", out var p) && p.GetBoolean();
                        if (isDraft || isPre) continue;
                        if (rel.TryGetProperty("assets", out var relAssets) && relAssets.ValueKind == JsonValueKind.Array)
                        {
                            foreach (var asset in relAssets.EnumerateArray())
                            {
                                var nameProp = asset.TryGetProperty("name", out var n) ? n.GetString() ?? string.Empty : string.Empty;
                                var urlProp = asset.TryGetProperty("browser_download_url", out var u) ? u.GetString() ?? string.Empty : string.Empty;
                                if (!string.IsNullOrEmpty(nameProp) && !string.IsNullOrEmpty(urlProp))
                                {
                                    if (!string.IsNullOrEmpty(assetMatch))
                                    {
                                        if (nameProp.IndexOf(assetMatch, StringComparison.OrdinalIgnoreCase) >= 0)
                                        {
                                            downloadUrl = urlProp;
                                            break;
                                        }
                                    }
                                    else if (nameProp.EndsWith(".exe", StringComparison.OrdinalIgnoreCase))
                                    {
                                        downloadUrl = urlProp;
                                        break;
                                    }
                                }
                            }
                        }
                        if (!string.IsNullOrEmpty(downloadUrl)) break;
                    }
                }
                if (string.IsNullOrEmpty(downloadUrl))
                {
                    PostUpdateResult(core, false, error: "no matching .exe asset found");
                    return;
                }

                PostUpdateProgress(core, "开始下载安装包...");
                var tmpDir = Path.Combine(Path.GetTempPath(), "AgenticRAG", "updates");
                Directory.CreateDirectory(tmpDir);
                var fileName = Path.GetFileName(new Uri(downloadUrl).LocalPath);
                var savePath = Path.Combine(tmpDir, fileName);
                using (var respDl = await http.GetAsync(downloadUrl, HttpCompletionOption.ResponseHeadersRead))
                {
                    if (!respDl.IsSuccessStatusCode)
                    {
                        PostUpdateResult(core, false, error: $"download failed: {(int)respDl.StatusCode}");
                        return;
                    }
                    var total = respDl.Content.Headers.ContentLength;
                    using (var inStream = await respDl.Content.ReadAsStreamAsync())
                    using (var fs = new FileStream(savePath, FileMode.Create, FileAccess.Write, FileShare.None))
                    {
                        var buffer = new byte[81920];
                        long readTotal = 0;
                        while (true)
                        {
                            var read = await inStream.ReadAsync(buffer, 0, buffer.Length);
                            if (read == 0) break;
                            await fs.WriteAsync(buffer, 0, read);
                            readTotal += read;
                            if (total.HasValue && total.Value > 0)
                            {
                                var percent = (int)(readTotal * 100 / total.Value);
                                PostUpdateProgressPercent(core, percent);
                            }
                        }
                    }
                }

                PostUpdateProgress(core, "下载完成");
                PostUpdateResult(core, true, message: "downloaded", path: savePath);
            }
            catch (Exception ex)
            {
                PostUpdateResult(core, false, error: ex.Message);
            }
        }

        /// <summary>
        /// 执行已下载的安装程序（前端确认后触发）
        /// </summary>
        private void HandleAppUpdateExecute(System.Text.Json.JsonElement obj, CoreWebView2 core)
        {
            try
            {
                if (!obj.TryGetProperty("payload", out var payload))
                {
                    PostUpdateResult(core, false, error: "missing payload");
                    return;
                }
                var path = payload.TryGetProperty("path", out var p) ? p.GetString() ?? string.Empty : string.Empty;
                var args = payload.TryGetProperty("args", out var a) ? a.GetString() ?? string.Empty : string.Empty;
                if (string.IsNullOrWhiteSpace(path) || !File.Exists(path))
                {
                    PostUpdateResult(core, false, error: "invalid installer path");
                    return;
                }
                var startInfo = new ProcessStartInfo
                {
                    FileName = path,
                    UseShellExecute = true,
                    Arguments = args ?? string.Empty
                };
                var proc = Process.Start(startInfo);
                if (proc != null)
                {
                    PostUpdateResult(core, true, message: "installer started");
                }
                else
                {
                    PostUpdateResult(core, false, error: "failed to start installer");
                }
            }
            catch (Exception ex)
            {
                PostUpdateResult(core, false, error: ex.Message);
            }
        }

        /// <summary>
        /// 发送更新进度消息到前端
        /// </summary>
        private void PostUpdateProgress(CoreWebView2 core, string message)
        {
            var resp = new { type = "app_update_progress", message };
            core?.PostWebMessageAsJson(System.Text.Json.JsonSerializer.Serialize(resp));
        }

        /// <summary>
        /// 发送更新结果消息到前端
        /// </summary>
        private void PostUpdateResult(CoreWebView2 core, bool success, string? message = null, string? error = null, string? path = null)
        {
            var resp = new { type = "app_update_result", success, message, error, path };
            core?.PostWebMessageAsJson(System.Text.Json.JsonSerializer.Serialize(resp));
        }

        /// <summary>
        /// 发送下载百分比进度到前端
        /// </summary>
        private void PostUpdateProgressPercent(CoreWebView2 core, int percent)
        {
            if (percent < 0) percent = 0; if (percent > 100) percent = 100;
            var resp = new { type = "app_update_progress", percent };
            core?.PostWebMessageAsJson(System.Text.Json.JsonSerializer.Serialize(resp));
        }

  
    }
}
