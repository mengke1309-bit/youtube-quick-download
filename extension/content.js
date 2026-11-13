// YouTube 页面注入脚本：悬停缩略图 -> 显示下载按钮 -> 点击发往后台
(function () {
  "use strict";

  const BTN_CLASS = "ytdl-hover-btn";
  let currentThumb = null; // 当前附着按钮的 ytd-thumbnail

  // ---------- 下载按钮 ----------
  const btn = document.createElement("button");
  btn.className = BTN_CLASS;
  btn.type = "button";
  btn.title = "下载这个视频（最高画质）";
  btn.innerHTML =
    '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" ' +
    'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M12 3v12"/><path d="m7 11 5 5 5-5"/><path d="M4 21h16"/></svg>';
  btn.style.display = "none";
  document.documentElement.appendChild(btn);

  // ---------- 提示条 ----------
  let toastTimer = null;
  const toast = document.createElement("div");
  toast.className = "ytdl-toast";
  document.documentElement.appendChild(toast);

  function showToast(text, isError) {
    toast.textContent = text;
    toast.classList.toggle("ytdl-toast-error", !!isError);
    toast.classList.add("ytdl-toast-show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("ytdl-toast-show"), 2600);
  }

  // ---------- 从缩略图找视频链接 ----------
  function findVideoUrl(thumb) {
    // 优先：缩略图内的链接
    let a = thumb.querySelector('a#thumbnail[href], a[href*="watch?v="], a[href*="/shorts/"], a[href*="youtu.be"]');
    // 兜底：向父级找渲染容器里的链接（新版 lockup 布局链接常在缩略图外）
    let scope = thumb;
    for (let i = 0; i < 5 && !a && scope; i++) {
      scope = scope.parentElement;
      if (scope) {
        a = scope.querySelector('a#thumbnail[href], a[href*="watch?v="], a[href*="/shorts/"], a[href*="youtu.be"]');
      }
    }
    if (!a) return null;
    const href = a.href;
    // 规整为干净链接，去掉多余的列表/跟踪参数
    const v = href.match(/[?&]v=([\w-]{6,})/);
    if (v) return "https://www.youtube.com/watch?v=" + v[1];
    const s = href.match(/\/shorts\/([\w-]{6,})/);
    if (s) return "https://www.youtube.com/shorts/" + s[1];
    const b = href.match(/youtu\.be\/([\w-]{6,})/);
    if (b) return "https://youtu.be/" + b[1];
    return href;
  }

  function attachTo(thumb) {
    if (currentThumb === thumb) return;
    currentThumb = thumb;
    thumb.appendChild(btn);
    btn.style.display = "flex";
  }

  function detach() {
    currentThumb = null;
    btn.style.display = "none";
  }

  // ---------- 悬停侦测（事件委托，兼容 YouTube SPA 无刷新跳转） ----------
  document.addEventListener("mouseover", (e) => {
    const thumb = e.target.closest && e.target.closest("ytd-thumbnail, yt-thumbnail-view-model");
    if (thumb) attachTo(thumb);
  }, true);

  document.addEventListener("mouseout", (e) => {
    if (!currentThumb) return;
    const to = e.relatedTarget;
    // 移出整个缩略图区域才隐藏（在缩略图内部移动、移到按钮上都不隐藏）
    if (!to || !currentThumb.contains(to)) detach();
  }, true);

  // ---------- 点击下载 ----------
  btn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();

    if (!currentThumb) return;
    const url = findVideoUrl(currentThumb);
    if (!url) {
      showToast("没识别出视频链接", true);
      return;
    }

    btn.classList.add("ytdl-btn-busy");
    chrome.runtime.sendMessage({ type: "ytdl-download", url: url }, (resp) => {
      btn.classList.remove("ytdl-btn-busy");
      if (chrome.runtime.lastError) {
        showToast("插件通信失败，请刷新页面", true);
        return;
      }
      if (resp && resp.ok) {
        showToast("已开始下载（最高画质），文件在 下载\\YouTube 目录");
      } else if (resp && resp.error === "bridge-offline") {
        showToast("下载服务没启动：请先双击 bridge 文件夹里的「启动下载服务.bat」", true);
      } else {
        showToast("下载失败：" + ((resp && resp.error) || "未知错误"), true);
      }
    });
  }, true);
})();
