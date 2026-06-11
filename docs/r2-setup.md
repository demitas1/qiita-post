# Cloudflare R2 セットアップ手順

`infra/cloudflare/` の Terraform 構成を使って Cloudflare R2 バケットを構築する手順書。

---

## 前提条件

- Cloudflare アカウント（R2 サブスクリプション有効化済み — 下記手順 0 を参照）
- tfenv インストール済み（`tfenv install 1.15.5 && tfenv use 1.15.5`）
- Cloudflare API トークン（権限: **Cloudflare R2 Storage: Edit**）
  - 発行手順: [Cloudflare ダッシュボード](https://dash.cloudflare.com/) > My Profile > API Tokens > Create Token
  - テンプレート: "Edit Cloudflare Workers" から R2 権限のみのトークンを作成

---

## 0. R2 サブスクリプションの有効化（初回のみ）

R2 を初めて使う場合、バケット作成前にサブスクリプション登録が必要。

1. [Cloudflare ダッシュボード](https://dash.cloudflare.com/) > 左メニュー **R2** をクリック
2. **"Get started with R2"** 画面で **"Add R2 subscription to my account"** をクリック
3. 無料枠の確認（ストレージ 10GB/月・Class A 1M ops/月・Class B 10M ops/月は無料）
4. **Total Due Now: $0.00** を確認して登録を完了する

> 無料枠を超えた場合のみ課金される。このプロジェクトの用途では無料枠内に収まる見込み。

---

## 1. terraform.tfvars の設定

```bash
cd infra/cloudflare
cp terraform.tfvars.example terraform.tfvars
```

`terraform.tfvars` を編集して値を設定：

```hcl
cloudflare_api_token = "your-cloudflare-api-token"
account_id           = "your-cloudflare-account-id"  # Dashboard 右サイドバーに表示
# bucket_name        = "qiita-post-images"            # デフォルトから変更する場合のみ
```

アカウント ID の確認: [Cloudflare ダッシュボード](https://dash.cloudflare.com/) の右サイドバー > "Account ID"

---

## 2. Terraform でバケットを構築

```bash
cd infra/cloudflare
terraform init
terraform plan
terraform apply
```

`apply` 後に出力される値を確認：

```
Outputs:
bucket_name  = "qiita-post-images"
r2_endpoint  = "https://<account_id>.r2.cloudflarestorage.com"
```

---

## 3. r2.dev パブリックアクセスを有効化（ダッシュボード操作）

Terraform では r2.dev の有効化がサポートされていないため、ダッシュボードから行う。

1. [Cloudflare ダッシュボード](https://dash.cloudflare.com/) > R2 > 作成されたバケットを選択
2. **Settings** タブ > **Public Development URL** セクション
3. **Enable** をクリックして有効化
4. 表示される URL（例: `https://pub-xxxxxxxx.r2.dev`）をメモする

---

## 4. R2 API トークン（アクセスキー）の発行

API トークンはバケット Settings ではなく **R2 トップページの Account Details** から発行する。

1. [Cloudflare ダッシュボード](https://dash.cloudflare.com/) > **R2 Object Storage**（バケット一覧ページ）
2. 右側 **Account Details** パネル > **API Tokens** > **"{ } Manage"** ボタンをクリック
3. **"Create API Token"** をクリック
4. 権限: **Object Read & Write**、対象バケット: `qiita-post-images`（または All buckets）
5. 発行された **Access Key ID** と **Secret Access Key** をメモ（画面を閉じると再表示不可）

---

## 5. config.json に R2 設定を追加

`~/.config/qiita_post/config.json`（またはプロジェクト直下の `config.json`）に追記：

```json
{
  "token": "your-qiita-token",
  "image_host": "r2",
  "r2": {
    "account_id": "your-cloudflare-account-id",
    "bucket": "qiita-post-images",
    "prefix": "qiita/",
    "access_key_id": "your-r2-access-key-id",
    "secret_access_key": "your-r2-secret-access-key",
    "public_url": "https://pub-xxxxxxxx.r2.dev"
  }
}
```

`public_url` には手順 3 で確認した r2.dev サブドメインを設定する。

---

## 動作確認

```bash
# テスト画像をアップロード
venv/bin/python - <<'PYEOF'
import json
from uploader_r2 import upload
with open("config.json") as f:
    config = json.load(f)
url = upload("tests/fixtures/test.png", config)
print(f"アップロード成功: {url}")
PYEOF

# CDN 経由でアクセスできることを確認（HTTP 200 が返ること）
curl -I <上記で出力された URL>
```

---

## バケットの削除（テスト完了後）

R2 バケットを削除する前にオブジェクトをすべて空にする必要がある。

```bash
# バケット内オブジェクトを削除
venv/bin/python - <<'PYEOF'
import boto3, json
with open("config.json") as f:
    cfg = json.load(f)["r2"]
s3 = boto3.client("s3",
    endpoint_url=f"https://{cfg['account_id']}.r2.cloudflarestorage.com",
    aws_access_key_id=cfg["access_key_id"],
    aws_secret_access_key=cfg["secret_access_key"],
    region_name="auto",
)
paginator = s3.get_paginator("list_objects_v2")
for page in paginator.paginate(Bucket=cfg["bucket"]):
    for obj in page.get("Contents", []):
        s3.delete_object(Bucket=cfg["bucket"], Key=obj["Key"])
        print(f"削除: {obj['Key']}")
PYEOF

# Terraform でバケットを削除
cd infra/cloudflare
terraform destroy
```

Cloudflare ダッシュボードで R2 バケットが削除されていることを確認する。
