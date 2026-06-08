# AWS S3 + CloudFront 認証情報の取得・設定

Terraform によるインフラ構築と boto3 による画像アップロードに必要な認証情報の取得・設定手順。

---

## 必要な認証情報の全体像

| 用途 | 種類 | 取得方法 |
|---|---|---|
| Terraform 実行 | AWS CLI の既存認証情報 | `~/.aws/credentials`（設定済みであれば不要） |
| boto3 アップロード | IAM ユーザーのアクセスキー | Terraform が作成・出力する |

Cloudflare と異なり、**Terraform 用の専用トークンは不要**。  
既存の AWS CLI 認証情報（管理者権限またはそれに準じる権限）をそのまま使用する。  
アップロード用の最小権限 IAM ユーザーは Terraform が自動作成する。

---

## 1. Terraform 実行用の認証情報確認

Terraform は `~/.aws/credentials` または環境変数から認証情報を自動取得する。

```bash
# 現在の認証情報を確認
aws sts get-caller-identity
```

以下のように表示されれば準備完了:

```json
{
    "UserId": "AIDAXXXXXXXXXXXXXXXXX",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/your-user"
}
```

Terraform 実行に必要な IAM 権限:

| サービス | 必要な権限 |
|---|---|
| S3 | `s3:CreateBucket`、`s3:PutBucketPolicy`、`s3:PutPublicAccessBlock` など |
| CloudFront | `cloudfront:CreateDistribution`、`cloudfront:CreateOriginAccessControl` など |
| IAM | `iam:CreateUser`、`iam:PutUserPolicy`、`iam:CreateAccessKey` など |

---

## 2. Terraform によるリソース作成

```bash
cd infra/aws
terraform init
terraform plan
terraform apply
```

成功すると以下が出力される（`outputs.tf` で定義）:

```
cloudfront_url      = "https://xxxxx.cloudfront.net"
bucket_name         = "your-qiita-images"
iam_access_key_id   = "AKIAXXXXXXXXXXXXXXXX"
iam_secret_access_key = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

`iam_secret_access_key` は **Terraform apply 時のみ表示**（再表示するには `terraform output -json` を実行）。

---

## 3. boto3 用 IAM 認証情報の設定

Terraform の出力値を `~/.aws/credentials` にプロファイルとして追記する。  
config.json には認証情報を書かない。

```ini
# ~/.aws/credentials に追記
[qiita-post]
aws_access_key_id     = AKIAXXXXXXXXXXXXXXXX
aws_secret_access_key = xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

```bash
# 動作確認（qiita-post プロファイルで S3 にアクセスできることを確認）
AWS_PROFILE=qiita-post aws s3 ls s3://your-qiita-images
```

---

## 4. config.json の設定

認証情報は `~/.aws/credentials` で管理するため、config.json には接続情報のみ記載する。

```json
{
  "token": "qiita_token",
  "image_host": "s3",
  "s3": {
    "bucket":          "your-qiita-images",
    "region":          "ap-northeast-1",
    "prefix":          "qiita/",
    "cloudfront_url":  "https://xxxxx.cloudfront.net",
    "profile":         "qiita-post"
  }
}
```

`profile` キーを省略した場合は `default` プロファイルまたは環境変数 `AWS_PROFILE` が使用される。

---

## 5. アカウント ID の確認

CloudFront の ARN 構成などで使用する。

```bash
aws sts get-caller-identity --query Account --output text
```

---

## Terraform 削除後の後処理

`terraform destroy` で IAM ユーザーが削除されると、そのアクセスキーも無効になる。  
`~/.aws/credentials` から `[qiita-post]` セクションを手動で削除しておく。

```bash
# infra/aws/terraform.destroy 前にバケットを空にする（必須）
aws s3 rm s3://your-qiita-images --recursive

cd infra/aws
terraform destroy

# ~/.aws/credentials の [qiita-post] セクションを削除
```

---

## 準備チェックリスト

- [ ] `aws sts get-caller-identity` で認証情報が有効であることを確認した
- [ ] `terraform apply` が成功し、outputs を取得した
- [ ] `~/.aws/credentials` に `[qiita-post]` プロファイルを追記した
- [ ] `config.json` の `s3` セクションに `cloudfront_url`・`bucket_name`・`profile` を記載した
- [ ] `AWS_PROFILE=qiita-post aws s3 ls s3://your-bucket` で疎通確認した

---

## 関連ドキュメント

- `docs/aws-setup.md` — Terraform による S3 + CloudFront 構築手順（Phase 4-1 実装時に作成）
- `docs/plan.md` — Phase 4-1 タスク一覧
