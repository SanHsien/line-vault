/**
 * LINE Vault - Front-end Application Logic
 */

document.addEventListener("DOMContentLoaded", () => {
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
  const kpiMonitoredChats = document.getElementById("kpiMonitoredChats");
  const kpiArchivedMedia = document.getElementById("kpiArchivedMedia");
  const kpiActionItems = document.getElementById("kpiActionItems");
  const globalSearchInput = document.getElementById("globalSearchInput");
  const globalSearchClear = document.getElementById("globalSearchClear");
  const btnScanLine = document.getElementById("btnScanLine");
  const btnAnalyzeAll = document.getElementById("btnAnalyzeAll");
  const btnSeedDemo = document.getElementById("btnSeedDemo");
  const btnRefreshAnalysis = document.getElementById("btnRefreshAnalysis");

  const chatListContainer = document.getElementById("chatListContainer");
  const chatCountBadge = document.getElementById("chatCountBadge");
  const chatSearchInput = document.getElementById("chatSearchInput");
  const filterTabs = document.querySelectorAll(".filter-tab");

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
          <h3>無相符聊天室</h3>
          <p>點選右上角「載入範例資料」即可建立測試資料。</p>
        </div>
      `;
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

  async function loadCenterContent() {
    if (!currentChatId && !globalSearchQuery) {
      centerContent.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">📁</div>
          <h3>尚未選擇聊天室</h3>
          <p>請從左側點選聊天室以檢視防過期保存之對話紀錄與媒體檔案。</p>
        </div>
      `;
      return;
    }

    centerContent.innerHTML = '<div class="loading-state">載入金庫資料中...</div>';

    if (activeTab === "messages") {
      await loadMessages();
    } else {
      await loadMedia();
    }
  }

  async function loadMessages() {
    let url = `/api/messages?limit=300&`;
    if (currentChatId) url += `chat_id=${encodeURIComponent(currentChatId)}&`;
    if (globalSearchQuery) url += `q=${encodeURIComponent(globalSearchQuery)}&`;
    if (dateFrom) url += `date_from=${encodeURIComponent(dateFrom)}&`;
    if (dateTo) url += `date_to=${encodeURIComponent(dateTo)}&`;

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
          <h3>尚無對話紀錄</h3>
          <p>此聊天室目前尚未有對話紀錄，或篩選條件無符合項目。</p>
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

      row.innerHTML = `
        <span class="message-sender">${escapeHtml(m.sender_name || "成員")}</span>
        <div class="message-bubble">
          <div class="message-text">${highlightText(m.text_content, globalSearchQuery)}</div>
          ${mediaHtml}
        </div>
        <div class="message-meta">
          <span>${formatTime(m.timestamp_ms)}</span>
          ${shieldBadge}
        </div>
      `;
      list.appendChild(row);
    });

    centerContent.innerHTML = "";
    centerContent.appendChild(list);
    // Scroll to bottom
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
        res = await fetch(`/api/analyze/${encodeURIComponent(chatId)}`, { method: "POST" });
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
      actionItemsHtml = actionItems.map(item => `
        <div class="action-item-card p-${item.priority}">
          <div class="action-item-header">
            <span class="action-category-tag">${getCategoryLabel(item.category)}</span>
            <span class="action-priority-badge ${item.priority}">${item.priority.toUpperCase()}</span>
          </div>
          <div class="action-item-title">${escapeHtml(item.title)}</div>
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

  // 7. Scan Local LINE Button
  if (btnScanLine) {
    btnScanLine.addEventListener("click", async () => {
      btnScanLine.disabled = true;
      btnScanLine.innerHTML = "<span>⏳</span> 掃描中...";
      try {
        const res = await fetch("/api/scan-line", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        });
        const data = await res.json();
        if (res.ok && data.success) {
          const sr = data.scan_result || {};
          showToast(
            `本機 LINE 掃描完成：檢查 ${sr.files_inspected || 0} 檔、歸檔 ${sr.media_imported || 0} 件媒體！`,
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
          showToast(data.error || "找不到本機 LINE 資料夾，可先載入範例資料體驗", "⚠️");
        }
      } catch (err) {
        showToast("掃描出錯: " + err.message, "❌");
      } finally {
        btnScanLine.disabled = false;
        btnScanLine.innerHTML = '<span class="btn-icon">🔄</span> 掃描本機 LINE';
      }
    });
  }

  // 7b. Seed Demo Data Button
  btnSeedDemo.addEventListener("click", async () => {
    btnSeedDemo.disabled = true;
    btnSeedDemo.innerHTML = "<span>⏳</span> 載入中...";
    try {
      const res = await fetch("/api/demo/seed", { method: "POST" });
      if (res.ok) {
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
      btnSeedDemo.disabled = false;
      btnSeedDemo.innerHTML = '<span class="btn-icon">✨</span> 載入範例資料';
    }
  });

  // 8. Analyze All Button
  btnAnalyzeAll.addEventListener("click", async () => {
    btnAnalyzeAll.disabled = true;
    btnAnalyzeAll.innerHTML = "<span>⏳</span> 分析中...";
    try {
      const res = await fetch("/api/analyze-all", { method: "POST" });
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
  btnRefreshAnalysis.addEventListener("click", () => {
    if (currentChatId) {
      loadChatInsight(currentChatId);
    }
  });

  // Initial Load
  fetchStatus();
  fetchChats().then(() => {
    // Automatically select the first chat if available
    if (chatsCache.length > 0) {
      selectChat(chatsCache[0]);
    }
  });
});
