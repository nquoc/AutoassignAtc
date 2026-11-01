document.addEventListener('DOMContentLoaded', async () => {
  const statusDot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');
  const cookieCount = document.getElementById('cookieCount');
  const badgeSession = document.getElementById('badgeSession');
  const badgeUser = document.getElementById('badgeUser');
  const badgeKvSession = document.getElementById('badgeKvSession');
  const alertBox = document.getElementById('alertBox');
  const cookiePreview = document.getElementById('cookiePreview');
  const btnCopy = document.getElementById('btnCopy');
  const btnDownload = document.getElementById('btnDownload');
  const btnOpenCrm = document.getElementById('btnOpenCrm');
  const toast = document.getElementById('toast');
  const csrfInfo = document.getElementById('csrfInfo');

  let fullCookieString = '';
  let extractedCsrf = '';

  // 1. Quét toàn bộ Cookie từ các nguồn của KiotViet
  async function fetchAllKiotVietCookies() {
    const cookieMap = new Map();

    const targets = [
      { url: "https://kvcrm.kiotviet.vn/" },
      { url: "https://kvcrm.kiotviet.vn/index.php" },
      { url: "http://kvcrm.kiotviet.vn/" },
      { domain: "kvcrm.kiotviet.vn" },
      { domain: ".kvcrm.kiotviet.vn" },
      { domain: "kiotviet.vn" },
      { domain: ".kiotviet.vn" },
      {} // Quét toàn bộ theo host_permissions của extension
    ];

    for (const target of targets) {
      try {
        const list = await new Promise(resolve => {
          chrome.cookies.getAll(target, cookies => {
            if (chrome.runtime.lastError) resolve([]);
            else resolve(cookies || []);
          });
        });

        if (Array.isArray(list)) {
          for (const c of list) {
            if (!c || !c.name) continue;
            const domain = (c.domain || "").toLowerCase();
            const name = (c.name || "");
            const nameLower = name.toLowerCase();

            if (
              domain.includes("kiotviet.vn") ||
              nameLower.includes("kvcrm") ||
              nameLower.includes("phpsessid") ||
              name === "current_user" ||
              nameLower.includes("kv-session") ||
              nameLower.includes("kvas")
            ) {
              // Ưu tiên cookie của domain kvcrm nếu trùng tên
              if (!cookieMap.has(name) || (c.domain && c.domain.includes("kvcrm"))) {
                cookieMap.set(name, c.value);
              }
            }
          }
        }
      } catch (err) {
        console.warn("Lỗi đọc cookie:", err);
      }
    }

    // Quét thêm từ active tab nếu là kiotviet
    try {
      const tabs = await new Promise(res => chrome.tabs.query({ active: true, currentWindow: true }, res));
      if (tabs && tabs[0] && tabs[0].url && tabs[0].url.includes("kiotviet.vn")) {
        const tabCookies = await new Promise(res => chrome.cookies.getAll({ url: tabs[0].url }, res));
        if (Array.isArray(tabCookies)) {
          for (const c of tabCookies) {
            if (c && c.name) cookieMap.set(c.name, c.value);
          }
        }
      }
    } catch (e) {}

    return cookieMap;
  }

  // 2. Thử lấy CSRF Token từ Tab hoặc background fetch
  async function fetchCsrfToken() {
    try {
      const tabs = await new Promise(res => chrome.tabs.query({ active: true, currentWindow: true }, res));
      if (tabs && tabs[0] && tabs[0].url && tabs[0].url.includes("kvcrm.kiotviet.vn")) {
        try {
          const results = await chrome.scripting.executeScript({
            target: { tabId: tabs[0].id },
            func: () => window.csrfMagicToken || document.querySelector('input[name="__vtrftk"]')?.value || ""
          });
          if (results && results[0] && results[0].result) {
            return results[0].result;
          }
        } catch (e) {}
      }
      
      // Fallback: fetch nhẹ trang CRM để bóc tách token
      const resp = await fetch("https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=List&viewname=16309", { credentials: "include" });
      const html = await resp.text();
      const match = html.match(/csrfMagicToken\s*=\s*["']([^"']+)["']/) || 
                    html.match(/name=["']__vtrftk["']\s+value=["']([^"']+)["']/) || 
                    html.match(/(sid:[a-zA-Z0-9,]+)/);
      if (match) return match[1];
    } catch (e) {}
    return "";
  }

  // 3. Khởi tạo và phân tích dữ liệu Cookie
  try {
    const cookieMap = await fetchAllKiotVietCookies();
    
    // Kiểm tra các cookie cốt lõi
    let phpsessidKey = null;
    for (const k of cookieMap.keys()) {
      if (k === "KVCRM_PHPSESSID" || k.toLowerCase().includes("phpsessid")) {
        phpsessidKey = k;
        break;
      }
    }
    const hasSession = !!phpsessidKey;
    const hasUser = cookieMap.has("current_user");
    const hasKvSession = cookieMap.has("kv-session") || cookieMap.has("kvas-uuid");

    // Sắp xếp các cookie quan trọng lên đầu chuỗi
    const keyPriority = ["KVCRM_PHPSESSID", "current_user", "kv-session", "kv-session-d", "kvas-uuid", "kvas-uuid-d", "gkvas-uuid", "gkvas-uuid-d"];
    const sortedEntries = Array.from(cookieMap.entries()).sort((a, b) => {
      const idxA = keyPriority.indexOf(a[0]);
      const idxB = keyPriority.indexOf(b[0]);
      if (idxA !== -1 && idxB !== -1) return idxA - idxB;
      if (idxA !== -1) return -1;
      if (idxB !== -1) return 1;
      return a[0].localeCompare(b[0]);
    });

    fullCookieString = sortedEntries.map(([k, v]) => `${k}=${v}`).join('; ');
    cookieCount.textContent = `${cookieMap.size} cookies`;

    // Cập nhật trạng thái hiển thị
    if (hasSession && (hasUser || hasKvSession)) {
      statusDot.className = 'dot online';
      statusText.textContent = 'Phiên CRM Hợp Lệ (Chuẩn 100%)';
      alertBox.style.display = 'none';
      btnCopy.classList.remove('disabled');

      badgeSession.className = 'badge ok';
      badgeSession.textContent = `✓ ${phpsessidKey}: ${cookieMap.get(phpsessidKey).slice(0, 8)}...`;

      if (hasUser) {
        badgeUser.className = 'badge ok';
        badgeUser.textContent = `✓ User: ${cookieMap.get('current_user')}`;
      } else {
        badgeUser.className = 'badge missing';
        badgeUser.textContent = '✗ User: Trống';
      }

      badgeKvSession.className = 'badge ok';
      badgeKvSession.textContent = '✓ SSO: Sẵn sàng';
    } else if (cookieMap.size > 0) {
      statusDot.className = 'dot warning';
      statusText.textContent = 'Thiếu Session CRM (PHPSESSID)';
      alertBox.style.display = 'block';

      badgeSession.className = 'badge missing';
      badgeSession.textContent = '✗ PHPSESSID: Thiếu';

      badgeUser.className = hasUser ? 'badge ok' : 'badge missing';
      badgeUser.textContent = hasUser ? `✓ User: ${cookieMap.get('current_user')}` : '✗ User: Thiếu';

      badgeKvSession.className = hasKvSession ? 'badge ok' : 'badge missing';
      badgeKvSession.textContent = hasKvSession ? '✓ SSO: Đã tìm thấy' : '✗ SSO: Thiếu';
    } else {
      statusDot.className = 'dot offline';
      statusText.textContent = 'Chưa đăng nhập CRM';
      alertBox.style.display = 'block';
      btnCopy.classList.add('disabled');

      badgeSession.className = 'badge missing';
      badgeSession.textContent = '✗ PHPSESSID: Chưa có';
      badgeUser.className = 'badge missing';
      badgeUser.textContent = '✗ User: Chưa có';
      badgeKvSession.className = 'badge missing';
      badgeKvSession.textContent = '✗ SSO: Chưa có';
    }

    cookiePreview.value = fullCookieString || "Không tìm thấy cookie CRM nào. Vui lòng mở trang kvcrm.kiotviet.vn và đăng nhập trước!";

    // Lấy CSRF ngầm
    fetchCsrfToken().then(token => {
      if (token) {
        extractedCsrf = token;
        csrfInfo.textContent = `(CSRF: ${token.slice(0, 10)}...)`;
      }
    });

  } catch (err) {
    statusDot.className = 'dot offline';
    statusText.textContent = 'Lỗi truy cập: ' + err.message;
    cookiePreview.value = 'Lỗi: ' + err.message;
  }

  // 4. Sự kiện Sao chép (1-Click)
  btnCopy.addEventListener('click', async () => {
    if (!fullCookieString) return;
    try {
      await navigator.clipboard.writeText(fullCookieString);
      toast.style.display = 'block';
      setTimeout(() => { toast.style.display = 'none'; }, 3000);
    } catch (e) {
      cookiePreview.select();
      document.execCommand('copy');
      toast.style.display = 'block';
      setTimeout(() => { toast.style.display = 'none'; }, 3000);
    }
  });

  // 5. Sự kiện Tải file cookie.txt
  btnDownload.addEventListener('click', () => {
    if (!fullCookieString) {
      alert("Chưa có cookie để lưu file!");
      return;
    }
    const blob = new Blob([fullCookieString], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "cookie.txt";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.textContent = "💾 Đã tải file cookie.txt về máy thành công!";
    toast.style.display = 'block';
    setTimeout(() => {
      toast.textContent = "🎉 Đã copy Cookie CRM chuẩn vào bộ nhớ tạm!";
      toast.style.display = 'none';
    }, 3000);
  });

  // 6. Mở hoặc chuyển sang Tab CRM
  btnOpenCrm.addEventListener('click', async () => {
    try {
      const tabs = await new Promise(res => chrome.tabs.query({}, res));
      const crmTab = tabs.find(t => t.url && t.url.includes("kvcrm.kiotviet.vn"));
      if (crmTab) {
        chrome.tabs.update(crmTab.id, { active: true });
        chrome.windows.update(crmTab.windowId, { focused: true });
      } else {
        chrome.tabs.create({ url: "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=List&viewname=16309" });
      }
      window.close();
    } catch (e) {
      window.open("https://kvcrm.kiotviet.vn/", "_blank");
    }
  });
});
