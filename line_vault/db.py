"""Database abstraction layer for LINE Vault using SQLite3, WAL mode, and FTS5."""

import datetime
import json
import sqlite3
import threading
from pathlib import Path


class VaultDB:
    """Manages chats, messages, media registry, FTS5 index, and AI insights."""

    def __init__(self, db_path: Path | str = "vault_data/vault.db"):
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=30.0,
        )
        self._conn.row_factory = sqlite3.Row
        self.has_fts5 = False
        self._init_schema()

    def _init_schema(self) -> None:
        """Create tables, indexes, and setup FTS5."""
        with self._lock, self._conn:
            cur = self._conn.cursor()
            cur.execute("PRAGMA journal_mode = WAL;")
            cur.execute("PRAGMA foreign_keys = ON;")

            # 1. Chats table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS chats (
                    chat_id TEXT PRIMARY KEY,
                    chat_name TEXT NOT NULL,
                    chat_type TEXT DEFAULT 'group',
                    monitored INTEGER DEFAULT 0,
                    auto_backup_media INTEGER DEFAULT 1,
                    auto_analyze INTEGER DEFAULT 1,
                    last_message_at INTEGER DEFAULT 0,
                    unread_count INTEGER DEFAULT 0,
                    notes TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_chats_monitored ON chats(monitored);")

            # 2. Messages table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    chat_id TEXT NOT NULL,
                    sender_id TEXT DEFAULT '',
                    sender_name TEXT DEFAULT '',
                    timestamp_ms INTEGER NOT NULL,
                    content_type TEXT DEFAULT 'text',
                    text_content TEXT DEFAULT '',
                    media_status TEXT DEFAULT 'none',
                    file_name TEXT DEFAULT '',
                    raw_metadata TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
                );
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat_ts ON messages(chat_id, timestamp_ms);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_media ON messages(media_status);")

            # 3. Media files table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS media_files (
                    media_id TEXT PRIMARY KEY,
                    message_id TEXT NOT NULL,
                    chat_id TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    file_name TEXT DEFAULT '',
                    mime_type TEXT DEFAULT 'application/octet-stream',
                    format_name TEXT DEFAULT '',
                    size_bytes INTEGER DEFAULT 0,
                    sha256 TEXT DEFAULT '',
                    vault_rel_path TEXT NOT NULL,
                    source_role TEXT DEFAULT 'original',
                    archived_at TEXT NOT NULL,
                    FOREIGN KEY(message_id) REFERENCES messages(message_id) ON DELETE CASCADE,
                    FOREIGN KEY(chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
                );
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_media_chat ON media_files(chat_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_media_type ON media_files(media_type);")

            # 4. Insights table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS insights (
                    insight_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    summary TEXT DEFAULT '',
                    action_items TEXT DEFAULT '[]',
                    suggested_replies TEXT DEFAULT '[]',
                    important_files TEXT DEFAULT '[]',
                    urgency TEXT DEFAULT 'normal',
                    engine_used TEXT DEFAULT 'local-smart-rules',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
                );
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_insights_chat ON insights(chat_id, insight_id DESC);")

            # 5. FTS5 Virtual Table
            try:
                cur.execute(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                        message_id UNINDEXED,
                        chat_id UNINDEXED,
                        text_content,
                        sender_name,
                        file_name
                    );
                    """
                )
                self.has_fts5 = True
            except sqlite3.OperationalError:
                self.has_fts5 = False

    def close(self) -> None:
        """Close database connection."""
        with self._lock:
            self._conn.close()

    def upsert_chat(
        self,
        chat_id: str,
        chat_name: str,
        chat_type: str = "group",
        monitored: bool = False,
        auto_backup_media: bool = True,
        auto_analyze: bool = True,
        last_message_at: int = 0,
        unread_count: int = 0,
        notes: str = "",
    ) -> dict:
        """Insert or update chat metadata."""
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._lock, self._conn:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO chats (
                    chat_id, chat_name, chat_type, monitored,
                    auto_backup_media, auto_analyze, last_message_at,
                    unread_count, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    chat_name = excluded.chat_name,
                    chat_type = excluded.chat_type,
                    monitored = excluded.monitored,
                    auto_backup_media = excluded.auto_backup_media,
                    auto_analyze = excluded.auto_analyze,
                    last_message_at = MAX(chats.last_message_at, excluded.last_message_at),
                    unread_count = excluded.unread_count,
                    notes = CASE WHEN excluded.notes != '' THEN excluded.notes ELSE chats.notes END,
                    updated_at = excluded.updated_at;
                """,
                (
                    chat_id,
                    chat_name,
                    chat_type,
                    1 if monitored else 0,
                    1 if auto_backup_media else 0,
                    1 if auto_analyze else 0,
                    last_message_at,
                    unread_count,
                    notes,
                    now_iso,
                    now_iso,
                ),
            )
        return self.get_chat(chat_id) or {}

    def set_chat_monitoring(
        self,
        chat_id: str,
        monitored: bool,
        auto_backup_media: bool = True,
        auto_analyze: bool = True,
    ) -> dict | None:
        """Toggle monitoring settings for a chat."""
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._lock, self._conn:
            cur = self._conn.cursor()
            cur.execute(
                """
                UPDATE chats
                SET monitored = ?,
                    auto_backup_media = ?,
                    auto_analyze = ?,
                    updated_at = ?
                WHERE chat_id = ?;
                """,
                (
                    1 if monitored else 0,
                    1 if auto_backup_media else 0,
                    1 if auto_analyze else 0,
                    now_iso,
                    chat_id,
                ),
            )
        return self.get_chat(chat_id)

    def get_chat(self, chat_id: str) -> dict | None:
        """Retrieve single chat information by chat_id."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM chats WHERE chat_id = ?;", (chat_id,))
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            res["monitored"] = bool(res["monitored"])
            res["auto_backup_media"] = bool(res["auto_backup_media"])
            res["auto_analyze"] = bool(res["auto_analyze"])
            return res

    def list_chats(
        self,
        only_monitored: bool = False,
        chat_type: str | None = None,
        query: str | None = None,
    ) -> list[dict]:
        """List chats with optional filtering."""
        with self._lock:
            sql = "SELECT * FROM chats WHERE 1=1"
            params: list = []
            if only_monitored:
                sql += " AND monitored = 1"
            if chat_type and chat_type != "all":
                sql += " AND chat_type = ?"
                params.append(chat_type)
            if query and query.strip():
                sql += " AND (chat_name LIKE ? OR notes LIKE ?)"
                like_term = f"%{query.strip()}%"
                params.extend([like_term, like_term])
            sql += " ORDER BY last_message_at DESC, chat_name ASC"

            cur = self._conn.cursor()
            cur.execute(sql, params)
            rows = cur.fetchall()

            results = []
            for r in rows:
                item = dict(r)
                item["monitored"] = bool(item["monitored"])
                item["auto_backup_media"] = bool(item["auto_backup_media"])
                item["auto_analyze"] = bool(item["auto_analyze"])
                results.append(item)
            return results

    def upsert_message(
        self,
        message_id: str,
        chat_id: str,
        sender_id: str = "",
        sender_name: str = "",
        timestamp_ms: int = 0,
        content_type: str = "text",
        text_content: str = "",
        media_status: str = "none",
        file_name: str = "",
        raw_metadata: dict | None = None,
    ) -> dict:
        """Insert or update a message record and update FTS5."""
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        metadata_str = json.dumps(raw_metadata or {}, ensure_ascii=False)

        with self._lock, self._conn:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO messages (
                    message_id, chat_id, sender_id, sender_name,
                    timestamp_ms, content_type, text_content,
                    media_status, file_name, raw_metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(message_id) DO UPDATE SET
                    media_status = excluded.media_status,
                    file_name = CASE WHEN excluded.file_name != '' THEN excluded.file_name ELSE messages.file_name END,
                    raw_metadata = excluded.raw_metadata;
                """,
                (
                    message_id,
                    chat_id,
                    sender_id,
                    sender_name,
                    timestamp_ms,
                    content_type,
                    text_content,
                    media_status,
                    file_name,
                    metadata_str,
                    now_iso,
                ),
            )

            # Update chat's last_message_at
            cur.execute(
                """
                UPDATE chats
                SET last_message_at = MAX(last_message_at, ?),
                    updated_at = ?
                WHERE chat_id = ?;
                """,
                (timestamp_ms, now_iso, chat_id),
            )

            # Update FTS5 if supported
            if self.has_fts5:
                try:
                    cur.execute("DELETE FROM messages_fts WHERE message_id = ?;", (message_id,))
                    cur.execute(
                        """
                        INSERT INTO messages_fts (message_id, chat_id, text_content, sender_name, file_name)
                        VALUES (?, ?, ?, ?, ?);
                        """,
                        (message_id, chat_id, text_content, sender_name, file_name),
                    )
                except sqlite3.Error:
                    self.has_fts5 = False

        return {
            "message_id": message_id,
            "chat_id": chat_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "timestamp_ms": timestamp_ms,
            "content_type": content_type,
            "text_content": text_content,
            "media_status": media_status,
            "file_name": file_name,
        }

    def register_media(
        self,
        media_id: str,
        message_id: str,
        chat_id: str,
        media_type: str,
        file_name: str,
        mime_type: str,
        format_name: str,
        size_bytes: int,
        sha256: str,
        vault_rel_path: str,
        source_role: str = "original",
    ) -> dict:
        """Register archived media file in the vault."""
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._lock, self._conn:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO media_files (
                    media_id, message_id, chat_id, media_type,
                    file_name, mime_type, format_name, size_bytes,
                    sha256, vault_rel_path, source_role, archived_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(media_id) DO UPDATE SET
                    file_name = excluded.file_name,
                    mime_type = excluded.mime_type,
                    format_name = excluded.format_name,
                    size_bytes = excluded.size_bytes,
                    sha256 = excluded.sha256,
                    vault_rel_path = excluded.vault_rel_path,
                    source_role = excluded.source_role,
                    archived_at = excluded.archived_at;
                """,
                (
                    media_id,
                    message_id,
                    chat_id,
                    media_type,
                    file_name,
                    mime_type,
                    format_name,
                    size_bytes,
                    sha256,
                    vault_rel_path,
                    source_role,
                    now_iso,
                ),
            )
            cur.execute(
                """
                UPDATE messages
                SET media_status = 'archived'
                WHERE message_id = ?;
                """,
                (message_id,),
            )

        return {
            "media_id": media_id,
            "message_id": message_id,
            "chat_id": chat_id,
            "media_type": media_type,
            "file_name": file_name,
            "mime_type": mime_type,
            "format_name": format_name,
            "size_bytes": size_bytes,
            "sha256": sha256,
            "vault_rel_path": vault_rel_path,
            "source_role": source_role,
            "archived_at": now_iso,
        }

    def _parse_date_to_ms(self, date_str: str, is_end: bool = False) -> int | None:
        """Parse string date to millisecond timestamp."""
        if not date_str:
            return None
        cleaned = date_str.strip()
        try:
            if cleaned.isdigit():
                val = int(cleaned)
                return val if val > 10_000_000_000 else val * 1000
            # Parse ISO or YYYY-MM-DD
            if "T" in cleaned:
                dt = datetime.datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
            else:
                parts = cleaned.split("-")
                if len(parts) == 3:
                    if is_end:
                        dt = datetime.datetime(
                            int(parts[0]), int(parts[1]), int(parts[2]), 23, 59, 59, 999000
                        )
                    else:
                        dt = datetime.datetime(int(parts[0]), int(parts[1]), int(parts[2]), 0, 0, 0)
                else:
                    return None
            return int(dt.timestamp() * 1000)
        except (ValueError, TypeError, OverflowError):
            return None

    def search_messages(
        self,
        query: str = "",
        chat_id: str | None = None,
        content_type: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 200,
    ) -> list[dict]:
        """Search messages with FTS5 or LIKE fallback and join media information."""
        with self._lock:
            cur = self._conn.cursor()
            params: list = []
            where_clauses: list[str] = ["1=1"]

            if chat_id:
                where_clauses.append("m.chat_id = ?")
                params.append(chat_id)

            if content_type and content_type != "all":
                where_clauses.append("m.content_type = ?")
                params.append(content_type)

            ms_from = self._parse_date_to_ms(date_from, is_end=False) if date_from else None
            if ms_from is not None:
                where_clauses.append("m.timestamp_ms >= ?")
                params.append(ms_from)

            ms_to = self._parse_date_to_ms(date_to, is_end=True) if date_to else None
            if ms_to is not None:
                where_clauses.append("m.timestamp_ms <= ?")
                params.append(ms_to)

            q_clean = query.strip() if query else ""

            # Check if we should use FTS5
            matched_msg_ids = None
            if q_clean and self.has_fts5:
                try:
                    # Sanitize for FTS5
                    safe_query = '"' + q_clean.replace('"', '""') + '"'
                    cur.execute(
                        "SELECT message_id FROM messages_fts WHERE messages_fts MATCH ? LIMIT 1000;",
                        (safe_query,),
                    )
                    rows = cur.fetchall()
                    matched_msg_ids = [r[0] for r in rows]
                except sqlite3.OperationalError:
                    matched_msg_ids = None

            if matched_msg_ids:
                placeholders = ",".join("?" for _ in matched_msg_ids)
                where_clauses.append(f"m.message_id IN ({placeholders})")
                params.extend(matched_msg_ids)
            elif q_clean:
                like_term = f"%{q_clean}%"
                where_clauses.append(
                    "(m.text_content LIKE ? OR m.sender_name LIKE ? OR m.file_name LIKE ?)"
                )
                params.extend([like_term, like_term, like_term])

            where_sql = " AND ".join(where_clauses)
            sql = f"""
                SELECT
                    m.message_id,
                    m.chat_id,
                    c.chat_name,
                    m.sender_id,
                    m.sender_name,
                    m.timestamp_ms,
                    m.content_type,
                    m.text_content,
                    m.media_status,
                    m.file_name,
                    m.raw_metadata,
                    m.created_at,
                    mf.media_id,
                    mf.media_type,
                    mf.vault_rel_path,
                    mf.mime_type,
                    mf.format_name,
                    mf.size_bytes AS media_size_bytes,
                    mf.sha256 AS media_sha256,
                    mf.source_role
                FROM messages m
                LEFT JOIN chats c ON m.chat_id = c.chat_id
                LEFT JOIN media_files mf ON m.message_id = mf.message_id
                WHERE {where_sql}
                ORDER BY m.timestamp_ms ASC
                LIMIT ?;
            """
            params.append(limit)
            cur.execute(sql, params)
            rows = cur.fetchall()

            results = []
            for r in rows:
                d = dict(r)
                try:
                    d["raw_metadata"] = json.loads(d.get("raw_metadata") or "{}")
                except (json.JSONDecodeError, TypeError):
                    d["raw_metadata"] = {}
                results.append(d)
            return results

    def list_media(
        self,
        chat_id: str | None = None,
        media_type: str | None = None,
        query: str | None = None,
        limit: int = 200,
    ) -> list[dict]:
        """List archived media files."""
        with self._lock:
            cur = self._conn.cursor()
            sql = """
                SELECT
                    mf.*,
                    c.chat_name,
                    m.sender_name,
                    m.timestamp_ms
                FROM media_files mf
                LEFT JOIN chats c ON mf.chat_id = c.chat_id
                LEFT JOIN messages m ON mf.message_id = m.message_id
                WHERE 1=1
            """
            params: list = []
            if chat_id:
                sql += " AND mf.chat_id = ?"
                params.append(chat_id)
            if media_type and media_type != "all":
                sql += " AND mf.media_type = ?"
                params.append(media_type)
            if query and query.strip():
                sql += " AND (mf.file_name LIKE ? OR c.chat_name LIKE ?)"
                like_q = f"%{query.strip()}%"
                params.extend([like_q, like_q])

            sql += " ORDER BY m.timestamp_ms DESC, mf.archived_at DESC LIMIT ?"
            params.append(limit)

            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]

    def get_media(self, media_id: str) -> dict | None:
        """Get single media record by media_id."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM media_files WHERE media_id = ?;", (media_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def save_insight(
        self,
        chat_id: str,
        summary: str,
        action_items: list[dict],
        suggested_replies: list[dict],
        important_files: list[dict],
        urgency: str = "normal",
        engine_used: str = "local-smart-rules",
    ) -> dict:
        """Save an AI analysis insight for a chat."""
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        actions_json = json.dumps(action_items or [], ensure_ascii=False)
        replies_json = json.dumps(suggested_replies or [], ensure_ascii=False)
        files_json = json.dumps(important_files or [], ensure_ascii=False)

        with self._lock, self._conn:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO insights (
                    chat_id, summary, action_items, suggested_replies,
                    important_files, urgency, engine_used, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    chat_id,
                    summary,
                    actions_json,
                    replies_json,
                    files_json,
                    urgency,
                    engine_used,
                    now_iso,
                ),
            )
            insight_id = cur.lastrowid

        return {
            "insight_id": insight_id,
            "chat_id": chat_id,
            "summary": summary,
            "action_items": action_items,
            "suggested_replies": suggested_replies,
            "important_files": important_files,
            "urgency": urgency,
            "engine_used": engine_used,
            "created_at": now_iso,
        }

    def get_latest_insight(self, chat_id: str) -> dict | None:
        """Retrieve most recent insight for a chat."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                SELECT * FROM insights
                WHERE chat_id = ?
                ORDER BY insight_id DESC
                LIMIT 1;
                """,
                (chat_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            try:
                res["action_items"] = json.loads(res.get("action_items") or "[]")
            except (json.JSONDecodeError, TypeError):
                res["action_items"] = []
            try:
                res["suggested_replies"] = json.loads(res.get("suggested_replies") or "[]")
            except (json.JSONDecodeError, TypeError):
                res["suggested_replies"] = []
            try:
                res["important_files"] = json.loads(res.get("important_files") or "[]")
            except (json.JSONDecodeError, TypeError):
                res["important_files"] = []
            return res

    def get_dashboard_stats(self) -> dict:
        """Calculate overall dashboard statistics."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("SELECT COUNT(*) FROM chats;")
            total_chats = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM chats WHERE monitored = 1;")
            monitored_chats = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM messages;")
            total_messages = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*), COALESCE(SUM(size_bytes), 0) FROM media_files;")
            archived_row = cur.fetchone()
            archived_media_count = archived_row[0]
            total_media_bytes = archived_row[1]

            cur.execute("SELECT COUNT(*) FROM messages WHERE media_status IN ('pending', 'cached_pending');")
            pending_media_count = cur.fetchone()[0]

            # Count pending action items across latest insights
            cur.execute(
                """
                SELECT action_items FROM insights
                GROUP BY chat_id
                HAVING insight_id = MAX(insight_id);
                """
            )
            total_action_items = 0
            for r in cur.fetchall():
                try:
                    items = json.loads(r[0] or "[]")
                    total_action_items += len(items)
                except (json.JSONDecodeError, TypeError):
                    continue

            return {
                "total_chats": total_chats,
                "monitored_chats": monitored_chats,
                "total_messages": total_messages,
                "archived_media_count": archived_media_count,
                "total_media_bytes": total_media_bytes,
                "pending_media_count": pending_media_count,
                "action_items_count": total_action_items,
            }
