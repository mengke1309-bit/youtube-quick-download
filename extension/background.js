// 后台服务：负责与本地桥接服务 (127.0.0.1:17890) 通信
// 由 service worker 发起请求，避开页面混合内容与跨域限制
const BRIDGE = "http://127.0.0.1:17890";

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg || msg.type !== "ytdl-download") return false;

  fetch(BRIDGE + "/download", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url: msg.url })
  })
    .then(async (res) => {
      if (res.ok) {
        sendResponse({ ok: true });
      } else {
        let detail = "";
        try { detail = (await res.json()).error || ""; } catch (e) { /* ignore */ }
        sendResponse({ ok: false, error: detail || ("HTTP " + res.status) });
      }
    })
    .catch(() => {
      sendResponse({ ok: false, error: "bridge-offline" });
    });

  return true; // 异步响应
});
