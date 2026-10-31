/**
 * LINE Vault - Front-end Application Logic
 */

document.addEventListener("DOMContentLoaded", () => {
  // Internationalization Dictionary
  const I18N = {
    "zh-TW": {
      langLabel: "English",
      subtitle: "Windows 11 本地對話與防過期媒體管理中心",
      kpiMonitored: "監控聊天室",
      kpiArchived: "永久保存媒體",
      kpiAction: "待辦追蹤",
      btnHelp: "使用說明",
      btnSettings: "金庫與同步設定",
      btnAnalyzeAll: "重新分析全部",
      btnSeedDemo: "載入範例資料",
      chatListTitle: "聊天室清單",
      filterAll: "全部",
      filterMonitored: "監控中",
      filterGroup: "群組",
      filterDirect: "個人",
      filterChatPlaceholder: "過濾聊天室名稱...",
      globalSearchPlaceholder: "搜尋所有對話紀錄、相片、影片與文件檔案...",
      exportReport: "匯出報告",
      autoMonitor: "自動監控 & 防過期備份",
      tabMessages: "對話紀錄",
      tabBookmarks: "收藏訊息",
      tabPhotos: "相片牆",
      tabVideos: "影片庫",
      tabFiles: "檔案櫃",
      dateFrom: "從：",
      dateTo: "至：",
      btnFilter: "篩選",
      btnReset: "重設",
      insightTitle: "AI 智慧分析與行動建議",
      btnRefresh: "🔄 重新分析",
      noChatSelected: "請選擇聊天室",
      noChatSelectedSub: "尚未選擇",
      bookmarkAdded: "已加入訊息收藏！",
      bookmarkRemoved: "已取消訊息收藏",
      actionDone: "待辦事項已標記為完成！",
      actionUndone: "待辦事項已標記為未完成",
      importSuccess: "對話紀錄匯入成功！",
      exportSuccess: "報告已開始下載！",
      txtImportTitle: "📄 匯入 LINE 文字對話紀錄 (.txt)：",
      txtSelectFile: "選擇 .txt 檔案",
      txtStartImport: "開始解析匯入",
      noFileSelected: "未選擇任何檔案",
    },
    "en": {
      langLabel: "繁體中文",
      subtitle: "Windows 11 Local Chat & Anti-Expiration Media Vault",
      kpiMonitored: "Monitored Chats",
      kpiArchived: "Vaulted Media",
      kpiAction: "Action Items",
      btnHelp: "Quick Guide",
      btnSettings: "Settings & Sync",
      btnAnalyzeAll: "Re-analyze All",
      btnSeedDemo: "Load Demo Data",
      chatListTitle: "Chats",
      filterAll: "All",
      filterMonitored: "Monitored",
      filterGroup: "Groups",
      filterDirect: "Direct",
      filterChatPlaceholder: "Filter chat name...",
      globalSearchPlaceholder: "Search messages, photos, videos, and documents...",
      exportReport: "Export Report",
      autoMonitor: "Auto Monitor & Vault",
      tabMessages: "Messages",
      tabBookmarks: "Bookmarks",
      tabPhotos: "Photos",
      tabVideos: "Videos",
      tabFiles: "Files",
      dateFrom: "From:",
      dateTo: "To:",
      btnFilter: "Filter",
      btnReset: "Reset",
      insightTitle: "AI Insights & Action Plan",
      btnRefresh: "🔄 Re-analyze",
      noChatSelected: "Please select a chat",
      noChatSelectedSub: "Not selected",
      bookmarkAdded: "Message added to bookmarks!",
      bookmarkRemoved: "Message removed from bookmarks",
      actionDone: "Action item marked as completed!",
      actionUndone: "Action item marked as pending",
      importSuccess: "Chat history imported successfully!",
      exportSuccess: "Report download started!",
      txtImportTitle: "📄 Import LINE Chat Export (.txt):",
      txtSelectFile: "Select .txt file",
      txtStartImport: "Start Import",
      noFileSelected: "No file selected",
    }
  };

  let currentLang = localStorage.getItem("line_vault_lang") || "zh-TW";
  function t(key) {
    return (I18N[currentLang] && I18N[currentLang][key]) || (I18N["zh-TW"] && I18N["zh-TW"][key]) || key;
  }

  // State
  let currentChatId = null;
  let currentChat = null;
  let activeTab = "messages";
  let chatFilter = "all";
  let chatSearchQuery = "";
  let globalSearchQuery = "";
  let dateFrom = "";
  let dateTo = "";
  let chatsCache = [];

  // DOM Elements
  const btnOpenHelp = document.getElementById("btnOpenHelp");
  const txtBtnHelp = document.getElementById("txtBtnHelp");
  const helpModal = document.getElementById("helpModal");
  const btnCloseHelp = document.getElementById("btnCloseHelp");
  const btnHelpSeedDemo = document.getElementById("btnHelpSeedDemo");
  const btnHelpOpenSettings = document.getElementById("btnHelpOpenSettings");

  const btnThemeToggle = document.getElementById("btnThemeToggle");
  const themeToggleIcon = document.getElementById("themeToggleIcon");
  const themeToggleLabel = document.getElementById("themeToggleLabel");
  const themeOptBtns = document.querySelectorAll(".theme-opt-btn");

  const btnLangToggle = document.getElementById("btnLangToggle");
  const langToggleLabel = document.getElementById("langToggleLabel");
  const i18nSubtitle = document.getElementById("i18nSubtitle");
  const txtBtnSettings = document.getElementById("txtBtnSettings");
  const txtBtnAnalyzeAll = document.getElementById("txtBtnAnalyzeAll");
  const txtBtnSeedDemo = document.getElementById("txtBtnSeedDemo");
  const txtExportReport = document.getElementById("txtExportReport");
  const btnExportReport = document.getElementById("btnExportReport");
  const txtAutoMonitor = document.getElementById("txtAutoMonitor");

  const tabMessagesTxt = document.getElementById("tabMessagesTxt");
  const tabBookmarksTxt = document.getElementById("tabBookmarksTxt");
  const tabPhotosTxt = document.getElementById("tabPhotosTxt");
  const tabVideosTxt = document.getElementById("tabVideosTxt");
  const tabFilesTxt = document.getElementById("tabFilesTxt");

  const kpiMonitoredChats = document.getElementById("kpiMonitoredChats");
  const kpiArchivedMedia = document.getElementById("kpiArchivedMedia");
  const kpiActionItems = document.getElementById("kpiActionItems");
  const globalSearchInput = document.getElementById("globalSearchInput");
  const globalSearchClear = document.getElementById("globalSearchClear");
  const btnAnalyzeAll = document.getElementById("btnAnalyzeAll");
  const btnSeedDemo = document.getElementById("btnSeedDemo");
  const btnRefreshAnalysis = document.getElementById("btnRefreshAnalysis");
  const btnOpenSettings = document.getElementById("btnOpenSettings");

  // Settings Modal Elements
  const settingsModal = document.getElementById("settingsModal");
  const btnCloseSettings = document.getElementById("btnCloseSettings");
  const settingsVaultDir = document.getElementById("settingsVaultDir");
  const settingsFts5 = document.getElementById("settingsFts5");
  const settingsLineStatus = document.getElementById("settingsLineStatus");
  const inputLineDataDir = document.getElementById("inputLineDataDir");
  const inputSyncDays = document.getElementById("inputSyncDays");
  const inputTargetChatName = document.getElementById("inputTargetChatName");
  const btnModalSyncMcp = document.getElementById("btnModalSyncMcp");
  const btnModalScanLine = document.getElementById("btnModalScanLine");
  const toggleAutoPoll = document.getElementById("toggleAutoPoll");

  // GUI Chat History Import Elements
  const txtImportSectionTitle = document.getElementById("txtImportSectionTitle");
  const inputImportChatName = document.getElementById("inputImportChatName");
  const inputChatTxtFile = document.getElementById("inputChatTxtFile");
  const btnTriggerFileSelect = document.getElementById("btnTriggerFileSelect");
  const txtBtnSelectFile = document.getElementById("txtBtnSelectFile");
  const importFileStatus = document.getElementById("importFileStatus");
  const btnImportTxt = document.getElementById("btnImportTxt");
  const txtBtnStartImport = document.getElementById("txtBtnStartImport");

  const chatListContainer = document.getElementById("chatListContainer");
  const chatCountBadge = document.getElementById("chatCountBadge");
  const chatSearchInput = document.getElementById("chatSearchInput");
  const filterTabs = document.querySelectorAll(".pane-left .filter-tab");

  const activeChatAvatar = document.getElementById("activeChatAvatar");
  const activeChatTitle = document.getElementById("activeChatTitle");
  const activeChatSubtitle = document.getElementById("activeChatSubtitle");
  const centerMonitorToggle = document.getElementById("centerMonitorToggle");
  const viewTabs = document.querySelectorAll(".view-tab");

  const dateFilterFrom = document.getElementById("dateFilterFrom");
  const dateFilterTo = document.getElementById("dateFilterTo");
  const btnApplyDateFilter = document.getElementById("btnApplyDateFilter");
  const btnResetFilter = document.getElementById("btnResetFilter");
  const filterStatusText = document.getElementById("filterStatusText");
  const centerContent = document.getElementById("centerContent");

  const urgencyBadge = document.getElementById("urgencyBadge");
  const insightContainer = document.getElementById("insightContainer");
  const toastContainer = document.getElementById("toastContainer");

  function updateLanguageUI() {
    if (langToggleLabel) langToggleLabel.textContent = t("langLabel");
    if (i18nSubtitle) i18nSubtitle.textContent = t("subtitle");
    if (txtBtnHelp) txtBtnHelp.textContent = t("btnHelp");
    if (txtBtnSettings) txtBtnSettings.textContent = t("btnSettings");
    if (txtBtnAnalyzeAll) txtBtnAnalyzeAll.textContent = t("btnAnalyzeAll");
    if (txtBtnSeedDemo) txtBtnSeedDemo.textContent = t("btnSeedDemo");
    if (txtExportReport) txtExportReport.textContent = t("exportReport");
    if (txtAutoMonitor) txtAutoMonitor.textContent = t("autoMonitor");

    if (tabMessagesTxt) tabMessagesTxt.textContent = t("tabMessages");
    if (tabBookmarksTxt) tabBookmarksTxt.textContent = t("tabBookmarks");
    if (tabPhotosTxt) tabPhotosTxt.textContent = t("tabPhotos");
    if (tabVideosTxt) tabVideosTxt.textContent = t("tabVideos");
    if (tabFilesTxt) tabFilesTxt.textContent = t("tabFiles");

    if (globalSearchInput) globalSearchInput.placeholder = t("globalSearchPlaceholder");
    if (chatSearchInput) chatSearchInput.placeholder = t("filterChatPlaceholder");

    if (txtImportSectionTitle) txtImportSectionTitle.textContent = t("txtImportTitle");
    if (txtBtnSelectFile) txtBtnSelectFile.textContent = t("txtSelectFile");
    if (txtBtnStartImport) txtBtnStartImport.textContent = t("txtStartImport");
  }

  // Utilities
  function showToast(message, icon = "✅") {
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(10px)";
      setTimeout(() => toast.remove(), 250);
    }, 2800);
  }

  function formatBytes(bytes) {
    if (!bytes || bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  }

  function formatTime(timestampMs) {
    if (!timestampMs) return "";
    const date = new Date(timestampMs);
    const m = (date.getMonth() + 1).toString().padStart(2, "0");
    const d = date.getDate().toString().padStart(2, "0");
    const h = date.getHours().toString().padStart(2, "0");
    const min = date.getMinutes().toString().padStart(2, "0");
    return `${m}/${d} ${h}:${min}`;
  }

  function highlightText(text, keyword) {
    if (!text) return "";
    if (!keyword) return escapeHtml(text);
    const escapedK = keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const regex = new RegExp(`(${escapedK})`, "gi");
    return escapeHtml(text).replace(regex, '<mark style="background:#fef08a;color:#1e293b;padding:0 2px;border-radius:2px;">$1</mark>');
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  // Copy to clipboard
  window.copySuggestedReply = function(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => {
        showToast("已複製回覆草稿至剪貼簿！", "📋");
      }).catch(() => fallbackCopy(text));
    } else {
      fallbackCopy(text);
    }
  };

  function fallbackCopy(text) {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
      showToast("已複製回覆草稿！", "📋");
    } catch (e) {
      showToast("複製失敗，請手動選取複製", "⚠️");
    }
    document.body.removeChild(ta);
  }

  // API Calls
  async function fetchStatus() {
    try {
      const res = await fetch("/api/status");
      if (!res.ok) return;
      const data = await res.json();
      const stats = data.stats || {};
      kpiMonitoredChats.textContent = stats.monitored_chats || 0;
      kpiArchivedMedia.textContent = stats.archived_media_count || 0;
      kpiActionItems.textContent = stats.action_items_count || 0;
    } catch (err) {
      console.error("fetchStatus error", err);
    }
  }

  async function fetchChats() {
    try {
      let url = "/api/chats?";
      if (chatFilter === "monitored") url += "monitored=1&";
      else if (chatFilter === "group" || chatFilter === "direct") url += `chat_type=${chatFilter}&`;
      if (chatSearchQuery) url += `q=${encodeURIComponent(chatSearchQuery)}&`;

      const res = await fetch(url);
      if (!res.ok) return;
      chatsCache = await res.json();
      renderChatList(chatsCache);
    } catch (err) {
      chatListContainer.innerHTML = '<div class="loading-state">載入聊天室失敗</div>';
    }
  }

  function renderChatList(chats) {
    chatCountBadge.textContent = chats.length;
    if (chats.length === 0) {
      chatListContainer.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">💬</div>
          <h3>尚無聊天室資料</h3>
          <p>點擊下方按鈕即可 1 秒建立完整測試對話、加密相片、影片與 PDF 合約。</p>
          <button class="btn btn-accent btn-sm js-seed-demo-trigger" style="margin-top:12px;">
            <span>✨ 立即載入範例資料</span>
          </button>
        </div>
      `;
      chatListContainer.querySelectorAll(".js-seed-demo-trigger").forEach(btn => {
        btn.addEventListener("click", () => triggerSeedDemo());
      });
      return;
    }

    chatListContainer.innerHTML = "";
    chats.forEach(c => {
      const card = document.createElement("div");
      card.className = `chat-card ${c.chat_id === currentChatId ? "active" : ""}`;
      card.onclick = () => selectChat(c);

      const typeLabel = c.chat_type === "direct" ? "個人" : "群組";
      const monitoredHtml = c.monitored
        ? '<span class="monitored-badge">🛡️ 監控備份中</span>'
        : "";
      const unreadHtml = c.unread_count > 0
        ? `<span class="unread-badge">${c.unread_count}</span>`
        : "";

      card.innerHTML = `
        <div class="chat-card-top">
          <span class="chat-card-title">
            <span>${c.chat_type === "direct" ? "👤" : "👥"}</span>
            <span>${escapeHtml(c.chat_name)}</span>
          </span>
          <span class="chat-card-type-tag">${typeLabel}</span>
        </div>
        <div class="chat-card-bottom">
          <span class="chat-card-time">${formatTime(c.last_message_at)}</span>
          <div class="chat-card-badges">
            ${monitoredHtml}
            ${unreadHtml}
          </div>
        </div>
      `;
      chatListContainer.appendChild(card);
    });
  }

  async function selectChat(chat) {
    currentChatId = chat.chat_id;
    currentChat = chat;

    if (btnExportReport) {
      btnExportReport.disabled = false;
    }

    // Update left pane active class
    document.querySelectorAll(".chat-card").forEach(el => el.classList.remove("active"));
    const activeEl = [...chatListContainer.children].find(
      el => el.querySelector(".chat-card-title span:last-child")?.textContent === chat.chat_name
    );
    if (activeEl) activeEl.classList.add("active");

    // Center header
    activeChatAvatar.textContent = chat.chat_type === "direct" ? "👤" : "👥";
    activeChatTitle.textContent = chat.chat_name;
    activeChatSubtitle.textContent = `${chat.chat_type === "direct" ? "個人對話" : "多人群組"} • ID: ${chat.chat_id}`;
    centerMonitorToggle.disabled = false;
    centerMonitorToggle.checked = Boolean(chat.monitored);

    // Load active tab content
    loadCenterContent();

    // Load AI insights
    loadChatInsight(chat.chat_id);
  }

  function renderOnboardingGuide() {
    centerContent.innerHTML = `
      <div class="onboarding-card">
        <div class="onboarding-header">
          <span class="onboarding-header-icon">🚀</span>
          <div>
            <h3>歡迎使用 LINE Vault — 3 步快速開始與測試指南</h3>
            <p>100% 本地端離線運作 • 防過期媒體永久保存 • AI 重點與待辦提取</p>
          </div>
        </div>
        <div class="onboarding-steps">
          <div class="onboarding-step">
            <div class="step-badge">步驟 1</div>
            <div class="step-content">
              <h4>✨ 一鍵載入測試範例資料（推薦！1 秒立即體驗）</h4>
              <p>首次測試無須準備任何檔案！點擊下方按鈕即可自動建立 4 個擬真聊天室（含客戶交付群、加密 PNG 相片、MP4 影片、PDF 合約與 AI 分析），並自動選取第一個聊天室開始體驗。</p>
              <button class="btn btn-accent btn-sm js-seed-demo-trigger" style="margin-top:8px;">
                <span>✨ 立即載入範例資料並開始測試</span>
              </button>
            </div>
          </div>
          <div class="onboarding-step">
            <div class="step-badge">步驟 2</div>
            <div class="step-content">
              <h4>🔄 匯入您真實的 Windows 11 LINE 資料</h4>
              <p>支援「掃描本機 LINE 快取資料夾 (自動解密還原相片/影片)」、「匯入 LINE .txt 聊天紀錄備份」或「MCP 同步加密資料庫」。</p>
              <button class="btn btn-secondary btn-sm js-open-settings-trigger" style="margin-top:8px;">
                <span>⚙️ 開啟金庫與同步設定</span>
              </button>
            </div>
          </div>
          <div class="onboarding-step">
            <div class="step-badge">步驟 3</div>
            <div class="step-content">
              <h4>🛡️ 體驗防過期媒體庫、☆ 訊息收藏與 ✅ 待辦勾選</h4>
              <p>選取左側聊天室後，可切換上方「💬 對話紀錄 / ⭐ 收藏訊息 / 🖼️ 相片牆 / 🎬 影片庫 / 📁 檔案櫃」，在右側勾選待辦事項或點擊「📥 匯出報告」。</p>
            </div>
          </div>
        </div>
      </div>
    `;
    centerContent.querySelectorAll(".js-seed-demo-trigger").forEach(btn => {
      btn.addEventListener("click", () => triggerSeedDemo());
    });
    centerContent.querySelectorAll(".js-open-settings-trigger").forEach(btn => {
      btn.addEventListener("click", () => openSettingsModal());
    });
  }

  async function loadCenterContent() {
    if (!currentChatId && !globalSearchQuery && activeTab !== "bookmarks") {
      renderOnboardingGuide();
      return;
    }

    centerContent.innerHTML = '<div class="loading-state">載入金庫資料中...</div>';

    if (activeTab === "messages") {
      await loadMessages(false);
    } else if (activeTab === "bookmarks") {
      await loadMessages(true);
    } else {
      await loadMedia();
    }
  }

  async function loadMessages(onlyBookmarked = false) {
    let url = `/api/messages?limit=300&`;
    if (currentChatId) url += `chat_id=${encodeURIComponent(currentChatId)}&`;
    if (globalSearchQuery) url += `q=${encodeURIComponent(globalSearchQuery)}&`;
    if (dateFrom) url += `date_from=${encodeURIComponent(dateFrom)}&`;
    if (dateTo) url += `date_to=${encodeURIComponent(dateTo)}&`;
    if (onlyBookmarked || activeTab === "bookmarks") url += `bookmarked=1&`;

    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error("載入訊息失敗");
      const msgs = await res.json();
      renderMessages(msgs);
    } catch (err) {
      centerContent.innerHTML = `<div class="loading-state">訊息讀取失敗: ${err.message}</div>`;
    }
  }

  function renderMessages(messages) {
    if (messages.length === 0) {
      filterStatusText.textContent = "查無符合條件的訊息";
      centerContent.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">💬</div>
          <h3>${activeTab === "bookmarks" ? "尚無收藏訊息" : "尚無對話紀錄"}</h3>
          <p>${activeTab === "bookmarks" ? "點擊訊息旁的 ⭐ 即可加入收藏清單。" : "此聊天室目前尚未有對話紀錄，或篩選條件無符合項目。"}</p>
        </div>
      `;
      return;
    }

    filterStatusText.textContent = `共顯示 ${messages.length} 則對話紀錄`;
    const list = document.createElement("div");
    list.className = "message-list";

    messages.forEach(m => {
      const row = document.createElement("div");
      const isMine = m.sender_name === "我";
      row.className = `message-row ${isMine ? "mine" : "others"}`;

      let mediaHtml = "";
      if (m.media_id && m.media_type === "image") {
        mediaHtml = `
          <div class="media-preview-box">
            <a href="/api/media/file/${m.media_id}" target="_blank" title="點擊檢視原圖">
              <img src="/api/media/file/${m.media_id}" alt="${escapeHtml(m.file_name || '相片')}" loading="lazy" />
            </a>
          </div>
        `;
      } else if (m.media_id && m.media_type === "video") {
        mediaHtml = `
          <div class="media-preview-box">
            <video controls preload="metadata">
              <source src="/api/media/file/${m.media_id}" type="${m.mime_type || 'video/mp4'}">
              您的瀏覽器不支援影片播放。
            </video>
          </div>
        `;
      } else if (m.media_id || m.file_name) {
        const icon = m.format_name === "pdf" ? "📄" : (m.format_name === "zip" ? "📦" : "📎");
        const fileUrl = m.media_id ? `/api/media/file/${m.media_id}` : "#";
        const downloadAttr = m.media_id ? `download="${escapeHtml(m.file_name || 'attachment')}"` : "";
        mediaHtml = `
          <div class="file-attachment-card">
            <span class="file-attachment-icon">${icon}</span>
            <div class="file-attachment-info">
              <div class="file-attachment-name">${escapeHtml(m.file_name || "附件檔案")}</div>
              <div class="file-attachment-size">${formatBytes(m.media_size_bytes)}</div>
            </div>
            ${m.media_id ? `<a href="${fileUrl}" ${downloadAttr} class="btn btn-sm btn-outline">下載</a>` : ""}
          </div>
        `;
      }

      const shieldBadge = m.media_status === "archived"
        ? '<span class="shield-badge-archived">🛡️ 已永久防過期備份</span>'
        : (m.media_status === "cached_pending" ? '<span class="shield-badge-pending">⏳ 待快取備份</span>' : '');

      const isBm = Boolean(m.bookmarked);
      const starIcon = isBm ? "⭐" : "☆";
      const starClass = isBm ? "btn-bookmark-msg bookmarked" : "btn-bookmark-msg";
      const starTitle = isBm ? "取消收藏" : "收藏訊息";

      row.innerHTML = `
        <span class="message-sender">${escapeHtml(m.sender_name || "成員")}</span>
        <div class="message-bubble">
          <div class="message-text">${highlightText(m.text_content, globalSearchQuery)}</div>
          ${mediaHtml}
        </div>
        <div class="message-meta">
          <span>${formatTime(m.timestamp_ms)}</span>
          ${shieldBadge}
          <button class="${starClass}" data-msg-id="${m.message_id}" title="${starTitle}">${starIcon}</button>
        </div>
      `;

      const starBtn = row.querySelector(".btn-bookmark-msg");
      if (starBtn) {
        starBtn.addEventListener("click", async (e) => {
          e.stopPropagation();
          const msgId = starBtn.getAttribute("data-msg-id");
          try {
            const res = await fetch(`/api/messages/${encodeURIComponent(msgId)}/bookmark`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({}),
            });
            if (!res.ok) throw new Error("收藏更新失敗");
            const updated = await res.json();
            const nowBm = Boolean(updated.bookmarked);
            m.bookmarked = nowBm;
            starBtn.className = nowBm ? "btn-bookmark-msg bookmarked" : "btn-bookmark-msg";
            starBtn.textContent = nowBm ? "⭐" : "☆";
            starBtn.title = nowBm ? "取消收藏" : "收藏訊息";
            showToast(nowBm ? t("bookmarkAdded") : t("bookmarkRemoved"), "⭐");
            if (activeTab === "bookmarks" && !nowBm) {
              row.remove();
            }
          } catch (err) {
            showToast("收藏失敗: " + err.message, "❌");
          }
        });
      }

      list.appendChild(row);
    });

    centerContent.innerHTML = "";
    centerContent.appendChild(list);
    centerContent.scrollTop = centerContent.scrollHeight;
  }

  async function loadMedia() {
    let typeParam = "all";
    if (activeTab === "photos") typeParam = "image";
    else if (activeTab === "videos") typeParam = "video";
    else if (activeTab === "files") typeParam = "file";

    let url = `/api/media?media_type=${typeParam}&limit=100&`;
    if (currentChatId) url += `chat_id=${encodeURIComponent(currentChatId)}&`;
    if (globalSearchQuery) url += `q=${encodeURIComponent(globalSearchQuery)}&`;

    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error("載入媒體庫失敗");
      const mediaList = await res.json();
      renderMediaGrid(mediaList);
    } catch (err) {
      centerContent.innerHTML = `<div class="loading-state">媒體讀取失敗: ${err.message}</div>`;
    }
  }

  function renderMediaGrid(mediaList) {
    if (mediaList.length === 0) {
      filterStatusText.textContent = "查無符合媒體";
      centerContent.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">${activeTab === "photos" ? "🖼️" : (activeTab === "videos" ? "🎬" : "📁")}</div>
          <h3>金庫無相符項目</h3>
          <p>本分類中尚未有已永久留存的媒體檔案。</p>
        </div>
      `;
      return;
    }

    filterStatusText.textContent = `共保存 ${mediaList.length} 個永久媒體檔案`;
    const grid = document.createElement("div");
    grid.className = "media-grid";

    mediaList.forEach(item => {
      const card = document.createElement("div");
      card.className = "media-card";

      let thumbHtml = "";
      if (item.media_type === "image") {
        thumbHtml = `<img src="/api/media/file/${item.media_id}" alt="${escapeHtml(item.file_name)}" loading="lazy" />`;
      } else if (item.media_type === "video") {
        thumbHtml = `<span class="fallback-icon">🎬</span>`;
      } else {
        const icon = item.format_name === "pdf" ? "📄" : (item.format_name === "zip" ? "📦" : "📁");
        thumbHtml = `<span class="fallback-icon">${icon}</span>`;
      }

      card.innerHTML = `
        <div class="media-card-thumb">${thumbHtml}</div>
        <div class="media-card-body">
          <div class="media-card-title" title="${escapeHtml(item.file_name)}">${escapeHtml(item.file_name)}</div>
          <div class="media-card-meta">
            <span>${formatBytes(item.size_bytes)}</span>
            <span class="shield-badge-archived">🛡️ 永久保存</span>
          </div>
          <a href="/api/media/file/${item.media_id}" download="${escapeHtml(item.file_name)}" class="btn btn-sm btn-outline" style="margin-top:4px;text-align:center;justify-content:center;">下載檔案</a>
        </div>
      `;
      grid.appendChild(card);
    });

    centerContent.innerHTML = "";
    centerContent.appendChild(grid);
  }

  async function loadChatInsight(chatId) {
    insightContainer.innerHTML = '<div class="loading-state">AI 智慧分析中...</div>';
    try {
      let res = await fetch(`/api/insights/${encodeURIComponent(chatId)}`);
      if (res.status === 404) {
        // Trigger auto analyze
        res = await fetch(`/api/analyze/${encodeURIComponent(chatId)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ lang: currentLang }),
        });
      }
      if (!res.ok) throw new Error("取得分析失敗");
      const insight = await res.json();
      renderInsight(insight);
    } catch (err) {
      insightContainer.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">⚠️</div>
          <h3>分析載入未完成</h3>
          <p>${err.message}</p>
        </div>
      `;
    }
  }

  function renderInsight(insight) {
    // Urgency pill
    const urgency = insight.urgency || "normal";
    urgencyBadge.className = `urgency-pill ${urgency}`;
    urgencyBadge.textContent = urgency === "high" ? "緊急行動" : (urgency === "medium" ? "待辦關注" : "狀態正常");

    const summary = insight.summary || "暫無對話重點摘要。";
    const actionItems = insight.action_items || [];
    const importantFiles = insight.important_files || [];
    const suggestedReplies = insight.suggested_replies || [];

    // Action Items HTML
    let actionItemsHtml = "";
    if (actionItems.length === 0) {
      actionItemsHtml = '<p style="font-size:12px;color:var(--text-sub);">對話中未偵測到明確期限、金流或待辦要求。</p>';
    } else {
      actionItemsHtml = actionItems.map((item, idx) => `
        <div class="action-item-card p-${item.priority} ${item.done ? 'done' : ''}" data-idx="${idx}">
          <div class="action-item-header">
            <label style="display:flex;align-items:center;cursor:pointer;">
              <input type="checkbox" class="action-checkbox" data-idx="${idx}" ${item.done ? 'checked' : ''} />
              <span class="action-category-tag">${getCategoryLabel(item.category)}</span>
            </label>
            <span class="action-priority-badge ${item.priority}">${item.priority.toUpperCase()}</span>
          </div>
          <div class="action-item-title ${item.done ? 'done' : ''}">${escapeHtml(item.title)}</div>
          <div class="action-item-footer">
            <span>👤 ${escapeHtml(item.assignee || "團隊")}</span>
            <span>⏳ ${escapeHtml(item.due_hint || "無指定期限")}</span>
          </div>
        </div>
      `).join("");
    }

    // Important Files HTML
    let filesHtml = "";
    if (importantFiles.length === 0) {
      filesHtml = '<p style="font-size:12px;color:var(--text-sub);">本聊天室暫無附件或媒體流通。</p>';
    } else {
      filesHtml = importantFiles.map(f => `
        <div class="file-health-item">
          <span class="file-health-name" title="${escapeHtml(f.file_name)}">${escapeHtml(f.file_name)}</span>
          <span class="file-health-status ${f.status}">
            ${f.status === "archived" ? "🛡️ 已永久留存" : (f.status === "cached_pending" ? "⏳ 待下載原檔" : "⚠️ 需快取")}
          </span>
        </div>
      `).join("");
    }

    // Suggested Replies HTML
    let repliesHtml = suggestedReplies.map(r => `
      <div class="suggested-reply-card">
        <div class="suggested-reply-header">
          <span class="reply-label">${escapeHtml(r.label)}</span>
          <span class="reply-tone">${escapeHtml(r.tone)}</span>
        </div>
        <div class="reply-text">${escapeHtml(r.text)}</div>
        <button class="copy-reply-btn" onclick="copySuggestedReply(${JSON.stringify(r.text)})">
          📋 複製回覆
        </button>
      </div>
    `).join("");

    insightContainer.innerHTML = `
      <!-- Summary -->
      <div class="insight-section">
        <div class="insight-section-title">📌 對話重點摘要</div>
        <div class="summary-text">${escapeHtml(summary)}</div>
      </div>

      <!-- Action Items -->
      <div class="insight-section">
        <div class="insight-section-title">
          <span>✅ 自動提取待辦與關鍵資訊</span>
          <span style="font-size:11px;color:var(--text-muted);margin-left:auto;">${actionItems.length} 項</span>
        </div>
        <div class="action-items-list">${actionItemsHtml}</div>
      </div>

      <!-- File Inspection -->
      <div class="insight-section">
        <div class="insight-section-title">🛡️ 防過期檔案巡檢</div>
        <div class="file-health-list">${filesHtml}</div>
      </div>

      <!-- Suggested Replies -->
      <div class="insight-section">
        <div class="insight-section-title">💡 建議回覆草稿 (一鍵複製)</div>
        <div class="suggested-reply-cards">${repliesHtml}</div>
      </div>
    `;

    // Wire action item check-off listeners
    insightContainer.querySelectorAll(".action-checkbox").forEach(chk => {
      chk.addEventListener("change", async (e) => {
        const idx = parseInt(e.target.getAttribute("data-idx"), 10);
        const done = e.target.checked;
        try {
          const res = await fetch(`/api/insights/${encodeURIComponent(currentChatId)}/action-status`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action_index: idx, done: done }),
          });
          if (!res.ok) throw new Error("待辦狀態更新失敗");
          const updatedInsight = await res.json();
          renderInsight(updatedInsight);
          fetchStatus();
          showToast(done ? t("actionDone") : t("actionUndone"), done ? "✅" : "⏳");
        } catch (err) {
          showToast("更新失敗: " + err.message, "❌");
        }
      });
    });
  }

  function getCategoryLabel(cat) {
    switch (cat) {
      case "deadline": return "📅 期限交付";
      case "finance": return "💰 款項報價";
      case "question": return "❓ 關鍵提問";
      case "task": return "🔨 任務指派";
      default: return "📌 重點項目";
    }
  }

  // Event Listeners
  // 1. Filter Tabs
  filterTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      filterTabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      chatFilter = tab.getAttribute("data-filter");
      fetchChats();
    });
  });

  // 2. Chat Search Input
  let chatSearchTimeout = null;
  chatSearchInput.addEventListener("input", (e) => {
    clearTimeout(chatSearchTimeout);
    chatSearchTimeout = setTimeout(() => {
      chatSearchQuery = e.target.value.trim();
      fetchChats();
    }, 200);
  });

  // 3. Global Search Input
  let globalSearchTimeout = null;
  globalSearchInput.addEventListener("input", (e) => {
    const val = e.target.value.trim();
    globalSearchClear.style.display = val ? "block" : "none";
    clearTimeout(globalSearchTimeout);
    globalSearchTimeout = setTimeout(() => {
      globalSearchQuery = val;
      loadCenterContent();
    }, 250);
  });

  globalSearchClear.addEventListener("click", () => {
    globalSearchInput.value = "";
    globalSearchClear.style.display = "none";
    globalSearchQuery = "";
    loadCenterContent();
  });

  // 4. View Tabs
  viewTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      viewTabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      activeTab = tab.getAttribute("data-tab");
      loadCenterContent();
    });
  });

  // 5. Center Monitoring Toggle
  centerMonitorToggle.addEventListener("change", async (e) => {
    if (!currentChatId) return;
    const isChecked = e.target.checked;
    try {
      const res = await fetch(`/api/chats/${encodeURIComponent(currentChatId)}/monitor`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          monitored: isChecked,
          auto_backup_media: isChecked,
          auto_analyze: isChecked,
        }),
      });
      if (res.ok) {
        showToast(isChecked ? "已開啟自動監控與防過期備份！" : "已關閉監控備份", isChecked ? "🛡️" : "⏸️");
        fetchStatus();
        fetchChats();
        if (isChecked) {
          loadChatInsight(currentChatId);
        }
      }
    } catch (err) {
      showToast("更新監控設定失敗", "❌");
    }
  });

  // 6. Date Filter Buttons
  btnApplyDateFilter.addEventListener("click", () => {
    dateFrom = dateFilterFrom.value;
    dateTo = dateFilterTo.value;
    loadCenterContent();
  });

  btnResetFilter.addEventListener("click", () => {
    dateFilterFrom.value = "";
    dateFilterTo.value = "";
    dateFrom = "";
    dateTo = "";
    loadCenterContent();
  });

  // 7. Seed Demo Data Helper & Button
  async function triggerSeedDemo() {
    if (btnSeedDemo) {
      btnSeedDemo.disabled = true;
      btnSeedDemo.innerHTML = "<span>⏳</span> 載入中...";
    }
    try {
      const res = await fetch("/api/demo/seed", { method: "POST" });
      if (res.ok) {
        if (helpModal) helpModal.style.display = "none";
        showToast("真實範例對話、相片、影片與合約已成功建立！", "✨");
        await fetchStatus();
        await fetchChats();
        if (chatsCache.length > 0) {
          selectChat(chatsCache[0]);
        }
      } else {
        showToast("範例載入失敗", "❌");
      }
    } catch (err) {
      showToast("載入出錯: " + err.message, "❌");
    } finally {
      if (btnSeedDemo) {
        btnSeedDemo.disabled = false;
        btnSeedDemo.innerHTML = `<span class="btn-icon">✨</span> <span id="txtBtnSeedDemo">${t("btnSeedDemo")}</span>`;
      }
    }
  }

  if (btnSeedDemo) {
    btnSeedDemo.addEventListener("click", () => triggerSeedDemo());
  }

  // 8. Analyze All Button
  btnAnalyzeAll.addEventListener("click", async () => {
    btnAnalyzeAll.disabled = true;
    btnAnalyzeAll.innerHTML = "<span>⏳</span> 分析中...";
    try {
      const res = await fetch("/api/analyze-all", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lang: currentLang }),
      });
      if (res.ok) {
        const data = await res.json();
        showToast(`已完成 ${data.analyzed_count} 個監控聊天室分析！`, "⚡");
        fetchStatus();
        if (currentChatId) {
          loadChatInsight(currentChatId);
        }
      }
    } catch (err) {
      showToast("批次分析失敗", "❌");
    } finally {
      btnAnalyzeAll.disabled = false;
      btnAnalyzeAll.innerHTML = '<span class="btn-icon">⚡</span> 重新分析全部';
    }
  });

  // 9. Single Chat Refresh Analysis Button
  btnRefreshAnalysis.addEventListener("click", async () => {
    if (!currentChatId) return;
    btnRefreshAnalysis.disabled = true;
    try {
      const res = await fetch(`/api/analyze/${encodeURIComponent(currentChatId)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lang: currentLang }),
      });
      if (!res.ok) throw new Error("分析失敗");
      const insight = await res.json();
      renderInsight(insight);
      showToast("聊天室 AI 分析已刷新！", "⚡");
    } catch (err) {
      showToast("分析錯誤: " + err.message, "❌");
    } finally {
      btnRefreshAnalysis.disabled = false;
    }
  });

  // 10. Settings & Sync Modal + Help Modal Handlers
  async function openSettingsModal() {
    if (!settingsModal) return;
    if (helpModal) helpModal.style.display = "none";
    settingsModal.style.display = "flex";
    inputLineDataDir.value = localStorage.getItem("line_vault_line_data_dir") || "";
    inputSyncDays.value = localStorage.getItem("line_vault_sync_days") || "14";
    inputTargetChatName.value = localStorage.getItem("line_vault_target_chat") || "";
    toggleAutoPoll.checked = localStorage.getItem("line_vault_auto_poll") === "true";

    try {
      const res = await fetch("/api/status");
      if (res.ok) {
        const data = await res.json();
        settingsVaultDir.textContent = data.vault_dir || "vault_data";
        settingsFts5.textContent = data.fts5_enabled ? "已啟用 (毫秒級搜尋)" : "未支援 (使用 LIKE 模式)";
        settingsLineStatus.textContent = data.line_detected ? "已偵測到本機 LINE" : "未偵測到 (可手動指定路徑)";
        if (!inputLineDataDir.value && data.line_path) {
          inputLineDataDir.value = data.line_path;
        }
      }
    } catch (e) {
      settingsVaultDir.textContent = "無法取得狀態";
    }
  }

  if (btnOpenSettings && settingsModal) {
    btnOpenSettings.addEventListener("click", () => openSettingsModal());

    btnCloseSettings.addEventListener("click", () => {
      settingsModal.style.display = "none";
    });

    settingsModal.addEventListener("click", (e) => {
      if (e.target === settingsModal) {
        settingsModal.style.display = "none";
      }
    });
  }

  if (btnOpenHelp && helpModal) {
    btnOpenHelp.addEventListener("click", () => {
      helpModal.style.display = "flex";
    });
    if (btnCloseHelp) {
      btnCloseHelp.addEventListener("click", () => {
        helpModal.style.display = "none";
      });
    }
    helpModal.addEventListener("click", (e) => {
      if (e.target === helpModal) {
        helpModal.style.display = "none";
      }
    });
    if (btnHelpSeedDemo) {
      btnHelpSeedDemo.addEventListener("click", () => triggerSeedDemo());
    }
    if (btnHelpOpenSettings) {
      btnHelpOpenSettings.addEventListener("click", () => openSettingsModal());
    }
  }

  // Sync Built-in Native Engine Button in Modal
  if (btnModalSyncMcp) {
    btnModalSyncMcp.addEventListener("click", async () => {
      btnModalSyncMcp.disabled = true;
      btnModalSyncMcp.innerHTML = "<span>⏳</span> 內建引擎同步中...";

      const chatName = inputTargetChatName.value.trim() || null;
      const days = parseInt(inputSyncDays.value || "14", 10);
      const cacheDir = inputLineDataDir.value.trim() || null;

      // Persist preferences
      localStorage.setItem("line_vault_line_data_dir", inputLineDataDir.value.trim());
      localStorage.setItem("line_vault_sync_days", days.toString());
      localStorage.setItem("line_vault_target_chat", inputTargetChatName.value.trim());

      try {
        const res = await fetch("/api/sync-mcp", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            chat_name: chatName,
            days: days,
            cache_dir: cacheDir,
          }),
        });
        const data = await res.json();
        if (res.ok && data.success) {
          const sr = data.sync_result || {};
          if (settingsModal) settingsModal.style.display = "none";
          showToast(
            `內建引擎同步完成！同步 ${sr.chats_synced || 0} 個聊天室、${sr.messages_synced || 0} 則紀錄，永久歸檔 ${sr.media_archived || 0} 件媒體！`,
            "🔐"
          );
          await fetchStatus();
          await fetchChats();
          if (chatsCache.length > 0 && !currentChatId) {
            selectChat(chatsCache[0]);
          } else if (currentChatId) {
            loadCenterContent();
            loadChatInsight(currentChatId);
          }
        } else {
          showToast(data.error || "同步失敗，請檢查設定與 LINE 目錄", "❌");
        }
      } catch (err) {
        showToast("同步出錯: " + err.message, "❌");
      } finally {
        btnModalSyncMcp.disabled = false;
        btnModalSyncMcp.innerHTML = "<span>🔐 同步 LINE 資料庫與快取 (內建引擎)</span>";
      }
    });
  }

  // Scan Line Cache Button in Modal
  if (btnModalScanLine) {
    btnModalScanLine.addEventListener("click", async () => {
      btnModalScanLine.disabled = true;
      btnModalScanLine.innerHTML = "<span>⏳</span> 正在掃描快取...";

      const cacheDir = inputLineDataDir.value.trim() || "";
      localStorage.setItem("line_vault_line_data_dir", cacheDir);

      try {
        const res = await fetch("/api/scan-line", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ cache_dir: cacheDir }),
        });
        const data = await res.json();
        if (res.ok && data.success) {
          const sr = data.scan_result || {};
          showToast(
            `快取掃描完成：檢查 ${sr.files_inspected || 0} 檔、歸檔 ${sr.media_imported || 0} 件媒體！`,
            "🔄"
          );
          await fetchStatus();
          await fetchChats();
          if (chatsCache.length > 0 && !currentChatId) {
            selectChat(chatsCache[0]);
          } else if (currentChatId) {
            loadCenterContent();
          }
        } else {
          showToast(data.error || "找不到指定的快取目錄", "⚠️");
        }
      } catch (err) {
        showToast("快取掃描出錯: " + err.message, "❌");
      } finally {
        btnModalScanLine.disabled = false;
        btnModalScanLine.innerHTML = "<span>🔄 掃描本機 LINE 快取資料夾</span>";
      }
    });
  }

  // Auto-poll Timer
  let autoPollInterval = null;
  function updateAutoPollSchedule(enabled) {
    if (autoPollInterval) {
      clearInterval(autoPollInterval);
      autoPollInterval = null;
    }
    if (enabled) {
      // Run every 5 minutes (300,000 ms)
      autoPollInterval = setInterval(async () => {
        const cacheDir = localStorage.getItem("line_vault_line_data_dir") || "";
        const readerScript = localStorage.getItem("line_vault_reader_script") || "";
        const days = parseInt(localStorage.getItem("line_vault_sync_days") || "14", 10);
        try {
          await fetch("/api/sync-mcp", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              days: days,
              reader_script: readerScript || null,
              cache_dir: cacheDir || null,
            }),
          });
          await fetchStatus();
          await fetchChats();
          if (currentChatId) {
            loadChatInsight(currentChatId);
          }
        } catch (e) {
          // Background polling silent error recovery
        }
      }, 300000);
    }
  }

  if (toggleAutoPoll) {
    toggleAutoPoll.addEventListener("change", (e) => {
      const isChecked = e.target.checked;
      localStorage.setItem("line_vault_auto_poll", isChecked ? "true" : "false");
      updateAutoPollSchedule(isChecked);
      showToast(isChecked ? "已啟用每 5 分鐘背景自動巡檢與防過期備份" : "已關閉背景自動巡檢", isChecked ? "⏱️" : "⏸️");
    });

    if (localStorage.getItem("line_vault_auto_poll") === "true") {
      toggleAutoPoll.checked = true;
      updateAutoPollSchedule(true);
    }
  }

  // 11. Theme (System / Light / Dark) & Language Toggle
  let currentThemeMode = localStorage.getItem("line_vault_theme") || "system";
  const systemLightMedia = window.matchMedia ? window.matchMedia("(prefers-color-scheme: light)") : null;

  function applyTheme(mode) {
    currentThemeMode = ["system", "light", "dark"].includes(mode) ? mode : "system";
    localStorage.setItem("line_vault_theme", currentThemeMode);

    let effectiveTheme = currentThemeMode;
    if (currentThemeMode === "system") {
      effectiveTheme = (systemLightMedia && systemLightMedia.matches) ? "light" : "dark";
    }
    document.documentElement.setAttribute("data-theme", effectiveTheme);

    if (themeToggleIcon && themeToggleLabel) {
      if (currentThemeMode === "system") {
        themeToggleIcon.textContent = "🌓";
        themeToggleLabel.textContent = currentLang === "en" ? "System" : "跟隨系統";
      } else if (currentThemeMode === "light") {
        themeToggleIcon.textContent = "☀️";
        themeToggleLabel.textContent = currentLang === "en" ? "Light" : "亮白主題";
      } else {
        themeToggleIcon.textContent = "🌙";
        themeToggleLabel.textContent = currentLang === "en" ? "Dark" : "深色主題";
      }
    }

    themeOptBtns.forEach(btn => {
      if (btn.getAttribute("data-theme-mode") === currentThemeMode) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }
    });
  }

  if (systemLightMedia && systemLightMedia.addEventListener) {
    systemLightMedia.addEventListener("change", () => {
      if (currentThemeMode === "system") {
        applyTheme("system");
      }
    });
  }

  if (btnThemeToggle) {
    btnThemeToggle.addEventListener("click", () => {
      const order = ["system", "light", "dark"];
      const nextMode = order[(order.indexOf(currentThemeMode) + 1) % order.length];
      applyTheme(nextMode);
      const labelMap = {
        system: currentLang === "en" ? "Theme: Follow System" : "外觀主題：🌓 跟隨系統",
        light: currentLang === "en" ? "Theme: Light Mode" : "外觀主題：☀️ 亮白主題",
        dark: currentLang === "en" ? "Theme: Dark Mode" : "外觀主題：🌙 深色主題",
      };
      showToast(labelMap[nextMode], nextMode === "light" ? "☀️" : (nextMode === "dark" ? "🌙" : "🌓"));
    });
  }

  themeOptBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const mode = btn.getAttribute("data-theme-mode") || "system";
      applyTheme(mode);
      const labelMap = {
        system: currentLang === "en" ? "Theme: Follow System" : "外觀主題：🌓 跟隨系統",
        light: currentLang === "en" ? "Theme: Light Mode" : "外觀主題：☀️ 亮白主題",
        dark: currentLang === "en" ? "Theme: Dark Mode" : "外觀主題：🌙 深色主題",
      };
      showToast(labelMap[mode], mode === "light" ? "☀️" : (mode === "dark" ? "🌙" : "🌓"));
    });
  });

  if (btnLangToggle) {
    btnLangToggle.addEventListener("click", () => {
      currentLang = currentLang === "zh-TW" ? "en" : "zh-TW";
      localStorage.setItem("line_vault_lang", currentLang);
      updateLanguageUI();
      applyTheme(currentThemeMode);
      if (currentChatId) {
        loadChatInsight(currentChatId);
      }
      loadCenterContent();
      showToast(currentLang === "en" ? "Switched to English" : "已切換為繁體中文", "🌐");
    });
  }

  // 12. One-Click Chat Report Export Button
  if (btnExportReport) {
    btnExportReport.addEventListener("click", async () => {
      if (!currentChatId) return;
      btnExportReport.disabled = true;
      try {
        const res = await fetch(`/api/export/${encodeURIComponent(currentChatId)}?fmt=markdown`);
        if (!res.ok) throw new Error("匯出報告失敗");
        const blob = await res.blob();
        const disposition = res.headers.get("Content-Disposition") || "";
        let filename = `line_vault_report_${currentChatId}.md`;
        const utf8Match = disposition.match(/filename\*=UTF-8''([^;\s]+)/i);
        const asciiMatch = disposition.match(/filename="?([^";]+)"?/);
        if (utf8Match && utf8Match[1]) {
          try {
            filename = decodeURIComponent(utf8Match[1]);
          } catch (e) {
            filename = utf8Match[1];
          }
        } else if (asciiMatch && asciiMatch[1]) {
          filename = asciiMatch[1];
        }
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        showToast(t("exportSuccess"), "📥");
      } catch (err) {
        showToast("匯出錯誤: " + err.message, "❌");
      } finally {
        btnExportReport.disabled = false;
      }
    });
  }

  // 13. GUI Text Import Handlers
  let selectedImportFileContent = "";
  let selectedImportFileName = "";

  if (btnTriggerFileSelect && inputChatTxtFile) {
    btnTriggerFileSelect.addEventListener("click", () => {
      inputChatTxtFile.click();
    });

    inputChatTxtFile.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (!file) return;
      selectedImportFileName = file.name;
      const reader = new FileReader();
      reader.onload = (event) => {
        const buffer = event.target.result;
        let decoded = "";
        try {
          const utf8Decoder = new TextDecoder("utf-8", { fatal: true });
          decoded = utf8Decoder.decode(buffer);
        } catch (utf8Err) {
          try {
            const big5Decoder = new TextDecoder("big5");
            decoded = big5Decoder.decode(buffer);
          } catch (fallbackErr) {
            const lenientDecoder = new TextDecoder("utf-8");
            decoded = lenientDecoder.decode(buffer);
          }
        }
        selectedImportFileContent = decoded;
        if (importFileStatus) {
          importFileStatus.textContent = `已選擇: ${file.name} (${formatBytes(file.size)})`;
          importFileStatus.style.color = "var(--accent-green)";
        }
        if (btnImportTxt) btnImportTxt.disabled = false;
      };
      reader.onerror = () => {
        showToast("檔案讀取失敗", "❌");
      };
      reader.readAsArrayBuffer(file);
    });
  }

  if (btnImportTxt) {
    btnImportTxt.addEventListener("click", async () => {
      if (!selectedImportFileContent) {
        showToast("請先選擇要匯入的 .txt 檔案", "⚠️");
        return;
      }
      btnImportTxt.disabled = true;
      btnImportTxt.innerHTML = "<span>⏳ 正在解析並匯入...</span>";

      const chatName = inputImportChatName ? (inputImportChatName.value.trim() || selectedImportFileName.replace(/\.txt$/i, "")) : selectedImportFileName;
      try {
        const res = await fetch("/api/import-text", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            chat_name: chatName,
            text_content: selectedImportFileContent,
            auto_analyze: true,
          }),
        });
        const data = await res.json();
        if (res.ok && data.success) {
          const ir = data.import_result || {};
          showToast(
            `匯入成功！聊天室「${ir.chat_name}」匯入 ${ir.imported_messages} 則對話，AI 已分析！`,
            "📄"
          );
          if (settingsModal) settingsModal.style.display = "none";
          await fetchStatus();
          await fetchChats();
          if (ir.chat_id) {
            const importedChat = chatsCache.find(c => c.chat_id === ir.chat_id);
            if (importedChat) {
              selectChat(importedChat);
            }
          }
        } else {
          showToast(data.error || "匯入失敗，請確認檔案格式", "❌");
        }
      } catch (err) {
        showToast("匯入錯誤: " + err.message, "❌");
      } finally {
        btnImportTxt.disabled = false;
        btnImportTxt.innerHTML = `<span>${t("txtStartImport")}</span>`;
      }
    });
  }

  // Purge any third-party browser extension DOM nodes appended to body
  function purgeInjectedExtensionNodes() {
    const allowedIds = new Set(["settingsModal", "helpModal", "toastContainer"]);
    Array.from(document.body.children).forEach((el) => {
      if (el.tagName === "SCRIPT") return;
      if (el.classList.contains("app-header") || el.classList.contains("main-layout")) return;
      if (allowedIds.has(el.id)) return;
      el.remove();
    });
  }
  purgeInjectedExtensionNodes();
  if (typeof MutationObserver !== "undefined") {
    const extObserver = new MutationObserver(() => purgeInjectedExtensionNodes());
    extObserver.observe(document.body, { childList: true });
  }

  // Initial Load
  updateLanguageUI();
  applyTheme(currentThemeMode);
  loadCenterContent();
  fetchStatus();
  fetchChats().then(() => {
    // Automatically select the first chat if available
    if (chatsCache.length > 0) {
      selectChat(chatsCache[0]);
    }
  });
});
