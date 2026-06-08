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
qiita-post delete <id>         # 記事を削除（確認プロンプトあり）
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

- [x] `venv` セットアップ・`requirements.txt` 作成
- [x] `qiita_api.py`: 認証・設定ファイル読み込み
- [x] `qiita_api.py`: POST /api/v2/items（新規作成）
- [x] `qiita_api.py`: PATCH /api/v2/items/:id（更新）
- [x] `qiita_post.py`: frontmatter 解析（`python-frontmatter`）
- [x] `qiita_post.py`: `post` コマンド（新規/更新の自動判定）
- [x] `qiita_post.py`: 投稿後に `qiita_id` を frontmatter に書き戻す
- [x] `--dry-run` オプション
- [x] `scripts/install.sh` 作成

### Phase 2: ユーザビリティ

- [x] `list` コマンド（自分の記事一覧）
- [x] `config show` コマンド
- [x] `--draft` オプション
- [x] `delete <id>` コマンド（削除確認プロンプト・`--yes` で省略）
- [x] エラーハンドリング（401/404/429/5xx）
- [x] 429・5xx のリトライ（エクスポネンシャルバックオフ）

### Phase 3: 発展

- [x] タグ数 5 件超過の警告
- [x] `--config` グローバルオプション

---

### Phase 4-1: AWS S3 + CloudFront 対応（Issue #1, #2）

AWS S3 + CloudFront を使った画像ホスティングのインフラ構築と Python 実装。  
Phase 4-2（Cloudflare）とは**完全独立**。コード・設定・Terraform ディレクトリのいずれも共有しない。

#### 処理フロー

```
1. Markdown 本文の ![alt](./local/path.png) を正規表現で検出
2. http:// / https:// 始まりはスキップ
3. S3 にアップロード（同一ファイルは ETag で重複アップロードを回避）
4. Markdown 内の参照を CloudFront URL で置き換え
5. 置き換え後の本文を Qiita API に投稿
```

#### ファイル構成

```
uploader_s3.py          # S3 アップロードモジュール（単独で完結）
infra/aws/
  main.tf               # provider 設定（Terraform 1.15.5、hashicorp/aws ~> 5.0）
  s3.tf                 # S3 バケット（非公開）
  cloudfront.tf         # CloudFront ディストリビューション + OAC
  iam.tf                # IAM ユーザー（s3:PutObject 権限のみ）
  variables.tf
  outputs.tf            # cloudfront_url, bucket_name
  .terraform-version    # "1.15.5" を記載
  terraform.tfvars      # 秘密情報（.gitignore 対象）
docs/aws-setup.md       # Terraform によるセットアップ手順
```

#### config.json（AWS 用キーのみ）

```json
{
  "token": "qiita_token",
  "image_host": "s3",
  "s3": {
    "bucket": "your-bucket-name",
    "region": "ap-northeast-1",
    "prefix": "qiita/",
    "cloudfront_url": "https://xxxxx.cloudfront.net"
  }
}
```

AWS 認証は boto3 のデフォルト credential chain を使用（`~/.aws/credentials` または環境変数）。config.json に認証情報は書かない。

#### コスト試算（100本・年間50,000PV）

| 項目 | コスト |
|---|---|
| ストレージ（7.5MB） | ¥0（無視できる） |
| CloudFront 転送（3.6GB/年） | **¥0**（無料枠 1TB/月 以内） |
| S3 → CloudFront 転送 | **¥0**（無料） |
| **合計** | **¥0〜¥100/年** |

#### タスク

- [ ] `infra/aws/` Terraform 構成作成（S3 + CloudFront + IAM）
- [ ] `docs/aws-setup.md` 作成（Terraform セットアップ手順）
- [ ] `requirements.txt` に `boto3` 追加
- [ ] `uploader_s3.py` 実装（`upload(local_path, config) → url`）
- [ ] `qiita_post.py` の `cmd_post` に `process_markdown_images()` を組み込む
- [ ] `--no-images` オプションでスキップ可能にする
- [ ] ローカル画像が存在しない場合の警告

---

### Phase 4-2: Cloudflare R2 + CDN 対応（Issue #1, #2）

Cloudflare R2 + CDN を使った画像ホスティングのインフラ構築と Python 実装。  
Phase 4-1（AWS）とは**完全独立**。コード・設定・Terraform ディレクトリのいずれも共有しない。

#### 処理フロー

```
1. Markdown 本文の ![alt](./local/path.png) を正規表現で検出
2. http:// / https:// 始まりはスキップ
3. R2 にアップロード（同一ファイルは ETag で重複アップロードを回避）
4. Markdown 内の参照を CDN の public_url で置き換え
5. 置き換え後の本文を Qiita API に投稿
```

#### ファイル構成

```
uploader_r2.py          # R2 アップロードモジュール（単独で完結）
infra/cloudflare/
  main.tf               # provider 設定（Terraform 1.15.5、cloudflare/cloudflare ~> 4.0）
  r2.tf                 # R2 バケット + カスタムドメイン
  variables.tf
  outputs.tf            # public_url, bucket_name
  .terraform-version    # "1.15.5" を記載
  terraform.tfvars      # 秘密情報（.gitignore 対象）
docs/r2-setup.md        # Terraform によるセットアップ手順
```

#### config.json（R2 用キーのみ）

```json
{
  "token": "qiita_token",
  "image_host": "r2",
  "r2": {
    "account_id": "your-cloudflare-account-id",
    "bucket": "your-bucket-name",
    "prefix": "qiita/",
    "access_key_id": "your-r2-access-key",
    "secret_access_key": "your-r2-secret-key",
    "public_url": "https://your-custom-domain.example.com"
  }
}
```

R2 は boto3 の S3 互換モードで接続:  
`endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"`

#### コスト試算（100本・年間50,000PV）

| 項目 | コスト |
|---|---|
| ストレージ（7.5MB） | **¥0**（無料枠 10GB/月 以内） |
| CDN 転送 | **¥0**（エグレス料金ゼロ） |
| **合計** | **¥0/年** |

#### タスク

- [ ] `infra/cloudflare/` Terraform 構成作成（R2 + カスタムドメイン）
- [ ] `docs/r2-setup.md` 作成（Terraform セットアップ手順）
- [ ] `uploader_r2.py` 実装（`upload(local_path, config) → url`）
- [ ] `qiita_post.py` の `cmd_post` に R2 対応を追加（`image_host: "r2"` の場合）
- [ ] `--no-images` オプションでスキップ可能にする（4-1 との共通処理）
- [ ] ローカル画像が存在しない場合の警告（4-1 との共通処理）

---

## 参考リポジトリ

- `~/work/github.com/whtwnd-cli/` — 設計の参照元。同じ構造・規約で実装する
  - `whtwnd_post.py` — メインスクリプトの参考
  - `atproto.py` — 共通モジュールの参考（`qiita_api.py` に相当）
  - `scripts/install.sh` — インストールスクリプトの参考
- Qiita API v2: https://qiita.com/api/v2/docs
- 個人アクセストークン発行: https://qiita.com/settings/tokens/new
