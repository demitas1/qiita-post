# qiita-post

Markdown ファイルを Qiita API 経由で投稿・更新する CLI ツール。  
ローカル画像を S3（または R2）にアップロードして CloudFront URL に置き換えてから投稿する機能を備える。

## インストール

```bash
git clone https://github.com/yourname/qiita-post.git
cd qiita-post
python3 -m venv venv
venv/bin/pip install -r requirements.txt
bash scripts/install.sh
```

## 設定

[Qiita の個人アクセストークン](https://qiita.com/settings/tokens/new) を発行し、設定ファイルを作成する。

```bash
mkdir -p ~/.config/qiita_post
cat > ~/.config/qiita_post/config.json << 'EOF'
{
  "token": "your_personal_access_token"
}
EOF
```

環境変数でも指定できる:

```bash
export QIITA_TOKEN=your_personal_access_token
```

### 画像アップロードを使う場合（AWS S3 + CloudFront）

```json
{
  "token": "your_personal_access_token",
  "image_host": "s3",
  "s3": {
    "bucket":         "your-bucket-name",
    "region":         "ap-northeast-1",
    "prefix":         "qiita/",
    "cloudfront_url": "https://xxxxx.cloudfront.net",
    "profile":        "your-aws-profile"
  }
}
```

AWS 認証は `~/.aws/credentials` のプロファイルで管理する（`profile` を省略するとデフォルトプロファイルを使用）。  
インフラ構築手順は `infra/aws/` および `docs/aws-credentials.md` を参照。

## 記事ファイルのフォーマット

```markdown
---
title: 記事タイトル
tags: [STM32, Rust, Embassy, Docker, Ubuntu]
private: false
qiita_id: ""
---

記事本文（Markdown）
```

| フィールド | 必須 | 説明 |
|---|---|---|
| `title` | ✓ | 記事タイトル |
| `tags` | ✓ | タグ一覧（最大5個） |
| `private` | — | `true` にすると限定公開（デフォルト: `false`） |
| `qiita_id` | — | 初回投稿後に自動書き込み。存在すれば更新、なければ新規作成 |

## 使い方

### 投稿・更新

```bash
qiita_post article.md
```

`qiita_id` が空なら新規作成、入力済みなら更新。投稿後は `qiita_id` が frontmatter に自動書き込みされる。

`image_host` が設定されている場合、本文中のローカル画像リンク（`![alt](./image.png)` 形式）を自動的にアップロードして CloudFront URL に置き換える。置き換え後の本文は `article.qiita.md` として保存される（元ファイルは保持）。

### 限定公開として投稿

```bash
qiita_post --draft article.md
```

frontmatter の `private` より優先される。

### 画像のみ処理・ファイル保存（投稿しない）

```bash
qiita_post --replace-only article.md
```

ローカル画像を S3 にアップロードして URL を置き換えた `article.qiita.md` を保存するが、Qiita への投稿は行わない。事前に画像処理の結果を確認したい場合に使う。

### 画像処理をスキップして投稿

```bash
qiita_post --no-images article.md
```

画像のアップロード・リンク置き換えを行わずに投稿する。以下のチェックを行い、問題があれば中断する:

- ローカル画像リンクが含まれていれば **エラーで中断**
- `http://` / `https://` の画像リンクは **HEAD リクエストで存在確認**し、無効なら **エラーで中断**

### 送信内容の確認（API 呼び出しなし）

```bash
qiita_post --dry-run article.md
```

実際の処理を行わずに送信内容を確認する:

- ローカル画像は `![alt](<UPLOAD:path>)` の形式で表示（アップロードなし）
- `http://` / `https://` の画像リンクは HEAD リクエストで存在確認し、結果を表示（無効でも中断しない）
- Qiita API への投稿・`article.qiita.md` の保存は行わない

### 記事を削除

```bash
qiita_post delete <qiita_id>
```

削除前に確認プロンプトが表示される。`--yes` / `-y` で省略可。

### 記事一覧

```bash
qiita_post list
```

### 設定の確認

```bash
qiita_post config show
```

### 設定ファイルの明示指定

```bash
qiita_post --config /path/to/config.json article.md
```

## オプション早見表

| オプション | 説明 |
|---|---|
| `--draft` / `-d` | 限定公開として投稿 |
| `--dry-run` | API を呼ばずに送信内容を表示 |
| `--replace-only` | 画像を処理して `.qiita.md` を保存するのみ（投稿しない） |
| `--no-images` | 画像処理をスキップ（ローカルリンクや無効な URL があればエラー） |
| `--config FILE` | 設定ファイルのパスを明示指定 |

## 画像処理のワークフロー

```
article.md（ローカル画像参照）
  ↓ qiita_post --replace-only article.md   # 画像を処理して確認
article.qiita.md（CloudFront URL に置き換え済み）
  ↓ qiita_post article.md                  # 投稿（.qiita.md も同時生成）
Qiita に投稿済み
```

再投稿時はすでに CloudFront URL に置き換わっているため、ローカルリンクは存在せず画像処理はスキップされる。

## 設定ファイルの探索順

1. 環境変数 `QIITA_TOKEN`
2. `--config FILE` で明示指定されたファイル
3. カレントディレクトリの `.qiita_config.json`
4. `~/.config/qiita_post/config.json`

## ライセンス

MIT License
