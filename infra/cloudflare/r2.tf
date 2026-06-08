resource "cloudflare_r2_bucket" "images" {
  account_id = var.account_id
  name       = var.bucket_name
}

# 注意: r2.dev パブリックアクセスの有効化は Cloudflare ダッシュボードから行う。
# Dashboard > R2 > バケット選択 > Settings > Public Access > Allow Access
# カスタムドメインを使う場合は cloudflare_r2_bucket_domain リソースを追加する。
