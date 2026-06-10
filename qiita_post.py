#!/usr/bin/env python3
"""
qiita_post.py - CLIからQiitaにMarkdown記事を投稿するスクリプト

使い方:
  python qiita_post.py article.md           # 投稿（qiita_id の有無で新規/更新を自動判定）
  python qiita_post.py --draft article.md   # 限定公開として投稿
  python qiita_post.py --dry-run article.md # 送信内容を表示するだけ（API呼び出しなし）
  python qiita_post.py list                 # 投稿済み記事一覧
  python qiita_post.py config show          # 設定ファイルのパスとユーザー名を表示

設定ファイル（~/.config/qiita_post/config.json または .qiita_config.json）:
  {
    "token": "your_personal_access_token"
  }

  または環境変数 QIITA_TOKEN でトークンを渡すこともできます。

記事ファイルのフォーマット:
  ---
  title: 記事タイトル
  tags: [STM32, Rust, Embassy]
  private: false
  qiita_id: ""
  ---

  記事本文（Markdown）
"""

import argparse
import json
import re
import sys
from pathlib import Path

import frontmatter as fm
import qiita_api


# ──────────────────────────────────────────────
# argv 前処理
# ──────────────────────────────────────────────

def _inject_post_subcommand():
    """
    サブコマンドなしでファイルパスが渡された場合に 'post' を注入する。
    グローバルオプション（--config VALUE）をサブコマンドの直後に移動することで、
    argparse のサブパーサーが --config を確実に受け取れるようにする。

    例:
      qiita_post.py article.md              → qiita_post.py post article.md
      qiita_post.py --config f article.md   → qiita_post.py post --config f article.md
      qiita_post.py --draft article.md      → qiita_post.py post --draft article.md
      qiita_post.py --config f list         → qiita_post.py list --config f
      qiita_post.py list                    → 変更なし
    """
    KNOWN_SUBCOMMANDS = frozenset(("post", "list", "config", "delete"))
    GLOBAL_OPTS_WITH_VALUE = {"--config"}

    prog = sys.argv[0]
    i = 1
    global_part: list[str] = []

    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in GLOBAL_OPTS_WITH_VALUE and i + 1 < len(sys.argv):
            global_part.extend([arg, sys.argv[i + 1]])
            i += 2
        else:
            break

    remaining = sys.argv[i:]

    first_pos = next((a for a in remaining if not a.startswith("-")), None)
    if first_pos is not None and first_pos not in KNOWN_SUBCOMMANDS:
        remaining = ["post"] + remaining

    # グローバルオプションをサブコマンドの直後に移動する。
    # argparse のサブパーサーは自身より後の引数しか処理しないため、
    # サブコマンドより前に置くと subparser のデフォルト値に上書きされる。
    if global_part and remaining and remaining[0] in KNOWN_SUBCOMMANDS:
        sys.argv = [prog, remaining[0]] + global_part + remaining[1:]
    else:
        sys.argv = [prog] + global_part + remaining


# ──────────────────────────────────────────────
# frontmatter 処理
# ──────────────────────────────────────────────

_FRONTMATTER_EXAMPLE = """\
  ---
  title: 記事タイトル
  tags: [STM32, Rust, Embassy]
  private: false
  qiita_id: ""
  ---"""


def parse_frontmatter(content: str) -> tuple[dict | None, str]:
    """
    YAML frontmatter を解析して (metadata, body) を返す。
    frontmatter がない場合は (None, content) を返す。
    """
    post = fm.loads(content)
    if not post.metadata:
        return None, content
    return dict(post.metadata), post.content


def build_tags(tag_list: list) -> list[dict]:
    """タグ名リストをQiita API形式に変換する"""
    return [{"name": str(t), "versions": []} for t in tag_list]


def write_back_qiita_id(md_file: Path, qiita_id: str):
    """投稿後に qiita_id を frontmatter に書き戻す"""
    post = fm.load(str(md_file))
    post["qiita_id"] = qiita_id
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(fm.dumps(post))


# ──────────────────────────────────────────────
# 画像処理
# ──────────────────────────────────────────────

