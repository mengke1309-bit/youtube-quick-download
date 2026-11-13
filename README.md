# YouTube 一键下载（Chrome 扩展）

鼠标悬停在 YouTube 视频缩略图上，右上角立刻浮现一个下载按钮，点一下就能把这个视频以**最高画质**下载到本地。

![原理](https://img.shields.io/badge/Chrome-MV3-blue) ![Python](https://img.shields.io/badge/Python-3.8%2B-3776ab)

## 效果

- 悬停缩略图 → 右上角出现圆形下载按钮（悬停变红放大）
- 点击 → 后台静默下载，页面底部弹出「已开始下载」提示
- 支持普通视频、Shorts、播放列表里的单个视频
- 下载画质：`bv*+ba/b`（最佳视频流 + 最佳音频流合并为 MP4）
- 自动复用 Windows 系统代理

## 原理

浏览器的页面脚本没法直接调 `yt-dlp`，所以拆成两部分：

```
YouTube 页面
   │  悬停缩略图，点下载按钮
   ▼
Chrome 扩展 (MV3)          extension/
   │  POST /download {url}
   ▼
本地桥接服务 127.0.0.1:17890   bridge/yt_bridge.pyw
   │  subprocess
   ▼
yt-dlp  ──►  下载\YouTube\xxx.mp4
```

扩展只负责「发现视频」和「发请求」，真正干活的是本地这个小服务。

## 安装

### 1. 启动本地下载服务

双击 `bridge/启动下载服务.bat`（无窗口后台运行）。

开机自启（可选）：`Win+R` → 输入 `shell:startup` → 回车，把该 bat 的快捷方式丢进去。

验证：浏览器访问 <http://127.0.0.1:17890/health>，返回 `{"ok": true, ...}` 即正常。

### 2. 加载扩展

1. 打开 Chrome，地址栏输入 `chrome://extensions`
2. 打开右上角「开发者模式」
3. 点「加载已解压的扩展程序」
4. 选择本项目的 `extension` 文件夹

### 3. 使用

打开 YouTube，鼠标悬停在任意视频缩略图上，点右上角按钮即可。

## 依赖

| 组件 | 作用 | 是否必需 |
| --- | --- | --- |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | 解析与下载 | 必需 |
| [ffmpeg](https://ffmpeg.org/) | 合并音视频轨（1080p 以上需要） | 强烈建议 |
| [deno](https://deno.com/) | JS 挑战解密 | 可选 |
| Python 3.8+ | 运行桥接服务 | 必需 |

程序会在 `PATH` 和 winget 安装目录里自动查找这些工具，找不到时回退到脚本同目录。

## 目录结构

```
extension/            Chrome 扩展
  manifest.json       MV3 配置
  content.js          悬停注入按钮 + 点击上报
  content.css         按钮与提示条样式
  background.js       与本地服务通信
bridge/
  yt_bridge.pyw       本地 HTTP 服务（127.0.0.1:17890）
  启动下载服务.bat    一键启动
安装说明.txt
```

## 常见问题

**点了按钮提示「下载服务没启动」**
桥接服务没跑，双击 `bridge/启动下载服务.bat`。

**按钮不出现**
YouTube 改版可能导致选择器失效，先刷新页面；仍不行请提 issue。

**下载失败**
看 `bridge/bridge.log` 里的日志，一般是 yt-dlp 版本过旧：
```bash
yt-dlp -U
```

## 注意

仅供个人学习与备份使用。请遵守 YouTube 服务条款及当地版权法规，不要下载或传播无授权的受版权保护内容。
