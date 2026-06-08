"""
qiita_api.py - Qiita API 共通操作モジュール

qiita_post.py から使用する。
- 設定ファイルの読み込み
- HTTPリクエスト共通処理（リトライ・エラーハンドリング）
- Qiita API 呼び出し（記事の作成・更新・一覧取得）
"""

import json
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("requests が必要です: pip install requests")
    sys.exit(1)

QIITA_BASE = "https://qiita.com/api/v2"

_LOCAL_CONFIG = Path(".qiita_config.json")
_HOME_CONFIG = Path.home() / ".config" / "qiita_post" / "config.json"


# ──────────────────────────────────────────────
# HTTP共通処理（リトライ）
# ──────────────────────────────────────────────

def api_request(method: str, url: str, *, max_retries: int = 3, **kwargs) -> requests.Response:
    """
    HTTPリクエストを実行する。
    以下の場合にエクスポネンシャルバックオフでリトライする:
      - ネットワークエラー（Timeout / ConnectionError）
      - 429 レート制限
      - 5xx サーバーエラー
    """
    for attempt in range(max_retries):
        try:
            resp = requests.request(method, url, **kwargs)
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                _backoff("タイムアウト", attempt, max_retries)
                continue
            print("エラー: 接続タイムアウトが続いています。ネットワーク環境を確認してください。")
            sys.exit(1)
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                _backoff("接続エラー", attempt, max_retries)
                continue
            print("エラー: サーバーに接続できません。ネットワーク環境を確認してください。")
            sys.exit(1)

        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 2 ** (attempt + 1)))
            if attempt < max_retries - 1:
                _backoff("レート制限", attempt, max_retries, wait)
                continue
            print("エラー: レート制限に達しました。しばらく時間をおいてから再試行してください。")
            sys.exit(1)

        if resp.status_code >= 500 and attempt < max_retries - 1:
            _backoff(f"サーバーエラー ({resp.status_code})", attempt, max_retries)
            continue

        return resp

    return resp


def _backoff(reason: str, attempt: int, max_retries: int, wait: int | None = None):
    """リトライ待機のアナウンスとsleep"""
    if wait is None:
        wait = 2 ** attempt
    print(f"  {reason}: {wait}秒後にリトライします... ({attempt + 1}/{max_retries})")
    time.sleep(wait)


# ──────────────────────────────────────────────
# 設定読み込み
# ──────────────────────────────────────────────

def resolve_config_path(config_path: str | None = None) -> Path:
    """設定ファイルのパスを解決する。明示指定がなければカレントディレクトリ→ホームの順に探す"""
    if config_path is not None:
        return Path(config_path)
    return _LOCAL_CONFIG if _LOCAL_CONFIG.exists() else _HOME_CONFIG


def load_config(config_path: str | None = None) -> dict:
    """設定ファイルを読み込む"""
    path = resolve_config_path(config_path)
    if not path.exists():
        print(f"設定ファイルが見つかりません: {path.resolve()}")
        print("以下の形式で作成してください:")
        print(json.dumps({"token": "your_personal_access_token"}, ensure_ascii=False, indent=2))
        print(f"  または環境変数 QIITA_TOKEN にトークンを設定してください。")
        sys.exit(1)
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"エラー: 設定ファイルのJSON形式が不正です: {path}")
        print(f"  詳細: {e}")
        print("以下の形式で修正してください:")
        print(json.dumps({"token": "your_personal_access_token"}, ensure_ascii=False, indent=2))
        sys.exit(1)


def load_token(config_path: str | None = None) -> str:
    """
    アクセストークンを返す。
    環境変数 QIITA_TOKEN を最優先し、なければ設定ファイルから読み込む。
    """
    token = os.environ.get("QIITA_TOKEN")
    if token:
        return token
    config = load_config(config_path)
    token = config.get("token", "")
    if not token:
        print("エラー: 設定ファイルに token が設定されていません。")
        print("  設定ファイルに以下を追加してください: \"token\": \"your_personal_access_token\"")
        sys.exit(1)
    return token


# ──────────────────────────────────────────────
# Qiita API
# ──────────────────────────────────────────────