def process_markdown_images(body: str, config: dict, dry_run: bool = False) -> str:
    """Markdown 本文中のローカル画像参照をクラウド URL に置き換える"""
    image_host = config.get("image_host")
    if not image_host:
        return body

    if image_host == "s3":
        import uploader_s3
        uploader = uploader_s3.upload
    else:
        print(f"警告: 未対応の image_host: {image_host}（スキップ）")
        return body

    def _replace(m):
        alt, path = m.group(1), m.group(2)
        if path.startswith(("http://", "https://")):
            return m.group(0)
        if dry_run:
            return f"![{alt}](<UPLOAD:{path}>)"
        try:
            url = uploader(path, config)
        except (RuntimeError, FileNotFoundError) as e:
            print(f"  警告: 画像アップロードをスキップ: {path} ({e})")
            return m.group(0)
        return f"![{alt}]({url})"

    return re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', _replace, body)


# ──────────────────────────────────────────────
# サブコマンド
# ──────────────────────────────────────────────

def cmd_post(args):
    md_file = Path(args.file)
    if not md_file.exists():
        print(f"ファイルが見つかりません: {md_file}")
        sys.exit(1)

    raw_content = md_file.read_text(encoding="utf-8")

    # frontmatter 解析
    metadata, body = parse_frontmatter(raw_content)
    if metadata is None:
        print("エラー: frontmatter が見つかりません。")
        print("  記事ファイルの先頭に frontmatter を追加してください:")
        print(_FRONTMATTER_EXAMPLE)
        sys.exit(1)

    # 必須フィールドの検証
    title = metadata.get("title", "").strip()
    if not title:
        print("エラー: frontmatter に title が設定されていません。")
        sys.exit(1)

    tag_list = metadata.get("tags", [])
    if not tag_list:
        print("エラー: frontmatter に tags が設定されていません（最低1つ必要）。")
        sys.exit(1)

    if len(tag_list) > 5:
        print(f"警告: タグが {len(tag_list)} 個あります。Qiita は最大5個までです。先頭5個を使用します。")
        tag_list = tag_list[:5]

    tags = build_tags(tag_list)
    private = bool(metadata.get("private", False))
    qiita_id = str(metadata.get("qiita_id", "")).strip()

    # --draft は private=True で上書き
    if args.draft:
        private = True

    # 画像処理（image_host が設定されている場合）
    if not args.no_images:
        _config = qiita_api.load_config(args.config)
        if _config.get("image_host"):
            print("[画像処理]")
            body = process_markdown_images(body, _config, dry_run=args.dry_run)

    # --dry-run: API を叩かずに送信内容を表示
    if args.dry_run:
        payload = {
            "title": title,
            "body": body,
            "tags": tags,
            "private": private,
        }
        action = "更新" if qiita_id else "新規作成"
        print(f"[dry-run] 操作: {action}" + (f" (id: {qiita_id})" if qiita_id else ""))
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    token = qiita_api.load_token(args.config)

    if not qiita_id:
        # 新規作成
        print("[記事の新規作成]")
        try:
            new_id, url = qiita_api.create_item(token, title, body, tags, private)
        except RuntimeError as e:
            print(f"エラー: {e}")
            sys.exit(1)

        write_back_qiita_id(md_file, new_id)
        print(f"✓ qiita_id を frontmatter に書き込みました: {new_id}")
        _print_result("投稿完了", title, private, url, new_id)
    else:
        # 更新
        print(f"[記事の更新] id: {qiita_id}")
        try:
            url = qiita_api.update_item(token, qiita_id, title, body, tags, private)
        except RuntimeError as e:
            print(f"エラー: {e}")
            sys.exit(1)

        _print_result("更新完了", title, private, url, qiita_id)


def _print_result(label: str, title: str, private: bool, url: str, item_id: str):
    status = "限定公開" if private else "公開"
    print(f"\n{'='*50}")
    print(f"✅ {label}!")
    print(f"   タイトル : {title}")
    print(f"   公開設定 : {status}")
    print(f"   id       : {item_id}")
    print(f"   URL      : {url}")
    print(f"{'='*50}\n")


