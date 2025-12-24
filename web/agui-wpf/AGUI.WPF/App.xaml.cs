using System.Windows;

namespace WPF_ArchiPlaning
{
    /// <summary>
    /// Interaction logic for App.xaml
    /// </summary>
    public partial class App : Application
    {
        /// <summary>
        /// 应用启动事件：初始化日志与全局异常捕获，便于定位“闪退”问题
        /// </summary>
        protected override void OnStartup(StartupEventArgs e)
        {
            base.OnStartup(e);

            AppLogger.Initialize();
            AppLogger.Info("App OnStartup");

            this.DispatcherUnhandledException += (_, args) =>
            {
                AppLogger.Error("DispatcherUnhandledException", args.Exception);
            };

            AppDomain.CurrentDomain.UnhandledException += (_, args) =>
            {
                var ex = args.ExceptionObject as Exception;
                AppLogger.Error($"AppDomain UnhandledException (IsTerminating={args.IsTerminating})", ex);
            };

            TaskScheduler.UnobservedTaskException += (_, args) =>
            {
                AppLogger.Error("TaskScheduler UnobservedTaskException", args.Exception);
                args.SetObserved();
            };
        }

        /// <summary>
        /// 应用退出事件：记录退出并尽量确保最后一段日志落盘
        /// </summary>
        protected override void OnExit(ExitEventArgs e)
        {
            AppLogger.Info($"App OnExit (Code={e.ApplicationExitCode})");
            base.OnExit(e);
        }
    }

}
