# Cloudflare R2 + CDN 認証情報の取得

Terraform によるインフラ構築と boto3 による画像アップロードに必要な認証情報の取得手順。

---

## 必要な認証情報の全体像

| 用途 | 種類 | 取得場所 |
|---|---|---|
| Terraform provider 認証 | Cloudflare API トークン | Dashboard > My Profile > API Tokens |
| boto3 / S3 互換 API 認証 | R2 API トークン（アクセスキー形式） | Dashboard > R2 > Manage R2 API Tokens |
| R2 エンドポイント URL の構成 | アカウント ID | Dashboard 右サイドバー |

---

## 1. アカウント ID の取得

Cloudflare ダッシュボード（dash.cloudflare.com）にログイン後、右サイドバーの **「Account ID」** をコピーする。

R2 エンドポイント URL に使用する:

```
https://{account_id}.r2.cloudflarestorage.com
```

---

## 2. Terraform 用 API トークンの作成

**My Profile > API Tokens > Create Token > Create Custom Token**

| 項目 | 設定値 |
|---|---|
| Token name | `terraform-qiita-post` など |
| Permissions | **Workers R2 Storage: Edit**（必須）← バケット作成・削除・オブジェクト管理 |
| Permissions | **Zone: Read**（カスタムドメインを使う場合） |
| Account Resources | Entire Account（または対象アカウントを指定） |
| Zone Resources | カスタムドメインを使う場合は対象ゾーンを指定 |

> **注意:** 検索で "r2" と入力すると "Workers R2 Data Catalog" が先に表示されるが、これはデータ分析用であり今回は不要。**Workers R2 Storage の Edit** を選択すること。

作成後に表示されるトークン文字列をメモする（**再表示不可**）。

```hcl
# infra/cloudflare/terraform.tfvars
cloudflare_api_token = "ここに貼る"
account_id           = "ここに貼る"
```

---

## 3. R2 API トークン（boto3 用）の作成

Terraform ではなく、**Python からのアップロード（boto3）に使う** S3 互換の認証情報。  
Terraform 用 API トークンとは別に作成する。

**Dashboard > R2 > 右上「Manage R2 API Tokens」> Create API Token**

| 項目 | 設定値 |
|---|---|
| Token name | `qiita-post-uploader` など |
| Permissions | **Object Read & Write** |
| Specify bucket | 対象バケットを指定（または All buckets） |
| TTL | 任意（無期限でも可） |

作成後に表示される以下をメモする（**再表示不可**）:

```
Access Key ID:     xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Secret Access Key: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

`config.json` の `r2` セクションに記載する:

```json
{
  "token": "qiita_token",
  "image_host": "r2",
  "r2": {
    "account_id":        "アカウントID",
    "bucket":            "バケット名",
    "prefix":            "qiita/",
    "access_key_id":     "Access Key ID",
    "secret_access_key": "Secret Access Key",
    "public_url":        "https://pub-xxxx.r2.dev または カスタムドメイン"
  }
}
```

---

## 4. カスタムドメイン vs r2.dev

| | r2.dev サブドメイン | カスタムドメイン |
|---|---|---|
| 設定の手間 | ほぼなし | DNS レコード追加が必要 |
| URL 形式 | `pub-xxxx.r2.dev/...` | `images.yourdomain.com/...` |
| Terraform リソース | `cloudflare_r2_bucket` の public_access を有効化するだけ | `cloudflare_r2_custom_domain` リソースが追加で必要 |
| Cloudflare プラン | 無料プランで可 | ドメインが Cloudflare で管理されていること（無料プランで可） |

手軽さ優先なら **r2.dev**、独自 URL が必要なら **カスタムドメイン** を選択する。

---

## 準備チェックリスト

- [ ] アカウント ID をメモした
- [ ] Terraform 用 API トークンを作成した（R2:Edit 権限）
- [ ] R2 API トークン（Access Key ID + Secret Access Key）を作成した
- [ ] `infra/cloudflare/terraform.tfvars` に API トークンとアカウント ID を記載した
- [ ] `config.json` の `r2` セクションに R2 API トークンを記載した

---

## 補足: 必要なツールについて

今回の R2 + CDN セットアップで必要なツールは以下の2つのみ。

| ツール | 用途 |
|---|---|
| Terraform | インフラ構築（R2 バケット・CDN 設定） |
| boto3（Python） | 画像アップロード（`uploader_r2.py` 内で使用） |

**Wrangler**（Cloudflare 公式 CLI）や **AWS CLI**（`--endpoint-url` で R2 に向ける使い方）は補足的な操作ツールとして存在するが、今回のセットアップでは不要。インフラは Terraform で、アップロードは boto3 で完結する。

---

## 関連ドキュメント

- `docs/r2-setup.md` — Terraform によるR2バケット構築手順（Phase 4-2 実装時に作成）
- `docs/plan.md` — Phase 4-2 タスク一覧
