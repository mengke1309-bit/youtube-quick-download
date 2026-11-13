# -*- coding: utf-8 -*-
"""YouTube 一键下载 - 本地桥接服务
监听 127.0.0.1:17890，接收浏览器插件发来的视频链接，
直接调用 yt-dlp 以最高画质下载到 下载\\YouTube 目录。
依赖：yt-dlp（必需）+ ffmpeg（合并音视频，可选）+ deno（JS 解密，可选）
"""
import json
import os
import re
import shutil
import subprocess
import threading
import time
import winreg
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 17890
DEFAULT_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "YouTube")
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bridge.log")
URL_RE = re.compile(r"^https?://(www\.|m\.)?(youtube\.com/(watch|shorts)|youtu\.be/)")


def log(text):
    line = "[%s] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), text)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass


def find_tool(name):
    """在 PATH 和 winget 安装位置找真实可执行文件（跳过 WinGet Links 垫片）"""
    p = shutil.which(name)
    if p and "WinGet\\Links" not in p and "WinGet/Links" not in p:
        return p
    local = os.environ.get("LOCALAPPDATA", "")
    pkg_root = os.path.join(local, "Microsoft", "WinGet", "Packages")
    found = []
    if os.path.isdir(pkg_root):
        for root, _dirs, files in os.walk(pkg_root):
            if name + ".exe" in files:
                found.append(os.path.join(root, name + ".exe"))
    if found:
        found.sort(key=lambda x: ("yt-dlp" not in x, x))
        return found[0]
    side = os.path.join(os.path.dirname(os.path.abspath(__file__)), name + ".exe")
    if os.path.isfile(side):
        return side
    return p


def get_system_proxy():
    """读取 Windows 系统代理设置，返回 http://host:port 或 None"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        )
        enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
        server, _ = winreg.QueryValueEx(key, "ProxyServer")
        winreg.CloseKey(key)
        if not enable or not server:
            return None
        if "=" in server:
            for part in server.split(";"):
                if part.strip().startswith("https="):
                    return "http://" + part.split("=", 1)[1].strip()
            first = server.split(";")[0]
            return "http://" + first.split("=", 1)[1].strip()
        return "http://" + server.strip()
    except OSError:
        return None


YT_DLP = find_tool("yt-dlp")
FFMPEG = find_tool("ffmpeg")
DENO = find_tool("deno")
PROXY = get_system_proxy()


def download(url):
    """后台线程执行 yt-dlp 下载"""
    if not YT_DLP:
        log("[!] 未找到 yt-dlp，无法下载: " + url)
        return
    os.makedirs(DEFAULT_DIR, exist_ok=True)
    cmd = [
        YT_DLP,
        "-f", "bv*+ba/b",
        "--merge-output-format", "mp4",
        "--newline",
        "--no-playlist",
        "-o", os.path.join(DEFAULT_DIR, "%(title)s.%(ext)s"),
    ]
    if FFMPEG:
        cmd += ["--ffmpeg-location", os.path.dirname(FFMPEG)]
    if PROXY:
        cmd += ["--proxy", PROXY]
    cmd.append(url)

    env = os.environ.copy()
    extra = [os.path.dirname(p) for p in (YT_DLP, FFMPEG, DENO) if p]
    env["PATH"] = os.pathsep.join(extra + [env.get("PATH", "")])

    log("[>] 开始下载: " + url)
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        code = proc.wait()
        log(("[v] 完成: " if code == 0 else "[x] 失败(%d): " % code) + url)
    except OSError as ex:
        log("[x] 启动 yt-dlp 失败: %s (%s)" % (ex, url))


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/health"):
            self._json(200, {"ok": True, "yt_dlp": bool(YT_DLP), "ffmpeg": bool(FFMPEG)})
        else:
            self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        if not self.path.startswith("/download"):
            self._json(404, {"ok": False, "error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            url = (data.get("url") or "").strip()
        except (ValueError, UnicodeDecodeError):
            self._json(400, {"ok": False, "error": "请求格式错误"})
            return
        if not URL_RE.match(url):
            self._json(400, {"ok": False, "error": "不是有效的 YouTube 链接"})
            return
        if not YT_DLP:
            self._json(500, {"ok": False, "error": "本机未安装 yt-dlp"})
            return
        threading.Thread(target=download, args=(url,), daemon=True).start()
        self._json(200, {"ok": True})

    def log_message(self, fmt, *args):
        pass  # 静默，不走 stderr


if __name__ == "__main__":
    os.makedirs(DEFAULT_DIR, exist_ok=True)
    log("=== 桥接服务启动 :%d (yt-dlp=%s ffmpeg=%s proxy=%s) ==="
        % (PORT, bool(YT_DLP), bool(FFMPEG), PROXY or "无"))
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
