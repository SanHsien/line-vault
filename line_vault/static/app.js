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
      btnAbout: "關於",
      btnHelp: "使用說明",
      btnSettings: "金庫與同步設定",
      btnManualSync: "同步 LINE 訊息",
      btnAnalyzeAll: "重新分析全部",
      btnSeedDemo: "載入範例資料",
      btnClearDemo: "清除範例",
      deleteChat: "刪除聊天室",
      chatListTitle: "聊天室清單",
      filterAll: "全部",
      filterMonitored: "監控中",
      filterGroup: "群組",
      filterDirect: "個人",
      filterCommunity: "社群",
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
      btnAbout: "About",
      btnHelp: "Quick Guide",
      btnSettings: "Settings & Sync",
      btnManualSync: "Sync LINE Chats",
      btnAnalyzeAll: "Re-analyze All",
      btnSeedDemo: "Load Demo Data",
      btnClearDemo: "Clear Demo",
      deleteChat: "Delete Chat",
      chatListTitle: "Chats",
      filterAll: "All",
      filterMonitored: "Monitored",
      filterGroup: "Groups",
      filterDirect: "Direct",
      filterCommunity: "Community",
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
  const btnOpenAbout = document.getElementById("btnOpenAbout");
  const txtBtnAbout = document.getElementById("txtBtnAbout");
  const aboutModal = document.getElementById("aboutModal");
  const btnCloseAbout = document.getElementById("btnCloseAbout");
  const aboutVersion = document.getElementById("aboutVersion");
  const aboutAuthor = document.getElementById("aboutAuthor");
  const aboutLicense = document.getElementById("aboutLicense");
  const aboutRepoLink = document.getElementById("aboutRepoLink");
  const updateStatusBox = document.getElementById("updateStatusBox");
  const btnCheckUpdate = document.getElementById("btnCheckUpdate");
  const btnDownloadUpdate = document.getElementById("btnDownloadUpdate");

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
  const txtBtnClearDemo = document.getElementById("txtBtnClearDemo");
  const btnClearDemo = document.getElementById("btnClearDemo");
  const txtExportReport = document.getElementById("txtExportReport");
  const btnExportReport = document.getElementById("btnExportReport");
  const btnDeleteChat = document.getElementById("btnDeleteChat");
  const txtDeleteChat = document.getElementById("txtDeleteChat");
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
  const txtBtnManualSync = document.getElementById("txtBtnManualSync");
  const btnManualSync = document.getElementById("btnManualSync");
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
  const inputMediaStorageDir = document.getElementById("inputMediaStorageDir");
  const btnPickMediaDir = document.getElementById("btnPickMediaDir");
  const chkAutoStickers = document.getElementById("chkAutoStickers");
  const chkAutoImages = document.getElementById("chkAutoImages");
  const chkAutoVideos = document.getElementById("chkAutoVideos");
  const chkAutoFiles = document.getElementById("chkAutoFiles");
  const inputTargetChatName = document.getElementById("inputTargetChatName");
  const btnModalSyncMcp = document.getElementById("btnModalSyncMcp");
  const btnModalScanLine = document.getElementById("btnModalScanLine");
  const toggleAutoUpdate = document.getElementById("toggleAutoUpdate");
  const inputAutoUpdateInterval = document.getElementById("inputAutoUpdateInterval");

  // GUI Chat History Import Elements
  const txtImportSectionTitle = document.getElementById("txtImportSectionTitle");
  // Live Timer & Status Progress Elements
  const globalSyncBanner = document.getElementById("globalSyncBanner");
  const globalSyncBannerText = document.getElementById("globalSyncBannerText");
  const globalSyncBannerBadge = document.getElementById("globalSyncBannerBadge");
  const syncModalTimerNotice = document.getElementById("syncModalTimerNotice");
  const syncModalTimerText = document.getElementById("syncModalTimerText");
  const importTimerNotice = document.getElementById("importTimerNotice");
  const importTimerText = document.getElementById("importTimerText");

  function createProgressTimer(onTick) {
    const startTs = Date.now();
    let currentFormatted = "00:00";
    onTick(currentFormatted, 0);
    const timerId = setInterval(() => {
      const elapsedSec = Math.floor((Date.now() - startTs) / 1000);
      const mm = String(Math.floor(elapsedSec / 60)).padStart(2, "0");
      const ss = String(elapsedSec % 60).padStart(2, "0");
      currentFormatted = `${mm}:${ss}`;
      onTick(currentFormatted, elapsedSec);
    }, 1000);

    return {
      stop: () => {
        clearInterval(timerId);
        return currentFormatted;
      },
    };
  }

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
    if (txtBtnAbout) txtBtnAbout.textContent = t("btnAbout");
    if (txtBtnHelp) txtBtnHelp.textContent = t("btnHelp");
    if (txtBtnSettings) txtBtnSettings.textContent = t("btnSettings");
    if (txtBtnManualSync) txtBtnManualSync.textContent = t("btnManualSync");
    if (txtBtnAnalyzeAll) txtBtnAnalyzeAll.textContent = t("btnAnalyzeAll");
    if (txtBtnSeedDemo) txtBtnSeedDemo.textContent = t("btnSeedDemo");
    if (txtBtnClearDemo) txtBtnClearDemo.textContent = t("btnClearDemo");
    if (txtExportReport) txtExportReport.textContent = t("exportReport");
    if (txtDeleteChat) txtDeleteChat.textContent = t("deleteChat");
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
      else if (chatFilter === "group" || chatFilter === "direct" || chatFilter === "community") url += `chat_type=${chatFilter}&`;
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

      const typeLabel = c.chat_type === "direct" ? "個人" : (c.chat_type === "community" ? "社群" : "群組");
      const typeIcon = c.chat_type === "direct" ? "👤" : (c.chat_type === "community" ? "🌐" : "👥");
      const monitoredHtml = c.monitored
        ? '<span class="monitored-badge">🛡️ 監控備份中</span>'
        : "";
      const unreadHtml = c.unread_count > 0
        ? `<span class="unread-badge">${c.unread_count}</span>`
        : "";

      card.innerHTML = `
        <div class="chat-card-top">
          <span class="chat-card-title">
            <span>${typeIcon}</span>
            <span>${escapeHtml(c.chat_name)}</span>
          </span>
          <div style="display:flex;align-items:center;gap:6px;">
            <span class="chat-card-type-tag">${typeLabel}</span>
            <button type="button" class="btn-card-del" data-chat-id="${escapeHtml(c.chat_id)}" title="刪除此聊天室" style="background:transparent;border:none;color:var(--text-muted);cursor:pointer;font-size:12px;padding:2px 4px;border-radius:4px;">🗑️</button>
          </div>
        </div>
        <div class="chat-card-bottom">
          <span class="chat-card-time">${formatTime(c.last_message_at)}</span>
          <div class="chat-card-badges">
            ${monitoredHtml}
            ${unreadHtml}
          </div>
        </div>
      `;
      const delBtn = card.querySelector(".btn-card-del");
      if (delBtn) {
        delBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          deleteChatById(c.chat_id, c.chat_name);
        });
      }
      chatListContainer.appendChild(card);
    });
  }

  async function deleteChatById(chatId, chatName) {
    if (!chatId) return;
    try {
      const res = await fetch(`/api/chats/${encodeURIComponent(chatId)}/delete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (!res.ok) throw new Error("刪除失敗");
      showToast(`已刪除聊天室「${chatName || chatId}」`, "🗑️");
      if (currentChatId === chatId) {
        currentChatId = null;
        currentChat = null;
        activeChatTitle.textContent = t("noChatSelected");
        activeChatSubtitle.textContent = t("noChatSelectedSub");
        if (btnExportReport) btnExportReport.disabled = true;
        if (btnDeleteChat) btnDeleteChat.disabled = true;
        centerMonitorToggle.disabled = true;
        centerMonitorToggle.checked = false;
      }
      await fetchStatus();
      await fetchChats();
      if (!currentChatId && chatsCache.length > 0) {
        selectChat(chatsCache[0]);
      } else if (!currentChatId) {
        loadCenterContent();
        insightContainer.innerHTML = `
          <div class="empty-state">
            <div class="empty-icon">🤖</div>
            <h3>尚無分析資料</h3>
            <p>選擇左側聊天室並開啟監控，AI 將即時提取對話摘要、重要待辦與建議回覆。</p>
          </div>
        `;
      }
    } catch (err) {
      showToast("刪除聊天室失敗: " + err.message, "❌");
    }
  }

  async function selectChat(chat) {
    currentChatId = chat.chat_id;
    currentChat = chat;

    if (btnExportReport) {
      btnExportReport.disabled = false;
    }
    if (btnDeleteChat) {
      btnDeleteChat.disabled = false;
    }

    // Update left pane active class
    document.querySelectorAll(".chat-card").forEach(el => el.classList.remove("active"));
    const activeEl = [...chatListContainer.children].find(
      el => el.querySelector(".chat-card-title span:last-child")?.textContent === chat.chat_name
    );
    if (activeEl) activeEl.classList.add("active");

    // Center header
    activeChatAvatar.textContent = chat.chat_type === "direct" ? "👤" : (chat.chat_type === "community" ? "🌐" : "👥");
    activeChatTitle.textContent = chat.chat_name;
    const typeDesc = chat.chat_type === "direct" ? "個人對話" : (chat.chat_type === "community" ? "LINE 社群" : "多人群組");
    activeChatSubtitle.textContent = `${typeDesc} • ID: ${chat.chat_id}`;
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
    let url = `/api/messages?limit=0&`;
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

    filterStatusText.textContent = `共顯示全部 ${messages.length} 則對話紀錄`;
    const list = document.createElement("div");
    list.className = "message-list";
    const frag = document.createDocumentFragment();

    messages.forEach(m => {
      const row = document.createElement("div");
      const isMine = m.sender_name === "我";
      row.className = `message-row ${isMine ? "mine" : "others"}`;

      let mediaHtml = "";
      if (m.source_role === "sticker" || m.content_type === "sticker") {
        if (m.media_id) {
          mediaHtml = `
            <div class="sticker-bubble" style="padding:4px;margin-top:4px;">
              <img src="/api/media/file/${m.media_id}" alt="貼圖" style="max-width:140px;max-height:140px;display:block;" loading="lazy" />
            </div>
          `;
        }
      } else if (m.media_id && m.media_type === "image") {
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
        ? '<span class="shield-badge-archived">🛡️ 已永久防過期備份<button type="button" class="btn-help" data-help="archived_media" title="已永久保存說明">?</button></span>'
        : (m.media_status === "cached_pending" ? '<span class="shield-badge-pending">⏳ 待快取備份<button type="button" class="btn-help" data-help="cached_pending" title="什麼是待快取備份？">?</button></span>' : '');

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

      frag.appendChild(row);
    });

    list.appendChild(frag);
    centerContent.innerHTML = "";
    centerContent.appendChild(list);
    centerContent.scrollTop = centerContent.scrollHeight;
  }

  async function loadMedia() {
    let typeParam = "all";
    if (activeTab === "photos") typeParam = "image";
    else if (activeTab === "videos") typeParam = "video";
    else if (activeTab === "files") typeParam = "file";

    let url = `/api/media?media_type=${typeParam}&limit=0&`;
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

  // Manual LINE Sync Button in Top Header with live stopwatch timer
  if (btnManualSync) {
    btnManualSync.addEventListener("click", async () => {
      btnManualSync.disabled = true;
      if (globalSyncBanner) globalSyncBanner.style.setProperty("display", "flex", "important");

      const timer = createProgressTimer((timeStr) => {
        btnManualSync.innerHTML = `<span><span class="spin-icon">⏳</span></span> ${currentLang === "en" ? "Syncing" : "同步中"} (${timeStr})...`;
        if (globalSyncBannerText) {
          globalSyncBannerText.textContent = currentLang === "en"
            ? `Syncing local LINE database & media... Elapsed ${timeStr} (Application is actively working, please wait)`
            : `正在同步本機 LINE 最新對話紀錄與防過期媒體... 已耗時 ${timeStr}（程式持續運作中，請稍候）`;
        }
      });

      try {
        const res = await fetch("/api/sync-mcp", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ days: 0 }),
        });
        const data = await res.json();
        const totalDuration = timer.stop();

        if (res.ok && data.success) {
          const sr = data.sync_result || {};
          if (globalSyncBannerText) {
            globalSyncBannerText.textContent = currentLang === "en"
              ? `✅ Sync complete in ${totalDuration}! (${sr.chats_synced || 0} chats, ${sr.messages_synced || 0} msgs)`
              : `✅ 本機 LINE 同步完成！共耗時 ${totalDuration}（同步 ${sr.chats_synced || 0} 個聊天室、${sr.messages_synced || 0} 則訊息）`;
          }
          if (globalSyncBannerBadge) {
            globalSyncBannerBadge.textContent = currentLang === "en" ? "Finished" : "完成";
            globalSyncBannerBadge.style.background = "var(--accent-green)";
          }
          setTimeout(() => {
            if (globalSyncBanner) globalSyncBanner.style.setProperty("display", "none", "important");
            if (globalSyncBannerBadge) {
              globalSyncBannerBadge.textContent = currentLang === "en" ? "In Progress" : "進行中";
              globalSyncBannerBadge.style.background = "var(--accent-blue)";
            }
          }, 4000);

          showToast(
            `LINE 手動同步完成（耗時 ${totalDuration}）！同步 ${sr.chats_synced || 0} 個聊天室、${sr.messages_synced || 0} 則訊息，歸檔 ${sr.media_archived || 0} 件媒體！`,
            "🔄"
          );
          await fetchStatus();
          await fetchChats();
          if (currentChatId) {
            loadCenterContent();
            loadChatInsight(currentChatId);
          } else if (chatsCache.length > 0) {
            selectChat(chatsCache[0]);
          }
        } else {
          timer.stop();
          if (globalSyncBanner) globalSyncBanner.style.setProperty("display", "none", "important");
          showToast(data.error || "手動同步未完成，請確認本機 LINE 是否已開啟", "⚠️");
        }
      } catch (err) {
        timer.stop();
        if (globalSyncBanner) globalSyncBanner.style.setProperty("display", "none", "important");
        showToast("同步出錯: " + err.message, "❌");
      } finally {
        btnManualSync.disabled = false;
        btnManualSync.innerHTML = `<span class="btn-icon">🔄</span> <span id="txtBtnManualSync">${t("btnManualSync")}</span>`;
      }
    });
  }

  if (btnClearDemo) {
    btnClearDemo.addEventListener("click", async () => {
      btnClearDemo.disabled = true;
      try {
        const res = await fetch("/api/demo/clear", { method: "POST" });
        const data = await res.json();
        if (res.ok && data.success) {
          const cr = data.clear_result || {};
          showToast(`已清除 ${cr.deleted_count || 0} 個測試範例聊天室！`, "🗑️");
          currentChatId = null;
          currentChat = null;
          if (btnExportReport) btnExportReport.disabled = true;
          if (btnDeleteChat) btnDeleteChat.disabled = true;
          centerMonitorToggle.disabled = true;
          centerMonitorToggle.checked = false;
          await fetchStatus();
          await fetchChats();
          if (chatsCache.length > 0) {
            selectChat(chatsCache[0]);
          } else {
            activeChatTitle.textContent = t("noChatSelected");
            activeChatSubtitle.textContent = t("noChatSelectedSub");
            loadCenterContent();
            insightContainer.innerHTML = `
              <div class="empty-state">
                <div class="empty-icon">🤖</div>
                <h3>尚無分析資料</h3>
                <p>選擇左側聊天室並開啟監控，AI 將即時提取對話摘要、重要待辦與建議回覆。</p>
              </div>
            `;
          }
        } else {
          showToast("清除範例資料失敗", "❌");
        }
      } catch (err) {
        showToast("清除範例失敗: " + err.message, "❌");
      } finally {
        btnClearDemo.disabled = false;
      }
    });
  }

  if (btnDeleteChat) {
    btnDeleteChat.addEventListener("click", () => {
      if (!currentChatId) return;
      deleteChatById(currentChatId, currentChat ? currentChat.chat_name : currentChatId);
    });
  }

  // About & Update Modal Handlers
  let latestDownloadUrl = "";
  let latestReleasePageUrl = "https://github.com/SanHsien/line-vault/releases";
  let repoHomeUrl = "https://github.com/SanHsien/line-vault";

  async function openAboutModal() {
    if (!aboutModal) return;
    if (settingsModal) settingsModal.style.display = "none";
    if (helpModal) helpModal.style.display = "none";
    aboutModal.style.display = "flex";
    try {
      const res = await fetch("/api/about");
      if (res.ok) {
        const info = await res.json();
        if (aboutVersion) aboutVersion.textContent = `v${info.version || "1.0.0"}`;
        if (aboutAuthor) aboutAuthor.textContent = info.author || "SanHsien";
        if (aboutLicense) aboutLicense.textContent = info.license || "MIT License";
        if (aboutRepoLink) {
          aboutRepoLink.textContent = info.github_repo || "SanHsien/line-vault";
          aboutRepoLink.href = info.github_repo_url || repoHomeUrl;
        }
        repoHomeUrl = info.github_repo_url || repoHomeUrl;
        latestReleasePageUrl = info.github_releases_url || latestReleasePageUrl;
        latestDownloadUrl = info.download_exe_url || "";
      }
    } catch (e) {
      // Keep default values
    }
  }

  if (btnOpenAbout && aboutModal) {
    btnOpenAbout.addEventListener("click", () => openAboutModal());
    if (btnCloseAbout) {
      btnCloseAbout.addEventListener("click", () => {
        aboutModal.style.display = "none";
      });
    }
    aboutModal.addEventListener("click", (e) => {
      if (e.target === aboutModal) {
        aboutModal.style.display = "none";
      }
    });
  }

  if (btnCheckUpdate) {
    btnCheckUpdate.addEventListener("click", async () => {
      btnCheckUpdate.disabled = true;
      btnCheckUpdate.innerHTML = "<span>⏳ 正在檢查 GitHub Releases...</span>";
      if (updateStatusBox) {
        updateStatusBox.textContent = "正在連線至 GitHub 檢查最新版本...";
      }
      try {
        const res = await fetch("/api/check-update");
        const data = await res.json();
        if (data.download_exe_url) latestDownloadUrl = data.download_exe_url;
        if (data.release_url) latestReleasePageUrl = data.release_url;
        if (updateStatusBox) {
          const statusColor = data.has_update ? "var(--accent-amber)" : "var(--accent-green)";
          updateStatusBox.innerHTML = `
            <div style="font-weight:700;color:${statusColor};margin-bottom:4px;">
              ${data.has_update ? "🚀 發現新版本！" : "✅ 目前已是最新版本"}
            </div>
            <div>目前版本：<b>v${escapeHtml(data.current_version || "1.0.0")}</b> ｜ 最新版本：<b>v${escapeHtml(data.latest_version || "1.0.0")}</b></div>
            <div style="color:var(--text-muted);margin-top:4px;">${escapeHtml(data.message || "")}</div>
          `;
        }
        showToast(data.message || "已完成版本更新檢查", data.has_update ? "🚀" : "✅");
      } catch (err) {
        if (updateStatusBox) {
          updateStatusBox.textContent = "檢查更新失敗: " + err.message;
        }
        showToast("檢查更新失敗", "⚠️");
      } finally {
        btnCheckUpdate.disabled = false;
        btnCheckUpdate.innerHTML = "<span>🔄 檢查更新</span>";
      }
    });
  }

  if (btnDownloadUpdate) {
    btnDownloadUpdate.addEventListener("click", async () => {
      btnDownloadUpdate.disabled = true;
      btnDownloadUpdate.innerHTML = "<span>⏳ 正在下載最新執行檔...</span>";
      try {
        const res = await fetch("/api/download-update", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ download_url: latestDownloadUrl }),
        });
        const data = await res.json();
        if (res.ok && data.success) {
          if (updateStatusBox) {
            updateStatusBox.innerHTML = `
              <div style="font-weight:700;color:var(--accent-green);">✅ 最新版執行檔已下載完成！</div>
              <div style="margin-top:4px;">儲存路徑：<code>${escapeHtml(data.saved_path)}</code> (${formatBytes(data.size_bytes)})</div>
            `;
          }
          showToast(`已下載至 ${data.saved_path}`, "⬇️");
        } else {
          throw new Error(data.error || "下載失敗");
        }
      } catch (err) {
        if (updateStatusBox) {
          updateStatusBox.innerHTML = `
            <div style="font-weight:700;color:var(--accent-red);margin-bottom:4px;">❌ 下載失敗</div>
            <div style="color:var(--text-muted);">${escapeHtml(err.message || "下載失敗")}</div>
          `;
        }
        showToast("一鍵下載失敗: " + err.message, "❌");
      } finally {
        btnDownloadUpdate.disabled = false;
        btnDownloadUpdate.innerHTML = "<span>⬇️ 一鍵下載最新執行檔至 Downloads</span>";
      }
    });
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
  async function saveSettings(patch) {
    try {
      await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
    } catch (e) {
      // Background save silent error handling
    }
  }

  async function openSettingsModal() {
    if (!settingsModal) return;
    if (helpModal) helpModal.style.display = "none";
    settingsModal.style.display = "flex";
    inputLineDataDir.value = localStorage.getItem("line_vault_line_data_dir") || "";
    inputTargetChatName.value = localStorage.getItem("line_vault_target_chat") || "";

    try {
      const res = await fetch("/api/status");
      if (res.ok) {
        const data = await res.json();
        settingsVaultDir.textContent = data.vault_dir || "line-vault";
        settingsFts5.textContent = data.fts5_enabled ? "已啟用 (毫秒級搜尋)" : "未支援 (使用 LIKE 模式)";
        settingsLineStatus.textContent = data.line_detected ? "已偵測到本機 LINE" : "未偵測到 (可手動指定路徑)";
        if (!inputLineDataDir.value && data.line_path) {
          inputLineDataDir.value = data.line_path;
        }
      }
    } catch (e) {
      settingsVaultDir.textContent = "無法取得狀態";
    }

    try {
      const resSet = await fetch("/api/settings");
      if (resSet.ok) {
        const cfg = await resSet.json();
        if (inputMediaStorageDir) inputMediaStorageDir.value = cfg.media_storage_dir || "";
        if (chkAutoStickers) chkAutoStickers.checked = !!cfg.auto_download_stickers;
        if (chkAutoImages) chkAutoImages.checked = !!cfg.auto_download_images;
        if (chkAutoVideos) chkAutoVideos.checked = !!cfg.auto_download_videos;
        if (chkAutoFiles) chkAutoFiles.checked = !!cfg.auto_download_files;
        if (toggleAutoUpdate) toggleAutoUpdate.checked = !!cfg.auto_update_enabled;
        if (inputAutoUpdateInterval) inputAutoUpdateInterval.value = cfg.auto_update_interval_minutes || 5;
      }
    } catch (e) {
      // Settings read fallback
    }
  }

  if (chkAutoStickers) chkAutoStickers.addEventListener("change", (e) => saveSettings({ auto_download_stickers: e.target.checked }));
  if (chkAutoImages) chkAutoImages.addEventListener("change", (e) => saveSettings({ auto_download_images: e.target.checked }));
  if (chkAutoVideos) chkAutoVideos.addEventListener("change", (e) => saveSettings({ auto_download_videos: e.target.checked }));
  if (chkAutoFiles) chkAutoFiles.addEventListener("change", (e) => saveSettings({ auto_download_files: e.target.checked }));
  if (inputMediaStorageDir) inputMediaStorageDir.addEventListener("change", (e) => saveSettings({ media_storage_dir: e.target.value.trim() }));
  if (inputAutoUpdateInterval) inputAutoUpdateInterval.addEventListener("change", (e) => saveSettings({ auto_update_interval_minutes: parseInt(e.target.value, 10) || 5 }));

  if (btnPickMediaDir) {
    btnPickMediaDir.addEventListener("click", async () => {
      try {
        btnPickMediaDir.disabled = true;
        const res = await fetch("/api/pick-folder", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ initial_dir: inputMediaStorageDir ? inputMediaStorageDir.value.trim() : "" }),
        });
        const data = await res.json();
        if (data.selected_path && inputMediaStorageDir) {
          inputMediaStorageDir.value = data.selected_path;
          saveSettings({ media_storage_dir: data.selected_path });
          showToast(`已設定媒體存放目錄：${data.selected_path}`, "📁");
        }
      } catch (err) {
        showToast("選擇資料夾失敗", "⚠️");
      } finally {
        btnPickMediaDir.disabled = false;
      }
    });
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

  // Sync Built-in Native Engine Button in Modal with live stopwatch timer
  if (btnModalSyncMcp) {
    btnModalSyncMcp.addEventListener("click", async () => {
      btnModalSyncMcp.disabled = true;
      if (syncModalTimerNotice) syncModalTimerNotice.style.display = "block";

      const timer = createProgressTimer((timeStr) => {
        btnModalSyncMcp.innerHTML = `<span>⏳</span> ${currentLang === "en" ? "Syncing" : "內建引擎同步中"} (${timeStr})...`;
        if (syncModalTimerText) {
          syncModalTimerText.textContent = currentLang === "en"
            ? `Elapsed ${timeStr} (Decrypting SQLite database & archiving stickers/media, working steadily...)`
            : `已耗時 ${timeStr}（正在解密本機 LINE 資料庫與永久歸檔貼圖媒體，程式持續運行中，請稍候...）`;
        }
      });

      const chatName = inputTargetChatName.value.trim() || null;
      const cacheDir = inputLineDataDir.value.trim() || null;

      localStorage.setItem("line_vault_line_data_dir", inputLineDataDir.value.trim());
      localStorage.setItem("line_vault_target_chat", inputTargetChatName.value.trim());

      try {
        const res = await fetch("/api/sync-mcp", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            chat_name: chatName,
            days: 0,
            cache_dir: cacheDir,
          }),
        });
        const data = await res.json();
        const totalDuration = timer.stop();

        if (res.ok && data.success) {
          const sr = data.sync_result || {};
          if (syncModalTimerNotice) syncModalTimerNotice.style.display = "none";
          if (settingsModal) settingsModal.style.display = "none";
          showToast(
            `內建引擎同步完成（耗時 ${totalDuration}）！全時間範圍同步 ${sr.chats_synced || 0} 個聊天室、${sr.messages_synced || 0} 則紀錄，永久歸檔 ${sr.media_archived || 0} 件媒體！`,
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
          timer.stop();
          if (syncModalTimerNotice) syncModalTimerNotice.style.display = "none";
          showToast(data.error || "同步失敗，請檢查設定與 LINE 目錄", "❌");
        }
      } catch (err) {
        timer.stop();
        if (syncModalTimerNotice) syncModalTimerNotice.style.display = "none";
        showToast("同步出錯: " + err.message, "❌");
      } finally {
        btnModalSyncMcp.disabled = false;
        btnModalSyncMcp.innerHTML = "<span>🔐 同步 LINE 資料庫與快取 (內建引擎)</span>";
      }
    });
  }

  // Scan Line Cache Button in Modal with live stopwatch timer
  if (btnModalScanLine) {
    btnModalScanLine.addEventListener("click", async () => {
      btnModalScanLine.disabled = true;
      if (syncModalTimerNotice) syncModalTimerNotice.style.display = "block";

      const timer = createProgressTimer((timeStr) => {
        btnModalScanLine.innerHTML = `<span>⏳</span> ${currentLang === "en" ? "Scanning" : "正在掃描快取"} (${timeStr})...`;
        if (syncModalTimerText) {
          syncModalTimerText.textContent = currentLang === "en"
            ? `Elapsed ${timeStr} (Scanning and restoring LINE local cached assets, please wait...)`
            : `已耗時 ${timeStr}（正在掃描與還原 LINE 本機快取媒體檔案，請稍候...）`;
        }
      });

      const cacheDir = inputLineDataDir.value.trim() || "";
      localStorage.setItem("line_vault_line_data_dir", cacheDir);

      try {
        const res = await fetch("/api/scan-line", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ cache_dir: cacheDir }),
        });
        const data = await res.json();
        const totalDuration = timer.stop();

        if (res.ok && data.success) {
          const sr = data.scan_result || {};
          if (syncModalTimerNotice) syncModalTimerNotice.style.display = "none";
          showToast(
            `快取掃描完成（耗時 ${totalDuration}）：檢查 ${sr.files_inspected || 0} 檔、歸檔 ${sr.media_imported || 0} 件媒體！`,
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
          timer.stop();
          if (syncModalTimerNotice) syncModalTimerNotice.style.display = "none";
          showToast(data.error || "找不到指定的快取目錄", "⚠️");
        }
      } catch (err) {
        timer.stop();
        if (syncModalTimerNotice) syncModalTimerNotice.style.display = "none";
        showToast("快取掃描出錯: " + err.message, "❌");
      } finally {
        btnModalScanLine.disabled = false;
        btnModalScanLine.innerHTML = "<span>🔄 掃描本機 LINE 快取資料夾</span>";
      }
    });
  }

  // Auto-update UI Timer
  let autoUpdateIntervalTimer = null;
  function updateAutoUpdateSchedule(enabled, intervalMin = 5) {
    if (autoUpdateIntervalTimer) {
      clearInterval(autoUpdateIntervalTimer);
      autoUpdateIntervalTimer = null;
    }
    if (enabled) {
      const ms = Math.max(1, intervalMin) * 60000;
      autoUpdateIntervalTimer = setInterval(async () => {
        try {
          await fetchStatus();
          await fetchChats();
          if (currentChatId) {
            loadChatInsight(currentChatId);
          }
        } catch (e) {
          // Background UI refresh error recovery
        }
      }, ms);
    }
  }

  if (toggleAutoUpdate) {
    toggleAutoUpdate.addEventListener("change", (e) => {
      const isChecked = e.target.checked;
      const intervalMin = parseInt(inputAutoUpdateInterval ? inputAutoUpdateInterval.value : "5", 10) || 5;
      saveSettings({ auto_update_enabled: isChecked });
      updateAutoUpdateSchedule(isChecked, intervalMin);
      showToast(isChecked ? `已啟用每 ${intervalMin} 分鐘背景自動更新` : "已關閉背景自動更新", isChecked ? "⏱️" : "⏸️");
    });
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
      if (importTimerNotice) importTimerNotice.style.display = "block";

      const timer = createProgressTimer((timeStr) => {
        btnImportTxt.innerHTML = `<span>⏳ ${currentLang === "en" ? "Importing" : "正在解析並匯入"} (${timeStr})...</span>`;
        if (importTimerText) {
          importTimerText.textContent = currentLang === "en"
            ? `Elapsed ${timeStr} (Parsing messages and running AI analysis, please wait...)`
            : `已耗時 ${timeStr}（正在解析文字對話並執行 AI 智慧分析，程式正常運作中，請稍候...）`;
        }
      });

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
        const totalDuration = timer.stop();

        if (res.ok && data.success) {
          const ir = data.import_result || {};
          if (importTimerNotice) importTimerNotice.style.display = "none";
          showToast(
            `匯入成功（耗時 ${totalDuration}）！聊天室「${ir.chat_name}」匯入 ${ir.imported_messages} 則對話，AI 已分析！`,
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
          timer.stop();
          if (importTimerNotice) importTimerNotice.style.display = "none";
          showToast(data.error || "匯入失敗，請確認檔案格式", "❌");
        }
      } catch (err) {
        timer.stop();
        if (importTimerNotice) importTimerNotice.style.display = "none";
        showToast("匯入錯誤: " + err.message, "❌");
      } finally {
        btnImportTxt.disabled = false;
        btnImportTxt.innerHTML = `<span>${t("txtStartImport")}</span>`;
      }
    });
  }

  // Purge any third-party browser extension DOM nodes appended to body
  function purgeInjectedExtensionNodes() {
    const allowedIds = new Set(["settingsModal", "helpModal", "aboutModal", "conceptHelpModal", "toastContainer"]);
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


  // ==========================================================================
  // Concept / Feature Explanation Tooltip Modals (?)
  // ==========================================================================
  const conceptHelpModal = document.getElementById("conceptHelpModal");
  const conceptModalTitle = document.getElementById("conceptModalTitle");
  const conceptModalBody = document.getElementById("conceptModalBody");
  const btnCloseConceptHelp = document.getElementById("btnCloseConceptHelp");
  const btnConfirmConceptHelp = document.getElementById("btnConfirmConceptHelp");

  const HELP_TOPICS = {
    manual_sync: {
      title_zh: "🔄 手動同步 LINE 訊息",
      title_en: "🔄 Manual LINE Sync",
      badge_zh: "即時雙向比對",
      badge_en: "Instant Local Scan",
      body_zh: `
        <p><b>手動同步會執行以下動作：</b></p>
        <ul style="padding-left:18px;margin:6px 0;">
          <li><b>解密本機 SQLite 資料庫</b>：讀取 Windows 桌面版 LINE 的最新聊天紀錄、成員暱稱與訊息。</li>
          <li><b>自動防過期歸檔</b>：掃描本機快取與暫存，將最新相片、影片、貼圖及檔案解密備份至本地金庫。</li>
          <li><b>AI 智慧重整</b>：更新統計數據、待辦清單與對話摘要。</li>
        </ul>
        <div class="concept-help-tip">💡 建議在重要對話或接收大量檔案後點擊一次，確保所有內容已永久儲存在您的電腦中。</div>
      `,
      body_en: `
        <p><b>Manual Sync performs the following:</b></p>
        <ul style="padding-left:18px;margin:6px 0;">
          <li><b>Decrypts Local SQLite DB</b>: Reads latest chats, member names, and messages from Windows LINE client.</li>
          <li><b>Automatic Anti-Expiration Backup</b>: Scans cache/downloads and archives photos, videos, stickers, and files to your local vault.</li>
          <li><b>AI Insights</b>: Updates action items, metrics, and conversation summaries.</li>
        </ul>
        <div class="concept-help-tip">💡 Tip: Run a manual sync after receiving important photos or files to guarantee permanent local protection.</div>
      `
    },
    cached_pending: {
      title_zh: "⏳ 什麼是「待快取備份」？如何自動下載原檔？",
      title_en: "⏳ What is 'Pending Cache Backup'? How to get original files?",
      badge_zh: "縮圖已安全保存・原檔需快取",
      badge_en: "Thumbnail Saved・Original Awaiting Cache",
      body_zh: `
        <p><b>LINE 官方的原圖傳輸與快取機制：</b></p>
        <ul style="padding-left:18px;margin:6px 0;">
          <li><b>縮圖已永久保存</b>：LINE 伺服器會自動先傳送預覽縮圖，<b>本系統已第一時間將該縮圖永久歸檔</b>至您的硬碟，即便超過 14~30 天官方過期，畫面也不會消失。</li>
          <li><b>原檔為什麼還在等待？</b>LINE 桌面版預設<b>不會主動自動將所有完整高畫質原檔載入硬碟</b>，只有在使用者於 LINE 聊天室中<b>「點擊照片放大」或「點下載」</b>時，LINE 才會向伺服器拉取完整原檔。</li>
          <li><b>如何自動升級成完整高畫質原檔？</b>只要您在 LINE 視窗中點開過那張照片或檔案，本程式在下一次同步時就會<b>全自動抓取該高畫質原檔並永久歸檔</b>，圖示將自動升級為「🛡️ 已永久保存」！</li>
        </ul>
        <div class="concept-help-tip">💡 批次密技：在 LINE 聊天室右上角開啟「相簿」或「照片／影片清單」，滑過或點擊載入，LINE Vault 就會全數自動接手永久歸檔！</div>
      `,
      body_en: `
        <p><b>How LINE Media Delivery & Caching Works:</b></p>
        <ul style="padding-left:18px;margin:6px 0;">
          <li><b>Thumbnail is Permanently Saved</b>: LINE automatically sends thumbnails first. <b>LINE Vault has already permanently archived this thumbnail</b> to your disk so it will never expire or turn grey.</li>
          <li><b>Why is the original pending?</b> The desktop LINE app does not auto-download high-resolution original files until you <b>click to enlarge or download</b> in the chat.</li>
          <li><b>How to get original files?</b> Simply view/enlarge the photo in LINE once. Next time LINE Vault syncs, it will <b>automatically grab the original file</b> and promote the status to '🛡️ Permanently Archived'!</li>
        </ul>
        <div class="concept-help-tip">💡 Pro Tip: Open 'Photos / Videos' in the LINE chat sidebar and scroll through; LINE Vault will automatically archive all original files!</div>
      `
    },
    archived_media: {
      title_zh: "🛡️ 什麼是「已永久保存」？",
      title_en: "🛡️ What is 'Permanently Archived'?",
      badge_zh: "100% 永久防過期",
      badge_en: "100% Anti-Expiration Safe",
      body_zh: `
        <p><b>此媒體檔案已安全落地儲存：</b></p>
        <ul style="padding-left:18px;margin:6px 0;">
          <li>該照片、影片或檔案已經過解密並完整複製到您的本機資料夾（按聊天室名稱分類）。</li>
          <li><b>即使 LINE 伺服器超過 30 天刪除檔案</b>，或者發送者事後收回/刪除帳號，您電腦硬碟中的檔案依然完整保留。</li>
          <li>隨時可以在「相片牆」、「影片庫」或本地資料夾直接開啟與離線使用。</li>
        </ul>
      `,
      body_en: `
        <p><b>This media file is permanently secured:</b></p>
        <ul style="padding-left:18px;margin:6px 0;">
          <li>The media has been decrypted and stored locally inside your vault directory, sorted by chat name.</li>
          <li><b>Even if LINE servers delete the file after 14-30 days</b>, your local copy remains fully intact and accessible offline.</li>
        </ul>
      `
    },
    auto_download_media: {
      title_zh: "⚙️ 自動下載原檔與媒體機制說明",
      title_en: "⚙️ Automatic Media & Original Download Policy",
      badge_zh: "全自動偵測與歸檔",
      badge_en: "Automated Detection & Storage",
      body_zh: `
        <p><b>各類型媒體的自動下載策略：</b></p>
        <ul style="padding-left:18px;margin:6px 0;">
          <li><b>貼圖 (Stickers)</b>：勾選後由系統直接向官方 CDN 下載原解析度 PNG 透明圖檔，<b>100% 全自動下載</b>。</li>
          <li><b>相片與影片</b>：若本機存有原檔（下載過或本機發送），系統<b>優先自動歸檔完整原檔</b>；若僅有縮圖快取，則自動歸檔縮圖並列為待快取備份。</li>
          <li><b>社群 (OpenChat)</b>：已全面支援自動歸檔社群之所有相片快取與原圖，不受限於加密金鑰。</li>
          <li><b>檔案 (Files)</b>：若您在 LINE 曾另存或開啟過該檔案，系統將自動納入本地金庫備份。</li>
        </ul>
      `,
      body_en: `
        <p><b>Auto-download strategies for each media type:</b></p>
        <ul style="padding-left:18px;margin:6px 0;">
          <li><b>Stickers</b>: 100% automatically downloaded in full resolution from official CDNs.</li>
          <li><b>Photos & Videos</b>: Automatically archives original files if downloaded/cached, otherwise archives thumbnails as safe backup.</li>
          <li><b>OpenChat Communities</b>: Full support for archiving OpenChat media and thumbnails without requiring E2EE keys.</li>
          <li><b>Files</b>: Automatically archives files accessed or saved in LINE.</li>
        </ul>
      `
    },
    media_dir: {
      title_zh: "📂 媒體與貼圖存放根目錄",
      title_en: "📂 Media & Sticker Storage Directory",
      badge_zh: "聊天室名稱自動子目錄",
      badge_en: "Auto-Organized by Chat Name",
      body_zh: `
        <p><b>存放路徑與分類原則：</b></p>
        <ul style="padding-left:18px;margin:6px 0;">
          <li><b>預設路徑</b>：程式所在資料夾下的 <code>line-vault/media</code>。</li>
          <li><b>自動分類</b>：系統會自動抓取真實聊天室名稱（如「里歐酷玩幫」、「家族群」），為每一個聊天室建立獨立的子資料夾。</li>
          <li><b>自訂位置</b>：您可以點擊「選擇資料夾」指定儲存於外接硬碟、OneDrive 或 NAS 路徑。</li>
        </ul>
      `,
      body_en: `
        <p><b>Storage Organization Rules:</b></p>
        <ul style="padding-left:18px;margin:6px 0;">
          <li><b>Default Location</b>: <code>line-vault/media</code> inside the application directory.</li>
          <li><b>Auto-Categorization</b>: Automatically creates subfolders named after each chat (e.g. 'Family Group', 'Leo Deals').</li>
          <li><b>Customization</b>: You can choose an external drive, OneDrive, or NAS path at any time.</li>
        </ul>
      `
    },
    sync_engine: {
      title_zh: "🔐 內建 SQLite 引擎同步",
      title_en: "🔐 Built-in SQLite Decryption Engine",
      badge_zh: "高精度對話關聯",
      badge_en: "High-Precision Association",
      body_zh: `
        <p><b>純 Python 內建讀取引擎：</b></p>
        <ul style="padding-left:18px;margin:6px 0;">
          <li>直接以唯讀方式解密 Windows LINE 的 <code>.edb</code> 與 <code>.edb-wal</code> 資料庫。</li>
          <li>能將每一張相片、影片、貼圖與發言者身分、傳送時間、聊天室對話精確關聯，是完整備份的最佳方式。</li>
        </ul>
      `,
      body_en: `
        <p><b>Pure Python Built-in Engine:</b></p>
        <ul style="padding-left:18px;margin:6px 0;">
          <li>Decrypts Windows LINE <code>.edb</code> and WAL databases in memory without external dependencies.</li>
          <li>Precisely associates every photo, video, and sticker with its sender, timestamp, and message context.</li>
        </ul>
      `
    },
    cache_scan: {
      title_zh: "🔄 掃描本機 LINE 快取資料夾",
      title_en: "🔄 Scan Local LINE Cache Directory",
      badge_zh: "快取檔案全盤打撈",
      badge_en: "Deep Cache Recovery",
      body_zh: `
        <p><b>快取目錄深度掃描：</b></p>
        <ul style="padding-left:18px;margin:6px 0;">
          <li>直接掃描 <code>%LOCALAPPDATA%\LINE\Cache</code> 目錄下的所有檔案。</li>
          <li>自動執行單字節 XOR 反混淆解碼，能打撈出即使資料庫已清理、但快取仍殘留的圖片與音訊。</li>
        </ul>
      `,
      body_en: `
        <p><b>Deep Directory Cache Scanning:</b></p>
        <ul style="padding-left:18px;margin:6px 0;">
          <li>Scans all files under <code>%LOCALAPPDATA%\LINE\Cache</code>.</li>
          <li>Applies single-byte XOR deobfuscation to recover orphan images and audio left in the cache.</li>
        </ul>
      `
    },
    import_txt: {
      title_zh: "📄 匯入 LINE 文字對話紀錄 (.txt)",
      title_en: "📄 Import LINE Chat Text Export (.txt)",
      badge_zh: "跨裝置匯入分析",
      badge_en: "Cross-Device Import & Analysis",
      body_zh: `
        <p><b>支援官方聊天紀錄匯出檔：</b></p>
        <ul style="padding-left:18px;margin:6px 0;">
          <li>從 LINE 手機版或電腦版聊天室設定中點選「傳送聊天記錄」，即可取得 <code>.txt</code> 檔案。</li>
          <li>支援全時間無上限訊息解析，自動識別日期、時間、發言人、通話紀錄與附件提示，並生成 AI 智慧摘要。</li>
        </ul>
      `,
      body_en: `
        <p><b>Official LINE Text Export Support:</b></p>
        <ul style="padding-left:18px;margin:6px 0;">
          <li>Export chat history directly from LINE app settings ('Export chat history') to get a <code>.txt</code> file.</li>
          <li>Parses all-time messages without limit, resolving timestamps, senders, and calls with AI summaries.</li>
        </ul>
      `
    },
    auto_update: {
      title_zh: "⏱️ 背景自動更新排程",
      title_en: "⏱️ Background Auto-Update Schedule",
      badge_zh: "無感守護",
      badge_en: "Silent Protection",
      body_zh: `
        <p><b>定時背景同步與防過期保護：</b></p>
        <ul style="padding-left:18px;margin:6px 0;">
          <li>系統會在背景依照您設定的分鐘數間隔（預設 5 分鐘）自動檢查本機 LINE 最新動態。</li>
          <li>新收到的訊息、貼圖與新快取的相片將自動納入金庫，無需手動頻繁點擊同步。</li>
        </ul>
      `,
      body_en: `
        <p><b>Periodic Background Synchronization:</b></p>
        <ul style="padding-left:18px;margin:6px 0;">
          <li>Automatically checks for new LINE messages and media in the background at your set interval (default 5 mins).</li>
          <li>Newly received messages, stickers, and cached photos are automatically secured without manual effort.</li>
        </ul>
      `
    },
    date_filter: {
      title_zh: "📅 時間區間篩選說明",
      title_en: "📅 Date Range Filter Explanation",
      badge_zh: "顯示視圖 Filter",
      badge_en: "Display View Filter Only",
      body_zh: `
        <p><b>全量分析與局部顯示：</b></p>
        <ul style="padding-left:18px;margin:6px 0;">
          <li>此處設定的時間區間<b>僅為中央清單的「顯示 Filter」</b>，讓您專注檢視特定日期的紀錄。</li>
          <li>系統底層的資料庫同步、防過期媒體下載與 AI 分析，均為<b>全時間範圍完整處理，絕不設上限</b>。</li>
        </ul>
      `,
      body_en: `
        <p><b>Full-History Processing vs View Filtering:</b></p>
        <ul style="padding-left:18px;margin:6px 0;">
          <li>The date range here acts purely as a <b>display filter</b> for the view.</li>
          <li>Database synchronization, media archiving, and AI analysis always process <b>all-time history without limits</b>.</li>
        </ul>
      `
    }
  };

  function openConceptHelp(topicKey) {
    if (!conceptHelpModal) return;
    const isEn = (typeof currentLang !== "undefined" && currentLang === "en");
    const topic = HELP_TOPICS[topicKey] || {
      title_zh: "💡 功能說明",
      title_en: "💡 Feature Information",
      badge_zh: "系統說明",
      badge_en: "System Help",
      body_zh: `<p>此功能為 LINE Vault 本地安全歸檔與分析的整合元件，所有操作均在您的 Windows 電腦本地進行，無須上傳外部雲端。</p>`,
      body_en: `<p>This feature operates strictly on your local Windows PC for anti-expiration archiving without cloud reliance.</p>`
    };
    const isEn = (typeof currentLang !== "undefined" && currentLang === "en");
    if (conceptModalTitle) {
      conceptModalTitle.textContent = isEn ? (topic.title_en || topic.title_zh) : topic.title_zh;
    }
    if (conceptModalBody) {
      const badgeText = isEn ? (topic.badge_en || topic.badge_zh) : topic.badge_zh;
      const htmlBody = isEn ? (topic.body_en || topic.body_zh) : topic.body_zh;
      conceptModalBody.innerHTML = `
        <div class="concept-help-section">
          <div class="concept-help-badge">📌 ${escapeHtml(badgeText)}</div>
          ${htmlBody}
        </div>
      `;
    }
    conceptHelpModal.style.setProperty("display", "flex", "important");
  }

  function closeConceptHelp() {
    if (conceptHelpModal) conceptHelpModal.style.setProperty("display", "none", "important");
  }

  if (btnCloseConceptHelp) btnCloseConceptHelp.addEventListener("click", closeConceptHelp);
  if (btnConfirmConceptHelp) btnConfirmConceptHelp.addEventListener("click", closeConceptHelp);
  if (conceptHelpModal) {
    conceptHelpModal.addEventListener("click", (e) => {
      if (e.target === conceptHelpModal) closeConceptHelp();
    });
  }

  // Delegate all clicks on .btn-help elements across document
  document.addEventListener("click", (e) => {
    const helpBtn = e.target.closest(".btn-help");
    if (!helpBtn) return;
    e.preventDefault();
    e.stopPropagation();
    const topic = helpBtn.getAttribute("data-help");
    if (topic) {
      openConceptHelp(topic);
    }
  });

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
