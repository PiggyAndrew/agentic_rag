﻿using BUD_Sustainable_Building_Designer;
using EmbedIO;
using Microsoft.Web.WebView2.Core;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using Path = System.IO.Path;

namespace WPF_ArchiPlaning
{
    /// <summary>
    /// Interaction logic for MainWindow.xaml
    /// </summary>
    public partial class MainWindow : Window
    {
        private ExeProcessService _exeProcessService;
        private WebMessageService _webMessageService;

        public MainWindow()
        {
            InitializeComponent();
            AppLogger.Initialize();
            AppLogger.Info($"MainWindow ctor (LogFile={AppLogger.GetLogFilePath() ?? "null"})");
            _exeProcessService = new ExeProcessService();
            _webMessageService = new WebMessageService();
            InitializeWebView();
        }
        /// <summary>
        /// 窗口加载完成事件处理
        /// </summary>
        private void MainWindow_Loaded(object sender, RoutedEventArgs e)
        {
            try
            {
                AppLogger.Info("MainWindow_Loaded: start");
                _exeProcessService.StartWindPathApiProcess();
                AppLogger.Info("MainWindow_Loaded: done");
            }
            catch (Exception ex)
            {
                AppLogger.Error("MainWindow_Loaded: exception", ex);
                throw;
            }
        }

        /// <summary>
        /// 窗口关闭事件处理
        /// </summary>
        private async void MainWindow_Closing(object sender, System.ComponentModel.CancelEventArgs e)
        {
            AppLogger.Info("MainWindow_Closing");
            _exeProcessService.StopWindPathApiProcess();
        }

        private async void InitializeWebView()
        {
            try
            {
                AppLogger.Info("InitializeWebView: start");
                try
                {
                    var ver = CoreWebView2Environment.GetAvailableBrowserVersionString();
                    AppLogger.Info($"WebView2 runtime version: {ver}");
                }
                catch (Exception ex)
                {
                    AppLogger.Warn($"WebView2 runtime version not available: {ex.Message}");
                }

                var env = await CoreWebView2Environment.CreateAsync(null, null, new CoreWebView2EnvironmentOptions());
                await webView.EnsureCoreWebView2Async(env);

                // 配置WebView2设置
                webView.CoreWebView2.Settings.IsWebMessageEnabled = true;
                webView.CoreWebView2.Settings.AreHostObjectsAllowed = true;
                webView.CoreWebView2.Settings.IsScriptEnabled = true;
                webView.CoreWebView2.Settings.AreDevToolsEnabled = true;
                webView.CoreWebView2.Settings.IsZoomControlEnabled = false;
                webView.ZoomFactor = 0.85;

                // 添加本地资源访问权限
                webView.CoreWebView2.SetVirtualHostNameToFolderMapping(
                    "app.local",
                    "dist",
                    CoreWebView2HostResourceAccessKind.Allow
                );

                // 加载网页时使用虚拟主机名
                webView.CoreWebView2.Navigate("http://app.local/index.html");
                webView.CoreWebView2.WebMessageReceived += _webMessageService.CoreWebView2_WebMessageReceived;
                AppLogger.Info("InitializeWebView: done");
            }
            catch (Exception ex)
            {
                AppLogger.Error("InitializeWebView: exception", ex);
                throw;
            }
        }


      
    }

}