def _auth_headers(token: str) -> dict:
    """認証ヘッダーを返す"""
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def create_item(token: str, title: str, body: str, tags: list[dict], private: bool = False) -> tuple[str, str]:
    """
    新規記事を作成して (item_id, url) を返す。
    失敗時は RuntimeError を送出する。
    """
    payload = {
        "title": title,
        "body": body,
        "tags": tags,
        "private": private,
    }
    resp = api_request(
        "POST",
        f"{QIITA_BASE}/items",
        headers=_auth_headers(token),
        json=payload,
        timeout=15,
    )
    if resp.status_code == 401:
        raise RuntimeError("記事作成失敗: トークンが無効です。個人アクセストークンを確認してください。")
    if resp.status_code == 422:
        raise RuntimeError(f"記事作成失敗: バリデーションエラー — {resp.json().get('message', resp.text)}")
    if not resp.ok:
        raise RuntimeError(f"記事作成失敗: {resp.status_code} {resp.text}")

    data = resp.json()
    return data["id"], data["url"]


def update_item(token: str, item_id: str, title: str, body: str, tags: list[dict], private: bool = False) -> str:
    """
    既存記事を更新して url を返す。
    失敗時は RuntimeError を送出する。
    """
    payload = {
        "title": title,
        "body": body,
        "tags": tags,
        "private": private,
    }
    resp = api_request(
        "PATCH",
        f"{QIITA_BASE}/items/{item_id}",
        headers=_auth_headers(token),
        json=payload,
        timeout=15,
    )
    if resp.status_code == 401:
        raise RuntimeError("記事更新失敗: トークンが無効です。個人アクセストークンを確認してください。")
    if resp.status_code == 403:
        raise RuntimeError(f"記事更新失敗: この記事を更新する権限がありません。")
    if resp.status_code == 404:
        raise RuntimeError(f"記事更新失敗: 記事が見つかりません (id: {item_id})")
    if resp.status_code == 422:
        raise RuntimeError(f"記事更新失敗: バリデーションエラー — {resp.json().get('message', resp.text)}")
    if not resp.ok:
        raise RuntimeError(f"記事更新失敗: {resp.status_code} {resp.text}")

    return resp.json()["url"]


def list_items(token: str, page: int = 1, per_page: int = 20) -> list[dict]:
    """
    自分の投稿済み記事一覧を返す。
    失敗時は sys.exit(1) する。
    """
    resp = api_request(
        "GET",
        f"{QIITA_BASE}/authenticated_user/items",
        headers=_auth_headers(token),
        params={"page": page, "per_page": per_page},
        timeout=15,
    )
    if resp.status_code == 401:
        print("一覧取得失敗: トークンが無効です。個人アクセストークンを確認してください。")
        sys.exit(1)
    if not resp.ok:
        print(f"一覧取得失敗: {resp.status_code} {resp.text}")
        sys.exit(1)
    return resp.json()


def delete_item(token: str, item_id: str) -> None:
    """
    記事を削除する。
    失敗時は RuntimeError を送出する。
    """
    resp = api_request(
        "DELETE",
        f"{QIITA_BASE}/items/{item_id}",
        headers=_auth_headers(token),
        timeout=15,
    )
    if resp.status_code == 401:
        raise RuntimeError("削除失敗: トークンが無効です。個人アクセストークンを確認してください。")
    if resp.status_code == 403:
        raise RuntimeError("削除失敗: この記事を削除する権限がありません。")
    if resp.status_code == 404:
        raise RuntimeError(f"削除失敗: 記事が見つかりません (id: {item_id})")
    if not resp.ok:
        raise RuntimeError(f"削除失敗: {resp.status_code} {resp.text}")


def get_authenticated_user(token: str) -> dict:
    """認証済みユーザー情報を返す。失敗時は sys.exit(1) する。"""
    resp = api_request(
        "GET",
        f"{QIITA_BASE}/authenticated_user",
        headers=_auth_headers(token),
        timeout=10,
    )
    if resp.status_code == 401:
        print("ユーザー情報取得失敗: トークンが無効です。")
        sys.exit(1)
    if not resp.ok:
        print(f"ユーザー情報取得失敗: {resp.status_code} {resp.text}")
        sys.exit(1)
    return resp.json()
