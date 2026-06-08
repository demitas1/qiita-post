# qiita-post

Markdown ファイルを Qiita API 経由で投稿・更新する CLI ツール。

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

### 限定公開として投稿

```bash
qiita_post --draft article.md
```

frontmatter の `private` より優先される。

### 送信内容の確認（API 呼び出しなし）

```bash
qiita_post --dry-run article.md
```

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

## 設定ファイルの探索順

1. 環境変数 `QIITA_TOKEN`
2. `--config FILE` で明示指定されたファイル
3. カレントディレクトリの `.qiita_config.json`
4. `~/.config/qiita_post/config.json`

## ライセンス

MIT License
