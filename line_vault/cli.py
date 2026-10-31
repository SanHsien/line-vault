"""Command line interface for LINE Vault."""

import argparse
import os
from pathlib import Path

from line_vault.analyzer import ChatAnalyzer
from line_vault.archiver import MediaArchiver
from line_vault.db import VaultDB
from line_vault.server import run_server


def _format_size(size_bytes: int) -> str:
    """Format bytes into human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.2f} MB"


def main(argv: list[str] | None = None) -> int:
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        prog="line-vault",
        description="LINE Vault - Windows 11 本地對話與防過期媒體管理中心",
    )
    parser.add_argument(
        "--vault-dir",
        default="vault_data",
        help="金庫資料儲存目錄 (預設: vault_data)",
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # 1. web
    web_parser = subparsers.add_parser("web", help="啟動 Web 管理介面與 REST 伺服器")
    web_parser.add_argument("--host", default="127.0.0.1", help="監聽位址 (預設: 127.0.0.1)")
    web_parser.add_argument("--port", type=int, default=8765, help="監聽連接埠 (預設: 8765)")
    web_parser.add_argument("--no-browser", action="store_true", help="啟動時不要自動開啟瀏覽器")

    # 2. seed
    subparsers.add_parser("seed", help="載入真實繁體中文範例對話、相片、影片與文件")

    # 3. stats
    subparsers.add_parser("stats", help="顯示目前金庫儲存與監控統計數據")

    # 4. search
    search_parser = subparsers.add_parser("search", help="全文檢索對話與媒體訊息")
    search_parser.add_argument("query", nargs="?", default="", help="關鍵字搜尋")
    search_parser.add_argument("--chat-id", help="限定特定聊天室 ID")
    search_parser.add_argument("--limit", type=int, default=50, help="最多回傳筆數 (預設: 50)")

    # 5. analyze
    analyze_parser = subparsers.add_parser("analyze", help="執行 AI 智慧分析與行動待辦提取")
    analyze_parser.add_argument("--chat-id", help="指定聊天室 ID")
    analyze_parser.add_argument("--all", action="store_true", help="分析所有已監控之聊天室")

    # 6. scan
    scan_parser = subparsers.add_parser("scan", help="掃描本機 LINE 快取資料夾並防過期保存")
    scan_parser.add_argument("--cache-dir", help="指定 LINE 快取目錄路徑")

    args = parser.parse_args(argv)

    vault_dir = Path(args.vault_dir).resolve()
    vault_dir.mkdir(parents=True, exist_ok=True)
    db = VaultDB(vault_dir / "vault.db")
    archiver = MediaArchiver(vault_dir, db)
    analyzer = ChatAnalyzer(db)

    if not args.command or args.command == "web":
        host = getattr(args, "host", "127.0.0.1")
        port = getattr(args, "port", 8765)
        no_browser = getattr(args, "no_browser", False)
        run_server(
            vault_dir=vault_dir,
            host=host,
            port=port,
            open_browser=not no_browser,
        )
        return 0

    if args.command == "seed":
        print("[*] 正在為金庫載入真實繁體中文範例對話、相片、影片與文件附件...")
        result = archiver.seed_demo_data(analyzer=analyzer)
        print(
            f"[+] 載入完成！成功建立 {result['chats_seeded']} 個聊天室、"
            f"{result['media_seeded']} 個已永久存檔之媒體，並已完成 {result['monitored_analyzed']} 個監控聊天室分析。"
        )
        return 0

    if args.command == "stats":
        stats = db.get_dashboard_stats()
        print("==================================================")
        print("         LINE 金庫 (LINE Vault) 統計資訊          ")
        print("==================================================")
        print(f" 金庫存放目錄: {vault_dir}")
        print(f" 聊天室總數:   {stats['total_chats']} 個 (監控中: {stats['monitored_chats']} 個)")
        print(f" 訊息紀錄總數: {stats['total_messages']} 則")
        print(
            f" 永久保存媒體: {stats['archived_media_count']} 個 "
            f"({_format_size(stats['total_media_bytes'])})"
        )
        print(f" 待快取下載:   {stats['pending_media_count']} 個")
        print(f" 提取待辦事項: {stats['action_items_count']} 個")
        print("==================================================")
        return 0

    if args.command == "search":
        q = args.query or ""
        msgs = db.search_messages(query=q, chat_id=args.chat_id, limit=args.limit)
        print(f"[*] 檢索條件: '{q}'，找到 {len(msgs)} 筆紀錄：")
        print("--------------------------------------------------")
        for m in msgs:
            sender = m.get("sender_name") or "成員"
            chat_name = m.get("chat_name") or m.get("chat_id")
            content = m.get("text_content") or f"[{m.get('content_type')} 附件: {m.get('file_name')}]"
            print(f"[{chat_name}] {sender}: {content}")
        print("--------------------------------------------------")
        return 0

    if args.command == "analyze":
        if args.all:
            chats = db.list_chats(only_monitored=True)
            print(f"[*] 開始分析 {len(chats)} 個監控中聊天室...")
            for c in chats:
                cid = c["chat_id"]
                res = analyzer.analyze_chat(cid)
                print(f"[+] 聊天室: {c['chat_name']} (緊急度: {res['urgency']})")
                print(f"    摘要: {res['summary']}")
                print(f"    待辦事項: {len(res['action_items'])} 個")
        elif args.chat_id:
            res = analyzer.analyze_chat(args.chat_id)
            print(f"[+] 聊天室 ID: {args.chat_id}")
            print(f"    緊急度: {res['urgency']}")
            print(f"    摘要: {res['summary']}")
            print("    待辦事項:")
            for item in res["action_items"]:
                print(f"      - [{item['priority'].upper()}] ({item['category']}) {item['title']} (指派: {item['assignee']}, 期限: {item['due_hint']})")
            print("    建議回覆:")
            for r in res["suggested_replies"]:
                print(f"      * [{r['label']} - {r['tone']}]: {r['text']}")
        else:
            print("[!] 請指定 --chat-id 或 --all 參數")
            return 1
        return 0

    if args.command == "scan":
        cache_dir = args.cache_dir
        if not cache_dir:
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            if local_appdata:
                cache_dir = str(Path(local_appdata) / "LINE" / "Data")
            else:
                cache_dir = ""

        if not cache_dir or not Path(cache_dir).exists():
            print(f"[!] 找不到預設 LINE 資料夾: {cache_dir}，請透過 --cache-dir 明確指定。")
            return 1

        print(f"[*] 掃描 LINE 快取資料夾: {cache_dir}")
        scan_res = archiver.scan_local_line_directory(cache_dir, analyzer=analyzer)
        print(
            f"[+] 掃描完畢！檢查 {scan_res['files_inspected']} 個檔案，"
            f"發現 {len(scan_res['edb_databases_found'])} 個 .edb 資料庫，"
            f"永久歸檔 {scan_res['media_imported']} 個媒體檔案。"
        )
        return 0

    return 0
