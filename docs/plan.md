# qiita-post 設計書

## 概要

Markdown ファイルを Qiita API 経由で投稿・更新する CLI ツール。
記事は単一の Markdown ファイルとして管理し（フラット構造）、投稿状態を frontmatter に記録する。

**設計参照:** `~/work/github.com/whtwnd-cli/` と同じ思想・構造で実装する。
- `atproto.py` に相当する共通モジュールを持つ
- `python-frontmatter` で frontmatter を処理する
- `scripts/install.sh` でシステムにインストールする
- `venv/` で Python 仮想環境を管理する
- SOLID 原則に従い、簡潔で拡張しやすい設計にする

---

## 記事ファイル仕様

### frontmatter

```yaml
---
title: "記事タイトル"
tags: [STM32, Rust, Embassy, Docker, Ubuntu]
private: false
qiita_id: ""          # 初回投稿後に自動書き込み
---
```

| フィールド | 必須 | 説明 |
|---|---|---|
| `title` | ✓ | 記事タイトル |
| `tags` | ✓ | タグ一覧（Qiita は最大5個） |
| `private` | - | 限定公開フラグ（デフォルト: false） |
| `qiita_id` | - | 投稿後に自動書き込み。存在すれば更新、なければ新規作成 |

### ファイル配置

特定のディレクトリ構造を要求しない。任意のパスの Markdown ファイルを対象にする。

---

## CLI 仕様

```
qiita-post <file>              # 投稿（qiita_id の有無で新規/更新を自動判定）
qiita-post --draft <file>      # 限定公開として投稿（private: true で上書き）
qiita-post --dry-run <file>    # API を叩かずに送信内容を標準出力に表示
qiita-post list                # 投稿済み記事一覧（自分のアカウントの記事）
qiita-post config show         # 設定ファイルのパスとユーザー名を表示
```

### 動作フロー（post）

```
1. Markdown ファイルを読み込む
2. frontmatter を解析（title, tags, private, qiita_id）
3. qiita_id が空 → POST /api/v2/items（新規作成）
   qiita_id がある → PATCH /api/v2/items/:id（更新）
4. 成功時: qiita_id を frontmatter に書き戻す
5. 記事 URL を標準出力に表示
```

---

## 認証

環境変数または設定ファイルでアクセストークンを渡す。

### 設定ファイル（whtwnd-cli の `.bsky_config.json` に相当）

`~/.config/qiita_post/config.json`:

```json
{
  "token": "your_personal_access_token"
}
```

### 設定ファイルの読み込み順

1. `--config FILE` で明示指定されたファイル
2. カレントディレクトリの `.qiita_config.json`
3. `~/.config/qiita_post/config.json`

環境変数 `QIITA_TOKEN` が設定されている場合はそちらを優先。

---

## Qiita API リファレンス

- ベース URL: `https://qiita.com/api/v2`
- 認証ヘッダー: `Authorization: Bearer {token}`
- レート制限: 1000 req/hour（認証済み）

### 新規作成 POST /api/v2/items

**リクエスト:**
```json
{
  "title": "記事タイトル",
  "body": "# マークダウン本文",
  "tags": [
    {"name": "STM32", "versions": []},
    {"name": "Rust", "versions": []}
  ],
  "private": false
}
```

**レスポンス（成功時 201）:**
```json
{
  "id": "c686397e4a0f4f11683d",
  "url": "https://qiita.com/username/items/c686397e4a0f4f11683d",
  "title": "...",
  ...
}
```

`id` を `qiita_id` として frontmatter に書き戻す。

### 更新 PATCH /api/v2/items/:id

リクエストボディは新規作成と同じ構造。成功時 200。

### 自分の記事一覧 GET /api/v2/authenticated_user/items

```
GET /api/v2/authenticated_user/items?page=1&per_page=20
```

---

## ファイル構成（目標）

```
qiita-post/
  qiita_post.py       # メインスクリプト（whtwnd_post.py に相当）
  qiita_api.py        # Qiita API 呼び出し共通モジュール（atproto.py に相当）
  requirements.txt    # 依存パッケージ（requests, python-frontmatter）
  README.md           # ユーザー向けドキュメント
  CLAUDE.md           # Claude Code 向け指示書
  .gitignore          # venv / __pycache__ / .qiita_config.json を除外
  scripts/
    qiita_post.sh     # qiita_post.py のラッパー（venv 自動適用）
    install.sh        # ~/.local/bin/ へインストール
  docs/
    plan.md           # このファイル
  venv/               # Python 仮想環境（.gitignore 対象）
```

### インストール後（リポジトリ外）

```
~/.local/bin/
  qiita_post          # install.sh が生成するランチャー

~/.config/qiita_post/
  config.json         # 設定ファイルの推奨配置パス（.gitignore 対象）
```

---

## 実装方針

- 言語: **Python 3.10+**（whtwnd-cli に揃える）
- frontmatter: `python-frontmatter` パッケージを使用
- HTTP: `requests` パッケージを使用
- SOLID 原則に従う
- ソースコード中のコメント・メッセージは日本語
- ドキュメントは日本語（指定がない場合）
- ディレクトリ名・ファイル名は英語

---

## 実装タスク

### Phase 1: 基本機能

- [ ] `venv` セットアップ・`requirements.txt` 作成
- [ ] `qiita_api.py`: 認証・設定ファイル読み込み
- [ ] `qiita_api.py`: POST /api/v2/items（新規作成）
- [ ] `qiita_api.py`: PATCH /api/v2/items/:id（更新）
- [ ] `qiita_post.py`: frontmatter 解析（`python-frontmatter`）
- [ ] `qiita_post.py`: `post` コマンド（新規/更新の自動判定）
- [ ] `qiita_post.py`: 投稿後に `qiita_id` を frontmatter に書き戻す
- [ ] `--dry-run` オプション
- [ ] `scripts/install.sh` 作成

### Phase 2: ユーザビリティ

- [ ] `list` コマンド（自分の記事一覧）
- [ ] `config show` コマンド
- [ ] `--draft` オプション
- [ ] エラーハンドリング（401/404/429/5xx）
- [ ] 429・5xx のリトライ（エクスポネンシャルバックオフ）

### Phase 3: 発展

- [ ] タグ数 5 件超過の警告
- [ ] `--config` グローバルオプション

---

## 参考リポジトリ

- `~/work/github.com/whtwnd-cli/` — 設計の参照元。同じ構造・規約で実装する
  - `whtwnd_post.py` — メインスクリプトの参考
  - `atproto.py` — 共通モジュールの参考（`qiita_api.py` に相当）
  - `scripts/install.sh` — インストールスクリプトの参考
- Qiita API v2: https://qiita.com/api/v2/docs
- 個人アクセストークン発行: https://qiita.com/settings/tokens/new
