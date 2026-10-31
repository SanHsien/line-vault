"""AI and rule-based chat analyzer for extracting action items, summaries, and smart replies."""

import datetime
import re

from line_vault.db import VaultDB


class ChatAnalyzer:
    """Analyzes chat messages to extract action items, summaries, file health, and suggested replies."""

    def __init__(self, db: VaultDB):
        self.db = db

    def analyze_chat(self, chat_id: str, lang: str = "zh-TW") -> dict:
        """Analyze message history for the given chat and save insight."""
        is_en = bool(lang and lang.lower().startswith("en"))
        chat = self.db.get_chat(chat_id)
        if not chat:
            raise ValueError(f"Chat not found: {chat_id}")

        messages = self.db.search_messages(chat_id=chat_id, limit=0)
        chat_name = chat.get("chat_name") or ("Unnamed Chat" if is_en else "未命名聊天室")

        if not messages:
            summary = (
                f"Chat '{chat_name}' currently has no message history."
                if is_en
                else f"聊天室「{chat_name}」目前尚無對話紀錄。"
            )
            action_items: list[dict] = []
            important_files: list[dict] = []
            if is_en:
                suggested_replies = [
                    {"label": "Greeting", "tone": "Polite & Friendly", "text": "Hello! Is there anything we need to discuss?"},
                    {"label": "Check In", "tone": "Concise & Professional", "text": "Hi there, feel free to reach out whenever you are online!"},
                    {"label": "Follow Up Later", "tone": "Courteous", "text": "Hello, I will follow up with you later to confirm details."},
                ]
            else:
                suggested_replies = [
                    {"label": "打招呼", "tone": "親切禮貌", "text": "您好！請問有什麼需要討論的事項嗎？"},
                    {"label": "確認在線", "tone": "簡潔專業", "text": "哈囉，在線上有空時隨時可以聯絡！"},
                    {"label": "稍後聯繫", "tone": "禮貌客氣", "text": "您好，晚點有空時再與您聯繫確認細節。"},
                ]
            return self.db.save_insight(
                chat_id=chat_id,
                summary=summary,
                action_items=action_items,
                suggested_replies=suggested_replies,
                important_files=important_files,
                urgency="normal",
                engine_used="local-smart-rules",
            )

        # 1. Action Items extraction
        action_items = []
        senders = set()
        urgent_flag = False

        for msg in messages:
            sender = msg.get("sender_name") or ("Member" if is_en else "成員")
            if sender not in ("我", "Me", "me"):
                senders.add(sender)
            text = (msg.get("text_content") or "").strip()
            msg_id = msg.get("message_id", "")
            if not text:
                continue

            # Urgency check
            text_lower = text.lower()
            is_urgent = any(
                kw in text
                for kw in ["緊急", "盡快", "今天", "ASAP", "務必", "立刻", "馬上", "即刻"]
            ) or any(
                kw in text_lower
                for kw in ["urgent", "asap", "immediately", "critical", "today"]
            )
            if is_urgent:
                urgent_flag = True

            # Category and pattern matching
            matched_category = None
            due_hint = ""

            # Check Deadline (explicit time/date expression)
            date_match = re.search(
                r"(本週[一二三四五六日]|星期[一二三四五六日]|明天|後天|今天|下週[一二三四五六日]?|\d{1,2}/\d{1,2}|\d{1,2}點|下班前|中午前|today|tomorrow|eod|asap|monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
                text,
                re.IGNORECASE,
            )
            if date_match and (
                any(w in text for w in ["前", "完成", "交付", "務必", "記得", "驗收"])
                or any(w in text_lower for w in ["before", "by", "complete", "due", "deliver", "deadline", "finish"])
            ):
                matched_category = "deadline"
                due_hint = date_match.group(0)

            # Check Finance
            elif any(
                kw in text
                for kw in ["報價", "報價單", "請款", "NT$", "發票", "金額", "元", "萬", "預算", "匯款"]
            ) or any(
                kw in text_lower
                for kw in ["quote", "quotation", "invoice", "payment", "usd", "$", "budget", "billing"]
            ):
                matched_category = "finance"
                amt_match = re.search(r"(NT\$?\s*[\d,]+|[\d,]+\s*元|[\d,]+\s*萬|\$\s*[\d,]+|[\d,]+\s*USD)", text, re.IGNORECASE)
                due_hint = amt_match.group(0) if amt_match else ("Financial item" if is_en else "金流項目")

            # Check Question
            elif any(
                kw in text
                for kw in ["?", "？", "請問", "能否", "可以嗎", "誰負責", "何時", "怎麼看"]
            ) or any(
                kw in text_lower
                for kw in ["how", "what", "when", "where", "who", "why", "could you", "can we", "is it"]
            ):
                matched_category = "question"
                due_hint = "Pending reply" if is_en else "待答覆"

            # Check Task / Request
            elif any(
                kw in text
                for kw in ["請", "麻煩", "記得", "確認", "修正", "提交", "審核", "更新", "上傳"]
            ) or any(
                kw in text_lower
                for kw in ["please", "kindly", "review", "submit", "update", "upload", "fix", "check", "verify"]
            ):
                matched_category = "task"
                due_hint = "Pending action" if is_en else "待執行"

            if matched_category:
                priority = "high" if is_urgent else ("medium" if matched_category in ("deadline", "finance", "task") else "low")
                clean_title = text.replace("\n", " ")
                if len(clean_title) > 48:
                    clean_title = clean_title[:45] + "..."

                action_items.append({
                    "title": clean_title,
                    "assignee": sender,
                    "due_hint": due_hint,
                    "priority": priority,
                    "source_message_id": msg_id,
                    "category": matched_category,
                })

        # 2. File inspection
        important_files = []
        media_count = 0
        archived_count = 0
        pending_count = 0

        for msg in messages:
            c_type = msg.get("content_type")
            fname = msg.get("file_name") or ""
            m_status = msg.get("media_status") or "none"
            m_id = msg.get("media_id") or msg.get("message_id")

            if c_type in ("image", "video", "audio", "file") or fname:
                media_count += 1
                if m_status == "archived":
                    archived_count += 1
                    status_desc = "archived"
                    advice = (
                        "Securely preserved in the local vault with no expiration risk"
                        if is_en
                        else "已安全保存於本地金庫，無過期風險"
                    )
                elif m_status == "cached_pending":
                    pending_count += 1
                    status_desc = "cached_pending"
                    advice = (
                        "Thumbnail/cache acquired; please download the original file before LINE server expiration"
                        if is_en
                        else "目前僅取得縮圖快取，請於 LINE 伺服器過期前點開下載原檔"
                    )
                else:
                    pending_count += 1
                    status_desc = "expired_or_missing"
                    advice = (
                        "Local backup pending; recommend downloading in desktop LINE to avoid permanent loss"
                        if is_en
                        else "尚未完成本地快取備份，建議盡速於電腦版點擊下載避免永久過期"
                    )

                display_name = fname if fname else (f"Attachment_{msg.get('message_id')}" if is_en else f"附件_{msg.get('message_id')}")
                important_files.append({
                    "message_id": msg.get("message_id"),
                    "media_id": m_id,
                    "file_name": display_name,
                    "media_type": c_type,
                    "status": status_desc,
                    "action_advice": advice,
                })

        # 3. Summary generation
        ts_list = [int(m["timestamp_ms"]) for m in messages if m.get("timestamp_ms")]
        if ts_list:
            min_ts = min(ts_list)
            max_ts = max(ts_list)
            try:
                dt_start = datetime.datetime.fromtimestamp(min_ts / 1000, tz=datetime.timezone.utc).strftime("%Y-%m-%d")
                dt_end = datetime.datetime.fromtimestamp(max_ts / 1000, tz=datetime.timezone.utc).strftime("%Y-%m-%d")
                date_range_str = f"{dt_start} 至 {dt_end}" if dt_start != dt_end else dt_start
                date_range_en = f"{dt_start} to {dt_end}" if dt_start != dt_end else dt_start
            except (ValueError, OSError, OverflowError):
                date_range_str = "全時間範圍"
                date_range_en = "all time"
        else:
            date_range_str = "全時間範圍"
            date_range_en = "all time"

        if is_en:
            senders_str = ", ".join(list(senders)[:5]) if senders else "Team members"
            key_topics = []
            if any(a["category"] == "deadline" for a in action_items):
                key_topics.append("Project milestones & deadlines")
            if any(a["category"] == "finance" for a in action_items):
                key_topics.append("Quotes, invoices & payments")
            if any(a["category"] == "question" for a in action_items):
                key_topics.append("Requirements & progress queries")
            if any(a["category"] == "task" for a in action_items):
                key_topics.append("Task collaboration")
            if not key_topics:
                key_topics.append("General communication & file sharing")

            topics_str = ", ".join(key_topics)
            file_note = (
                f", with {pending_count} file(s) needing cache attention"
                if pending_count > 0
                else ", and all files are safely preserved"
            )
            summary = (
                f"Covering message history from {date_range_en} (unlimited all-time analysis), Chat '{chat_name}' has accumulated {len(messages)} messages with key participants including {senders_str}. "
                f"Core topics cover {topics_str}. A total of {media_count} media and file attachments were exchanged, "
                f"with {archived_count} permanently secured in the local vault{file_note}."
            )
        else:
            senders_str = "、".join(list(senders)[:5]) if senders else "團隊成員"
            key_topics = []
            if any(a["category"] == "deadline" for a in action_items):
                key_topics.append("專案里程碑交付與期限")
            if any(a["category"] == "finance" for a in action_items):
                key_topics.append("款項報價與發票請款")
            if any(a["category"] == "question" for a in action_items):
                key_topics.append("規格與進度提問")
            if any(a["category"] == "task" for a in action_items):
                key_topics.append("工作任務協作")
            if not key_topics:
                key_topics.append("日常業務交流與檔案共享")

            topics_str = "、".join(key_topics)
            summary = (
                f"本聊天室「{chat_name}」對話時間範圍自 {date_range_str}（完整無上限分析），累計 {len(messages)} 則對話，主要參與者包含 {senders_str}。"
                f"探討重點涵蓋 {topics_str}。共流通 {media_count} 個媒體與檔案附件，"
                f"其中 {archived_count} 個已完成防過期永久金庫留存"
                f"{f'，仍有 {pending_count} 個檔案需留意快取狀態' if pending_count > 0 else '，所有檔案保存狀態良好'}。"
            )

        # 4. Suggested Replies based on last incoming message
        last_incoming = None
        for m in reversed(messages):
            if m.get("sender_name") not in ("我", "Me", "me"):
                last_incoming = m
                break
        if not last_incoming and messages:
            last_incoming = messages[-1]

        last_text = (last_incoming.get("text_content") or "").strip() if last_incoming else ""
        last_sender = (last_incoming.get("sender_name") or ("Partner" if is_en else "夥伴")) if last_incoming else ("Partner" if is_en else "夥伴")
        last_lower = last_text.lower()

        if is_en:
            if any(kw in last_lower for kw in ["quote", "quotation", "invoice", "payment", "billing", "報價", "發票", "款"]):
                suggested_replies = [
                    {
                        "label": "Quote Received",
                        "tone": "Business Professional",
                        "text": f"Hi {last_sender}, received the quote and breakdown. We will arrange payment after verification. Thank you!",
                    },
                    {
                        "label": "Approval Update",
                        "tone": "Proactive",
                        "text": f"Received {last_sender}'s payment details. Confirming with team/finance and will update you before EOD!",
                    },
                    {
                        "label": "Invoice Confirmation",
                        "tone": "Detailed",
                        "text": "Thanks for providing this! Please confirm billing information before invoicing. We will share confirmation once processed.",
                    },
                ]
            elif any(q in last_lower for q in ["?", "how", "what", "when", "could you", "can we", "請問", "能否"]):
                suggested_replies = [
                    {
                        "label": "Affirmative Response",
                        "tone": "Decisive & Positive",
                        "text": f"Sounds good {last_sender}, no problem regarding your question. We are on track for delivery!",
                    },
                    {
                        "label": "Check & Report",
                        "tone": "Careful & Professional",
                        "text": f"Received your question {last_sender}. Let me check the latest progress with the team and get back to you shortly.",
                    },
                    {
                        "label": "Alternative Suggestion",
                        "tone": "Collaborative",
                        "text": f"Hi {last_sender}, if time is tight, could we review the core phase 1 deliverables first?",
                    },
                ]
            elif any(f_kw in last_lower for f_kw in ["file", "attachment", "screenshot", "pdf", "zip", "檔案", "截圖", "影片", "文件"]):
                suggested_replies = [
                    {
                        "label": "File Received & Saved",
                        "tone": "Professional & Clear",
                        "text": f"Received the files from {last_sender}! Downloaded and safely backed up to the local vault. Thank you!",
                    },
                    {
                        "label": "Reviewing Details",
                        "tone": "Rigorous",
                        "text": "Files received successfully. The team is reviewing the details and will share feedback shortly.",
                    },
                    {
                        "label": "Brief Acknowledgement",
                        "tone": "Concise",
                        "text": f"Received! Thank you {last_sender} for organizing and sharing!",
                    },
                ]
            else:
                suggested_replies = [
                    {
                        "label": "Progress Commitment",
                        "tone": "Proactive",
                        "text": f"Received your update {last_sender}! We will proceed on schedule and keep everyone posted on any updates.",
                    },
                    {
                        "label": "Handling Shortly",
                        "tone": "Steady & Polite",
                        "text": "Message received! I'm on it and will report back as soon as this is wrapped up.",
                    },
                    {
                        "label": "Appreciation",
                        "tone": "Courteous",
                        "text": f"Thanks {last_sender} for the heads up and support. Have a great day!",
                    },
                ]
        else:
            if "報價" in last_text or "發票" in last_text or "款" in last_text:
                suggested_replies = [
                    {
                        "label": "報價收到核對",
                        "tone": "商務專業",
                        "text": f"好的{last_sender}，相關報價單與明細我們已存檔留底，核對金額無誤後會依時程安排請款作業，謝謝您！",
                    },
                    {
                        "label": "稍後核准回報",
                        "tone": "積極溝通",
                        "text": f"收到{last_sender}的款項資訊，目前正在與主管/採購確認流程中，今天下班前會盡速向您回饋！",
                    },
                    {
                        "label": "發票抬頭確認",
                        "tone": "細節嚴謹",
                        "text": "感謝提供！發票開立前請協助留意統一編號與抬頭資訊，待款項送出後會再提供水單給您。",
                    },
                ]
            elif any(q in last_text for q in ["?", "？", "能否", "可以嗎", "請問", "何時"]):
                suggested_replies = [
                    {
                        "label": "明確肯定答覆",
                        "tone": "果斷積極",
                        "text": f"好的{last_sender}，關於您詢問的事項沒有問題，我們正在按計劃推進，預計依約定時程交付！",
                    },
                    {
                        "label": "稍後確認回報",
                        "tone": "謹慎專業",
                        "text": f"收到{last_sender}的提問，我先與團隊核對最新數據與進度，稍後向您詳細說明。",
                    },
                    {
                        "label": "提供替代建議",
                        "tone": "協同解決",
                        "text": f"{last_sender}好，若時程較緊湊，我們先就第一階段的核心部分進行驗收，您看這樣合適嗎？",
                    },
                ]
            elif any(f_kw in last_text for f_kw in ["檔案", "截圖", "影片", "壓縮包", "文件", "錄影", "合約"]):
                suggested_replies = [
                    {
                        "label": "檔案存檔確認",
                        "tone": "專業明確",
                        "text": f"收到{last_sender}提供的檔案！已下載並備份至本地金庫永久留存，內容非常完整，謝謝！",
                    },
                    {
                        "label": "正在檢視回饋",
                        "tone": "積極嚴謹",
                        "text": "檔案已順利接收，目前團隊正在檢視細節，稍後將彙整反饋意見與大家同步。",
                    },
                    {
                        "label": "簡短收到",
                        "tone": "簡明俐落",
                        "text": f"已收到，感謝{last_sender}辛苦整理分享！",
                    },
                ]
            else:
                suggested_replies = [
                    {
                        "label": "正面進度承諾",
                        "tone": "積極負責",
                        "text": f"收到{last_sender}的說明！我們會依時程全力推進，若有任何更新會即時在群組同步。",
                    },
                    {
                        "label": "稍後處理回覆",
                        "tone": "禮貌穩健",
                        "text": "收到訊息！我正在處理相關事項，稍後告一段落馬上向您回報結果。",
                    },
                    {
                        "label": "致謝確認",
                        "tone": "親切禮貌",
                        "text": f"好的，謝謝{last_sender}的提醒與協助，祝工作順心！",
                    },
                ]

        # 5. Overall Urgency
        if urgent_flag or any(a["priority"] == "high" for a in action_items):
            urgency = "high"
        elif any(a["priority"] == "medium" for a in action_items) or pending_count > 0:
            urgency = "medium"
        else:
            urgency = "normal"

        return self.db.save_insight(
            chat_id=chat_id,
            summary=summary,
            action_items=action_items,
            suggested_replies=suggested_replies,
            important_files=important_files,
            urgency=urgency,
            engine_used="local-smart-rules",
        )
