using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using WPF_ArchiPlaning;

namespace BUD_Sustainable_Building_Designer
{
    class ExeProcessService
    {

        private Process _windPathApiProcess;
        private readonly string _exeName = "agent_api.exe";

        /// <summary>
        /// 启动 wind_path_api.exe 后台服务（无权限提示、安全启动）
        /// 说明：
        /// - 若存在同名进程，先尝试终止后再启动，避免端口/资源冲突
        /// - 使用非提权方式启动（UseShellExecute=false，移除 Verb=runas）以消除 UAC 弹窗
        /// - 设置工作目录为可写的应用目录，避免权限问题（绑定高位端口、仅监听 127.0.0.1）建议在服务内部实现
        /// </summary>
        public async void StartWindPathApiProcess()
        {
            try
            {
                string exePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, _exeName);
                AppLogger.Info($"StartWindPathApiProcess: exePath={exePath}");

                if (!File.Exists(exePath))
                {
                    AppLogger.Warn($"StartWindPathApiProcess: agent_api.exe not found: {exePath}");
                    return;
                }

                // 若已有同名进程在运行，则先尝试终止
                var existingProcesses = Process.GetProcessesByName("agent_api");
                if (existingProcesses != null && existingProcesses.Length > 0)
                {
                    var pids = string.Join(",", existingProcesses.Select(p => p.Id));
                    AppLogger.Warn($"StartWindPathApiProcess: found existing processes, killing (pids={pids})");
                    foreach (var proc in existingProcesses)
                    {
                        try
                        {
                            proc.Kill();
                            proc.WaitForExit(3000);
                            AppLogger.Info($"StartWindPathApiProcess: killed pid={proc.Id}");
                        }
                        catch (Exception killEx)
                        {
                            AppLogger.Error($"StartWindPathApiProcess: kill failed pid={proc.Id}", killEx);
                        }
                        try { proc.Dispose(); } catch { }
                    }
                }

                _windPathApiProcess = new Process
                {
                    StartInfo = new ProcessStartInfo
                    {
                        FileName = exePath,
                        UseShellExecute = false, // 以非提权方式启动，避免 UAC 弹窗
                        CreateNoWindow = true,
                        WindowStyle = ProcessWindowStyle.Hidden,
                        RedirectStandardOutput = true,
                        RedirectStandardError = true,
                        RedirectStandardInput = false,
                        WorkingDirectory = AppDomain.CurrentDomain.BaseDirectory
                    },
                    EnableRaisingEvents = true
                };

                // 进程退出事件处理
                _windPathApiProcess.Exited += (sender, e) =>
                {
                    try
                    {
                        var exitCode = _windPathApiProcess?.HasExited == true ? _windPathApiProcess.ExitCode : -1;
                        AppLogger.Warn($"agent_api.exe exited (ExitCode={exitCode})");
                    }
                    catch (Exception ex)
                    {
                        AppLogger.Error("agent_api.exe exited handler exception", ex);
                    }
                };

                _windPathApiProcess.OutputDataReceived += (_, args) =>
                {
                    if (!string.IsNullOrWhiteSpace(args.Data))
                    {
                        AppLogger.Info($"agent_api stdout: {args.Data}");
                    }
                };
                _windPathApiProcess.ErrorDataReceived += (_, args) =>
                {
                    if (!string.IsNullOrWhiteSpace(args.Data))
                    {
                        AppLogger.Warn($"agent_api stderr: {args.Data}");
                    }
                };

                _windPathApiProcess.Start();
                AppLogger.Info($"{_exeName} started (pid={_windPathApiProcess.Id})");
                _windPathApiProcess.BeginOutputReadLine();
                _windPathApiProcess.BeginErrorReadLine();

                // 等待一小段时间确保进程启动
                await Task.Delay(1000);
            }
            catch (Exception ex)
            {
                AppLogger.Error("StartWindPathApiProcess: exception", ex);
            }
        }

 
        public async void StopWindPathApiProcess()
        {
            try
            {
                if (_windPathApiProcess != null && !_windPathApiProcess.HasExited)
                {
                    AppLogger.Info($"StopWindPathApiProcess: stopping pid={_windPathApiProcess.Id}");
                    // 尝试优雅关闭
                    _windPathApiProcess.CloseMainWindow();

                    // 等待进程自行退出
                    if (!_windPathApiProcess.WaitForExit(100))
                    {
                        // 如果3秒内没有退出，强制终止
                        _windPathApiProcess.Kill();
                        await Task.Run(() => _windPathApiProcess.WaitForExit(3000));
                    }

                    _windPathApiProcess.Dispose();
                    AppLogger.Info("StopWindPathApiProcess: stopped");
                }

                // 清理可能残留的同名进程
                var remainingProcesses = Process.GetProcessesByName("wind_path_api");
                foreach (var proc in remainingProcesses)
                {
                    try
                    {
                        AppLogger.Warn($"StopWindPathApiProcess: killing remaining pid={proc.Id}");
                        proc.Kill();
                    }
                    catch { }
                }
            }
            catch (Exception ex)
            {
                AppLogger.Error("StopWindPathApiProcess: exception", ex);
            }
            finally
            {
                _windPathApiProcess = null;
            }
        }
    }
}
