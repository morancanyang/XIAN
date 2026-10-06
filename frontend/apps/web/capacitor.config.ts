import type { CapacitorConfig } from '@capacitor/cli';

/**
 * XIAN · AI Agent 红蓝对抗平台 —— Android 壳配置。
 *
 * 说明：XIAN 为 B/S 架构，APK 内为 WebView 容器 + 已构建的前端静态资源；
 * 后端地址在应用「登录页 → 服务器设置」中运行时指定，不写入安装包。
 */
const config: CapacitorConfig = {
  appId: 'com.xian.redblue',
  appName: 'XIAN',
  webDir: 'dist',
  android: {
    /* 允许向局域网 http 后端发起请求（演示态后端通常无 TLS） */
    allowMixedContent: true,
    webContentsDebuggingEnabled: true
  },
  server: {
    /* 使用 https 方案加载本地资源，避免 file:// 下的 CORS 限制 */
    androidScheme: 'https'
  }
};

export default config;
