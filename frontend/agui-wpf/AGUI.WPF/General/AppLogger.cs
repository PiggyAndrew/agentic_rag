using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;

namespace WPF_ArchiPlaning
{
    internal static class AppLogger
    {
        private static readonly object SyncRoot = new();
        private static int _initialized;
        private static string? _logDirectoryPath;
        private static string? _logFilePath;

        /// <summary>
        /// 初始化日志系统（多次调用安全），创建日志目录并写入启动信息
        /// </summary>
        public static void Initialize()
        {
            if (Interlocked.Exchange(ref _initialized, 1) == 1) return;

            try
            {
                var appName = Assembly.GetEntryAssembly()?.GetName().Name ?? "BUD Sustainable Building Designer";
                var localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                _logDirectoryPath = Path.Combine(localAppData, appName, "logs");
                Directory.CreateDirectory(_logDirectoryPath);

                var now = DateTimeOffset.Now;
                var pid = Environment.ProcessId;
                var fileName = $"{now:yyyyMMdd_HHmmss}_pid{pid}.log";
                _logFilePath = Path.Combine(_logDirectoryPath, fileName);

                Info("Logger initialized");
                Info(BuildRuntimeSummary());
            }
            catch
            {
                _logDirectoryPath = null;
                _logFilePath = null;
            }
        }

        /// <summary>
        /// 记录 Info 级别日志
        /// </summary>
        public static void Info(string message) => Write("INFO", message, null);

        /// <summary>
        /// 记录 Warning 级别日志
        /// </summary>
        public static void Warn(string message) => Write("WARN", message, null);

        /// <summary>
        /// 记录 Error 级别日志（支持附带异常堆栈）
        /// </summary>
        public static void Error(string message, Exception? ex = null) => Write("ERROR", message, ex);

        /// <summary>
        /// 获取本次运行的日志文件路径（可能为空）
        /// </summary>
        public static string? GetLogFilePath() => _logFilePath;

        /// <summary>
        /// 尝试将日志写入文件（任何异常都不会向外抛出）
        /// </summary>
        public static void Write(string level, string message, Exception? ex)
        {
            try
            {
                if (_logFilePath == null) Initialize();
                if (_logFilePath == null) return;

                var ts = DateTimeOffset.Now.ToString("yyyy-MM-dd HH:mm:ss.fff");
                var pid = Environment.ProcessId;
                var tid = Environment.CurrentManagedThreadId;
                var line = $"{ts} [pid:{pid} tid:{tid}] {level} {message}";
                if (ex != null) line += $"{Environment.NewLine}{ex}";
                line += Environment.NewLine;

                lock (SyncRoot)
                {
                    File.AppendAllText(_logFilePath, line, Encoding.UTF8);
                }
            }
            catch
            {
            }
        }

        private static string BuildRuntimeSummary()
        {
            var entry = Assembly.GetEntryAssembly();
            var name = entry?.GetName();
            var version = name?.Version?.ToString() ?? "unknown";
            var fileVersion = entry == null ? "unknown" : (entry.GetCustomAttribute<AssemblyFileVersionAttribute>()?.Version ?? "unknown");
            var os = Environment.OSVersion.VersionString;
            var arch = RuntimeInformation.OSArchitecture.ToString();
            var processArch = RuntimeInformation.ProcessArchitecture.ToString();
            var framework = RuntimeInformation.FrameworkDescription;
            var isAdmin = false;
            try
            {
                using var identity = System.Security.Principal.WindowsIdentity.GetCurrent();
                var principal = new System.Security.Principal.WindowsPrincipal(identity);
                isAdmin = principal.IsInRole(System.Security.Principal.WindowsBuiltInRole.Administrator);
            }
            catch
            {
            }

            return $"AppVersion={version}, FileVersion={fileVersion}, OS={os}, OSArch={arch}, ProcessArch={processArch}, Framework={framework}, IsAdmin={isAdmin}, BaseDir={AppDomain.CurrentDomain.BaseDirectory}";
        }
    }
}