def cmd_list(args):
    token = qiita_api.load_token(args.config)
    items = qiita_api.list_items(token)

    if not items:
        print("記事がありません。")
        return

    print(f"\n{'─'*70}")
    print(f"{'タイトル':<30} {'公開設定':<8} {'作成日':<12} id")
    print(f"{'─'*70}")
    for item in items:
        title = item.get("title", "(無題)")[:28]
        status = "限定公開" if item.get("private") else "公開"
        created = item.get("created_at", "")[:10]
        item_id = item.get("id", "")
        print(f"{title:<30} {status:<8} {created:<12} {item_id}")
    print(f"{'─'*70}\n")


def cmd_delete(args):
    item_id = args.id.strip()

    if not args.yes:
        answer = input(f"記事 {item_id} を削除しますか？ [y/N]: ").strip().lower()
        if answer not in ("y", "yes"):
            print("削除をキャンセルしました。")
            return

    token = qiita_api.load_token(args.config)
    try:
        qiita_api.delete_item(token, item_id)
    except RuntimeError as e:
        print(f"エラー: {e}")
        sys.exit(1)

    print(f"✓ 記事を削除しました: {item_id}")


def cmd_config(args):
    token = qiita_api.load_token(args.config)
    config_path = qiita_api.resolve_config_path(args.config)
    user = qiita_api.get_authenticated_user(token)
    print(f"設定ファイル: {config_path.resolve()}")
    print(f"  ユーザー名 : {user.get('id')}")
    print(f"  表示名     : {user.get('name')}")


# ──────────────────────────────────────────────
# メイン
# ──────────────────────────────────────────────

def main():
    _inject_post_subcommand()

    # --config を全サブコマンドで使えるよう parent parser に切り出す
    config_parser = argparse.ArgumentParser(add_help=False)
    config_parser.add_argument(
        "--config", metavar="FILE",
        help="設定ファイルのパス（デフォルト: ~/.config/qiita_post/config.json）",
    )

    parser = argparse.ArgumentParser(
        parents=[config_parser],
        description="QiitaにMarkdown記事をCLIから投稿するツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 投稿（新規作成 or 更新を自動判定）
  python qiita_post.py article.md

  # 限定公開として投稿
  python qiita_post.py --draft article.md

  # 送信内容を確認するだけ（APIを叩かない）
  python qiita_post.py --dry-run article.md

  # 投稿済み記事の一覧を表示
  python qiita_post.py list

  # 設定ファイルの場所とユーザー名を確認
  python qiita_post.py config show

設定ファイル（~/.config/qiita_post/config.json）:
  {
    "token": "個人アクセストークン"
  }

  ※ https://qiita.com/settings/tokens/new で発行
        """,
    )
    sub = parser.add_subparsers(dest="command")

    # post サブコマンド
    p_post = sub.add_parser("post", parents=[config_parser], help="Markdownファイルを投稿（新規作成または更新）")
    p_post.add_argument("file", help="Markdownファイルのパス")
    p_post.add_argument("--draft", "-d", action="store_true", help="限定公開として投稿（frontmatter の private より優先）")
    p_post.add_argument("--dry-run", action="store_true", dest="dry_run", help="APIを叩かずに送信内容を表示する")
    p_post.add_argument("--no-images", action="store_true", dest="no_images", help="画像アップロードをスキップする")
    p_post.set_defaults(func=cmd_post)

    # list サブコマンド
    p_list = sub.add_parser("list", parents=[config_parser], help="投稿済み記事の一覧を表示")
    p_list.set_defaults(func=cmd_list)

    # config サブコマンド
    p_config = sub.add_parser("config", parents=[config_parser], help="設定を表示")
    p_config.add_argument("action", choices=["show"], help="show: 現在の設定を表示")
    p_config.set_defaults(func=cmd_config)

    # delete サブコマンド
    p_delete = sub.add_parser("delete", parents=[config_parser], help="記事を削除する")
    p_delete.add_argument("id", help="削除する記事の Qiita ID")
    p_delete.add_argument("--yes", "-y", action="store_true", help="確認プロンプトをスキップ")
    p_delete.set_defaults(func=cmd_delete)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
